import random

import pytest

from mayday.questions import Question, draw_questions, parse_questions, read_question_bank

RAW = {
    "id": "fitz",
    "category": "Great Lakes",
    "prompt": "Which lake?",
    "choices": ["Michigan", "Superior", "Huron", "Erie"],
    "answer": 1,
    "fact": "29 lost.",
    "sources": [{"url": "https://example.org", "quotes": ["a quote"]}],
}


def test_parse_builds_questions() -> None:
    [q] = parse_questions([RAW])
    assert q.correct_choice == "Superior"
    assert q.category == "Great Lakes"


@pytest.mark.parametrize(
    "bad",
    [
        {**RAW, "choices": ["a", "b", "c"]},
        {**RAW, "answer": 4},
        {**RAW, "answer": -1},
        {**RAW, "prompt": ""},
    ],
)
def test_question_refuses_invalid_shape(bad: dict) -> None:
    with pytest.raises(ValueError):
        parse_questions([bad])


def test_duplicate_ids_are_refused() -> None:
    with pytest.raises(ValueError):
        parse_questions([RAW, RAW])


def _bank(n: int) -> tuple[Question, ...]:
    return parse_questions([{**RAW, "id": f"q{i}", "prompt": f"Q{i}?"} for i in range(n)])


def test_draw_takes_distinct_questions() -> None:
    drawn = draw_questions(_bank(30), random.Random(1), count=10)
    assert len(drawn) == 10
    assert len({q.id for q in drawn}) == 10


def test_draw_shuffles_choices_but_keeps_answer_right() -> None:
    drawn = draw_questions(_bank(30), random.Random(3), count=10)
    assert all(q.correct_choice == "Superior" for q in drawn)
    assert {q.answer for q in drawn} != {1}


def test_draw_never_asks_for_more_than_the_bank_has() -> None:
    assert len(draw_questions(_bank(3), random.Random(1), count=10)) == 3


def test_packaged_bank_loads() -> None:
    assert len(read_question_bank()) >= 10


def test_question_needs_a_source_with_a_quote() -> None:
    with pytest.raises(ValueError):
        parse_questions([{**RAW, "sources": []}])
    with pytest.raises(ValueError):
        parse_questions([{**RAW, "sources": [{"url": "https://en.wikipedia.org/wiki/X", "quotes": []}]}])


def test_sources_parse_into_url_and_quotes() -> None:
    [q] = parse_questions([RAW])
    assert q.sources[0].url == "https://example.org"
    assert q.sources[0].quotes == ("a quote",)
