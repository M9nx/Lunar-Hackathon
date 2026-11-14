---
name: lunar-result-contract
description: >-
  Owns versioned run JSON, schema fields, and engine/UI/export parity. Use at M1+
  when writing readers, exporters, or timeline UI against saved results.
disable-model-invocation: true
---

# Result contract (§5 Run result)

Time fields: see **Time and angles** in `lunar-guardrails.mdc`.

## Ownership

Single source of truth for how **engine**, **browser replay**, and **export** interpret the same artifact. Master Reference **§5** + `core_model` in `MASTER_REFERENCE.json`.

## Required agreement (before M1.4 integration)

| Topic | Rule |
|-------|------|
| Time | ISO 8601 UTC ending in `Z`; shared grid per scenario |
| Angles | Degrees; azimuth `[0, 360)` clockwise from local north |
| States | `clear`, `blocked`, `unknown` — lowercase in JSON |
| Margin | `elevation_deg - horizon_deg`; null when Unknown |
| Both lane | Priority: blocked > unknown > clear |
| Intervals | `[start, end)`; **left-sample** policy; terminal sample adds **zero** duration |
| Schema | `schema_version` on every published run; unsupported → explicit reader error |

## Fixtures

| File | Use |
|------|------|
| `tests/fixtures/run_result_geometric_0deg_minimal.json` | Contract skeleton (M1.2+) |
| `tests/fixtures/site04_p02_practice_scenario.json` | Horizons case input |
| Master `examples/synthetic_hour` | Totals + interval states for parity tests (§6 worked example) |

## Commands

```sh
python3 builder/scripts/verify_result_contract.py tests/fixtures/run_result_geometric_0deg_minimal.json
python3 builder/scripts/run_acceptance.py --gate M1
```

## Integration checks (enable when artifacts exist)

1. **Synthetic hour:** engine totals = `examples.synthetic_hour.duration_seconds`; 01:00 row adds no interval.
2. **Inspector:** playhead fields match classified sample at same UTC.
3. **Export:** byte-identical to file UI offers (M2.3 / §9 comparable A/B).
4. **Site A real:** trace one Sun + one Earth row Horizons → engine row → UI → export (M1.5).

## Unknown representation

`horizon_deg`, `margin_deg`, or ephemeris null → `state: unknown` + `reason` (never coerce to 0°).

## Lane

Pair with `lunar-comparison-ux` (UI) and `lunar-engine-impl` (writer). Math lane signs off totals before merge.