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
