# Sprint 2 Science review package (builder evidence, not a Science sign-off)

15 November 2026. This page collects what the builder checked for the terrain review: frame, observer height, radial coverage and one independent skyline. **It does not pass M2.5 or M4.** Science reviews it and records the decision in `s2_scope_decision.md`. Terrain stays Unknown in the product.

## 1. Frame

| Item | Saved value | Source |
| --- | --- | --- |
| Observer frame in the Horizons request | `MEAN_ME` (header: `Center pole/equ : MEAN_ME (high precision)`) | `response.json` of every export |
| Angle convention | airless apparent (`Atmos refraction: NO (AIRLESS)`, `Azi_(a-app)`, `Elev_(a-app)`) | same; the intake rejects a copy that changes either marker |
| Ephemeris | DE441 (Horizons header) | same |
| Lunar sphere | R = 1,737,400 m (header `Center radii 1737.4 km`) | same; `terrain.MOON_RADIUS_M` uses the same value |
| DEM projection | IAU 30135 south-polar stereographic on a 1,737,400 m sphere | `LDEM_60S_240MPP_ADJ.TIF`, `LDEM_80S_20MPP_ADJ.TIF` |
| DEM frame in the PGDA description | MOON_ME / DE421 | PGDA product description (not re-read here) |

**Open for Science:** the tie between `MEAN_ME` with DE441 and the DEM's `MOON_ME` / DE421 description. The builder did not resolve it and did not apply any rotation.

## 2. Observer height

See `s2_malapert_reference_altitude.md`. Short version: Site04's practice altitude (1,738.902 m) sits within 2 to 5 m of the DEM at the site. Malapert's practice altitude (0 km) is about 4.85 km below the DEM there. The DEM240 diagnostic profile uses the DEM surface height for Malapert (4,864.25 m), which is not the height used for the 0° run. **Open for Science:** the height reference for each site.

## 3. Radial coverage

The shipped DEM240 diagnostic profiles sample 1.5 km to 50 km in 1.5 km steps at 5° azimuth bins. The nearest sample is 1.5 km out. The independent trace below uses 100 m steps and finds obstacles inside that first 1.5 km that the profile cannot see:

* Malapert, azimuths 359°, 0° and 1°: a DEM20 cell 300 m away gives +7.9° where the profile says about −0.5°.
* Site04, azimuths 359°, 0° and 1° and 90°: nearest-ground slope at 200 m gives −1.1° to −1.5° where the profile says −2.1° to −2.4°.

So a populated azimuth bin does not establish radial coverage. The product does not use these profiles for any state. **Open for Science:** the minimum range and step, and whether near-field terrain inside 1.5 km must be included.

## 4. One independent skyline

`builder/scripts/s2_independent_skyline.py` traces rays on the **20 m DEM** (`LDEM_80S_20MPP_ADJ.TIF`, SHA-256 `09b7ca80f9e6a146f970225d18af72fc02787669b3ef51b888e347d2b6845649`) and compares them with the **DEM240 profile**. It does not call `terrain._destination` or `terrain._elevation_deg`:

* ray points from `pyproj.Geod(a=R, b=R).fwd` (a spherical geodesic),
* elevation from a local East/North/Up basis, `atan2(up, hypot(east, north))`,
* the ray azimuth is recovered from the same vectors. The largest departure from the requested azimuth was below 1×10⁻¹⁰°, so every sample lies along the requested azimuth.

It also checks the analytic flat-ground case: a same-height surface at 100 km is `−θ/2 = −1.648894°`. The script and `tests/test_terrain_geometry.py` agree to 1×10⁻⁹°.

Result file: `s2/terrain_independent_skyline.json` (written by `run_sprint_evidence.sh s2`). Same observer height for both traces. Columns: DEM240 profile value, DEM20 on the profile's own radial grid (1.5 km steps to 50 km), DEM20 at 100 m steps. Differences are DEM20 minus DEM240, in degrees.

| Site | Azimuth | DEM240 | DEM20, same grid | Diff | DEM20, 100 m steps | Diff |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| Site04 | 0° | −2.219 | −2.236 | −0.017 | −1.062 at 200 m | +1.157 |
| Site04 | 90° | −2.243 | −2.241 | +0.002 | −1.534 at 200 m | +0.709 |
| Site04 | 180° | −3.179 | −3.172 | +0.006 | −3.116 at 44.5 km | +0.063 |
| Site04 | 270° | −0.786 | −0.780 | +0.006 | −0.749 at 35.6 km | +0.037 |
| Site04 | 359° | −2.363 | −2.354 | +0.009 | −1.062 at 200 m | +1.301 |
| Site04 | 1° | −2.099 | −2.157 | −0.058 | −1.062 at 200 m | +1.037 |
| Site04 | 318.624° | −2.703 | −2.686 | +0.017 | −2.637 at 6.7 km | +0.065 |
| Malapert | 0° | −0.575 | −0.455 | +0.119 | +7.946 at 300 m | +8.520 |
| Malapert | 90° | +1.407 | +1.422 | +0.014 | +1.539 at 2.0 km | +0.131 |
| Malapert | 180° | −10.382 | −10.388 | −0.006 | −10.302 at 50 km | +0.080 |
| Malapert | 270° | −4.967 | −5.009 | −0.042 | −4.786 at 700 m | +0.181 |
| Malapert | 359° | −0.575 | −0.529 | +0.045 | +7.946 at 300 m | +8.520 |
| Malapert | 1° | −0.499 | −0.433 | +0.066 | +7.946 at 300 m | +8.445 |
| Malapert | 318.624° | +3.464 | +3.730 | +0.266 | +4.391 at 700 m | +0.927 |

Reading, without a tolerance (Science sets one):

* **Geometry agrees.** On the same radial grid, the two independent implementations on two DEM resolutions differ by 0.002° to 0.27°, mostly under 0.07°. The largest is Malapert at 318.6° (+0.27°), where the terrain is steep.
* **Radial sampling disagrees.** With a 100 m step the horizon rises by up to +8.5° at some azimuths. That is a coverage finding, not a geometry error.
* **The 359° / 0° seam is consistent.** Values at 359°, 0° and 1° are continuous in both traces, and `tests/test_terrain_geometry.py` checks the wrap in the interpolation helper and with a synthetic ridge across north.
* The earlier reported value at Site04 azimuth 318.623526° (about −2.482° near 53.5 km, with a 100 km range) is for a different range. Here the range is 50 km to match the profile. The values are not comparable.

## 5. What this does not show

* No frame tie, no height-reference decision, no accepted range or step, no tolerance.
* Only seven directions at two sites. Not a full skyline.
* It does not show that the terrain-mode result is correct for any timestamp. No terrain-mode result exists.
* The practice altitudes are practice inputs.

## 6. Tests added

`tests/test_terrain_geometry.py` (30 tests): analytic equality across angles and heights; flat same-height ground at 100 km reproduces −θ/2; a raised plateau equals the analytic sightline; a ridge across bearings −4° to +4° raises 357° to 3° symmetrically and leaves 20°, 180°, 340° flat; interpolation wraps between 359° and 0°; a gap in either bracketing bin returns Unknown, including a gap at 0°; azimuth normalisation is half-open.
