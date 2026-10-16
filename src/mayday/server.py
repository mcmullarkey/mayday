"""Server: the effectful shell around the pure game core (ADR-0001).

Holds the one live Lobby and the open WebSockets for the TV and phones. Turns phone
intents into core transitions, then pushes a fresh view (ADR-0002) to every device.
Also serves the TV and phone pages.

Does not: contain game rules (lobby) or decide what a screen shows (views).
"""

import random
import secrets
from pathlib import Path

from starlette.applications import Starlette
from starlette.responses import FileResponse
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket, WebSocketDisconnect

from mayday.lobby import Lobby, Player, PlayerId, join
from mayday.room_code import new_room_code
from mayday.views import host_view, player_view

STATIC = Path(__file__).parent / "static"


class Table:
    """The live game and every device watching it."""

    def __init__(self, lobby: Lobby, join_url: str) -> None:
        self.lobby = lobby
        self.join_url = join_url
        self.hosts: set[WebSocket] = set()
        self.phones: dict[WebSocket, PlayerId] = {}

    async def send_views(self) -> None:
        for ws in list(self.hosts):
            await ws.send_json(host_view(self.lobby, self.join_url))
        for ws, player_id in list(self.phones.items()):
            await ws.send_json(player_view(self.lobby, player_id))


def create_app(join_url: str, rng: random.Random | None = None) -> Starlette:
    table = Table(Lobby(code=new_room_code(rng or random.SystemRandom())), join_url)

    async def host_socket(ws: WebSocket) -> None:
        await ws.accept()
        table.hosts.add(ws)
        try:
            await ws.send_json(host_view(table.lobby, table.join_url))
            while True:
                await ws.receive_text()
        except WebSocketDisconnect:
            pass
        finally:
            table.hosts.discard(ws)

    async def play_socket(ws: WebSocket) -> None:
        await ws.accept()
        try:
            while True:
                intent = await ws.receive_json()
                if intent.get("t") == "join" and ws not in table.phones:
                    player = Player(id=PlayerId(secrets.token_hex(8)), name=intent["name"])
                    table.lobby = join(table.lobby, player)
                    table.phones[ws] = player.id
                    await table.send_views()
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
