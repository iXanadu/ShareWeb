"""Internal health and readiness endpoints (spec §2.8)."""

from pathlib import Path

import structlog
from fastapi import APIRouter, Request, Response

from .. import __version__
from ..config import get_settings
from ..db import get_migration_revision, get_pool

logger = structlog.get_logger()

router = APIRouter(prefix="/internal", tags=["internal"])

EXPECTED_MIGRATION = "002_session_grants"


def _is_loopback(client_host: str | None) -> bool:
    if not client_host:
        return False
    return client_host in {"127.0.0.1", "::1", "localhost"}


@router.api_route("/authorize", methods=["GET", "HEAD"])
async def internal_authorize(request: Request) -> Response:
    from ..services.authorize import internal_authorize as _authorize

    return await _authorize(request)


@router.get("/health")
async def internal_health(request: Request) -> Response:
    if not _is_loopback(request.client.host if request.client else None):
        return Response(status_code=403)
    return Response(content='{"status":"ok"}', media_type="application/json")


@router.get("/ready")
async def internal_ready(request: Request, response: Response) -> dict:
    if not _is_loopback(request.client.host if request.client else None):
        response.status_code = 403
        return {"status": "forbidden"}

    settings = get_settings()
    checks: dict[str, str] = {}

    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            revision = await get_migration_revision(conn)
            if revision == EXPECTED_MIGRATION:
                checks["postgres"] = "ok"
            else:
                checks["postgres"] = f"bad revision: {revision!r}, want {EXPECTED_MIGRATION}"
    except Exception as exc:
        checks["postgres"] = f"error: {exc}"

    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        try:
            pong = await client.ping()
            checks["redis"] = "ok" if pong else "no pong"
        finally:
            await client.aclose()
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    for label, path in (("file_root", settings.file_root), ("tmp_root", settings.tmp_root)):
        try:
            path.mkdir(parents=True, exist_ok=True)
            test_file = path / ".write_test"
            test_file.write_text("ok")
            test_file.unlink()
            if label == "tmp_root":
                file_root = Path(settings.file_root)
                file_root.mkdir(parents=True, exist_ok=True)
                if path.stat().st_dev != file_root.stat().st_dev:
                    checks[label] = "not same filesystem as file_root"
                    continue
            checks[label] = "ok"
        except Exception as exc:
            checks[label] = f"error: {exc}"

    all_ok = all(v == "ok" for v in checks.values())
    if not all_ok:
        response.status_code = 503
    return {
        "status": "ok" if all_ok else "degraded",
        "version": __version__,
        "checks": checks,
    }
