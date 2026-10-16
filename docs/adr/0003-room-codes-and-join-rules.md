# ADR-0003: Room codes and join rules

Status: Accepted (2026-10-16). Code lifetime amended by ADR-0007.

## Context

Only people in the room should be able to join, and the TV is the only thing everyone
in the room can see. Names show up big on the TV, so they need limits.

## Options

1. **No code; anyone on the network joins.** Simplest on home WiFi, but useless once
   hosted, and two games on one network would collide.
2. **Four-letter code shown only on the TV.** Jackbox's approach. 23^4 ≈ 280k codes.
3. **Long random token in a QR code only.** Unguessable, but nobody can type it, and a
   phone that can't scan is stuck.

## Decision

Option 2, with the QR code (later slice) pre-filling the same four letters.

- Alphabet excludes I, L, O (misread as 1, 1, 0 across a room) and the generator rejects
  a small list of rude words.
- Guesses are case-insensitive.
- Names: trimmed, 1–12 characters, unique per room ignoring case.
- 8 players maximum. The first player aboard is Captain.
- Every rule lives in the pure `lobby` core and returns a closed `JoinRefusal` reason.

## Consequences

- On LAN the code is a sanity check; hosted, it is the lock and will need a rate limit on
  wrong guesses (hosted slice).
- A phone never receives the code in any view: it already typed it.
