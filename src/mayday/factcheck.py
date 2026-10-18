"""Factcheck: confirm each question's quotes really appear in its Wikipedia source (ADR-0011).

`missing_quotes` is the pure comparison (ignores case, line breaks, curly vs straight
quotes and dash styles). `fetch_article_text` is the one network call: Wikipedia's
plain-text extract for an article URL, following redirects.

Does not: decide which questions exist (see questions) or run during a game.
"""

import functools
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

_FOLD = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "–": "-", "—": "-", " ": " "})


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.translate(_FOLD)).strip().casefold()


def missing_quotes(article_text: str, quotes: list[str] | tuple[str, ...]) -> list[str]:
    haystack = _normalize(article_text)
    return [q for q in quotes if _normalize(q) not in haystack]


@functools.cache
def fetch_article_text(url: str) -> str:
    """Cached per URL; waits and retries when Wikipedia rate-limits (HTTP 429)."""
    title = urllib.parse.unquote(url.rsplit("/wiki/", 1)[1])
    query = urllib.parse.urlencode(
        {"action": "query", "prop": "extracts", "explaintext": 1, "format": "json", "redirects": 1, "titles": title}
    )
    request = urllib.request.Request(
        f"https://en.wikipedia.org/w/api.php?{query}",
        headers={"User-Agent": "mayday-trivia-factcheck/0.1 (github.com/mcmullarkey/mayday)"},
    )
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                pages = json.load(response)["query"]["pages"]
            time.sleep(1.0)  # stay well under Wikipedia's rate limit
            return next(iter(pages.values())).get("extract", "")
        except urllib.error.HTTPError as error:
            if error.code != 429:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Wikipedia kept rate-limiting {url}")
