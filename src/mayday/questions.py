"""Questions: the trivia bank and how a game draws from it (ADR-0004).

Contains the validated Question record (with its Wikipedia sources and quotes, ADR-0011),
parsing from the bank's JSON shape, the random draw for one game (rng passed in), and
the one function that reads the packaged file.

Does not: track which question is on screen or score answers (see trivia).
"""

import json
import random
from dataclasses import dataclass, replace
from importlib.resources import files

CHOICES_PER_QUESTION = 4


@dataclass(frozen=True)
class Source:
    """A page that backs a question up, with verbatim quotes from it (ADR-0011)."""

    url: str
    quotes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.url or not self.quotes or not all(q.strip() for q in self.quotes):
            raise ValueError(f"source {self.url!r} needs a URL and at least one quote")


@dataclass(frozen=True)
class Question:
    id: str
    category: str
    prompt: str
    choices: tuple[str, ...]
    answer: int
    fact: str
    sources: tuple[Source, ...]

    def __post_init__(self) -> None:
        if not self.sources:
            raise ValueError(f"question {self.id!r} needs at least one source")
        if not self.id or not self.prompt:
            raise ValueError(f"question {self.id!r} needs an id and a prompt")
        if len(self.choices) != CHOICES_PER_QUESTION:
            raise ValueError(f"question {self.id!r} needs exactly {CHOICES_PER_QUESTION} choices")
        if not 0 <= self.answer < CHOICES_PER_QUESTION:
            raise ValueError(f"question {self.id!r} has answer index {self.answer} out of range")

    @property
    def correct_choice(self) -> str:
        return self.choices[self.answer]


def parse_questions(raw: list[dict]) -> tuple[Question, ...]:
    questions = tuple(
        Question(
            id=item["id"],
            category=item["category"],
            prompt=item["prompt"],
            choices=tuple(item["choices"]),
            answer=item["answer"],
            fact=item["fact"],
            sources=tuple(Source(url=s["url"], quotes=tuple(s["quotes"])) for s in item["sources"]),
        )
        for item in raw
    )
    ids = [q.id for q in questions]
    if len(ids) != len(set(ids)):
        raise ValueError("question ids must be unique")
    return questions


def _shuffle_choices(question: Question, rng: random.Random) -> Question:
    order = list(range(CHOICES_PER_QUESTION))
    rng.shuffle(order)
    return replace(
        question,
        choices=tuple(question.choices[i] for i in order),
        answer=order.index(question.answer),
    )


def draw_questions(bank: tuple[Question, ...], rng: random.Random, count: int) -> tuple[Question, ...]:
    picked = rng.sample(bank, k=min(count, len(bank)))
    return tuple(_shuffle_choices(q, rng) for q in picked)


def read_question_bank(name: str = "sea_disasters") -> tuple[Question, ...]:
    text = files("mayday").joinpath(f"questions/{name}.json").read_text(encoding="utf-8")
    return parse_questions(json.loads(text))
