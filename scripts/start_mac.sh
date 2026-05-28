#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="pm-mvp:dev"
CONTAINER_NAME="pm-mvp"
PORT="8000"
ENV_FILE="$ROOT_DIR/.env"

echo "Building Docker image: $IMAGE_NAME"
docker build -t "$IMAGE_NAME" "$ROOT_DIR"

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

if [[ -f "$ENV_FILE" ]]; then
  docker run -d --name "$CONTAINER_NAME" -p "$PORT:8000" --env-file "$ENV_FILE" "$IMAGE_NAME" >/dev/null
else
  docker run -d --name "$CONTAINER_NAME" -p "$PORT:8000" "$IMAGE_NAME" >/dev/null
fi

echo "Container started: $CONTAINER_NAME"
echo "App URL: http://localhost:$PORT"
