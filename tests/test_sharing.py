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


async def test_share_link_download_button_for_non_html(client, root_user):
    import hashlib

    body = b"deed text"
    sha = hashlib.sha256(body).hexdigest()
    declared = await client.post(
        "/api/v1/artifacts",
        headers=root_user["headers"],
        json={
            "name": "deed",
            "title": "Sleepy Hole Deed",
            "files": [
                {
                    "path": "deed.txt",
                    "size": len(body),
                    "contentType": "text/plain; charset=utf-8",
                    "sha256": sha,
                }
            ],
        },
    )
    assert declared.status_code == 201, declared.text
    data = declared.json()
    from urllib.parse import urlparse

    url = data["uploads"][0]["url"]
    parsed = urlparse(url)
    put = await client.put(f"{parsed.path}?{parsed.query}", content=body)
    assert put.status_code == 200, put.text
    committed = await client.post(
        f"/api/v1/artifacts/deed/versions/{data['versionId']}/commit",
        headers=root_user["headers"],
    )
    assert committed.status_code == 200, committed.text
    client.cookies.set("share_s", root_user["session"])
    created = await client.post(
        "/api/v1/artifacts/deed/links",
        json={"ttl": "14d", "label": "download-me"},
    )
    assert created.status_code == 201, created.text
    token = created.json()["url"].rstrip("/").rsplit("/s/", 1)[-1]
    landing = await client.get(f"/s/{token}/")
    assert landing.status_code == 200
    assert "text/html" in landing.headers.get("content-type", "")
    assert b"Download" in landing.content
    assert b"View" in landing.content
    assert b"?download=1" in landing.content
    dl = await client.get(f"/s/{token}/?download=1")
    assert dl.status_code == 200
    assert dl.headers.get("content-disposition", "").startswith("attachment")
    assert b"deed text" in dl.content
    viewed = await client.get(f"/s/{token}/deed.txt")
    assert viewed.status_code == 200
    assert viewed.content == body


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
