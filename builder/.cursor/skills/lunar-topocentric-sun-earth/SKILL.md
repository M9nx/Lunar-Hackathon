---
name: lunar-topocentric-sun-earth
description: >-
  JPL Horizons apparent azimuth/elevation for a lunar surface observer: local
  horizontal, quantity 4, centre-ray targets. Use when parsing Horizons or
  disputing angle conventions.
disable-model-invocation: true
---

# Topocentric Sun / Earth (lunar observer)

## Horizons definitions ([manual](https://ssd.jpl.nasa.gov/horizons/manual.html))

| Quantity | Meaning |
|----------|---------|
| **Azimuth** | Clockwise from **north** along the horizon plane (0°=N, 90°=E) |
| **Elevation** | Angle above/below plane ⊥ to **local zenith** — not necessarily the visible terrain horizon |

**Implication:** Q4 az/el is against the **mathematical local horizontal** (0° baseline in `geometric_0deg` mode). Terrain skyline is a separate layer (see `lunar-skyline-rays-moon`).

## Request (saved tables for this project)

- `CENTER=coord@301`, geodetic `SITE_COORD` (east lon°, lat°, alt **km**)
- `COMMAND=10` (Sun centre), `399` (Earth centre)
- `QUANTITIES=4`, apparent **airless** columns in CSV

## Pitfalls

- Do not use Earth–Moon barycentre `3` for centre-ray demo.
- Header `Center geodetic` vs requested coords — case-fit before claim.
- Elevation below 0° is valid; do not clip for storage.
- Confusing **zenith plane** with **terrain horizon** causes false “clear” labels in terrain mode.

## Cross-check (optional)

NAIF local topocentric: surface normal as zenith, north from pole projection ([SPICE discussion](https://naif.jpl.nasa.gov/pipermail/spice_discussion/2010-June/000306.html)); `azlcpo_c` on ellipsoid — independent of DEM, not terrain clearance.

## Harness

`builder/scripts/case_fit_horizons.py` · skill `lunar-horizons-ephemeris`