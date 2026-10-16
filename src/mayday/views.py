"""Views: what each screen is allowed to see (ADR-0002, ADR-0005).

Pure projections from the game phase to the JSON view sent to one device. The TV gets
the room code, the crew and the question; a phone gets only itself, a head count, and
the buttons it can press. While a question is open no view carries its answer, and the
TV shows who has answered but never what. Countdowns go out as `remaining_ms`.

Does not: send anything, read a clock (callers pass `now`), or change game state.
"""

from typing import Literal, TypedDict

from mayday.game import Game
from mayday.lobby import MAX_PLAYERS, Lobby, Player, PlayerId
from mayday.questions import CHOICES_PER_QUESTION
from mayday.trivia import Asking, Revealed, Trivia


class CrewMember(TypedDict):
    name: str
    captain: bool


class Sailor(TypedDict):
    name: str
    captain: bool
    answered: bool


class HostLobbyView(TypedDict):
    t: Literal["view"]
    screen: Literal["lobby"]
    code: str
    join_url: str
    max_players: int
    players: list[CrewMember]


class PlayerLobbyView(TypedDict):
    t: Literal["view"]
    screen: Literal["lobby"]
    you: CrewMember
    crew_count: int


class HostQuestionView(TypedDict):
    t: Literal["view"]
    screen: Literal["question"]
    number: int
    total: int
    category: str
    prompt: str
    choices: list[str]
    remaining_ms: int
    duration_ms: int
    players: list[Sailor]


class PlayerQuestionView(TypedDict):
    t: Literal["view"]
    screen: Literal["question"]
    number: int
    total: int
    choices: list[str]
    remaining_ms: int
    duration_ms: int
    your_choice: int | None


class HostRevealView(TypedDict):
    t: Literal["view"]
    screen: Literal["reveal"]
    number: int
    total: int
    category: str
    prompt: str
    choices: list[str]
    answer: int
    picks: list[list[str]]
    fact: str


class PlayerRevealView(TypedDict):
    t: Literal["view"]
    screen: Literal["reveal"]
    number: int
    total: int
    choices: list[str]
    answer: int
    your_choice: int | None
    correct: bool


HostView = HostLobbyView | HostQuestionView | HostRevealView
PlayerView = PlayerLobbyView | PlayerQuestionView | PlayerRevealView


def _crew_member(player: Player, captain: Player | None) -> CrewMember:
    return {"name": str(player.name), "captain": player == captain}


def _host_lobby(lobby: Lobby, join_url: str) -> HostLobbyView:
    return {
        "t": "view",
        "screen": "lobby",
        "code": lobby.code,
        "join_url": join_url,
        "max_players": MAX_PLAYERS,
        "players": [_crew_member(p, lobby.captain) for p in lobby.players],
    }


def _player_lobby(lobby: Lobby, player_id: PlayerId) -> PlayerLobbyView:
    me = next(p for p in lobby.players if p.id == player_id)
    return {
        "t": "view",
        "screen": "lobby",
        "you": _crew_member(me, lobby.captain),
        "crew_count": len(lobby.players),
    }


def _remaining_ms(asking: Asking, now: float) -> int:
    return max(0, round((asking.deadline - now) * 1000))


def _duration_ms(asking: Asking) -> int:
    return round((asking.deadline - asking.opened_at) * 1000)


def _host_question(trivia: Trivia, asking: Asking, now: float) -> HostQuestionView:
    question = trivia.current
    return {
        "t": "view",
        "screen": "question",
        "number": trivia.number,
        "total": len(trivia.questions),
        "category": question.category,
        "prompt": question.prompt,
        "choices": list(question.choices),
        "remaining_ms": _remaining_ms(asking, now),
        "duration_ms": _duration_ms(asking),
        "players": [
            {
                "name": str(p.name),
                "captain": p == trivia.captain,
                "answered": trivia.choice_of(p.id) is not None,
            }
            for p in trivia.players
        ],
    }


def _player_question(trivia: Trivia, asking: Asking, player_id: PlayerId, now: float) -> PlayerQuestionView:
    return {
        "t": "view",
        "screen": "question",
        "number": trivia.number,
        "total": len(trivia.questions),
        "choices": list(trivia.current.choices),
        "remaining_ms": _remaining_ms(asking, now),
        "duration_ms": _duration_ms(asking),
        "your_choice": trivia.choice_of(player_id),
    }


def _picks(trivia: Trivia, revealed: Revealed) -> list[list[str]]:
    names = {p.id: str(p.name) for p in trivia.players}
    picks: list[list[str]] = [[] for _ in range(CHOICES_PER_QUESTION)]
    for a in revealed.answers:
        picks[a.choice].append(names[a.player_id])
    return picks


def _host_reveal(trivia: Trivia, revealed: Revealed) -> HostRevealView:
    question = trivia.current
    return {
        "t": "view",
        "screen": "reveal",
        "number": trivia.number,
        "total": len(trivia.questions),
        "category": question.category,
        "prompt": question.prompt,
        "choices": list(question.choices),
        "answer": question.answer,
        "picks": _picks(trivia, revealed),
        "fact": question.fact,
    }


def _player_reveal(trivia: Trivia, player_id: PlayerId) -> PlayerRevealView:
    question = trivia.current
    your_choice = trivia.choice_of(player_id)
    return {
        "t": "view",
        "screen": "reveal",
        "number": trivia.number,
        "total": len(trivia.questions),
        "choices": list(question.choices),
        "answer": question.answer,
        "your_choice": your_choice,
        "correct": your_choice == question.answer,
    }


def host_view(game: Game, join_url: str, now: float) -> HostView:
    match game:
        case Lobby():
            return _host_lobby(game, join_url)
        case Trivia(round=Asking() as asking):
            return _host_question(game, asking, now)
        case Trivia(round=Revealed() as revealed):
            return _host_reveal(game, revealed)


def player_view(game: Game, player_id: PlayerId, now: float) -> PlayerView:
    match game:
        case Lobby():
            return _player_lobby(game, player_id)
        case Trivia(round=Asking() as asking):
            return _player_question(game, asking, player_id, now)
        case Trivia(round=Revealed()):
            return _player_reveal(game, player_id)
