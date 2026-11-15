# Task log

Persistent record of milestone work. Status: `planned` | `in_progress` | `passed` | `passed_with_open_decisions` | `blocked` | `skipped`. Only `passed` is verified credit. `passed_with_open_decisions` is conditional. `skipped` earns no credit and does not satisfy a dependency. A task recorded as done while a prerequisite is unmet is reported as invalid credit by `builder/scripts/task_counts.py`.

| Task ID | Status | Started (UTC) | Passed (UTC) | Evidence |
|---------|--------|---------------|--------------|----------|
| M6.1 | passed_with_open_decisions | 2026-11-15 | 2026-11-15 | Local 0° judging package: landing page, docs, Jan 3–10 case, release verification 24/24. Lead decisions still pending. `builder/docs/evidence/s3/release_verify/`. |
| M0.1 | passed_with_open_decisions | 2026-11-14 | 2026-11-14 | Reopened as the active handoff. Challenge page HTTP 500. `docs/evidence/m0_1_lead_handoff.md`. |
| M0.2 | passed_with_open_decisions | 2026-11-14 | 2026-11-14 | Practice pair used for the replay. Eligibility, Malapert 0 km height, and Appendix B raw hash stay open. |
| M0.3 | passed_with_open_decisions | 2026-11-14 | 2026-11-14 | `docs/evidence/m0_offline_smoke.log`; local `data/` bundle. Covers the four practice CSVs by presence and row count, not eligibility. Re-evaluated 2026-11-15: the Appendix B raw-response digest mismatch is still open (`docs/evidence/horizons_digest_provenance.md`), so the checksum acceptance is conditional. |
| M0.4 | passed | 2026-11-14 | 2026-11-14 | `docs/evidence/m0_4_wheels.log`, `docs/evidence/m0_4_open_dem.log` |
| M0.5 | passed | 2026-11-14 | 2026-11-14T09:54:24Z | `docs/evidence/wifi_off_attestation.txt`, `docs/evidence/m0_5_wifi_off.log`, `docs/evidence/m0_5_backup_checksums.log` |
| M1.1 | passed | 2026-11-14 | 2026-11-14 | Practice Sun/Earth tables joined by the engine. Case-fit already passed. |
| M1.2 | passed | 2026-11-14 | 2026-11-14 | `src/lunar_navigator/engine.py`. Later endpoint and header checks: pytest 17 passed at `1f3fb06`. |
| M1.3 | passed | 2026-11-14 | 2026-11-14 | `web/replay/` timeline shell. |
| M1.4 | passed | 2026-11-14 | 2026-11-14 | `web/replay/runs/site04-p02-practice.json` |
| M1.5 | passed | 2026-11-14 | 2026-11-14 | Trace in that run. Separate review `docs/evidence/m3_review.md`. |
| M2.1 | passed | 2026-11-14 | 2026-11-14 | `web/replay/runs/malapert-practice.json` |
| M2.2 | passed | 2026-11-14 | 2026-11-14 | Shared playhead in `web/replay/app.js`. |
| M2.3 | passed | 2026-11-14 | 2026-11-14 | Browser load and export URL are the same run files. |
| M2.4 | passed | 2026-11-14 | 2026-11-14 | Sun-centre clear differs by 172800 s. Both-centres clear ties at 0. Unknown 0 s. |
| M2.5 | blocked | 2026-11-14 | — | Preflight recorded in `docs/evidence/m2_5_preflight.md`. Frame tie, height reference, coverage, and an independent skyline stay open. 0° package stays the demo. Sprint 2 (2026-11-15): science package `docs/evidence/s2_science_review.md`, independent 20 m DEM skyline `docs/evidence/s2/terrain_independent_skyline.json` (same-grid agreement 0.002°–0.27°; 100 m steps expose near-field terrain up to +8.5° the 1.5 km profile misses), Malapert altitude record `docs/evidence/s2_malapert_reference_altitude.md`, scope proposal SC-1 **pending Lead and Science** in `docs/evidence/s2_scope_decision.md`. Stays blocked. |
| M3.1 | passed | 2026-11-14 | 2026-11-14 | `web/replay/` plus `web/replay/README.md` |
| M3.2 | passed | 2026-11-14 | 2026-11-14T10:35:24Z | Clean Chromium profile, Wi-Fi off, playhead and both exports. `docs/evidence/m3_clean_browser.md`. Commit `1f3fb06`. |
| M3.3 | passed | 2026-11-14 | 2026-11-14 | Pitch draft `docs/evidence/m3_3_pitch.md`. Practice label kept. |
| M3.4 | blocked | 2026-11-14 | — | Re-evaluated 2026-11-15. Depends on M2.5, which is blocked. The earlier `passed_with_open_decisions` was invalid credit. The package and run IDs are handed off, but the task passes only after M2.5 closes or Lead and Science approve a recorded scope change (`scope_changes` in `agent_handoff.json`, currently proposed, not approved). |
| M4.1 | blocked | 2026-11-14 | — | 0° fallback is the demo. Frame, height, coverage, and an independent skyline stay open. |
| M5.1 | planned | 2026-11-14 | — | Re-evaluated 2026-11-15. The earlier `skipped` is no longer completion. Depends on M4.4, which is not met. Optional; +24 h comparison is not in the witnessed build. |
| M6.1 | in_progress | 2026-11-14 | — | Judging record drafted in `docs/evidence/m6_0deg_submission_package.md`. No tag. Eligibility still false. |
| Stream | passed | 2026-11-14 | 2026-11-14 | Local `run`/`stream`/`serve` against saved Horizons. Batch-stream parity. Evidence `docs/evidence/stream_local_run.md`. |
| Stream-comparison | passed | 2026-11-14 | 2026-11-14 | Two-site live pair from saved Horizons. Shared-prefix totals, uneven batches, fail/cancel. Evidence `docs/evidence/stream_comparison_live.md`. |
| Review-candidate Trek UI | superseded | 2026-11-14 | 2026-11-14 | Replaced by polar sky stage (no Moon Trek globe on demo path). |
| Review-candidate sky stage | passed | 2026-11-14 | 2026-11-14 | Edu-style dual polar maps, sun waves, stream info strip. Evidence `docs/evidence/review_candidate_sky_polar.png`. |
| Terrain diagnostic start | passed_with_open_decisions | 2026-11-14 | 2026-11-14 | `lunar_navigator.terrain` + DEM240 profiles under `web/review-candidate/terrain/`. UI draws H(A) as diagnostic. Classification still geometric 0°. M4 review open. `docs/evidence/terrain_gen.log`. |
| Review-candidate verdict + windows | passed_with_open_decisions | 2026-11-14 | 2026-11-14 | Verdict sentence, 0° primary plots with opt-in terrain diagnostic, Locations tab (A/B pins), live progress / Follow latest / Playback speed, Sun-Earth-Both window explorer. Metric cards restored, click-to-preview, state-ring glyphs, regrouped controls with Play/Pause. Sky tools (scale, path, layers, sites, decimals, step, jumps, focus lane, cursor readout) and full-fraction metrics. Terrain shapes (silhouette, outline, raw bins, above-0° tint, peaks and leaders, skyline summary chips). Browser walkthrough 66/66 and full pytest 34 passed. Open: pin orientation checked on one landmark only, so no coordinate picking or distances. Evidence `docs/evidence/review_candidate_browser.log`, `review_candidate_window_trace.md`, `review_candidate_stage_*.png`. |
| Review-candidate one-flow refinement | passed_with_open_decisions | 2026-11-15 | 2026-11-15 | Choose case → read result → select window → inspect why. Scenario bar; equal-footing Sun headline (Site04 48 h, Malapert 0 h) and joint line (0 h at either site); raw seconds, counts and `terrain_not_reviewed` behind Details. One lane picker drives chart (A/B labelled traces, dark plot, labelled 0° line, pink selected-time line), lanes, margins table (Both) and Windows rail; window click selects span and site and moves the playhead; View evidence holds the Horizons row and export; "Closest sampled point to 0°" with final-sample zero-elapsed note. Live: per-site progress, shared cutoff, partial label, pending dotted vs Unknown crosshatch. 390 px: result before chart, Windows below, sticky time dock. Screening filter (minimum clear window): practice 4 h Sun finds a Site04 window, 4 h Both finds none, both from engine intervals. Browser walkthrough 139/139, pytest 34 passed, `web/replay/` diff empty, no CDN. Evidence `review_candidate_flow_trace.md`, `review_candidate_browser.log`, `review_candidate_stage_*.png`. Open: Product 69 and terrain unchanged; no coordinate picking. |
| Sprint 1 — engine, stream, evidence | passed | 2026-11-15 | 2026-11-15 | Dependency accounting (`task_counts.py`, invalid credit removed), failure/Stop feedback, atomic JSON publish, sky-trace reconciliation, both raw digest sets kept. Revision `f534f8c-dirty`; pytest 57 passed, live trace 28/28, browser 139/139. `docs/evidence/s1/summary.txt`, `docs/evidence/s1_reconciliation.md`. |
| Sprint 2 — science scope and decision flow | passed_with_open_decisions | 2026-11-15 | 2026-11-15 | "Why this result?" (48 h, 0 h, both centres, terrain Unknown) with UTC range, mode and saved source rows; "Is there a clear window?" decision panel with minimum length, closest-to-0°, and other supported cases; second real case (practice 30 days, Malapert Sun-centre change at 2025-01-05T10:00Z traced to the raw Horizons row); QA fixture transition and Unknown checked; trace notebook; terrain curvature, analytic and 359°/0° tests; independent skyline. Revision `f534f8c-dirty` (code digest in `docs/evidence/s2/revision_before.json`): pytest 96 passed, live trace 28/28, browser 139/139, S2 flow 39/39, skyline and notebook exit 0, witnessed replay unchanged. **Open:** Lead eligibility and deliverables (L1–L5), Science approval of SC-1 and terrain items (S1–S5). `docs/evidence/s2/summary.txt`. |

