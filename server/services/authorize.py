"""Resolution and can_view (§6.5)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from fastapi import Request

from ..auth import Actor
from ..config import get_settings
from ..db import get_pool
from ..errors import not_found_response
from ..paths import RESERVED_FIRST_SEGMENTS
from .store import blob_abs, blob_relpath


@dataclass
class PasswordRequired:
    token: str


@dataclass
class ResolvedFile:
    abs_path: Path
    rel: str
    content_type: str
    cache_control: str
    disposition: str | None
    csp: str | None
    frame: str
    artifact_id: str
    version_id: str


def can_view(actor: Actor, artifact_user_id: str, grant: bool, link_ok: bool) -> bool:
    if actor.is_user and actor.user_id == artifact_user_id:
        return True
    if actor.is_user and grant:
        return True
    if actor.is_recipient and link_ok:
        return True
    return False


def split_space(path: str) -> tuple[str | None, str]:
    raw = path if path.startswith("/") else "/" + path
    parts = [p for p in raw.split("/") if p]
    if not parts:
        return "root", "/"
    if parts[0] in RESERVED_FIRST_SEGMENTS or parts[0] == "~":
        return None, raw
    if parts[0].startswith("~") and parts[0] != "~":
        handle = parts[0][1:]
        rest = "/" + "/".join(parts[1:]) if len(parts) > 1 else "/"
        return handle, rest
    return "root", raw if raw.startswith("/") else "/" + raw


async def _owner_id_for_space(conn, space: str) -> str | None:
    if space == "root":
        return await conn.fetchval("SELECT id FROM app_user WHERE is_root = true")
    return await conn.fetchval("SELECT id FROM app_user WHERE handle = $1", space)


async def resolve_longest(conn, user_id: str, rest: str):
    rest = rest if rest.startswith("/") else "/" + rest
    trimmed = rest.strip("/")
    if not trimmed:
        return None, None
    segments = trimmed.split("/")
    for i in range(len(segments), 0, -1):
        name = "/".join(segments[:i])
        art = await conn.fetchrow(
            """
            SELECT a.*, av.id AS version_id, av.created_at AS version_created
            FROM artifact a
            JOIN artifact_version av ON av.id = a.live_version_id
            WHERE a.user_id = $1 AND a.name = $2
              AND a.deleted_at IS NULL
            """,
            user_id,
            name,
        )
        if art:
            remainder = "/" + "/".join(segments[i:]) if i < len(segments) else "/"
            return art, remainder
    return None, None


async def _has_grant(conn, artifact_id: str, user_id: str) -> bool:
    row = await conn.fetchval(
        """
        SELECT 1 FROM share_grant
        WHERE artifact_id = $1 AND user_id = $2 AND revoked_at IS NULL
        """,
        artifact_id,
        user_id,
    )
    return bool(row)


def _listing_html(name: str, files: list) -> bytes:
    rows = "".join(
        f"<li><a href='{f['path'].lstrip('/')}'>{f['path']}</a> "
        f"<span>{f['size']} bytes</span></li>"
        for f in files
    )
    html = (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='robots' content='noindex, nofollow'>"
        f"<title>{name}</title></head><body><h1>{name}</h1><ul>{rows}</ul></body></html>"
    )
    return html.encode("utf-8")


async def authorize_request(request: Request):
    """Return (ResolvedFile | bytes listing | None for 404, extra)."""
    path = request.headers.get("x-forwarded-uri") or request.headers.get(
        "x-original-uri"
    ) or request.url.path
    cookie = request.cookies.get("share_s")
    actor = Actor()
    if cookie:
        try:
            from ..auth import _lookup_session

            found = await _lookup_session(cookie)
            actor = found or Actor()
        except Exception:
            actor = Actor()

    parts = [p for p in path.split("/") if p]
    pool = await get_pool()
    async with pool.acquire() as conn:
        now = datetime.now(UTC)
        if parts and parts[0] == "s":
            if len(parts) < 2:
                return None
            from .sharing import resolve_token

            row = await resolve_token(parts[1])
            if (
                row is None
                or row["revoked_at"] is not None
                or row["expires_at"] < now
                or row["trashed_at"] is not None
                or row["deleted_at"] is not None
            ):
                return None
            if row["password_hash"]:
                from .sharing import cookie_name, parse_recipient_cookie, recipient_session_ok

                cookie = request.cookies.get(cookie_name(parts[1]))
                sid = parse_recipient_cookie(cookie or "")
                if not sid or not await recipient_session_ok(sid, row["id"]):
                    return PasswordRequired(token=parts[1])
            actor = Actor(
                is_recipient=True,
                link_id=row["id"],
                link_artifact_id=row["artifact_id"],
                link_live=True,
            )
            art = await conn.fetchrow(
                """
                SELECT a.*, av.id AS version_id, av.created_at AS version_created
                FROM artifact a
                JOIN artifact_version av ON av.id = a.live_version_id
                WHERE a.id = $1
                """,
                row["artifact_id"],
            )
            remainder = "/" + "/".join(parts[2:]) if len(parts) > 2 else "/"
            grant = False
            link_ok = True
        else:
            space, rest = split_space(path)
            if space is None:
                return None
            owner_id = await _owner_id_for_space(conn, space)
            if owner_id is None:
                return None
            art, remainder = await resolve_longest(conn, owner_id, rest)
            if (
                art is None
                or art["trashed_at"] is not None
                or (art["ttl_expires_at"] is not None and art["ttl_expires_at"] < now)
            ):
                return None
            grant = False
            if actor.is_user and actor.user_id != art["user_id"]:
                grant = await _has_grant(conn, art["id"], actor.user_id)
            link_ok = bool(
                actor.is_recipient
                and actor.link_artifact_id == art["id"]
                and actor.link_live
            )
        if art is None:
            return None
        if not can_view(actor, art["user_id"], grant, link_ok):
            return None
        files = await conn.fetch(
            "SELECT path, sha256, size, content_type FROM version_file WHERE version_id = $1",
            art["version_id"],
        )
        by_path = {r["path"]: r for r in files}
        filepath = remainder if remainder != "/" else ""
        target = None
        if filepath in {"", "/"}:
            entry = art["entry_path"]
            if entry and entry in by_path:
                target = by_path[entry]
            elif not entry:
                listing = _listing_html(
                    art["name"],
                    [{"path": r["path"], "size": r["size"]} for r in files],
                )
                return listing
        if target is None and filepath in by_path:
            target = by_path[filepath]
        if target is None and filepath.endswith("/") and (filepath + "index.html") in by_path:
            target = by_path[filepath + "index.html"]
        if target is None and (filepath.rstrip("/") + "/index.html") in by_path:
            target = by_path[filepath.rstrip("/") + "/index.html"]
        if target is None and (filepath + ".html") in by_path:
            target = by_path[filepath + ".html"]
        if target is None and "/404.html" in by_path:
            target = by_path["/404.html"]
            # still 404 at HTTP layer — caller uses content
        if target is None:
            return None
        sha_hex = target["sha256"].hex()
        ctype = target["content_type"] or "application/octet-stream"
        path_name = target["path"] or "file"
        want_download = request.query_params.get("download") in {"1", "true"}
        htmlish = ctype.startswith("text/html") or path_name.lower().endswith((".html", ".htm"))
        if not want_download:
            from .markdown_view import is_markdown, render_markdown_file

            if is_markdown(path_name, ctype):
                rendered = render_markdown_file(
                    blob_abs(sha_hex),
                    title=art["title"],
                    download_href="?download=1",
                )
                if rendered is not None:
                    return rendered
        if (
            actor.is_recipient
            and not want_download
            and filepath in {"", "/"}
            and not htmlish
        ):
            from .sharing import recipient_landing_html

            view = path_name.lstrip("/")
            kind = (ctype.split(";")[0] or Path(path_name).suffix.lstrip(".") or "file")
            title = art["title"] or art["name"]
            return recipient_landing_html(
                title=title,
                kind=kind,
                view_href=view,
                download_href="?download=1",
            )
        disp = None
        if ctype == "application/octet-stream" or want_download:
            fname = Path(path_name).name.replace('"', "")
            disp = f'attachment; filename="{fname}"'
        csp = art["csp"]
        if Path(target["path"]).suffix.lower() == ".svg":
            csp = "default-src 'none'; style-src 'unsafe-inline'"
        frame = "SAMEORIGIN" if not art["allow_framing"] else ""
        cache = "private, max-age=300"
        if actor.is_recipient:
            cache = "private, no-store"
        return ResolvedFile(
            abs_path=blob_abs(sha_hex),
            rel=blob_relpath(sha_hex),
            content_type=ctype,
            cache_control=cache,
            disposition=disp,
            csp=csp,
            frame=frame,
            artifact_id=art["id"],
            version_id=art["version_id"],
        )


async def internal_authorize(request: Request):
    result = await authorize_request(request)
    if result is None:
        return not_found_response()
    from fastapi import Response

    if isinstance(result, (bytes, bytearray)):
        from .markdown_view import GENERATED_HTML_CSP

        return Response(
            content=result,
            media_type="text/html; charset=utf-8",
            headers={
                "Cache-Control": "no-store",
                "X-Robots-Tag": "noindex, nofollow",
                "Content-Security-Policy": GENERATED_HTML_CSP,
            },
        )
    headers = {
        "X-Share-File": result.rel,
        "X-Share-Content-Type": result.content_type,
        "X-Share-Cache-Control": result.cache_control,
    }
    if result.disposition:
        headers["X-Share-Disposition"] = result.disposition
    if result.csp:
        headers["X-Share-CSP"] = result.csp
    if result.frame:
        headers["X-Share-Frame-Options"] = result.frame
    settings = get_settings()
    if settings.debug:
        headers["X-Share-Artifact"] = result.artifact_id
        headers["X-Share-Version"] = result.version_id
    return Response(status_code=200, headers=headers)
