"""Append-only audit events (§3.8)."""

from __future__ import annotations

import json

from ..ids import prefixed


async def record(
    conn,
    *,
    user_id: str | None,
    actor_type: str,
    actor_token_id: str | None,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    target_label: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    metadata: dict | None = None,
) -> None:
    await conn.execute(
        """
        INSERT INTO audit_event (
            id, user_id, actor_type, actor_token_id, action,
            target_type, target_id, target_label, ip, user_agent, metadata
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::inet,$10,$11::jsonb)
        """,
        prefixed("aud"),
        user_id,
        actor_type,
        actor_token_id,
        action,
        target_type,
        target_id,
        target_label,
        ip,
        user_agent,
        json.dumps(metadata or {}),
    )
