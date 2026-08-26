# Part 5 — Spaces, Ownership, and the Artifact API

## 5.1 API conventions

**Base URL.** `https://share.c52.com/api/v1`. One host, one API. The dashboard, the MCP
endpoint, and the CLI all call it.

**Content type.** `application/json; charset=utf-8`, except file uploads
(`application/octet-stream`) and the bundle endpoint (`application/x-tar` / `application/gzip`).

**Casing.** `camelCase` in JSON, `snake_case` in the database. Nothing leaks across.

**Timestamps.** RFC 3339 with `Z`. **Sizes.** Integer bytes, never formatted strings.

**Versioning.** `v1` in the path; additive changes ship without a bump. Responses carry
`X-Share-Api-Version: 1`.

### 5.1.1 Error envelope

Every non-2xx response is exactly this and nothing else:

```json
{
  "error": {
    "code": "artifact_not_found",
    "message": "No artifact named 'postcal' in your space.",
    "detail": { "name": "postcal" },
    "requestId": "req_01JAV…"
  }
}
```

`code` is stable and part of the contract — agents branch on it. `message` is one sentence,
safe to print to a terminal, and never contains a credential or a filesystem path. For
validation failures, `detail` is
`{"fields":[{"path":"files[3].sha256","code":"invalid_hash","message":"…"}]}`. Every response,
success or failure, carries `X-Share-Request-Id`.

### 5.1.2 Pagination

Cursor-based, using the ULID primary key. `?limit=50&cursor=art_01JAV…&order=desc`, returning
`{ items, nextCursor, hasMore }`. `limit` defaults to 50, maximum 200. Offsets are not
supported anywhere.

### 5.1.3 Idempotency

Any creating `POST` accepts `Idempotency-Key` (≤255 chars), scoped to `(user, endpoint, key)`
and cached in Redis for 24 hours with the full serialised response. A replay returns the
original status and body plus `X-Share-Idempotent-Replay: true`; a replay with a different body
is `409 idempotency_key_reused`.

### 5.1.4 Request limits

| Limit | Value |
| --- | --- |
| JSON body | 10 MB |
| File upload body | `SHARE_MAX_FILE_BYTES`, default 5 GB |
| Bundle upload | 200 MB compressed / 800 MB expanded |
| URL length | 8 KB |
| Upload timeout | 3600 s (video) |
| Everything else | 30 s |

## 5.2 Spaces are hard boundaries

Every artifact belongs to exactly one user's space. There is **no API by which any principal
writes into a space it does not own** — no `userId` parameter on any write, no admin override,
no impersonation. The owning user is always derived from the credential, never from the
request.

This is the property that makes multi-user safe without a permission system: a compromised
token can damage exactly one space, and reading across spaces requires an explicit share
(§7.7).

Reading follows the same rule with one addition: a principal may read an artifact in another
space if and only if a live `share_grant` names them, or they hold a live share link.

## 5.3 Naming artifacts

Names are the address. They are chosen, not generated.

- Pattern: `^[a-z0-9][a-z0-9._-]*(/[a-z0-9][a-z0-9._-]*)*$`, at most 200 characters, at most 8
  segments. Slashes are allowed so `q3/market-report` works.
- Lowercase only. A submitted name is lowercased before validation, so `PostCal` becomes
  `postcal` rather than being rejected — agents are inconsistent about case and this is not
  worth an error.
- Unique per space among non-deleted artifacts. Trashed artifacts hold their name (§8.4), so a
  name is not reusable until the trash is emptied or the artifact is purged.
- Reserved names, per §6.3, are rejected with `422 name_reserved`.
- A name may not end in `/` and may not contain `..`, `//`, or a segment that is only dots.

Because names may contain slashes, every API path segment carrying a `{name}` is
**percent-encoded** by the client — `q3/market-report` becomes `q3%2Fmarket-report` in
`/api/v1/artifacts/q3%2Fmarket-report/links`. The server decodes exactly once and rejects any
residual `%` (§6.4 rule 1). Artifact **URLs** are unaffected: `/q3/market-report` is a real
path, not an encoded one.

**If no name is supplied**, the server generates `{adjective}-{noun}-{4 chars}` from curated
word lists — readable, typeable, and not a random hex string. Generated names are for scratch
output; anything the agent intends you to return to should be named.

**Renaming** (`PATCH`, §5.9) moves the address. The old name 404s immediately and is not
aliased. Share links are unaffected — they address the artifact, not the name (§7.2), which is
exactly why a link handed to a client survives a rename.

