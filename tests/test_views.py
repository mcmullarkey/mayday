from mayday.lobby import Lobby, Player, PlayerId, PlayerName, join
from mayday.questions import parse_questions
from mayday.room_code import RoomCode
from mayday.trivia import Pace, Trivia, answer, open_trivia, tick
from mayday.views import host_view, player_view

JOIN_URL = "http://192.168.0.10:8000"
[QUESTION] = parse_questions(
    [
        {
            "id": "fitz",
            "category": "Great Lakes",
            "prompt": "Which lake?",
            "choices": ["Michigan", "Superior", "Huron", "Erie"],
            "answer": 1,
            "fact": "29 lost.",
            "source": "https://example.org",
        }
    ]
)
CHOICES = ["Michigan", "Superior", "Huron", "Erie"]


def _lobby_with(*names: str) -> Lobby:
    lobby = Lobby(code=RoomCode("MXQT"))
    for i, name in enumerate(names):
        result = join(lobby, lobby.code, name, PlayerId(f"p{i}"))
        assert isinstance(result, Lobby)
        lobby = result
    return lobby


def test_host_lobby_view_shows_code_join_url_and_crew() -> None:
    view = host_view(_lobby_with("Dana", "Bev"), JOIN_URL, now=0)
    assert view == {
        "t": "view",
        "screen": "lobby",
        "code": "MXQT",
        "join_url": JOIN_URL,
        "max_players": 8,
        "players": [
            {"name": "Dana", "captain": True},
            {"name": "Bev", "captain": False},
        ],
    }


def test_player_lobby_view_shows_self_and_never_the_room_code() -> None:
    view = player_view(_lobby_with("Dana", "Bev"), PlayerId("p1"), now=0)
    assert view == {
        "t": "view",
        "screen": "lobby",
        "you": {"name": "Bev", "captain": False},
        "crew_count": 2,
    }
    assert "code" not in view


def test_player_view_marks_captain() -> None:
    assert player_view(_lobby_with("Dana"), PlayerId("p0"), now=0)["you"]["captain"] is True


DANA, BEV = PlayerId("p0"), PlayerId("p1")
PLAYERS = (Player(DANA, PlayerName("Dana")), Player(BEV, PlayerName("Bev")))


def _trivia() -> Trivia:
    """Opened at t=100 with a 20 s timer; Dana has answered Huron at t=104."""
    trivia = answer(open_trivia(PLAYERS, (QUESTION,), now=100, pace=Pace(question=20)), DANA, 2, now=104)
    assert isinstance(trivia, Trivia)
    return trivia


def test_host_question_view_shows_who_answered_but_not_what() -> None:
    assert host_view(_trivia(), JOIN_URL, now=105.25) == {
        "t": "view",
        "screen": "question",
        "number": 1,
        "total": 1,
        "category": "Great Lakes",
        "prompt": "Which lake?",
        "choices": CHOICES,
        "remaining_ms": 14_750,
        "duration_ms": 20_000,
        "players": [
            {"name": "Dana", "captain": True, "answered": True},
            {"name": "Bev", "captain": False, "answered": False},
        ],
    }


def test_player_question_view_shows_question_choices_and_own_lock() -> None:
    assert player_view(_trivia(), DANA, now=105) == {
        "t": "view",
        "screen": "question",
        "number": 1,
        "total": 1,
        "category": "Great Lakes",
        "prompt": "Which lake?",
        "choices": CHOICES,
        "remaining_ms": 15_000,
        "duration_ms": 20_000,
        "your_choice": 2,
    }
    assert player_view(_trivia(), BEV, now=105)["your_choice"] is None


def test_remaining_time_never_goes_negative() -> None:
    assert host_view(_trivia(), JOIN_URL, now=130)["remaining_ms"] == 0


