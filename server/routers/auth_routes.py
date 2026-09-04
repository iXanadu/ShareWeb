"""Passkey ceremony routes at /auth/* (§4.2–4.3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse

from ..auth import Actor, require_passkey_session
from ..config import get_settings
from ..errors import ShareError
from ..services import passkeys, session_grants

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
async def register_begin(actor: Actor = Depends(require_passkey_session)) -> dict:
    return await passkeys.register_begin(actor)


@router.post("/passkey/register/finish")
async def register_finish(
    request: Request,
    response: Response,
    actor: Actor = Depends(require_passkey_session),
) -> dict:
    body = await request.json()
    credential = body.get("credential") or body
    name = body.get("name") or "Passkey"
    if not isinstance(credential, dict):
        raise ShareError(401, "webauthn_verification_failed", "That sign-in could not be verified.")
    result = await passkeys.register_finish(actor, credential, name)
    if actor.session_purpose == "recovery":
        response.set_cookie(
            "share_s",
            request.cookies["share_s"],
            httponly=True,
            secure=_secure_cookie(),
            samesite="lax",
            path="/",
            max_age=2592000,
        )
    return result


@router.get("/grant")
async def redeem_session_grant(request: Request, token: str = Query("")) -> RedirectResponse:
    redeemed = await session_grants.redeem(
        token,
        request.client.host if request.client else None,
        request.headers.get("user-agent"),
    )
    response = RedirectResponse(url="/~/security/passkeys/new", status_code=303)
    response.set_cookie(
        "share_s",
        redeemed["secret"],
        httponly=True,
        secure=_secure_cookie(),
        samesite="lax",
        path="/",
        max_age=redeemed["maxAge"],
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response
