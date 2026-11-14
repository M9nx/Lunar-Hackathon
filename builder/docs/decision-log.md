# Decision log

Record amendments with date, owner, previous/new decision, evidence, and milestone impact (Master Reference §11).

## Repository layout (2026-11-14)

- **`builder/`** — agent worker (handoff, harness scripts, skills, task/decision logs). Not submission product code.
- **Repo root** — `src/`, `web/`, `tests/`, `Master-Reference/`, `data/`.

## M0 closure — evidence still needed (QA / Lead / Data)

| Item | Owner | Status |
|------|-------|--------|
| **Selected case** (Site A observers, UTC window, or approved one-site/two-window fallback) | Data + Science | **Practice replay selected.** Submission eligibility and Malapert 0 km height stay open. |
| **Kickoff disposition** (brief, eligibility, submission format, AI disclosure) | Lead | **Open** — title page loaded; Resources tab still HTTP 500 |
| **Wi-Fi-off witness** | QA | **Passed** — `wlan0` down and soft-blocked at 2026-11-14T09:54:24Z on `m9nx-83dg`. Attestation written. Smoke exit 0. Radio restored afterward. |
| **Backup data copy** on demo laptop | QA / Data | **Passed** — `/home/m9nx/Lunar-Hackathon-data-backup`. Core and four practice Horizons checks exit 0 on both copies. |
| M0.3 vs M0.2 alignment | Lead if bundle precedes final case | Staged bundle includes both practice exports. Submission claim **not** accepted |

Run: `cd builder && python3 scripts/check_m0_closure.py`

## Kickoff session

| Field | Value |
|-------|--------|
| **Kickoff confirmed (harness)** | 2026-11-14 — project-scoped lunar-builder harness started in this repo (user-directed). |
| **Official local H0** | *Open — Lead:* confirm wall-clock kickoff with organizers. |
| **Working window (proposed)** | 36 h from H0; freeze target H30; submission target H34; 2 h reserve (local workbook *Timeline* sheet). |
| **Schedule authority** | `Master-Reference/MASTER_REFERENCE.json` → `schedule.tasks` (32 items M0.1–M6.5). Local `docs/Lunar-Hackathon-Timeline.xlsx` has **Timeline** + **Milestone decisions** only; **no Tasks tab** — discrepancy recorded 2026-11-14 (`scripts/compare_workbook_schedule.py`). |

### M0.1 — Event scope, cutoff, resources, disclosure

