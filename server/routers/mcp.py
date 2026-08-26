"""Remote MCP endpoint at /mcp (Part 9). JSON-RPC POST + SSE GET, bearer token."""

from __future__ import annotations

import base64
import hashlib
import json as json_mod
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from ..auth import Actor, require_user
from ..errors import ShareError
from ..services import artifacts as arts
from ..services import sharing

router = APIRouter(tags=["mcp"])

TOOLS = [
    {
        "name": "share_list",
        "description": "List artifacts in the caller's space.",
        "inputSchema": {
            "type": "object",
            "properties": {"trashed": {"type": "boolean"}},
        },
    },
    {
        "name": "share_get",
        "description": "Get one artifact by name.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "share_post",
        "description": (
            "Post files as an artifact. Small files inline. Posting does not make "
            "anything public — call share_create_link for a URL others can open. "
            "title and tags are how it will be found later."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "title": {"type": "string"},
                "files": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                            "contentBase64": {"type": "string"},
                            "contentType": {"type": "string"},
                        },
                        "required": ["path"],
                    },
                },
            },
            "required": ["files"],
        },
    },
    {
        "name": "share_delete",
        "description": "Move an artifact to trash.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "share_restore",
        "description": "Restore an artifact from trash.",
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "share_whoami",
        "description": "Return the authenticated identity.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "share_create_link",
        "description": (
            "Create an unguessable /s/ URL for an artifact so someone without an "
            "account can open it. External effect: anyone with the URL can view "
            "until it expires. Every link expires. Posting does not create a link."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "ttl": {"type": "string", "description": "14d, 24h, or 30m. Default 14d."},
                "password": {
                    "description": "true to generate one, or a string (>=8 chars).",
                    "oneOf": [{"type": "boolean"}, {"type": "string"}],
                },
                "label": {"type": "string"},
            },
            "required": ["name"],
        },
    },
]


def _ok(rpc_id, result) -> JSONResponse:
    return JSONResponse({"jsonrpc": "2.0", "id": rpc_id, "result": result})


def _err(rpc_id, code: int, message: str) -> JSONResponse:
    return JSONResponse(
        {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": code, "message": message}}
    )


async def _share_post(actor: Actor, args: dict, ip: str | None) -> dict:
    files_in = args.get("files") or []
    declared = []
    blobs: dict[str, bytes] = {}
    for item in files_in:
        if item.get("contentBase64"):
            data = base64.b64decode(item["contentBase64"])
        else:
            data = (item.get("content") or "").encode("utf-8")
        sha = hashlib.sha256(data).hexdigest()
        declared.append(
            {
                "path": item["path"],
                "size": len(data),
                "contentType": item.get("contentType") or "text/plain; charset=utf-8",
                "sha256": sha,
            }
        )
        blobs[sha] = data
    body: dict[str, Any] = {"files": declared}
    if args.get("name"):
        body["name"] = args["name"]
    if args.get("title"):
        body["title"] = args["title"]
    session = await arts.declare(actor, body, ip)
    from urllib.parse import parse_qs, urlparse

    for upload in session.get("uploads") or []:
        parsed = urlparse(upload["url"])
        qs = parse_qs(parsed.query)
        await arts.upload_file(
            upload["sha256"],
            qs["sid"][0],
            qs["exp"][0],
            qs["sig"][0],
            blobs[upload["sha256"]],
        )
    return await arts.commit(actor, session["name"], session["versionId"], ip)


async def _call(actor: Actor, name: str, args: dict, ip: str | None):
    args = args or {}
    if name == "share_list":
        return await arts.list_artifacts(actor, trashed=bool(args.get("trashed")))
    if name == "share_get":
        return await arts.get_artifact(actor, args["name"])
    if name == "share_post":
        return await _share_post(actor, args, ip)
    if name == "share_delete":
        await arts.trash(actor, args["name"], purge=False, request_ip=ip)
        return {"ok": True}
    if name == "share_restore":
        return await arts.restore(actor, args["name"], ip)
    if name == "share_whoami":
        return {"id": actor.user_id, "handle": actor.handle, "isRoot": actor.is_root}
    if name == "share_create_link":
        return await sharing.create_link(
            actor,
            args["name"],
            ttl=args.get("ttl"),
            label=args.get("label"),
            password=args.get("password"),
            request_ip=ip,
        )
    raise ShareError(404, "artifact_not_found", f"Unknown tool {name}")


@router.get("/mcp")
async def mcp_get(actor: Actor = Depends(require_user)):
    """Streamable-HTTP SSE channel. JSON-RPC still goes on POST /mcp."""

    async def events():
        yield "event: ping\ndata: {}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


@router.post("/mcp")
async def mcp_post(request: Request, actor: Actor = Depends(require_user)):
    payload = await request.json()
    rpc_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params") or {}
    if method == "initialize":
        return _ok(
            rpc_id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "share", "version": "0.1.0"},
            },
        )
    if method == "notifications/initialized":
        return JSONResponse({"jsonrpc": "2.0", "result": None})
    if method == "tools/list":
        return _ok(rpc_id, {"tools": TOOLS})
    if method == "tools/call":
        tool = params.get("name")
        arguments = params.get("arguments") or {}
        ip = request.client.host if request.client else None
        try:
            result = await _call(actor, tool, arguments, ip)
        except ShareError as exc:
            return _ok(
                rpc_id,
                {
                    "content": [{"type": "text", "text": f"{exc.code}: {exc.message}"}],
                    "isError": True,
                },
            )
        return _ok(
            rpc_id,
            {
                "content": [
                    {"type": "text", "text": json_mod.dumps(result, default=str)}
                ]
            },
        )
    return _err(rpc_id, -32601, f"Unknown method {method}")
