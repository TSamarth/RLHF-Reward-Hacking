#!/usr/bin/env bash
# Build the sandbox image. Run from anywhere; paths are resolved relative to
# this script. Container binary comes from CONTAINER_BIN (.env / env var),
# defaulting to podman, so docker stays a drop-in replacement.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"
if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

CONTAINER_BIN="${CONTAINER_BIN:-podman}"
IMAGE_NAME="redactor-sandbox:latest"

cd "$SCRIPT_DIR"
MSYS_NO_PATHCONV=1 "$CONTAINER_BIN" build -t "$IMAGE_NAME" -f Dockerfile .
