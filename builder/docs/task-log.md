# Task log

Persistent record of milestone work. Status: `planned` | `in_progress` | `passed` | `passed_with_open_decisions` | `blocked` | `skipped`.

| Task ID | Status | Started (UTC) | Passed (UTC) | Evidence |
|---------|--------|---------------|--------------|----------|
| M0.1 | passed_with_open_decisions | 2026-11-14 | 2026-11-14 | `docs/decision-log.md` (live brief **open** — Lead) |
| M0.2 | in_progress | 2026-11-14 | — | Practice fixtures named; submission A/B **open** |
| M0.3 | passed | 2026-11-14 | 2026-11-14 | `docs/evidence/m0_offline_smoke.log`; local `data/` bundle |
| M0.4 | passed | 2026-11-14 | 2026-11-14 | `docs/evidence/m0_4_wheels.log`, `docs/evidence/m0_4_open_dem.log` |
| M0.5 | in_progress | 2026-11-14 | — | Partial static checks; **Wi-Fi-off pending** (QA) |
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
| Submission Site A/B | **Open** | Coordinates, height reference, UTC window — Data + Science |

## Commands (fresh evidence)

```text
python3 scripts/sync_master_reference.py          # sha_verify=OK rev 0.5
python3 scripts/compare_workbook_schedule.py      # NO Tasks tab → JSON schedule
scripts/run_m0_offline_smoke.sh
scripts/verify_offline_wheels.sh
.venv/bin/python lunar_offline_pack.py --root data check core terrain --open-dem
```

## Next

- **M0.5:** QA disables Wi-Fi on demo laptop, re-runs smoke, records backup copy.
- **M0.2:** Close observer A/B and UTC window in `docs/decision-log.md`.
- **M1:** Engine + UI only after M0.5 passes.