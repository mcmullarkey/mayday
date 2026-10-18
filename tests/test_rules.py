"""Playtest 1: when the Captain casts off, the TV walks the crew through the rules
(30 s clock, speed scoring) before question 1; the Captain can skip, and Play again
goes straight to questions."""

import json

from websockets.sync.client import ClientConnection, connect

from conftest import receive_reply, receive_screen, receive_view, running_server
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
            "source": "https://example.org",
        }
    ]
)


def _send(ws: ClientConnection, intent: dict) -> None:
    ws.send(json.dumps(intent))


def _board(address: str, tv: ClientConnection, dana: ClientConnection, bev: ClientConnection) -> None:
    code = receive_view(tv)["code"]
    for phone, name in ((dana, "Dana"), (bev, "Bev")):
        _send(phone, {"t": "join", "code": code, "name": name})
        receive_view(phone)
    _send(dana, {"t": "start"})


def test_rules_play_before_question_one() -> None:
    pace = Pace(question=30, reveal=0.2, standings=0.2, rules=0.3)
    with (
        running_server(bank=BANK, pace=pace) as address,
        connect(f"ws://{address}/ws/host") as tv,
        connect(f"ws://{address}/ws/play") as dana,
        connect(f"ws://{address}/ws/play") as bev,
    ):
        _board(address, tv, dana, bev)

        slides = [receive_screen(tv, "rules") for _ in range(3)]
        assert [(s["slide"], s["slides"]) for s in slides] == [(1, 3), (2, 3), (3, 3)]
        assert slides[0]["question_seconds"] == 30
        assert (slides[0]["base_points"], slides[0]["speed_points"]) == (500, 500)

        bev_rules = receive_screen(bev, "rules")
        assert bev_rules["captain"] is False
        assert receive_screen(dana, "rules")["captain"] is True

        question = receive_screen(tv, "question", timeout=3)
        assert question["number"] == 1


def test_captain_skips_rules_and_replay_skips_them() -> None:
    pace = Pace(question=30, reveal=0.2, standings=0.2, rules=30)
    with (
        running_server(bank=BANK, pace=pace) as address,
        connect(f"ws://{address}/ws/host") as tv,
        connect(f"ws://{address}/ws/play") as dana,
        connect(f"ws://{address}/ws/play") as bev,
    ):
        _board(address, tv, dana, bev)
        assert receive_screen(tv, "rules")["slide"] == 1

        _send(bev, {"t": "skip"})
        assert receive_reply(bev) == {"t": "refused", "reason": "not_captain"}

        _send(dana, {"t": "skip"})
        question = receive_screen(tv, "question")
        right = question["choices"].index("right")
        for phone in (dana, bev):
            _send(phone, {"t": "answer", "choice": right})
        receive_screen(tv, "final")

        _send(dana, {"t": "again"})
        assert receive_view(tv)["screen"] == "question"
