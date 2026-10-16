"""Trivia: the sea-disaster quiz once the Captain has cast off.

Pure domain core. Holds the crew, the questions drawn for this game, and which one is
on screen.

Does not: decide who may start a game (see game), draw questions (see questions), or
render anything (see views).
"""

from dataclasses import dataclass

from mayday.lobby import Player
from mayday.questions import Question


@dataclass(frozen=True)
class Trivia:
    players: tuple[Player, ...]
    questions: tuple[Question, ...]
    index: int = 0

    def __post_init__(self) -> None:
        if not self.players or not self.questions:
            raise ValueError("trivia needs at least one player and one question")
        if not 0 <= self.index < len(self.questions):
            raise ValueError(f"question index {self.index} out of range")

    @property
    def current(self) -> Question:
        return self.questions[self.index]

    @property
    def number(self) -> int:
        return self.index + 1

    @property
    def captain(self) -> Player:
        return self.players[0]
