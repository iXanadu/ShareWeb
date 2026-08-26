#!/usr/bin/env bash
# provision-db.sh — create the PostgreSQL role + dev/prod databases for this project.
#
# MANUAL, deliberate, one-time. NOT run by /init or any Claude skill — you invoke it
# yourself, only when the project actually needs a database. It mutates the SHARED
# cluster (creates a role + two databases) using admin creds from ~/.pgpass, and
# sources the app password from ./.keys at runtime — no secret is ever hardcoded here.
#
# Usage:  DB_HOST=... DB_ADMIN_USER=... ./scripts/provision-db.sh <projectname>
set -euo pipefail

NAME="${1:?usage: ./scripts/provision-db.sh <projectname>}"
HOST="${DB_HOST:?set DB_HOST}"
ADMIN="${DB_ADMIN_USER:?set DB_ADMIN_USER}"

[ -f .keys ] || { echo "ERROR: no .keys in $(pwd) — run from the project root after env setup."; exit 1; }
DB_PASSWORD=$(grep -E '^(SHARE_)?DB_PASSWORD=' .keys | tail -1 | cut -d= -f2-)
[ -n "${DB_PASSWORD:-}" ] || { echo "ERROR: DB_PASSWORD not found in .keys"; exit 1; }

echo "Provisioning role '$NAME' + ${NAME}_dev / ${NAME}_prod on $HOST ..."
createuser -h "$HOST" -U "$ADMIN" "$NAME"
psql -h "$HOST" -U "$ADMIN" -d postgres -c "ALTER USER \"$NAME\" WITH PASSWORD '$DB_PASSWORD';"
psql -h "$HOST" -U "$ADMIN" -d postgres -c "GRANT \"$NAME\" TO \"$ADMIN\";"
createdb -h "$HOST" -U "$ADMIN" -O "$NAME" "${NAME}_dev"
createdb -h "$HOST" -U "$ADMIN" -O "$NAME" "${NAME}_prod"
echo "Done: provisioned $NAME (dev + prod) on $HOST."
