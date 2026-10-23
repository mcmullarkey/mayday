# ADR-0013: Leaving the ship and Captain hand-over

Status: Accepted (2026-10-23)

## Context

The Captain (first aboard) is the only one who can start a game, and ADR-0012 keeps
the Captain aboard on every return to the lobby. A Captain who goes home, or whose
phone dies, strands the party in the lobby until the server restarts.

## Options

1. **Explicit "Leave ship" in the lobby.** Anyone can leave; since the Captain is
   whoever is first in line, the next sailor inherits the helm for free.
2. **Drop a Captain whose phone has been gone for a grace period.** Covers leaving
   without tapping anything; risks dropping a Captain whose phone merely slept.
3. **Demote rather than drop.** Keeps a sleeping Captain aboard but leaves a gone one
   listed forever, which ADR-0012 set out to avoid.

## Decision

Options 1 and 2 together.

- Pure core: `leave(lobby, player_id)` removes a sailor; the Captain stays "first in
  line", so hand-over needs no extra state. Leaving is lobby-only (`game_started`).
- Phone intent `{"t": "leave"}` → the phone gets `{"t": "left"}`, its binding and
  rejoin token are forgotten, and it shows the join form.
- When the Captain's last phone disconnects in the lobby, the server waits
  `captain_grace` (60 s by default). If the Captain is still unbound, still Captain,
  and the game is still a lobby, the Captain is dropped. That includes a lone Captain:
  otherwise latecomers would join behind a dead phone. A lone Captain who comes back
  is first in line again anyway.

## Consequences

- A Captain whose phone sleeps for over a minute in the lobby comes back to the join
  form (name remembered) instead of the helm. Accepted: rejoining is two taps.

## Amendment (2026-10-23): mid-game hand-over

A Captain who vanished mid-game used to block "Skip rules", "Play again" and "Back to
lobby". Mid-game the grace period ends in `hand_over_helm` instead of a drop: the
Captain moves to the back of the line (still playing, score and standings intact) and
the next sailor becomes Captain. Removing them would rewrite scores mid-game. If the new
Captain then heads back to the lobby, ADR-0012 drops the old one as usual. A lone
Captain mid-game is left alone: there's nobody to hand over to, and the clock still
carries the game to the final screen.
