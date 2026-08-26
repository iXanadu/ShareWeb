"""Device-code approval flow (§4.6.2)."""


async def test_device_unknown_lookup(client, root_user):
    client.cookies.set("share_s", root_user["session"])
    resp = await client.post("/api/v1/auth/device/lookup", json={"userCode": "AAAA-AAAA"})
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "unknown_or_expired"


async def test_device_start_poll_approve(client, root_user):
    started = await client.post(
        "/api/v1/auth/device/start", json={"name": "claude-code@macmini"}
    )
    assert started.status_code == 200, started.text
    data = started.json()
    assert data["userCode"].count("-") == 1
    pending = await client.post(
        "/api/v1/auth/device/poll", json={"deviceCode": data["deviceCode"]}
    )
    assert pending.status_code == 428
    assert pending.json()["error"]["code"] == "authorization_pending"

    client.cookies.set("share_s", root_user["session"])
    looked = await client.post(
        "/api/v1/auth/device/lookup", json={"userCode": data["userCode"]}
    )
    assert looked.status_code == 200, looked.text
    assert looked.json()["name"] == "claude-code@macmini"

    approved = await client.post(
        "/api/v1/auth/device/approve", json={"userCode": data["userCode"]}
    )
    assert approved.status_code == 200, approved.text
    assert "token" not in approved.json()
    token_id = approved.json()["tokenId"]

    polled = await client.post(
        "/api/v1/auth/device/poll", json={"deviceCode": data["deviceCode"]}
    )
    assert polled.status_code == 200, polled.text
    assert polled.json()["token"].startswith("shr_")
    assert polled.json()["tokenId"] == token_id

    listed = await client.get("/api/v1/artifacts", headers={"Authorization": f"Bearer {polled.json()['token']}"})
    assert listed.status_code == 200
