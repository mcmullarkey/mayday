"""Answer: one sailor's locked-in choice for the open question.

Shared value type between trivia (which records answers) and scoring (which prices them).
Does not: validate choices or know about deadlines (see trivia).
"""

from dataclasses import dataclass

from mayday.lobby import PlayerId


@dataclass(frozen=True)
class Answer:
    player_id: PlayerId
    choice: int
    seconds: float  # since the question opened
