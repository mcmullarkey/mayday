# ADR-0012: Back to lobby starts a new voyage

Status: Accepted (2026-10-23)

## Context

ADR-0007 returned the whole crew to the lobby. At a party, people drift off and others
arrive: departed players stayed listed forever (and in every new game's standings),
and with 8 seats a full crew locked newcomers out.

## Options

1. **Keep the crew, add a "Leave" button and a Captain "kick".** Precise, but relies on
   leavers remembering to tap Leave, and gives the Captain a moderation chore.
2. **Drop players whose phone disconnected.** Phones sleep mid-party; a locked screen
   would kick someone who is still playing.
3. **Empty the lobby except the Captain; invite every other phone back with one tap.**
   Whoever is still holding their phone is back in a second; whoever left simply
   doesn't tap.

## Decision

Option 3.

- `back_to_lobby` returns a `Lobby` holding only the Captain (who chose to stay), with
  the same room code.
- The server forgets every other player's phone binding and rejoin token, then sends
  that phone `{"t": "new_voyage", "name": <old name>, "code": <room code>}`.
- The phone shows its join form prefilled with both and a "Climb back aboard" button;
  rejoining is an ordinary `join`, so every join rule (name taken, room full) applies.

## Consequences

- Supersedes the "same crew" part of ADR-0007's `{"t": "lobby"}`; "Play again" still
  keeps the whole crew.
- An old rejoin token after a new voyage gets `unknown_player` (ADR-0009) and the phone
  falls back to the join form.
