"""Application settings via pydantic-settings (spec §2.7)."""

from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SHARE_",
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT / ".keys"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Public hostname (also WebAuthn RP ID in production)
    host: str = "share.c52.com"
    bind_host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    log_level: str = "info"

    # Database
    database_url: str = ""
    db_host: str = ""  # empty → Unix socket (local peer auth)
    db_port: int = 5432
    db_name: str = "share_dev"
    db_user: str = "share"
    db_password: str = ""

    # Redis
    redis_url: str = "redis://127.0.0.1:6379/0"

    # Storage
    file_root: Path = Path("/var/lib/share/files")
    tmp_root: Path = Path("/var/lib/share/tmp")

    # Mail (required in production; optional for local API-only dev)
    smtp_url: str = ""
    mail_from: str = ""

    # Policy defaults (spec §2.7)
    default_share_ttl: str = "14d"
    max_share_ttl: str = "180d"
    trash_days: int = 30
    # Match WebOne nginx client_max_body_size 64M (Rob: 50MB is already a big file).
    max_artifact_bytes: int = 67_108_864  # 64 MiB
    max_file_bytes: int = 52_428_800  # 50 MiB
    max_files_per_version: int = 5000
    user_quota_bytes: int = 536_870_912_000

    # Credentials (from .keys)
    secret_key: str = ""
    view_salt: str = ""

    @property
    def dsn(self) -> str:
        if self.database_url:
            return self.database_url
        user = self.db_user
        name = self.db_name
        if not self.db_host:
            return f"postgresql://{user}@/{name}"
        if self.db_password:
            pw = quote_plus(self.db_password)
            return f"postgresql://{user}:{pw}@{self.db_host}:{self.db_port}/{name}"
        return f"postgresql://{user}@{self.db_host}:{self.db_port}/{name}"

    @property
    def asyncpg_dsn(self) -> str:
        """asyncpg expects postgresql:// without +asyncpg driver suffix."""
        url = self.dsn
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql://", 1)
        return url


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
