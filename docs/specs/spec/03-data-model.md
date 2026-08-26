# Part 3 — Data Model and Storage

## 3.1 Conventions

- PostgreSQL 16. Timestamps are `timestamptz`, stored UTC.
- Primary keys are prefixed ULIDs: `{prefix}_{26-char Crockford base32}`. They sort by creation
  time, so `ORDER BY id` is a valid cheap ordering and cursor pagination is trivial.
- Soft deletes use `trashed_at` (recoverable, §8.4) or `deleted_at` (gone at the next
  collection). Every read filters both unless explicitly listing trash.
- Sizes are `bigint` bytes. No floats.
- JSONB only for genuinely schemaless payloads (audit metadata, user settings).
- Alembic migrations; the initial one creates tables in dependency order and adds the two
  forward-referencing foreign keys (`artifact.live_version_id`, `artifact_version.artifact_id`)
  afterwards.
- `CREATE EXTENSION citext;` and `CREATE EXTENSION pg_trgm;` in the first migration — the
  latter powers name and title search (§8.7).

### 3.1.1 ID prefixes

| Prefix | Entity | Prefix | Entity |
| --- | --- | --- | --- |
| `usr_` | user | `art_` | artifact |
| `pky_` | passkey credential | `ver_` | artifact version |
| `ses_` | session | `ups_` | upload session |
| `shr_` | API token (also the token prefix) | `lnk_` | share link |
| `inv_` | invite | `grn_` | share grant (to a user) |
| `rcp_` | recipient session | `aud_` | audit event |

## 3.2 Entity overview

```
app_user ──< passkey_credential
         ──< recovery_code
         ──< session
         ──< api_token
         ──< artifact ──< artifact_version ──< version_file >── file
         │           ├──< share_link ──< recipient_session
         │           ├──< share_grant >── app_user   ("shared with me")
         │           └──< artifact_tag
         └──< audit_event
```

## 3.3 Users and credentials

```sql
CREATE TABLE app_user (
    id              text PRIMARY KEY,
    email           citext NOT NULL UNIQUE,
    display_name    text,
    handle          citext UNIQUE,          -- namespace label; NULL only for the root user
    is_root         boolean NOT NULL DEFAULT false,  -- holds the bare root namespace
    quota_bytes     bigint NOT NULL DEFAULT 536870912000,
    storage_bytes   bigint NOT NULL DEFAULT 0,
    artifact_count  integer NOT NULL DEFAULT 0,
    settings        jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now(),
    last_seen_at    timestamptz,
    disabled_at     timestamptz,
    CONSTRAINT handle_format CHECK (
        handle IS NULL OR handle ~ '^[a-z0-9]([a-z0-9-]{0,30}[a-z0-9])?$')
);
-- Exactly one root user.
CREATE UNIQUE INDEX one_root_user ON app_user ((true)) WHERE is_root;
```

The root user still has a handle. Their artifacts are reachable at both `/name` and
`/~handle/name` (§6.2), so promoting or demoting the root flag never breaks a link — the
canonical form always exists.

