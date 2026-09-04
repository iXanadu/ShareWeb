"""One-time server-issued owner session grants (§4.5)."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from ..auth import public_base_url
from ..db import get_pool
from ..errors import ShareError
from ..ids import new_session_secret, prefixed
from . import audit


def _digest(secret: str) -> bytes:
    return hashlib.sha256(secret.encode("utf-8")).digest()


async def create(email: str, minutes: int) -> dict:
    """Create one active grant for an existing owner and return its URL once."""
    if not 1 <= minutes <= 60:
        raise ValueError("minutes must be between 1 and 60")

    pool = await get_pool()
    async with pool.acquire() as conn, conn.transaction():
        user = await conn.fetchrow(
            "SELECT id, email FROM app_user WHERE email = $1 AND disabled_at IS NULL",
            email.strip(),
        )
        if user is None:
            raise ShareError(404, "user_not_found", "No active user has that email address.")

        await conn.execute(
            """
            UPDATE session_grant
            SET used_at = now()
            WHERE user_id = $1 AND used_at IS NULL
            """,
            user["id"],
        )
        grant_id = prefixed("sgr")
        secret = new_session_secret()
        expires_at = datetime.now(UTC) + timedelta(minutes=minutes)
        await conn.execute(
            """
            INSERT INTO session_grant (id, user_id, token_hash, expires_at)
            VALUES ($1,$2,$3,$4)
            """,
            grant_id,
            user["id"],
            _digest(secret),
            expires_at,
        )
        await audit.record(
            conn,
            user_id=user["id"],
            actor_type="system",
            actor_token_id=None,
            action="auth.session_granted",
            target_type="session_grant",
            target_id=grant_id,
            target_label=str(user["email"]),
            metadata={"minutes": minutes},
        )

    return {
        "id": grant_id,
        "url": f"{public_base_url()}/auth/grant?token={quote(secret)}",
        "expiresAt": expires_at,
    }


async def redeem(secret: str, request_ip: str | None, user_agent: str | None) -> dict:
    """Consume a grant atomically and issue a purpose-limited browser session."""
    if not secret:
        raise ShareError(404, "invalid_or_expired_grant", "That session link is invalid or expired.")

    pool = await get_pool()
    async with pool.acquire() as conn, conn.transaction():
        grant = await conn.fetchrow(
            """
            SELECT sg.id, sg.user_id, sg.expires_at, u.handle
            FROM session_grant sg
            JOIN app_user u ON u.id = sg.user_id
            WHERE sg.token_hash = $1
              AND sg.used_at IS NULL
              AND sg.expires_at > now()
              AND u.disabled_at IS NULL
            FOR UPDATE OF sg
            """,
            _digest(secret),
        )
        if grant is None:
            raise ShareError(
                404,
                "invalid_or_expired_grant",
                "That session link is invalid or expired.",
            )

        await conn.execute(
            "UPDATE session_grant SET used_at = now(), used_ip = $2::inet WHERE id = $1",
            grant["id"],
            request_ip,
        )
        session_secret = new_session_secret()
        session_id = prefixed("ses")
        await conn.execute(
            """
            INSERT INTO session (
                id, user_id, token_hash, expires_at, ip, user_agent, purpose
            ) VALUES ($1,$2,$3,$4,$5::inet,$6,'recovery')
            """,
            session_id,
            grant["user_id"],
            _digest(session_secret),
            grant["expires_at"],
            request_ip,
            user_agent,
        )
        await audit.record(
            conn,
            user_id=grant["user_id"],
            actor_type="system",
            actor_token_id=None,
            action="auth.session_grant_redeemed",
            target_type="session",
            target_id=session_id,
            ip=request_ip,
            user_agent=user_agent,
            metadata={"grantId": grant["id"]},
        )

    max_age = max(1, int((grant["expires_at"] - datetime.now(UTC)).total_seconds()))
    return {
        "secret": session_secret,
        "maxAge": max_age,
        "handle": grant["handle"],
    }
