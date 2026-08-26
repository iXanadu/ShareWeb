#!/bin/bash
# Shared config for Share prod scripts. SOURCED, not executed.
# Prod scripts: uvicorn_<subdomain>_<env>, loopback, nginx at the edge.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$SCRIPT_DIR")"          # /var/www/share.c52.com/prod

SERVICE_NAME="uvicorn_share_c52_prod"
APP_PORT=8021
HEALTH_URL="http://127.0.0.1:${APP_PORT}/health"

VENV="/usr/local/pyenv/versions/share-3.13"
UVICORN="${VENV}/bin/uvicorn"
RUN_USER="share_user"
RUN_GROUP="www-data"

require_linux() {
    if [[ "$(uname)" != "Linux" ]]; then
        echo "This is the systemd (prod) path. For local dev run uvicorn on the LAN port in .env." >&2
        exit 1
    fi
}

health_check() {
    local i
    for i in $(seq 1 20); do
        if curl -sf "$HEALTH_URL" >/dev/null 2>&1; then
            echo "Health check: OK ($HEALTH_URL)"
            return 0
        fi
        sleep 1
    done
    echo "WARNING: health check failed after ~20s — inspect: sudo journalctl -u ${SERVICE_NAME} -n 50 --no-pager"
    return 1
}
