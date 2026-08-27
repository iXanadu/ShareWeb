"""Shared test fixtures — function-scoped DB pool, async HTTP client."""

import hashlib
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Must run before server.config is imported.
ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("SHARE_HOST", "localhost")
os.environ.setdefault("SHARE_PORT", "8000")
os.environ.setdefault("SHARE_DB_USER", os.environ.get("USER", "dev"))
os.environ.setdefault("SHARE_DB_NAME", "share_test")
os.environ.setdefault("SHARE_DB_PASSWORD", "")
os.environ.setdefault("SHARE_REDIS_URL", "redis://127.0.0.1:6379/1")
os.environ.setdefault("SHARE_FILE_ROOT", str(ROOT / "var" / "share-test" / "files"))
os.environ.setdefault("SHARE_TMP_ROOT", str(ROOT / "var" / "share-test" / "tmp"))
os.environ.setdefault("SHARE_SECRET_KEY", "test-secret-key-not-for-prod")
os.environ.setdefault("SHARE_VIEW_SALT", "test-view-salt-not-for-prod")
os.environ.setdefault("SHARE_DEBUG", "true")

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

import server.config as config_mod  # noqa: E402
from server.config import get_settings  # noqa: E402

config_mod._settings = None
get_settings()


@pytest_asyncio.fixture
async def services():
    from server.db import close_pool, init_pool
    from server.services.store import ensure_roots

    ensure_roots()
    pool = await init_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            TRUNCATE
              link_viewer_day, recipient_session, share_grant, share_link,
              artifact_tag, version_file, upload_session,
              idempotency_record, view_daily, audit_event,
              artifact_version, artifact, file,
              api_token, session, recovery_code, passkey_credential,
              invite, app_user
            RESTART IDENTITY CASCADE
            """
        )
    yield
    await close_pool()


@pytest_asyncio.fixture
async def client(services):
    from server.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def db_pool(services):
    from server.db import get_pool

    return await get_pool()


@pytest_asyncio.fixture
async def root_user(db_pool):
    from server.ids import new_api_token_secret, new_session_secret, prefixed

    secret = new_api_token_secret()
    session_secret = new_session_secret()
    user_id = prefixed("usr")
    token_id = prefixed("shr")
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO app_user (id, email, handle, is_root)
            VALUES ($1, 'root@example.com', 'robert', true)
            """,
            user_id,
        )
        await conn.execute(
            """
            INSERT INTO api_token (id, user_id, name, display_prefix, token_hash, scopes)
            VALUES ($1,$2,'test',$3,$4,$5)
            """,
            token_id,
            user_id,
            secret[:12],
            hashlib.sha256(secret.encode()).digest(),
            ["artifacts:read", "artifacts:write", "artifacts:delete"],
        )
        await conn.execute(
            """
            INSERT INTO session (id, user_id, token_hash, expires_at)
            VALUES ($1,$2,$3,$4)
            """,
            prefixed("ses"),
            user_id,
            hashlib.sha256(session_secret.encode()).digest(),
            datetime.now(UTC) + timedelta(days=1),
        )
    return {
        "user_id": user_id,
        "token": secret,
        "session": session_secret,
        "headers": {"Authorization": f"Bearer {secret}"},
    }
