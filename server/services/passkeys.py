"""WebAuthn registration and login (§4.2–4.4)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import bytes_to_base64url, options_to_json_dict
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from ..auth import Actor, _sha256
from ..config import get_settings
from ..db import get_pool
from ..errors import ShareError
from ..ids import new_session_secret, prefixed

_CHALLENGE_TTL = 300


def _rp_id() -> str:
    host = get_settings().host
    return host.split(":")[0]


def _origin() -> str:
    settings = get_settings()
    host = settings.host
    if (
        host in {"localhost", "127.0.0.1"}
        or host.endswith(".local")
        or "." not in host
        or settings.debug
    ):
        port = settings.port
        if port in (80, 443):
            return f"http://{host}"
        return f"http://{host}:{port}"
    return f"https://{host}"


async def _redis():
    return aioredis.from_url(get_settings().redis_url, decode_responses=True)


async def _put_challenge(challenge: bytes, payload: dict) -> None:
    client = await _redis()
    try:
        key = "sh:wa:" + bytes_to_base64url(challenge)
        await client.set(key, json.dumps(payload), ex=_CHALLENGE_TTL)
    finally:
        await client.aclose()


async def _pop_challenge(challenge_b64: str) -> dict | None:
    client = await _redis()
    try:
        key = "sh:wa:" + challenge_b64
        raw = await client.getdel(key)
    finally:
        await client.aclose()
    if not raw:
        return None
    return json.loads(raw)


async def login_begin() -> dict:
    options = generate_authentication_options(
        rp_id=_rp_id(),
        timeout=120000,
        allow_credentials=[],
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    await _put_challenge(options.challenge, {"kind": "login"})
    return {"publicKey": options_to_json_dict(options)}


async def register_begin(actor: Actor) -> dict:
    if not actor.is_user or not actor.user_id:
        raise ShareError(401, "session_expired", "Sign in first.")
    pool = await get_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM app_user WHERE id = $1", actor.user_id)
        existing = await conn.fetch(
            """
            SELECT credential_id FROM passkey_credential
            WHERE user_id = $1 AND revoked_at IS NULL
            """,
            actor.user_id,
        )
    exclude = [
        PublicKeyCredentialDescriptor(id=row["credential_id"]) for row in existing
    ]
    options = generate_registration_options(
        rp_id=_rp_id(),
        rp_name="Share",
        user_name=user["email"],
        user_id=actor.user_id.encode(),
        user_display_name=user["display_name"] or user["handle"] or user["email"],
        timeout=120000,
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        exclude_credentials=exclude or None,
    )
    await _put_challenge(options.challenge, {"kind": "register", "user_id": actor.user_id})
    return {"publicKey": options_to_json_dict(options)}


def _challenge_from_client_data(credential: dict) -> str | None:
    import base64

    raw = credential.get("response", {}).get("clientDataJSON")
    if not raw:
        return None
    pad = "=" * (-len(raw) % 4)
    try:
        data = json.loads(base64.urlsafe_b64decode(raw + pad))
    except Exception:
        return None
    return data.get("challenge")


async def login_finish(credential: dict) -> tuple[dict, str]:
    challenge_b64 = _challenge_from_client_data(credential)
    if not challenge_b64:
        raise ShareError(401, "webauthn_verification_failed", "That sign-in could not be verified.")
    stored = await _pop_challenge(challenge_b64)
    if not stored or stored.get("kind") != "login":
        raise ShareError(401, "webauthn_verification_failed", "That sign-in could not be verified.")
    cred_id = credential.get("id") or credential.get("rawId")
    if not cred_id:
        raise ShareError(401, "invalid_credential", "That passkey is not registered here.")
    from webauthn.helpers import base64url_to_bytes

    try:
        cred_bytes = base64url_to_bytes(cred_id)
    except Exception as exc:
        raise ShareError(401, "invalid_credential", "That passkey is not registered here.") from exc
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT p.*, u.email, u.handle, u.display_name, u.is_root, u.disabled_at
            FROM passkey_credential p
            JOIN app_user u ON u.id = p.user_id
            WHERE p.credential_id = $1 AND p.revoked_at IS NULL
            """,
            cred_bytes,
        )
        if row is None or row["disabled_at"] is not None:
            raise ShareError(401, "invalid_credential", "That passkey is not registered here.")
        try:
            verification = verify_authentication_response(
                credential=credential,
                expected_challenge=base64url_to_bytes(challenge_b64),
                expected_rp_id=_rp_id(),
                expected_origin=_origin(),
                credential_public_key=row["public_key"],
                credential_current_sign_count=row["sign_count"],
                require_user_verification=False,
            )
        except Exception as exc:
            raise ShareError(
                401, "webauthn_verification_failed", "That sign-in could not be verified."
            ) from exc
        new_count = verification.new_sign_count
        if row["sign_count"] and new_count <= row["sign_count"]:
            raise ShareError(
                401,
                "credential_counter_regressed",
                "That passkey may have been copied. Sign-in was refused.",
            )
        await conn.execute(
            """
            UPDATE passkey_credential
            SET sign_count = $2, last_used_at = now()
            WHERE id = $1
            """,
            row["id"],
            new_count,
        )
        secret = new_session_secret()
        await conn.execute(
            """
            INSERT INTO session (id, user_id, token_hash, passkey_id, expires_at)
            VALUES ($1,$2,$3,$4,$5)
            """,
            prefixed("ses"),
            row["user_id"],
            _sha256(secret),
            row["id"],
            datetime.now(UTC) + timedelta(days=30),
        )
    user = {
        "id": row["user_id"],
        "email": row["email"],
        "handle": row["handle"],
        "displayName": row["display_name"],
        "isRoot": bool(row["is_root"]),
    }
    return user, secret


