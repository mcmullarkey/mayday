"""Live smoke test against a deployed server (ADR-0008). Skipped unless configured:

    MAYDAY_LIVE_URL=https://mayday-qsu4.onrender.com MAYDAY_HOST_KEY=... uv run pytest tests/test_live.py

Plays one question end to end over wss:// through Render's proxy. Restart the service
afterwards if you need a clean lobby (this leaves a game in progress).
"""

import json
import os

import pytest
from websockets.sync.client import connect

from conftest import receive_screen, receive_view

LIVE_URL = os.environ.get("MAYDAY_LIVE_URL", "").rstrip("/")
HOST_KEY = os.environ.get("MAYDAY_HOST_KEY", "")
pytestmark = pytest.mark.skipif(not LIVE_URL, reason="set MAYDAY_LIVE_URL to run against a deployed server")


def test_live_server_plays_a_question_over_wss() -> None:
    ws_base = LIVE_URL.replace("https://", "wss://").replace("http://", "ws://")
    with (
        connect(f"{ws_base}/ws/host?key={HOST_KEY}", open_timeout=90) as tv,
        connect(f"{ws_base}/ws/play") as phone,
    ):
        lobby = receive_view(tv, timeout=10)
        assert lobby["join_url"] == LIVE_URL
        phone.send(json.dumps({"t": "join", "code": lobby["code"], "name": "Smoke Test"}))
        assert receive_view(phone, timeout=10)["you"]["captain"] in (True, False)
        phone.send(json.dumps({"t": "start"}))
        question = receive_screen(tv, "question", timeout=10)
        phone.send(json.dumps({"t": "answer", "choice": 0}))
        reveal = receive_screen(tv, "reveal", timeout=10)
        assert reveal["prompt"] == question["prompt"]
