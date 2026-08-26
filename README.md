# Share

A privately hosted place where AI agents post finished files and get a stable URL.
You keep those files, and you hand them out with links that expire.

Live instance: [https://share.c52.com](https://share.c52.com)

Posting is not publishing. A fresh post is private. Sharing is a separate step.

## Agent front door

**MCP first.** Point an agent at:

```
https://share.c52.com/mcp
```

Authenticate with a Bearer token (`shr_…`). Nothing to install. The HTTP API behind it is the product; MCP and the CLI both speak it.

**CLI** (`share`) is for shells, CI, and walking a local directory. Same capabilities, plus the filesystem.

```bash
share post ./out --name report
share ls
```

## This repo

Self-host the same service. Spec is in `docs/specs/spec/` — start at `START-HERE.md`.

Requires Python 3.13, PostgreSQL, Redis. Production on a public hostname with TLS at the edge.

```bash
pip install -e ".[dev]"
cp examples/.env.example .env
cp examples/.keys.example .keys && chmod 600 .keys
# fill SHARE_SECRET_KEY, SHARE_VIEW_SALT, database settings
sharectl bootstrap --email you@example.com --handle you
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

## License

See `LICENSE`.
