# Share (repo: ShareWeb)

Privately hosted artifact host at `share.c52.com`. AI agents post finished files over an API
and get a stable URL. The owner keeps them and hands them out with expiring links.

## Sources of truth

- `BACKLOG.md` — deferred work. Read every session.
- `docs/specs/spec/START-HERE.md` — product brief. Then `01-overview.md`, `USE-CASES.md`, `16-roadmap.md`.
- `docs/specs/spec/DECISIONS.md` — resolutions, including local fills D-19–D-24.
- Spec owns behaviour. Design (`Foundations.dc.html`, `Screens.dc.html`, `recipient/`) owns appearance.

## Project Structure

```
ShareWeb/
├── AGENTS.md
├── server/           # FastAPI app
├── sharectl/         # operator CLI
├── tests/
├── docs/specs/spec/  # behaviour spec
└── var/share/        # local file store (not committed)
```

## Commands

```bash
pyenv virtualenv 3.13.12 share-3.13
pyenv local share-3.13
pip install -e ".[dev]"

# first time
cp examples/.env.example .env
cp examples/.keys.example .keys && chmod 600 .keys
# fill SHARE_SECRET_KEY and SHARE_VIEW_SALT
sharectl bootstrap --email you@c52.com --handle robert

uvicorn server.main:app --reload --port 8000
pytest tests/ -v
ruff check .
```

## Conventions

- Config: `.env` (non-sensitive) + `.keys` (secrets). Prefix `SHARE_`.
- Python: pyenv + pyenv-virtualenv, env `share-3.13`. Never `python -m venv`.
- Database: PostgreSQL (local Homebrew 17) + asyncpg. Redis for cache/rate limits.
- Local only this sprint. Do not deploy to WebOne until the owner sets folder + HTTPS.
- Routers thin; logic in `server/services/`.
- `can_view` is four lines and has no fifth case. P1: unknown and unauthorized are the same 404.

## State

Memory-first via engram (`project = shareweb` in `.engram.cfg`). Deferred work in `BACKLOG.md`.
