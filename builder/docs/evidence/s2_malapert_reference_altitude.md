# Malapert practice reference altitude

The practice request for Malapert uses **altitude 0.0 km** with `COORD_TYPE=GEODETIC`, `SITE_COORD='-2.93,-85.99,0.0'`, centre body `301`. This page says what that number is, what it is not, and what it does and does not change. It is a documentation record for Science. It is not a height-reference decision.

## Facts from the saved files

| Item | Value | Where |
| --- | --- | --- |
| Practice Horizons altitude, Malapert | 0.0 km | `data/horizons/malapert-practice*/…/provenance.json`, `request_url` |
| Practice Horizons altitude, Site04 | 1.738902 km | `data/horizons/site04-p02-practice*/…/provenance.json` |
| Horizons lunar radii (sphere) | 1737.4 km | response header, `Center radii` |
| DEM240 pixel at Malapert | 4,864.25 m (3×3 range 4,793.33–4,911.73 m) | `LDEM_60S_240MPP_ADJ.TIF`, row 3373, col 3854 |
| DEM20 pixel at Malapert | 4,846.38 m (3×3 range 4,839.55–4,852.92 m) | `LDEM_80S_20MPP_ADJ.TIF`, row 9125, col 14889 |
| DEM240 pixel at Site04 | 1,734.31 m | row 3905, col 3868 |
| DEM20 pixel at Site04 | 1,736.68 m (3×3 range 1,733.20–1,737.41 m) | row 15504, col 15067 |

Site04's practice altitude (1,738.902 m) is within about 2 to 5 m of the DEM at the site. Malapert's is about **4.85 km below** the DEM surface at the same longitude and latitude.

## What 0.0 km means

In Horizons, `0.0` is the height above the 1737.4 km reference sphere. The Moon is not a sphere at that level. At Malapert the DEM surface is more than 4.8 km above that sphere. So the practice observer is a point on the reference sphere below the terrain, not a point on the surface. Nobody stands there.

## Why it was left at 0.0

It is the value in the practice request that the team staged and the witnessed `1f3fb06` replay uses. Changing it would change the saved inputs and the witnessed package. It was not changed.

## What it changes

* **Geometric 0° result: reported not to change.** The preflight reports a capture at 4.86425 km (same 48 h grid, quantity 4, Sun 10, Earth 399) in which both bodies stayed Blocked, with 0 of 193 samples changing state at 0°. That capture is not under this laptop's `data/horizons/` and was **not re-queried here**. Treat it as reported.
* **Terrain result: would change.** A skyline traced from a 0 m observer sits inside the terrain. At 100 m along an azimuth the nearest DEM cell is 4.8 km above the observer, giving an elevation near +88.8°. `s2/terrain_independent_skyline.json` → `malapert_practice_altitude_probe` records that case: a 0 m observer, azimuth 0°, within 2 km, with the maximum elevation and the terrain height there. The DEM240 diagnostic profile therefore uses the DEM surface height (4,864.25 m) for Malapert. That is a different height from the practice request. The profile and the 0° run do not share an observer.
* **30-day case:** it reuses the same 0.0 km, so Malapert's 436 h Sun-centre figure is for that observer. It carries the same caveat.

## What stays open

* Which height reference is correct for a Malapert surface observer (DEM surface, a stated mast height above it, or the sphere). Science decides (S3 in `s2_scope_decision.md`).
* A new Horizons capture at the chosen altitude, with its own receipt, if the 0° result should be shown for a surface observer. That needs the team's contact value for the JPL User-Agent and a deliberate request. It is not part of this local build.
* Whether the 4.86425 km sensitivity should be shown on screen. It is not shown now.

The result screen says: "Observer reference altitude in the saved inputs … practice request values and not a reviewed surface height" under *Why terrain Unknown?*.
