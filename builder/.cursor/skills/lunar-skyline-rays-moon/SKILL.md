---
name: lunar-skyline-rays-moon
description: >-
  Lunar terrain skyline geometry: radial rays, max elevation angle, NoData gaps,
  near-field DEM limits. Use for M4 terrain and skyline_check validation.
disable-model-invocation: true
---

# Skyline rays (Moon)

## Method (Master Reference §6.2 + literature)

1. Observer in Moon-fixed 3D frame with reviewed height convention.
2. Local basis: **up** (surface normal or ellipsoid radial at observer), **north**, **east**.
3. For azimuth `A`, sample terrain along reviewed range; sight angle `α = atan2(U, hypot(E,N))`.
4. Skyline `H(A) = max(α)` along supported ray; **ridge** sets max even if farther point is higher in absolute elevation.
5. **Curvature** included in 3D chord geometry — no second correction (§6).

Polar planning literature ([DLR EPSC horizon method](https://elib.dlr.de/94242/1/EPSC2014-136-1.pdf)): step azimuth ~ solar disk scale (~0.5°) when validating disk illumination; this project’s **v1 demo** stays **centre-ray** unless finite-disc upgrade (§10).

## Coverage honesty

- Populated azimuth bin ≠ continuous support along ray → `terrain_gap` / Unknown.
- Site04 5 m tile ≈ **near-field** only; far-field needs regional DEM (Product 90) with frame review.
- NoData / LDEC masks: skip or Unknown per policy — never interpolate across gaps without declared policy.

## Teaching CLI

```sh
python3 builder/scripts/skyline_check.py
```

Ridge worked example: +0.8° centre vs +1.2° skyline → −0.4° margin, **blocked**.

## Related

`lunar-frames-terrain-science` · NASA polar illumination context ([JPL 42-176](https://ipnpr.jpl.nasa.gov/progress_report/42-176/176C.pdf)) — aggregate maps, not selected-date centre-ray truth.