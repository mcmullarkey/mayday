"""Scoring: how many points one answer earns.

Pure rule: a right answer is worth 500, plus a speed bonus sliding from 500 (instant)
to 0 (at the deadline). Wrong or missing answers earn 0; nobody loses points.

Does not: keep totals or decide when a round is scored (see trivia).
"""

from mayday.answer import Answer

BASE_POINTS = 500
SPEED_POINTS = 500
MAX_POINTS = BASE_POINTS + SPEED_POINTS


def points_for(answer: Answer | None, correct: int, duration: float) -> int:
    if answer is None or answer.choice != correct:
        return 0
    left = min(1.0, max(0.0, 1 - answer.seconds / duration))
    return BASE_POINTS + round(SPEED_POINTS * left)
