#!/usr/bin/env bash
# M0.5: offline smoke plus Wi-Fi-off attestation file (QA on demo laptop).
set -euo pipefail
BUILDER="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$BUILDER/.." && pwd)"
EVIDENCE="${WIFI_OFF_EVIDENCE:-$BUILDER/docs/evidence/wifi_off_attestation.txt}"

if [[ -f "$EVIDENCE" ]]; then
  echo "wifi_off_attestation=OK path=$EVIDENCE"
elif [[ "${WIFI_OFF_CONFIRMED:-}" == "1" ]]; then
  echo "wifi_off_attestation=ENV_CONFIRMED (record $EVIDENCE on demo laptop)"
else
  echo "wifi_off_attestation=MISSING"
  echo "Create $EVIDENCE with one line: witness, UTC, laptop id — or set WIFI_OFF_CONFIRMED=1 for dev-only."
  exit 2
fi

export DATA_ROOT="${DATA_ROOT:-$REPO/data}"
"$BUILDER/scripts/offline_pack.sh" check core
"$BUILDER/scripts/offline_pack.sh" check-horizons
if [[ -x "$REPO/.venv/bin/python" ]]; then
  "$REPO/.venv/bin/python" "$REPO/lunar_offline_pack.py" --root "$DATA_ROOT" check core terrain --open-dem
fi
echo "wifi_off_smoke=OK"