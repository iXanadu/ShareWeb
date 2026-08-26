# Part 6 — The URL Model, Resolution, and Serving

## 6.1 Four kinds of URL

Everything Share serves falls into one of four shapes, and they never overlap.

| Shape | Example | Who reaches it |
| --- | --- | --- |
| **Root space** | `share.c52.com/postcal` | The root user, signed in |
| **User space** | `share.c52.com/~sarah/deck` | Sarah signed in, plus anyone she granted |
| **Share link** | `share.c52.com/s/9fq2n4kw…` | Anyone holding it, until it expires |
| **Application** | `share.c52.com/~/artifacts` | Signed-in users |

## 6.2 Root and canonical forms

Every user has a handle, including the root user. The root user's artifacts resolve at **both**
`/postcal` and `/~robert/postcal`; the second is the canonical form and always exists. Everyone
else has only the `~handle` form.

This means the root flag is a routing convenience rather than a structural special case. If it
ever moved, existing root-form links would `301` to the canonical form rather than break, and
nothing in the data model would change.

The dashboard shows the short form for the root user because that is what they will type and
send.

## 6.3 The application namespace, and why `/~/`

Artifacts living at the root compete with the application's own pages: is `/settings` a
settings screen or an artifact named `settings`? A reserved-word list would then have to grow
every time a page is added, and adding a page could break a URL already sent to someone.

The fix is that the application lives under **`/~/`** — a bare tilde, which cannot be a handle,
so collision is impossible by construction rather than by list maintenance.

```
/~/artifacts      /~/artifacts/{name}    /~/shared       /~/trash
/~/search         /~/tokens              /~/settings     /~/security
/~/authorize      /~/help                /~/users
```

The complete reserved list is therefore small and fixed:

```
~   s   api   mcp   auth   internal   .well-known   robots.txt   favicon.ico   install.sh
how-it-works   for-agents
```

Public marketing pages occupy `/`, `/how-it-works` and `/for-agents`. They are not artifacts.

Handles additionally may not be any of: `www`, `admin`, `root`, `system`, `support`, `help`,
`about`, `status`, `null`, `undefined`.

## 6.4 Path normalisation

Applied to every declared file path at post time, and to every request path at serve time.
Failure is `422 invalid_path` (post) or `404` (serve).

1. Convert `\` to `/`; percent-decode once, then reject any remaining `%` that would decode
   further (double-encoding is always an attack).
2. Reject any segment equal to `.` or `..`, any empty segment, any Windows drive prefix.
3. Reject NUL and any control character below `0x20`.
4. Apply Unicode NFC; reject characters in the Unicode `Cf` category (homograph tricks in file
   listings).
5. Reject a path over 1,024 bytes UTF-8, any segment over 255 bytes, or more than 32 segments.
6. **Case-collision check at post time:** two paths in one manifest differing only by case are
   `422 path_case_collision`. The store is case-sensitive; agents on macOS routinely produce
   manifests that cannot round-trip.
7. Paths beginning with a dot segment — `/.git/`, `/.env`, `/.ssh/` — are **rejected** at post
   time with `422 dotfile_rejected`. `/.well-known/` is the sole exception and is served
   normally.

Stored form: leading slash, no trailing slash.

The CLI additionally refuses to walk `.git`, `.env*`, `*.pem`, `*.key`, `id_rsa*`,
`node_modules`, `__pycache__`, and `.DS_Store` before a manifest is ever built (§9.5). Server
rules are the backstop; the client rule is what actually catches the mistake.

## 6.5 Resolution and the authorize algorithm

`/internal/authorize` is the single decision point for artifact requests. Complete logic, in
order. Steps 2 and 3 must not be reordered — resolving before checking access is what creates
timing oracles.

```python
def authorize(path, headers, client_ip) -> Response:
    # 1. Which space, and what remains of the path?
    #    /~sarah/deck/style.css  → space=sarah, rest=/deck/style.css
    #    /postcal/style.css      → space=root,  rest=/postcal/style.css
    space, rest = split_space(path)
    if space is None:
        return not_found()

    # 2. Longest-prefix artifact match. '/q3/report/img/a.png' tries
    #    'q3/report/img/a.png', then 'q3/report/img', then 'q3/report' — first hit wins.
    artifact, filepath = resolve_longest_prefix(space, rest)
    if artifact is None or artifact.trashed or artifact.ttl_expired_now():
        return not_found()

    # 3. Access check, before anything else about the artifact is consulted.
    actor = identify(headers)          # session | recipient session | none
    if not can_view(actor, artifact):
        return not_found()             # P1: identical to step 2's response

    # 4. File resolution within the version (§6.6).
    resolved = resolve_file(artifact.live_version, filepath)
    if resolved is None:
        return not_found_in_artifact(artifact)

    # 5. Serve.
    return ok(file=blob_path(resolved.sha256),
              content_type=resolved.content_type,
              cache_control=cache_for(artifact, actor, resolved),
              disposition=disposition_for(resolved),
              csp=csp_for(resolved))
