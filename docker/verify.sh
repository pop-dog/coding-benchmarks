#!/usr/bin/env bash
# verify.sh — runs inside benchmark-base:latest to confirm all toolchains work.
# Exits 0 if every check passes; exits 1 on the first failure.

set -euo pipefail

PASS=0
FAIL=0

check() {
    local label="$1"
    shift
    if "$@" > /dev/null 2>&1; then
        echo "[PASS] ${label}"
        PASS=$((PASS + 1))
    else
        echo "[FAIL] ${label}"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== benchmark-base toolchain verification ==="
echo ""

# python3
check "python3 available"        python3 --version

# pip / pytest importable
check "pytest available"         python3 -m pytest --version

# go
check "go available"             go version

# rustc
check "rustc available"          rustc --version

# cargo
check "cargo available"          cargo --version

# node
check "node available"           node --version

# npm
check "npm available"            npm --version

# claude (Claude Code CLI)
check "claude available"         claude --version

echo ""
echo "=== Results: ${PASS} passed, ${FAIL} failed ==="

if [ "${FAIL}" -gt 0 ]; then
    echo "VERIFICATION FAILED"
    exit 1
fi

echo "VERIFICATION PASSED"
exit 0
