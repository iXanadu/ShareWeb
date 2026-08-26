"""Artifact post, read, trash, restore (Phase 1)."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from ..auth import Actor, public_base_url
from ..config import get_settings
from ..db import get_pool
from ..errors import ShareError
from ..ids import prefixed
from ..names import generate_name
from ..paths import check_case_collisions, normalize_file_path, normalize_name
from . import audit, store

_SHA_RE = __import__("re").compile(r"^[0-9a-f]{64}$")

EXT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".mjs": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".avif": "image/avif",
    ".pdf": "application/pdf",
    ".json": "application/json",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/plain; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
    ".woff2": "font/woff2",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mov": "video/quicktime",
    ".mp3": "audio/mpeg",
    ".m4a": "audio/mp4",
    ".wav": "audio/wav",
    ".wasm": "application/wasm",
}


def _content_type(path: str, declared: str | None) -> str:
    ext = os.path.splitext(path)[1].lower()
    if declared:
        if ext in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif", ".woff2", ".mp4", ".webm"}:
            if declared.startswith("text/html"):
                return EXT_TYPES.get(ext, declared)
        return declared
    return EXT_TYPES.get(ext, "application/octet-stream")


def _kind_from_files(files: list[dict]) -> str:
    if len(files) > 1:
        return "bundle"
    path = files[0]["path"]
    ctype = files[0]["contentType"]
    ext = os.path.splitext(path)[1].lower()
    if ext in {".html", ".htm"} or ctype.startswith("text/html"):
        return "page"
    if ext in {".pdf", ".doc", ".docx"} or "pdf" in ctype:
        return "document"
    if ctype.startswith("image/") or ext in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}:
        return "image"
    if ctype.startswith("video/") or ext in {".mp4", ".webm", ".mov"}:
        return "video"
    return "file"


def _entry_path(files: list[dict], requested: str | None) -> tuple[str | None, list[dict]]:
    warnings: list[dict] = []
    paths = {f["path"] for f in files}
    if requested:
        norm = normalize_file_path(requested)
        if norm in paths:
            return norm, warnings
        warnings.append(
            {
                "code": "entry_path_not_found",
                "message": "entryPath was not in the manifest; another file was chosen.",
            }
        )
    if "/index.html" in paths:
        return "/index.html", warnings
    html = [f["path"] for f in files if f["path"].endswith((".html", ".htm"))]
    if len(html) == 1:
        return html[0], warnings
    if len(files) == 1:
        return files[0]["path"], warnings
    warnings.append(
        {"code": "no_entry_point", "message": "No entry file; the root will show a listing."}
    )
    return None, warnings


def _sign_upload(sha: str, sid: str, exp: int) -> str:
    key = get_settings().secret_key.encode("utf-8")
    msg = f"{sha}|{sid}|{exp}".encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def verify_upload_sig(sha: str, sid: str, exp: str, sig: str) -> None:
    try:
        exp_i = int(exp)
    except ValueError as exc:
        raise ShareError(403, "upload_signature_invalid", "Upload URL is invalid.") from exc
    if exp_i < int(time.time()):
        raise ShareError(403, "upload_signature_invalid", "Upload URL is invalid.")
    expected = _sign_upload(sha, sid, exp_i)
    if not hmac.compare_digest(expected, sig):
        raise ShareError(403, "upload_signature_invalid", "Upload URL is invalid.")


def _artifact_url(actor: Actor, name: str) -> str:
    base = public_base_url()
    if actor.is_root:
        return f"{base}/{name}"
    return f"{base}/~{actor.handle}/{name}"


async def declare(actor: Actor, body: dict[str, Any], request_ip: str | None) -> dict:
    actor.require_scope("artifacts:write")
    settings = get_settings()
    files_in = body.get("files")
    if not files_in or not isinstance(files_in, list):
        raise ShareError(422, "invalid_path", "files is required.")
    if len(files_in) > settings.max_files_per_version:
        raise ShareError(413, "too_many_files", "Too many files in one version.")

    prepared: list[dict] = []
    for item in files_in:
        path = normalize_file_path(item.get("path") or "")
        sha = (item.get("sha256") or "").lower()
        if not _SHA_RE.match(sha):
            raise ShareError(422, "invalid_path", "sha256 must be 64 lowercase hex characters.")
        size = int(item.get("size") or 0)
        if size < 0 or size > settings.max_file_bytes:
            raise ShareError(413, "file_too_large", "A file exceeds the size limit.")
        prepared.append(
            {
                "path": path,
                "sha256": sha,
                "size": size,
                "contentType": _content_type(path, item.get("contentType")),
            }
        )
    check_case_collisions([f["path"] for f in prepared])

    name = body.get("name")
    name = generate_name() if not name else normalize_name(str(name))

    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            """
            SELECT id, trashed_at, deleted_at FROM artifact
            WHERE user_id = $1 AND name = $2 AND deleted_at IS NULL
            """,
            actor.user_id,
            name,
        )
        if existing and existing["trashed_at"] is not None:
            raise ShareError(409, "name_taken", "That name is held by a trashed artifact.")

        if existing is None:
            art_id = prefixed("art")
            await conn.execute(
                """
                INSERT INTO artifact (
                    id, user_id, name, title, description, kind, created_by_token
                ) VALUES ($1,$2,$3,$4,$5,'file',$6)
                """,
                art_id,
                actor.user_id,
                name,
                body.get("title"),
                body.get("description"),
                actor.token_id,
            )
        else:
            art_id = existing["id"]

        ver_id = prefixed("ver")
        draft_seq = -int.from_bytes(os.urandom(3), "big") - 1
        await conn.execute(
            """
            INSERT INTO artifact_version (
                id, artifact_id, seq, file_count, total_bytes, note,
                created_by_token, created_by_user
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
            """,
            ver_id,
            art_id,
            draft_seq,
            len(prepared),
            sum(f["size"] for f in prepared),
            body.get("note"),
            actor.token_id,
            actor.user_id,
        )
        sid = prefixed("ups")
        expires = datetime.now(UTC) + timedelta(hours=4)
        unique_hashes = {}
        for f in prepared:
            unique_hashes.setdefault(f["sha256"], f)
        owned = await conn.fetch(
            """
            SELECT DISTINCT encode(vf.sha256, 'hex') AS sha
            FROM version_file vf
            JOIN artifact_version av ON av.id = vf.version_id
            JOIN artifact a ON a.id = av.artifact_id
            WHERE a.user_id = $1 AND a.deleted_at IS NULL
            """,
            actor.user_id,
        )
        owned_set = {r["sha"] for r in owned}
        pending = [h for h in unique_hashes if h not in owned_set]
        manifest = {
            "files": prepared,
            "entryPath": body.get("entryPath"),
            "pending": pending,
            "received": [h for h in unique_hashes if h in owned_set],
        }
        await conn.execute(
            """
            INSERT INTO upload_session (
                id, artifact_id, version_id, user_id, state, manifest,
                pending_count, created_by_token, expires_at
            ) VALUES ($1,$2,$3,$4,'open',$5::jsonb,$6,$7,$8)
            """,
            sid,
            art_id,
            ver_id,
            actor.user_id,
            json.dumps(manifest),
            len(pending),
            actor.token_id,
            expires,
        )
        exp = int(expires.timestamp())
        uploads = []
        for sha in pending:
            sig = _sign_upload(sha, sid, exp)
            uploads.append(
                {
                    "path": unique_hashes[sha]["path"].lstrip("/"),
                    "sha256": sha,
                    "method": "PUT",
                    "url": (
                        f"{public_base_url()}/api/v1/files/{sha}"
                        f"?sid={sid}&exp={exp}&sig={sig}"
                    ),
                }
            )
        warnings: list[dict] = []
        prefix_hit = await conn.fetchval(
            """
            SELECT 1 FROM artifact
            WHERE user_id = $1 AND deleted_at IS NULL AND trashed_at IS NULL
              AND name LIKE $2 AND name <> $3
            LIMIT 1
            """,
            actor.user_id,
            name + "/%",
            name,
        )
        if prefix_hit:
            warnings.append(
                {
                    "code": "shadowing_name",
                    "message": "This name is a prefix of an existing artifact name.",
                }
            )
        await audit.record(
            conn,
            user_id=actor.user_id,
            actor_type="token" if actor.token_id else "user",
            actor_token_id=actor.token_id,
            action="artifact.declare",
            target_type="artifact",
            target_id=art_id,
            target_label=name,
            ip=request_ip,
        )
    return {
        "artifactId": art_id,
        "name": name,
        "versionId": ver_id,
        "seq": 1 if existing is None else None,
        "uploadSessionId": sid,
        "expiresAt": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "totalFiles": len(prepared),
        "skipped": len(unique_hashes) - len(pending),
        "uploads": uploads,
        "warnings": warnings,
    }


async def upload_file(sha: str, sid: str, exp: str, sig: str, data: bytes) -> dict:
    sha = sha.lower()
    verify_upload_sig(sha, sid, exp, sig)
    pool = await get_pool()
    async with pool.acquire() as conn:
        session = await conn.fetchrow(
            "SELECT * FROM upload_session WHERE id = $1",
            sid,
        )
        if session is None:
            raise ShareError(403, "upload_signature_invalid", "Upload URL is invalid.")
        if session["state"] != "open":
            raise ShareError(409, "upload_session_closed", "This upload session is closed.")
        if session["expires_at"] < datetime.now(UTC):
            raise ShareError(409, "upload_session_expired", "This upload session has expired.")
        manifest = session["manifest"]
        if isinstance(manifest, str):
            manifest = json.loads(manifest)
        pending = set(manifest.get("pending") or [])
        received = set(manifest.get("received") or [])
        declared = {f["sha256"]: f for f in manifest["files"]}
        if sha not in declared:
            raise ShareError(403, "upload_signature_invalid", "Upload URL is invalid.")
        expected_size = declared[sha]["size"]
        dest = store.blob_abs(sha)
        if dest.exists() or sha in received:
            if sha in pending:
                pending.remove(sha)
                received.add(sha)
        else:
            await store.write_blob(sha, expected_size, data)
            pending.discard(sha)
            received.add(sha)
        await conn.execute(
            """
            INSERT INTO file (sha256, size) VALUES ($1, $2)
            ON CONFLICT (sha256) DO UPDATE SET last_ref_at = now()
            """,
            bytes.fromhex(sha),
            expected_size,
        )
        manifest["pending"] = sorted(pending)
        manifest["received"] = sorted(received)
        await conn.execute(
            """
            UPDATE upload_session
            SET pending_count = $2, manifest = $3::jsonb
            WHERE id = $1
            """,
            sid,
            len(pending),
            json.dumps(manifest),
        )
    return {"sha256": sha, "size": expected_size, "remaining": len(pending)}


async def commit(actor: Actor, name: str, version_id: str, request_ip: str | None) -> dict:
    actor.require_scope("artifacts:write")
    name = normalize_name(name)
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            art = await conn.fetchrow(
                """
                SELECT * FROM artifact
                WHERE user_id = $1 AND name = $2 AND deleted_at IS NULL
                FOR UPDATE
                """,
                actor.user_id,
                name,
            )
            if art is None:
                raise ShareError(404, "artifact_not_found", "No artifact with that name.")
            session = await conn.fetchrow(
                """
                SELECT * FROM upload_session
                WHERE artifact_id = $1 AND version_id = $2
                FOR UPDATE
                """,
                art["id"],
                version_id,
            )
            if session is None:
                raise ShareError(404, "version_not_found", "No such version.")
            if session["state"] == "expired":
                raise ShareError(409, "upload_session_expired", "This upload session has expired.")
            if session["state"] != "open":
                raise ShareError(409, "upload_session_closed", "This upload session is closed.")
            if session["expires_at"] < datetime.now(UTC):
                await conn.execute(
                    "UPDATE upload_session SET state = 'expired' WHERE id = $1",
                    session["id"],
                )
                raise ShareError(409, "upload_session_expired", "This upload session has expired.")
            manifest = session["manifest"]
            if isinstance(manifest, str):
                manifest = json.loads(manifest)
            files = manifest["files"]
            for f in files:
                row = await conn.fetchrow(
                    "SELECT size FROM file WHERE sha256 = $1",
                    bytes.fromhex(f["sha256"]),
                )
                path = store.blob_abs(f["sha256"])
                if row is None or not path.exists():
                    raise ShareError(409, "files_missing", "Not every declared file has been uploaded.")
                if row["size"] != f["size"]:
                    raise ShareError(409, "file_size_mismatch", "A stored file size does not match.")
            max_seq = await conn.fetchval(
                """
                SELECT COALESCE(MAX(seq), 0) FROM artifact_version
                WHERE artifact_id = $1 AND seq > 0
                """,
                art["id"],
            )
            seq = int(max_seq) + 1
            kind = _kind_from_files(files)
            entry, warnings = _entry_path(files, manifest.get("entryPath"))
            await conn.execute(
                """
                UPDATE artifact_version
                SET seq = $2, entry_path = $3, file_count = $4, total_bytes = $5
                WHERE id = $1
                """,
                version_id,
                seq,
                entry,
                len(files),
                sum(f["size"] for f in files),
            )
            for f in files:
                await conn.execute(
                    """
                    INSERT INTO version_file (version_id, path, sha256, size, content_type)
                    VALUES ($1,$2,$3,$4,$5)
                    """,
                    version_id,
                    f["path"],
                    bytes.fromhex(f["sha256"]),
                    f["size"],
                    f["contentType"],
                )
                await conn.execute(
                    "UPDATE file SET ref_count = ref_count + 1, last_ref_at = now() WHERE sha256 = $1",
                    bytes.fromhex(f["sha256"]),
                )
            await conn.execute(
                """
                UPDATE artifact
                SET kind = $2, live_version_id = $3, entry_path = $4,
                    title = COALESCE($5, title), updated_at = now(),
                    trashed_at = NULL
                WHERE id = $1
                """,
                art["id"],
                kind,
                version_id,
                entry,
                None,
            )
            await conn.execute(
                """
                UPDATE upload_session
                SET state = 'committed', pending_count = 0, committed_at = now()
                WHERE id = $1
                """,
                session["id"],
            )
            await conn.execute(
                """
                UPDATE app_user
                SET artifact_count = (
                    SELECT COUNT(*) FROM artifact
                    WHERE user_id = $1 AND deleted_at IS NULL AND trashed_at IS NULL
                )
                WHERE id = $1
                """,
                actor.user_id,
            )
            await audit.record(
                conn,
                user_id=actor.user_id,
                actor_type="token" if actor.token_id else "user",
                actor_token_id=actor.token_id,
                action="artifact.post",
                target_type="artifact",
                target_id=art["id"],
                target_label=name,
                ip=request_ip,
            )
    return {
        "artifactId": art["id"],
        "name": name,
        "url": _artifact_url(actor, name),
        "seq": seq,
        "kind": kind,
        "entryPath": entry,
        "fileCount": len(files),
        "totalBytes": sum(f["size"] for f in files),
        "visibility": "private",
        "shareLinks": 0,
        "warnings": warnings,
    }


def _item(actor: Actor, row, tags: list[str]) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "title": row["title"],
        "kind": row["kind"],
        "url": _artifact_url(actor, row["name"]),
        "owner": {"handle": actor.handle, "isSelf": True},
        "visibility": "private",
        "shareLinks": [],
        "grants": [],
        "seq": row["seq"],
        "versionCount": row["version_count"],
        "fileCount": row["file_count"],
        "totalBytes": row["total_bytes"],
        "entryPath": row["entry_path"],
        "tags": tags,
        "ttlExpiresAt": row["ttl_expires_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
        if row["ttl_expires_at"]
        else None,
        "pinned": row["pinned"],
        "allowFraming": row["allow_framing"],
        "csp": row["csp"],
        "viewCount": row["view_count"],
        "lastViewedAt": row["last_viewed_at"].strftime("%Y-%m-%dT%H:%M:%SZ")
        if row["last_viewed_at"]
        else None,
        "createdAt": row["created_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updatedAt": row["updated_at"].strftime("%Y-%m-%dT%H:%M:%SZ"),
        "createdBy": {
            "type": "token" if row["created_by_token"] else "user",
            "id": row["created_by_token"],
            "name": None,
        },
    }


_LIST_SQL = """
SELECT a.*, av.seq, av.file_count, av.total_bytes,
       (SELECT COUNT(*) FROM artifact_version v
        WHERE v.artifact_id = a.id AND v.deleted_at IS NULL AND v.seq > 0) AS version_count
FROM artifact a
LEFT JOIN artifact_version av ON av.id = a.live_version_id
WHERE a.user_id = $1 AND a.deleted_at IS NULL
"""


async def list_artifacts(actor: Actor, *, trashed: bool = False) -> dict:
    actor.require_scope("artifacts:read")
    pool = await get_pool()
    clause = " AND a.trashed_at IS NOT NULL" if trashed else " AND a.trashed_at IS NULL"
    async with pool.acquire() as conn:
        rows = await conn.fetch(_LIST_SQL + clause + " ORDER BY a.updated_at DESC LIMIT 50", actor.user_id)
        items = []
        for row in rows:
            tags = [
                r["tag"]
                for r in await conn.fetch(
                    "SELECT tag FROM artifact_tag WHERE artifact_id = $1", row["id"]
                )
            ]
            items.append(_item(actor, row, tags))
    return {"items": items, "nextCursor": None, "hasMore": False}


async def get_artifact(actor: Actor, name: str) -> dict:
    actor.require_scope("artifacts:read")
    name = normalize_name(name)
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            _LIST_SQL + " AND a.name = $2 AND a.trashed_at IS NULL",
            actor.user_id,
            name,
        )
        if row is None:
            raise ShareError(404, "artifact_not_found", "No artifact with that name.")
        tags = [
            r["tag"]
            for r in await conn.fetch("SELECT tag FROM artifact_tag WHERE artifact_id = $1", row["id"])
        ]
    return _item(actor, row, tags)


async def trash(actor: Actor, name: str, *, purge: bool, request_ip: str | None) -> None:
    name = normalize_name(name)
    pool = await get_pool()
    async with pool.acquire() as conn:
        art = await conn.fetchrow(
            "SELECT * FROM artifact WHERE user_id = $1 AND name = $2 AND deleted_at IS NULL",
            actor.user_id,
            name,
        )
        if art is None:
            raise ShareError(404, "artifact_not_found", "No artifact with that name.")
        if purge:
            actor.require_scope("artifacts:delete")
            await conn.execute(
                """
                UPDATE share_link SET revoked_at = now()
                WHERE artifact_id = $1 AND revoked_at IS NULL
                """,
                art["id"],
            )
            await conn.execute(
                """
                UPDATE share_grant SET revoked_at = now()
                WHERE artifact_id = $1 AND revoked_at IS NULL
                """,
                art["id"],
            )
            files = await conn.fetch(
                """
                SELECT vf.sha256 FROM version_file vf
                JOIN artifact_version av ON av.id = vf.version_id
                WHERE av.artifact_id = $1
                """,
                art["id"],
            )
            await conn.execute("UPDATE artifact SET live_version_id = NULL WHERE id = $1", art["id"])
            await conn.execute("DELETE FROM version_file WHERE version_id IN (SELECT id FROM artifact_version WHERE artifact_id = $1)", art["id"])
            for f in files:
                await conn.execute(
                    """
                    UPDATE file SET ref_count = GREATEST(ref_count - 1, 0), last_ref_at = now()
                    WHERE sha256 = $1
                    """,
                    f["sha256"],
                )
            await conn.execute(
                "UPDATE artifact SET deleted_at = now(), trashed_at = now() WHERE id = $1",
                art["id"],
            )
            await audit.record(
                conn,
                user_id=actor.user_id,
                actor_type="token" if actor.token_id else "user",
                actor_token_id=actor.token_id,
                action="artifact.purge",
                target_type="artifact",
                target_id=art["id"],
                target_label=name,
                ip=request_ip,
            )
            return
        actor.require_scope("artifacts:write")
        await conn.execute(
            """
            UPDATE share_link SET revoked_at = now()
            WHERE artifact_id = $1 AND revoked_at IS NULL
            """,
            art["id"],
        )
        await conn.execute(
            """
            UPDATE share_grant SET revoked_at = now()
            WHERE artifact_id = $1 AND revoked_at IS NULL
            """,
            art["id"],
        )
        await conn.execute(
            "UPDATE artifact SET trashed_at = now(), updated_at = now() WHERE id = $1",
            art["id"],
        )
        await audit.record(
            conn,
            user_id=actor.user_id,
            actor_type="token" if actor.token_id else "user",
            actor_token_id=actor.token_id,
            action="artifact.trash",
            target_type="artifact",
            target_id=art["id"],
            target_label=name,
            ip=request_ip,
        )


async def restore(actor: Actor, name: str, request_ip: str | None) -> dict:
    actor.require_scope("artifacts:write")
    name = normalize_name(name)
    pool = await get_pool()
    async with pool.acquire() as conn:
        art = await conn.fetchrow(
            """
            SELECT * FROM artifact
            WHERE user_id = $1 AND name = $2 AND deleted_at IS NULL AND trashed_at IS NOT NULL
            """,
            actor.user_id,
            name,
        )
        if art is None:
            raise ShareError(404, "artifact_not_found", "No artifact with that name.")
        await conn.execute(
            "UPDATE artifact SET trashed_at = NULL, updated_at = now() WHERE id = $1",
            art["id"],
        )
        await audit.record(
            conn,
            user_id=actor.user_id,
            actor_type="token" if actor.token_id else "user",
            actor_token_id=actor.token_id,
            action="artifact.restore",
            target_type="artifact",
            target_id=art["id"],
            target_label=name,
            ip=request_ip,
        )
    return await get_artifact(actor, name)


async def _live_version_id(conn, actor: Actor, name: str, version: str | None) -> str:
    art = await conn.fetchrow(
        """
        SELECT id, live_version_id FROM artifact
        WHERE user_id = $1 AND name = $2 AND deleted_at IS NULL AND trashed_at IS NULL
        """,
        actor.user_id,
        name,
    )
    if art is None or art["live_version_id"] is None:
        raise ShareError(404, "artifact_not_found", "No artifact with that name.")
    if version:
        ok = await conn.fetchval(
            """
            SELECT id FROM artifact_version
            WHERE artifact_id = $1 AND id = $2 AND deleted_at IS NULL
            """,
            art["id"],
            version,
        )
        if not ok:
            raise ShareError(404, "version_not_found", "No such version.")
        return version
    return art["live_version_id"]


async def list_files(actor: Actor, name: str, version: str | None = None) -> dict:
    actor.require_scope("artifacts:read")
    name = normalize_name(name)
    pool = await get_pool()
    async with pool.acquire() as conn:
        vid = await _live_version_id(conn, actor, name, version)
        rows = await conn.fetch(
            """
            SELECT path, size, content_type, encode(sha256, 'hex') AS sha256
            FROM version_file WHERE version_id = $1 ORDER BY path
            """,
            vid,
        )
    return {
        "items": [
            {
                "path": r["path"],
                "size": r["size"],
                "contentType": r["content_type"],
                "sha256": r["sha256"],
            }
            for r in rows
        ]
    }


async def file_bytes(actor: Actor, name: str, path: str, version: str | None = None):
    actor.require_scope("artifacts:read")
    name = normalize_name(name)
    norm = normalize_file_path(path)
    pool = await get_pool()
    async with pool.acquire() as conn:
        vid = await _live_version_id(conn, actor, name, version)
        row = await conn.fetchrow(
            """
            SELECT path, size, content_type, encode(sha256, 'hex') AS sha256
            FROM version_file WHERE version_id = $1 AND path = $2
            """,
            vid,
            norm,
        )
    if row is None:
        raise ShareError(404, "file_not_found", "That path is not in this version.")
    blob = store.blob_abs(row["sha256"])
    if not blob.is_file():
        raise ShareError(404, "file_not_found", "That path is not in this version.")
    return blob, row["content_type"]
