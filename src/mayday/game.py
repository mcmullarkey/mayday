"""Game: which phase the party is in, and the transitions between phases (ADR-0004).

Pure domain core. `Game` is the sum of every phase; the functions here take a phase and
a player's request and return the next phase or a closed refusal reason.

Does not: hold rules internal to a phase (see lobby, trivia), talk to sockets, or pick
questions (callers pass them in).
"""

from enum import StrEnum

from mayday.lobby import JoinRefusal, Lobby, PlayerId, join
from mayday.questions import Question
from mayday.trivia import Pace, Trivia, open_trivia

Game = Lobby | Trivia


class StartRefusal(StrEnum):
    NOT_CAPTAIN = "not_captain"
    ALREADY_STARTED = "already_started"


def join_game(game: Game, code_guess: str, raw_name: str, player_id: PlayerId) -> Lobby | JoinRefusal:
    if isinstance(game, Trivia):
        return JoinRefusal.GAME_STARTED
    return join(game, code_guess, raw_name, player_id)


def start_game(
    game: Game,
    requester: PlayerId,
    questions: tuple[Question, ...],
    now: float,
    pace: Pace,
) -> Trivia | StartRefusal:
    if isinstance(game, Trivia):
        return StartRefusal.ALREADY_STARTED
    if game.captain is None or game.captain.id != requester:
        return StartRefusal.NOT_CAPTAIN
    return open_trivia(game.players, questions, now=now, pace=pace)
