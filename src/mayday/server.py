"""Server: the effectful shell around the pure game core (ADR-0001).

Holds the one live Lobby and the open WebSockets for the TV and phones. Turns phone
intents into core transitions, then pushes a fresh view (ADR-0002) to every device.
Also serves the TV and phone pages.

Does not: contain game rules (lobby) or decide what a screen shows (views).
"""

import asyncio
import json
import random
import secrets
import time
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
from mayday.trivia import AnswerRefusal, Asking, Trivia, answer, expire
from mayday.views import host_view, player_view

STATIC = Path(__file__).parent / "static"
QUESTIONS_PER_GAME = 10
QUESTION_SECONDS = 20.0


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
        self._deadline_task: asyncio.Task | None = None

    async def send_views(self) -> None:
        now = time.monotonic()
        for ws in list(self.hosts):
            await _send_quietly(ws, host_view(self.game, self.join_url, now))
        for ws, player_id in list(self.phones.items()):
            await _send_quietly(ws, player_view(self.game, player_id, now))

    def watch_deadline(self) -> None:
        """Close the open question when its time runs out (ADR-0005)."""
        if self._deadline_task is not None:
            self._deadline_task.cancel()
        self._deadline_task = asyncio.create_task(self._expire_at_deadline())

    async def _expire_at_deadline(self) -> None:
        while isinstance(self.game, Trivia) and isinstance(self.game.round, Asking):
            remaining = self.game.round.deadline - time.monotonic()
            if remaining > 0:
                await asyncio.sleep(remaining)
                continue
            self.game = expire(self.game, time.monotonic())
            await self.send_views()


async def _send_quietly(ws: WebSocket, message: dict) -> None:
    """A device that vanished mid-send is cleaned up by its own handler; don't crash others."""
    try:
        await ws.send_json(message)
    except (WebSocketDisconnect, RuntimeError):
        pass


def create_app(
    join_url: str,
    rng: random.Random | None = None,
    bank: tuple[Question, ...] | None = None,
    question_seconds: float = QUESTION_SECONDS,
) -> Starlette:
    rng = rng or random.SystemRandom()
    bank = bank if bank is not None else read_question_bank()
    table = Table(Lobby(code=new_room_code(rng)), join_url)

    async def host_socket(ws: WebSocket) -> None:
        await ws.accept()
        table.hosts.add(ws)
        try:
            await ws.send_json(host_view(table.game, table.join_url, time.monotonic()))
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
        result = start_game(table.game, player_id, questions, time.monotonic(), question_seconds)
        if isinstance(result, StartRefusal):
            await ws.send_json({"t": "refused", "reason": result.value})
            return
        table.game = result
        table.watch_deadline()
        await table.send_views()

    async def handle_answer(ws: WebSocket, player_id: PlayerId, intent: dict) -> None:
        if not isinstance(table.game, Trivia):
            await ws.send_json({"t": "refused", "reason": AnswerRefusal.ROUND_CLOSED.value})
            return
        result = answer(table.game, player_id, intent.get("choice"), time.monotonic())
        if isinstance(result, AnswerRefusal):
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
                elif intent.get("t") == "answer":
                    await handle_answer(ws, player_id, intent)
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
