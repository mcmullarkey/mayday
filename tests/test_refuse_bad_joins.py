"""Slice 2: a wrong room code, a taken or bad name, or a full room is refused with a
reason the phone can show, and the TV crew manifest does not change."""

import json
from contextlib import ExitStack

import pytest
from websockets.sync.client import ClientConnection, connect

from conftest import receive_view


def _join(phone: ClientConnection, code: str, name: str) -> dict:
    phone.send(json.dumps({"t": "join", "code": code, "name": name}))
    return json.loads(phone.recv(timeout=2))


@pytest.fixture
def tv(server_address: str):
    with connect(f"ws://{server_address}/ws/host") as tv:
        yield tv


def test_wrong_code_and_taken_name_are_refused(server_address: str, tv: ClientConnection) -> None:
    code = receive_view(tv)["code"]
    wrong = "".join("A" if c != "A" else "B" for c in code)

    with connect(f"ws://{server_address}/ws/play") as bev, connect(f"ws://{server_address}/ws/play") as copycat:
        assert _join(bev, wrong, "Bev") == {"t": "refused", "reason": "wrong_code"}
        assert _join(bev, code.lower(), "Bev")["t"] == "view"
        assert _join(copycat, code, "  bev ") == {"t": "refused", "reason": "name_taken"}
        assert _join(copycat, code, "") == {"t": "refused", "reason": "bad_name"}
        assert _join(copycat, code, "Thirteen chrs") == {"t": "refused", "reason": "bad_name"}

        assert [p["name"] for p in receive_view(tv)["players"]] == ["Bev"]


def test_ninth_sailor_is_refused(server_address: str, tv: ClientConnection) -> None:
    code = receive_view(tv)["code"]
    with ExitStack() as stack:
        phones = [stack.enter_context(connect(f"ws://{server_address}/ws/play")) for _ in range(9)]
        for i, phone in enumerate(phones[:8]):
            assert _join(phone, code, f"Sailor {i}")["t"] == "view"
        assert _join(phones[8], code, "Stowaway") == {"t": "refused", "reason": "room_full"}
