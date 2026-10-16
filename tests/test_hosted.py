"""Slice 10: hosted on the public internet, only the laptop with the host key can open
the TV (and so see the room code), and guessing room codes gets you locked out."""

import json

import pytest
from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect

from conftest import receive_view, running_server


def test_tv_needs_the_host_key_when_one_is_set() -> None:
    with running_server(host_key="lighthouse") as address:
        with connect(f"ws://{address}/ws/host") as stranger:
            assert json.loads(stranger.recv(timeout=2))["reason"] == "host_key_required"
            with pytest.raises(ConnectionClosed) as closed:
                stranger.recv(timeout=2)
            assert closed.value.rcvd is not None and closed.value.rcvd.code == 4401

        with connect(f"ws://{address}/ws/host?key=wrong") as stranger:
            # Proxies (Render) can hold back the close frame, so the refusal comes first as a message.
            assert json.loads(stranger.recv(timeout=2)) == {"t": "refused", "reason": "host_key_required"}
            with pytest.raises(ConnectionClosed):
                stranger.recv(timeout=2)

        with connect(f"ws://{address}/ws/host?key=lighthouse") as tv:
            assert receive_view(tv)["screen"] == "lobby"


def test_repeated_wrong_codes_lock_the_guesser_out() -> None:
    with running_server() as address, connect(f"ws://{address}/ws/host") as tv:
        code = receive_view(tv)["code"]
        wrong = "".join("A" if c != "A" else "B" for c in code)
        with connect(f"ws://{address}/ws/play") as guesser:
            for _ in range(10):
                guesser.send(json.dumps({"t": "join", "code": wrong, "name": "Pirate"}))
                assert json.loads(guesser.recv(timeout=2))["reason"] == "wrong_code"
            guesser.send(json.dumps({"t": "join", "code": code, "name": "Pirate"}))
            assert json.loads(guesser.recv(timeout=2)) == {"t": "refused", "reason": "too_many_guesses"}

        with connect(f"ws://{address}/ws/play") as reconnected:
            reconnected.send(json.dumps({"t": "join", "code": code, "name": "Pirate"}))
            assert json.loads(reconnected.recv(timeout=2))["reason"] == "too_many_guesses"
