"""HTTP API /api/v1 — artifacts, files, commit."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import FileResponse, JSONResponse

from ..auth import Actor, require_user
from ..services import artifacts as arts
from ..services import device, passkeys, sharing, tokens

router = APIRouter(prefix="/api/v1", tags=["v1"])


@router.get("/me")
async def me(actor: Actor = Depends(require_user)):
    return {
        "id": actor.user_id,
        "handle": actor.handle,
        "isRoot": actor.is_root,
    }


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/artifacts")
async def declare_artifact(request: Request, actor: Actor = Depends(require_user)):
    body = await request.json()
    data = await arts.declare(actor, body, _ip(request))
    return JSONResponse(status_code=201, content=data)


@router.post("/artifacts/{name:path}/versions/{version_id}/commit")
async def commit_version(
    name: str,
    version_id: str,
    request: Request,
    actor: Actor = Depends(require_user),
):
    return await arts.commit(actor, name, version_id, _ip(request))


@router.get("/artifacts")
async def list_artifacts(
    actor: Actor = Depends(require_user),
    trashed: bool = Query(False),
):
    return await arts.list_artifacts(actor, trashed=trashed)


@router.get("/artifacts/{name:path}/files/content")
async def artifact_file_content(
    name: str,
    actor: Actor = Depends(require_user),
    path: str = Query(...),
    version: str | None = Query(None),
):
    blob, content_type = await arts.file_bytes(actor, name, path, version)
    return FileResponse(blob, media_type=content_type)


@router.post("/artifacts/{name:path}/links")
async def create_share_link(
    name: str,
    request: Request,
    actor: Actor = Depends(require_user),
):
    body = await request.json()
    data = await sharing.create_link(
        actor,
        name,
        ttl=body.get("ttl"),
        label=body.get("label"),
        password=body.get("password"),
        request_ip=_ip(request),
    )
    return JSONResponse(status_code=201, content=data)


@router.get("/artifacts/{name:path}/files")
async def artifact_files(
    name: str,
    actor: Actor = Depends(require_user),
    version: str | None = Query(None),
):
    return await arts.list_files(actor, name, version)


@router.get("/artifacts/{name:path}")
async def get_artifact(name: str, actor: Actor = Depends(require_user)):
    return await arts.get_artifact(actor, name)


@router.delete("/artifacts/{name:path}")
async def delete_artifact(
    name: str,
    request: Request,
    actor: Actor = Depends(require_user),
    purge: bool = Query(False),
):
    await arts.trash(actor, name, purge=purge, request_ip=_ip(request))
    return Response(status_code=204)


@router.post("/artifacts/{name:path}/restore")
async def restore_artifact(
    name: str,
    request: Request,
    actor: Actor = Depends(require_user),
):
    return await arts.restore(actor, name, _ip(request))


@router.get("/tokens")
async def list_tokens(actor: Actor = Depends(require_user)):
    return await tokens.list_tokens(actor)


@router.post("/tokens")
async def create_token(request: Request, actor: Actor = Depends(require_user)):
    body = await request.json()
    data = await tokens.create_token(
        actor, body.get("name") or "", body.get("scopes") or [], _ip(request)
    )
    return JSONResponse(status_code=201, content=data)


@router.delete("/tokens/{token_id}")
async def delete_token(token_id: str, request: Request, actor: Actor = Depends(require_user)):
    await tokens.revoke_token(actor, token_id, _ip(request))
    return Response(status_code=204)


@router.get("/auth/passkeys")
async def list_passkeys(actor: Actor = Depends(require_user)):
    return await passkeys.list_passkeys(actor)


@router.post("/auth/device/start")
async def device_start(request: Request):
    body = await request.json()
    return await device.start(
        body.get("name") or "",
        _ip(request),
        request.headers.get("user-agent"),
    )


@router.post("/auth/device/poll")
async def device_poll(request: Request):
    body = await request.json()
    return await device.poll(body.get("deviceCode") or "")


@router.post("/auth/device/lookup")
async def device_lookup(request: Request, actor: Actor = Depends(require_user)):
    body = await request.json()
    return await device.lookup(body.get("userCode") or "")


@router.post("/auth/device/approve")
async def device_approve(request: Request, actor: Actor = Depends(require_user)):
    body = await request.json()
    return await device.approve(actor, body.get("userCode") or "", _ip(request))


@router.post("/auth/device/deny")
async def device_deny(request: Request, actor: Actor = Depends(require_user)):
    body = await request.json()
    return await device.deny(body.get("userCode") or "")


@router.put("/files/{sha256}")
async def put_file(
    sha256: str,
    request: Request,
    sid: str,
    exp: str,
    sig: str,
):
    data = await request.body()
    return await arts.upload_file(sha256, sid, exp, sig, data)
