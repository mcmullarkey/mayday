"""Game: which phase the party is in, and the transitions between phases (ADR-0004/7).

Pure domain core. `Game` is the sum of every phase; the functions here take a phase and
a player's request and return the next phase or a closed refusal reason. Starting
(with the rules briefing), skipping the rules, replaying (without them) and returning
to the lobby (a new voyage: only the Captain stays aboard, ADR-0012) are Captain-only.

Does not: hold rules internal to a phase (see lobby, trivia), talk to sockets, or pick
questions or room codes (callers pass them in).
"""

from enum import StrEnum

from mayday.lobby import JoinRefusal, Lobby, Player, PlayerId, join
from mayday.questions import Question
from mayday.room_code import RoomCode
from mayday.trivia import Briefing, Over, Pace, Trivia, open_trivia, skip_briefing

Game = Lobby | Trivia


class CaptainRefusal(StrEnum):
    NOT_CAPTAIN = "not_captain"
    ALREADY_STARTED = "already_started"
    GAME_NOT_OVER = "game_not_over"
    NOTHING_TO_SKIP = "nothing_to_skip"


def join_game(game: Game, code_guess: str, raw_name: str, player_id: PlayerId) -> Lobby | JoinRefusal:
    if isinstance(game, Trivia):
        return JoinRefusal.GAME_STARTED
    return join(game, code_guess, raw_name, player_id)


def _is_captain(captain: Player | None, requester: PlayerId) -> bool:
    return captain is not None and captain.id == requester


def start_game(
    game: Game,
    requester: PlayerId,
    questions: tuple[Question, ...],
    now: float,
    pace: Pace,
) -> Trivia | CaptainRefusal:
    if isinstance(game, Trivia):
        return CaptainRefusal.ALREADY_STARTED
    if not _is_captain(game.captain, requester):
        return CaptainRefusal.NOT_CAPTAIN
    return open_trivia(game.players, questions, now=now, pace=pace, briefing=True)


def skip_rules(game: Game, requester: PlayerId, now: float) -> Trivia | CaptainRefusal:
    if not isinstance(game, Trivia) or not isinstance(game.round, Briefing):
        return CaptainRefusal.NOTHING_TO_SKIP
    if not _is_captain(game.captain, requester):
        return CaptainRefusal.NOT_CAPTAIN
    return skip_briefing(game, now)


def _finished(game: Game, requester: PlayerId) -> Trivia | CaptainRefusal:
    if not isinstance(game, Trivia) or not isinstance(game.round, Over):
        return CaptainRefusal.GAME_NOT_OVER
    if not _is_captain(game.captain, requester):
        return CaptainRefusal.NOT_CAPTAIN
    return game


def play_again(game: Game, requester: PlayerId, questions: tuple[Question, ...], now: float) -> Trivia | CaptainRefusal:
    finished = _finished(game, requester)
    if isinstance(finished, CaptainRefusal):
        return finished
    return open_trivia(finished.players, questions, now=now, pace=finished.pace)


def back_to_lobby(game: Game, requester: PlayerId, code: RoomCode) -> Lobby | CaptainRefusal:
    finished = _finished(game, requester)
    if isinstance(finished, CaptainRefusal):
        return finished
    return Lobby(code=code, players=(finished.players[0],))
