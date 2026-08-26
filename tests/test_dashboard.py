"""Dashboard SPA routes under /~/*."""


async def test_dashboard_signin(client):
    resp = await client.get("/~/signin")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "")
    assert 'id="app"' in resp.text
    assert "/~/static/app.js" in resp.text


async def test_dashboard_static_css(client):
    resp = await client.get("/~/static/share.css")
    assert resp.status_code == 200
    assert "share-signin" in resp.text


async def test_dashboard_spa_fallback(client):
    resp = await client.get("/~/artifacts")
    assert resp.status_code == 200
    assert "share-app" in resp.text
