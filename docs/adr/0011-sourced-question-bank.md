# ADR-0011: Every question carries checkable Wikipedia quotes

Status: Accepted (2026-10-18)

## Context

Playtest 1 asked for Jackbox-style questions (phrasing that hints at the answer) and
for sea topics beyond shipwrecks. The host also wants every answer and fun fact
traceable, so anyone at the party can double-check. The v1 bank linked a source per
question, but its facts were written from memory: re-checking found six that were
wrong or unsupported (e.g. Halifax: "about 2,000" dead vs. Wikipedia's "at least
1,782").

## Options

1. **URL per question, trust the author.** What v1 did; errors slip in silently.
2. **URL plus exact quotes.** Each question lists one or more sources, each with
   verbatim snippets from that article that support the answer and the fact. A checker
   re-downloads the articles and fails on any quote that is missing.
3. **Generate questions from Wikipedia automatically.** Accurate, but the jokes and the
   hints are the point.

## Decision

Option 2.

- JSON shape: `"sources": [{"url": "https://en.wikipedia.org/wiki/…", "quotes": ["…"]}]`
  replaces `"source"`. `Question` refuses to exist without at least one source with at
  least one quote.
- `mayday.factcheck`: `fetch_article_text(url)` (Wikipedia's plain-text extract API,
  following redirects) and pure `missing_quotes(text, quotes)`, which ignores case and
  collapses whitespace.
- Run it: `MAYDAY_FACTCHECK=1 uv run pytest tests/test_question_bank.py`
  (network, so opt-in).
- Hints in the phrasing are wordplay or common knowledge (Superior "sounds like it's
  bragging"); the answer and fact claims are what the quotes back up.

## Consequences

- Wikipedia edits can break a quote; the checker says which, and the question gets
  re-verified or rewritten.
- Adding a question means pasting its quotes, which is slower but keeps the bank honest.
