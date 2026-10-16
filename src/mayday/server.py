"""Server: the effectful shell around the pure game core (ADR-0001).

Holds the one live Lobby and the open WebSockets for the TV and phones. Turns phone
intents into core transitions, then pushes a fresh view (ADR-0002) to every device.
Also serves the TV and phone pages.

Does not: contain game rules (lobby) or decide what a screen shows (views).
"""

import json
import random
import secrets
from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import FileResponse
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket, WebSocketDisconnect

from mayday.game import Game, StartRefusal, join_game, start_game
from mayday.lobby import JoinRefusal, Lobby, PlayerId
from mayday.questions import Question, draw_questions, read_question_bank
from mayday.room_code import new_room_code
from mayday.views import host_view, player_view

STATIC = Path(__file__).parent / "static"
QUESTIONS_PER_GAME = 10


def _parse_intent(raw: str) -> dict:
    """Untrusted phone input: anything that isn't a JSON object becomes an empty intent."""
    try:
        intent = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return intent if isinstance(intent, dict) else {}


def _text(intent: dict, key: str) -> str:
    value = intent.get(key)
    return value if isinstance(value, str) else ""


class Table:
    """The live game and every device watching it."""

    def __init__(self, game: Game, join_url: str) -> None:
        self.game = game
        self.join_url = join_url
        self.hosts: set[WebSocket] = set()
        self.phones: dict[WebSocket, PlayerId] = {}

    async def send_views(self) -> None:
        for ws in list(self.hosts):
            await ws.send_json(host_view(self.game, self.join_url))
        for ws, player_id in list(self.phones.items()):
            await ws.send_json(player_view(self.game, player_id))


def create_app(
    join_url: str,
    rng: random.Random | None = None,
    bank: tuple[Question, ...] | None = None,
) -> Starlette:
    rng = rng or random.SystemRandom()
    bank = bank if bank is not None else read_question_bank()
    table = Table(Lobby(code=new_room_code(rng)), join_url)

    async def host_socket(ws: WebSocket) -> None:
        await ws.accept()
        table.hosts.add(ws)
        try:
            await ws.send_json(host_view(table.game, table.join_url))
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            table.hosts.discard(ws)

    async def handle_join(ws: WebSocket, intent: dict) -> None:
        player_id = PlayerId(secrets.token_hex(8))
        result = join_game(table.game, _text(intent, "code"), _text(intent, "name"), player_id)
        if isinstance(result, JoinRefusal):
            await ws.send_json({"t": "refused", "reason": result.value})
            return
        table.game = result
        table.phones[ws] = player_id
        await table.send_views()

    async def handle_start(ws: WebSocket, player_id: PlayerId) -> None:
        questions = draw_questions(bank, rng, count=QUESTIONS_PER_GAME)
        result = start_game(table.game, player_id, questions)
        if isinstance(result, StartRefusal):
            await ws.send_json({"t": "refused", "reason": result.value})
            return
        table.game = result
        await table.send_views()

    async def play_socket(ws: WebSocket) -> None:
        await ws.accept()
        try:
            while True:
                intent = _parse_intent(await ws.receive_text())
                player_id = table.phones.get(ws)
                if player_id is None:
                    if intent.get("t") == "join":
                        await handle_join(ws, intent)
                elif intent.get("t") == "start":
                    await handle_start(ws, player_id)
        except WebSocketDisconnect:
            pass
        finally:
            table.phones.pop(ws, None)

    async def phone_page(_request) -> FileResponse:
        return FileResponse(STATIC / "play.html")

    async def host_page(_request) -> FileResponse:
        return FileResponse(STATIC / "host.html")

    return Starlette(
        routes=[
            Route("/", phone_page),
            Route("/host", host_page),
            WebSocketRoute("/ws/host", host_socket),
            WebSocketRoute("/ws/play", play_socket),
            Mount("/static", StaticFiles(directory=STATIC), name="static"),
        ]
    )
