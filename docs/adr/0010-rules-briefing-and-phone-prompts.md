# ADR-0010: Rules briefing, and the question on phones (playtest 1)

Status: Accepted (2026-10-18)

## Context

First playtest: the host explained the rules out loud every game, and players wanted to
read questions in their hand (the biggest difference from Jackbox they noticed, along
with time pressure). They also asked for 30 s instead of 20 s per question.

## Options

Rules:
1. **Static rules page** on the TV lobby. Easy to ignore; nobody reads it while joining.
2. **A timed briefing round** before question 1: three slides advance on the server
   clock (ADR-0006), with Skip on the Captain's phone.
3. **Rules text on each phone.** Splits attention, and the room should hear it together.

Question on phones:
a. Keep the prompt TV-only (ADR-0002's original split).
b. Send the prompt and category in the phone's question view too.

## Decision

Option 2 and option (b).

- `Round` gains `Briefing(slide, until)`; `Pace.rules` (6 s) is per slide; 3 slides.
  `tick` moves slide 1 → 2 → 3 → question 1. `start_game` begins with the briefing;
  `play_again` skips it (the crew already knows).
- `{"t": "skip"}` from the Captain jumps to question 1 (`CaptainRefusal.NOTHING_TO_SKIP`
  otherwise).
- The rules view carries the real numbers (`question_seconds`, `base_points`,
  `speed_points`, `standings_every`) so the slides can't drift from the rules.
- Default `Pace.question` is now 30 s.
- Still never sent while a question is open: the answer index.

## Consequences

- ADR-0002's "phones see only the buttons" no longer holds for questions; hidden
  information (Mutiny roles) is unaffected.
- A game now takes about 18 s longer to start, or 0 s if the Captain skips.
