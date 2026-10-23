import random
from dataclasses import replace

from mayday.game import CaptainRefusal, back_to_lobby, join_game, leave_game, play_again, skip_rules, start_game
from mayday.lobby import JoinRefusal, Lobby, PlayerId
from mayday.questions import draw_questions, read_question_bank
from mayday.room_code import RoomCode
from mayday.trivia import Asking, Over, Pace, Trivia

CODE = RoomCode("MXQT")
QUESTIONS = draw_questions(read_question_bank(), random.Random(0), count=10)
OTHER_QUESTIONS = draw_questions(read_question_bank(), random.Random(1), count=10)
DANA, BEV = PlayerId("p0"), PlayerId("p1")


def _lobby(*names: str) -> Lobby:
    game = Lobby(code=CODE)
    for i, name in enumerate(names):
        result = join_game(game, CODE, name, PlayerId(f"p{i}"))
        assert isinstance(result, Lobby)
        game = result
    return game


def _started(*names: str) -> Trivia:
    game = start_game(_lobby(*names), DANA, QUESTIONS, now=0.0, pace=Pace())
    assert isinstance(game, Trivia)
    return game


def _over(*names: str) -> Trivia:
    trivia = _started(*names)
    return replace(trivia, index=len(QUESTIONS) - 1, round=Over(), totals={DANA: 4000, BEV: 2500})


def test_captain_starts_trivia_on_question_one() -> None:
    game = _started("Dana", "Bev")
    assert game.number == 1
    assert game.current == QUESTIONS[0]
    assert [str(p.name) for p in game.players] == ["Dana", "Bev"]


def test_crew_member_cannot_start() -> None:
    assert start_game(_lobby("Dana", "Bev"), BEV, QUESTIONS, now=0.0, pace=Pace()) is CaptainRefusal.NOT_CAPTAIN


def test_empty_lobby_cannot_start() -> None:
    assert start_game(_lobby(), DANA, QUESTIONS, now=0.0, pace=Pace()) is CaptainRefusal.NOT_CAPTAIN


def test_cannot_start_twice() -> None:
    assert start_game(_started("Dana"), DANA, QUESTIONS, now=0.0, pace=Pace()) is CaptainRefusal.ALREADY_STARTED


def test_join_after_start_is_refused() -> None:
    assert join_game(_started("Dana"), CODE, "Late", PlayerId("p9")) is JoinRefusal.GAME_STARTED


def test_play_again_keeps_crew_and_pace_but_resets_scores_and_questions() -> None:
    again = play_again(_over("Dana", "Bev"), DANA, OTHER_QUESTIONS, now=50.0)
    assert isinstance(again, Trivia)
    assert [str(p.name) for p in again.players] == ["Dana", "Bev"]
    assert again.questions == OTHER_QUESTIONS
    assert again.number == 1
    assert again.totals == {DANA: 0, BEV: 0}
    assert again.round == Asking(opened_at=50.0, deadline=80.0)


def test_only_captain_can_play_again() -> None:
    assert play_again(_over("Dana", "Bev"), BEV, OTHER_QUESTIONS, now=0) is CaptainRefusal.NOT_CAPTAIN


def test_cannot_play_again_mid_game_or_from_lobby() -> None:
    assert play_again(_started("Dana"), DANA, OTHER_QUESTIONS, now=0) is CaptainRefusal.GAME_NOT_OVER
    assert play_again(_lobby("Dana"), DANA, OTHER_QUESTIONS, now=0) is CaptainRefusal.GAME_NOT_OVER


def test_back_to_lobby_keeps_only_the_captain_and_reopens_room() -> None:
    lobby = back_to_lobby(_over("Dana", "Bev"), DANA, CODE)
    assert isinstance(lobby, Lobby)
    assert lobby.code == CODE
    assert [str(p.name) for p in lobby.players] == ["Dana"]
    assert isinstance(join_game(lobby, CODE, "Late", PlayerId("p9")), Lobby)


def test_back_to_lobby_is_captain_only_and_after_the_game() -> None:
    assert back_to_lobby(_over("Dana", "Bev"), BEV, CODE) is CaptainRefusal.NOT_CAPTAIN
    assert back_to_lobby(_started("Dana"), DANA, CODE) is CaptainRefusal.GAME_NOT_OVER


def test_new_game_opens_with_the_rules_briefing() -> None:
    from mayday.trivia import Briefing

    assert isinstance(_started("Dana").round, Briefing)


def test_captain_skips_the_rules() -> None:
    skipped = skip_rules(_started("Dana", "Bev"), DANA, now=3.0)
    assert isinstance(skipped, Trivia)
    assert isinstance(skipped.round, Asking)


def test_only_captain_skips_and_only_during_rules() -> None:
    assert skip_rules(_started("Dana", "Bev"), BEV, now=3.0) is CaptainRefusal.NOT_CAPTAIN
    asking = skip_rules(_started("Dana"), DANA, now=3.0)
    assert isinstance(asking, Trivia)
    assert skip_rules(asking, DANA, now=4.0) is CaptainRefusal.NOTHING_TO_SKIP
    assert skip_rules(_lobby("Dana"), DANA, now=4.0) is CaptainRefusal.NOTHING_TO_SKIP


def test_leaving_is_for_the_lobby_only() -> None:
    assert [str(p.name) for p in leave_game(_lobby("Dana", "Bev"), DANA).players] == ["Bev"]
    assert leave_game(_started("Dana", "Bev"), DANA) is JoinRefusal.GAME_STARTED


def test_handing_over_the_helm_moves_the_captain_to_the_back_with_score_intact() -> None:
    from mayday.game import hand_over_helm

    game = hand_over_helm(_over("Dana", "Bev"))
    assert [str(p.name) for p in game.players] == ["Bev", "Dana"]
    assert game.captain.id == BEV
    assert game.totals == {DANA: 4000, BEV: 2500}
