#!/bin/bash
# Restart the Share service (use after a git pull).  Usage: ./scripts/restart.sh
set -e
source "$(cd "$(dirname "$0")" && pwd)/_env.sh"
require_linux
echo "Restarting ${SERVICE_NAME}..."
sudo systemctl restart "$SERVICE_NAME"
health_check
