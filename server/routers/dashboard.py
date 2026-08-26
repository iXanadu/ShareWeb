"""Dashboard SPA — serves /~/* (spec §11)."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

WEB_ROOT = Path(__file__).resolve().parent.parent.parent / "web"
STATIC_ROOT = WEB_ROOT / "static"
INDEX = WEB_ROOT / "index.html"

router = APIRouter(tags=["dashboard"])


@router.get("/~")
@router.get("/~/{path:path}")
async def dashboard_spa(path: str = "") -> FileResponse:
    """Single-page app shell for all dashboard routes."""
    return FileResponse(INDEX, media_type="text/html")


def mount_dashboard_static(app) -> None:
    """Mount static assets; call after router registration."""
    app.mount(
        "/~/static",
        StaticFiles(directory=STATIC_ROOT),
        name="dashboard-static",
    )
