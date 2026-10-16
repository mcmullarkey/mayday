"""Guesses: lock out an address that keeps getting the room code wrong (ADR-0008).

Pure record of recent wrong-code timestamps per client address. Ten wrong codes within
five minutes locks that address out until the oldest of them ages past the window.

Does not: find out who a client is (the server passes an address) or check codes (see lobby).
"""

from dataclasses import dataclass, field

MAX_WRONG = 10
WINDOW_SECONDS = 300.0


@dataclass(frozen=True)
class GuessLog:
    wrong: dict[str, tuple[float, ...]] = field(default_factory=dict)

    def _recent(self, who: str, now: float) -> tuple[float, ...]:
        return tuple(t for t in self.wrong.get(who, ()) if now - t < WINDOW_SECONDS)

    def locked(self, who: str, now: float) -> bool:
        return len(self._recent(who, now)) >= MAX_WRONG

    def record_wrong(self, who: str, now: float) -> "GuessLog":
        return GuessLog({**self.wrong, who: (*self._recent(who, now), now)})
