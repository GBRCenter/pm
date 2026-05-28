#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="pm-mvp"

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
echo "Container stopped/removed: $CONTAINER_NAME"
