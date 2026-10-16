import random

from mayday.room_code import ALPHABET, BLOCKED, new_room_code


def test_room_code_is_four_unambiguous_letters() -> None:
    code = new_room_code(random.Random(1))
    assert len(code) == 4
    assert set(code) <= set(ALPHABET)


def test_alphabet_skips_letters_that_read_as_digits() -> None:
    assert not set("IOL") & set(ALPHABET)


def test_same_seed_same_code() -> None:
    assert new_room_code(random.Random(7)) == new_room_code(random.Random(7))


class _Scripted(random.Random):
    """Hands out letters from a fixed script, so the test controls the draw."""

    def __init__(self, letters: str) -> None:
        super().__init__(0)
        self._letters = iter(letters)

    def choice(self, seq):  # type: ignore[override]
        return next(self._letters)


def test_blocked_words_are_redrawn() -> None:
    blocked = sorted(BLOCKED)[0]
    assert new_room_code(_Scripted(blocked + "MXQT")) == "MXQT"
