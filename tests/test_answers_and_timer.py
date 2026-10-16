"""Slice 4: when sailors tap a flag their answer locks in and the TV shows who's in;
the round closes when everyone has answered or the timer runs out, and the TV reveals
the right answer with who picked what."""

import json
import time

from websockets.sync.client import ClientConnection, connect

from conftest import receive_screen, receive_view


def _send(ws: ClientConnection, intent: dict) -> None:
    ws.send(json.dumps(intent))


def _board(address: str, tv: ClientConnection, *phones: ClientConnection) -> dict:
    """Join each phone in order (first is Captain), cast off, return the TV question view."""
    code = receive_view(tv)["code"]
    for i, phone in enumerate(phones):
        _send(phone, {"t": "join", "code": code, "name": f"Sailor {i}"})
        receive_view(phone)
    _send(phones[0], {"t": "start"})
    for phone in phones:
        receive_screen(phone, "question")
    return receive_screen(tv, "question")


def test_everyone_answering_closes_the_round_early(server_address: str) -> None:
    with (
        connect(f"ws://{server_address}/ws/host") as tv,
        connect(f"ws://{server_address}/ws/play") as dana,
        connect(f"ws://{server_address}/ws/play") as bev,
    ):
        question = _board(server_address, tv, dana, bev)
        assert 19_000 < question["remaining_ms"] <= 20_000
        assert [p["answered"] for p in question["players"]] == [False, False]

        _send(dana, {"t": "answer", "choice": 2})
        assert receive_screen(dana, "question")["your_choice"] == 2
        assert [p["answered"] for p in receive_screen(tv, "question")["players"]] == [True, False]

        started = time.monotonic()
        _send(bev, {"t": "answer", "choice": 0})
        reveal = receive_screen(tv, "reveal")
        assert time.monotonic() - started < 2

        assert reveal["prompt"] == question["prompt"]
        assert reveal["choices"] == question["choices"]
        picks = {i: [] for i in range(4)}
        picks[2].append("Sailor 0")
        picks[0].append("Sailor 1")
        assert reveal["picks"] == [picks[i] for i in range(4)]
        assert 0 <= reveal["answer"] < 4
        assert reveal["fact"]

        dana_reveal = receive_screen(dana, "reveal")
        assert dana_reveal["your_choice"] == 2
        assert dana_reveal["correct"] == (reveal["answer"] == 2)


def test_timer_closes_the_round_and_late_answers_bounce(quick_server_address: str) -> None:
    with (
        connect(f"ws://{quick_server_address}/ws/host") as tv,
        connect(f"ws://{quick_server_address}/ws/play") as dana,
        connect(f"ws://{quick_server_address}/ws/play") as bev,
    ):
        _board(quick_server_address, tv, dana, bev)
        _send(dana, {"t": "answer", "choice": 1})

        reveal = receive_screen(tv, "reveal")
        assert reveal["picks"][1] == ["Sailor 0"]

        bev_reveal = receive_screen(bev, "reveal")
        assert bev_reveal["your_choice"] is None
        assert bev_reveal["correct"] is False

        _send(bev, {"t": "answer", "choice": 1})
        assert json.loads(bev.recv(timeout=2)) == {"t": "refused", "reason": "round_closed"}