```sql
CREATE TABLE passkey_credential (
    id              text PRIMARY KEY,
    user_id         text NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    credential_id   bytea NOT NULL UNIQUE,   -- raw WebAuthn credential ID
    public_key      bytea NOT NULL,          -- COSE key
    sign_count      bigint NOT NULL DEFAULT 0,
    transports      text[] NOT NULL DEFAULT '{}',
    aaguid          uuid,
    backup_eligible boolean NOT NULL DEFAULT false,
    backup_state    boolean NOT NULL DEFAULT false,
    name            text NOT NULL,           -- "1Password", "MacBook Touch ID"
    created_at      timestamptz NOT NULL DEFAULT now(),
    last_used_at    timestamptz,
    revoked_at      timestamptz
);
CREATE INDEX ON passkey_credential (user_id) WHERE revoked_at IS NULL;

CREATE TABLE recovery_code (
    id              text PRIMARY KEY,
    user_id         text NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    code_hash       bytea NOT NULL,          -- argon2id: this one IS low-entropy-ish and typed
    created_at      timestamptz NOT NULL DEFAULT now(),
    used_at         timestamptz,
    used_ip         inet
);
CREATE INDEX ON recovery_code (user_id) WHERE used_at IS NULL;

CREATE TABLE session (
    id              text PRIMARY KEY,
    user_id         text NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    token_hash      bytea NOT NULL UNIQUE,
    passkey_id      text REFERENCES passkey_credential(id),  -- which key signed in
    created_at      timestamptz NOT NULL DEFAULT now(),
    last_seen_at    timestamptz NOT NULL DEFAULT now(),
    expires_at      timestamptz NOT NULL,
    ip              inet,
    user_agent      text,
    revoked_at      timestamptz
);
CREATE INDEX ON session (user_id) WHERE revoked_at IS NULL;

CREATE TABLE api_token (
    id              text PRIMARY KEY,        -- shr_...
    user_id         text NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    name            text NOT NULL,           -- "claude-code@macmini"
    display_prefix  text NOT NULL,           -- first 12 chars, shown in the UI
    token_hash      bytea NOT NULL UNIQUE,   -- sha256; tokens are 256-bit random
    scopes          text[] NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    last_used_at    timestamptz,
    last_used_ip    inet,
    expires_at      timestamptz,
    revoked_at      timestamptz
);
CREATE INDEX ON api_token (user_id) WHERE revoked_at IS NULL;

CREATE TABLE invite (
    id              text PRIMARY KEY,
    email           citext NOT NULL,
    handle          citext NOT NULL,         -- the namespace they will get
    token_hash      bytea NOT NULL,
    invited_by      text NOT NULL REFERENCES app_user(id),
    expires_at      timestamptz NOT NULL,
    accepted_at     timestamptz,
    revoked_at      timestamptz,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ON invite (email) WHERE accepted_at IS NULL AND revoked_at IS NULL;
```

WebAuthn challenges are **not** stored in Postgres — they live in Redis at
`sh:wa:{challengeId}` with a 300-second TTL, because they are single-use and worthless
afterwards.

## 3.4 Artifacts, versions, files

