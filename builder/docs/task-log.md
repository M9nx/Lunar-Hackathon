# Task log

Persistent record of milestone work. Status: `planned` | `in_progress` | `passed` | `passed_with_open_decisions` | `blocked` | `skipped`.

| Task ID | Status | Started (UTC) | Passed (UTC) | Evidence |
|---------|--------|---------------|--------------|----------|
| M0.1 | passed_with_open_decisions | 2026-11-14 | 2026-11-14 | `docs/decision-log.md` (live brief **open** — Lead) |
| M0.2 | in_progress | 2026-11-14 | — | Practice pair **proposed, not accepted**. Case-fit pass; claim flag false. See decision log. |
| M0.3 | passed | 2026-11-14 | 2026-11-14 | `docs/evidence/m0_offline_smoke.log`; local `data/` bundle. Covers the four practice CSVs by presence and row count, not eligibility. |
| M0.4 | passed | 2026-11-14 | 2026-11-14 | `docs/evidence/m0_4_wheels.log`, `docs/evidence/m0_4_open_dem.log` |
| M0.5 | in_progress | 2026-11-14 | — | `docs/evidence/m0_5_observed_2026-11-14.md`. Wi-Fi was **on**; backup **not found**. Not a pass. |
| M1.* | blocked | — | — | Start after **M0.5** `passed` |

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
| Submission Site A/B | **Proposed, not accepted** | Site A `site04-p02-practice`; Site B `malapert-practice`; `2025-01-01T00:00:00Z`–`2025-01-03T00:00:00Z` @ 900 s. Data + Science must accept before a demo claim. |

## Commands (fresh evidence)

```text
python3 scripts/sync_master_reference.py          # sha_verify=OK rev 0.5
python3 scripts/compare_workbook_schedule.py      # NO Tasks tab → JSON schedule
scripts/run_m0_offline_smoke.sh
scripts/verify_offline_wheels.sh
.venv/bin/python lunar_offline_pack.py --root data check core terrain --open-dem
```

## Next

- **M0.5:** Human QA on `m9nx-83dg` disables Wi-Fi, writes `docs/evidence/wifi_off_attestation.txt`, runs `scripts/wifi_off_smoke.sh`, and notes a second copy of `data/`. Instructions are in `docs/evidence/m0_5_observed_2026-11-14.md`.
- **M0.2:** Data + Science accept or replace the proposed practice pair. Lead still owns the live brief (HTTP 500).
- **M1:** Engine + UI only after M0.5 passes. Not started this session.

## M0.5 gate (self-review, 2026-11-14T09:34:18Z)

| Field | Value |
| --- | --- |
| Verdict | pending |
| Reviewer | self-review |
| Revision | `87e5518aafbc0f5cfbd9dffe24bbb3b6582afcfd` (dirty tree) |
| Run ID | none |
| Evidence | `docs/evidence/m0_5_observed_2026-11-14.md` |
| Unresolved | Wi-Fi witness, backup copy, live brief, case acceptance, Appendix B raw SHA-256 |