"""API token list/create/revoke for the dashboard (§4.6, 11.18)."""

from __future__ import annotations

import hashlib

from ..auth import Actor
from ..db import get_pool
from ..errors import ShareError
from ..ids import new_api_token_secret, prefixed
from . import audit

ALLOWED_SCOPES = {
    "artifacts:read",
    "artifacts:write",
    "artifacts:delete",
    "share:create",
    "account:read",
}


async def list_tokens(actor: Actor) -> dict:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, name, display_prefix, scopes, created_at, last_used_at, expires_at
            FROM api_token
            WHERE user_id = $1 AND revoked_at IS NULL
            ORDER BY created_at DESC
            """,
            actor.user_id,
        )
    return {
        "items": [
            {
                "id": r["id"],
                "name": r["name"],
                "displayPrefix": r["display_prefix"],
                "scopes": list(r["scopes"] or []),
                "createdAt": r["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                "lastUsedAt": r["last_used_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
                if r["last_used_at"]
                else None,
                "expiresAt": r["expires_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
                if r["expires_at"]
                else None,
            }
            for r in rows
        ]
    }


async def create_token(actor: Actor, name: str, scopes: list[str], request_ip: str | None) -> dict:
    name = (name or "").strip()
    if not name:
        raise ShareError(422, "invalid_name", "A token needs a name.")
    cleaned = [s for s in scopes if s in ALLOWED_SCOPES]
    if not cleaned:
        cleaned = ["artifacts:read", "artifacts:write"]
    if "share:create" in cleaned and actor.token_id:
        raise ShareError(
            403,
            "insufficient_scope",
            "Only a signed-in owner can grant share:create.",
            {"scope": "share:create"},
        )
    secret = new_api_token_secret()
    token_id = prefixed("shr")
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO api_token (id, user_id, name, display_prefix, token_hash, scopes)
            VALUES ($1,$2,$3,$4,$5,$6)
            """,
            token_id,
            actor.user_id,
            name,
            secret[:12],
            hashlib.sha256(secret.encode()).digest(),
            cleaned,
        )
        await audit.record(
            conn,
            user_id=actor.user_id,
            actor_type="token" if actor.token_id else "user",
            actor_token_id=actor.token_id,
            action="token.create",
            target_type="api_token",
            target_id=token_id,
            target_label=name,
            ip=request_ip,
        )
    return {
        "token": secret,
        "tokenId": token_id,
        "name": name,
        "scopes": cleaned,
        "displayPrefix": secret[:12],
    }


async def revoke_token(actor: Actor, token_id: str, request_ip: str | None) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id FROM api_token
            WHERE id = $1 AND user_id = $2 AND revoked_at IS NULL
            """,
            token_id,
            actor.user_id,
        )
        if row is None:
            raise ShareError(404, "artifact_not_found", "No token with that id.")
        await conn.execute(
            "UPDATE api_token SET revoked_at = now() WHERE id = $1",
            token_id,
        )
        await audit.record(
            conn,
            user_id=actor.user_id,
            actor_type="token" if actor.token_id else "user",
            actor_token_id=actor.token_id,
            action="token.revoke",
            target_type="api_token",
            target_id=token_id,
            ip=request_ip,
        )
