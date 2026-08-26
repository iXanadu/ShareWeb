#!/bin/bash
# Start the Share service.  Usage: ./scripts/start.sh
set -e
source "$(cd "$(dirname "$0")" && pwd)/_env.sh"
require_linux
echo "Starting ${SERVICE_NAME}..."
sudo systemctl start "$SERVICE_NAME"
health_check
