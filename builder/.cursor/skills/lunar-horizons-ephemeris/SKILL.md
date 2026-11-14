---
name: lunar-horizons-ephemeris
description: >-
  JPL Horizons saved-table intake for lunar surface observers: Q4, body IDs,
  SITE_COORD, UTC grid. Use for M1.1 data lane and case-fit checks.
---

# Horizons ephemeris (saved tables)

## Request shape (Master Reference §6.1)

| Parameter | Value |
|-----------|--------|
| `CENTER` | `coord@301` (Moon) |
| `COORD_TYPE` | `GEODETIC` |
| `COMMAND` | `10` Sun, `399` Earth (not barycentre `3`) |
| `QUANTITIES` | `4` (apparent airless az/el) |
| `TIME` | UT; serialize ISO 8601 `Z` in engine |
| Observer | east lon°, lat°, ref altitude **km** in `SITE_COORD` |

API reference: [Horizons API](https://ssd-api.jpl.nasa.gov/doc/horizons.html), [quantity 4](https://ssd.jpl.nasa.gov/horizons/manual.html#apparent-azimuth--elevation-az-el-).

## Practice vs submission

- `data/horizons/*-practice/` — smoke/fixtures only until case-fit + eligibility pass.
- Verify: `python3 builder/scripts/case_fit_horizons.py --scenario tests/fixtures/site04_p02_practice_scenario.json`

## Headers to read

Target body name, center body Moon (301), center geodetic, observer frame (e.g. MEAN_ME), ephemeris version — record in manifest; mismatches → **Unknown**, not silent fixes.

## Fair use

Respect JPL identification, serial requests, caching, backoff when fetching online; demo path uses **saved** exports only.