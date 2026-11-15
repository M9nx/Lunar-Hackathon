# Science and Data Reference — Lunar Landing Site Navigator (local candidate)

For reviewers who need to know exactly what was computed, from which data, and what the numbers do and do not mean. Users: [User Guide](user-guide.md). Operators: [Operator Manual](operator-manual.md). Science acceptance of anything here is a separate decision recorded in `builder/docs/evidence/s2_scope_decision.md`; this document does not make it.

## 1. Claim scope

**Claimed.** For a saved observer on the Moon and a saved UTC grid: whether the **centre** of the Sun (Horizons body `10`) or of Earth (`399`) has an apparent, airless elevation **above** a flat 0° horizon, per sample and as interval totals. Three lanes: *Sun-centre clearance*, *Earth-centre clearance*, *Both centres clear*.

**Not claimed.**

* Visibility of the Sun's or Earth's *disc*. A centre just below 0° can leave part of the disc above the horizontal plane. That does not change the centre-ray state.
* Received power, illumination, or thermal conditions.
* Ground-station or radio-link availability. Earth-centre clearance is not contact.
* Terrain clearance. Terrain is **Unknown** (`terrain_not_reviewed`) in every view and export.
* That any case is eligible for a submission claim. All inputs are practice and `eligible_for_submission_claim` is `false` until the Lead records a decision.
* Agreement with NASA LRO Product 69 (§8).

## 2. Data provenance (JPL Horizons)

Each export lives in `data/horizons/<site>/<body>-<hash12>/` as three files: `response.json` (raw Horizons reply), `provenance.json` (request and checksums), `angles.csv` (parsed rows).

| Request field | Value |
| --- | --- |
| Service | JPL Horizons API 1.2, `https://ssd.jpl.nasa.gov/api/horizons.api`, `format=json` |
| Target | `COMMAND='10'` (Sun) or `'399'` (Earth). Barycentre `3` is rejected. |
| Observer | `CENTER='coord@301'` (Moon), `COORD_TYPE='GEODETIC'`, `SITE_COORD='<east lon°>,<lat°>,<alt km>'` |
| Output | `EPHEM_TYPE='OBSERVER'`, `QUANTITIES='4'` (azimuth and apparent elevation), `ANG_FORMAT='DEG'`, `CSV_FORMAT='YES'` |
| Time | `TIME_TYPE='UT'`, `START_TIME`, `STOP_TIME`, `STEP_SIZE` (15 m for 48 h, 60 m for 30 d) |
| Cuts | `ELEV_CUT='-90'`, `SKIP_DAYLT='NO'`, so every step is returned, including below the horizon |
| Response header (checked) | `Atmos refraction: NO (AIRLESS)`, `Center pole/equ : MEAN_ME (high precision)`, ephemeris DE441, lunar radius 1737.4 km, columns `Azi_(a-app)`, `Elev_(a-app)` |

Retrieval date: 13 November 2026 (header timestamp). The saved response is the truth for a run; nothing is re-queried when a result is computed.

### Observers

| Case site | East longitude | Latitude | Height in request | Meaning of the height |
| --- | --- | --- | --- | --- |
| Site04 (`site04-p02-practice`) | −156.4386° | −89.7812° | 1.738902 km | Practice request value; within about 2–5 m of the DEM at the site. |
| Malapert (`malapert-practice`) | −2.93° | −85.99° | **0.0 km** | Height above the 1737.4 km reference sphere. The DEM surface at Malapert is about 4.85 km above that sphere, so this observer is below the terrain surface. It is a practice request value, not a reviewed surface height. See `builder/docs/evidence/s2_malapert_reference_altitude.md`. |

The geometric 0° result for Malapert is reported (in the preflight, from a capture not held on this machine and **not re-queried**) not to change at 4.86425 km. Treat that as reported only. The terrain result *would* change.

### Raw-file identity (open)

The SHA-256 of the on-disk `response.json` for the original 48 h exports differs from Master Reference Appendix B. Matching angle rows do not close that. Both digest sets are kept in `builder/docs/evidence/s2/horizons_digest_provenance.md`. The 30-day exports are not in Appendix B. The mismatch stays **open** until a file-level comparison is done.

## 3. The 0° centre-ray method

For each saved sample with elevation `e` (degrees) and horizon `h = 0°`:

