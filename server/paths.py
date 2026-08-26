"""Name and file-path rules (§5.3, §6.3, §6.4)."""

from __future__ import annotations

import re
import unicodedata

from .errors import ShareError

RESERVED_FIRST_SEGMENTS = {
    "~",
    "s",
    "api",
    "mcp",
    "auth",
    "internal",
    ".well-known",
    "robots.txt",
    "favicon.ico",
    "install.sh",
    "health",
    "how-it-works",
    "for-agents",
}

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*(/[a-z0-9][a-z0-9._-]*)*$")


def normalize_name(name: str) -> str:
    lowered = name.strip().lower()
    if not lowered or lowered.endswith("/") or ".." in lowered or "//" in lowered:
        raise ShareError(422, "invalid_name", "That name is not allowed.")
    if lowered.count("/") > 7 or len(lowered) > 200:
        raise ShareError(422, "invalid_name", "That name is not allowed.")
    if not NAME_RE.match(lowered):
        raise ShareError(422, "invalid_name", "That name is not allowed.")
    first = lowered.split("/", 1)[0]
    if first in RESERVED_FIRST_SEGMENTS:
        raise ShareError(422, "name_reserved", "That name is reserved.", {"name": lowered})
    return lowered


def normalize_file_path(raw: str) -> str:
    if raw is None:
        raise ShareError(422, "invalid_path", "A file path is required.")
    text = raw.replace("\\", "/")
    if "%" in text:
        # Decode once; residual % is an attack.
        from urllib.parse import unquote

        decoded = unquote(text)
        if "%" in decoded:
            raise ShareError(422, "invalid_path", "Double-encoded path rejected.")
        text = decoded
    if "\x00" in text or any(ord(ch) < 0x20 for ch in text):
        raise ShareError(422, "invalid_path", "Control characters are not allowed in paths.")
    text = unicodedata.normalize("NFC", text)
    if any(unicodedata.category(ch) == "Cf" for ch in text):
        raise ShareError(422, "invalid_path", "Format characters are not allowed in paths.")
    if text.startswith("/"):
        text = text
    else:
        text = "/" + text
    text = text.rstrip("/") or "/"
    if text != "/":
        segments = text.split("/")[1:]
    else:
        segments = []
    if len(text.encode("utf-8")) > 1024 or len(segments) > 32:
        raise ShareError(422, "invalid_path", "Path is too long.")
    for seg in segments:
        if not seg or seg in {".", ".."} or re.match(r"^[a-zA-Z]:", seg):
            raise ShareError(422, "invalid_path", "Path contains an illegal segment.")
        if len(seg.encode("utf-8")) > 255:
            raise ShareError(422, "invalid_path", "A path segment is too long.")
    if segments and segments[0].startswith(".") and "/".join(segments[:1]) != ".well-known":
        raise ShareError(
            422,
            "dotfile_rejected",
            "Dotfile paths are rejected.",
            {"path": text},
        )
    return text if text != "/" else text


def check_case_collisions(paths: list[str]) -> None:
    seen: dict[str, str] = {}
    for path in paths:
        key = path.lower()
        if key in seen and seen[key] != path:
            raise ShareError(
                422,
                "path_case_collision",
                "Two paths differ only by case.",
                {"paths": [seen[key], path]},
            )
        seen[key] = path
