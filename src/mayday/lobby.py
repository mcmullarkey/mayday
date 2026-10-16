"""Lobby: who is aboard before the game starts (ADR-0003).

Pure domain core. Holds validated player names, the Lobby record, and the join
transition with every rule that can refuse it. The Captain is whoever came aboard first.

Does not: talk to sockets, generate player ids or room codes (callers pass them in),
or decide what any screen shows (see views).
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import NewType, Self

from mayday.room_code import RoomCode

PlayerId = NewType("PlayerId", str)

MAX_PLAYERS = 8
MAX_NAME_LENGTH = 12


@dataclass(frozen=True)
class PlayerName:
    """A trimmed name of 1–12 characters. Build one with `parse`."""

    value: str

    def __post_init__(self) -> None:
        if self.value != self.value.strip() or not 1 <= len(self.value) <= MAX_NAME_LENGTH:
            raise ValueError(f"invalid player name: {self.value!r}")

    @classmethod
    def parse(cls, raw: str) -> Self | None:
        trimmed = raw.strip()
        return cls(trimmed) if 1 <= len(trimmed) <= MAX_NAME_LENGTH else None

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Player:
    id: PlayerId
    name: PlayerName


class JoinRefusal(StrEnum):
    WRONG_CODE = "wrong_code"
    NAME_TAKEN = "name_taken"
    BAD_NAME = "bad_name"
    ROOM_FULL = "room_full"
    GAME_STARTED = "game_started"
    TOO_MANY_GUESSES = "too_many_guesses"


@dataclass(frozen=True)
class Lobby:
    code: RoomCode
    players: tuple[Player, ...] = ()

    @property
    def captain(self) -> Player | None:
        return self.players[0] if self.players else None


def join(lobby: Lobby, code_guess: str, raw_name: str, player_id: PlayerId) -> Lobby | JoinRefusal:
    """A phone's join request, straight off the wire: the guess and name are untrusted."""
    if code_guess.strip().upper() != lobby.code:
        return JoinRefusal.WRONG_CODE
    name = PlayerName.parse(raw_name)
    if name is None:
        return JoinRefusal.BAD_NAME
    if len(lobby.players) >= MAX_PLAYERS:
        return JoinRefusal.ROOM_FULL
    if any(p.name.value.casefold() == name.value.casefold() for p in lobby.players):
        return JoinRefusal.NAME_TAKEN
    return Lobby(code=lobby.code, players=(*lobby.players, Player(id=player_id, name=name)))
