"""Verify health endpoint responds."""



async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


async def test_internal_health(client):
    resp = await client.get("/internal/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_internal_ready(client):
    resp = await client.get("/internal/ready")
    # 200 if all deps ok, 503 if postgres/redis not provisioned yet
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "checks" in data
    assert "postgres" in data["checks"]
