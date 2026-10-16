"""Scoring: how many points one answer earns, and who is ahead.

Pure rules. A right answer is worth 500, plus a speed bonus sliding from 500 (instant)
to 0 (at the deadline). Wrong or missing answers earn 0; nobody loses points. Ranking
shares places on ties (500, 500, 0 ranks 1, 1, 3).

Does not: keep totals or decide when a round is scored (see trivia).
"""

from mayday.answer import Answer
from mayday.lobby import PlayerId

BASE_POINTS = 500
SPEED_POINTS = 500
MAX_POINTS = BASE_POINTS + SPEED_POINTS


def points_for(answer: Answer | None, correct: int, duration: float) -> int:
    if answer is None or answer.choice != correct:
        return 0
    left = min(1.0, max(0.0, 1 - answer.seconds / duration))
    return BASE_POINTS + round(SPEED_POINTS * left)


def rank(totals: dict[PlayerId, int], order: tuple[PlayerId, ...]) -> list[tuple[int, PlayerId, int]]:
    """(place, player, score), best first; ties keep `order` (join order) and share a place."""
    ordered = sorted(order, key=lambda pid: -totals[pid])
    return [(1 + sum(totals[o] > totals[pid] for o in order), pid, totals[pid]) for pid in ordered]
