# Share

Self-hosted artifact host. An agent posts finished files over MCP and gets a stable URL. You keep the files and hand them out with links that expire.

**Not** a public SaaS, not GitHub Pages, not a zip in an email. You run a copy. Posting is not publishing: a new post is private until you create a share link.

## Features

- **MCP** — seven tools at `POST /mcp`, bearer token `shr_…`
- **Private by default** — `share_post` never mints a public URL
- **Expiring share links** — `share_create_link` (`/s/…`), optional password, revoke anytime
- **Content-addressed files** — SHA-256; re-posting a directory uploads only what changed
- **Passkeys + tokens** — you sign in in the browser; agents get named, scoped, revocable tokens
- **Same 404** — unknown and unauthorized are indistinguishable

## Requirements

- Python 3.13 via [pyenv](https://github.com/pyenv/pyenv) + pyenv-virtualenv (do **not** use `python -m venv`)
- PostgreSQL 17
- Redis

macOS with Homebrew: `brew install pyenv pyenv-virtualenv postgresql@17 redis`, then start Postgres and Redis.

## Quick start

```bash
git clone https://github.com/iXanadu/ShareWeb.git
cd ShareWeb

pyenv virtualenv 3.13.12 share-3.13
pyenv local share-3.13
pip install -e ".[dev]"

cp examples/.env.example .env
cp examples/.keys.example .keys
chmod 600 .keys
```

Edit `.env`: `SHARE_DB_USER` is your OS username on a Mac (leave `SHARE_DB_HOST` empty for the Unix socket). On Linux it is often `share`.

```bash
createdb share_dev          # once
openssl rand -hex 32        # → SHARE_SECRET_KEY in .keys
openssl rand -hex 32        # → SHARE_VIEW_SALT in .keys

uvicorn server.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, create the owner:

```bash
sharectl bootstrap --email you@example.com --handle you
```

Migrations run on application and `sharectl` startup. Bootstrap prints **once**:

- an agent API token (`shr_…`) with `artifacts:read` and `artifacts:write`; and
- a one-time owner setup URL valid for 30 minutes.

Open the setup URL immediately and register a passkey. Share has no password login. The URL
creates a restricted browser session that can only inspect and register passkeys until setup is
complete. If you lose it before registering a passkey, use the server recovery command below.

| URL | What |
| --- | --- |
| http://127.0.0.1:8000/ | Public pages |
| http://127.0.0.1:8000/~/ | Dashboard — register a passkey, issue tokens |
| http://127.0.0.1:8000/mcp | MCP (JSON-RPC POST) |

```bash
pytest tests/ -q
ruff check .
```

## Create agent tokens

Open `/~/tokens` while signed in. Create a separate named token for each coder, bot, or service;
do not share one bearer token across unrelated agents. Separate tokens give useful attribution
and let you revoke one agent without stopping the others.

Every token starts with `artifacts:read` and `artifacts:write`. Add `share:create` only when that
agent should be able to publish expiring `/s/…` links. Add `artifacts:delete` only when it should
be able to purge trash permanently. The full token is shown once.

## Point an agent at it

One token. That is the only secret that belongs in the agent config.

```json
{
  "mcpServers": {
    "share": {
      "url": "https://YOUR-HOST/mcp",
      "headers": { "Authorization": "Bearer shr_…" }
    }
  }
}
```

From a terminal:

```bash
share post ./out --name report
share ls
```

## Recover owner access

There is no password or email-link bypass. If all owner passkeys are unavailable, SSH to the
Share server and run this as root:

```bash
sharectl grant-session --email you@example.com --minutes 30
```

Open the printed URL once. It expires within 30 minutes, cannot be replayed, and forces passkey
registration before token administration or artifact access. Creating and redeeming it are
written to the audit log.

## Tools

| Tool | Notes |
| --- | --- |
| `share_post` | Post files. Stays private. Returns the artifact URL. |
| `share_create_link` | Mint an expiring `/s/…` URL. Needs `share:create`. |
| `share_list` | List artifacts. Pass `trashed` for trash. |
| `share_get` | One artifact by name. |
| `share_delete` | Move to trash. Recoverable. |
| `share_restore` | Restore from trash. |
| `share_whoami` | Authenticated identity. |

Failed calls come back as MCP tool content with `isError: true` and a `code: message` string, not as a protocol error.

## Configuration

Non-sensitive settings in `.env`; secrets in `.keys` (never commit either when filled). Templates: `examples/.env.example`, `examples/.keys.example`.

| Variable | File | Purpose |
| --- | --- | --- |
| `SHARE_HOST` | `.env` | Public hostname (WebAuthn RP ID in production) |
| `SHARE_BIND_HOST` | `.env` | Bind address (local: `127.0.0.1`) |
| `SHARE_PORT` | `.env` | Listen port (default `8000`) |
| `SHARE_DB_HOST` | `.env` | Empty = Unix socket (peer auth) |
| `SHARE_DB_NAME` | `.env` | Database (local: `share_dev`) |
| `SHARE_DB_USER` | `.env` | Role (your OS user on a Mac) |
| `SHARE_REDIS_URL` | `.env` | Redis |
| `SHARE_FILE_ROOT` | `.env` | Artifact blobs |
| `SHARE_TMP_ROOT` | `.env` | Upload scratch (same filesystem as file root) |
| `SHARE_SECRET_KEY` | `.keys` | App secret |
| `SHARE_VIEW_SALT` | `.keys` | View-token salt |
| `SHARE_DB_PASSWORD` | `.keys` | Only if the role has a password |

## Putting it on a box

Bind the app to loopback and put nginx (or Caddy) in front for TLS. Run it as its own service user, never as root. Files and Postgres stay on that machine — back them up off-box.

The public page `/your-server` is the practice: ten minutes by hand, then you prompt an agent for the rest. Live copy: [share.c52.com/your-server](https://share.c52.com/your-server).

## Tests

```bash
pytest tests/ -q
```

Uses a local `share_test` database and Redis DB `/1`. No production data.

## Open work

[BACKLOG.md](BACKLOG.md) — if it is not there, it is not tracked.

The `docs/specs/` tree is historical. Do not start there.

## License

Apache License 2.0. See [LICENSE](LICENSE).
