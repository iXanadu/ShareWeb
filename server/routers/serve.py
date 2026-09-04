"""Local artifact serving when Caddy is not in front (D-21)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Form, Request, Response
from fastapi.responses import FileResponse, RedirectResponse

from ..config import get_settings
from ..errors import NOT_FOUND_HEADERS, not_found_response
from ..services import sharing
from ..services.authorize import PasswordRequired, authorize_request

router = APIRouter(tags=["serve"])


@router.get("/robots.txt")
async def robots() -> Response:
    return Response(
        # Whole site open to crawlers and agents (owner call 2026-09-01).
        # Private shares are protected by per-response noindex, which only
        # works when the crawler is allowed to fetch the page.
        content="User-agent: *\nAllow: /\n",
        media_type="text/plain; charset=utf-8",
        headers={"Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow"},
    )


@router.post("/s/{token}/unlock")
async def unlock_share(token: str, request: Request, password: str = Form("")):
    row = await sharing.resolve_token(token)
    now = datetime.now(UTC)
    if row is None or row["revoked_at"] or row["expires_at"] < now:
        return not_found_response()
    if not row["password_hash"] or not sharing.verify_link_password(row["password_hash"], password):
        html = sharing.password_gate_html(token, wrong=True)
        return Response(content=html, status_code=401, media_type="text/html; charset=utf-8")
    _sid, cookie = await sharing.issue_recipient_session(
        row["id"], row["expires_at"], request.client.host if request.client else None
    )
    response = RedirectResponse(url=f"/s/{token}/", status_code=303)
    host = get_settings().host
    response.set_cookie(
        sharing.cookie_name(token),
        cookie,
        httponly=True,
        samesite="lax",
        path=f"/s/{token}",
        max_age=86400,
        secure="." in host and host not in {"localhost", "127.0.0.1"},
    )
    return response


@router.api_route("/{full_path:path}", methods=["GET", "HEAD"])
async def serve_artifact(full_path: str, request: Request):
    parts = [p for p in full_path.split("/") if p]
    if len(parts) == 2 and parts[0] == "s" and not str(request.url.path).endswith("/"):
        return RedirectResponse(url=f"/s/{parts[1]}/", status_code=308)
    result = await authorize_request(request)
    if isinstance(result, PasswordRequired):
        html = sharing.password_gate_html(result.token)
        return Response(
            content=html,
            status_code=401,
            media_type="text/html; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )
    if result is None:
        return not_found_response()
    if isinstance(result, (bytes, bytearray)):
        from ..services.markdown_view import GENERATED_HTML_CSP

        return Response(
            content=bytes(result),
            media_type="text/html; charset=utf-8",
            headers={
                "Cache-Control": "no-store",
                "Content-Security-Policy": GENERATED_HTML_CSP,
                **NOT_FOUND_HEADERS,
            },
        )
    headers = {
        "Cache-Control": result.cache_control,
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "X-Robots-Tag": "noindex, nofollow",
        "Permissions-Policy": "interest-cohort=()",
    }
    if result.csp:
        headers["Content-Security-Policy"] = result.csp
    if result.frame:
        headers["X-Frame-Options"] = result.frame
    if result.disposition:
        headers["Content-Disposition"] = result.disposition
    if not result.abs_path.is_file():
        return not_found_response()
    return FileResponse(
        result.abs_path,
        media_type=result.content_type,
        headers=headers,
    )