```

`can_view` is the whole access model, and it is four lines:

```python
def can_view(actor, artifact):
    if actor.is_user and actor.user_id == artifact.user_id:        return True   # owner
    if actor.is_user and has_live_grant(artifact, actor.user_id):  return True   # shared with
    if actor.is_recipient and actor.link.artifact_id == artifact.id
       and actor.link.live():                                      return True   # share link
    return False
```

There is no fifth case. No admin bypass, no "public" flag, no network exemption.

### 6.5.1 Longest-prefix matching

Because names may contain slashes, `/q3/report/img/a.png` is ambiguous between "artifact
`q3/report`, file `/img/a.png`" and "artifact `q3/report/img/a.png`". Longest match wins, which
makes it deterministic. The candidate set is at most 8 lookups (the segment limit), all against
the unique index on `(user_id, name)`, and the whole resolution is cached for 60 seconds.

Posting an artifact whose name is a strict prefix of an existing artifact's name is allowed but
returns a `shadowing_name` warning — `q3/report` shadows nothing, but creating `q3` when
`q3/report` exists means `/q3/report` now resolves to a file inside `q3` if one is there.

### 6.5.2 Indistinguishability

P1 requires that an artifact you cannot see is indistinguishable from one that never existed.
Three things make that true:

1. **Identical body** — the same not-found page, no artifact-specific content.
2. **Identical headers** — no `X-Share-Artifact`, no differing cache directives.
3. **Comparable timing** — negative resolutions are cached in Redis with the same TTL as
   positive ones, and on a cache miss the same indexed queries run. T-PRIV-01 measures both
   paths over 1,000 requests and asserts a median difference under 2 ms.

## 6.6 Serving files

### 6.6.1 Resolution within a version

Given the remaining path `P` and the live version's manifest `M`:

1. `P` is empty or `/` → serve `entry_path`; if none, render the listing page.
2. Exact match in `M` → serve it.
3. `P` ends in `/` → try `P + "index.html"`.
4. `P + "/index.html"` exists → `308` to `P + "/"`, preserving the query string, so relative
   links inside the document resolve.
5. `P + ".html"` exists → serve it.
6. `/404.html` exists in the artifact → serve it with status `404`.
7. Otherwise the standard not-found page with status `404`.

There is no SPA fallback. Share hosts artifacts, not applications (N1), and a catch-all that
returns HTML for a missing `.json` causes more confusion than it prevents.

### 6.6.2 The listing page

When a bundle has no entry point, its root renders a plain file listing — name, size, type,
one link each — styled with the same inline CSS as the error pages, no external requests.
This is also what a multi-file, non-HTML artifact looks like: post three PDFs together and the
artifact root is a tidy index of them.

Listings are only ever shown for the artifact being addressed. There is no listing of a space,
ever, for anyone.

### 6.6.3 Content types

The manifest's `contentType` wins; otherwise it derives from the extension.

| Ext | Type | | Ext | Type |
| --- | --- | --- | --- | --- |
| `.html` `.htm` | `text/html; charset=utf-8` | | `.pdf` | `application/pdf` |
| `.css` | `text/css; charset=utf-8` | | `.json` | `application/json` |
| `.js` `.mjs` | `text/javascript; charset=utf-8` | | `.txt` `.md` | `text/plain; charset=utf-8` |
| `.svg` | `image/svg+xml` | | `.csv` | `text/csv; charset=utf-8` |
| `.png` `.jpg` `.jpeg` `.webp` `.gif` `.avif` | the image type | | `.woff2` | `font/woff2` |
| `.mp4` `.webm` `.mov` | the video type | | `.wasm` | `application/wasm` |
| `.mp3` `.m4a` `.wav` | the audio type | | anything else | `application/octet-stream` |

Sanitising rules, applied to every response:

- `X-Content-Type-Options: nosniff` always.
- A declared `text/html` on a path with an image, video, or font extension is **coerced** to the
  extension's type. Uploading an HTML payload named `logo.png` and declaring it HTML is stored
  XSS on the artifact's own origin; the extension wins.
- `.svg` is served with `Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'`
  so scripts inside SVG are inert.
