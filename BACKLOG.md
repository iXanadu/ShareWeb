# BACKLOG

Single source of truth for deferred work. If it is not here, it is not tracked.

**Baseline (2026-08-27):** 35 tests pass locally (`pytest tests/ -q`). Huddle ShareWEb closed —
idle unless owner speaks.

Triage: BLOCKING (breaks the build / wrong-or-harmful output / destroys data → fix now) vs
DEGRADING (still runs → pin and keep moving).

Status: OPEN / IN-PROGRESS / FIXED / WONTFIX. Root = where born. Found = where surfaced.

## BLOCKING

_(none)_

## NEEDS-DECISION

_(none)_

## DEGRADING

- **SW-1** Headed passkey register+sign-in passed (scripts/headed_passkey_check.py). Bootstrap
  session cookie still exists as a local back door (D-22). Root: Phase 1 §4. Found: 2026-08-26.
- **SW-2** Mini has no Caddy; FastAPI serves artifacts locally (D-21). Prod is nginx on WebOne,
  not Caddy. Root: §2.4. Found: 2026-08-26.
- **SW-3** Phase 1 dashboard screens 11.1/11.3/11.5–8/11.15/11.18/11.19/11.26/11.27 are built
  (shareweb-cursor-2). Nav also links `/~/shared` and audit log but those routes are stubs
  ("not built yet"). Still missing sharing tabs (create-link in the web UI), recovery, audit.
  Share links work via API/MCP today — not in the dashboard UI. Root: Part 11. Found: 2026-08-26.
- **SW-4** MCP is JSON-RPC POST `/mcp` plus a one-shot GET SSE ping, not full streamable-HTTP.
  CLI has post/ls/get/rm/restore/whoami/login/logout/doctor; missing `open/cat/pull/link`.
  `share_create_link` exists on MCP. Root: Part 9. Found: 2026-08-26.
- **SW-5** Alembic not used; SQL files instead (D-23). Root: §3.1. Found: 2026-08-26.
- **SW-6** Dashboard API `05a-dashboard-api.md` not written. Root: PLUMBING-AUDIT §2. Found: spec.
- **SW-8** Mail/SMTP is empty. Notices (new share link, expiry, new token) are specified, not
  wired. Root: §15. Found: huddle 2026-08-26.
- **SW-9** `share_user` GitHub deploy key on WebOne cannot `git fetch` (`Permission denied
  (publickey)`). Pulls work as `ixanadu` (in `share_user` group). Root: prod ops. Found: 2026-08-28.

## BLOCKED-EXTERNAL

_(none)_

## STRATEGIC

- Spec Phase 2+ : grants / second user, richer sharing UI, hardening.
  (Expiring share links, passwords, and recipient View/Download already shipped.)

## FIXED

- **SW-11** Bearer tokens could access owner-only token administration and passkey enrollment.
  Fixed with browser-session dependencies and purpose-limited, one-time recovery grants; deployed
  to WebOne at `75a2a8e`. Root: Phase 1 auth plumbing. Found/fixed: 2026-09-04.
- **SW-7** WebOne `share.c52.com` live: nginx TLS → `127.0.0.1:8021`, unit
  `uvicorn_share_c52_prod`, 50MiB/file 64MiB/artifact. Found: huddle 2026-08-26.
