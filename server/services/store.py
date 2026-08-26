"""Content-addressed file store (§3.5)."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from ..config import get_settings
from ..errors import ShareError


def blob_relpath(sha_hex: str) -> str:
    return f"{sha_hex[:2]}/{sha_hex[2:4]}/{sha_hex}"


def blob_abs(sha_hex: str) -> Path:
    settings = get_settings()
    return Path(settings.file_root) / sha_hex[:2] / sha_hex[2:4] / sha_hex


def ensure_roots() -> None:
    settings = get_settings()
    Path(settings.file_root).mkdir(parents=True, exist_ok=True)
    Path(settings.tmp_root).mkdir(parents=True, exist_ok=True)


async def write_blob(expected_sha: str, expected_size: int, data: bytes) -> str:
    ensure_roots()
    settings = get_settings()
    if len(data) != expected_size:
        raise ShareError(
            400,
            "file_size_mismatch",
            "Uploaded length differs from the declared size.",
            {"expected": expected_size, "actual": len(data)},
        )
    digest = hashlib.sha256(data).hexdigest()
    if digest != expected_sha:
        quarantine = Path(settings.tmp_root).parent / "quarantine"
        quarantine.mkdir(parents=True, exist_ok=True)
        (quarantine / digest).write_bytes(data)
        raise ShareError(
            400,
            "file_hash_mismatch",
            "Uploaded bytes do not match the digest in the URL.",
        )
    dest = blob_abs(digest)
    if dest.exists():
        return digest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(settings.tmp_root) / f"{os.urandom(8).hex()}.part"
    tmp.write_bytes(data)
    os.replace(tmp, dest)
    return digest
