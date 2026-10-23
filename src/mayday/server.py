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

from mayday.game import (
    Game,
    back_to_lobby,
    hand_over_helm,
    join_game,
    leave_game,
    play_again,
    skip_rules,
    start_game,
)
from mayday.guesses import GuessLog
from mayday.lobby import JoinRefusal, Lobby, PlayerId, leave
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

    def __init__(self, game: Game, join_url: str, captain_grace: float) -> None:
        self.game = game
        self.join_url = join_url
        self.captain_grace = captain_grace
        self.hosts: set[WebSocket] = set()
        self.phones: dict[WebSocket, PlayerId] = {}
        self.tokens: dict[str, PlayerId] = {}  # rejoin secrets (ADR-0009)
        self._clock_task: asyncio.Task | None = None
        self._grace_tasks: set[asyncio.Task] = set()

    async def let_go(self, player_id: PlayerId, lobby: Lobby) -> None:
        """A sailor left the ship (ADR-0013): forget their phone and token, then show the rest."""
        await self._forget(player_id, {"t": "left"})
        await self.apply(lobby)

    async def _forget(self, player_id: PlayerId, farewell: dict) -> None:
        """Drop a sailor's rejoin token and phone binding, telling the phone why."""
        self.tokens = {t: pid for t, pid in self.tokens.items() if pid != player_id}
        for ws, pid in list(self.phones.items()):
            if pid == player_id:
                del self.phones[ws]
                await _send_quietly(ws, farewell)

    def phone_gone(self, player_id: PlayerId) -> None:
        """A Captain whose last phone closed gets `captain_grace` seconds to return (ADR-0013)."""
        if not self._is_absent_captain(player_id):
            return
        task = asyncio.create_task(self._relieve_captain_if_still_gone(player_id))
        self._grace_tasks.add(task)
        task.add_done_callback(self._grace_tasks.discard)

    def _is_absent_captain(self, player_id: PlayerId) -> bool:
        captain = self.game.captain
        return captain is not None and captain.id == player_id and player_id not in self.phones.values()

    async def _relieve_captain_if_still_gone(self, player_id: PlayerId) -> None:
        """In the lobby the Captain is dropped; mid-game they hand over the helm instead."""
        await asyncio.sleep(self.captain_grace)
        if not self._is_absent_captain(player_id):
            return
        if isinstance(self.game, Lobby):
            await self.let_go(player_id, leave(self.game, player_id))
        elif len(self.game.players) > 1:
            await self.apply(hand_over_helm(self.game))

    async def new_voyage(self, lobby: Lobby) -> None:
        """Back to lobby (ADR-0012): forget everyone not aboard and invite their phones back."""
        aboard = {p.id for p in lobby.players}
        for player in self.game.players:
            if player.id not in aboard:
                await self._forget(player.id, {"t": "new_voyage", "name": str(player.name), "code": lobby.code})
        await self.apply(lobby)

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
    captain_grace: float = 60.0,
) -> Starlette:
    """`host_key`, when set, must be passed as `?key=` to open the TV socket (ADR-0008).
    `captain_grace`: seconds a Captain's phone may be gone from the lobby (ADR-0013)."""
    rng = rng or random.SystemRandom()
    bank = bank if bank is not None else read_question_bank()
    code = new_room_code(rng)
    table = Table(Lobby(code=code), join_url, captain_grace)
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
            # Say why before closing: proxies can delay the close frame (ADR-0008).
            await ws.send_json({"t": "refused", "reason": "host_key_required"})
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
            case "skip":
                await settle(ws, skip_rules(table.game, player_id, now))
            case "again":
                await settle(ws, play_again(table.game, player_id, fresh_questions(), now))
            case "lobby":
                result = back_to_lobby(table.game, player_id, code)
                if isinstance(result, Lobby):
                    await table.new_voyage(result)
                else:
                    await settle(ws, result)
            case "leave":
                result = leave_game(table.game, player_id)
                if isinstance(result, Lobby):
                    await table.let_go(player_id, result)
                else:
                    await settle(ws, result)
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
            if (player_id := table.phones.pop(ws, None)) is not None:
                table.phone_gone(player_id)

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
