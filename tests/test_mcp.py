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
