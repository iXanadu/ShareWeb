"""Public marketing pages at the base URL."""


async def test_marketing_home(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert "Your agent" in resp.text
    assert "share_create_link" in resp.text
    assert "BACKLOG.md" in resp.text
    assert "START-HERE" not in resp.text
    assert "16-roadmap" not in resp.text
    assert "commits/main" not in resp.text
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
    server = await client.get("/your-server")
    assert server.status_code == 200
    assert "Your own server" in server.text
    assert "sw_live_" not in server.text
    assert "PostgreSQL" in server.text
    slash = await client.get("/your-server/", follow_redirects=False)
    assert slash.status_code == 308


async def test_marketing_does_not_steal_artifacts(client, root_user):
    from tests.test_artifacts import _post_hello

    await _post_hello(client, root_user["headers"], name="shown")
    missing = await client.get("/no-such-artifact")
    assert missing.status_code == 404
    hidden = await client.get("/shown")
    assert hidden.status_code == 404
    assert missing.content == hidden.content


async def test_robots_allows_whole_site(client):
    resp = await client.get("/robots.txt")
    assert resp.status_code == 200
    body = resp.text
    assert "User-agent: *" in body
    assert "Allow: /" in body
    assert "Disallow" not in body


async def test_marketing_assets(client):
    css = await client.get("/site.css")
    assert css.status_code == 200
    assert "text/css" in css.headers.get("content-type", "")
    hero = await client.get("/assets/01-hero-rook-nest.jpg")
    assert hero.status_code == 200
    assert hero.headers.get("content-type", "").startswith("image/")
    fav = await client.get("/favicon.png")
    assert fav.status_code == 200