## M0.4 runtime pin

| Item | Value |
|------|--------|
| Interpreter | Python **3.14.9** (`/usr/bin/python3`) |
| Wheel cache tag | `data/offline/wheels/cpython-314-linux-x86_64/` |
| Venv | `.venv/` (gitignored) |
| Imports verified | numpy 2.5.4, rasterio, pyproj, pytest |

## M0.2 observer selection (open)

| Candidate | Role | Notes |
|-----------|------|--------|
| site04-p02-practice | Fixture / smoke | Horizons saved; not promoted for submission claim |
| malapert-practice | Fixture / smoke | Same |
| Working practice pair | **Selected for the replay** | Site A `site04-p02-practice`; Site B `malapert-practice`; `2025-01-01T00:00:00Z`–`2025-01-03T00:00:00Z` @ 900 s. Labeled practice. Submission claim still open. |

## Commands (fresh evidence)

```text
python3 scripts/sync_master_reference.py          # sha_verify=OK rev 0.5
python3 scripts/compare_workbook_schedule.py      # NO Tasks tab → JSON schedule
scripts/run_m0_offline_smoke.sh
scripts/verify_offline_wheels.sh
.venv/bin/python lunar_offline_pack.py --root data check core terrain --open-dem
```

## Next

- **0° submission:** Lead confirms eligibility and the required deliverables. The witnessed demo stays commit `1f3fb06`. New Horizons runs use the hardened engine.
- **M2.5:** Science reviews terrain in parallel. Until that review passes, show terrain as Unknown. Malapert 4.86425 km is a sensitivity input.
- **Digests:** Keep both raw-response digest sets. Matching angle CSVs support the replay totals. Raw-file identity stays open.
- **Replay:** `python3 -m http.server 8765 --directory web/replay` then `http://127.0.0.1:8765/`.

