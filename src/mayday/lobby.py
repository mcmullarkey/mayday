"""Lobby: who is aboard before the game starts.

Pure domain core. Holds the Lobby record and the join transition; the Captain is
whoever came aboard first.

Does not: talk to sockets, generate player ids or room codes (callers pass them in),
or decide what any screen shows (see views).
"""

from dataclasses import dataclass
from typing import NewType

from mayday.room_code import RoomCode

PlayerId = NewType("PlayerId", str)


@dataclass(frozen=True)
class Player:
    id: PlayerId
    name: str


@dataclass(frozen=True)
class Lobby:
    code: RoomCode
    players: tuple[Player, ...] = ()

    @property
    def captain(self) -> Player | None:
        return self.players[0] if self.players else None


def join(lobby: Lobby, player: Player) -> Lobby:
    return Lobby(code=lobby.code, players=(*lobby.players, player))
