#!/usr/bin/env bash
# build.sh — builds benchmark-base:latest and verifies all toolchains.
# Run from anywhere; the Dockerfile is resolved relative to this script.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="benchmark-base:latest"

echo "=== Building ${IMAGE} ==="
docker build --tag "${IMAGE}" "${SCRIPT_DIR}"

echo ""
echo "=== Running verify.sh inside ${IMAGE} ==="
docker run --rm \
    --entrypoint /bin/bash \
    --volume "${SCRIPT_DIR}/verify.sh:/verify.sh:ro" \
    "${IMAGE}" \
    /verify.sh

echo ""
echo "=== Done. ${IMAGE} is ready. ==="
