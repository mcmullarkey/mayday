import random

from mayday.game import StartRefusal, join_game, start_game
from mayday.lobby import JoinRefusal, Lobby, PlayerId
from mayday.questions import draw_questions, read_question_bank
from mayday.room_code import RoomCode
from mayday.trivia import Trivia

CODE = RoomCode("MXQT")
QUESTIONS = draw_questions(read_question_bank(), random.Random(0), count=10)


def _lobby(*names: str) -> Lobby:
    game = Lobby(code=CODE)
    for i, name in enumerate(names):
        result = join_game(game, CODE, name, PlayerId(f"p{i}"))
        assert isinstance(result, Lobby)
        game = result
    return game


def test_captain_starts_trivia_on_question_one() -> None:
    game = start_game(_lobby("Dana", "Bev"), PlayerId("p0"), QUESTIONS, now=0.0, question_seconds=20)
    assert isinstance(game, Trivia)
    assert game.number == 1
    assert game.current == QUESTIONS[0]
    assert [str(p.name) for p in game.players] == ["Dana", "Bev"]


def test_crew_member_cannot_start() -> None:
    assert start_game(_lobby("Dana", "Bev"), PlayerId("p1"), QUESTIONS, now=0.0, question_seconds=20) is StartRefusal.NOT_CAPTAIN


def test_empty_lobby_cannot_start() -> None:
    assert start_game(_lobby(), PlayerId("p0"), QUESTIONS, now=0.0, question_seconds=20) is StartRefusal.NOT_CAPTAIN


def test_cannot_start_twice() -> None:
    started = start_game(_lobby("Dana"), PlayerId("p0"), QUESTIONS, now=0.0, question_seconds=20)
    assert isinstance(started, Trivia)
    assert start_game(started, PlayerId("p0"), QUESTIONS, now=0.0, question_seconds=20) is StartRefusal.ALREADY_STARTED


def test_join_after_start_is_refused() -> None:
    started = start_game(_lobby("Dana"), PlayerId("p0"), QUESTIONS, now=0.0, question_seconds=20)
    assert isinstance(started, Trivia)
    assert join_game(started, CODE, "Late", PlayerId("p9")) is JoinRefusal.GAME_STARTED
