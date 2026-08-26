#!/bin/bash
# Stop the Share service.  Usage: ./scripts/stop.sh
set -e
source "$(cd "$(dirname "$0")" && pwd)/_env.sh"
require_linux
echo "Stopping ${SERVICE_NAME}..."
sudo systemctl stop "$SERVICE_NAME"
echo "Stopped."
