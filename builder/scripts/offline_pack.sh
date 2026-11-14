#!/usr/bin/env bash
# Wrapper for lunar_offline_pack.py — agents must use this instead of improvising paths.
set -euo pipefail
BUILDER="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$BUILDER/.." && pwd)"
DATA_ROOT="${DATA_ROOT:-$REPO/data}"
export DATA_ROOT
exec python3 "$REPO/lunar_offline_pack.py" --root "$DATA_ROOT" "$@"