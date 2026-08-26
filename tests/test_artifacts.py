"""Phase 1: post, open, P1 indistinguishability, trash."""

from __future__ import annotations

import hashlib


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_ready(client):
    resp = await client.get("/internal/ready")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ok"
    assert body["checks"]["postgres"] == "ok"
    assert body["checks"]["redis"] == "ok"


async def _post_hello(client, headers, name="hello"):
    body = b"<html><body>hi</body></html>"
    sha = hashlib.sha256(body).hexdigest()
    declared = await client.post(
        "/api/v1/artifacts",
        headers=headers,
        json={
            "name": name,
            "title": "Hello",
            "files": [
                {
                    "path": "index.html",
                    "size": len(body),
                    "contentType": "text/html",
                    "sha256": sha,
                }
            ],
        },
    )
    assert declared.status_code == 201, declared.text
    data = declared.json()
    if data["uploads"]:
        from urllib.parse import urlparse

        url = data["uploads"][0]["url"]
        parsed = urlparse(url)
        put = await client.put(f"{parsed.path}?{parsed.query}", content=body)
        assert put.status_code == 200, put.text
    committed = await client.post(
        f"/api/v1/artifacts/{name}/versions/{data['versionId']}/commit",
        headers=headers,
    )
    assert committed.status_code == 200, committed.text
    return committed.json(), body


async def test_post_and_open(client, root_user):
    result, body = await _post_hello(client, root_user["headers"])
    assert result["name"] == "hello"
    assert result["visibility"] == "private"
    assert result["url"].endswith("/hello")

    forbidden = await client.get("/hello")
    assert forbidden.status_code == 404

    allowed = await client.get("/hello", cookies={"share_s": root_user["session"]})
    assert allowed.status_code == 200
    assert b"hi" in allowed.content


async def test_priv01_identical_404(client, root_user):
    await _post_hello(client, root_user["headers"], name="secret")
    missing = await client.get("/no-such-artifact")
    hidden = await client.get("/secret")
    assert missing.status_code == 404
    assert hidden.status_code == 404
    assert missing.content == hidden.content
    assert missing.headers.get("cache-control") == hidden.headers.get("cache-control")


async def test_trash_hides_artifact(client, root_user):
    await _post_hello(client, root_user["headers"], name="gone")
    deleted = await client.delete("/api/v1/artifacts/gone", headers=root_user["headers"])
    assert deleted.status_code == 204
    listed = await client.get("/api/v1/artifacts", headers=root_user["headers"])
    assert all(item["name"] != "gone" for item in listed.json()["items"])
    opened = await client.get("/gone", cookies={"share_s": root_user["session"]})
    assert opened.status_code == 404
    restored = await client.post("/api/v1/artifacts/gone/restore", headers=root_user["headers"])
    assert restored.status_code == 200
    opened2 = await client.get("/gone", cookies={"share_s": root_user["session"]})
    assert opened2.status_code == 200
