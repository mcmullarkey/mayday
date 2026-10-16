"""Trivia: the sea-disaster quiz once the Captain has cast off (ADR-0004/5/6).

Pure domain core. Holds the crew, the questions drawn for this game, which one is on
screen, running totals, and the current round: asking (until a deadline), revealed
(for a few seconds), standings (every third question), or over (after the last
question, ADR-0007). `tick` performs whichever
timed transition is due; nothing here reads a clock, callers pass `now`.

Does not: decide who may start a game (see game), draw questions (see questions),
price answers (see scoring), schedule timers (see server), or render (see views).
"""

from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import TypeGuard

from mayday.answer import Answer
from mayday.lobby import Player, PlayerId
from mayday.questions import CHOICES_PER_QUESTION, Question
from mayday.scoring import points_for

STANDINGS_EVERY = 3


@dataclass(frozen=True)
class Pace:
    """Seconds each round lasts."""

    question: float = 20.0
    reveal: float = 8.0
    standings: float = 5.0


@dataclass(frozen=True)
class Asking:
    opened_at: float
    deadline: float
    answers: tuple[Answer, ...] = ()


@dataclass(frozen=True)
class Revealed:
    answers: tuple[Answer, ...]
    gained: dict[PlayerId, int]  # points each player earned on this question
    until: float


@dataclass(frozen=True)
class Standings:
    until: float


@dataclass(frozen=True)
class Over:
    """The last question has been revealed; the Captain decides what happens next."""


Round = Asking | Revealed | Standings | Over


class AnswerRefusal(StrEnum):
    ROUND_CLOSED = "round_closed"
    ALREADY_ANSWERED = "already_answered"
    BAD_CHOICE = "bad_choice"


@dataclass(frozen=True)
class Trivia:
    players: tuple[Player, ...]
    questions: tuple[Question, ...]
    round: Round
    pace: Pace
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
    def is_last_question(self) -> bool:
        return self.number == len(self.questions)

    @property
    def captain(self) -> Player:
        return self.players[0]

    @property
    def wakes_at(self) -> float | None:
        """When `tick` next has something to do; None if nothing is scheduled."""
        match self.round:
            case Asking(deadline=deadline):
                return deadline
            case Revealed(until=until) | Standings(until=until):
                return until
            case Over():
                return None

    def choice_of(self, player_id: PlayerId) -> int | None:
        answers = self.round.answers if isinstance(self.round, Asking | Revealed) else ()
        return next((a.choice for a in answers if a.player_id == player_id), None)


def _asking(now: float, pace: Pace) -> Asking:
    return Asking(opened_at=now, deadline=now + pace.question)


def open_trivia(players: tuple[Player, ...], questions: tuple[Question, ...], now: float, pace: Pace) -> Trivia:
    return Trivia(
        players=players,
        questions=questions,
        round=_asking(now, pace),
        pace=pace,
        totals={p.id: 0 for p in players},
    )


def _reveal(trivia: Trivia, asking: Asking, answers: tuple[Answer, ...], now: float) -> Trivia:
    by_player = {a.player_id: a for a in answers}
    duration = asking.deadline - asking.opened_at
    gained = {p.id: points_for(by_player.get(p.id), trivia.current.answer, duration) for p in trivia.players}
    totals = {pid: trivia.totals.get(pid, 0) + gained[pid] for pid in gained}
    return replace(trivia, round=Revealed(answers, gained, until=now + trivia.pace.reveal), totals=totals)


def _next_question(trivia: Trivia, now: float) -> Trivia:
    return replace(trivia, index=trivia.index + 1, round=_asking(now, trivia.pace))


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
        return _reveal(trivia, asking, answers, now)
    return replace(trivia, round=replace(asking, answers=answers))


def tick(trivia: Trivia, now: float) -> Trivia:
    """Perform the timed transition that is due at `now`, if any (ADR-0006)."""
    wakes_at = trivia.wakes_at
    if wakes_at is None or now < wakes_at:
        return trivia
    match trivia.round:
        case Asking() as asking:
            return _reveal(trivia, asking, asking.answers, now)
        case Revealed() if trivia.is_last_question:
            return replace(trivia, round=Over())
        case Revealed() if trivia.number % STANDINGS_EVERY == 0:
            return replace(trivia, round=Standings(until=now + trivia.pace.standings))
        case Revealed() | Standings():
            return _next_question(trivia, now)
        case Over():
            return trivia
