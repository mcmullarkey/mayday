# ADR-0002: JSON intents in, per-device full views out

Status: Accepted (2026-10-16)

## Context

The TV and each phone must show different things (the TV shows the room code; a phone
shows its own name; later, secret roles). Phones drop connections constantly and must
recover by reconnecting.

## Options

1. **Shared state broadcast.** Every device gets the whole game state and filters it.
   Leaks hidden information to every phone.
2. **Diff/event stream.** Small messages, but a reconnecting client must replay or
   resync, and every client re-implements state transitions.
3. **Per-device full views.** After every change the server computes, for each device,
   the complete screen it should show and pushes that.
4. **htmx WebSocket extension, server pushing HTML fragments.** Same per-device idea, but
   the TV needs real JS for timers and animations anyway.

## Decision

Option 3, as JSON over one WebSocket per device.

- Endpoints: `/ws/host` (TV), `/ws/play` (phones).
- Client → server: intents, e.g. `{"t": "join", "code": "MXQT", "name": "Bev"}`.
- Server → client: `{"t": "view", "screen": "<name>", ...}` carrying everything that
  screen needs. Projection functions (`host_view`, `player_view`) are pure.
- Server → client, when an intent is not allowed: `{"t": "refused", "reason": "<code>"}`.
  Reasons are a closed set owned by the core (join: `wrong_code`, `name_taken`,
  `bad_name`, `room_full`). The phone maps each to its own wording; the state, and so
  every view, is unchanged.

## Consequences

- Clients are renderers: they switch on `screen` and draw. No game rules in JS.
- A reconnecting device is whole again after one message.
- Payloads are a few hundred bytes; with ≤ 9 devices, re-sending full views is free.
- Hidden information is safe by construction: a device can only see what its projection
  includes.
