"""Views: what each screen is allowed to see (ADR-0002).

Pure projections from the game phase to the JSON view sent to one device. The TV gets
the room code, the crew and the question; a phone gets only itself, a head count, and
the buttons it can press. No view carries a question's answer while it is open.

Does not: send anything, or change game state.
"""

from typing import Literal, TypedDict

from mayday.game import Game
from mayday.lobby import MAX_PLAYERS, Lobby, Player, PlayerId
from mayday.trivia import Trivia


class CrewMember(TypedDict):
    name: str
    captain: bool


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
    players: list[CrewMember]


class PlayerQuestionView(TypedDict):
    t: Literal["view"]
    screen: Literal["question"]
    number: int
    total: int
    choices: list[str]


def _crew(players: tuple[Player, ...], captain: Player | None) -> list[CrewMember]:
    return [{"name": str(p.name), "captain": p == captain} for p in players]


def _host_lobby(lobby: Lobby, join_url: str) -> HostLobbyView:
    return {
        "t": "view",
        "screen": "lobby",
        "code": lobby.code,
        "join_url": join_url,
        "max_players": MAX_PLAYERS,
        "players": _crew(lobby.players, lobby.captain),
    }


def _host_question(trivia: Trivia) -> HostQuestionView:
    question = trivia.current
    return {
        "t": "view",
        "screen": "question",
        "number": trivia.number,
        "total": len(trivia.questions),
        "category": question.category,
        "prompt": question.prompt,
        "choices": list(question.choices),
        "players": _crew(trivia.players, trivia.captain),
    }


def _player_lobby(lobby: Lobby, player_id: PlayerId) -> PlayerLobbyView:
    me = next(p for p in lobby.players if p.id == player_id)
    return {
        "t": "view",
        "screen": "lobby",
        "you": {"name": str(me.name), "captain": me == lobby.captain},
        "crew_count": len(lobby.players),
    }


def _player_question(trivia: Trivia) -> PlayerQuestionView:
    return {
        "t": "view",
        "screen": "question",
        "number": trivia.number,
        "total": len(trivia.questions),
        "choices": list(trivia.current.choices),
    }


def host_view(game: Game, join_url: str) -> HostLobbyView | HostQuestionView:
    match game:
        case Lobby():
            return _host_lobby(game, join_url)
        case Trivia():
            return _host_question(game)


def player_view(game: Game, player_id: PlayerId) -> PlayerLobbyView | PlayerQuestionView:
    match game:
        case Lobby():
            return _player_lobby(game, player_id)
        case Trivia():
            return _player_question(game)
