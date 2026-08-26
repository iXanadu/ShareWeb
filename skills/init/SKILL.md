---
name: init
description: When initializing a new project from this template for the first time — run this to bootstrap project name, env files, and initial memory state. It does NOT create databases (that's a deliberate manual step).
---

This is a NEW PROJECT initialization from the FastAPI template. Follow these steps:

## 1. Gather Project Information

Ask the user for:
- **Project name** (lowercase, no spaces, e.g., `beastchat`)
- **Brief description** (one line — what does this app do?)
- **Port number** (default: 8000, but check for conflicts)

## 2. Set Up Python Environment

```bash
pyenv virtualenv 3.13 {projectname}-3.13
pyenv local {projectname}-3.13
pip install -e ".[dev]"
```

## 3. Set Up Environment Files

Copy examples to live files:
```bash
cp examples/.env.example .env
cp examples/.keys.example .keys
chmod 600 .keys
```

Edit `.env` to replace placeholders:
- `PROJECTNAME` → actual project name
- `PORT` → chosen port number

## 4. Read Project Specs

Read any files in `docs/specs/` (especially `prd.md`) to understand what this project should do.

## 5. Database — MANUAL, NOT done by `/init`

`/init` never touches a database. Provisioning the Postgres role + dev/prod DBs mutates the
shared cluster, so it's a deliberate step **you run yourself**, and only if the project needs one:

```bash
./scripts/provision-db.sh <projectname>
```

That script sources the app password from `.keys` (never hardcoded) and admin
creds from `~/.pgpass` (`DB_HOST` and `DB_ADMIN_USER` required). No database needed? Skip this entirely.

## 6. Customize the Skeleton

Edit the following files to replace `projectname` with actual values:
- `pyproject.toml` — name, description
- `server/config.py` — env_prefix
- `AGENTS.md` — project name, description, structure
- `systemd/projectname.service` — rename file and update paths

## 7. Verify It Runs

```bash
uvicorn server.main:app --reload --port {port}
# In another terminal or browser:
curl http://localhost:{port}/health
```

## 8. Git Init

```bash
git init
git add -A
git commit -m "Initialize {projectname} from FastAPI template"
```

Write `.engram.cfg` at repo root:
```
project = {projectname}
```
Stage and commit: `Add .engram.cfg — canonical project identifier`

Ask user if they want to push to GitHub.

## 9. Store Initial State in Memory

Use `memory_store` with `scope=project` to record:
- Key: `session/YYYY-MM-DD-project-init`
- Include: project name, port, database info, what specs describe, setup steps completed

## 10. Summary

Summarize:
- What was set up (env, DB, skeleton, git)
- What the PRD says the project should do (if specs exist)
- Suggested next steps
- Ask what the user wants to work on first
