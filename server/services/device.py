"""Device-code flow for agent tokens (§4.6.2)."""

from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis

from ..auth import AGENT_SCOPES, Actor
from ..config import get_settings
from ..errors import ShareError
from . import tokens

_TTL = 600
_ALPH = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _user_code() -> str:
    raw = "".join(secrets.choice(_ALPH) for _ in range(8))
    return f"{raw[:4]}-{raw[4:]}"


def _norm_code(code: str) -> str:
    compact = "".join(ch for ch in (code or "").upper() if ch.isalnum())
    if len(compact) != 8:
        return ""
    return f"{compact[:4]}-{compact[4:]}"


async def _r():
    return aioredis.from_url(get_settings().redis_url, decode_responses=True)


async def start(name: str, request_ip: str | None, user_agent: str | None) -> dict:
    name = (name or "").strip() or "unnamed-agent"
    device_code = secrets.token_urlsafe(32)
    user_code = _user_code()
    now = datetime.now(UTC)
    payload = {
        "deviceCode": device_code,
        "userCode": user_code,
        "name": name,
        "status": "pending",
        "requestedScopes": list(AGENT_SCOPES),
        "sourceIp": request_ip,
        "userAgent": user_agent,
        "createdAt": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expiresAt": (now + timedelta(seconds=_TTL)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "userId": None,
        "token": None,
        "tokenId": None,
    }
    client = await _r()
    try:
        await client.set(f"sh:dev:{device_code}", json.dumps(payload), ex=_TTL)
        await client.set(f"sh:ucode:{user_code}", device_code, ex=_TTL)
    finally:
        await client.aclose()
    from ..auth import public_base_url

    return {
        "deviceCode": device_code,
        "userCode": user_code,
        "verifyUrl": f"{public_base_url()}/~/authorize",
        "expiresIn": _TTL,
        "interval": 5,
    }


async def _load_by_device(device_code: str) -> dict | None:
    client = await _r()
    try:
        raw = await client.get(f"sh:dev:{device_code}")
    finally:
        await client.aclose()
    return json.loads(raw) if raw else None


async def _load_by_user(user_code: str) -> tuple[str, dict] | None:
    code = _norm_code(user_code)
    if not code:
        return None
    client = await _r()
    try:
        device_code = await client.get(f"sh:ucode:{code}")
        if not device_code:
            return None
        raw = await client.get(f"sh:dev:{device_code}")
    finally:
        await client.aclose()
    if not raw:
        return None
    return device_code, json.loads(raw)


async def _save(device_code: str, payload: dict) -> None:
    client = await _r()
    try:
        ttl = await client.ttl(f"sh:dev:{device_code}")
        if ttl is None or ttl < 1:
            ttl = _TTL
        await client.set(f"sh:dev:{device_code}", json.dumps(payload), ex=ttl)
    finally:
        await client.aclose()


async def poll(device_code: str) -> dict:
    payload = await _load_by_device(device_code)
    if not payload or payload["status"] == "denied":
        raise ShareError(404, "unknown_or_expired", "That request is unknown or expired.")
    if payload["status"] == "pending":
        raise ShareError(428, "authorization_pending", "Waiting for approval.")
    token = payload.get("token")
    if not token:
        raise ShareError(404, "unknown_or_expired", "That request is unknown or expired.")
    payload["token"] = None
    await _save(device_code, payload)
    return {
        "token": token,
        "tokenId": payload["tokenId"],
        "scopes": payload["requestedScopes"],
    }


async def lookup(user_code: str) -> dict:
    found = await _load_by_user(user_code)
    if not found or found[1]["status"] != "pending":
        raise ShareError(404, "unknown_or_expired", "That request is unknown or expired.")
    p = found[1]
    return {
        "name": p["name"],
        "requestedScopes": p["requestedScopes"],
        "sourceIp": p.get("sourceIp"),
        "userAgent": p.get("userAgent"),
        "createdAt": p["createdAt"],
        "expiresAt": p["expiresAt"],
    }


async def approve(actor: Actor, user_code: str, request_ip: str | None) -> dict:
    found = await _load_by_user(user_code)
    if not found or found[1]["status"] != "pending":
        raise ShareError(404, "unknown_or_expired", "That request is unknown or expired.")
    device_code, payload = found
    created = await tokens.create_token(
        actor, payload["name"], list(AGENT_SCOPES), request_ip
    )
    payload["status"] = "approved"
    payload["userId"] = actor.user_id
    payload["token"] = created["token"]
    payload["tokenId"] = created["tokenId"]
    await _save(device_code, payload)
    return {
        "tokenId": created["tokenId"],
        "name": payload["name"],
        "scopes": created["scopes"],
    }


async def deny(user_code: str) -> dict:
    found = await _load_by_user(user_code)
    if not found or found[1]["status"] != "pending":
        raise ShareError(404, "unknown_or_expired", "That request is unknown or expired.")
    device_code, payload = found
    payload["status"] = "denied"
    payload["token"] = None
    await _save(device_code, payload)
    return {}