```sql
CREATE TYPE artifact_kind AS ENUM ('bundle', 'page', 'document', 'image', 'video', 'file');

CREATE TABLE artifact (
    id              text PRIMARY KEY,
    user_id         text NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    name            text NOT NULL,           -- 'postcal', 'q3/market-report'
    title           text,                    -- explicit only, never inferred (P5)
    description     text,
    kind            artifact_kind NOT NULL,
    live_version_id text,                    -- FK added after artifact_version exists
    entry_path      text,                    -- '/index.html' for bundles, '/report.pdf' for a single file
    ttl_expires_at  timestamptz,             -- NULL = keeps until deleted
    pinned          boolean NOT NULL DEFAULT false,
    view_count      integer NOT NULL DEFAULT 0,
    last_viewed_at  timestamptz,
    created_by_token text REFERENCES api_token(id),
    copied_from     text REFERENCES artifact(id),   -- 'save a copy' provenance
    allow_framing   boolean NOT NULL DEFAULT false,  -- §6.6.6; ignored on password-protected links
    csp             text,                    -- served verbatim with this artifact's HTML (§6.6.6)
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    trashed_at      timestamptz,
    deleted_at      timestamptz,
    CONSTRAINT name_format CHECK (
        name ~ '^[a-z0-9][a-z0-9._-]*(/[a-z0-9][a-z0-9._-]*)*$' AND length(name) <= 200)
);
CREATE UNIQUE INDEX ON artifact (user_id, name) WHERE deleted_at IS NULL;
CREATE INDEX ON artifact (user_id, updated_at DESC) WHERE trashed_at IS NULL AND deleted_at IS NULL;
CREATE INDEX ON artifact (trashed_at) WHERE trashed_at IS NOT NULL;
CREATE INDEX ON artifact (ttl_expires_at) WHERE ttl_expires_at IS NOT NULL AND trashed_at IS NULL;
CREATE INDEX artifact_name_trgm ON artifact USING gin (name gin_trgm_ops);
CREATE INDEX artifact_title_trgm ON artifact USING gin (title gin_trgm_ops);

CREATE TABLE artifact_version (
    id              text PRIMARY KEY,
    artifact_id     text NOT NULL REFERENCES artifact(id) ON DELETE CASCADE,
    seq             integer NOT NULL,        -- 1, 2, 3… human-facing version number
    file_count      integer NOT NULL,
    total_bytes     bigint NOT NULL,
    entry_path      text,
    note            text,
    created_by_token text REFERENCES api_token(id),
    created_by_user  text REFERENCES app_user(id),
    created_at      timestamptz NOT NULL DEFAULT now(),
    deleted_at      timestamptz,
    UNIQUE (artifact_id, seq)
);
CREATE INDEX ON artifact_version (artifact_id, seq DESC) WHERE deleted_at IS NULL;

CREATE TABLE version_file (
    version_id      text NOT NULL REFERENCES artifact_version(id) ON DELETE CASCADE,
    path            text NOT NULL,           -- normalised, leading slash
    sha256          bytea NOT NULL REFERENCES file(sha256),
    size            bigint NOT NULL,
    content_type    text NOT NULL,
    PRIMARY KEY (version_id, path)
);
CREATE INDEX ON version_file (sha256);

CREATE TABLE file (
    sha256          bytea PRIMARY KEY,
    size            bigint NOT NULL,
    ref_count       integer NOT NULL DEFAULT 0,
    has_brotli      boolean NOT NULL DEFAULT false,
    has_gzip        boolean NOT NULL DEFAULT false,
    created_at      timestamptz NOT NULL DEFAULT now(),
    last_ref_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON file (last_ref_at) WHERE ref_count = 0;

CREATE TABLE artifact_tag (
    artifact_id     text NOT NULL REFERENCES artifact(id) ON DELETE CASCADE,
    tag             citext NOT NULL,
    PRIMARY KEY (artifact_id, tag),
    CONSTRAINT tag_format CHECK (tag ~ '^[a-z0-9][a-z0-9 _-]{0,39}$')
);
CREATE INDEX ON artifact_tag (tag);

CREATE TYPE upload_state AS ENUM ('open', 'committing', 'committed', 'expired', 'aborted');

CREATE TABLE upload_session (
    id              text PRIMARY KEY,
    artifact_id     text NOT NULL REFERENCES artifact(id) ON DELETE CASCADE,
    version_id      text NOT NULL REFERENCES artifact_version(id) ON DELETE CASCADE,
    user_id         text NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    state           upload_state NOT NULL DEFAULT 'open',
    manifest        jsonb NOT NULL,
    pending_count   integer NOT NULL,
    created_by_token text REFERENCES api_token(id),
    created_at      timestamptz NOT NULL DEFAULT now(),
    expires_at      timestamptz NOT NULL,    -- created_at + 4h (video is in scope)
    committed_at    timestamptz
);
CREATE INDEX ON upload_session (state, expires_at) WHERE state = 'open';
```

**`kind` is derived, not inferred from content.** It is set at commit from the manifest's
shape: more than one file → `bundle`; one file whose type is HTML → `page`; PDF or office
document → `document`; image, video → those; anything else → `file`. It drives which viewer
chrome the dashboard shows (§11) and nothing else. No file is opened to determine it.

## 3.5 File storage

```
/var/lib/share/
├── files/
│   └── ab/cd/abcdef…9f          # sha256 hex, sharded 2/2
│       ├── (the bytes, 0640, share:share-read)
│       ├── abcdef…9f.br         # optional
│       └── abcdef…9f.gz         # optional
├── tmp/                         # uploads land here; same filesystem, atomic rename
├── quarantine/                  # hash mismatches, kept 24 h
└── backups/                     # nightly staging
```

