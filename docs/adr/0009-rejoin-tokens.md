# ADR-0009: Rejoin tokens

Status: Accepted (2026-10-16)

## Context

Phones drop their socket all the time: screen lock, app switch, reload, WiFi blip.
Until now a dropped phone left its player stranded: still in the game, but with no way
back in (its name was "taken" and joins are refused mid-game).

## Options

1. **Rejoin by name.** Typing the same name reclaims the seat. Anyone can steal anyone's
   seat by typing their name.
2. **Secret token per player, kept on the phone.** The server sends a random token right
   after a successful join; the phone stores it (localStorage) and sends
   `{"t": "rejoin", "token": ...}` whenever it reconnects.

## Decision

Option 2.

- After the join's views, the server sends `{"t": "welcome", "token": "<32 hex>"}`.
- Tokens live in the server shell (`token → PlayerId`), never in views or game state.
- A rejoin attaches the new socket to that player; any older socket for the same player
  is detached so one player is one phone.
- Unknown token (e.g. the server restarted) → `refused: unknown_player`; the phone
  forgets the token and shows the join form.
- Both pages reconnect automatically with backoff when their socket closes (except
  the TV's 4401 host-key refusal).

## Consequences

- A server restart still ends everything (ADR-0001); tokens don't survive it.
- No Captain hand-off yet: if the Captain's phone is gone for good, the game can still
  finish on its timers, but nobody can press "Play again". Restart the server.
