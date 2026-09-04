"""One-time server recovery grants are narrow and non-replayable."""

import base64
import json
from types import SimpleNamespace
from urllib.parse import urlsplit


async def test_grant_redeems_once_into_restricted_session(client, root_user):
    from server.services import session_grants

    grant = await session_grants.create("root@example.com", 30)
    url = urlsplit(grant["url"])

    redeemed = await client.get(f"{url.path}?{url.query}", follow_redirects=False)
    assert redeemed.status_code == 303, redeemed.text
    assert redeemed.headers["location"] == "/~/security/passkeys/new"
    assert "share_s=" in redeemed.headers["set-cookie"]
    assert "HttpOnly" in redeemed.headers["set-cookie"]

    replayed = await client.get(f"{url.path}?{url.query}", follow_redirects=False)
    assert replayed.status_code == 404
    assert replayed.json()["error"]["code"] == "invalid_or_expired_grant"

    me = await client.get("/api/v1/me")
    assert me.status_code == 200, me.text
    assert me.json()["requiresPasskey"] is True

    artifacts = await client.get("/api/v1/artifacts")
    assert artifacts.status_code == 403
    assert artifacts.json()["error"]["code"] == "restricted_session"

    tokens = await client.get("/api/v1/tokens")
    assert tokens.status_code == 403
    assert tokens.json()["error"]["code"] == "restricted_session"

    passkeys = await client.get("/api/v1/auth/passkeys")
    assert passkeys.status_code == 200
    assert passkeys.json()["items"] == []

    register = await client.post("/auth/passkey/register/begin", json={})
    assert register.status_code == 200, register.text


async def test_new_grant_invalidates_previous_open_grant(client, root_user):
    from server.services import session_grants

    first = urlsplit((await session_grants.create("root@example.com", 30))["url"])
    second = urlsplit((await session_grants.create("root@example.com", 30))["url"])

    stale = await client.get(f"{first.path}?{first.query}", follow_redirects=False)
    assert stale.status_code == 404

    current = await client.get(f"{second.path}?{second.query}", follow_redirects=False)
    assert current.status_code == 303


async def test_passkey_enrollment_upgrades_recovery_session(
    client,
    root_user,
    db_pool,
    monkeypatch,
):
    from server.services import passkeys, session_grants

    grant = urlsplit((await session_grants.create("root@example.com", 30))["url"])
    redeemed = await client.get(f"{grant.path}?{grant.query}", follow_redirects=False)
    assert redeemed.status_code == 303

    started = await client.post("/auth/passkey/register/begin", json={})
    challenge = started.json()["publicKey"]["challenge"]
    client_data = (
        base64.urlsafe_b64encode(json.dumps({"challenge": challenge}).encode())
        .decode()
        .rstrip("=")
    )
    monkeypatch.setattr(
        passkeys,
        "verify_registration_response",
        lambda **kwargs: SimpleNamespace(
            credential_id=b"new-passkey-id",
            credential_public_key=b"new-public-key",
            sign_count=0,
        ),
    )

    finished = await client.post(
        "/auth/passkey/register/finish",
        json={
            "name": "Test passkey",
            "credential": {
                "id": "ignored-by-mock",
                "response": {"clientDataJSON": client_data},
            },
        },
    )
    assert finished.status_code == 200, finished.text
    assert "Max-Age=2592000" in finished.headers["set-cookie"]

    async with db_pool.acquire() as conn:
        purpose = await conn.fetchval(
            "SELECT purpose FROM session ORDER BY created_at DESC LIMIT 1"
        )
    assert purpose == "full"

    tokens = await client.get("/api/v1/tokens")
    assert tokens.status_code == 200, tokens.text