async def register_finish(actor: Actor, credential: dict, name: str) -> dict:
    if not actor.is_user:
        raise ShareError(401, "session_expired", "Sign in first.")
    challenge_b64 = _challenge_from_client_data(credential)
    if not challenge_b64:
        raise ShareError(401, "webauthn_verification_failed", "That sign-in could not be verified.")
    stored = await _pop_challenge(challenge_b64)
    if not stored or stored.get("kind") != "register" or stored.get("user_id") != actor.user_id:
        raise ShareError(401, "webauthn_verification_failed", "That sign-in could not be verified.")
    from webauthn.helpers import base64url_to_bytes

    try:
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(challenge_b64),
            expected_rp_id=_rp_id(),
            expected_origin=_origin(),
            require_user_verification=False,
        )
    except Exception as exc:
        raise ShareError(
            401, "webauthn_verification_failed", "That sign-in could not be verified."
        ) from exc
    pky_id = prefixed("pky")
    label = (name or "").strip() or "Passkey"
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO passkey_credential (
                id, user_id, credential_id, public_key, sign_count, name, aaguid
            ) VALUES ($1,$2,$3,$4,$5,$6,$7)
            """,
            pky_id,
            actor.user_id,
            verification.credential_id,
            verification.credential_public_key,
            verification.sign_count,
            label,
            None,
        )
    return {
        "id": pky_id,
        "name": label,
        "createdAt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


async def list_passkeys(actor: Actor) -> dict:
    if not actor.is_user or not actor.user_id:
        raise ShareError(401, "session_expired", "Sign in first.")
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, name, created_at, last_used_at, backup_state, transports
            FROM passkey_credential
            WHERE user_id = $1 AND revoked_at IS NULL
            ORDER BY created_at
            """,
            actor.user_id,
        )
    items = []
    for r in rows:
        items.append(
            {
                "id": r["id"],
                "name": r["name"],
                "createdAt": r["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
                "lastUsedAt": r["last_used_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
                if r["last_used_at"]
                else None,
                "backupState": r["backup_state"],
                "transports": list(r["transports"] or []),
            }
        )
    return {"items": items}
