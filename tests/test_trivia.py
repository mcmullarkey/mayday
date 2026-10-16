import pytest

from mayday.lobby import Player, PlayerId, PlayerName
from mayday.questions import parse_questions
from mayday.trivia import Answer, AnswerRefusal, Asking, Revealed, Trivia, answer, expire, open_trivia

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
DANA, BEV = PlayerId("dana"), PlayerId("bev")
PLAYERS = (Player(DANA, PlayerName("Dana")), Player(BEV, PlayerName("Bev")))


def _open(now: float = 100.0) -> Trivia:
    return open_trivia(PLAYERS, (QUESTION,), now=now, seconds=20)


def test_open_trivia_asks_question_one_until_deadline() -> None:
    trivia = _open(now=100.0)
    assert trivia.round == Asking(opened_at=100.0, deadline=120.0, answers=())
    assert trivia.number == 1


def test_answer_is_recorded_with_seconds_since_open() -> None:
    trivia = answer(_open(100.0), DANA, 2, now=103.5)
    assert isinstance(trivia, Trivia)
    assert trivia.round.answers == (Answer(DANA, 2, 3.5),)
    assert trivia.choice_of(DANA) == 2
    assert trivia.choice_of(BEV) is None


def test_last_answer_reveals_immediately() -> None:
    trivia = answer(_open(), DANA, 2, now=101)
    assert isinstance(trivia, Trivia)
    trivia = answer(trivia, BEV, 1, now=102)
    assert isinstance(trivia, Trivia)
    assert isinstance(trivia.round, Revealed)
    assert [a.player_id for a in trivia.round.answers] == [DANA, BEV]


def test_second_answer_is_refused() -> None:
    trivia = answer(_open(), DANA, 2, now=101)
    assert isinstance(trivia, Trivia)
    assert answer(trivia, DANA, 3, now=102) is AnswerRefusal.ALREADY_ANSWERED


@pytest.mark.parametrize("choice", [-1, 4, "1", None, True, 1.0])
def test_choice_must_be_an_index(choice: object) -> None:
    assert answer(_open(), DANA, choice, now=101) is AnswerRefusal.BAD_CHOICE


def test_answer_at_or_after_deadline_is_refused() -> None:
    assert answer(_open(100.0), DANA, 1, now=120.0) is AnswerRefusal.ROUND_CLOSED


def test_answer_after_reveal_is_refused() -> None:
    revealed = expire(_open(100.0), now=120.0)
    assert answer(revealed, DANA, 1, now=121) is AnswerRefusal.ROUND_CLOSED


def test_expire_before_deadline_changes_nothing() -> None:
    trivia = _open(100.0)
    assert expire(trivia, now=119.9) == trivia


def test_expire_at_deadline_reveals_with_answers_so_far() -> None:
    trivia = answer(_open(100.0), DANA, 2, now=101)
    assert isinstance(trivia, Trivia)
    revealed = expire(trivia, now=120.0)
    assert isinstance(revealed.round, Revealed)
    assert revealed.round.answers == (Answer(DANA, 2, 1.0),)


def test_expire_is_idempotent_after_reveal() -> None:
    revealed = expire(_open(100.0), now=120.0)
    assert expire(revealed, now=500.0) == revealed


def test_reveal_scores_each_player_and_adds_to_totals() -> None:
    QUESTION_ANSWER = QUESTION.answer
    trivia = answer(_open(100.0), DANA, QUESTION_ANSWER, now=105)
    assert isinstance(trivia, Trivia)
    trivia = answer(trivia, BEV, (QUESTION_ANSWER + 1) % 4, now=106)
    assert isinstance(trivia, Trivia)
    assert isinstance(trivia.round, Revealed)
    assert trivia.round.gained == {DANA: 875, BEV: 0}
    assert trivia.totals == {DANA: 875, BEV: 0}


def test_timeout_reveal_scores_silent_players_zero() -> None:
    revealed = expire(_open(100.0), now=120.0)
    assert revealed.totals == {DANA: 0, BEV: 0}


def test_fresh_game_totals_start_at_zero() -> None:
    assert _open().totals == {DANA: 0, BEV: 0}
