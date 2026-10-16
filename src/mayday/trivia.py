"""Trivia: the sea-disaster quiz once the Captain has cast off (ADR-0004, ADR-0005).

Pure domain core. Holds the crew, the questions drawn for this game, which one is on
screen, and that question's round: still asking (with a deadline) or revealed. Every
transition takes `now` as an argument; nothing here reads a clock.

Does not: decide who may start a game (see game), draw questions (see questions),
schedule timers (see server), or render anything (see views).
"""

from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import TypeGuard

from mayday.answer import Answer
from mayday.lobby import Player, PlayerId
from mayday.questions import CHOICES_PER_QUESTION, Question
from mayday.scoring import points_for


@dataclass(frozen=True)
class Asking:
    opened_at: float
    deadline: float
    answers: tuple[Answer, ...] = ()


@dataclass(frozen=True)
class Revealed:
    answers: tuple[Answer, ...]
    gained: dict[PlayerId, int]  # points each player earned on this question


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
    totals: dict[PlayerId, int] = field(default_factory=dict)

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
    return Trivia(
        players=players,
        questions=questions,
        round=Asking(opened_at=now, deadline=now + seconds),
        totals={p.id: 0 for p in players},
    )


def _reveal(trivia: Trivia, asking: Asking, answers: tuple[Answer, ...]) -> Trivia:
    by_player = {a.player_id: a for a in answers}
    duration = asking.deadline - asking.opened_at
    gained = {
        p.id: points_for(by_player.get(p.id), trivia.current.answer, duration) for p in trivia.players
    }
    totals = {pid: trivia.totals.get(pid, 0) + gained[pid] for pid in gained}
    return replace(trivia, round=Revealed(answers, gained), totals=totals)


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
    if len(answers) == len(trivia.players):
        return _reveal(trivia, asking, answers)
    return replace(trivia, round=replace(asking, answers=answers))


def expire(trivia: Trivia, now: float) -> Trivia:
    asking = trivia.round
    if isinstance(asking, Asking) and now >= asking.deadline:
        return _reveal(trivia, asking, asking.answers)
    return trivia
