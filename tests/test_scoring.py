"""Slice 5: when the round is revealed, right answers score 500 plus up to 500 for
speed, wrong or missing answers score 0, and the TV and phones show the points."""

import json

from websockets.sync.client import ClientConnection, connect

from conftest import receive_screen, receive_view, running_server
from mayday.questions import parse_questions

[FITZ] = parse_questions(
    [
        {
            "id": "fitz",
            "category": "Great Lakes",
            "prompt": "The SS Edmund Fitzgerald went down on which Great Lake?",
            "choices": ["Lake Michigan", "Lake Superior", "Lake Huron", "Lake Erie"],
            "answer": 1,
            "fact": "All 29 crew were lost.",
            "source": "https://en.wikipedia.org/wiki/SS_Edmund_Fitzgerald",
        }
    ]
)


def _send(ws: ClientConnection, intent: dict) -> None:
    ws.send(json.dumps(intent))


def test_reveal_scores_right_answers_by_speed_and_shows_totals() -> None:
    with (
        running_server(bank=(FITZ,)) as address,
        connect(f"ws://{address}/ws/host") as tv,
        connect(f"ws://{address}/ws/play") as dana,
        connect(f"ws://{address}/ws/play") as bev,
    ):
        code = receive_view(tv)["code"]
        for phone, name in ((dana, "Dana"), (bev, "Bev")):
            _send(phone, {"t": "join", "code": code, "name": name})
            receive_view(phone)
        _send(dana, {"t": "start"})
        question = receive_screen(tv, "question")
        right = question["choices"].index("Lake Superior")
        wrong = (right + 1) % 4

        _send(dana, {"t": "answer", "choice": right})
        _send(bev, {"t": "answer", "choice": wrong})

        reveal = receive_screen(tv, "reveal")
        dana_score, bev_score = reveal["scores"]
        assert dana_score["name"] == "Dana"
        assert 950 <= dana_score["gained"] <= 1000
        assert dana_score["total"] == dana_score["gained"]
        assert bev_score == {"name": "Bev", "gained": 0, "total": 0}

        dana_reveal = receive_screen(dana, "reveal")
        assert (dana_reveal["gained"], dana_reveal["total"]) == (dana_score["gained"], dana_score["total"])
        bev_reveal = receive_screen(bev, "reveal")
        assert (bev_reveal["gained"], bev_reveal["total"]) == (0, 0)