- Any type not in the table and not explicitly declared is `application/octet-stream` with
  `Content-Disposition: attachment` — unknown binaries download rather than render.

Compressible for precompression: `text/*`, `application/json`, `application/xml`,
`application/javascript`, `image/svg+xml`, `application/wasm`. Never images, video, audio, or
PDFs.

### 6.6.4 Range requests and video

Caddy's `file_server` handles `Range`, `If-Range`, and multipart ranges natively, which is what
makes seeking work in a video element. The authorisation call runs first, once, per request;
the byte serving happens afterwards with no application involvement. A 2 GB MP4 therefore
streams at disk speed, and a seek is a fresh authorised range request.

Video artifacts get no transcoding, no thumbnail generation, and no probing — Share does not
open the file (P5). The dashboard's video viewer uses a native `<video>` element and whatever
the browser can play. The docs say plainly that H.264/AAC in MP4 is the format that works
everywhere.

### 6.6.5 Cache-Control

| Case | Header |
| --- | --- |
| Owner or grantee viewing their own artifact | `private, max-age=300` |
| Any file reached through a share link | `private, no-store` |
| Immutable-looking asset (content hash in the filename) | `private, max-age=31536000, immutable` |
| The listing page and error pages | `no-store` |

Everything is `private`. Nothing Share serves may be cached by a shared proxy, because
everything requires authorisation. `ETag` is the file's SHA-256; `Last-Modified` is the
version's creation time. Conditional requests return `304` from Caddy — the authorize call
still ran, so a `304` on an artifact whose access was just revoked cannot happen.

**The share-link row wins every collision.** A content-hashed asset inside a bundle
(`app.a1b2c3.js`) matches both the immutable row and the share-link row; reached through
`/s/{token}` it is `no-store`, without exception. Otherwise the assets a page loads most of would
be the ones that survive the link's death in a borrowed browser, which is precisely what that row
exists to prevent. The cost is one conditional request per asset per recipient.

### 6.6.6 Constant headers

Set in Caddy (§2.4) on every artifact response:

```
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
X-Robots-Tag: noindex, nofollow
Permissions-Policy: interest-cohort=()
```

Deliberately absent: `Server`, anything naming a version, an owner, or an artifact ID.

`X-Frame-Options` is `SAMEORIGIN` by default. An artifact may opt out by posting with
`"allowFraming": true`, which is needed for a dashboard someone embeds elsewhere. Artifacts
reached through a **password-protected** share link may not opt out — framing a password gate
is a credential-theft path — and the flag is ignored with a warning.

Share imposes no default `Content-Security-Policy` on artifact content, because
agent-generated pages routinely use inline styles and scripts and a default would break most of
them silently. An artifact may declare its own `csp` string at post time and it is served
verbatim.

## 6.7 robots.txt

`GET /robots.txt` is served by the API, always, and always returns:

```
User-agent: *
Disallow: /
```

There is no per-artifact override and no `indexable` flag. Nothing here is meant to be found by
search; the artifacts that are public are protected by link entropy, and an indexed share link
would defeat that completely.

## 6.8 Serving error codes

| HTTP | Code | Meaning |
| --- | --- | --- |
| 401 | `recipient_auth_required` | Share link needs its password |
| 401 | `recipient_auth_failed` | Wrong password |
| 404 | `not_found` | Everything indistinguishable: unknown name, no access, expired TTL, revoked link, missing file |
| 410 | `link_expired` | **Only** on the `/s/{token}` entry page, where a recipient benefits from knowing the link died rather than being told the artifact never existed. Never leaks the artifact's name or owner (§7.6) |
| 429 | `rate_limited` | §10.2 |
