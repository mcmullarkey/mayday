"""Slice 7: after the last reveal the TV crowns the winner; the Captain can start a fresh
game with the same crew, or head back to the lobby so others can join (see test_new_voyage)."""

import json

from websockets.sync.client import ClientConnection, connect

from conftest import receive_screen, receive_view, running_server
from mayday.questions import parse_questions
from mayday.trivia import Pace

BANK = parse_questions(
    [
        {
            "id": "only",
            "category": "Test",
            "prompt": "The only question?",
            "choices": ["right", "wrong a", "wrong b", "wrong c"],
            "answer": 0,
            "fact": "A fact.",
            "sources": [{"url": "https://example.org", "quotes": ["a quote"]}],
        }
    ]
)
FAST = Pace(question=10, reveal=0.2, standings=0.2, rules=0.01)


def _send(ws: ClientConnection, intent: dict) -> None:
    ws.send(json.dumps(intent))


def _play_only_question(tv: ClientConnection, dana: ClientConnection, bev: ClientConnection) -> dict:
    """Dana right, Bev wrong; returns the TV's final view."""
    question = receive_screen(tv, "question")
    right = question["choices"].index("right")
    _send(dana, {"t": "answer", "choice": right})
    _send(bev, {"t": "answer", "choice": (right + 1) % 4})
    return receive_screen(tv, "final")


def test_winner_is_crowned_and_captain_can_replay_or_return_to_lobby() -> None:
    with (
        running_server(bank=BANK, pace=FAST) as address,
        connect(f"ws://{address}/ws/host") as tv,
        connect(f"ws://{address}/ws/play") as dana,
        connect(f"ws://{address}/ws/play") as bev,
        connect(f"ws://{address}/ws/play") as late,
    ):
        code = receive_view(tv)["code"]
        for phone, name in ((dana, "Dana"), (bev, "Bev")):
            _send(phone, {"t": "join", "code": code, "name": name})
            receive_view(phone)
        _send(dana, {"t": "start"})

        final = _play_only_question(tv, dana, bev)
        assert final["winners"] == ["Dana"]
        assert [(s["rank"], s["name"]) for s in final["standings"]] == [(1, "Dana"), (2, "Bev")]
        dana_final = receive_screen(dana, "final")
        assert (dana_final["rank"], dana_final["captain"]) == (1, True)
        bev_final = receive_screen(bev, "final")
        assert (bev_final["rank"], bev_final["captain"]) == (2, False)

        _send(bev, {"t": "again"})
        assert json.loads(bev.recv(timeout=2)) == {"t": "refused", "reason": "not_captain"}

        _send(dana, {"t": "again"})
        final = _play_only_question(tv, dana, bev)
        assert final["standings"][0]["score"] <= 1000, "scores reset for the new game"

        _send(dana, {"t": "lobby"})
        lobby = receive_screen(tv, "lobby")
        assert lobby["code"] == code
        assert [p["name"] for p in lobby["players"]] == ["Dana"]

        _send(late, {"t": "join", "code": code, "name": "Late Larry"})
        assert receive_view(late)["screen"] == "lobby"
