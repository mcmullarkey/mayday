"""Trivia: the sea-disaster quiz once the Captain has cast off (ADR-0004, ADR-0005).

Pure domain core. Holds the crew, the questions drawn for this game, which one is on
screen, and that question's round: still asking (with a deadline) or revealed. Every
transition takes `now` as an argument; nothing here reads a clock.

Does not: decide who may start a game (see game), draw questions (see questions),
schedule timers (see server), or render anything (see views).
"""

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import TypeGuard

from mayday.lobby import Player, PlayerId
from mayday.questions import CHOICES_PER_QUESTION, Question


@dataclass(frozen=True)
class Answer:
    player_id: PlayerId
    choice: int
    seconds: float  # since the question opened


@dataclass(frozen=True)
class Asking:
    opened_at: float
    deadline: float
    answers: tuple[Answer, ...] = ()


@dataclass(frozen=True)
class Revealed:
    answers: tuple[Answer, ...]


Round = Asking | Revealed


class AnswerRefusal(StrEnum):
    ROUND_CLOSED = "round_closed"
    ALREADY_ANSWERED = "already_answered"
    BAD_CHOICE = "bad_choice"


@dataclass(frozen=True)
class Trivia:
    players: tuple[Player, ...]
    questions: tuple[Question, ...]
    round: Round
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

    def choice_of(self, player_id: PlayerId) -> int | None:
        return next((a.choice for a in self.round.answers if a.player_id == player_id), None)


def open_trivia(players: tuple[Player, ...], questions: tuple[Question, ...], now: float, seconds: float) -> Trivia:
    return Trivia(players=players, questions=questions, round=Asking(opened_at=now, deadline=now + seconds))


def _is_choice(choice: object) -> TypeGuard[int]:
    return type(choice) is int and 0 <= choice < CHOICES_PER_QUESTION


def answer(trivia: Trivia, player_id: PlayerId, choice: object, now: float) -> Trivia | AnswerRefusal:
    """A phone's answer, straight off the wire: `choice` is untrusted."""
    asking = trivia.round
    if not isinstance(asking, Asking) or now >= asking.deadline:
        return AnswerRefusal.ROUND_CLOSED
    if not _is_choice(choice):
        return AnswerRefusal.BAD_CHOICE
    if trivia.choice_of(player_id) is not None:
        return AnswerRefusal.ALREADY_ANSWERED
    answers = (*asking.answers, Answer(player_id, choice, now - asking.opened_at))
    everyone_in = len(answers) == len(trivia.players)
    return replace(trivia, round=Revealed(answers) if everyone_in else replace(asking, answers=answers))


def expire(trivia: Trivia, now: float) -> Trivia:
    asking = trivia.round
    if isinstance(asking, Asking) and now >= asking.deadline:
        return replace(trivia, round=Revealed(asking.answers))
    return trivia
