---
name: lunar-data-intake
description: >-
  Stages and verifies offline lunar data packs, Horizons practice exports, and
  case-fit checks. Use for M0.3, M0.5, M1.1, and Horizons provenance work.
---

# Lunar data intake

## Commands

```sh
export DATA_ROOT="$(pwd)/data"
scripts/offline_pack.sh check core
scripts/offline_pack.sh check-horizons
# After M0.4 rasterio install:
.venv/bin/python lunar_offline_pack.py --root "$DATA_ROOT" check core terrain --open-dem
python3 builder/scripts/case_fit_horizons.py --scenario tests/fixtures/site04_p02_practice_scenario.json
```

Or: `scripts/run_m0_offline_smoke.sh` / `scripts/wifi_off_smoke.sh` (M0.5)

## Practice exports (fixture / smoke only)

| Site ID | Path under `data/horizons/` |
|---------|----------------------------|
| site04-p02-practice | `site04-p02-practice/{sun,earth}-*/` |
| malapert-practice | `malapert-practice/{sun,earth}-*/` |

Each folder: `provenance.json`, `angles.csv`, `response.json` — hashes in `provenance.json`.

## Case-fit (before demo claim)

Verify against scenario §5: observer lon/lat/alt km, `CENTER=coord@301`, bodies 10/399, UTC grid, Q4 apparent airless, terminal sample policy.

## Distinguish

- **Core** pack failure → blocks geometric path.
- **Optional** packs (visuals, upgrade, spice) missing → note in handoff; geometric path may still proceed.