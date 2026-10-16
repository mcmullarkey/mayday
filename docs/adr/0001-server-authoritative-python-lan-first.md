# ADR-0001: Authoritative Python server, home network first

Status: Accepted (2026-10-16)

## Context

Mayday is a Jackbox-style game: the laptop drives a TV over HDMI and up to 8 phones act
as controllers. All players are in one room at one party. We need low latency, hidden
information (secret roles in the later Mutiny game), timers, and a join flow that only
people in the room can complete.

## Options

1. **Authoritative server process.** TV and phones are thin browser clients over
   WebSockets. Server holds all state, timing, scoring.
2. **TV browser as host, phones peer-to-peer (WebRTC).** Static site (itch.io-friendly),
   but needs a third-party signaling service and fails on some cellular NATs. Hidden info
   lives in the TV's JavaScript.
3. **Node + TypeScript server** instead of Python. Shared message types with the browser,
   at the cost of a build toolchain and leaving the uv/pytest workflow.

## Decision

Option 1 in Python: Starlette + uvicorn, vanilla JS clients with no build step.
Phase 1 runs on the laptop (`uv run mayday`), phones join over home WiFi. Phase 2 deploys
the same server to a small host for cellular play. itch.io, if used, is a storefront only.

## Consequences

- One process, one event loop, one room at a time. No database: state lives in memory and
  a restart ends the game. Fine for a single party.
- Rules live in a pure core (state in, state out) wrapped by a thin WebSocket shell, so
  game rules are tested without sockets.
- Guest networks with client isolation block phase 1; hosted mode is the fallback.
