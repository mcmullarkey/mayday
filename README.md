# Mayday!

A Jackbox-style party game about disasters at sea. The laptop drives the TV over HDMI;
up to 8 phones join as controllers over the home WiFi.

Games:
1. **Sea Disaster Trivia** (in progress)
2. **Mutiny on the USS Marsh** (later)

## Run it

```sh
uv run mayday
```

Open the printed host URL on the laptop (fullscreen it on the TV). Phones open the
join URL shown on the TV.

Options: `--port 8000`, `--question-seconds 30`.

## Host it online (friends on cellular)

Runs as a free Render web service (see `docs/adr/0008-hosted-mode-on-render.md`).

- Build: `pip install uv && uv sync --frozen --no-dev`
- Start: `uv run mayday --port $PORT --public-url $RENDER_EXTERNAL_URL`
- Env: `MAYDAY_HOST_KEY` (a secret only the TV knows), `PYTHON_VERSION=3.12.7`

Open the TV at `https://<service>.onrender.com/host?key=<MAYDAY_HOST_KEY>` a minute
before people arrive (free services sleep when idle). Phones go to
`https://<service>.onrender.com` and type the code from the TV.

## Develop

```sh
uv run pytest
```

Questions live in `src/mayday/questions/sea_disasters.json`. Each one cites Wikipedia
with exact quotes; re-check them all against live Wikipedia (about 5 minutes):

```sh
MAYDAY_FACTCHECK=1 uv run pytest tests/test_question_bank.py
```

Design decisions live in `docs/adr/`. Build order lives in `docs/plan.md`.