```
margin = e − h            (unrounded)
state  = clear    if margin > 0
         blocked  if margin ≤ 0        (exact contact is blocked)
         unknown  if the angle is missing for that body and time
```

Both lane: **blocked** if either body is blocked; else **unknown** if either is unknown; else **clear** only if both are clear. Classification uses the unrounded value. Display rounding never changes a state.

Azimuth is clockwise from true local north in [0°, 360°). Elevation is relative to local horizontal. Both are degrees. Times are ISO 8601 UTC ending in `Z`.

**Invalid versus missing.** Malformed rows, conflicting duplicate timestamps, a changed frame or angle convention, or a hash that does not match provenance are rejected with an error naming the file. A valid scenario with missing coverage keeps the requested grid and marks the affected body and time `unknown` with a reason. Missing numbers are `null`; `0` is a real angle.

## 4. Intervals

Interval policy `left_sample_both_endpoints`:

* A sample at `t` represents `[t, t + step)`: start included, end excluded.
* The final sample (at the window end) represents **0 s**.
* Adjacent samples with the same state merge into one interval.
* For every lane, clear + blocked + unknown = requested duration. For 48 h at 15 min: 192 samples × 900 s = 172,800 s.

The sampling is the limit of resolution: a transition happens somewhere between two samples. The tool reports the sample times either side, not the exact crossing.

## 5. Terrain

No terrain-mode result is produced. The M4 gate (reviewed frame, vertical reference, radial coverage, one independently checked skyline direction) has **not** passed. The 0° baseline is always labelled and selectable; terrain is Unknown.

Builder evidence for the Science review (not a sign-off): `builder/docs/evidence/s2_science_review.md` and `s2/terrain_independent_skyline.json`.

