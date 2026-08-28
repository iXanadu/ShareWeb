"""Public marketing pages at /, /how-it-works, /for-agents, /your-server."""

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

WEB_ROOT = Path(__file__).resolve().parent.parent.parent / "web" / "marketing"
ASSETS_ROOT = WEB_ROOT / "assets"

router = APIRouter(tags=["marketing"])


def _page(name: str) -> FileResponse:
    return FileResponse(WEB_ROOT / name, media_type="text/html; charset=utf-8")


def _file(name: str, media: str) -> FileResponse:
    return FileResponse(WEB_ROOT / name, media_type=media)


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


@router.get("/your-server/")
async def marketing_server_slash() -> RedirectResponse:
    return RedirectResponse(url="/your-server", status_code=308)


@router.get("/your-server")
@router.get("/your-server.html")
async def marketing_server() -> FileResponse:
    return _page("your-server.html")


@router.get("/site.css")
async def marketing_css() -> FileResponse:
    return _file("site.css", "text/css; charset=utf-8")


@router.get("/favicon.png")
@router.get("/favicon.ico")
async def marketing_favicon() -> FileResponse:
    return _file("favicon.png", "image/png")


@router.get("/apple-touch-icon.png")
async def marketing_apple_icon() -> FileResponse:
    return _file("apple-touch-icon.png", "image/png")


@router.get("/author-avatar.png")
async def marketing_avatar() -> FileResponse:
    return _file("author-avatar.png", "image/png")


def mount_marketing_static(app) -> None:
    app.mount("/assets", StaticFiles(directory=ASSETS_ROOT), name="marketing-assets")
