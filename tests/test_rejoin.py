"""Slice 8: a phone that drops (screen lock, reload, WiFi blip) comes back as the same
player with the same seat, Captaincy and score, mid-game included."""

import json

from websockets.sync.client import ClientConnection, connect

from conftest import receive_screen, receive_view


def _send(ws: ClientConnection, intent: dict) -> None:
    ws.send(json.dumps(intent))


def _recv(ws: ClientConnection) -> dict:
    return json.loads(ws.recv(timeout=2))


def _join(phone: ClientConnection, code: str, name: str) -> str:
    _send(phone, {"t": "join", "code": code, "name": name})
    while (message := _recv(phone))["t"] != "welcome":
        assert message["t"] == "view"
    return message["token"]


def test_dropped_phone_rejoins_as_the_same_player(server_address: str) -> None:
    with connect(f"ws://{server_address}/ws/host") as tv:
        code = receive_view(tv)["code"]
        with connect(f"ws://{server_address}/ws/play") as dana, connect(f"ws://{server_address}/ws/play") as bev:
            dana_token = _join(dana, code, "Dana")
            _join(bev, code, "Bev")
            dana.close()

            with connect(f"ws://{server_address}/ws/play") as dana_again:
                _send(dana_again, {"t": "rejoin", "token": dana_token})
                assert receive_view(dana_again)["you"] == {"name": "Dana", "captain": True}

                _send(dana_again, {"t": "start"})
                question = receive_screen(tv, "question")
                assert [p["name"] for p in question["players"]] == ["Dana", "Bev"]

            with connect(f"ws://{server_address}/ws/play") as dana_third:
                _send(dana_third, {"t": "rejoin", "token": dana_token})
                assert receive_view(dana_third)["screen"] == "question"
                _send(dana_third, {"t": "answer", "choice": 0})
                assert receive_screen(dana_third, "question")["your_choice"] == 0


def test_unknown_token_is_refused(server_address: str) -> None:
    with connect(f"ws://{server_address}/ws/play") as phone:
        _send(phone, {"t": "rejoin", "token": "not-a-real-token"})
        assert _recv(phone) == {"t": "refused", "reason": "unknown_player"}
