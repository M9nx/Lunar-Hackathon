---
name: lunar-qa-evidence
description: >-
  Validates handoff checks, offline smoke, Wi-Fi-off attestation, and task-gate
  evidence. Use for M0.5, M1.5, M3.2, M6.
disable-model-invocation: true
---

# QA lane

## Commands (run in order)

```sh
cd builder && python3 scripts/validate_handoff.py
builder/scripts/offline_pack.sh check core
builder/scripts/wifi_off_smoke.sh   # builder/docs/evidence/wifi_off_attestation.txt
python3 builder/scripts/run_acceptance.py --offline --gate M0
```

## Wi-Fi-off attestation

Create `docs/evidence/wifi_off_attestation.txt` (witness, UTC, laptop id) on the **demo laptop** with Wi-Fi disabled. Dev-only: `WIFI_OFF_CONFIRMED=1`.

## Pass criteria

- `validate_handoff.py` → `HANDOFF OK`
- No `fail` in `handoff.checks`; document `pending` with owner
- Distinguish **missing core** (blocks) vs **optional pack** (note only)