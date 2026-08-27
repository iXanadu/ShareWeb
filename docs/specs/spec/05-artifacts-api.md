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

Any creating `POST` accepts `Idempotency-Key` (≤255 chars), scoped to `(user, endpoint, key)` and
stored for 24 hours with the full serialised response in `idempotency_record` (§3.9.1) — in
Postgres, not the cache, because a Redis flush must not turn a retried post into a second
artifact. A replay returns the
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
them. The full catalogue is in §5.12 beside the error codes.

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

Every 15 minutes the worker marks `open` sessions past `expires_at` as `expired` and clears their
`version_id`, then deletes the orphaned draft version row — no `version_file` rows exist, so no
reference counts move. Uploaded files become unreferenced and are collected after the 24-hour
grace window.

`upload_session.version_id` is therefore **nullable and does not cascade**. If it did, deleting
the draft version would delete the session row with it, the `expired` state could never be
observed, and the next paragraph's error would be unreachable — a lapsed agent would get
`404 artifact_not_found` and no way to tell "your window closed, re-declare" from "that name does
not exist".

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
  "ttlExpiresAt": null, "pinned": false, "allowFraming": false, "csp": null,
  "viewCount": 41, "lastViewedAt": "…",
  "createdAt": "…", "updatedAt": "…",
  "createdBy": { "type": "token", "id": "shr_01J…", "name": "grokbot@hosta" }
}
```

**Which URL `url` carries.** The short root-space form (`/postcal`) appears only when the response
is going to the artifact's owner *and* that owner is the root user. In every other response —
a grantee's listing, `?shared=true`, an MCP result naming another user's artifact — it is the
canonical `~handle` form (§6.2). A recipient viewing through a share link never receives a `url`
field at all, since the artifact's real address is exactly what §7.6 withholds.

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

### 5.12.1 Warning codes

Warnings ride along on a successful response in a `warnings` array of `{code, message, detail?}`
objects. **They carry the same stability guarantee as error codes** — an agent may branch on them,
and one is never renamed. A warning never means the operation partly failed; it means something
about the result is worth knowing.

| Code | Raised when | §ok |
| --- | --- | --- |
| `no_entry_point` | No file resolves at the artifact root, so it will serve a listing | §5.5 |
| `entry_path_not_found` | An explicit `entryPath` was not in the manifest; resolution fell through | §5.5 |
| `shadowing_name` | The new name is a strict prefix of an existing artifact's name | §6.5.1 |
| `ttl_with_live_links` | A TTL was set on an artifact whose live links will die with it | §8.5 |
| `framing_ignored_password_link` | `allowFraming` was ignored because the request came through a password-protected link | §6.6.6 |
| `possible_credential_form` | A posted page has a password input in a form posting off-origin. Advisory to the owner only, never blocking | §10.5 |
| `archive_ratio_high` | A bundle expanded steeply but under the hard 100:1 limit | §5.6 |
| `quota_warning` | The commit put the user over 80% or 95% of quota | §10.3 |

## 5.13 What the dashboard's API must provide

The dashboard calls endpoints this part does not specify: token management, settings, passkey and
session listing, tags, users, invites, device approval (§4.6.2), and an artifact archive. Their
shapes are the build team's to define, in `05a-dashboard-api.md`, alongside the code.

**Four of them are not free choices**, because a screen's honesty depends on what they return.
These are requirements; the shapes around them are not.

### 5.13.1 The `settings` keys and their defaults

`app_user.settings` is schemaless in Postgres but not in the product. These keys exist, with these
defaults, and each one is a decision made elsewhere in this document rather than a preference:

| Key | Default | Fixed by |
| --- | --- | --- |
| `defaultShareTtl` | `14d` | §7.3. Preselected on the create-link dialog and marked as the user's default |
| `notifyOnShare` | **`true`** | §7.3. The owner learns by email every time anything of theirs becomes reachable without a sign-in, *including when an agent does it*. This default is the mechanism P3 rests on and must not be flipped |
| `notifyOnLinkExpiring` | `true` | §10.8, with the T−24 h mail |
| `versionRetention` | `{keepLast: 20, keepDays: 365, keepPinned: true, minimum: 3}` | §8.3 |
| `staleDays` | `90` | §8.6 |
| `timeZone` | `UTC` | §11.29.3. Display only; every stored time stays UTC |
| `notifyOnQuota`, `notifyOnTokenCreated`, `notifyOnAnomaly` | `true` | §10.8 |
| `firstRun` | `{}` | §11.6 checklist dismissals |

Two notifications in §10.8 — recovery-code use and passkey counter regression — **have no settings
key at all.** They are not defaults that happen to be on; they are unconditional, because they are
the two that mean someone may be getting in. A key that could disable them must not exist.

### 5.13.2 `GET /api/v1/status`

Five screens read this, and one of its jobs is behavioural rather than informational: at 100% of
quota, **posting fails while reading, sharing and deleting continue** (§10.3). A response that does
not let the dashboard say which of those is true leaves a user unable to see the way out.

It must report, for the caller: `storageBytes`, `quotaBytes`, `artifactCount`, `trashBytes`,
`staleBytes`, and a stale artifact count. For the root user, additionally: `version`,
`uptimeSeconds`, `diskFreeBytes`, `queueDepths`, `lastBackupAt` with its outcome, and
`migrationRevision`. A non-root caller gets the instance fields omitted, not nulled — §11.28's
reduced view exists so a user can answer "is it me or the server" without learning host details.

`trashBytes` and `staleBytes` are load-bearing: they are the two numbers §11.25 turns into "what
would free space", and the trash figure is why §8.4 says the trash counts against quota.

### 5.13.3 The share-link list

`GET /api/v1/artifacts/{name}/links` is the sharing panel (§11.12), which is the one screen whose
whole purpose is telling the owner the truth about who can reach something. Per link it must carry
`id`, `label`, `displayPrefix`, `expiresAt`, `hasPassword`, `viewCount`, `viewerDays`,
`lastViewedAt`, `maxViews`, `createdAt`, `createdBy`, and `revokedAt`.

Three of those are there for specific reasons. **`createdBy`** because a link an agent made is
exactly the one the owner most needs to notice. **`revokedAt`** because revoked and expired links
stay listed — what used to be reachable is part of the record, so this endpoint returns them rather
than filtering them out, and the caller separates live from ended using the one definition in
§7.7.2. **`displayPrefix` and not a URL**, because §7.3 stores only the token's hash: the full
address is unrecoverable after the response that created it, and the panel says so plainly instead
of offering a copy control that cannot work.

### 5.13.4 The activity feed

`GET /api/v1/artifacts/{name}/activity` (§8.8) merges audit events and daily view rollups. Every
entry must name its actor as one of a user handle, a token with its name, or `system` — an
unattributed event is not useful, and attribution is the property that makes full agent autonomy
acceptable (§8.1).

View entries carry a count, a date, and which link was used. **They never carry an identity, an
address, or an approximate location**, and no shape here may be extended to allow one: the daily
salted hash of §3.8 supports "3 viewers on Tuesday" and cannot support "which three". That is P6,
and it is a property of the data rather than a policy about it.
