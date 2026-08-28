"""Markdown display wrapper (D-29)."""

from __future__ import annotations

import hashlib
from pathlib import Path

from server.services.markdown_view import (
    document_title,
    is_markdown,
    render_markdown_body,
    render_markdown_file,
    wrap_document,
)


def test_is_markdown_by_extension_and_type():
    assert is_markdown("notes.md", "text/plain; charset=utf-8")
    assert is_markdown("README.markdown", "application/octet-stream")
    assert is_markdown("untitled", "text/markdown")
    assert not is_markdown("notes.txt", "text/plain")
    assert not is_markdown("index.html", "text/html")


def test_render_escapes_raw_html_and_js_urls():
    html = render_markdown_body(
        "Hello <script>alert(1)</script>\n\n"
        "[x](javascript:alert(1))\n\n"
        "<img src=x onerror=alert(1)>\n"
    )
    assert "<script>" not in html.lower()
    assert "javascript:" not in html.lower()
    assert "<img" not in html.lower()
    assert "&lt;script&gt;" in html.lower()
    assert "&lt;img" in html.lower()
    assert 'href="#harmful-link"' in html


def test_render_formats_headings_lists_and_code():
    html = render_markdown_body(
        "# Title\n\n"
        "## Sub\n\n"
        "A paragraph with `code` and **bold**.\n\n"
        "- one\n- two\n\n"
        "```\nprint('hi')\n```\n"
    )
    assert "<h1>" in html and "Title" in html
    assert "<h2>" in html
    assert "<ul>" in html and "<li>" in html
    assert "<code>" in html
    assert "<strong>" in html
    assert "<pre>" in html


def test_document_title_prefers_artifact_then_heading():
    src = "# Pigeon Gmail token death\n\nbody\n"
    assert document_title(src, "Hand diagnostic") == "Hand diagnostic"
    assert document_title(src, None) == "Pigeon Gmail token death"
    assert document_title("no heading", None) == "share.c52.com"


def test_wrap_and_file_roundtrip(tmp_path: Path):
    source = "# Hello\n\nThis is **fine**.\n"
    path = tmp_path / "note.md"
    path.write_text(source, encoding="utf-8")
    page = render_markdown_file(path, title="Hello")
    assert page is not None
    text = page.decode("utf-8")
    assert "<h1>" in text and "Hello" in text
    assert "<strong>fine</strong>" in text
    assert 'href="?download=1"' in text
    assert "share.c52.com" in text
    wrapped = wrap_document(title="t", body_html="<p>x</p>", download_href="?download=1")
    assert b"<p>x</p>" in wrapped
    assert b"<!--email_off-->" in wrapped
    assert b"<!--/email_off-->" in wrapped


async def _post_markdown(client, headers, name="note"):
    body = b"# Hello\n\nA list:\n\n- alpha\n- beta\n\n`code`\n"
    sha = hashlib.sha256(body).hexdigest()
    declared = await client.post(
        "/api/v1/artifacts",
        headers=headers,
        json={
            "name": name,
            "title": "Hello note",
            "files": [
                {
                    "path": "hello.md",
                    "size": len(body),
                    "contentType": "text/markdown",
                    "sha256": sha,
                }
            ],
        },
    )
    assert declared.status_code == 201, declared.text
    data = declared.json()
    from urllib.parse import urlparse

    url = data["uploads"][0]["url"]
    parsed = urlparse(url)
    put = await client.put(f"{parsed.path}?{parsed.query}", content=body)
    assert put.status_code == 200, put.text
    committed = await client.post(
        f"/api/v1/artifacts/{name}/versions/{data['versionId']}/commit",
        headers=headers,
    )
    assert committed.status_code == 200, committed.text
    return body


async def test_owner_markdown_renders_html(client, root_user):
    await _post_markdown(client, root_user["headers"], name="mdown")
    rawish = await client.get("/mdown")
    assert rawish.status_code == 404
    page = await client.get("/mdown", cookies={"share_s": root_user["session"]})
    assert page.status_code == 200
    assert "text/html" in page.headers.get("content-type", "")
    assert b"<h1>" in page.content
    assert b"Hello" in page.content
    assert b"<ul>" in page.content
    assert b"<script>" not in page.content
    dl = await client.get(
        "/mdown?download=1", cookies={"share_s": root_user["session"]}
    )
    assert dl.status_code == 200
    assert dl.headers.get("content-disposition", "").startswith("attachment")
    assert dl.content.startswith(b"# Hello")


async def test_share_link_markdown_skips_r2(client, root_user):
    await _post_markdown(client, root_user["headers"], name="sharedmd")
    client.cookies.set("share_s", root_user["session"])
    created = await client.post(
        "/api/v1/artifacts/sharedmd/links",
        json={"ttl": "14d", "label": "md-review"},
    )
    assert created.status_code == 201, created.text
    token = created.json()["url"].rstrip("/").rsplit("/s/", 1)[-1]
    landing = await client.get(f"/s/{token}/")
    assert landing.status_code == 200
    assert "text/html" in landing.headers.get("content-type", "")
    assert b"<h1>" in landing.content
    assert b"alpha" in landing.content
    assert b"View" not in landing.content
    assert b"Download" in landing.content
    assert b"?download=1" in landing.content
    dl = await client.get(f"/s/{token}/?download=1")
    assert dl.status_code == 200
    assert dl.headers.get("content-disposition", "").startswith("attachment")
    assert dl.content.startswith(b"# Hello")
