"""sharectl — bootstrap and operator tools."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import sys
from pathlib import Path

# Load env from project root
os.chdir(Path(__file__).resolve().parent.parent)
from server.config import get_settings  # noqa: E402
from server.db import close_pool, init_pool  # noqa: E402
from server.errors import ShareError  # noqa: E402
from server.ids import new_api_token_secret, prefixed  # noqa: E402
from server.services import session_grants  # noqa: E402
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
    ensure_roots()
    grant = await session_grants.create(email, 30)
    await close_pool()
    print(f"root user: {email}  handle: {handle}  id: {user_id}")
    print("API token (shown once):")
    print(secret)
    print("One-time owner setup URL (valid for 30 minutes):")
    print(grant["url"])
    print("Open it now and register a passkey before configuring agents.")


async def _grant_session(email: str, minutes: int) -> None:
    await init_pool()
    try:
        grant = await session_grants.create(email, minutes)
    except (ShareError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        await close_pool()
        sys.exit(1)
    await close_pool()
    print(f"One-time owner session URL (valid for {minutes} minutes):")
    print(grant["url"])
    print("Open it now. Share will require passkey registration before owner access.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="sharectl")
    sub = parser.add_subparsers(dest="cmd", required=True)
    boot = sub.add_parser("bootstrap", help="Create the root user")
    boot.add_argument("--email", required=True)
    boot.add_argument("--handle", required=True)
    grant = sub.add_parser("grant-session", help="Issue a one-time owner recovery URL")
    grant.add_argument("--email", required=True)
    grant.add_argument("--minutes", type=int, default=30)
    args = parser.parse_args()
    if args.cmd == "bootstrap":
        asyncio.run(_bootstrap(args.email, args.handle))
    elif args.cmd == "grant-session":
        if os.geteuid() != 0:
            print("ERROR: grant-session must run as root on the Share server.", file=sys.stderr)
            sys.exit(1)
        asyncio.run(_grant_session(args.email, args.minutes))


if __name__ == "__main__":
    main()
