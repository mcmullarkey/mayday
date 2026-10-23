# ADR-0007: End of game, replay, and back to lobby

Status: Accepted (2026-10-16)

## Context

After question 10 the party needs a winner and a way to keep going without restarting
the server: the same crew playing again, or reopening the room for latecomers.

## Options

1. **Final screen as a new top-level phase** (`Game = Lobby | Trivia | Final`). Clean
   separation, but `tick` would have to return a different phase type.
2. **`Over` as the last trivia round** (`Round = Asking | Revealed | Standings | Over`).
   The last reveal's timer ticks into `Over` like any other round; the crew and totals
   are already on `Trivia`.
3. **Restart the server between games.** What we did until now.

Room code on return to lobby:
a. **New code**, per ADR-0003's original "fresh code each game".
b. **Same code.** Players already aboard never retype it; anyone who stepped away can
   rejoin with what's still on the TV.

## Decision

Option 2 with code (b).

- `tick` takes the last question's `Revealed` to `Over` after the reveal pause.
- Captain intents: `{"t": "again"}` starts new trivia with the same crew, fresh
  questions and zeroed scores; `{"t": "lobby"}` returns to a `Lobby` holding the same
  crew and the server's room code, open to new joiners.
- Refusals share one enum, `CaptainRefusal` (renamed from `StartRefusal`):
  `not_captain`, `already_started`, `game_not_over`.
- Final views: the TV gets ranked standings and `winners` (everyone tied for first);
  each phone gets its rank and whether it is Captain (to show the buttons).

## Consequences

- ADR-0003 amended: the code lasts for the life of the server, not one game.
- One server run can host a whole evening.

## Superseded in part by ADR-0012

`{"t": "lobby"}` now keeps only the Captain; everyone else is invited back with one tap.
