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
    handle /install.sh { reverse_proxy unix//run/share/api.sock }   # CLI installer (§9.8)
    handle /.well-known/* { reverse_proxy unix//run/share/api.sock } # descriptors (§9.8)

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
| `sh:ltok:{sha256}` | Share-link validity and its artifact | 300 s, deleted on revoke |
| `sh:atok:{sha256}` | API-token validity, scopes, and owner | 30 s, deleted on revoke |
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
