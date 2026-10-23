"""Back to lobby starts a new voyage: only the Captain stays aboard, everyone else's phone
offers a one-tap rejoin, so people who left the party drop off and newcomers can join."""

import json

from websockets.sync.client import ClientConnection, connect

from conftest import receive_reply, receive_screen, receive_view, running_server
from test_final_and_replay import BANK, FAST, _play_only_question


def _send(ws: ClientConnection, intent: dict) -> None:
    ws.send(json.dumps(intent))


def test_back_to_lobby_keeps_only_the_captain_and_invites_the_rest_back() -> None:
    with (
        running_server(bank=BANK, pace=FAST) as address,
        connect(f"ws://{address}/ws/host") as tv,
        connect(f"ws://{address}/ws/play") as dana,
        connect(f"ws://{address}/ws/play") as bev,
        connect(f"ws://{address}/ws/play") as cal,
        connect(f"ws://{address}/ws/play") as late,
    ):
        code = receive_view(tv)["code"]
        tokens = {}
        for phone, name in ((dana, "Dana"), (bev, "Bev"), (cal, "Cal")):
            _send(phone, {"t": "join", "code": code, "name": name})
            receive_view(phone)
            tokens[name] = json.loads(phone.recv(timeout=2))["token"]
        _send(dana, {"t": "start"})
        question = receive_screen(tv, "question")
        _send(cal, {"t": "answer", "choice": question["choices"].index("right")})
        _play_only_question(tv, dana, bev)

        _send(dana, {"t": "lobby"})
        lobby = receive_screen(tv, "lobby")
        assert [p["name"] for p in lobby["players"]] == ["Dana"]
        assert receive_screen(dana, "lobby")["you"] == {"name": "Dana", "captain": True}
        assert receive_reply(bev) == {"t": "new_voyage", "name": "Bev", "code": code}
        assert receive_reply(cal) == {"t": "new_voyage", "name": "Cal", "code": code}

        _send(bev, {"t": "join", "code": code, "name": "Bev"})
        assert receive_view(bev)["you"] == {"name": "Bev", "captain": False}
        _send(late, {"t": "join", "code": code, "name": "Late Larry"})
        assert receive_view(late)["screen"] == "lobby"
        assert [p["name"] for p in receive_screen(tv, "lobby")["players"]] == ["Dana", "Bev"]

        _send(cal, {"t": "rejoin", "token": tokens["Cal"]})
        assert receive_reply(cal) == {"t": "refused", "reason": "unknown_player"}
