"""Share links — unguessable URLs, optional password (Part 7)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from ..auth import Actor, public_base_url
from ..db import get_pool
from ..errors import ShareError
from ..ids import prefixed
from . import audit

_ph = PasswordHasher()
_ADJECTIVES = "amber coral ember moss slate cedar ivory sage pearl flax linen frost dune pine".split()
_NOUNS = "harbor lantern meadow orchard ridge mill quay grove ledger folio atlas kiln loom".split()

_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _b58(data: bytes) -> str:
    n = int.from_bytes(data, "big")
    chars: list[str] = []
    while n:
        n, r = divmod(n, 58)
        chars.append(_B58[r])
    pad = 0
    for b in data:
        if b == 0:
            pad += 1
        else:
            break
    return (_B58[0] * pad) + "".join(reversed(chars)) or _B58[0]


def _parse_ttl(raw: str | None) -> timedelta:
    text = (raw or "14d").strip().lower()
    if text.endswith("d"):
        return timedelta(days=int(text[:-1] or "14"))
    if text.endswith("h"):
        return timedelta(hours=int(text[:-1] or "24"))
    if text.endswith("m"):
        return timedelta(minutes=int(text[:-1] or "30"))
    raise ShareError(422, "invalid_name", "ttl must look like 14d, 24h, or 30m.")


def generate_link_password() -> str:
    return f"{secrets.choice(_ADJECTIVES)}-{secrets.choice(_NOUNS)}-{secrets.randbelow(90) + 10}"


def _hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_link_password(password_hash: str, password: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerifyMismatchError, Exception):
        return False


async def create_link(
    actor: Actor,
    name: str,
    *,
    ttl: str | None,
    label: str | None,
    password: bool | str | None = None,
    request_ip: str | None,
) -> dict:
    actor.require_scope("share:create")
    from ..paths import normalize_name

    name = normalize_name(name)
    expires = datetime.now(UTC) + _parse_ttl(ttl)
    pool = await get_pool()
    async with pool.acquire() as conn:
        art = await conn.fetchrow(
            """
            SELECT id, name, title FROM artifact
            WHERE user_id = $1 AND name = $2 AND deleted_at IS NULL AND trashed_at IS NULL
            """,
            actor.user_id,
            name,
        )
        if art is None:
            raise ShareError(404, "artifact_not_found", "No artifact with that name.")
        token = None
        prefix = None
        digest = None
        for _ in range(8):
            raw = secrets.token_bytes(16)
            token = _b58(raw)
            prefix = token[:8]
            clash = await conn.fetchval(
                """
                SELECT 1 FROM share_link
                WHERE display_prefix = $1 AND revoked_at IS NULL
                """,
                prefix,
            )
            if clash:
                continue
            digest = hashlib.sha256(token.encode()).digest()
            break
        if token is None or digest is None:
            raise ShareError(500, "rate_limited", "Could not allocate a link token.")
        plaintext = None
        password_hash = None
        if password is True:
            plaintext = generate_link_password()
            password_hash = _hash_password(plaintext)
        elif isinstance(password, str) and password:
            if len(password) < 8:
                raise ShareError(422, "invalid_name", "A link password needs at least 8 characters.")
            plaintext = password
            password_hash = _hash_password(password)
        link_id = prefixed("lnk")
        await conn.execute(
            """
            INSERT INTO share_link (
                id, artifact_id, token_hash, display_prefix, label, password_hash,
                expires_at, created_by_user, created_by_token
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            """,
            link_id,
            art["id"],
            digest,
            prefix,
            label,
            password_hash,
            expires,
            actor.user_id,
            actor.token_id,
        )
        await audit.record(
            conn,
            user_id=actor.user_id,
            actor_type="token" if actor.token_id else "user",
            actor_token_id=actor.token_id,
            action="link.create",
            target_type="artifact",
            target_id=art["id"],
            target_label=name,
            ip=request_ip,
            metadata={
                "hasPassword": bool(password_hash),
                "expiresAt": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
            },
        )
    out = {
        "id": link_id,
        "url": f"{public_base_url()}/s/{token}",
        "expiresAt": expires.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hasPassword": bool(password_hash),
        "label": label,
        "artifact": {"name": art["name"], "title": art["title"]},
        "warnings": [],
    }
    if plaintext:
        out["password"] = plaintext
    return out


def recipient_landing_html(*, title: str, kind: str, view_href: str, download_href: str) -> bytes:
    """R2 — View + Download chrome for a non-HTML share link."""
    from html import escape
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "docs" / "specs" / "recipient" / "R2-landing.html"
    title_e = escape(title)
    kind_e = escape(kind)
    view_e = escape(view_href, quote=True)
    dl_e = escape(download_href, quote=True)
    if path.is_file():
        html = path.read_text(encoding="utf-8")
        html = html.replace("<title>Q3 margin review</title>", f"<title>{title_e}</title>")
        html = html.replace("<h1>Q3 margin review</h1>", f"<h1>{title_e}</h1>")
        html = html.replace(
            '<p class="m">PDF &middot; 3 files &middot; 2.4 MB</p>',
            f'<p class="m">{kind_e}</p>',
        )
        html = html.replace('href="./index.html"', f'href="{view_e}"')
        html = html.replace('href="./?download=1"', f'href="{dl_e}"')
        return html.encode("utf-8")
    return (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>{title_e}</title></head><body><h1>{title_e}</h1>"
        f"<p>{kind_e}</p><p><a href='{view_e}'>View</a> "
        f"<a href='{dl_e}'>Download</a></p></body></html>"
    ).encode()


def password_gate_html(token: str, *, wrong: bool = False) -> str:
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "docs" / "specs" / "recipient" / (
        "R1-password-gate-wrong.html" if wrong else "R1-password-gate.html"
    )
    html = path.read_text(encoding="utf-8") if path.is_file() else (
        "<!DOCTYPE html><title>password</title><form method='post'><input name='password'>"
        "<button>Continue</button></form>"
    )
    return html.replace('action=""', f'action="/s/{token}/unlock"')


def cookie_name(token: str) -> str:
    return f"share_r_{token[:8]}"


def _mac(session_id: str) -> str:
    from ..config import get_settings

    key = get_settings().secret_key.encode()
    return hmac.new(key, session_id.encode(), hashlib.sha256).hexdigest()


def parse_recipient_cookie(value: str) -> str | None:
    if not value or "." not in value:
        return None
    sid, mac = value.split(".", 1)
    if not hmac.compare_digest(_mac(sid), mac):
        return None
    return sid


async def issue_recipient_session(link_id: str, expires_at, ip: str | None) -> tuple[str, str]:
    sid = prefixed("rcp")
    token_hash = hashlib.sha256(sid.encode()).digest()
    lifetime = datetime.now(UTC) + timedelta(hours=24)
    if expires_at and expires_at < lifetime:
        lifetime = expires_at
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO recipient_session (id, share_link_id, token_hash, expires_at)
            VALUES ($1,$2,$3,$4)
            """,
            sid,
            link_id,
            token_hash,
            lifetime,
        )
    return sid, f"{sid}.{_mac(sid)}"


async def recipient_session_ok(session_id: str, link_id: str) -> bool:
    from datetime import UTC, datetime

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id FROM recipient_session
            WHERE id = $1 AND share_link_id = $2
              AND revoked_at IS NULL AND expires_at > $3
            """,
            session_id,
            link_id,
            datetime.now(UTC),
        )
    return row is not None


async def resolve_token(token: str):
    digest = hashlib.sha256(token.encode()).digest()
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT sl.*, a.user_id AS artifact_user_id, a.trashed_at, a.deleted_at,
                   a.ttl_expires_at, a.live_version_id, a.entry_path, a.csp, a.allow_framing,
                   a.name AS artifact_name, a.id AS artifact_pk
            FROM share_link sl
            JOIN artifact a ON a.id = sl.artifact_id
            WHERE sl.token_hash = $1
            """,
            digest,
        )
    return row