* Diagnostic DEM240 profiles (5° bins, 1.5–50 km at 1.5 km) exist for display only.
* An independent trace on the 20 m DEM agrees with the profile geometry to 0.002°–0.27° on the same radial grid (spherical Moon, R = 1,737,400 m; flat same-height ground at 100 km gives `−θ/2 = −1.648894°`, matched to 1×10⁻⁹°).
* Finer radial steps raise the horizon by up to +8.5° at some azimuths (Malapert, azimuth 359°–1°: a cell 300 m away). So a populated azimuth bin does not establish radial coverage.
* Azimuth interpolation wraps between 359° and 0°; a gap in either bracketing bin gives Unknown (`terrain_gap_in_azimuth_bracket`). Tested in `tests/test_terrain_geometry.py` (30 tests).
* Open for Science: the frame tie (`MEAN_ME` with DE441 versus the DEM's `MOON_ME`/DE421 description), height reference, minimum range and step, tolerance.

## 6. One worked sample

All values are copied from saved files; you can check each against `response.json`.

**Sample.** Malapert, Sun, 2025-01-01T00:00:00Z.

1. Raw Horizons line (`data/horizons/malapert-practice/sun-d10bfb555ec3/response.json`):
   `2025-Jan-01 00:00, , , 165.111466,    -2.355809,`
   Azimuth 165.111466°, apparent elevation −2.355809°.
2. Horizon 0° → margin = −2.355809 − 0 = **−2.355809°** → `≤ 0` → **blocked**.
3. Earth at the same time: line `2025-Jan-01 00:00, , , 358.310734,    -2.303347,` → margin −2.303347° → blocked. Both lane: blocked (`centre_below_or_on_horizon:sun+earth`).
4. Source row in the result file: `horizons/malapert-practice/sun-d10bfb555ec3/angles.csv#row=2`.

**Interval total (30 days, Malapert, Sun).** Hourly samples; the blocked→clear transition pair is shown in the *Why* panel and in the notebook.

* 2025-01-05T09:00Z: line `2025-Jan-05 09:00,*,i, 111.880820,    -0.011369,` → margin −0.011369° → blocked.
* 2025-01-05T10:00Z: line `2025-Jan-05 10:00,*,i, 111.375064,     0.021266,` → margin +0.021266° → clear (first clear sample, `angles.csv#row=108`).
* Clear continues until the sample at 2025-01-23T14:00Z, the first blocked sample after it.
* Clear interval `[2025-01-05T10:00Z, 2025-01-23T14:00Z)` = 18 d 4 h = **436 h** = 1,569,600 s. Blocked: `[start, 01-05T10:00Z)` and `[01-23T14:00Z, 01-31T00:00Z)` = 1,022,400 s. Unknown: 0. 1,569,600 + 1,022,400 + 0 = 2,592,000 s = 720 h. ✓

Reproduce independently: `docs/notebooks/01_trace_observation_to_interval_total.ipynb` (standard library only) reads the saved rows, applies the rule, builds the intervals, and compares with the engine. It runs offline from a fresh project (`builder/scripts/run_notebook.py --check <notebook>`).

The values in the flag columns of a Horizons row (`*`, `i`, blanks) are not used by the engine; only azimuth and elevation are read.

## 7. Practice cases and results

| Case | Window | Step | Sun clear | Earth clear | Both clear |
| --- | --- | --- | --- | --- | --- |
| Site04, 48 h | 2025-01-01 → 01-03 | 15 min | 48 h | 0 h | 0 h |
| Malapert, 48 h | same | 15 min | 0 h | 0 h | 0 h |
| Site04, 30 d | 2025-01-01 → 01-31 | 1 h | 720 h | 303 h | 303 h |
| Malapert, 30 d | same | 1 h | 436 h | 456 h | 398 h |

Unknown is 0 h in every row. Source: each case's `runs/*.json` → `elapsed_seconds`.

A site-to-site overlap difference is shown only when duration, step, horizon mode and interval policy match, and each case's Unknown duration is shown beside it. A geometric-versus-terrain comparison would be labelled a model comparison; none exists yet.

## 8. Product 69 and "any-disc" (context only)

The LRO south-pole 240 m solar product (Product 69) reports, per pixel, the fraction of modelled timesteps in which *any part* of the Sun's disc was visible (a crescent and a full disc both count; no area or power weighting). Its Earth layer is the fraction of timesteps when any part of Earth's disc was unobscured, not visibility of a specific station. It describes a long-term average (the product page: hourly averages over 18.6 years; PDS labels carry `START_TIME`/`STOP_TIME` in 2009–2013; the simulation start and end are not fixed by those sources and are left unresolved).

Product 69 therefore supplies neither a timestamped answer nor a like-for-like benchmark for a centre-ray window. This tool does not compare against it. A future any-disc metric needs angular size and terrain coverage across the disc's azimuth span, and must match period, cadence, location, observer height, terrain basis and visibility definition before any comparison.

## 8a. Missing angles, terrain Unknown, and the expanded real cases

- **Missing angle (`n.a.`).** Kept as a row with `null` angles, never `0`. A missing angle at sample *t* makes the span ending at *t* Unknown (`missing_right_endpoint` on the left sample) and the span starting at *t* Unknown (`missing_ephemeris`). On a 15-minute grid, `n.a.` at 00:30 gives 30 minutes of Unknown, 00:15 to 00:45. Adjacent intervals with different reasons stay separate in the engine and are merged for display. Sun, Earth and Both Unknown are counted separately, and Clear + Blocked + Unknown equals the requested duration for each lane. A confirmed blocker beats Unknown in Both.
- **Terrain mode.** Needs a skyline reviewed for the matching observer (`<data>/terrain/reviewed/*.json`: approved review, reviewer, frame, vertical reference, radial coverage, independent check). Otherwise every sample is Unknown with `terrain_not_reviewed`, `terrain_no_skyline_for_observer` or `terrain_review_incomplete`; a gap in the azimuth bracket gives `terrain_gap_in_azimuth_bracket`. The elevation is kept and the horizon and margin are blank. No reviewed skyline exists, so every real terrain-mode run is Unknown. The diagnostic DEM profile is not a review.
- **Real cases.** The six-hour scans (2025-01-01 to 2025-04-01) and 15-minute windows are real JPL Horizons practice exports with no `n.a.` rows, so they carry no Unknown. They contain all four outcomes (Sun-only, Earth-only, Both-clear, neither) and many crossings. The traced spans are in `docs/real-case-trace.md`. They are centre-ray clearances at practice sites and say nothing about disc visibility, power or contact.

# 9. Limitations

* Centre-ray only; terrain Unknown; practice inputs; not eligible.
* Resolution is the sample step (15 min, 1 h). Transitions between samples are not located.
* Malapert height is a practice value below the terrain surface.
* Raw-file identity against Appendix B is open.
* Horizons angles come from DE441 with the Moon's `MEAN_ME` frame; no independent ephemeris was compared.
* Two real practice sites in two windows; a synthetic QA fixture exercises Unknown and transitions and says nothing about the Moon.
