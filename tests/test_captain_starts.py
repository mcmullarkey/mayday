"""Slice 3: when the Captain casts off, question 1 (prompt and choices) appears on the TV and every phone,
and the room is closed to new crew."""

import json
from importlib.resources import files

from websockets.sync.client import ClientConnection, connect

from conftest import receive_reply, receive_view

BANK = json.loads(files("mayday").joinpath("questions/sea_disasters.json").read_text())
PROMPTS = {q["prompt"] for q in BANK}


def _send(ws: ClientConnection, intent: dict) -> None:
    ws.send(json.dumps(intent))


def _recv(ws: ClientConnection) -> dict:
    return receive_reply(ws)


def test_captain_casts_off_and_question_one_appears_everywhere(server_address: str) -> None:
    with (
        connect(f"ws://{server_address}/ws/host") as tv,
        connect(f"ws://{server_address}/ws/play") as dana,
        connect(f"ws://{server_address}/ws/play") as bev,
    ):
        code = receive_view(tv)["code"]
        _send(dana, {"t": "join", "code": code, "name": "Dana"})
        receive_view(dana)
        _send(bev, {"t": "join", "code": code, "name": "Bev"})
        receive_view(bev)
        receive_view(dana)
        receive_view(tv)
        receive_view(tv)

        _send(dana, {"t": "start"})

        question = receive_view(tv)
        assert question["screen"] == "question"
        assert (question["number"], question["total"]) == (1, 10)
        assert question["prompt"] in PROMPTS
        assert len(question["choices"]) == 4
        assert [p["name"] for p in question["players"]] == ["Dana", "Bev"]

        for phone in (dana, bev):
            on_phone = receive_view(phone)
            assert on_phone["screen"] == "question"
            assert (on_phone["number"], on_phone["total"]) == (1, 10)
            assert on_phone["choices"] == question["choices"]
            assert on_phone["prompt"] == question["prompt"]  # playtest 1: read it on your phone too


def test_only_the_captain_casts_off_and_latecomers_are_turned_away(server_address: str) -> None:
    with (
        connect(f"ws://{server_address}/ws/host") as tv,
        connect(f"ws://{server_address}/ws/play") as dana,
        connect(f"ws://{server_address}/ws/play") as bev,
        connect(f"ws://{server_address}/ws/play") as late,
    ):
        code = receive_view(tv)["code"]
        _send(dana, {"t": "join", "code": code, "name": "Dana"})
        receive_view(dana)
        _send(bev, {"t": "join", "code": code, "name": "Bev"})
        receive_view(bev)

        _send(bev, {"t": "start"})
        assert _recv(bev) == {"t": "refused", "reason": "not_captain"}

        _send(dana, {"t": "start"})
        assert receive_view(bev)["screen"] == "question"

        _send(late, {"t": "join", "code": code, "name": "Late Larry"})
        assert _recv(late) == {"t": "refused", "reason": "game_started"}
