"""Credential identification: API tokens and dashboard sessions."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from fastapi import Request

from .config import get_settings
from .db import get_pool
from .errors import ShareError

AGENT_SCOPES = ("artifacts:read", "artifacts:write")


@dataclass
class Actor:
    is_user: bool = False
    is_recipient: bool = False
    user_id: str | None = None
    token_id: str | None = None
    token_name: str | None = None
    scopes: tuple[str, ...] = ()
    handle: str | None = None
    is_root: bool = False
    link_id: str | None = None
    link_artifact_id: str | None = None
    link_live: bool = False

    def require_scope(self, scope: str) -> None:
        if scope not in self.scopes:
            raise ShareError(
                403,
                "insufficient_scope",
                "This token is missing a required scope.",
                {"scope": scope},
            )


def _sha256(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


async def _lookup_token(secret: str) -> Actor | None:
    if not secret.startswith("shr_"):
        return None
    digest = _sha256(secret)
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT t.id, t.user_id, t.name, t.scopes, t.revoked_at, t.expires_at,
                   u.handle, u.is_root, u.disabled_at
            FROM api_token t
            JOIN app_user u ON u.id = t.user_id
            WHERE t.token_hash = $1
            """,
            digest,
        )
    if row is None:
        return None
    if row["revoked_at"] is not None or row["disabled_at"] is not None:
        return None
    if row["expires_at"] is not None:
        from datetime import UTC, datetime

        if row["expires_at"] < datetime.now(UTC):
            return None
    return Actor(
        is_user=True,
        user_id=row["user_id"],
        token_id=row["id"],
        token_name=row["name"],
        scopes=tuple(row["scopes"] or ()),
        handle=row["handle"],
        is_root=bool(row["is_root"]),
    )


async def _lookup_session(secret: str) -> Actor | None:
    digest = _sha256(secret)
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT s.id, s.user_id, s.revoked_at, s.expires_at,
                   u.handle, u.is_root, u.disabled_at
            FROM session s
            JOIN app_user u ON u.id = s.user_id
            WHERE s.token_hash = $1
            """,
            digest,
        )
    if row is None:
        return None
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    if row["revoked_at"] is not None or row["disabled_at"] is not None:
        return None
    if row["expires_at"] < now:
        return None
    return Actor(
        is_user=True,
        user_id=row["user_id"],
        scopes=("artifacts:read", "artifacts:write", "artifacts:delete", "share:create"),
        handle=row["handle"],
        is_root=bool(row["is_root"]),
    )


async def identify(request: Request) -> Actor:
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        secret = auth[7:].strip()
        actor = await _lookup_token(secret)
        if actor is None:
            raise ShareError(401, "invalid_token", "Invalid or missing API token.")
        return actor
    cookie = request.cookies.get("share_s")
    if cookie:
        actor = await _lookup_session(cookie)
        if actor is None:
            raise ShareError(401, "session_expired", "Session expired. Sign in again.")
        return actor
    return Actor()


async def require_user(request: Request) -> Actor:
    actor = await identify(request)
    if not actor.is_user:
        raise ShareError(401, "invalid_token", "Invalid or missing API token.")
    return actor


def public_base_url() -> str:
    settings = get_settings()
    host = settings.host
    # Single-label LAN names (macmini) and localhost are HTTP this sprint.
    if (
        host in {"localhost", "127.0.0.1"}
        or host.endswith(".local")
        or "." not in host
        or settings.debug
    ):
        scheme = "http"
        port = settings.port
        if port not in (80, 443):
            return f"{scheme}://{host}:{port}"
        return f"{scheme}://{host}"
    return f"https://{host}"