Write protocol: stream to `tmp/{random}.part` hashing incrementally and enforcing
`SHARE_MAX_FILE_BYTES`; compare the digest to the one in the URL; on mismatch move to
`quarantine/` and return `400 file_hash_mismatch`; `fsync`; `rename()` into place (atomic
within a filesystem, so a reader never sees a partial file); `fsync` the directory;
`INSERT … ON CONFLICT (sha256) DO UPDATE SET last_ref_at = now()`.

**Precompression.** After a successful write, if the content type is compressible (§6.6) and
the size is 1 KB–10 MB, the worker queues brotli (q9) and gzip (l6) siblings for Caddy's
`precompressed`. Outside that window, files are served as stored; Caddy does not compress on
the fly, which would defeat `sendfile`. Video and images are never precompressed.

**Deduplication is instance-wide.** Two users posting the same file share one blob. The
`skipped` count returned by the post API is computed **only against files already referenced by
the calling user**, so it can never be used to test whether anyone else on the instance holds a
given file (§5.4.1).

**Range requests.** Caddy's `file_server` handles `Range` natively, which is what makes video
seeking work. Nothing in the API needs to participate; the authorisation call happens first and
the byte serving happens after.

## 3.6 Reference counting and collection

`file.ref_count` moves with `version_file` rows, transactionally. The sweep requires **both** a
non-positive counter and a `NOT EXISTS`, so the two failure directions have different costs and
the cheaper one was chosen deliberately: a counter that has drifted **high** on an unreferenced
file makes that file permanently uncollectable, which costs disk; a counter that has drifted
**low** on a *referenced* file is caught by the `NOT EXISTS` and cannot delete live data. Leaking
disk is recoverable, deleting a referenced file is not.

The remedy for a drifted counter is `sharectl recompute-refs`. So the leak is visible rather than
silent, the nightly pass logs a count of rows where
`ref_count > 0 AND NOT EXISTS (SELECT 1 FROM version_file vf WHERE vf.sha256 = f.sha256)`.

Nightly at 04:00:

```sql
SELECT sha256 FROM file f
WHERE f.ref_count <= 0
  AND f.last_ref_at < now() - interval '24 hours'
  AND NOT EXISTS (SELECT 1 FROM version_file vf WHERE vf.sha256 = f.sha256)
LIMIT 5000
FOR UPDATE SKIP LOCKED;
```

For each: delete the blob and its `.br`/`.gz` siblings, delete the row, prune empty shard
directories. Bounded at 5,000 per run, logged with a summary. The 24-hour grace window plus the
row lock make it impossible to collect a file an in-flight upload session is about to reference.

Hard deletion cascade: trashed artifacts are hard-deleted after `SHARE_TRASH_DAYS`, which
removes `version_file` rows, which drops ref counts, which makes files collectable on the
following run. An artifact trashed today has its unique bytes gone in 31 days. The
`DELETE /api/v1/artifacts/{name}?purge=true` path skips the trash window entirely and is
audited — that is the path P8 is tested against.

## 3.7 Sharing tables

