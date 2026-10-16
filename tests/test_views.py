from mayday.lobby import Lobby, PlayerId, join
from mayday.room_code import RoomCode
from mayday.views import host_view, player_view

JOIN_URL = "http://192.168.0.10:8000"


def _lobby_with(*names: str) -> Lobby:
    lobby = Lobby(code=RoomCode("MXQT"))
    for i, name in enumerate(names):
        result = join(lobby, lobby.code, name, PlayerId(f"p{i}"))
        assert isinstance(result, Lobby)
        lobby = result
    return lobby


def test_host_lobby_view_shows_code_join_url_and_crew() -> None:
    view = host_view(_lobby_with("Dana", "Bev"), JOIN_URL)
    assert view == {
        "t": "view",
        "screen": "lobby",
        "code": "MXQT",
        "join_url": JOIN_URL,
        "max_players": 8,
        "players": [
            {"name": "Dana", "captain": True},
            {"name": "Bev", "captain": False},
        ],
    }


def test_player_lobby_view_shows_self_and_never_the_room_code() -> None:
    view = player_view(_lobby_with("Dana", "Bev"), PlayerId("p1"))
    assert view == {
        "t": "view",
        "screen": "lobby",
        "you": {"name": "Bev", "captain": False},
        "crew_count": 2,
    }
    assert "code" not in view


def test_player_view_marks_captain() -> None:
    assert player_view(_lobby_with("Dana"), PlayerId("p0"))["you"]["captain"] is True
