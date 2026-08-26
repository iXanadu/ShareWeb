# BACKLOG

Single source of truth for deferred work. If it is not here, it is not tracked.

Triage: BLOCKING (breaks the build / wrong-or-harmful output / destroys data → fix now) vs
DEGRADING (still runs → pin and keep moving).

Status: OPEN / IN-PROGRESS / FIXED / WONTFIX. Root = where born. Found = where surfaced.

## BLOCKING

_(none)_

## NEEDS-DECISION

_(none)_

## DEGRADING

- **SW-1** Headed passkey register+sign-in passed (scripts/headed_passkey_check.py, virtual authenticator). Bootstrap session cookie still exists as a local back door (D-22). Root: Phase 1 §4. Found: 2026-08-26.
- **SW-2** Caddy not installed on macmini; API serves artifacts (D-21). Root: §2.4. Found: 2026-08-26.
- **SW-3** Dashboard screens 11.x not built. Assigned to shareweb-cursor-2. Root: Part 11. Found: 2026-08-26.
- **SW-4** MCP is JSON-RPC POST /mcp (initialize, tools/list, tools/call) not full streamable-HTTP/SSE. CLI missing `open/cat/pull/link`. Root: Part 9. Found: 2026-08-26.
- **SW-5** Alembic not used; SQL files instead (D-23). Root: §3.1. Found: 2026-08-26.
- **SW-6** Dashboard API `05a-dashboard-api.md` not written. Root: PLUMBING-AUDIT §2. Found: spec.

## BLOCKED-EXTERNAL

- **SW-7** WebOne deploy / HTTPS / folder layout. Owner. Do not deploy. Found: huddle 2026-08-26.

## STRATEGIC

- Phase 2 sharing, Phase 3 users, Phase 4 hardening.

## FIXED

_(cleared)_
