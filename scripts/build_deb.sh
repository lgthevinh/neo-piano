#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="debian:bookworm"

CONTAINER_ENGINE="docker"
if ! command -v docker >/dev/null 2>&1; then
    if command -v podman >/dev/null 2>&1; then
        CONTAINER_ENGINE="podman"
    else
        echo "ERROR: docker or podman is required." >&2
        exit 1
    fi
fi

mkdir -p "$REPO_ROOT/dist"

"$CONTAINER_ENGINE" run --rm \
    -v "$REPO_ROOT:/src:ro" \
    -v "$REPO_ROOT/dist:/out" \
    "$IMAGE" bash -euo pipefail -c '
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq
        apt-get install -y -qq --no-install-recommends \
            build-essential debhelper dh-python devscripts \
            python3-all python3-setuptools pybuild-plugin-pyproject \
            >/dev/null

        cp -a /src /build
        cd /build
        rm -rf dist .git
        dpkg-buildpackage -us -uc -b
        cp /neo-piano_*_all.deb /out/
        chown "$(stat -c "%u:%g" /out)" /out/neo-piano_*_all.deb || true
        ls -lh /out/neo-piano_*_all.deb
    '

