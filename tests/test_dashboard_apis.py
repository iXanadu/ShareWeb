"""Files, tokens, and passkey list for the dashboard."""


async def test_list_files_and_content(client, root_user):
    from tests.test_artifacts import _post_hello

    await _post_hello(client, root_user["headers"], name="docs")
    listed = await client.get("/api/v1/artifacts/docs/files", headers=root_user["headers"])
    assert listed.status_code == 200, listed.text
    items = listed.json()["items"]
    assert items[0]["path"] == "/index.html"
    content = await client.get(
        "/api/v1/artifacts/docs/files/content",
        headers=root_user["headers"],
        params={"path": "/index.html"},
    )
    assert content.status_code == 200
    assert b"hi" in content.content


async def test_tokens_create_list_revoke(client, root_user):
    client.cookies.set("share_s", root_user["session"])
    created = await client.post(
        "/api/v1/tokens",
        json={"name": "laptop", "scopes": ["artifacts:read", "artifacts:write"]},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["token"].startswith("shr_")
    token_id = body["tokenId"]
    listed = await client.get("/api/v1/tokens")
    assert any(item["id"] == token_id for item in listed.json()["items"])
    deleted = await client.delete(f"/api/v1/tokens/{token_id}")
    assert deleted.status_code == 204
    listed2 = await client.get("/api/v1/tokens")
    assert all(item["id"] != token_id for item in listed2.json()["items"])


async def test_passkeys_list_empty(client, root_user):
    client.cookies.set("share_s", root_user["session"])
    resp = await client.get("/api/v1/auth/passkeys")
    assert resp.status_code == 200, resp.text
    assert resp.json()["items"] == []
