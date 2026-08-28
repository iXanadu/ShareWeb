"""Server-side Markdown → HTML for display (D-29).

Bytes stay `text/plain` / `text/markdown`. Opening a .md file without
`?download=1` wraps a sanitized HTML document in the recipient type tokens.
No JavaScript. Raw HTML in the source is escaped; link schemes are allowlisted.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

import mistune
import nh3

MAX_MARKDOWN_BYTES = 1_048_576

GENERATED_HTML_CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' https:; "
    "media-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'; "
    "frame-ancestors 'none'"
)

_MD_EXTS = {".md", ".markdown", ".mdown"}
_MD_TYPES = {"text/markdown", "text/x-markdown"}

_ALLOWED_TAGS = {
    "a",
    "blockquote",
    "br",
    "code",
    "del",
    "div",
    "em",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "hr",
    "img",
    "input",
    "li",
    "ol",
    "p",
    "pre",
    "span",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}

_ALLOWED_ATTRS = {
    "a": {"href", "title"},
    "code": {"class"},
    "img": {"src", "alt", "title"},
    "input": {"type", "checked", "disabled"},
    "li": {"class"},
    "ol": {"start", "class"},
    "td": {"align"},
    "th": {"align"},
    "ul": {"class"},
}

_RENDER = mistune.create_markdown(
    escape=True,
    plugins=["strikethrough", "table", "url", "task_lists", "footnotes"],
)

_DOCUMENT_CSS = """
    :root { color-scheme: light dark; }
    html { -webkit-text-size-adjust: 100%; }
    body {
      margin: 0;
      background: #f3f2f2;
      color: #201e1d;
      font-family: Georgia, "Times New Roman", Times, serif;
      font-size: 19px;
      line-height: 1.55;
    }
    .w { max-width: 42em; margin: 0 auto; padding: 2.5em 1.25em 4em; }
    .top { display: flex; flex-wrap: wrap; gap: 0.75em 1.25em; align-items: baseline;
           justify-content: space-between; margin: 0 0 2.25em; }
    .h { font-size: 0.79em; letter-spacing: 0.08em; text-transform: uppercase;
         color: #605d5d; margin: 0; }
    .b2 {
      display: inline-block; font: inherit; color: #201e1d;
      background: transparent; border: 1px solid #bab6b6; border-radius: 2px;
      padding: 0.35em 0.8em; min-height: 44px; box-sizing: border-box;
      text-decoration: none; line-height: 2;
    }
    .b2:hover { background: #eae7e7; border-color: #7d7979; }
    .md > :first-child { margin-top: 0; }
    .md h1 { font-size: 1.7em; line-height: 1.18; font-weight: 600; margin: 0 0 0.6em; }
    .md h2 { font-size: 1.28em; line-height: 1.25; font-weight: 600; margin: 1.6em 0 0.5em; }
    .md h3 { font-size: 1.1em; line-height: 1.3; font-weight: 600; margin: 1.4em 0 0.4em; }
    .md h4, .md h5, .md h6 { font-size: 1em; font-weight: 600; margin: 1.2em 0 0.35em; }
    .md p { margin: 0 0 1em; }
    .md ul, .md ol { margin: 0 0 1em; padding: 0 0 0 1.4em; }
    .md li { margin: 0 0 0.28em; }
    .md li > ul, .md li > ol { margin: 0.28em 0 0; }
    .md blockquote {
      margin: 0 0 1em; padding: 0 0 0 1em;
      border-left: 3px solid #bab6b6; color: #605d5d;
    }
    .md pre {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.84em; line-height: 1.45;
      background: #eae7e7; padding: 0.9em 1em; overflow-x: auto;
      border-radius: 2px; margin: 0 0 1em;
    }
    .md code {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: 0.84em; background: #eae7e7; padding: 0.1em 0.35em; border-radius: 2px;
    }
    .md pre code { background: none; padding: 0; font-size: inherit; }
    .md table { border-collapse: collapse; width: 100%; margin: 0 0 1em; font-size: 0.92em; }
    .md th, .md td { border: 1px solid #bab6b6; padding: 0.4em 0.6em; text-align: left; }
    .md img { max-width: 100%; height: auto; }
    .md hr { border: none; border-top: 1px solid #bab6b6; margin: 2em 0; }
    .md a { color: #006786; text-underline-offset: 2px; }
    .md a:hover { color: #aa0b56; }
    .md input[type="checkbox"] { margin-right: 0.4em; }
    input:focus-visible, a:focus-visible { outline: 2px solid #201e1d; outline-offset: 2px; }
    ::selection { background: #cbeeff; }
    @media (prefers-color-scheme: dark) {
      body { background: #1a1918; color: #ece9e7; }
      .h { color: #bab6b6; }
      .b2 { color: #ece9e7; border-color: #605d5d; }
      .b2:hover { background: #232120; border-color: #bab6b6; }
      .md blockquote { border-left-color: #605d5d; color: #bab6b6; }
      .md pre, .md code { background: #232120; }
      .md pre code { background: none; }
      .md th, .md td, .md hr { border-color: #605d5d; }
      .md a { color: #62c5ee; }
      .md a:hover { color: #ff90b1; }
      input:focus-visible, a:focus-visible { outline-color: #ece9e7; }
      ::selection { background: #0a303e; }
    }
""".strip()


def is_markdown(path: str, content_type: str | None) -> bool:
    suffix = Path(path).suffix.lower()
    if suffix in _MD_EXTS:
        return True
    base = (content_type or "").split(";", 1)[0].strip().lower()
    return base in _MD_TYPES


def document_title(source: str, artifact_title: str | None) -> str:
    if artifact_title and artifact_title.strip():
        return artifact_title.strip()
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()[:200] or "share.c52.com"
    return "share.c52.com"


def render_markdown_body(source: str) -> str:
    raw = _RENDER(source)
    if not isinstance(raw, str):
        raw = str(raw)
    return nh3.clean(
        raw,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        url_schemes={"http", "https", "mailto"},
        link_rel="noopener noreferrer nofollow",
    )


def wrap_document(*, title: str, body_html: str, download_href: str) -> bytes:
    title_e = escape(title)
    href_e = escape(download_href, quote=True)
    html = (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        '  <meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '  <meta name="robots" content="noindex, nofollow">\n'
        f"  <title>{title_e}</title>\n"
        f"  <style>\n    {_DOCUMENT_CSS}\n  </style>\n"
        "</head>\n"
        "<body>\n"
        '  <div class="w">\n'
        '    <div class="top">\n'
        '      <p class="h">share.c52.com</p>\n'
        f'      <a class="b2" href="{href_e}">Download</a>\n'
        "    </div>\n"
        "    <!--email_off-->\n"
        f'    <article class="md">\n{body_html}\n    </article>\n'
        "    <!--/email_off-->\n"
        "  </div>\n"
        "</body>\n"
        "</html>\n"
    )
    return html.encode("utf-8")


def render_markdown_file(
    abs_path: Path,
    *,
    title: str | None,
    download_href: str = "?download=1",
) -> bytes | None:
    try:
        size = abs_path.stat().st_size
    except OSError:
        return None
    if size <= 0 or size > MAX_MARKDOWN_BYTES:
        return None
    try:
        source = abs_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    if source.startswith("\ufeff"):
        source = source[1:]
    body = render_markdown_body(source)
    return wrap_document(
        title=document_title(source, title),
        body_html=body,
        download_href=download_href,
    )
