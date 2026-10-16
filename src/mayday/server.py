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
from enum import StrEnum
from pathlib import Path

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import FileResponse, Response
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket, WebSocketDisconnect

from mayday.game import Game, back_to_lobby, join_game, play_again, start_game
from mayday.guesses import GuessLog
from mayday.lobby import JoinRefusal, Lobby, PlayerId
from mayday.qr import join_link, qr_svg
from mayday.questions import Question, draw_questions, read_question_bank
from mayday.room_code import new_room_code
from mayday.trivia import AnswerRefusal, Pace, Trivia, answer, tick
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


class AlwaysRevalidate:
    """ASGI middleware: HTTP responses carry `Cache-Control: no-cache` unless they set their
    own, so after a redeploy no browser runs a cached old script against a new page."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_header(message) -> None:
            if message["type"] == "http.response.start":
                headers = message.setdefault("headers", [])
                if not any(name.lower() == b"cache-control" for name, _ in headers):
                    headers.append((b"cache-control", b"no-cache"))
            await send(message)

        await self.app(scope, receive, send_with_header)


class Table:
    """The live game and every device watching it."""

    def __init__(self, game: Game, join_url: str) -> None:
        self.game = game
        self.join_url = join_url
        self.hosts: set[WebSocket] = set()
        self.phones: dict[WebSocket, PlayerId] = {}
        self.tokens: dict[str, PlayerId] = {}  # rejoin secrets (ADR-0009)
        self._clock_task: asyncio.Task | None = None

    async def send_views(self) -> None:
        now = time.monotonic()
        for ws in list(self.hosts):
            await _send_quietly(ws, host_view(self.game, self.join_url, now))
        for ws, player_id in list(self.phones.items()):
            await _send_quietly(ws, player_view(self.game, player_id, now))

    async def apply(self, game: Game) -> None:
        """Every state change goes through here: store it, re-arm the clock, push views."""
        self.game = game
        self._run_clock()
        await self.send_views()

    def _run_clock(self) -> None:
        """Sleep until the game's next timed transition (ADR-0006), restarting on every change."""
        if self._clock_task is not None and self._clock_task is not asyncio.current_task():
            self._clock_task.cancel()
        self._clock_task = asyncio.create_task(self._tick_when_due())

    async def _tick_when_due(self) -> None:
        if not isinstance(self.game, Trivia) or (wakes_at := self.game.wakes_at) is None:
            return
        await asyncio.sleep(max(0.0, wakes_at - time.monotonic()))
        if not isinstance(self.game, Trivia):
            return
        ticked = tick(self.game, time.monotonic())
        if ticked is self.game:  # woke a hair early: nothing due yet, so don't resend views
            self._run_clock()
            return
        await self.apply(ticked)


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
    pace: Pace = Pace(),
    host_key: str | None = None,
) -> Starlette:
    """`host_key`, when set, must be passed as `?key=` to open the TV socket (ADR-0008)."""
    rng = rng or random.SystemRandom()
    bank = bank if bank is not None else read_question_bank()
    code = new_room_code(rng)
    table = Table(Lobby(code=code), join_url)
    guesses = GuessLog()

    async def settle(ws: WebSocket, result: Game | StrEnum) -> None:
        """A refusal goes back to the phone that asked; anything else becomes the new game."""
        if isinstance(result, StrEnum):
            await ws.send_json({"t": "refused", "reason": result.value})
        else:
            await table.apply(result)

    def fresh_questions() -> tuple[Question, ...]:
        return draw_questions(bank, rng, count=QUESTIONS_PER_GAME)

    def may_host(conn: WebSocket | Request) -> bool:
        return host_key is None or secrets.compare_digest(conn.query_params.get("key", ""), host_key)

    async def qr_code(request: Request) -> Response:
        """The TV's QR code; it carries the room code, so hosted it needs the key (ADR-0008)."""
        if not may_host(request):
            return Response("host key required", status_code=401)
        svg = qr_svg(join_link(table.join_url, code))
        return Response(svg, media_type="image/svg+xml", headers={"Cache-Control": "no-store"})

    async def host_socket(ws: WebSocket) -> None:
        await ws.accept()
        if not may_host(ws):
            await ws.close(code=4401, reason="host key required")
            return
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
        nonlocal guesses
        who, now = (ws.client.host if ws.client else "unknown"), time.monotonic()
        if guesses.locked(who, now):
            await settle(ws, JoinRefusal.TOO_MANY_GUESSES)
            return
        player_id = PlayerId(secrets.token_hex(8))
        result = join_game(table.game, _text(intent, "code"), _text(intent, "name"), player_id)
        if result is JoinRefusal.WRONG_CODE:
            guesses = guesses.record_wrong(who, now)
        if not isinstance(result, StrEnum):
            table.phones[ws] = player_id
        await settle(ws, result)
        if not isinstance(result, StrEnum):
            token = secrets.token_hex(16)
            table.tokens[token] = player_id
            await ws.send_json({"t": "welcome", "token": token})

    async def handle_rejoin(ws: WebSocket, intent: dict) -> None:
        player_id = table.tokens.get(_text(intent, "token"))
        if player_id is None:
            await settle(ws, JoinRefusal.UNKNOWN_PLAYER)
            return
        for other, pid in list(table.phones.items()):
            if pid == player_id:
                del table.phones[other]
        table.phones[ws] = player_id
        await table.send_views()

    async def handle_captain_or_answer(ws: WebSocket, player_id: PlayerId, intent: dict) -> None:
        now = time.monotonic()
        match intent.get("t"):
            case "start":
                await settle(ws, start_game(table.game, player_id, fresh_questions(), now, pace))
            case "again":
                await settle(ws, play_again(table.game, player_id, fresh_questions(), now))
            case "lobby":
                await settle(ws, back_to_lobby(table.game, player_id, code))
            case "answer" if isinstance(table.game, Trivia):
                await settle(ws, answer(table.game, player_id, intent.get("choice"), now))
            case "answer":
                await settle(ws, AnswerRefusal.ROUND_CLOSED)

    async def play_socket(ws: WebSocket) -> None:
        await ws.accept()
        try:
            while True:
                intent = _parse_intent(await ws.receive_text())
                player_id = table.phones.get(ws)
                if player_id is None:
                    if intent.get("t") == "join":
                        await handle_join(ws, intent)
                    elif intent.get("t") == "rejoin":
                        await handle_rejoin(ws, intent)
                else:
                    await handle_captain_or_answer(ws, player_id, intent)
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
            Route("/qr.svg", qr_code),
            WebSocketRoute("/ws/host", host_socket),
            WebSocketRoute("/ws/play", play_socket),
            Mount("/static", StaticFiles(directory=STATIC), name="static"),
        ],
        middleware=[Middleware(AlwaysRevalidate)],
    )
