# Data & Research — Lunar Landing Site Navigator

What data the local release uses, where it comes from, and what is still open for the terrain review. Companion documents: [Science and Data Reference](science-and-data-reference.md), [Engine Reference](engine-reference.md), [Project Progress](project-progress.md).

## Datasets and assets used by the release

### JPL Horizons Quantity 4 exports

| Filename / query | Target | Observer | UTC window | Step | Use in release | Evidence |
|------------------|--------|----------|------------|------|----------------|----------|
| `data/horizons/site04-p02-practice/sun-8a039d445c7f/response.json` | Sun `10` | Site04 (−156.4386° E, −89.7812°, 1.738902 km) | 2025-01-01 → 2025-01-03 | 15 min | Witnessed replay Sun lane | `provenance.json`, `angles.csv` |
| `data/horizons/site04-p02-practice/earth-167962cea6a2/response.json` | Earth `399` | Site04 (same) | 2025-01-01 → 2025-01-03 | 15 min | Witnessed replay Earth lane | `provenance.json`, `angles.csv` |
| `data/horizons/malapert-practice/sun-d10bfb555ec3/response.json` | Sun `10` | Malapert (−2.93° E, −85.99°, 0.0 km) | 2025-01-01 → 2025-01-03 | 15 min | Witnessed replay Sun lane | `provenance.json`, `angles.csv` |
| `data/horizons/malapert-practice/earth-062e67d0fdf0/response.json` | Earth `399` | Malapert (same) | 2025-01-01 → 2025-01-03 | 15 min | Witnessed replay Earth lane | `provenance.json`, `angles.csv` |
| `data/horizons/site04-p02-practice-30d/sun-80eafb942730/response.json` | Sun `10` | Site04 (same) | 2025-01-01 → 2025-01-31 | 60 min | Practice 30-day comparison | `provenance.json`, `angles.csv` |
| `data/horizons/site04-p02-practice-30d/earth-67a08fde71c1/response.json` | Earth `399` | Site04 (same) | 2025-01-01 → 2025-01-31 | 60 min | Practice 30-day comparison | `provenance.json`, `angles.csv` |
| `data/horizons/malapert-practice-30d/sun-0ebf1cb6ff30/response.json` | Sun `10` | Malapert (same) | 2025-01-01 → 2025-01-31 | 60 min | Practice 30-day comparison | `provenance.json`, `angles.csv` |
| `data/horizons/malapert-practice-30d/earth-64da8e67c3e9/response.json` | Earth `399` | Malapert (same) | 2025-01-01 → 2025-01-31 | 60 min | Practice 30-day comparison | `provenance.json`, `angles.csv` |

All requests use `EPHEM_TYPE='OBSERVER'`, `QUANTITIES='4'`, `ANG_FORMAT='DEG'`, `CSV_FORMAT='YES'`, `Atmos refraction: NO (AIRLESS)`, `Center pole/equ : MEAN_ME (high precision)`, ephemeris DE441, lunar radius 1737.4 km. The on-disk raw-response SHA-256 values match the PR run-input digests on this laptop; the match against Master Reference Appendix B is still open. See `builder/docs/evidence/s2/horizons_digest_provenance.md`.

### LOLA Product 90 (large-area DEMs)

