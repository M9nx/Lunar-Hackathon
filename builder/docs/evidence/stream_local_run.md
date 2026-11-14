# Local on-demand run and streaming

2026-11-14. Calculation uses saved Horizons inputs only. Acquisition remains a separate `lunar_offline_pack.py horizons` step. The witnessed `web/replay/` package was not regenerated.

## Commands

```sh
# Batch
PYTHONPATH=src python3 -m lunar_navigator.cli --revision test run \
  --scenario tests/fixtures/site04_p02_practice_scenario.json \
  --out /tmp/site04-batch.json

PYTHONPATH=src python3 -m lunar_navigator.cli --revision test run \
  --scenario tests/fixtures/site04_p02_practice_6h_scenario.json \
  --out /tmp/site04-6h-batch.json

# Stream (NDJSON)
PYTHONPATH=src python3 -m lunar_navigator.cli --revision test stream \
  --scenario tests/fixtures/site04_p02_practice_6h_scenario.json \
  --batch-size 2

# UI + API
PYTHONPATH=src python3 -m lunar_navigator.cli --revision test serve --port 8766
```

Open `http://127.0.0.1:8766/review-candidate/`.

## Event trace (6 h Site04, batch size 2)

```text
TRACE_FIRST_BATCH 9c3a7a62bcfb index=0 samples_emitted=2 first=2025-01-01T00:00:00Z complete=False
EVENT_ORDER stage, metadata, batch ×13, complete
MATCH samples/intervals/elapsed/run_id = True against batch file
TERMINAL duration_seconds=0 at 2025-01-01T06:00:00Z
SOURCE0 horizons/site04-p02-practice/sun-8a039d445c7f/angles.csv#row=2
```

## Control checks

| Case | Run ID | Result |
| --- | --- | --- |
| Cancel after first batch | `f934bd801510` | `stage, metadata, batch, cancelled`; `complete=false`, `partial=true` |
| Fail after first batch | `d74c46005e36` | `stage, metadata, batch, error`; samples_emitted=2 |
| UI complete | `05719b812a66` | Status Complete; export link; 6 h totals Sun clear 21600 s |
| UI fail test | `24620e66d6c1` | Status Failed; banner Partial totals |

`pytest tests` → 28 passed. `web/replay/` unchanged. `code_revision` `1f3fb06`, `eligible_for_submission_claim` false.
