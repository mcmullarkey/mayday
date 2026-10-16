"""Slice 1: when a phone joins with the TV's room code and a name, the TV lobby shows that name."""

import json

from websockets.sync.client import connect

from conftest import receive_view


def test_phone_join_puts_name_on_tv_lobby(server_address: str) -> None:
    with connect(f"ws://{server_address}/ws/host") as tv:
        lobby = receive_view(tv)
        assert lobby["screen"] == "lobby"
        assert lobby["players"] == []

        with connect(f"ws://{server_address}/ws/play") as phone:
            phone.send(json.dumps({"t": "join", "code": lobby["code"], "name": "Barnacle Bev"}))

            tv_lobby = receive_view(tv)
            assert tv_lobby["players"] == [{"name": "Barnacle Bev", "captain": True}]

            phone_lobby = receive_view(phone)
            assert phone_lobby["screen"] == "lobby"
            assert phone_lobby["you"] == {"name": "Barnacle Bev", "captain": True}
