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

- **Decision:** Adapt educational-console visual patterns (NASA banner, brand header, mono kickers, stage pipe, starfield, south-pole context) into `web/review-candidate/` only. Keep `web/replay/` witnessed. Do not pull CDN Google Fonts or Three.js. Full-width layout with sticky action rail for Start/Cancel/status. Context uses local `PIA13523` with approximate pins; labeled not a DEM and not terrain clearance. Scene stage emits `lunar:site-select`, `lunar:scene-scrub`, and `lunar:scene-ready` for stream/3D wiring. Three.js mounts into `#scene-3d` once vendored offline.
- **Source:** `~/Documents/Learning/lunar-landing-site-navigator` (read-only historical). Fresh CSS/HTML/JS in this repo.

## Two-site live stream (2026-11-14)

- **Decision:** Live comparison uses one `comparison_id` and a run ID per site on a shared UTC grid. Totals for the pair use only the shared resolved sample prefix and stay labeled partial until both sites complete. Pending samples are not scientific Unknown. Complete comparison export only after both succeed. Incompatible grids return an actionable error. Evidence: `docs/evidence/stream_comparison_live.md`.
- **Unchanged:** Centre-ray 0° practice totals (172800 s vs 0 s Sun clear; both clear 0 s). Terrain Unknown. `web/replay/` witness `1f3fb06`. Eligibility false. Horizons acquisition separate.

## Workbook vs JSON schedule (2026-11-14)

- **Workbook sheets:** `Timeline`, `Milestone decisions` (high-level M0–M6 phases).
- **JSON snapshot:** 32 executable tasks (`M0.1` … `M6.5`, `Rest`).
- **Agent routing:** Use JSON unless Lead replaces snapshot and updates this log.

## Educational archive (read-only)

Path: `~/Documents/Learning/lunar-landing-site-navigator`.  
Lessons carried forward: MOON_ME/DE421 frame ties, height reference vs surface, NoData/radial gaps, near-field-only 5 m DEM horizon, offline replay without CDN (`docs/BENCHMARK_PLAN.md`, `FRAME_GEOMETRY_VALIDATION.md` — **historical**). Fresh evidence only from this repository.