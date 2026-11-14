#!/usr/bin/env bash
# M0.4: offline wheel install smoke (does not modify system Python).
set -euo pipefail
BUILDER="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$BUILDER/.." && pwd)"
WHEEL_DIR="${WHEEL_DIR:-$REPO/data/offline/wheels/cpython-314-linux-x86_64}"
REQ="$WHEEL_DIR/requirements-offline.txt"
VENV="${VENV:-$REPO/.venv}"

echo "python=$(command -v python3) $(python3 --version)"
echo "wheel_tag=cpython-314-linux-x86_64"
test -d "$WHEEL_DIR" || { echo "MISSING wheel dir: $WHEEL_DIR"; exit 1; }

python3 -m venv "$VENV"
# shellcheck disable=SC1091
. "$VENV/bin/activate"
python -m pip install --upgrade pip >/dev/null
python -m pip install --no-index --find-links "$WHEEL_DIR" -r "$REQ"
python - <<'PY'
import numpy, rasterio, pyproj, pytest
print("imports=OK", "numpy", numpy.__version__)
PY