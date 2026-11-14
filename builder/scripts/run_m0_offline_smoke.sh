#!/usr/bin/env bash
# M0.5-oriented offline smoke: static pack checks (run with Wi-Fi off on demo laptop).
set -euo pipefail
BUILDER="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$BUILDER/.." && pwd)"
DATA_ROOT="${DATA_ROOT:-$REPO/data}"
export DATA_ROOT
python3 "$REPO/lunar_offline_pack.py" --root "$DATA_ROOT" check core
python3 "$ROOT/lunar_offline_pack.py" --root "$DATA_ROOT" check-horizons
echo "Note: run 'check core terrain --open-dem' after rasterio install (M0.4)."