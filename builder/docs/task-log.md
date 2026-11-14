# Task log

Persistent record of milestone work. Status: `planned` | `in_progress` | `passed` | `passed_with_open_decisions` | `blocked` | `skipped`.

| Task ID | Status | Started (UTC) | Passed (UTC) | Evidence |
|---------|--------|---------------|--------------|----------|
| M0.1 | passed_with_open_decisions | 2026-11-14 | 2026-11-14 | Reopened as the active handoff. Challenge page HTTP 500. `docs/evidence/m0_1_lead_handoff.md`. |
| M0.2 | passed_with_open_decisions | 2026-11-14 | 2026-11-14 | Practice pair used for the replay. Eligibility, Malapert 0 km height, and Appendix B raw hash stay open. |
| M0.3 | passed | 2026-11-14 | 2026-11-14 | `docs/evidence/m0_offline_smoke.log`; local `data/` bundle. Covers the four practice CSVs by presence and row count, not eligibility. |
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
| M2.5 | blocked | 2026-11-14 | — | Preflight recorded in `docs/evidence/m2_5_preflight.md`. Frame tie, height reference, coverage, and an independent skyline stay open. 0° package stays the demo. |
| M3.1 | passed | 2026-11-14 | 2026-11-14 | `web/replay/` plus `web/replay/README.md` |
| M3.2 | passed | 2026-11-14 | 2026-11-14T10:35:24Z | Clean Chromium profile, Wi-Fi off, playhead and both exports. `docs/evidence/m3_clean_browser.md`. Commit `1f3fb06`. |
| M3.3 | passed | 2026-11-14 | 2026-11-14 | Pitch draft `docs/evidence/m3_3_pitch.md`. Practice label kept. |
| M3.4 | passed_with_open_decisions | 2026-11-14 | 2026-11-14 | Run IDs and 0° package handed off. M2.5 terrain questions stay open. |

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