| Local file | Source | Published scale | Coverage | Frame / units | Use in release | Evidence |
|------------|--------|-----------------|----------|---------------|----------------|----------|
| `data/LOLA_20mpp/LDEM_60S_240MPP_ADJ.TIF` | [PGDA Product 90](https://pgda.gsfc.nasa.gov/products/90) | 240 m/pixel | 60°S–90°S, stereographic range ±931.2 km | South-polar stereographic, sphere radius 1,737,400 m; `AREA_OR_POINT=Area`; NoData NaN | Diagnostic 240 m skyline profiles for both sites; background coverage check | `builder/docs/evidence/m2_5_preflight.md` |
| `data/LOLA_20mpp/LDEM_80S_80MPP_ADJ.TIF` | [PGDA Product 90](https://pgda.gsfc.nasa.gov/products/90) | 80 m/pixel | 80°S–90°S, stereographic range ±304 km | Same stereographic sphere | Candidate intermediate-range terrain; coverage diagnostics | `builder/docs/evidence/m2_5_preflight.md` |

### LOLA Product 78 (5 m local terrain)

| Local file | Source | Published scale | Coverage | Frame / units | Use in release | Evidence |
|------------|--------|-----------------|----------|---------------|----------------|----------|
| `data/LOLA_5mpp/Site04/Site04_final_adj_5mpp_surf.tif` | [PGDA Product 78](https://pgda.gsfc.nasa.gov/products/78) | 5 m/pixel | 16 × 16 km around Site04 S04-P02 | South-polar stereographic, MOON_ME/DE421 | Near-field diagnostic skyline for Site04; independent 20 m cross-check | `builder/docs/evidence/s2/terrain_independent_skyline.json` |
| `data/LOLA_5mpp/Site23/Site23_final_adj_5mpp_surf.tif` | Product 78 | 5 m/pixel | 16 × 16 km around Site23 | Same | Not used for the practice cases; available for future site review | — |

### LOLA Product 69 (long-term illumination/visibility context)

| Local file | Source | What it measures | Time span | Use in release | Evidence |
|------------|--------|------------------|-----------|----------------|----------|
| `data/LOLA_product69/AVGVISIB_65S_240M_201608.TIF` | [PGDA Product 69](https://pgda.gsfc.nasa.gov/products/69) | Fraction of modelled timesteps when any part of the Sun’s disc was visible | Hourly averages over ~18.6 years (product description); PDS labels carry 2009–2013 | Context only. Not a timestamped or like-for-like benchmark for the centre-ray windows. | `docs/science-and-data-reference.md` §8 |
| `data/LOLA_product69/AVGVISIB_65S_240M_201608_EARTH.TIF` | Product 69 | Fraction of modelled timesteps when any part of Earth’s disc was unobscured | Same | Context only. Not ground-station contact. | `docs/science-and-data-reference.md` §8 |

### SPICE kernels

| Local file | Source | Use in release | Evidence |
|------------|--------|----------------|----------|
| `data/spice/de421/de421.bsp` | [NAIF DE421](https://naif.jpl.nasa.gov/naif/data_generic.html) | Not used by the centre-ray engine (Horizons already supplies apparent angles); retained for historical frame checks | `builder/docs/evidence/s2_science_review.md` |
| `data/spice/de421/moon_080317.tf`, `moon_pa_de421_1900-2050.bpc`, `naif0012.tls`, `pck00010.tpc` | NAIF | Historical frame/angle conversion checks in the edu archive | `research/B5_OWNER_REVIEW_CHECKLIST.md` (read-only historical) |

### Imagery and 3-D assets

| File | Source / credit | Use in release |
|------|-----------------|----------------|
| `web/review-candidate/media/pia13523_clear.jpg` | NASA / JPL / GSFC / ASU, PIA13523 south-pole mosaic (local clear derivative) | Locations tab background map |
| `web/review-candidate/media/lroc_south_band.jpg` | NASA / GSFC / ASU LROC WAC | Alternate map layer |
| `web/review-candidate/vendor/three.module.min.js` | Three.js (local copy, `THREE_LICENSE.txt`) | Optional sky-stage rendering |
| `data/offline/assets/PIA13523-south-pole.jpg` | PIA13523 | Backup reference image |

## Terrain review history

The release keeps terrain classified as **Unknown** because the M4 review has not passed. The evidence below is diagnostic, not a sign-off.

### 1. Site04 5 m near-field check (educational repo, reported)

- **Source:** `data/LOLA_5mpp/Site04/Site04_final_adj_5mpp_surf.tif`.
- **Observer:** Site04 S04-P02, projected coordinate X=−2652.5 m, Y=−6082.5 m; the DEM pixel centre row 1416, col 1269.
- **Sampling:** 720 azimuth bins at 0.5°; radial samples out to 5 km.
- **Coverage:** 720/720 bins with samples.
- **Finding:** Method A and Method B agreed to ~3.6×10⁻¹⁵° maximum absolute profile difference on the same pixel-centre samples. This checks two code paths against each other, not independent validation of the DEM or the frame tie.
- **Remaining question:** The 5 m raster covers only 16 × 16 km, so it cannot supply a far-field skyline.

Source: [educational repo `docs/BENCHMARK_PLAN.md`](https://github.com/M9nx/lunar-landing-site-navigator-edu/blob/main/docs/BENCHMARK_PLAN.md) (read-only historical evidence).

### 2. Product 90 compatibility and radial/overlap diagnostics (educational repo, reported)

- **Source:** `data/LOLA_20mpp/LDEM_80S_80MPP_ADJ.TIF` and `LDEM_60S_240MPP_ADJ.TIF`.
- **Observer:** Site04.
- **Sampling:** 720 × 0.5° azimuth bins; 80 m band 5–100 km; 240 m band 100–450 km; pixel-centre assignment.
- **Finding:**
  - 80 m band: all 720 bins have at least one sample; the largest inner-ring gap reported is ~3362 m under the assignment rules (bin 313 corridor diagnostic). This is a posting/binning diagnostic, not proof of a NoData wedge.
  - 240 m band: all 720 bins have samples; largest radial gap ~339 m, posting-limited.
  - Co-located overlap diagnostics (80 m − aggregated 5 m, 240 m − 80 m) show median residuals near 0 m, but the PROJ operation description contains `Ballpark`, so the residuals are diagnostic only.
- **Remaining question:** Independent frame/body-fixed tie between `MEAN_ME`/DE441 (Horizons) and `MOON_ME`/DE421 (PGDA Product 90); vertical-datum proof; and a coverage policy for inner-ring gaps and NoData holes.

Source: [educational repo `docs/FAR_FIELD_B5_B6_PLAN.md`](https://github.com/M9nx/lunar-landing-site-navigator-edu/blob/main/docs/FAR_FIELD_B5_B6_PLAN.md) and [BENCHMARK_PLAN.md](https://github.com/M9nx/lunar-landing-site-navigator-edu/blob/main/docs/BENCHMARK_PLAN.md) (read-only historical).

### 3. Fresh 240 m diagnostic profiles (this release)

- **Source:** `data/LOLA_20mpp/LDEM_60S_240MPP_ADJ.TIF`.
- **Observers:** Site04 (height 1,738.902 m) and Malapert (DEM surface height 4,864.25 m, not the practice 0 km observer).
- **Sampling:** 5° azimuth bins, 1.5–50 km at 1.5 km radial steps.
- **Finding:**
  - An independent 20 m DEM sightline for Site04 agrees with the 240 m profile geometry to 0.002°–0.27° on the same radial grid.
  - Finer radial steps raise the horizon by up to +8.5° at some azimuths inside the 1.5 km first step, so a populated bin does not prove radial coverage.
  - Azimuth interpolation wraps between 359° and 0°; a gap in either bracketing bin makes the direction Unknown (`terrain_gap_in_azimuth_bracket`).
- **Files:** `web/review-candidate/terrain/site04-p02-practice-dem240-horizon-diagnostic.json`, `web/review-candidate/terrain/malapert-practice-dem240-horizon-diagnostic.json`.

Evidence: `builder/docs/evidence/s2/terrain_independent_skyline.json`, `tests/test_terrain_geometry.py`.

## The Malapert discrepancy

The saved Malapert practice request uses **0 km** above the 1737.4 km reference sphere. The DEM surface at the same longitude and latitude is about **4,864.25 m** above that sphere.

| Observer basis | Height | What it means |
|----------------|--------|---------------|
| Saved Horizons request | 0 km | Practice value; the observer is below the terrain surface. |
| DEM240 pixel at Malapert | 4,864.25 m | Surface height from `LDEM_60S_240MPP_ADJ.TIF`. |

### What changes and what does not

- **Geometric 0° result:** A reported sensitivity capture at 4.86425 km found 0 of 193 samples changing state; both bodies stayed Blocked. That capture was **not re-queried on this machine** and is treated as reported only.
- **Terrain result:** Would change. A skyline traced from 0 m sits inside the terrain, so the practice 0 km observer cannot be used for terrain clearance without a deliberate Science decision and a matching new Horizons export.

Evidence: `builder/docs/evidence/s2_malapert_reference_altitude.md`.

## M4: concrete next attempt

The next step is to produce one independently checked skyline direction for Site04 before any terrain-mode claim.

1. **Verify the 240 m file and Site04 observer frame/height.**
   - Confirm `data/LOLA_20mpp/LDEM_60S_240MPP_ADJ.TIF` SHA-256, CRS, and NoData.
   - Confirm Site04 observer: east longitude −156.4386°, latitude −89.7812°, height 1,738.902 m above the 1737.4 km reference sphere.
   - Record the frame convention used by the DEM (PGDA documents MOON_ME/DE421) and the Horizons observer frame (`MEAN_ME`/DE441). Science decides whether the product-level description is sufficient or a control-point tie is required.

2. **Independently trace the recorded 318.623526° direction.**
   - Target azimuth: the Sun’s centre at Site04 on 2025-01-01T00:00:00Z, `318.623526°` clockwise from true local north.
   - Range: 0 to at least 100 km, using both the Site04 5 m DEM (0–5 km) and the 240 m DEM (5–100 km).
   - Sampling: fine enough to catch near-field features (sub-100 m steps near the observer) and coarser far-field steps where the DEM posting limits resolution.
   - Gaps: flag any NoData or missing radial coverage; do not bridge gaps.
   - Horizon-angle comparison: report `H(318.623526°)` from the skyline and compare to the geometric elevation of the Sun at that azimuth.

3. **Record range, sampling, gaps, and the comparison.**
   - Output: `range_m`, `sampling_m`, `max_gap_m`, `horizon_elevation_deg`, `sun_elevation_deg`, `margin_deg`, `coverage_flag`.
   - Use two independent traversals (e.g. the engine’s terrain module and a separate sightline script) and compare their horizon angles.
   - Science sets the tolerance and accepts or rejects the result.

4. **Apply the same workflow to Malapert after reconciling its observer reference.**
   - Choose a reviewed surface height (e.g. DEM surface, mast height above it, or another reference).
   - Re-query JPL Horizons for Malapert at that height using the team contact value; save the receipt.
   - Build a skyline for the new observer and run the 318°/Sun and Earth directions through it.
   - Until then, Malapert terrain remains Unknown and the practice 0 km result is shown for geometric 0° only.

## What is not claimed

- No terrain clearance total is produced or displayed.
- Product 69 is long-term context, not a timestamped centre-ray benchmark.
- The near-field 5 m pass and the Product 90 coverage diagnostics are reported historical evidence; they do not close far-field B5 or M4.

## References

- [educational repo BENCHMARK_PLAN.md](https://github.com/M9nx/lunar-landing-site-navigator-edu/blob/main/docs/BENCHMARK_PLAN.md)
- [educational repo FAR_FIELD_B5_B6_PLAN.md](https://github.com/M9nx/lunar-landing-site-navigator-edu/blob/main/docs/FAR_FIELD_B5_B6_PLAN.md)
- [educational repo B5_OWNER_REVIEW_CHECKLIST.md](https://github.com/M9nx/lunar-landing-site-navigator-edu/blob/main/research/B5_OWNER_REVIEW_CHECKLIST.md)
- `builder/docs/evidence/s2_science_review.md`
- `builder/docs/evidence/s2_malapert_reference_altitude.md`
- `builder/docs/evidence/s2/terrain_independent_skyline.json`