```sql
CREATE TABLE share_link (
    id              text PRIMARY KEY,
    artifact_id     text NOT NULL REFERENCES artifact(id) ON DELETE CASCADE,
    token_hash      bytea NOT NULL UNIQUE,   -- sha256 of the 128-bit token
    display_prefix  text NOT NULL,           -- first 8 chars, so the UI can name it
    label           text,                    -- "Fairfield team", operator's note
    password_hash   text,                    -- argon2id; NULL = no password
    expires_at      timestamptz NOT NULL,    -- NEVER NULL (P4)
    max_views       integer,                 -- optional burn-after-N viewer-days
    view_count      integer NOT NULL DEFAULT 0,   -- authorised responses; display only
    viewer_days     integer NOT NULL DEFAULT 0,   -- exact count of distinct (day, viewer-hash)
                                                  -- pairs; this drives max_views, never the HLL
    last_viewed_at  timestamptz,
    created_by_user text REFERENCES app_user(id),
    created_by_token text REFERENCES api_token(id),
    created_at      timestamptz NOT NULL DEFAULT now(),
    revoked_at      timestamptz,
    CONSTRAINT expiry_required CHECK (expires_at IS NOT NULL)
);
CREATE INDEX ON share_link (artifact_id) WHERE revoked_at IS NULL;
CREATE INDEX ON share_link (expires_at) WHERE revoked_at IS NULL;

CREATE TABLE share_grant (
    id              text PRIMARY KEY,
    artifact_id     text NOT NULL REFERENCES artifact(id) ON DELETE CASCADE,
    user_id         text NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    note            text,
    created_by      text NOT NULL REFERENCES app_user(id),
    created_at      timestamptz NOT NULL DEFAULT now(),
    revoked_at      timestamptz,
    UNIQUE (artifact_id, user_id)
);
CREATE INDEX ON share_grant (user_id) WHERE revoked_at IS NULL;

CREATE TABLE recipient_session (
    id              text PRIMARY KEY,
    share_link_id   text NOT NULL REFERENCES share_link(id) ON DELETE CASCADE,
    token_hash      bytea NOT NULL UNIQUE,
    ip_hash         bytea,                   -- HMAC(view_salt‖utc_date, share_link_id‖ip) (P6)
    created_at      timestamptz NOT NULL DEFAULT now(),
    expires_at      timestamptz NOT NULL,
    revoked_at      timestamptz
);
CREATE INDEX ON recipient_session (share_link_id) WHERE revoked_at IS NULL;

-- Exact distinct-viewer accounting for max_views. Durable, because it enforces a ceiling.
CREATE TABLE link_viewer_day (
    share_link_id   text NOT NULL REFERENCES share_link(id) ON DELETE CASCADE,
    day             date NOT NULL,
    viewer_hash     bytea NOT NULL,          -- HMAC(view_salt‖utc_date, share_link_id‖ip)
    PRIMARY KEY (share_link_id, day, viewer_hash)
);
```

`share_link.viewer_days` is the count of rows here for that link, folded into the column at the
60-second flush. It lives in Postgres and not in Redis because it enforces `max_views`: a cache
flush must not reset a burn-after-N link's ceiling to zero.

Two distinct mechanisms, deliberately not merged:

- A **share link** is a bearer capability for anyone, account or not.
- A **share grant** points an artifact at another *user* of this instance, which is what puts it
  in their "shared with me". It needs no token and cannot leak by forwarding.

A recipient session never outlives its share link: revoking the link, changing its password, or
trashing the artifact deletes the sessions immediately (P9).

## 3.8 Audit and views

```sql
CREATE TABLE audit_event (
    id              text PRIMARY KEY,        -- ULID: chronological
    user_id         text REFERENCES app_user(id) ON DELETE SET NULL,
    actor_type      text NOT NULL,           -- 'user' | 'token' | 'recipient' | 'system'
    actor_token_id  text REFERENCES api_token(id),
    action          text NOT NULL,           -- §10.7
    target_type     text,
    target_id       text,
    target_label    text,                    -- denormalised; survives deletion
    ip              inet,
    user_agent      text,
    metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON audit_event (user_id, created_at DESC);
CREATE INDEX ON audit_event (action, created_at DESC);
CREATE INDEX ON audit_event (target_id);
```

The application database role holds `INSERT, SELECT` on this table and nothing else, so no code
path can rewrite history. Retention is indefinite; the table stays small.

```sql
CREATE TABLE view_daily (
    artifact_id     text NOT NULL REFERENCES artifact(id) ON DELETE CASCADE,
    day             date NOT NULL,
    source          text NOT NULL,           -- 'owner' | 'grant' | 'link'
    share_link_id   text REFERENCES share_link(id) ON DELETE SET NULL,
    views           integer NOT NULL DEFAULT 0,
    viewers         integer NOT NULL DEFAULT 0,
    bytes_served    bigint NOT NULL DEFAULT 0,
    PRIMARY KEY (artifact_id, day, source, share_link_id)
);
```

