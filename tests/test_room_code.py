import random

from mayday.room_code import ALPHABET, new_room_code


def test_room_code_is_four_unambiguous_letters() -> None:
    code = new_room_code(random.Random(1))
    assert len(code) == 4
    assert set(code) <= set(ALPHABET)


def test_alphabet_skips_letters_that_read_as_digits() -> None:
    assert not set("IOL") & set(ALPHABET)


def test_same_seed_same_code() -> None:
    assert new_room_code(random.Random(7)) == new_room_code(random.Random(7))
