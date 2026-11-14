---
name: lunar-frames-terrain-science
description: >-
  Lunar frames, height references, DEM NoData, radial skyline gaps, and terrain
  Unknown reasons. Use for M2.5/M4 and geometry review before terrain claims.
---

# Frames, geometry, terrain science

## Centre-ray vs terrain (Master Reference §6)

- Horizons gives **apparent centre** az/el above local horizontal.
- Terrain adds **H(A)** from reviewed DEM; margin `e - H(A)`.
- Populated azimuth bin ≠ supported ray along range (**radial gap** → Unknown).

## Coordinate / height (Product 78 / edu *historical* checklist)

- PGDA Site04/Site23 5 m grids: south-polar stereographic metres, **MOON_ME / DE421** in product description.
- Separate **observer height reference** from DEM vertical datum; unresolved tie → `unreviewed_height_reference` / Unknown.
- **NoData**, LDEC masks, interpolated cells — document before M4 promotion.

## Horizons vs smooth horizon

- `geometric_0deg`: `H = 0°` is local horizontal, not physical limb.
- 3D skyline along reviewed range; **no second curvature correction** after vector subtraction (§6).

## Long-term products (Product 69)

- 18.6-year **aggregate** disc visibility ≠ selected-date centre-ray. Use only as context check, not demo truth.

## Evidence before terrain UI labels

Science review record: registration, one independent skyline direction, supported range (§9 terrain evidence). Defer **Product 90 vs 78** choice to **M4.1**.

## Edu archive (read-only)

`~/Documents/Learning/lunar-landing-site-navigator/docs/FRAME_GEOMETRY_VALIDATION.md` — historical gates B1–B7; fresh evidence only in this repo.