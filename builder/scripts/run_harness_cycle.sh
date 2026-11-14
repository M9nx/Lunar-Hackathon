#!/usr/bin/env bash
# Standard builder entry: full harness cycle from builder/ directory.
set -euo pipefail
BUILDER="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BUILDER"
exec python3 scripts/harness_cycle.py "$@"