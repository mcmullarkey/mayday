# Build plan

Status 2026-10-18: slices 1–10 built, plus playtest 1 changes (30 s timer, rules briefing, questions on phones; ADR-0010). Live at https://mayday-qsu4.onrender.com (TV: /host?key=...).

Design proposal: https://claude.ai/artifact/AxsNQiLCisbMNpGGNYhScr

Decisions settled (2026-10-16): Python + Starlette, home network first, night-sea look,
working title "Mayday!".

Each slice = one "when I do X, I see Y" integration test against a real server and real
WebSockets, then a rodney browser check.

1. A phone joins and its name appears on the TV lobby.
2. A wrong room code or bad name is refused with a reason the phone can show.
3. The Captain starts and a question appears on the TV and every phone.
4. Answers lock in and the timer cuts the round off.
5. The reveal shows who was right and the scores move.
6. After the reveal the game moves on: next question, with standings every third.
7. A full 10-question game ends with a winner and replay.
8. A phone that drops comes back as the same player.
9. The TV shows a QR code that opens the join page with the code filled in.
10. Friends join from cellular (hosted deploy).
