# Evidence artifacts

Fresh acceptance logs for this repository (not historical edu outputs).

| File | Milestone | Description |
|------|-----------|-------------|
| `m0_offline_smoke.log` | M0.5 (partial) | `lunar_offline_pack.py check core` + `check-horizons` |
| `m0_4_wheels.log` | M0.4 | Offline venv install from `data/offline/wheels/cpython-314-linux-x86_64/` |
| `m0_4_open_dem.log` | M0.4 | `check core terrain --open-dem` with rasterio |
| `m0_5_observed_2026-11-14.md` | M0.5 (earlier) | Wi-Fi was on before the witness |
| `wifi_off_attestation.txt` | M0.5 | `witness=m9nx utc=2026-11-14T09:54:24Z laptop=m9nx-83dg wifi=off` |
| `m0_5_wifi_off.log` | M0.5 | Radio off, smoke exit 0, radio restored |
| `m0_5_backup_checksums.log` | M0.5 | Core and Horizons checks on `data/` and the backup |
| `m3_review.md` | M3 | Separate reviewer plus the earlier Cursor-browser note |
| `m3_clean_browser.md` | M3.2 | Clean Chromium profile, Wi-Fi off, commit `1f3fb06` |
| `m3_clean_browser.log` | M3.2 | Radio, playhead, and export log for that pass |
| `m3_clean_00.png`, `m3_clean_15.png` | M3.3 | Playhead screenshots at 00:00 and 00:15 |
| `m3_3_pitch.md` | M3.3 | Practice pitch draft |
| `m2_5_preflight.md` | M2.5 | Diagnostic DEM, altitude, and skyline notes. Terrain stays Unknown |
| `m0_1_lead_handoff.md` | M0.1 | Lead handoff: practice-case eligibility and required deliverables |
| `m0_1_project_tab_draft.md` | M0.1 | Project tab text approved for now. Eligibility stays false |
| `m6_0deg_submission_package.md` | M6.1 | Witnessed `1f3fb06` build, walkthrough, credits, and disclosure starter |
| `stream_local_run.md` | Engine/stream | Local on-demand run, NDJSON stream, cancel/fail checks |
| `review_candidate_trek_globe.png` | Review UI | Offline LROC globe (SVS CGI Moon Kit) + scene HUD |
| `review_candidate_sky_polar.png` | Review UI | Earlier sky polar plots (superseded: the old scale clamped near +23° and labelled the centre zenith) |
| `review_candidate_stage_desktop.png` | Review UI | Verdict, 0°-primary sky plots, Windows tab with Closest to 0° (desktop) |
| `review_candidate_stage_390.png` | Review UI | Same view at 390 px, plots stacked |
| `review_candidate_stage_terrain.png` | Review UI | 13:00 UTC with "Show terrain diagnostic" on, verdict unchanged |
| `review_candidate_stage_locations.png` | Review UI | Locations tab, B pin selected |
| `review_candidate_stage_live.png` | Review UI | Live stream, scrubbed back, Follow latest off, pending zone |
| `review_candidate_stage_preview.png` | Review UI | Preview card opened from the Malapert Sun marker |
| `review_candidate_stage_tools.png` | Review UI | Sky tools row, time tools, Full-window path on, 6-decimal metrics |
| `review_candidate_stage_terrain.png` / `_terrain_bins.png` / `_terrain_30.png` | Review UI | Terrain shapes: silhouette with peaks and leaders, raw bins, silhouette at ±30° |
| `review_candidate_stage_both.png` / `_filter.png` / `_qa.png` | Review UI | Both lane with the two centre margins; 4 h Both filter (no joint window); QA fixture with Unknown |
| `review_candidate_stage_390.png` / `_390_dock.png` / `_390_qa.png` | Review UI | 390 px: result before chart, sticky time dock, QA fixture |
| `review_candidate_browser.log` / `.json` | Review UI | 139 browser checks via `builder/scripts/review_candidate_browser_check.py` |
| `review_candidate_pytest.log` | Review UI | Full `pytest -q`: 34 passed |
| `review_candidate_flow_trace.md` | Review UI | Reviewer trace: Sun headline, 4 h joint window, state to Horizons row, QA, live, layout |
| `review_candidate_window_trace.md` | Review UI | Interval and sample to saved row and export JSON |
| `pia13523_registration.log` | Review UI | 85°S ring radius vs predicted, landmark pixels |

**Backup:** `/home/m9nx/Lunar-Hackathon-data-backup`.
