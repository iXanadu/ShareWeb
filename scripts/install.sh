#!/bin/bash
# Install (or refresh) the Share systemd service — Linux/systemd prod path.
#
# Prereqs (clone time, usually the human): pyenv venv share-3.13, pip install -e .
# .env + .keys written (chmod 600 .keys). nginx + TLS by WebOne website-setup.
#
# Usage:  ./scripts/install.sh
#
set -e
source "$(cd "$(dirname "$0")" && pwd)/_env.sh"
require_linux

echo "=== Share service install ==="
echo "  service:  $SERVICE_NAME"
echo "  app dir:  $APP_DIR"
echo "  uvicorn:  $UVICORN"
echo "  port:     $APP_PORT (loopback; nginx is the public edge)"
echo ""

[[ -x "$UVICORN" ]] || { echo "ERROR: uvicorn not found at $UVICORN — create the venv + pip install first"; exit 1; }
[[ -f "$APP_DIR/.env"  ]] || echo "WARNING: $APP_DIR/.env missing"
[[ -f "$APP_DIR/.keys" ]] || echo "WARNING: $APP_DIR/.keys missing"
mkdir -p "$APP_DIR/logs" /var/lib/share/files /var/lib/share/tmp

UNIT_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
echo "Writing unit → $UNIT_PATH"
sudo tee "$UNIT_PATH" >/dev/null <<UNIT
[Unit]
Description=Share FastAPI service (share.c52.com)
After=network-online.target postgresql.service
Wants=network-online.target

[Service]
Type=simple
User=${RUN_USER}
Group=${RUN_GROUP}
WorkingDirectory=${APP_DIR}
Environment=PATH=${VENV}/bin:/usr/local/bin:/usr/bin:/bin
# nginx is the only public edge -> bind loopback.
ExecStart=${UVICORN} server.main:app --host 127.0.0.1 --port ${APP_PORT} --workers 1
Restart=always
RestartSec=5
TimeoutStopSec=20
KillSignal=SIGTERM
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${SERVICE_NAME}

[Install]
WantedBy=multi-user.target
UNIT

echo "Reloading systemd, enabling on boot, (re)starting..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"
health_check
echo ""
echo "Done. Control with ./scripts/{start,stop,restart}.sh  ·  logs: sudo journalctl -u ${SERVICE_NAME} -f"
