"""No-password share links."""


async def test_share_link_without_password(client, root_user):
    from tests.test_artifacts import _post_hello

    await _post_hello(client, root_user["headers"], name="shown")
    # bootstrap-style token has no share:create
    denied = await client.post(
        "/api/v1/artifacts/shown/links",
        headers=root_user["headers"],
        json={"ttl": "14d", "label": "review"},
    )
    assert denied.status_code == 403

    client.cookies.set("share_s", root_user["session"])
    created = await client.post(
        "/api/v1/artifacts/shown/links",
        json={"ttl": "14d", "label": "review"},
    )
    assert created.status_code == 201, created.text
    url = created.json()["url"]
    token = url.rstrip("/").rsplit("/s/", 1)[-1]
    anonymous = await client.get(f"/s/{token}/")
    assert anonymous.status_code == 200
    assert b"hi" in anonymous.content
    missing = await client.get("/s/notarealtokenvaluezzzz/")
    assert missing.status_code == 404


async def test_share_link_with_password(client, root_user):
    from tests.test_artifacts import _post_hello

    await _post_hello(client, root_user["headers"], name="locked")
    client.cookies.set("share_s", root_user["session"])
    created = await client.post(
        "/api/v1/artifacts/locked/links",
        json={"ttl": "14d", "password": True, "label": "pw-review"},
    )
    assert created.status_code == 201, created.text
    password = created.json()["password"]
    assert "-" in password
    token = created.json()["url"].rstrip("/").rsplit("/s/", 1)[-1]
    gated = await client.get(f"/s/{token}/")
    assert gated.status_code == 401
    assert b"password" in gated.content.lower()
    bad = await client.post(f"/s/{token}/unlock", data={"password": "nope-nope-00"})
    assert bad.status_code == 401
    ok = await client.post(f"/s/{token}/unlock", data={"password": password})
    assert ok.status_code in {200, 303}
    opened = await client.get(f"/s/{token}/")
    assert opened.status_code == 200
    assert b"hi" in opened.content
