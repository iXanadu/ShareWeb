"""FastAPI application factory with lifespan management."""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from . import __version__
from .config import get_settings
from .db import close_pool, init_pool
from .errors import RequestIdMiddleware, ShareError, share_error_handler
from .logging import setup_logging
from .routers import api, auth_routes, dashboard, health, internal, mcp, serve, v1


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(debug=settings.debug)
    logger = structlog.get_logger()
    logger.info("starting", version=__version__, host=settings.host, port=settings.port)
    await init_pool()
    yield
    await close_pool()
    logger.info("shutdown_complete")


app = FastAPI(
    title="Share",
    version=__version__,
    lifespan=lifespan,
)
app.add_middleware(RequestIdMiddleware)
app.add_exception_handler(ShareError, share_error_handler)

app.include_router(health.router)
app.include_router(internal.router)
app.include_router(auth_routes.router)
app.include_router(api.router)
app.include_router(v1.router)
app.include_router(mcp.router)
dashboard.mount_dashboard_static(app)
app.include_router(dashboard.router)
app.include_router(serve.router)  # last: artifact catch-all when Caddy is absent
