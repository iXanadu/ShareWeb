"""Database pool and schema migrations via asyncpg."""

from pathlib import Path

import asyncpg
import structlog

from .config import get_settings

logger = structlog.get_logger()

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
_pool: asyncpg.Pool | None = None


async def get_migration_revision(conn: asyncpg.Connection) -> str | None:
    exists = await conn.fetchval(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'schema_migration'
        )
        """
    )
    if not exists:
        return None
    return await conn.fetchval(
        "SELECT revision FROM schema_migration ORDER BY applied_at DESC LIMIT 1"
    )


def _split_sql_statements(sql: str) -> list[str]:
    """Split a migration file into individual statements for asyncpg."""
    statements: list[str] = []
    current: list[str] = []
    for line in sql.splitlines():
        stripped = line.strip()
        if stripped.startswith("--") or not stripped:
            continue
        current.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
    if current:
        statement = "\n".join(current).strip()
        if statement:
            statements.append(statement)
    return statements


async def apply_migrations(conn: asyncpg.Connection) -> None:
    """Apply pending SQL migrations in lexical order."""
    applied = set()
    exists = await conn.fetchval(
        """
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'schema_migration'
        )
        """
    )
    if exists:
        rows = await conn.fetch("SELECT revision FROM schema_migration")
        applied = {row["revision"] for row in rows}

    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        revision = path.stem
        if revision in applied:
            continue
        statements = _split_sql_statements(path.read_text(encoding="utf-8"))
        async with conn.transaction():
            for statement in statements:
                await conn.execute(statement)
            await conn.execute(
                "INSERT INTO schema_migration (revision) VALUES ($1) ON CONFLICT DO NOTHING",
                revision,
            )
        logger.info("migration_applied", revision=revision)


async def init_pool() -> asyncpg.Pool:
    """Create the connection pool and run migrations."""
    global _pool
    settings = get_settings()
    _pool = await asyncpg.create_pool(
        dsn=settings.asyncpg_dsn,
        min_size=2,
        max_size=10,
    )
    async with _pool.acquire() as conn:
        await apply_migrations(conn)
    logger.info("database_pool_initialized", db=settings.db_name)
    return _pool


async def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool not initialized — call init_pool() first")
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("database_pool_closed")
