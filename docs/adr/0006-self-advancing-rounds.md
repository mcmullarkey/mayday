# ADR-0006: Self-advancing rounds driven by one `tick`

Status: Accepted (2026-10-16)

## Context

After a reveal the game must move on by itself: to the next question, or first to a
standings screen every third question. That adds two more timed transitions on top of
ADR-0005's question deadline. Nobody at a party should have to press "next".

## Options

1. **One asyncio timer per transition type** in the server (deadline timer, reveal timer,
   standings timer). Three code paths that can race each other.
2. **Captain presses "next"** on their phone. Fewer timers, but stalls whenever the Captain
   is in the kitchen.
3. **Every round knows when it wakes; one pure `tick(trivia, now)` performs whatever
   transition is due.** The server runs a single loop: sleep until `trivia.wakes_at`,
   call `tick`, push views.

## Decision

Option 3.

- `Round = Asking | Revealed | Standings`. Each carries the time it ends
  (`deadline` / `until`).
- Durations live in a `Pace(question, reveal, standings)` value held by `Trivia`,
  defaulting to 30 s / 8 s / 5 s (20 s until playtest 1). `create_app(pace=...)` overrides it; tests run fast.
- `tick` replaces ADR-0005's `expire`: Asking → Revealed at the deadline;
  Revealed → Standings (after questions 3, 6, 9) or the next Asking; Standings → next
  Asking. Calling `tick` early, or twice, changes nothing.
- `wakes_at` is `None` when nothing is scheduled (the last reveal, until slice 7 adds the
  final screen), and the server loop stops.

## Consequences

- ADR-0005 stands, except `expire` is now `tick`.
- Adding the final screen (slice 7) is one more branch in `tick`, not another timer.
