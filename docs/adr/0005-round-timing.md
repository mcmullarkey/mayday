# ADR-0005: Round timing: server deadline, relative countdown on screens

Status: Accepted (2026-10-16)

## Context

Each question runs 20 seconds or until everyone has answered. Phones, the TV and the
server all have their own clocks, which can disagree by seconds. Late answers must not
count, and later slices score answers by speed.

## Options

1. **Each screen runs its own timer from when it got the question.** Simple, but the
   server can't enforce anything and screens drift apart.
2. **Server sends an absolute deadline (wall-clock ms) plus its current time**; clients
   compute their clock offset. Accurate, a little fiddly.
3. **Server sends `remaining_ms` with every question view**; each screen counts down
   from when that view arrived. Network delay (ms on LAN) is the only error, and each
   new view re-syncs the countdown.

## Decision

Option 3, with the server as the only authority on time.

- The pure core never reads a clock. Transitions take `now` (seconds from
  `time.monotonic()`), so tests drive time directly.
- `Trivia.round` is a sum type: `Asking(opened_at, deadline, answers)` or
  `Revealed(answers)`.
- `answer(...)` records `seconds` since the question opened; when the last player locks
  in, it moves straight to `Revealed`.
- `expire(trivia, now)` reveals once `now >= deadline`; it does nothing earlier or when
  already revealed, so a stale timer firing is harmless.
- The server shell schedules one asyncio task per question that sleeps until the
  deadline and calls `expire`.
- Answers after the reveal are refused with `round_closed`.

## Consequences

- Question length is a `create_app(question_seconds=...)` option; tests use 0.5 s.
- Speed scoring (slice 5) reads `Answer.seconds`, which is measured on one clock.
