import pytest

from mayday.lobby import MAX_PLAYERS, JoinRefusal, Lobby, Player, PlayerId, PlayerName, join
from mayday.room_code import RoomCode

CODE = RoomCode("MXQT")


def _player(pid: str, name: str) -> Player:
    return Player(id=PlayerId(pid), name=PlayerName.parse(name))


def _joined(*names: str) -> Lobby:
    lobby = Lobby(code=CODE)
    for i, name in enumerate(names):
        result = join(lobby, CODE, name, PlayerId(f"p{i}"))
        assert isinstance(result, Lobby)
        lobby = result
    return lobby


def test_empty_lobby_has_no_captain() -> None:
    assert Lobby(code=CODE).captain is None


def test_join_adds_player_in_arrival_order() -> None:
    assert [str(p.name) for p in _joined("Dana", "Bev").players] == ["Dana", "Bev"]


def test_first_player_aboard_is_captain() -> None:
    assert _joined("Dana", "Bev").captain == _player("p0", "Dana")


def test_join_does_not_mutate_original_lobby() -> None:
    lobby = Lobby(code=CODE)
    join(lobby, CODE, "Dana", PlayerId("p1"))
    assert lobby.players == ()


def test_wrong_code_is_refused() -> None:
    assert join(Lobby(code=CODE), "MXQA", "Dana", PlayerId("p1")) is JoinRefusal.WRONG_CODE


def test_code_guess_ignores_case_and_spaces() -> None:
    assert isinstance(join(Lobby(code=CODE), " mxqt ", "Dana", PlayerId("p1")), Lobby)


def test_name_already_aboard_is_refused_ignoring_case() -> None:
    assert join(_joined("Bev"), CODE, " BEV", PlayerId("p9")) is JoinRefusal.NAME_TAKEN


def test_full_room_is_refused() -> None:
    full = _joined(*(f"S{i}" for i in range(MAX_PLAYERS)))
    assert join(full, CODE, "Stowaway", PlayerId("p9")) is JoinRefusal.ROOM_FULL


@pytest.mark.parametrize("raw", ["", "   ", "Thirteen chrs"])
def test_bad_names_do_not_parse(raw: str) -> None:
    assert PlayerName.parse(raw) is None


def test_bad_name_is_refused() -> None:
    assert join(Lobby(code=CODE), CODE, "   ", PlayerId("p1")) is JoinRefusal.BAD_NAME


def test_name_is_trimmed() -> None:
    assert str(PlayerName.parse("  Bev ")) == "Bev"


def test_name_cannot_be_built_unvalidated() -> None:
    with pytest.raises(ValueError):
        PlayerName("")
