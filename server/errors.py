"""API error envelope (§5.1.1) and frozen not-found page (P1)."""

from __future__ import annotations

from pathlib import Path

from fastapi import Request
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_NOT_FOUND_PATH = PROJECT_ROOT / "docs" / "specs" / "recipient" / "R4-not-found.html"

NOT_FOUND_HEADERS = {
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Robots-Tag": "noindex, nofollow",
    "Permissions-Policy": "interest-cohort=()",
}


def not_found_html() -> str:
    if _NOT_FOUND_PATH.is_file():
        return _NOT_FOUND_PATH.read_text(encoding="utf-8")
    return (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        "<title>share</title></head><body><p>Not found.</p></body></html>"
    )


def not_found_response() -> Response:
    return Response(
        content=not_found_html(),
        status_code=404,
        media_type="text/html; charset=utf-8",
        headers=dict(NOT_FOUND_HEADERS),
    )


class ShareError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        detail: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.detail = detail or {}


async def share_error_handler(request: Request, exc: ShareError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None) or request.headers.get(
        "x-share-request-id", "req_unknown"
    )
    return JSONResponse(
        status_code=exc.status,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "detail": exc.detail,
                "requestId": request_id,
            }
        },
        headers={
            "X-Share-Request-Id": request_id,
            "X-Share-Api-Version": "1",
        },
    )


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        from .ids import prefixed

        request_id = request.headers.get("x-share-request-id") or prefixed("req")
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers.setdefault("X-Share-Request-Id", request_id)
        response.headers.setdefault("X-Share-Api-Version", "1")
        return response
