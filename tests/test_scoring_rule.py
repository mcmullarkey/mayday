import pytest

from mayday.lobby import PlayerId
from mayday.scoring import MAX_POINTS, points_for
from mayday.answer import Answer

P = PlayerId("p")


@pytest.mark.parametrize(
    ("seconds", "points"),
    [(0.0, 1000), (10.0, 750), (20.0, 500), (5.0, 875)],
)
def test_right_answer_scores_500_plus_speed_bonus(seconds: float, points: int) -> None:
    assert points_for(Answer(P, 1, seconds), correct=1, duration=20) == points


def test_wrong_answer_scores_nothing() -> None:
    assert points_for(Answer(P, 2, 0.0), correct=1, duration=20) == 0


def test_no_answer_scores_nothing() -> None:
    assert points_for(None, correct=1, duration=20) == 0


def test_bonus_never_goes_negative_or_over_max() -> None:
    assert points_for(Answer(P, 1, 25.0), correct=1, duration=20) == 500
    assert points_for(Answer(P, 1, -1.0), correct=1, duration=20) == MAX_POINTS


def test_rank_orders_by_score_and_shares_ties() -> None:
    from mayday.scoring import rank

    a, b, c, d = (PlayerId(x) for x in "abcd")
    ranked = rank({a: 500, b: 900, c: 500, d: 0}, order=(a, b, c, d))
    assert ranked == [(1, b, 900), (2, a, 500), (2, c, 500), (4, d, 0)]