## M0.5 gate (session operator, 2026-11-14T09:54:24Z)

| Field | Value |
| --- | --- |
| Verdict | passed |
| Witness | `witness=m9nx utc=2026-11-14T09:54:24Z laptop=m9nx-83dg wifi=off` |
| Backup | `/home/m9nx/Lunar-Hackathon-data-backup` (5.2G). Core check and four Horizons checks exit 0 on both copies. |
| Smoke | `./scripts/wifi_off_smoke.sh` exit 0. `WIFI_OFF_CONFIRMED` was unset. |
| Radio after | Restored at 2026-11-14T09:54:38Z. A second off window for the replay was 10:11:45Z–10:12:40Z. |

## M3 package gate

| Field | Value |
| --- | --- |
| Verdict | passed_with_open_decisions |
| Reviewer | separate reviewer [centre-ray replay review](89204d16-ed87-4a7b-99b9-d1d4bc52fafb); clean-profile pass by the session operator |
| Revision | `1f3fb06` |
| Run IDs | `site04-p02-practice-q4-centre-0deg-a24325ba50c4`, `malapert-practice-q4-centre-0deg-88b9b3cfef57` |
| Evidence | `docs/evidence/m3_review.md`, `docs/evidence/m3_clean_browser.md`, `docs/evidence/m3_3_pitch.md` |
| Unresolved | Submission eligibility, Malapert 0 km as a reviewed height, Appendix B raw-response hash, M2.5 terrain |

## Earlier M0.5 note (superseded, 2026-11-14T09:34:18Z)

| Field | Value |
| --- | --- |
| Verdict | pending |
| Reviewer | self-review |
| Revision | `87e5518aafbc0f5cfbd9dffe24bbb3b6582afcfd` (dirty tree) |
| Run ID | none |
| Evidence | `docs/evidence/m0_5_observed_2026-11-14.md` |
| Unresolved | Wi-Fi witness, backup copy, live brief, case acceptance, Appendix B raw SHA-256 |