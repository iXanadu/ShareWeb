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
| Bytes posted in an hour by one token | > 25 GB | Bulk shape. Above the 10 GB artifact ceiling by enough that one legitimate maximum-size post does not trip it |
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
retention policy — there is no raw data whose expiry could be misconfigured.

The hash is `HMAC(key = view_salt ‖ utc_date, msg = artifact_id ‖ client_ip)`, and the
recipient-session equivalent substitutes `share_link_id` for the artifact (§3.8). The target being
part of the message is what makes the same visitor unlinkable across two artifacts; the key
rotating at the UTC day boundary is what makes yesterday's hashes unrecomputable.

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