## 5.4 Posting an artifact — three phases

Designed so unchanged files are never re-sent, a partial upload never goes live, and a crashed
agent can resume.

### Phase 1 — declare

```
POST /api/v1/artifacts
Authorization: Bearer shr_…
Idempotency-Key: 0f1c…
```

```json
{
  "name": "postcal",
  "title": "Q4 posting calendar",
  "entryPath": "index.html",
  "tags": ["social", "grokbot"],
  "ttl": null,
  "note": "regenerated with November slots",
  "files": [
    { "path": "index.html",     "size": 18422, "contentType": "text/html", "sha256": "9f2a…" },
    { "path": "style.css",      "size": 4110,  "contentType": "text/css",  "sha256": "1b70…" },
    { "path": "img/chart.png",  "size": 90211, "contentType": "image/png", "sha256": "cc31…" }
  ]
}
```

| Field | Required | Notes |
| --- | --- | --- |
| `files` | yes | 1–`SHARE_MAX_FILES_PER_VERSION` |
| `files[].path` | yes | Normalised per §6.4 |
| `files[].size` | yes | Must match the uploaded body exactly |
| `files[].sha256` | yes | Lowercase hex, 64 chars |
| `files[].contentType` | no | Defaults from the extension map (§6.6); explicit wins |
| `name` | no | Absent → generated. Present and existing in this space → a new version of it |
| `title`, `description` | no | Explicit metadata only; never inferred |
| `entryPath` | no | Which file to serve at the artifact root. Defaults per §5.5 |
| `tags` | no | Up to 20 |
| `ttl` | no | Duration string (`30d`) or `null`. Artifacts do not expire unless asked |
| `note` | no | Version note, ≤500 chars |
| `allowFraming` | no | Default `false` → `X-Frame-Options: SAMEORIGIN`. Ignored with a warning on artifacts reached through a password-protected link (§6.6.6) |
| `csp` | no | A `Content-Security-Policy` string served verbatim with this artifact's HTML. Share imposes no default (§6.6.6) |

**Response `201`:**

```json
{
  "artifactId": "art_01JAV…",
  "name": "postcal",
  "versionId": "ver_01JAV…",
  "seq": 2,
  "uploadSessionId": "ups_01JAV…",
  "expiresAt": "2026-08-24T22:04:00Z",
  "totalFiles": 3,
  "skipped": 2,
  "uploads": [
    { "path": "img/chart.png", "sha256": "cc31…", "method": "PUT",
      "url": "https://share.c52.com/api/v1/files/cc31…?sid=ups_01JAV…&exp=1756070000&sig=…" }
  ],
  "warnings": []
}
```

`uploads` is deduplicated by hash — the same file at three paths uploads once.

Every entry in a `warnings` array has the shape `{code, message, detail?}`, and warning codes
are part of the API contract with the same stability as error codes — an agent may branch on
them. The full catalogue is §12.6.

#### 5.4.1 The dedupe oracle

`skipped` counts only files already referenced by an artifact **belonging to the calling user**.
A file held solely by another user is re-uploaded and silently deduplicated on write, costing
nothing. Without this rule, `skipped` would answer "does anyone on this instance hold these
exact bytes", which is a real leak on a multi-user instance and free to close.

### Phase 2 — upload

```
PUT /api/v1/files/{sha256}?sid={uploadSessionId}&exp={unix}&sig={hmac}
Content-Type: application/octet-stream
Content-Length: 90211
```

- The URL is signed with `secret_key` over `sha256 | sid | exp`, valid for the session's
  lifetime. Tampered or expired → `403 upload_signature_invalid`.
- **No `Authorization` header is needed** — the signature is the credential, so an agent can
  hand URLs to a parallel uploader without sharing its token.
- Digest mismatch → `400 file_hash_mismatch`, body quarantined, the pending set unchanged so a
  retry works. Size mismatch → `400 file_size_mismatch`.
- A file the server already holds returns `200` immediately without reading the body; clients
  must tolerate a response arriving before they finish sending.
- Up to 16 concurrent uploads per session; beyond that, `429 too_many_uploads` with
  `Retry-After`. Recommended agent concurrency is 4 for large files, 8 for small.

Response: `{ "sha256": "cc31…", "size": 90211, "remaining": 0 }` — so a client knows it is
ready to commit without polling.

**Resuming.** `GET /api/v1/uploads/{uploadSessionId}` returns the session with freshly signed
URLs for whatever is still pending.