def test_host_reveal_view_shows_answer_and_who_picked_what() -> None:
    assert host_view(tick(_trivia(), now=120), JOIN_URL, now=121) == {
        "t": "view",
        "screen": "reveal",
        "number": 1,
        "total": 1,
        "category": "Great Lakes",
        "prompt": "Which lake?",
        "choices": CHOICES,
        "answer": 1,
        "picks": [[], [], ["Dana"], []],
        "fact": "29 lost.",
        "scores": [
            {"name": "Dana", "gained": 0, "score": 0},
            {"name": "Bev", "gained": 0, "score": 0},
        ],
    }


def test_player_reveal_view_says_whether_you_were_right() -> None:
    revealed = tick(_trivia(), now=120)
    assert player_view(revealed, DANA, now=121) == {
        "t": "view",
        "screen": "reveal",
        "number": 1,
        "total": 1,
        "choices": CHOICES,
        "answer": 1,
        "your_choice": 2,
        "correct": False,
        "gained": 0,
        "score": 0,
    }
    assert player_view(revealed, BEV, now=121)["correct"] is False


def test_reveal_views_carry_points_for_a_right_answer() -> None:
    trivia = answer(open_trivia(PLAYERS, (QUESTION,), now=100, pace=Pace(question=20)), DANA, 1, now=110)
    assert isinstance(trivia, Trivia)
    revealed = tick(trivia, now=120)
    assert host_view(revealed, JOIN_URL, now=121)["scores"][0] == {"name": "Dana", "gained": 750, "score": 750}
    mine = player_view(revealed, DANA, now=121)
    assert (mine["correct"], mine["gained"], mine["score"]) == (True, 750, 750)
    assert mine["total"] == 1



def test_standings_views_rank_the_crew() -> None:
    from dataclasses import replace

    from mayday.trivia import Standings

    trivia = replace(
        open_trivia(PLAYERS, (QUESTION,), now=0, pace=Pace(question=20)),
        round=Standings(until=5),
        totals={DANA: 3000, BEV: 0},
    )
    assert host_view(trivia, JOIN_URL, now=0) == {
        "t": "view",
        "screen": "standings",
        "number": 1,
        "total": 1,
        "standings": [
            {"rank": 1, "name": "Dana", "score": 3000},
            {"rank": 2, "name": "Bev", "score": 0},
        ],
    }
    assert player_view(trivia, BEV, now=0) == {
        "t": "view",
        "screen": "standings",
        "number": 1,
        "total": 1,
        "rank": 2,
        "of": 2,
        "score": 0,
    }


def test_final_views_crown_everyone_tied_for_first() -> None:
    from dataclasses import replace

    from mayday.trivia import Over

    over = replace(
        open_trivia(PLAYERS, (QUESTION,), now=0, pace=Pace(question=20)),
        round=Over(),
        totals={DANA: 2000, BEV: 2000},
    )
    assert host_view(over, JOIN_URL, now=0) == {
        "t": "view",
        "screen": "final",
        "winners": ["Dana", "Bev"],
        "standings": [
            {"rank": 1, "name": "Dana", "score": 2000},
            {"rank": 1, "name": "Bev", "score": 2000},
        ],
    }
    assert player_view(over, BEV, now=0) == {
        "t": "view",
        "screen": "final",
        "rank": 1,
        "of": 2,
        "score": 2000,
        "captain": False,
    }
    assert player_view(over, DANA, now=0)["captain"] is True


def test_rules_views_carry_the_real_numbers() -> None:
    trivia = open_trivia(PLAYERS, (QUESTION,), now=0, pace=Pace(question=30, rules=6), briefing=True)
    assert host_view(trivia, JOIN_URL, now=1.5) == {
        "t": "view",
        "screen": "rules",
        "slide": 1,
        "slides": 3,
        "remaining_ms": 4_500,
        "duration_ms": 6_000,
        "total": 1,
        "question_seconds": 30,
        "base_points": 500,
        "speed_points": 500,
        "standings_every": 3,
    }
    assert player_view(trivia, DANA, now=1.5) == {
        "t": "view",
        "screen": "rules",
        "slide": 1,
        "slides": 3,
        "captain": True,
    }
    assert player_view(trivia, BEV, now=1.5)["captain"] is False
