"""Public marketing pages at the base URL."""


async def test_marketing_home(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "Your agent" in resp.text
    assert "share_create_link" in resp.text
    assert "sw_live_" not in resp.text
    assert "/robert/" not in resp.text


async def test_marketing_inner_pages(client):
    how = await client.get("/how-it-works")
    assert how.status_code == 200
    assert "Declare the manifest" in how.text
    agents = await client.get("/for-agents")
    assert agents.status_code == 200
    assert "Bearer shr_" in agents.text
    assert "sw_live_" not in agents.text
    html = await client.get("/for-agents.html")
    assert html.status_code == 200


async def test_marketing_does_not_steal_artifacts(client, root_user):
    from tests.test_artifacts import _post_hello

    await _post_hello(client, root_user["headers"], name="shown")
    missing = await client.get("/no-such-artifact")
    assert missing.status_code == 404
    hidden = await client.get("/shown")
    assert hidden.status_code == 404
    assert missing.content == hidden.content


async def test_robots_allows_marketing(client):
    resp = await client.get("/robots.txt")
    assert resp.status_code == 200
    body = resp.text
    assert "Allow: /$" in body
    assert "Allow: /how-it-works" in body
    assert "Allow: /for-agents" in body
    assert "Disallow: /" in body