### Phase 3 — commit

```
POST /api/v1/artifacts/{name}/versions/{versionId}/commit
```

The `seq` shown at declare time is provisional. It is **assigned at commit** under a row lock
on the artifact, so two agents declaring concurrently cannot collide on
`UNIQUE (artifact_id, seq)`.

In one transaction: verify every declared hash exists and every size matches
(`409 files_missing` / `409 file_size_mismatch`, nothing mutated); check quota
(`413 quota_exceeded` with `currentBytes`, `projectedBytes`, `quotaBytes`); `COPY` the
`version_file` rows and increment reference counts; derive `kind` from the manifest shape;
resolve `entry_path` per §5.5; set the artifact's `live_version_id`; mark the session
committed; write `artifact.post` to the audit log.

After commit, outside the transaction: invalidate the resolution cache, queue precompression,
mark the user dirty for a storage recompute.

**Response `200`:**

```json
{
  "artifactId": "art_01JAV…",
  "name": "postcal",
  "url": "https://share.c52.com/postcal",
  "seq": 2,
  "kind": "bundle",
  "entryPath": "/index.html",
  "fileCount": 3,
  "totalBytes": 112743,
  "visibility": "private",
  "shareLinks": 0,
  "warnings": []
}
```

`visibility` is always `private` on a fresh post. Posting never creates a share link — that is
a separate call with a separate scope.

The pointer flip is the only moment the artifact changes. There is no window where half a
version is live, and a viewer mid-request against the old version keeps being served from
immutable files.

## 5.5 Entry path resolution

For a bundle, something has to answer at the artifact root. In order:

1. An explicit `entryPath` in the request, if it exists in the manifest. If it was supplied but
   is not in the manifest, resolution falls through to the next rule and an
   `entry_path_not_found` warning is returned — a post is never failed over a cosmetic field.
   On `PATCH`, where there is no manifest to fall back through, the same condition is
   `422 invalid_entry_path`.
2. `/index.html`.
3. If exactly one file is HTML, that file.
4. If exactly one file exists at all, that file.
5. Otherwise none — the artifact root renders the file-listing page (§6.5) and a
   `no_entry_point` warning is returned.

A single-file artifact always gets its own file as the entry path, so `share.c52.com/report`
renders `report.pdf` directly rather than a listing with one row.

## 5.6 One-shot bundle upload

Three round trips is two too many for small things.

```
POST /api/v1/artifacts/bundle?name=postcal&title=…&entryPath=index.html
Content-Type: application/x-tar          (or application/gzip)
```

- ≤200 MB compressed, ≤800 MB expanded, ≤5,000 entries.
- Symlinks, hardlinks, device nodes, and traversing or absolute paths are rejected outright
  with `422 invalid_archive`.
- Expansion ratio over 100:1 → `422 archive_ratio_exceeded`.
- Returns the same body as commit.

The CLI and MCP server choose this path automatically under 25 MB and 200 files, and the
three-phase path above it, where deduplication starts to pay. Overridable with
`--bundle` / `--no-bundle`.

## 5.7 Abandoned sessions

Every 15 minutes the worker marks `open` sessions past `expires_at` as `expired` and deletes
the draft version row — no `version_file` rows exist, so no reference counts move. Uploaded
files become unreferenced and are collected after the 24-hour grace window.

Committing an expired session returns `409 upload_session_expired`. Re-declaring is cheap: all
the files are already on the server, so the new session's `uploads` array will be empty.

## 5.8 Reading

```
GET /api/v1/artifacts?limit=50&cursor=…&q=calendar&tag=social&kind=bundle&order=updated_desc
GET /api/v1/artifacts?shared=true            → shared with me (§7.7)
GET /api/v1/artifacts?trashed=true           → the trash
GET /api/v1/artifacts/{name}
GET /api/v1/artifacts/{name}/files?version=…
GET /api/v1/artifacts/{name}/files/content?path=/index.html&version=…
```

Item shape:

```json
{
  "id": "art_01JAV…", "name": "postcal", "title": "Q4 posting calendar",
  "kind": "bundle", "url": "https://share.c52.com/postcal",
  "owner": { "handle": "robert", "isSelf": true },
  "visibility": "shared",           // 'private' | 'shared' | 'granted'
  "shareLinks": [ { "id": "lnk_…", "expiresAt": "…", "hasPassword": true,
                    "label": "Fairfield team", "viewCount": 3 } ],
  "grants": [ { "handle": "sarah", "createdAt": "…" } ],
  "seq": 2, "versionCount": 2, "fileCount": 3, "totalBytes": 112743,
  "entryPath": "/index.html", "tags": ["social","grokbot"],
  "ttlExpiresAt": null, "pinned": false,
  "viewCount": 41, "lastViewedAt": "…",
  "createdAt": "…", "updatedAt": "…",
  "createdBy": { "type": "token", "id": "shr_01J…", "name": "grokbot@macmini" }
}
```

