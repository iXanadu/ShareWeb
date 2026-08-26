"""sharectl — bootstrap and operator tools."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Load env from project root
os.chdir(Path(__file__).resolve().parent.parent)
from server.config import get_settings  # noqa: E402
from server.db import close_pool, init_pool  # noqa: E402
from server.ids import new_api_token_secret, new_session_secret, prefixed  # noqa: E402
from server.services.store import ensure_roots  # noqa: E402


async def _bootstrap(email: str, handle: str) -> None:
    settings = get_settings()
    if not settings.secret_key:
        print("ERROR: SHARE_SECRET_KEY is empty. Fill .keys first.", file=sys.stderr)
        sys.exit(1)
    pool = await init_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchval("SELECT COUNT(*) FROM app_user")
        if existing:
            print("ERROR: bootstrap already ran — a user exists.", file=sys.stderr)
            await close_pool()
            sys.exit(1)
        user_id = prefixed("usr")
        token_id = prefixed("shr")
        secret = new_api_token_secret()
        session_secret = new_session_secret()
        await conn.execute(
            """
            INSERT INTO app_user (id, email, display_name, handle, is_root, settings)
            VALUES ($1,$2,$3,$4,true,$5::jsonb)
            """,
            user_id,
            email,
            handle,
            handle,
            '{"defaultShareTtl":"14d","notifyOnShare":true}',
        )
        await conn.execute(
            """
            INSERT INTO api_token (
                id, user_id, name, display_prefix, token_hash, scopes
            ) VALUES ($1,$2,$3,$4,$5,$6)
            """,
            token_id,
            user_id,
            "bootstrap",
            secret[:12],
            hashlib.sha256(secret.encode()).digest(),
            ["artifacts:read", "artifacts:write"],
        )
        await conn.execute(
            """
            INSERT INTO session (id, user_id, token_hash, expires_at)
            VALUES ($1,$2,$3,$4)
            """,
            prefixed("ses"),
            user_id,
            hashlib.sha256(session_secret.encode()).digest(),
            datetime.now(UTC) + timedelta(days=30),
        )
    ensure_roots()
    await close_pool()
    print(f"root user: {email}  handle: {handle}  id: {user_id}")
    print("API token (shown once):")
    print(secret)
    print("Session cookie share_s (shown once, until passkeys exist):")
    print(session_secret)


def main() -> None:
    parser = argparse.ArgumentParser(prog="sharectl")
    sub = parser.add_subparsers(dest="cmd", required=True)
    boot = sub.add_parser("bootstrap", help="Create the root user")
    boot.add_argument("--email", required=True)
    boot.add_argument("--handle", required=True)
    args = parser.parse_args()
    if args.cmd == "bootstrap":
        asyncio.run(_bootstrap(args.email, args.handle))


if __name__ == "__main__":
    main()
