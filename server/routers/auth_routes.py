"""Passkey ceremony routes at /auth/* (§4.2–4.3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response

from ..auth import Actor, require_user
from ..config import get_settings
from ..errors import ShareError
from ..services import passkeys

router = APIRouter(prefix="/auth", tags=["auth"])


def _secure_cookie() -> bool:
    host = get_settings().host
    return "." in host and host not in {"localhost", "127.0.0.1"}


@router.post("/passkey/login/begin")
async def login_begin() -> dict:
    return await passkeys.login_begin()


@router.post("/passkey/login/finish")
async def login_finish(request: Request, response: Response) -> dict:
    body = await request.json()
    credential = body.get("credential") or body
    user, secret = await passkeys.login_finish(credential)
    response.set_cookie(
        "share_s",
        secret,
        httponly=True,
        secure=_secure_cookie(),
        samesite="lax",
        path="/",
        max_age=2592000,
    )
    return {"user": user}


@router.post("/passkey/register/begin")
async def register_begin(actor: Actor = Depends(require_user)) -> dict:
    return await passkeys.register_begin(actor)


@router.post("/passkey/register/finish")
async def register_finish(request: Request, actor: Actor = Depends(require_user)) -> dict:
    body = await request.json()
    credential = body.get("credential") or body
    name = body.get("name") or "Passkey"
    if not isinstance(credential, dict):
        raise ShareError(401, "webauthn_verification_failed", "That sign-in could not be verified.")
    return await passkeys.register_finish(actor, credential, name)
