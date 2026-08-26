"""Local tree walk for `share post` (§9.4.2)."""

from __future__ import annotations

import hashlib
import mimetypes
import os
from pathlib import Path

SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    ".terraform",
    ".idea",
    ".vscode",
}
SKIP_FILE_NAMES = {".DS_Store", "Thumbs.db"}
SECRET_SUFFIXES = {".pem", ".key", ".p12", ".keystore"}
SECRET_NAMES = {".env", "credentials", ".netrc"}


class SecretFileError(Exception):
    def __init__(self, path: Path) -> None:
        super().__init__(f"refusing to post secret file: {path}")
        self.path = path


def _is_secret(path: Path) -> bool:
    name = path.name
    if name == ".env" or name.startswith(".env."):
        return True
    if name in SECRET_NAMES or name.startswith("id_rsa"):
        return True
    if path.suffix.lower() in SECRET_SUFFIXES:
        return True
    return False


def walk_files(root: Path, *, force_secrets: bool = False) -> list[dict]:
    root = root.resolve()
    files: list[dict] = []
    if root.is_file():
        paths = [root]
        base = root.parent
    else:
        paths = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES and d != ".next"]
            for name in filenames:
                if name in SKIP_FILE_NAMES or name.endswith(".pyc"):
                    continue
                paths.append(Path(dirpath) / name)
        base = root
    for path in paths:
        if path.is_symlink():
            continue
        if not path.is_file():
            continue
        if _is_secret(path) and not force_secrets:
            raise SecretFileError(path)
        rel = path.name if root.is_file() else path.relative_to(base).as_posix()
        data = path.read_bytes()
        ctype, _ = mimetypes.guess_type(path.name)
        files.append(
            {
                "path": rel,
                "size": len(data),
                "contentType": ctype or "application/octet-stream",
                "sha256": hashlib.sha256(data).hexdigest(),
                "bytes": data,
            }
        )
    if not files:
        raise FileNotFoundError(f"no files to post under {root}")
    return files
