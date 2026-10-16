# ADR-0004: Game phases as a sum type; question bank as packaged JSON

Status: Accepted (2026-10-16)

## Context

Slice 3 is the first time the game leaves the lobby. The server needs to know which phase
it is in to decide what each intent means (a `join` during a question is refused), and the
trivia game needs questions from somewhere.

## Options

Phases:
1. **One mutable record with a `phase: str` field** plus optional question fields. Easy to
   start, but every field is `Optional` and nothing stops "lobby with a current question".
2. **A sum type: `Game = Lobby | Trivia`.** Each phase is its own frozen dataclass holding
   only what that phase needs. Transitions are pure functions returning a new phase or a
   refusal.

Questions:
1. **JSON file shipped inside the package** (`mayday/questions/*.json`), parsed into
   validated `Question` records at startup.
2. **SQLite / database.** Supports editing in-app, which we don't need.
3. **Python literals in a module.** No parse step, but harder for a non-programmer to edit.

## Decision

`Game = Lobby | Trivia` (option 2), and packaged JSON (option 1).

- `game.join_game` / `game.start_game` dispatch on phase and return the next phase or a
  closed refusal enum (`JoinRefusal.GAME_STARTED`, `StartRefusal.NOT_CAPTAIN`).
- `Question` refuses to exist without exactly 4 choices and a valid answer index.
- A game draws 10 questions at random and shuffles each question's choices, using an
  `rng` passed in, so tests can pin the draw.
- Views never include the answer index while a question is open.

## Consequences

- Adding Mutiny later means adding a phase to the union and new views, not touching trivia.
- Editing questions means editing JSON; a bad file fails at server start, not mid-game.
