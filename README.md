# Share

A place you host yourself. An AI agent posts finished files and gets a URL.
You keep those files and hand them out with links that expire.

Posting is not publishing. A new post is private until you create a share link.

There is no public hosted service. You run a copy.

## Run it

You need **Python 3.13** ([pyenv](https://github.com/pyenv/pyenv) + pyenv-virtualenv), **PostgreSQL**, and **Redis**.

```bash
git clone https://github.com/iXanadu/ShareWeb.git
cd ShareWeb

pyenv virtualenv 3.13.12 share-3.13
pyenv local share-3.13
pip install -e ".[dev]"

cp examples/.env.example .env
cp examples/.keys.example .keys && chmod 600 .keys
```

Edit `.env` (database user is your OS username on a Mac, or `share` on Linux).
Put two long random strings in `.keys` for `SHARE_SECRET_KEY` and `SHARE_VIEW_SALT`.

```bash
sharectl bootstrap --email you@example.com --handle you
uvicorn server.main:app --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) for the public pages, and
[http://127.0.0.1:8000/~/](http://127.0.0.1:8000/~/) to sign in with a passkey
and issue tokens.

## Point an agent at your copy

One API token. It looks like `shr_…`. That is the only secret.

```json
{
  "mcpServers": {
    "share": {
      "url": "https://YOUR-HOST/mcp",
      "headers": {
        "Authorization": "Bearer shr_…"
      }
    }
  }
}
```

The agent posts files with `share_post` and mints an expiring link with `share_create_link`.

From a terminal, against the same host:

```bash
share post ./out --name report
share ls
```

## Docs

- Behaviour spec (start here): [docs/specs/spec/START-HERE.md](docs/specs/spec/START-HERE.md)
- After it is running locally: `/how-it-works` and `/for-agents`

## License

Apache License 2.0. See [LICENSE](LICENSE).
