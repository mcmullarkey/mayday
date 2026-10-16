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

## Develop

```sh
uv run pytest
```

Design decisions live in `docs/adr/`. Build order lives in `docs/plan.md`.
