import pytest

from mayday.answer import Answer
from mayday.lobby import Player, PlayerId, PlayerName
from mayday.questions import Question, parse_questions
from mayday.trivia import (
    AnswerRefusal,
    Asking,
    Briefing,
    Over,
    Pace,
    Revealed,
    Standings,
    Trivia,
    answer,
    open_trivia,
    skip_briefing,
    tick,
)


def _question(n: int) -> Question:
    [q] = parse_questions(
        [
            {
                "id": f"q{n}",
                "category": "Great Lakes",
                "prompt": f"Which lake {n}?",
                "choices": ["Michigan", "Superior", "Huron", "Erie"],
                "answer": 1,
                "fact": "29 lost.",
                "sources": [{"url": "https://example.org", "quotes": ["a quote"]}],
            }
        ]
    )
    return q


QUESTION = _question(0)
DANA, BEV = PlayerId("dana"), PlayerId("bev")
PLAYERS = (Player(DANA, PlayerName("Dana")), Player(BEV, PlayerName("Bev")))
PACE = Pace(question=20, reveal=8, standings=5)


def _open(now: float = 100.0, questions: tuple[Question, ...] = (QUESTION,)) -> Trivia:
    return open_trivia(PLAYERS, questions, now=now, pace=PACE)


def _answered(trivia: Trivia, player: PlayerId, choice: int, now: float) -> Trivia:
    result = answer(trivia, player, choice, now=now)
    assert isinstance(result, Trivia)
    return result


# Asking


def test_open_trivia_asks_question_one_until_deadline() -> None:
    trivia = _open(now=100.0)
    assert trivia.round == Asking(opened_at=100.0, deadline=120.0, answers=())
    assert trivia.number == 1
    assert trivia.wakes_at == 120.0


def test_answer_is_recorded_with_seconds_since_open() -> None:
    trivia = _answered(_open(100.0), DANA, 2, now=103.5)
    assert trivia.round.answers == (Answer(DANA, 2, 3.5),)
    assert trivia.choice_of(DANA) == 2
    assert trivia.choice_of(BEV) is None


def test_last_answer_reveals_immediately() -> None:
    two = (_question(0), _question(1))
    trivia = _answered(_answered(_open(questions=two), DANA, 2, now=101), BEV, 1, now=102)
    assert isinstance(trivia.round, Revealed)
    assert [a.player_id for a in trivia.round.answers] == [DANA, BEV]
    assert trivia.wakes_at == 102 + PACE.reveal


def test_second_answer_is_refused() -> None:
    trivia = _answered(_open(), DANA, 2, now=101)
    assert answer(trivia, DANA, 3, now=102) is AnswerRefusal.ALREADY_ANSWERED


@pytest.mark.parametrize("choice", [-1, 4, "1", None, True, 1.0])
def test_choice_must_be_an_index(choice: object) -> None:
    assert answer(_open(), DANA, choice, now=101) is AnswerRefusal.BAD_CHOICE


def test_answer_at_or_after_deadline_is_refused() -> None:
    assert answer(_open(100.0), DANA, 1, now=120.0) is AnswerRefusal.ROUND_CLOSED


def test_answer_after_reveal_is_refused() -> None:
    assert answer(tick(_open(100.0), now=120.0), DANA, 1, now=121) is AnswerRefusal.ROUND_CLOSED


# Reveal by deadline


def test_tick_before_deadline_changes_nothing() -> None:
    trivia = _open(100.0)
    assert tick(trivia, now=119.9) == trivia


def test_tick_at_deadline_reveals_with_answers_so_far() -> None:
    revealed = tick(_answered(_open(100.0), DANA, 2, now=101), now=120.0)
    assert isinstance(revealed.round, Revealed)
    assert revealed.round.answers == (Answer(DANA, 2, 1.0),)
    assert revealed.round.until == 128.0


# Scoring