| Decision | Status | Owner | Notes / evidence |
|----------|--------|-------|------------------|
| Submission channel | **Recorded** | Lead | The 2026 listing confirms submission through the team’s Project tab. Exact required fields and demo limits remain unverified because the Resources guide page returned an error. |
| Project tab text | **Approved for now** | Lead | Draft in `docs/evidence/m0_1_project_tab_draft.md`. Demo recording uses `1f3fb06`. This approval is the text, not eligibility. |
| Actual submission cutoff | **Recorded** | Lead | Sunday, November 15, 2026, at 11:59 p.m. local event time. |
| Eligible NASA data sources | **Source listed; case still open** | Lead | The captured Resources tab lists JPL Horizons. Lead uses that screenshot for the source check. Whether the saved January 2025 practice runs can support the submission is a separate decision. |
| Permitted tools / AI use | **Required, unfinished** | Lead | Disclose how AI was used before submission. [Organizer discussion](https://github.com/nasa/spaceapps/discussions/1849). A starter sentence is in the Project tab draft. |
| Result format (UTC, Unknown states) | **Confirmed (design)** | Lead + QA | Versioned run JSON per §5; states `clear` / `blocked` / `unknown`; ISO 8601 UTC with `Z`. |
| Practice Horizons for demo claim | **Open** | Lead | Keep `eligible_for_submission_claim=false` until Lead records whether the January 2025 practice runs can support the submission. Use demo commit `1f3fb06`. A replacement case, if approved, is a separate hardened-engine candidate. |

### M0.2 — Observer selection (in progress)

| Item | Status | Notes |
|------|--------|--------|
| Practice Site04-P02 | Recorded | `data/horizons/site04-p02-practice/` — 193-row Sun/Earth CSVs; **practice only** |
| Practice Malapert | Recorded | `data/horizons/malapert-practice/` — **practice only** |
| Working Site A | **Selected for practice replay** | `site04-p02-practice`: east lon −156.4386°, lat −89.7812°, Horizons reference altitude 1.738902 km. Sun `10`, Earth `399`, `coord@301`, Q4 airless. `practice=true`. Not a submission claim. |
| Working Site B | **Selected for practice replay** | `malapert-practice`: east lon −2.93°, lat −85.99°, reference altitude **0 km** (not a reviewed surface height). Same query shape and window. |
| UTC window & cadence | **Selected for practice replay** | `2025-01-01T00:00:00Z` through `2025-01-03T00:00:00Z`, step 900 s (193 samples, 192 intervals, 172800 s). |
| Observer height reference | **Open for any height-dependent claim** | Site A uses the Horizons `SITE_COORD` kilometres. Site B’s practice altitude is 0 km. Malapert **4.86425 km** is a sensitivity input, not the practice or submission height. A reported quantity-4 rerun at that altitude changed no 0° sample state. |
| Why this pair | Recommendation | Only Sun+Earth pair staged under `data/horizons/`. Case-fit passed for both practice scenarios with `eligible_for_submission_claim=false`. Recomputed 0° totals: Site A Sun clear 172800 s, Earth and Both blocked 172800 s; Site B all three lanes blocked 172800 s; Unknown 0 s. Visible difference is Sun-centre clearance. Joint Both clearance ties. |
| Appendix B raw SHA-256 | **Unresolved** | Keep both raw-response digest sets. On this laptop, `response.json` matches the PR run-input digests and does not match Appendix B. A separate rerun reported the reverse file identity. The matching angle CSVs support the replay totals. Raw-file identity stays open. Reference text was not edited. |

## Centre-ray versus Product 69 (2026-11-14)

Confirmed for the sprint and enforced in `builder/.cursor/rules/lunar-guardrails.mdc`. Previous working rule already kept centre-ray clearance and forbade power or radio-link claims. This amendment fixes the labels and bars Product 69 from validating a centre-ray window.

| Decision | Status | Owner | Notes |
|----------|--------|-------|--------|
| Navigator math | **Confirmed** | Science | Horizons quantity 4, apparent airless azimuth and elevation of the **target centre** from the lunar observer’s local horizontal. Sun `10`, Earth `399`. |
| M1–M3 labels | **Confirmed** | Science + UI | **Sun-centre clearance**, **Earth-centre clearance**, **Both centres clear**. Practice 48-hour 0° totals stay valid under that sampled policy. Submission eligibility stays pending. |
| Validation | **Confirmed** | QA | Trace angles to saved Horizons rows. Test horizon, interval, and Unknown rules on their own. |
| Product 69 role | **Confirmed (context only)** | Science | South-pole 240 m solar layer: fraction of modeled timesteps when **any portion of the Sun’s disc** was visible. A crescent and a full disc both count. No weighting by visible area or received power. Earth layer: fraction of timesteps when **any portion of Earth’s disc** was unobscured, not a specific ground station. |
| Product 69 as a centre-ray benchmark | **Rejected** | Science | A pixel is not a timestamped answer and not a like-for-like check of a centre-ray window. |
| Product 69 dates | **Unresolved** | Science | Product page: hourly averages over 18.6 years. PDS labels also carry `START_TIME` and `STOP_TIME` in 2009–2013. Do not invent the simulation start or end. |
| Any-disc metric | **Deferred** | Science | Separate from centre-ray. Needs angular size and terrain coverage across the disc’s azimuth span. Match period, cadence, location, observer height, terrain basis, and visibility definition before comparing averages. |
| Malapert definition check | **Recorded** | User, 2026-11-14 | A fresh Horizons query with quantities 4 and 13 matched the saved CSVs at reported precision for both bodies at the two requested timestamps. At `2025-01-02T23:45:00Z`, Earth centre elevation **−0.474336°**, apparent diameter **6999.524 arcsec**. Circular-disc upper limb about **+0.497820°** relative to the 0° plane, so the centre is Blocked while part of the disc clears that plane. Terrain clearance and ground-station visibility stay unverified. This limb figure is not a navigator state. |

### M0.4 — Runtime (passed 2026-11-14)

Python **3.14.9** matches wheel tag `cpython-314-linux-x86_64`. Offline venv imports and DEM window smoke: `docs/evidence/m0_4_wheels.log`, `docs/evidence/m0_4_open_dem.log`.

### M0.3 — Local dataset bundle (passed 2026-11-14)

Staged tree under `data/` (~5.5 GB inventory). Core + Horizons practice checks: `docs/evidence/m0_offline_smoke.log`. Large rasters remain outside Git per `.gitignore`.

### §12 decisions still open (unchanged at M0.1)

| Decision | Proposed start | Owner |
|----------|----------------|-------|
| Observer A/B and UTC window | Two points; one-site two-window fallback | Data + Science |
| Submission coordinates & height refs | Not set | Data + Science |
| Terrain DEM for M4 | Product 90 vs 78 — defer to M4 | Science |
| Python pin | Match demo laptop to wheel tag `cpython-314-linux-x86_64` | Engine |

## M2.5 preflight (2026-11-14)

Diagnostic only. M2.5 stays blocked. Detail: `docs/evidence/m2_5_preflight.md`.

| Item | Status | Owner |
| --- | --- | --- |
| Product 90 file identity, 240 m grid, area registration, NaN NoData | **Recorded** | Data |
| Frame tie: IAU 30135 / 1,737,400 m sphere versus PGDA MOON_ME/DE421 versus Horizons MEAN_ME and DE441 | **Open** | Science |
| DEM height reference and a reviewed observer height | **Open** | Science |
| Radial coverage and one independently traversed skyline | **Open** | Science |
| Header frame and airless angle convention bound to the scenario | **Confirmed for the next production run** | Engine |

The witnessed 0° demo build stays commit `1f3fb06`. Do not regenerate that package. New Horizons runs use the hardened engine, which binds the raw header’s frame and airless angle convention to the scenario (19 tests passing in the working tree).

The next decision for a 0° submission is Lead’s confirmation of eligibility and the required deliverables. Science reviews terrain in parallel. Until that review passes, the replay shows terrain as Unknown. Malapert 4.86425 km stays labeled as a sensitivity input.

## 0° judging package (2026-11-14)

The submission package is prepared around the witnessed replay. Detail: `docs/evidence/m6_0deg_submission_package.md`.

| Decision | Status | Notes |
| --- | --- | --- |
| Demo build | **Recorded** | Commit `1f3fb06`. `web/replay/` stays as witnessed. |
| M5 +24-hour comparison | **Deferred** | Not in this build. Mention it only after a later verified package includes it. |
| M4 terrain in the demo | **0° fallback** | Science review stays open. The page keeps terrain Unknown. |
| M6 freeze and submit | **Not closed** | No release tag. Eligibility stays false. The local URL is not a public demo link. The walkthrough, credits, and disclosure starter are in the package note. |

## Engine corrections (2026-11-14, commit `1f3fb06`)

| Decision | Status | Notes |
| --- | --- | --- |
| File belongs to the case | **Confirmed** | SHA-256 still checks the bytes against provenance. The production path also reads the raw Horizons header and rejects a target id or observer that does not match the scenario. A swapped Sun and Earth export fails this check. |
| Both endpoints | **Confirmed** | For `[t_i, t_(i+1))`, the left sample’s state counts only when both endpoints have usable angles. A clear Sun sample whose next Sun sample is missing is Unknown for that span. Earth stays on its own endpoint rule, then the Both rule applies. |
| Practice totals | **Unchanged** | Site A Sun clear 172800 s and Both clear 0 s. Site B Sun, Earth, and Both blocked 172800 s. Unknown 0 s. Run IDs unchanged. |

## Review-candidate NASA chrome (2026-11-14)

- **Decision:** Adapt educational-console visual patterns (NASA banner, brand header, mono kickers, stage pipe, starfield, south-pole context) into `web/review-candidate/` only. Keep `web/replay/` witnessed. Full-width sticky action rail. Offline-vendored Three.js drives an illustrative globe in `#scene-3d` that follows the shared playhead and stream batches. Procedural moon texture (no CDN albedo). Map toggle keeps local `PIA13523`. Scene emits `lunar:site-select`, `lunar:scene-scrub`, `lunar:stream-batch`, and `lunar:stream-complete`. Labels: not SPICE, not terrain clearance; terrain Unknown.
- **Source:** `~/Documents/Learning/lunar-landing-site-navigator` (read-only historical). Fresh CSS/HTML/JS in this repo.

## Two-site live stream (2026-11-14)

- **Decision:** Live comparison uses one `comparison_id` and a run ID per site on a shared UTC grid. Totals for the pair use only the shared resolved sample prefix and stay labeled partial until both sites complete. Pending samples are not scientific Unknown. Complete comparison export only after both succeed. Incompatible grids return an actionable error. Evidence: `docs/evidence/stream_comparison_live.md`.
- **Unchanged:** Centre-ray 0° practice totals (172800 s vs 0 s Sun clear; both clear 0 s). Terrain Unknown. `web/replay/` witness `1f3fb06`. Eligibility false. Horizons acquisition separate.

## Workbook vs JSON schedule (2026-11-14)

- **Workbook sheets:** `Timeline`, `Milestone decisions` (high-level M0–M6 phases).
- **JSON snapshot:** 32 executable tasks (`M0.1` … `M6.5`, `Rest`).
- **Agent routing:** Use JSON unless Lead replaces snapshot and updates this log.

## Review-candidate sky stage (2026-11-14)

- **Decision:** Scene stage uses the PIA13523 south-pole map plus dual polar sky plots. DEM horizon silhouettes come from diagnostic LDEM 240 m profiles (`web/review-candidate/terrain/*-dem240-horizon-diagnostic.json`) via `lunar_navigator.terrain`. Status remains `diagnostic_unreviewed`. Stream speed control remains.
- **Unchanged:** Classification is centre-ray vs geometric 0° only. Terrain mode Clear/Blocked is blocked until M4 review. Eligibility false. No CDN at runtime.

## Review-candidate verdict, windows, and locations (2026-11-14)

- **Decision:** The first screen is a selected-UTC verdict sentence plus two sky plots, not the map. Full-window totals are labelled separately. The 0° ring is the primary reference. The DEM profile is opt-in ("Show terrain diagnostic"), drawn as a thin line with hatching for no-data azimuths, and never changes a state. Malapert at 13:00 UTC stays "Blocked at geometric 0°" (Sun −2.22° vs displayed DEM −9.37°) with terrain Unknown.
- **Plot scale:** One linear elevation scale on both plots: centre +15°, 0° ring, edge −15°. The old radial mapping clamped near +23° and labelled the centre "zenith". That label is gone. Off-scale markers sit on the rim and say "off scale".
- **Windows explorer:** Reads `payload.intervals` and `elapsed_seconds` only. Adjacent intervals with the same state are merged for display (reasons listed). "Closest to 0°" is a navigation aid for a lane with no transition. It adds no window and no claim.
- **Locations:** The map moved to a Locations tab. A (circle) and B (diamond) pins. Yellow and blue are reserved for Sun and Earth. Registration check: the 85°S graticule ring measures 379 px at eight azimuths against a predicted 379.3 px (2R·tan(colat/2), 400 m/px, 1521 px). Orientation (0° up, east right) was checked only against Amundsen. Coordinate picking and distances stay out until a second landmark or a georeferenced source is checked. Evidence `docs/evidence/pia13523_registration.log`.
- **Live runs:** Server batch (4) and pause (0.05 s) are fixed. "Playback speed" is client display pacing only. Follow latest turns off on any user move. Pending samples are drawn as a Pending zone and counted as pending, not Unknown.
- **Metrics and preview (follow-up):** Per-plot metric cards are back (all saved values, always, including during a stream) with a per-plot stream meter. Clicking a marker, card, window, or timeline segment opens a fixed preview card with a margin chart; window clicks preview first and jump only from the card. Controls regrouped as Data, Live run, Playback speed. Play/Pause now gives Playback speed a replay meaning. It remains display pacing only.
- **Sky tools (follow-up):** Scale presets, path, layers, sites, decimals, step size, change/start/end jumps, focus lane, and a cursor az/el readout. All are display settings and change no engine result. Decimals default to 6 so saved fractions show in full. The verdict sentence stays at 2 decimals for readability. Both plots always share one scale.
- **Terrain shapes (follow-up):** The DEM skyline can be shown as Silhouette (default), Outline, or Raw bins, with peaks and Sun/Earth leaders. Colours: sand below the 0° ring, rust above it; yellow and blue stay for Sun and Earth. The smooth outline is a Catmull-Rom spline through 5° bins, so it is a visual aid; Raw bins draws the saved values unchanged and is the honest view. Unknown azimuths split the skyline (never bridged) and keep the hatch. Summary chips report high, low, share of known azimuths above 0°, unknown azimuth span, bin size and range. Terrain diagnostic stays `diagnostic_unreviewed`, never changes a state, and terrain stays Unknown until M4. Leaders use linear interpolation between the two neighbouring bins; the metric cards and notes keep the nearest-bin value.
- **One flow (2026-11-15):** The page is reordered as choose the case → read the result → select a window → inspect why. The first screen is a compact scenario bar (sites, UTC range, sample step, Geometric 0°) and a Sun-centre headline that gives both sites equal weight, then "Both centres clear · 0 h at either site". Raw seconds, sample counts, Unknown durations and `terrain_not_reviewed` sit under Details. "0 h" for zero, "min" when minutes are needed. Practice and Terrain clearance unknown stay visible in the header and beside the numbers.
- **One lane picker:** Sun / Earth / Both sits above the timeline and drives the chart, lanes, margins table, Windows rail and readout. Sun and Earth draw A (solid) and B (dashed) traces with direct labels. Both draws the joint lanes and a table of the two individual centre margins at the selected time (the Both lane uses the smaller). A window click (row or lane segment) highlights its span, selects its site and moves the shared playhead to its start. The exact Horizons row, source, run ID and export live behind View evidence. Changing the lane clears the window selection.
- **Closest sampled point to 0°:** offered only for Sun or Earth when a site has no clear window. It names the sample and, when it is the final sample, says that sample adds 0 elapsed time. A navigation aid only.
- **Unknown, not a clearance:** the readout labels an Unknown state with its reason and never presents a margin as a clearance. A sample with no saved angle shows "no saved margin" (null, not 0).
- **Live feedback:** per-site progress, "Results through <latest shared UTC>", partial headline "Partial totals through <that UTC>". Pending (not calculated yet) is dotted with a dashed cutoff line. Scientific Unknown is crosshatched and purple. The playhead range is the shared resolved sample count and grows with the stream.
- **Narrow screens:** result before chart; Windows stacked below the timeline; the time dock is sticky with a one-line UTC / state / margin readout. The chart is drawn in real pixels so axis text stays 11 px.
- **Screening filter:** Minimum clear window (any, 15 min, 1 h, 2 h, 4 h, 8 h). It hides clear rows shorter than the minimum, lists qualifying windows per site with a summary line, dims shorter lane segments, and says when none qualify and what the longest clear window is. It reads the same merged engine intervals and never changes totals, headline numbers or the joint line. It resets when the case changes. Practice: 4 h Sun → Site04 1 window, Malapert none; 4 h Both → none at either site.
- **Unchanged:** Centre-ray vs geometric 0°. Terrain Clear/Blocked waits for M4. Eligibility false. `web/replay` untouched (witness `1f3fb06`). No CDN.

## Educational archive (read-only)

Path: `~/Documents/Learning/lunar-landing-site-navigator`.  
Lessons carried forward: MOON_ME/DE421 frame ties, height reference vs surface, NoData/radial gaps, near-field-only 5 m DEM horizon, offline replay without CDN (`docs/BENCHMARK_PLAN.md`, `FRAME_GEOMETRY_VALIDATION.md` — **historical**). Fresh evidence only from this repository.