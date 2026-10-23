"""Playtest 1, question bank v2: every question is sourced to Wikipedia with exact quotes
anyone can check, and the bank goes beyond shipwrecks (legends, diving, strange waters).

The live check re-downloads every source and confirms each quote is really there:

    MAYDAY_FACTCHECK=1 uv run pytest tests/test_question_bank.py
"""

import os
from collections import Counter

import pytest

from mayday.factcheck import fetch_article_text, missing_quotes
from mayday.questions import read_question_bank

BANK = read_question_bank()
BEYOND_SHIPWRECKS = {"Legends & Monsters", "Into the Deep", "Strange Waters"}


def test_every_question_cites_wikipedia_with_quotes() -> None:
    for q in BANK:
        assert q.sources, q.id
        for source in q.sources:
            assert source.url.startswith("https://en.wikipedia.org/wiki/"), q.id
            assert source.quotes and all(quote.strip() for quote in source.quotes), q.id


def test_bank_goes_beyond_shipwrecks() -> None:
    counts = Counter(q.category for q in BANK)
    assert all(counts[c] >= 4 for c in BEYOND_SHIPWRECKS), counts
    assert len(BANK) >= 110  # doubled after playtest 1 (v3)


@pytest.mark.skipif(not os.environ.get("MAYDAY_FACTCHECK"), reason="set MAYDAY_FACTCHECK=1 to re-check sources online")
def test_every_quote_appears_in_its_source() -> None:
    problems = []
    for q in BANK:
        for source in q.sources:
            for quote in missing_quotes(fetch_article_text(source.url), source.quotes):
                problems.append(f"{q.id}: {source.url} lacks {quote!r}")
    assert not problems, "\n".join(problems)
