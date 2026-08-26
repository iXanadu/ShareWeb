"""Public marketing pages at /, /how-it-works, /for-agents."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

WEB_ROOT = Path(__file__).resolve().parent.parent.parent / "web" / "marketing"

router = APIRouter(tags=["marketing"])


def _page(name: str) -> FileResponse:
    return FileResponse(WEB_ROOT / name, media_type="text/html; charset=utf-8")


@router.get("/")
async def marketing_home() -> FileResponse:
    return _page("index.html")


@router.get("/index.html")
async def marketing_index_html() -> FileResponse:
    return _page("index.html")


@router.get("/how-it-works")
@router.get("/how-it-works.html")
async def marketing_how() -> FileResponse:
    return _page("how-it-works.html")


@router.get("/for-agents")
@router.get("/for-agents.html")
async def marketing_agents() -> FileResponse:
    return _page("for-agents.html")
