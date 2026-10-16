"""Views: what each screen is allowed to see (ADR-0002).

Pure projections from game state to the JSON view sent to one device. The TV gets the
room code and the crew list; a phone gets only itself and a head count.

Does not: send anything, or change game state.
"""

from typing import Literal, TypedDict

from mayday.lobby import Lobby, Player, PlayerId

MAX_PLAYERS = 8


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


def _crew_member(lobby: Lobby, player: Player) -> CrewMember:
    return {"name": player.name, "captain": player == lobby.captain}


def host_view(lobby: Lobby, join_url: str) -> HostLobbyView:
    return {
        "t": "view",
        "screen": "lobby",
        "code": lobby.code,
        "join_url": join_url,
        "max_players": MAX_PLAYERS,
        "players": [_crew_member(lobby, p) for p in lobby.players],
    }


def player_view(lobby: Lobby, player_id: PlayerId) -> PlayerLobbyView:
    me = next(p for p in lobby.players if p.id == player_id)
    return {
        "t": "view",
        "screen": "lobby",
        "you": _crew_member(lobby, me),
        "crew_count": len(lobby.players),
    }
