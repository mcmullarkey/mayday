"""Slice 6: after each reveal the game moves on by itself to the next question, and
after every third question the TV shows the standings first."""

import json

from websockets.sync.client import ClientConnection, connect

from conftest import receive_screen, receive_view, running_server
from mayday.questions import parse_questions
from mayday.trivia import Pace

BANK = parse_questions(
    [
        {
            "id": f"q{n}",
            "category": "Test",
            "prompt": f"Question number {n}?",
            "choices": [f"right {n}", f"wrong {n}a", f"wrong {n}b", f"wrong {n}c"],
            "answer": 0,
            "fact": "A fact.",
            "source": "https://example.org",
        }
        for n in range(4)
    ]
)
RIGHT = {q.prompt: q.correct_choice for q in BANK}
FAST = Pace(question=10, reveal=0.3, standings=0.3, rules=0.01)


def _send(ws: ClientConnection, intent: dict) -> None:
    ws.send(json.dumps(intent))


def _question(ws: ClientConnection, number: int) -> dict:
    """Skip views left over from earlier questions until question `number` opens."""
    while (view := receive_screen(ws, "question"))["number"] != number:
        pass
    return view


def _play_question(tv: ClientConnection, dana: ClientConnection, bev: ClientConnection, number: int) -> None:
    """Dana answers right, Bev answers wrong."""
    question = _question(tv, number)
    right = question["choices"].index(RIGHT[question["prompt"]])
    for phone in (dana, bev):
        _question(phone, number)
    _send(dana, {"t": "answer", "choice": right})
    _send(bev, {"t": "answer", "choice": (right + 1) % 4})
    assert receive_screen(tv, "reveal")["number"] == number


def test_game_moves_on_and_shows_standings_every_third_question() -> None:
    with (
        running_server(bank=BANK, pace=FAST) as address,
        connect(f"ws://{address}/ws/host") as tv,
        connect(f"ws://{address}/ws/play") as dana,
        connect(f"ws://{address}/ws/play") as bev,
    ):
        code = receive_view(tv)["code"]
        for phone, name in ((dana, "Dana"), (bev, "Bev")):
            _send(phone, {"t": "join", "code": code, "name": name})
            receive_view(phone)
        _send(dana, {"t": "start"})

        for number in (1, 2, 3):
            _play_question(tv, dana, bev, number)

        standings = receive_view(tv)
        assert standings["screen"] == "standings"
        assert [(s["rank"], s["name"]) for s in standings["standings"]] == [(1, "Dana"), (2, "Bev")]
        assert standings["standings"][1]["score"] == 0
        assert standings["standings"][0]["score"] > 1500

        bev_standing = receive_screen(bev, "standings")
        assert (bev_standing["rank"], bev_standing["of"], bev_standing["score"]) == (2, 2, 0)

        assert receive_view(tv)["number"] == 4