There is no raw view table. Events buffer in Redis for 60 seconds and aggregate straight into
daily rows, with a `HyperLogLog` per (artifact, day, source) for the distinct-viewer estimate.
The HLL is an **estimate and is never used for enforcement** — `share_link.viewer_days`, backed by
`link_viewer_day` (§3.7), is the exact count `max_views` burns against.

Both hashes are keyed HMACs with the target as part of the message, which is what makes them
unlinkable across targets rather than merely anonymous:

| Hash | Construction |
| --- | --- |
| View hash | `HMAC(key = view_salt ‖ utc_date, msg = artifact_id ‖ client_ip)` |
| Recipient-session hash | `HMAC(key = view_salt ‖ utc_date, msg = share_link_id ‖ client_ip)` |

The key rotates at the UTC day boundary, so yesterday's hashes cannot be recomputed once the day
rolls over.
Nothing per-request is ever written to disk, which makes P6 true by construction rather than by
a retention policy — there is no raw data to expire.

## 3.9 Denormalised counters

`app_user.storage_bytes` and `artifact_count` are maintained by trigger into a Redis dirty-set
that the worker drains every 60 seconds, not by application code that can forget. A user is
charged for every file their artifacts reference, even one another user also references; this
over-counts globally and is the intended simple behaviour. `sharectl recompute-quota` rebuilds
from scratch.

### 3.9.1 Idempotency records

```sql
CREATE TABLE idempotency_record (
    user_id         text NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    endpoint        text NOT NULL,
    key             text NOT NULL,           -- client-supplied, ≤255 chars
    request_digest  bytea NOT NULL,          -- sha256 of the canonical request body
    status_code     integer NOT NULL,
    response_body   jsonb NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, endpoint, key)
);
CREATE INDEX ON idempotency_record (created_at);
```

Rows are reaped after 24 hours by the nightly job. A replay with a matching `request_digest`
returns the stored status and body; a mismatch is `409 idempotency_key_reused` (§5.1.3).

## 3.10 Redis keyspace

Nothing durable lives here. A flush costs at most 60 seconds of view counts and resets rate
limits. That claim is load-bearing, so two things that a cache would otherwise be the obvious
home for are deliberately in Postgres instead: **idempotency records** (§3.9.1 — a flush must not
let a replayed `POST` create a second artifact) and **`link_viewer_day`** (§3.7 — a flush must not
reset a `max_views` ceiling). If it enforces something, it is not in Redis.

| Key | Type | TTL | Purpose |
| --- | --- | --- | --- |
| `sh:res:{space}:{name}` | hash | 60 s | Resolved artifact + live version |
| `sh:man:{versionId}` | hash | 600 s | path → file |
| `sh:ltok:{sha256}` | string | 300 s | Share-link validity |
| `sh:atok:{sha256}` | string | 30 s | API-token validity and scopes |
| `sh:sess:{sha256}` | string | 300 s | Dashboard session validity |
| `sh:rcp:{id}` | string | 300 s | Recipient-session validity (§4.7) |
| `sh:wa:{challengeId}` | string | 300 s | WebAuthn challenge |
| `sh:rl:{bucket}:{subject}` | string | window | Rate limit buckets |
| `sh:up:{sessionId}` | hash | 4 h | Pending file set for an upload |
| `sh:views` | stream | — | View events awaiting flush |
| `sh:hll:{artifactId}:{day}:{source}` | HLL | 40 d | Distinct viewer estimate |
| `sh:dirty:users` | set | — | Users needing a storage recompute |
| `sh:tokuse` | hash | — | API-token `last_used_at`/`ip`, flushed every 60 s (§4.6) |

## 3.11 Bootstrap

`sharectl bootstrap --email you@c52.com --handle robert` creates the root user with
`is_root = true`, prints a passkey-registration URL valid for 15 minutes, and refuses to run if
any user already exists. Registration of the first passkey completes the bootstrap and prints
one recovery code and one API token.