def test_reveal_scores_each_player_and_adds_to_totals() -> None:
    trivia = _answered(_answered(_open(100.0), DANA, 1, now=105), BEV, 0, now=106)
    assert isinstance(trivia.round, Revealed)
    assert trivia.round.gained == {DANA: 875, BEV: 0}
    assert trivia.totals == {DANA: 875, BEV: 0}


def test_timeout_reveal_scores_silent_players_zero() -> None:
    assert tick(_open(100.0), now=120.0).totals == {DANA: 0, BEV: 0}


def test_fresh_game_totals_start_at_zero() -> None:
    assert _open().totals == {DANA: 0, BEV: 0}


# Moving on


def test_reveal_moves_to_next_question_when_its_time_is_up() -> None:
    questions = tuple(_question(n) for n in range(2))
    revealed = tick(_open(100.0, questions), now=120.0)
    assert tick(revealed, now=127.9) == revealed
    nxt = tick(revealed, now=128.0)
    assert nxt.number == 2
    assert nxt.round == Asking(opened_at=128.0, deadline=148.0, answers=())


def test_totals_carry_over_to_the_next_question() -> None:
    questions = tuple(_question(n) for n in range(2))
    trivia = _answered(_answered(_open(100.0, questions), DANA, 1, now=100), BEV, 0, now=100)
    nxt = tick(trivia, now=200.0)
    assert nxt.number == 2
    assert nxt.totals == {DANA: 1000, BEV: 0}


def test_standings_follow_every_third_reveal() -> None:
    questions = tuple(_question(n) for n in range(4))
    trivia = _open(0.0, questions)
    for _ in range(3):
        trivia = tick(tick(trivia, now=trivia.wakes_at), now=trivia.wakes_at + PACE.question)
    # questions 1 and 2 went straight on; question 3's reveal led to standings
    assert trivia.number == 3
    assert isinstance(trivia.round, Standings)
    after = tick(trivia, now=trivia.round.until)
    assert after.number == 4
    assert isinstance(after.round, Asking)


def test_last_reveal_ends_the_game_after_the_pause() -> None:
    revealed = tick(_open(100.0), now=120.0)
    assert revealed.wakes_at == 128.0
    over = tick(revealed, now=128.0)
    assert isinstance(over.round, Over)
    assert over.wakes_at is None
    assert tick(over, now=10_000) == over


def test_last_question_skips_standings_even_on_a_third() -> None:
    questions = tuple(_question(n) for n in range(3))
    trivia = _open(0.0, questions)
    for _ in range(3):
        trivia = tick(tick(trivia, now=trivia.wakes_at), now=trivia.wakes_at + PACE.question)
    assert trivia.number == 3
    assert isinstance(trivia.round, Over)


# Rules briefing (ADR-0010)


def _briefed(now: float = 0.0) -> Trivia:
    return open_trivia(PLAYERS, (QUESTION,), now=now, pace=Pace(question=30, rules=6), briefing=True)


def test_briefing_opens_on_slide_one() -> None:
    trivia = _briefed(0.0)
    assert trivia.round == Briefing(slide=1, until=6.0)
    assert trivia.wakes_at == 6.0
    assert trivia.choice_of(DANA) is None


def test_briefing_steps_through_slides_then_asks_question_one() -> None:
    trivia = _briefed(0.0)
    trivia = tick(trivia, now=6.0)
    assert trivia.round == Briefing(slide=2, until=12.0)
    trivia = tick(tick(trivia, now=12.0), now=18.0)
    assert trivia.round == Asking(opened_at=18.0, deadline=48.0)
    assert trivia.number == 1


def test_no_answers_during_the_briefing() -> None:
    assert answer(_briefed(), DANA, 0, now=1.0) is AnswerRefusal.ROUND_CLOSED


def test_skip_briefing_asks_question_one_now() -> None:
    skipped = skip_briefing(_briefed(0.0), now=2.5)
    assert skipped.round == Asking(opened_at=2.5, deadline=32.5)


def test_skip_outside_briefing_changes_nothing() -> None:
    asking = _open(100.0)
    assert skip_briefing(asking, now=101) == asking
