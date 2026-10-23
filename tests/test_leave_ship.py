"""In the lobby anyone can leave the ship; if the Captain leaves (or their phone has been
gone for the grace period) the next sailor in line takes the helm (ADR-0013)."""

import json
import time

from websockets.sync.client import ClientConnection, connect

from conftest import receive_reply, receive_screen, receive_view, running_server


def _send(ws: ClientConnection, intent: dict) -> None:
    ws.send(json.dumps(intent))


def _board(phone: ClientConnection, code: str, name: str) -> str:
    """Join and return the rejoin token."""
    _send(phone, {"t": "join", "code": code, "name": name})
    receive_view(phone)
    return json.loads(phone.recv(timeout=2))["token"]


def _crew(tv: ClientConnection, names: list[str]) -> None:
    while [p["name"] for p in receive_screen(tv, "lobby")["players"]] != names:
        pass


def test_captain_leaves_the_ship_and_the_next_sailor_takes_the_helm() -> None:
    with (
        running_server() as address,
        connect(f"ws://{address}/ws/host") as tv,
        connect(f"ws://{address}/ws/play") as dana,
        connect(f"ws://{address}/ws/play") as bev,
    ):
        code = receive_view(tv)["code"]
        _board(dana, code, "Dana")
        _board(bev, code, "Bev")

        _send(dana, {"t": "leave"})
        assert receive_reply(dana) == {"t": "left"}
        _crew(tv, ["Bev"])
        assert receive_screen(bev, "lobby")["you"] == {"name": "Bev", "captain": True}


def test_captain_whose_phone_stays_gone_is_replaced() -> None:
    with (
        running_server(captain_grace=0.3) as address,
        connect(f"ws://{address}/ws/host") as tv,
        connect(f"ws://{address}/ws/play") as bev,
    ):
        code = receive_view(tv)["code"]
        with connect(f"ws://{address}/ws/play") as dana:
            dana_token = _board(dana, code, "Dana")
        _board(bev, code, "Bev")

        _crew(tv, ["Bev"])
        assert receive_screen(bev, "lobby")["you"] == {"name": "Bev", "captain": True}
        with connect(f"ws://{address}/ws/play") as dana:
            _send(dana, {"t": "rejoin", "token": dana_token})
            assert receive_reply(dana) == {"t": "refused", "reason": "unknown_player"}


def test_captain_who_reconnects_within_the_grace_period_keeps_the_helm() -> None:
    with (
        running_server(captain_grace=0.5) as address,
        connect(f"ws://{address}/ws/host") as tv,
        connect(f"ws://{address}/ws/play") as bev,
    ):
        code = receive_view(tv)["code"]
        with connect(f"ws://{address}/ws/play") as dana:
            dana_token = _board(dana, code, "Dana")
        _board(bev, code, "Bev")
        with connect(f"ws://{address}/ws/play") as dana:
            _send(dana, {"t": "rejoin", "token": dana_token})
            receive_view(dana)
            time.sleep(0.8)  # past the grace period, still connected
            with connect(f"ws://{address}/ws/play") as dana_again:
                _send(dana_again, {"t": "rejoin", "token": dana_token})
                assert receive_view(dana_again)["you"] == {"name": "Dana", "captain": True}


def test_captain_gone_mid_game_hands_the_final_choice_to_the_next_sailor() -> None:
    from test_final_and_replay import BANK

    from mayday.trivia import Pace

    with (
        running_server(bank=BANK, pace=Pace(question=0.6, reveal=0.2, standings=0.2, rules=0.01), captain_grace=0.3) as address,
        connect(f"ws://{address}/ws/host") as tv,
        connect(f"ws://{address}/ws/play") as bev,
    ):
        code = receive_view(tv)["code"]
        with connect(f"ws://{address}/ws/play") as dana:
            _board(dana, code, "Dana")
            _board(bev, code, "Bev")
            _send(dana, {"t": "start"})
            receive_screen(dana, "rules")

        final = receive_screen(bev, "final", timeout=3)
        assert final["captain"] is True
        assert {s["name"] for s in receive_screen(tv, "final")["standings"]} == {"Dana", "Bev"}, "Dana stays in the standings"
        _send(bev, {"t": "lobby"})
        _crew(tv, ["Bev"])
