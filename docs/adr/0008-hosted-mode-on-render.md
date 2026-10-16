# ADR-0008: Hosted mode on Render's free plan

Status: Accepted (2026-10-16)

## Context

Friends should be able to join from cellular, not just the home WiFi. That means a
public server. On the public internet, anyone who opens `/host` would see the room code,
and anyone can script guesses at four-letter codes (ADR-0003 deferred this).

## Options

Hosting:
1. **Render free web service** built from the GitHub repo. Native WebSockets, HTTPS,
   free. Spins down after ~15 idle minutes and takes up to a minute to wake.
2. **Fly.io / Railway.** Similar, but they need a card on file or trial credit.
3. **Static host (itch.io) + peer-to-peer.** Rejected in ADR-0001.

Protecting the TV:
a. **Per-visit rooms** (every `/host` visit makes its own room, Jackbox-style). Correct
   for many strangers, but turns one-room state into a room registry.
b. **Host key.** When `MAYDAY_HOST_KEY` is set, `/ws/host` requires `?key=<value>`;
   without it the socket closes with code 4401. Unset on LAN, so party mode is unchanged.

Guessing:
- **Per-address lockout:** 10 wrong codes within 5 minutes from one client address
  refuses every join from it with `too_many_guesses` until the window passes.
  Pure `GuessLog` (time passed in); the server reads the address from the proxy's
  `X-Forwarded-For` via uvicorn's proxy headers.

## Decision

Render free web service (1), host key (b), per-address lockout.

- Build: `pip install uv && uv sync --frozen --no-dev`; start:
  `uv run mayday --port $PORT --public-url $RENDER_EXTERNAL_URL`.
- `--public-url` replaces LAN-address detection for the join URL shown on the TV.
- One instance, in-memory state (ADR-0001): a restart or spin-down ends the game.

## Consequences

- Open the TV at `https://<service>.onrender.com/host?key=<key>`. Phones use the plain
  address and the code on the TV.
- Load the TV page a minute before people arrive so the instance is awake. An open TV
  socket keeps traffic flowing, so it should not spin down mid-game.
- Trusting `X-Forwarded-For` on LAN lets a client fake its address and dodge the lockout;
  acceptable there, where the code is only a sanity check.