`q` matches **name, title, description, and tags only** — never file contents (P5). Matching is
trigram-based so partial and misspelled words work (§8.7).

`files/content` streams a file with its recorded content type. This is how an agent inspects
what it posted without going through the artifact URL, and the only way to read a
password-protected artifact's bytes with a token.

## 5.9 Updating metadata

```
PATCH /api/v1/artifacts/{name}
```

Accepts any subset of `name`, `title`, `description`, `entryPath`, `tags`, `ttl`, `pinned`,
`allowFraming`, `csp`.
Absent fields are unchanged; `null` clears where nullable.

- Changing `name` moves the address immediately; the old one 404s. Share links keep working.
- Changing `entryPath` takes effect without reposting.
- `ttl` accepts a duration from now, an absolute timestamp, or `null` to clear.
- **Visibility is not settable here.** Sharing has its own endpoints (§7). A `PATCH` containing
  `visibility` or `shareLinks` is `422 use_share_endpoint` — a loud failure rather than a
  silent ignore.

## 5.10 Copying

```
POST /api/v1/artifacts/{name}/copy      { "name": "…", "title": "…" }
```

Creates a new artifact **in the caller's own space** whose first version references the same
files — zero bytes copied. Works on your own artifacts and on anything shared with you, which
is the "save a copy so it survives their deletion" path from §7.7.

The copy is always private with no share links, whatever the source had, and records
`copied_from`. Copying something shared with you is audited on both sides, and the original
owner sees it in their artifact's activity — no silent duplication of someone else's work.

## 5.11 Deleting

```
DELETE /api/v1/artifacts/{name}                 → to trash, restorable 30 days
DELETE /api/v1/artifacts/{name}?purge=true      → permanent, needs artifacts:delete
POST   /api/v1/artifacts/{name}/restore         → back from trash
```

Trashing revokes every share link and grant on the artifact immediately — a trashed artifact is
not viewable by anyone, including people who held a link. Restoring does **not** bring the
links back; they must be recreated. That asymmetry is deliberate: undoing a deletion should not
silently re-open access.

## 5.12 Error codes

| HTTP | Code | Meaning |
| --- | --- | --- |
| 400 | `file_hash_mismatch` | Uploaded bytes do not match the digest in the URL |
| 400 | `file_size_mismatch` | Uploaded length differs from the declared size |
| 403 | `upload_signature_invalid` | Signed URL expired or tampered |
| 403 | `not_your_artifact` | Write attempted against another space |
| 404 | `artifact_not_found` | No such name in the addressed space |
| 404 | `version_not_found` | No such version |
| 404 | `file_not_found` | Path not in the requested version |
| 409 | `name_taken` | Name in use, including by a trashed artifact |
| 409 | `files_missing` | Commit before all uploads finished |
| 409 | `upload_session_closed` | Already committed or aborted |
| 409 | `upload_session_expired` | Past its window |
| 409 | `idempotency_key_reused` | Same key, different body |
| 413 | `quota_exceeded` | User storage limit |
| 413 | `artifact_too_large` | One version over the artifact ceiling |
| 413 | `file_too_large` | One file over the file ceiling |
| 413 | `too_many_files` | Over the per-version file count |
| 422 | `invalid_name` | Failed the name pattern |
| 422 | `name_reserved` | Collides with a reserved path (§6.3) |
| 422 | `invalid_path` | A file path failed normalisation (§6.4) |
| 422 | `dotfile_rejected` | A file path began with a dot segment other than `/.well-known/` (§6.4) |
| 422 | `invalid_entry_path` | `PATCH` set an `entryPath` not present in the live version |
| 422 | `path_case_collision` | Two paths differ only by case |
| 422 | `invalid_archive` | Bundle held a symlink, device, or traversing path |
| 422 | `archive_ratio_exceeded` | Decompression bomb |
| 422 | `use_share_endpoint` | Visibility passed to `PATCH` |
| 429 | `too_many_uploads` | Over 16 concurrent on one session |
| 429 | `rate_limited` | See §10.2 |
