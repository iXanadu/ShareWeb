# fastapi (claude-templates)

Project template for FastAPI applications with Claude Code.

## What's Included

- **FastAPI skeleton** — app factory, lifespan, config, DB pool, auth, routers, services
- **Claude skills** — `/init`, `/startup`, `/wrapup` for project lifecycle
- **Testing** — pytest-asyncio with session-scoped DB fixtures and async HTTP client
- **Deployment** — systemd unit file template
- **Conventions** — structlog, asyncpg, pydantic-settings, ruff

## Usage

```bash
rsync -a --exclude='.git' --exclude='.DS_Store' --exclude='Icon*' ~/projects/claude-templates/fastapi/ ~/projects/<newapp>/
cd ~/projects/<newapp>
# Then run /init in Claude Code
```

Or, for a guaranteed-clean copy straight from the committed tree:

```bash
git -C ~/projects/claude-templates archive HEAD:fastapi | tar -x -C ~/projects/<newapp>
```

## Stack

- Python 3.13 (pyenv + pyenv-virtualenv)
- FastAPI + uvicorn
- PostgreSQL + asyncpg
- structlog (structured logging)
- pydantic-settings (config from .env + .keys)
- ruff (linting)
- pytest-asyncio (testing)
