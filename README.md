# Share

A privately hosted place where AI agents post finished files and get a stable URL.
You keep those files, and you hand them out with links that expire.

Live instance: [https://share.c52.com](https://share.c52.com)

Posting is not publishing. A fresh post is private. Sharing is a separate step
(`share_create_link` / a dashboard or API link).

## Agent front door

**MCP first.** Point an agent at:

```
https://share.c52.com/mcp
```

Authenticate with a Bearer token (`shr_…`). One token. Nothing to install.

Tools: `share_post`, `share_create_link`, `share_list`, `share_get`,
`share_delete`, `share_restore`, `share_whoami`.

**CLI** (`share`) is for shells, CI, and walking a local directory.

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

Apache License 2.0. See `LICENSE`.
