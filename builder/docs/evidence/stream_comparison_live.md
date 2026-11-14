# Two-site live calculation from saved Horizons

2026-11-14. Local only. Horizons acquisition stays separate. Terrain remains Unknown (`terrain_not_reviewed`). `web/replay/` was not regenerated (witness revision `1f3fb06`).

## Commands

```sh
# Single-site baseline (Site04 first 6 h)
PYTHONPATH=src .venv/bin/python -m lunar_navigator.cli --revision evidence run \
  --scenario tests/fixtures/site04_p02_practice_6h_scenario.json \
  --out /tmp/site04-6h-batch.json

PYTHONPATH=src .venv/bin/python -m lunar_navigator.cli --revision evidence stream \
  --scenario tests/fixtures/site04_p02_practice_6h_scenario.json \
  --batch-size 4

# Two-site live stream (48 h practice pair, uneven batches)
PYTHONPATH=src .venv/bin/python -m lunar_navigator.cli --revision evidence stream-comparison \
  --scenario-a tests/fixtures/site04_p02_practice_scenario.json \
  --scenario-b tests/fixtures/malapert_practice_scenario.json \
  --batch-size-a 2 --batch-size-b 5

# Forced mid-run failure
PYTHONPATH=src .venv/bin/python -m lunar_navigator.cli --revision evidence stream-comparison \
  --scenario-a tests/fixtures/site04_p02_practice_scenario.json \
  --scenario-b tests/fixtures/malapert_practice_scenario.json \
  --batch-size-a 4 --batch-size-b 4 --fail-after-batches-a 1

# UI + API
PYTHONPATH=src .venv/bin/python -m lunar_navigator.cli --revision evidence serve --port 8766
# POST /api/comparisons {"pair":"practice-48h","batch_size_a":3,"batch_size_b":5}
# GET  /api/comparisons/<comparison_id>/events
```

Open `http://127.0.0.1:8766/review-candidate/` and choose **Practice pair, 48 h**.

## 1. Single-site baseline (Site04 6 h)

| Check | Value |
| --- | --- |
| Sun-centre clear | **21600 s** |
| Terminal sample duration | **0 s** |
| Batch run ID | `site04-p02-practice-6h-q4-centre-0deg-a24325ba50c4-20250101T000000Z-20250101T060000Z` |
| Stream first batch before complete | True (`samples_emitted=4` of 25) |
| Event prefix | `stage, metadata, batch, …` |
| Parity samples / intervals / elapsed / source refs | **MATCH** |

## 2. Two-site live pair (48 h)

| Field | Value |
| --- | --- |
| comparison_id | `6a70569a3fbb` |
| stream run_id_a / run_id_b | `adbee650f530` / `d897e6da4915` |
| result_run_id_a | `site04-p02-practice-q4-centre-0deg-a24325ba50c4` |
| result_run_id_b | `malapert-practice-q4-centre-0deg-88b9b3cfef57` |
| Sun-centre clear | Site A **172800 s**, Site B **0 s** |
| Both centres clear | **0 s** at either site |
| First site_batch | role=`site_a`, n=2, shared=2, `complete=false` |
| Uneven arrival | first `site_b` batch n=5 |
| Event trace | `stage, metadata, site_batch × N, complete` |

## 3. Control cases

| Case | Outcome |
| --- | --- |
| Incompatible grids (`step_seconds` 900 vs 1800) | `error` — `incompatible time grids: step_seconds 900 != 1800` |
| Forced fail after first site_a batch | `error` role=`site_a`, `partial=true`, shared=4, no complete comparison export |
| Cancel + restart | new `comparison_id`; stale events dropped by id in the UI |
| Unknown across batch boundary | Site A 00:15 `unknown` / `missing_right_endpoint` with batch_size_a=1; pending ≠ Unknown |

## 4. UI behaviour (this pass)

- Per-site sample progress in the status line and answer strip.
- Comparison totals only over the shared resolved prefix; labeled **partial** until both finish.
- Playhead clamped to shared samples.
- Complete comparison export offered only on `complete`.
- Layout unchanged; practice pair added to the scenario select.

## 5. Tests

```sh
.venv/bin/python -m pytest tests -q
# 32 passed
```

`eligible_for_submission_claim` remains false. M0.1 and M2.5 stay open.
