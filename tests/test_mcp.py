"""Remote MCP JSON-RPC over HTTP."""


async def test_mcp_initialize_and_list(client, root_user):
    init = await client.post(
        "/mcp",
        headers=root_user["headers"],
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
        },
    )
    assert init.status_code == 200, init.text
    assert init.json()["result"]["serverInfo"]["name"] == "share"
    listed = await client.post(
        "/mcp",
        headers=root_user["headers"],
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    )
    names = {t["name"] for t in listed.json()["result"]["tools"]}
    assert "share_post" in names
    assert "share_list" in names
    assert "share_create_link" in names


async def test_mcp_post_and_list(client, root_user):
    posted = await client.post(
        "/mcp",
        headers=root_user["headers"],
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "share_post",
                "arguments": {
                    "name": "mcpnote",
                    "files": [{"path": "note.txt", "content": "hello from mcp"}],
                },
            },
        },
    )
    assert posted.status_code == 200, posted.text
    assert posted.json()["result"].get("isError") is not True
    listed = await client.post(
        "/mcp",
        headers=root_user["headers"],
        json={
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "share_list", "arguments": {}},
        },
    )
    body = listed.json()["result"]["content"][0]["text"]
    assert "mcpnote" in body


async def test_mcp_create_link(client, root_user, db_pool):
    from tests.test_artifacts import _post_hello

    await _post_hello(client, root_user["headers"], name="mcpshare")
    denied = await client.post(
        "/mcp",
        headers=root_user["headers"],
        json={
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {"name": "share_create_link", "arguments": {"name": "mcpshare", "ttl": "14d"}},
        },
    )
    assert denied.status_code == 200
    deny_text = denied.json()["result"]["content"][0]["text"]
    assert denied.json()["result"].get("isError") is True
    assert "insufficient_scope" in deny_text

    async with db_pool.acquire() as conn:
        await conn.execute(
            "UPDATE api_token SET scopes = array['artifacts:read','artifacts:write','share:create'] "
            "WHERE user_id = $1",
            root_user["user_id"],
        )
    created = await client.post(
        "/mcp",
        headers=root_user["headers"],
        json={
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {"name": "share_create_link", "arguments": {"name": "mcpshare", "ttl": "14d"}},
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["result"].get("isError") is not True
    payload = created.json()["result"]["content"][0]["text"]
    assert "/s/" in payload


async def test_mcp_get_sse(client, root_user):
    async with client.stream("GET", "/mcp", headers=root_user["headers"]) as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")
        lines = []
        async for line in resp.aiter_lines():
            lines.append(line)
            if any(x.startswith("event:") for x in lines):
                break
    assert any("ping" in x for x in lines)


async def test_mcp_get_unauthenticated_is_401_not_404(client):
    resp = await client.get("/mcp")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "invalid_token"
