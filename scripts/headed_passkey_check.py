#!/usr/bin/env python3
"""Headed passkey register + sign-in click-through against local dev (11.1, 11.3)."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BASE = "http://localhost:8000"


async def ensure_bootstrap_session() -> str:
    from server.db import close_pool, init_pool
    from server.ids import new_session_secret, prefixed

    pool = await init_pool()
    async with pool.acquire() as conn:
        user_id = await conn.fetchval("SELECT id FROM app_user WHERE is_root = true")
        if not user_id:
            await close_pool()
            raise SystemExit("No root user — run sharectl bootstrap first")
        secret = new_session_secret()
        await conn.execute(
            """
            INSERT INTO session (id, user_id, token_hash, expires_at)
            VALUES ($1,$2,$3,$4)
            """,
            prefixed("ses"),
            user_id,
            hashlib.sha256(secret.encode()).digest(),
            datetime.now(UTC) + timedelta(hours=1),
        )
    await close_pool()
    return secret


def add_virtual_authenticator(page) -> None:
    client = page.context.new_cdp_session(page)
    client.send("WebAuthn.enable")
    client.send(
        "WebAuthn.addVirtualAuthenticator",
        {
            "options": {
                "protocol": "ctap2",
                "transport": "internal",
                "hasResidentKey": True,
                "hasUserVerification": True,
                "isUserVerified": True,
            }
        },
    )


def run_clickthrough(session_secret: str, *, headed: bool) -> dict[str, str]:
    from playwright.sync_api import sync_playwright

    results: dict[str, str] = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        context = browser.new_context()
        context.add_cookies(
            [
                {
                    "name": "share_s",
                    "value": session_secret,
                    "domain": "localhost",
                    "path": "/",
                    "httpOnly": True,
                    "sameSite": "Lax",
                }
            ]
        )
        page = context.new_page()
        add_virtual_authenticator(page)

        page.goto(f"{BASE}/~/security/passkeys/new", wait_until="networkidle")
        page.wait_for_selector("#register-pk", timeout=15000)
        page.fill("#pk-name", "Headed test passkey")
        page.click("#register-pk")
        try:
            page.wait_for_url("**/~/security", timeout=30000)
            results["register"] = "pass"
        except Exception as exc:
            err = page.query_selector("#pk-error")
            msg = err.inner_text() if err and err.is_visible() else str(exc)
            results["register"] = f"fail: {msg}"

        context.clear_cookies()

        page.goto(f"{BASE}/~/signin", wait_until="networkidle")
        page.wait_for_selector("#signin-btn", timeout=15000)
        page.click("#signin-btn")
        try:
            page.wait_for_url("**/~/artifacts", timeout=30000)
            results["signin"] = "pass"
        except Exception as exc:
            err = page.query_selector(".share-error")
            msg = err.inner_text() if err and err.is_visible() else str(exc)
            results["signin"] = f"fail: {msg}"

        browser.close()

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--headless", action="store_true", help="Run without a visible window")
    args = parser.parse_args()
    session = asyncio.run(ensure_bootstrap_session())
    results = run_clickthrough(session, headed=not args.headless)
    print(f"register: {results.get('register')}")
    print(f"signin: {results.get('signin')}")
    if results.get("register") != "pass" or results.get("signin") != "pass":
        sys.exit(1)


if __name__ == "__main__":
    main()
