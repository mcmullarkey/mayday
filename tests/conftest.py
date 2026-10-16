"""Shared integration fixtures: a real uvicorn server on a free localhost port.

Integration tests talk to it over real WebSockets, exactly as the TV and phones do.
"""

import json
import threading
import time
from collections.abc import Iterator

import pytest
import uvicorn
from websockets.sync.client import ClientConnection


@pytest.fixture
def server_address() -> Iterator[str]:
    from mayday.server import create_app

    app = create_app(join_url="http://192.168.0.10:8000")
    config = uvicorn.Config(app, host="127.0.0.1", port=0, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("test server did not start")
        time.sleep(0.01)
    port = server.servers[0].sockets[0].getsockname()[1]
    yield f"127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


def receive_view(connection: ClientConnection) -> dict:
    """Read messages until the next screen view arrives."""
    while True:
        message = json.loads(connection.recv(timeout=2))
        if message["t"] == "view":
            return message
