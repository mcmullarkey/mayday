from mayday.lobby import Lobby, Player, PlayerId, join
from mayday.room_code import RoomCode


def _player(pid: str, name: str) -> Player:
    return Player(id=PlayerId(pid), name=name)


def test_empty_lobby_has_no_captain() -> None:
    assert Lobby(code=RoomCode("MXQT")).captain is None


def test_join_adds_player_in_arrival_order() -> None:
    lobby = Lobby(code=RoomCode("MXQT"))
    lobby = join(lobby, _player("p1", "Dana"))
    lobby = join(lobby, _player("p2", "Bev"))
    assert [p.name for p in lobby.players] == ["Dana", "Bev"]


def test_first_player_aboard_is_captain() -> None:
    lobby = join(join(Lobby(code=RoomCode("MXQT")), _player("p1", "Dana")), _player("p2", "Bev"))
    assert lobby.captain == _player("p1", "Dana")


def test_join_does_not_mutate_original_lobby() -> None:
    lobby = Lobby(code=RoomCode("MXQT"))
    join(lobby, _player("p1", "Dana"))
    assert lobby.players == ()
