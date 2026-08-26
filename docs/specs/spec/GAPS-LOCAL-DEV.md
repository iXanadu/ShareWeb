# Share — local dev gap fills (spec ambiguities resolved during bootstrap)

## G-01 — Local file store paths on macmini

**Context:** Spec §3.5 assumes `/var/lib/share/files`. On macmini dev we use `~/var/share/files` and `~/var/share/tmp` (same filesystem).

**Resolution:** local `.env` points `SHARE_FILE_ROOT` / `SHARE_TMP_ROOT` at a directory under the operator home. Production playbook (Part 15) unchanged.

## G-02 — Database host for local dev

**Context:** spec assumes a network Postgres role `share`. Local Homebrew Postgres on this box uses peer auth as the OS user.

**Resolution:** empty `SHARE_DB_HOST` (unix socket), `SHARE_DB_USER` = the OS user. Production uses role `share`.

## G-03 — Migration runner

**Context:** Spec mentions Alembic; template used inline SQL.

**Resolution:** SQL files in `server/migrations/` with `schema_migration` revision tracking. Sufficient for Phase 1; can migrate to Alembic later if needed.

## G-04 — Dashboard API (05a)

**Status:** Still unwritten per spec. Will be authored alongside dashboard implementation.
