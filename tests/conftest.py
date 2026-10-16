"""Shared integration fixtures: a real uvicorn server on a free localhost port.

Integration tests talk to it over real WebSockets, exactly as the TV and phones do.
"""

import json
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

import pytest
import uvicorn
from websockets.sync.client import ClientConnection


@contextmanager
def running_server(**app_options) -> Iterator[str]:
    from mayday.server import create_app

    app = create_app(join_url="http://192.168.0.10:8000", **app_options)
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
    try:
        yield f"127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)


@pytest.fixture
def server_address() -> Iterator[str]:
    with running_server() as address:
        yield address


@pytest.fixture
def quick_server_address() -> Iterator[str]:
    """A server whose questions close after half a second."""
    from mayday.trivia import Pace

    with running_server(pace=Pace(question=0.5)) as address:
        yield address


def receive_view(connection: ClientConnection, timeout: float = 2) -> dict:
    """Read messages until the next screen view arrives."""
    while True:
        message = json.loads(connection.recv(timeout=timeout))
        if message["t"] == "view":
            return message


def receive_screen(connection: ClientConnection, screen: str, timeout: float = 2) -> dict:
    """Read views until one for `screen` arrives."""
    while True:
        view = receive_view(connection, timeout)
        if view["screen"] == screen:
            return view
