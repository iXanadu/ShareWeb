"""Passkey ceremony endpoints exist and fail closed."""


async def test_login_begin_shape(client):
    resp = await client.post("/auth/passkey/login/begin", json={})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    pk = body["publicKey"]
    assert pk["rpId"] in {"localhost", "share.c52.com"}
    assert "challenge" in pk
    assert pk.get("allowCredentials") in ([], None)


async def test_login_finish_garbage(client):
    resp = await client.post("/auth/passkey/login/finish", json={"credential": {"id": "nope"}})
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] in {
        "webauthn_verification_failed",
        "invalid_credential",
    }


async def test_register_begin_requires_session(client):
    resp = await client.post("/auth/passkey/register/begin", json={})
    assert resp.status_code == 401


async def test_register_begin_rejects_bearer_token(client, root_user):
    resp = await client.post(
        "/auth/passkey/register/begin",
        json={},
        headers=root_user["headers"],
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "wrong_credential_class"


async def test_register_begin_with_session(client, root_user):
    client.cookies.set("share_s", root_user["session"])
    resp = await client.post("/auth/passkey/register/begin", json={})
    assert resp.status_code == 200, resp.text
    pk = resp.json()["publicKey"]
    assert pk["rp"]["id"] in {"localhost", "share.c52.com"}
    assert pk["user"]["name"] == "root@example.com"


async def test_me_with_session(client, root_user):
    client.cookies.set("share_s", root_user["session"])
    resp = await client.get("/api/v1/me")
    assert resp.status_code == 200, resp.text
    assert resp.json()["handle"] == "robert"
    assert resp.json()["isRoot"] is True
