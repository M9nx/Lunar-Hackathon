# Decision log

Record amendments with date, owner, previous/new decision, evidence, and milestone impact (Master Reference §11).

## Repository layout (2026-11-14)

- **`builder/`** — agent worker (handoff, harness scripts, skills, task/decision logs). Not submission product code.
- **Repo root** — `src/`, `web/`, `tests/`, `Master-Reference/`, `data/`.

## M0 closure — evidence still needed (QA / Lead / Data)

| Item | Owner | Status |
|------|-------|--------|
| **Selected case** (Site A observers, UTC window, or approved one-site/two-window fallback) | Data + Science | **Open** |
| **Kickoff disposition** (brief, eligibility, submission format, AI disclosure) | Lead | **Open** (challenge page unverified 2026-11-14) |
| **Wi-Fi-off witness** | QA | **Pending** → `builder/docs/evidence/wifi_off_attestation.txt` |
| **Backup data copy** on demo laptop | QA / Data | **Pending** |
| M0.3 vs M0.2 alignment | Lead if bundle precedes final case | Practice OK; submission case-fit **not** done |

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
| Submission format and required outputs | **Open** | Lead | Challenge page fetch returned HTTP 500 (2026-11-14). Confirm live wording, Resources tab, and local organizer instructions at kickoff. |
| Actual submission cutoff | **Open** | Lead | Use workbook submit H34 until organizers state otherwise. |
| Eligible NASA data sources | **Proposed** | Data | Global Awards: ≥1 NASA data source from challenge Resources list (Master Reference §2). Enumerate chosen sources when case is selected. |
| Permitted tools / AI use | **Proposed** | Lead | Follow [organizer guidance](https://github.com/nasa/spaceapps/discussions/1827) and [AI disclosure](https://github.com/nasa/spaceapps/discussions/1849); document tools in freeze package (M6). |
| Result format (UTC, Unknown states) | **Confirmed (design)** | Lead + QA | Versioned run JSON per §5; states `clear` / `blocked` / `unknown`; ISO 8601 UTC with `Z`. |
| Practice Horizons for demo claim | **Confirmed (practice only)** | Data | Site04-P02 and Malapert practice exports are smoke/fixture inputs until eligibility + case-fit pass (§12). |

### M0.2 — Observer selection (in progress)

| Item | Status | Notes |
|------|--------|--------|
| Practice Site04-P02 | Recorded | `data/horizons/site04-p02-practice/` — 193-row Sun/Earth CSVs; **practice only** |
| Practice Malapert | Recorded | `data/horizons/malapert-practice/` — **practice only** |
| Submission Site A | **Open** | Data + Science |
| Submission Site B | **Open** | Data + Science; two-window one-site fallback per §3 |
| UTC window & cadence | **Open** | Default proposal 48 h @ 15 min in reference examples; confirm at kickoff |
| Observer height reference | **Open** | Horizons `SITE_COORD` km; separate surface vs reference height for terrain (edu: *historical* frame notes) |

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

## Workbook vs JSON schedule (2026-11-14)

- **Workbook sheets:** `Timeline`, `Milestone decisions` (high-level M0–M6 phases).
- **JSON snapshot:** 32 executable tasks (`M0.1` … `M6.5`, `Rest`).
- **Agent routing:** Use JSON unless Lead replaces snapshot and updates this log.

## Educational archive (read-only)

Path: `~/Documents/Learning/lunar-landing-site-navigator`.  
Lessons carried forward: MOON_ME/DE421 frame ties, height reference vs surface, NoData/radial gaps, near-field-only 5 m DEM horizon, offline replay without CDN (`docs/BENCHMARK_PLAN.md`, `FRAME_GEOMETRY_VALIDATION.md` — **historical**). Fresh evidence only from this repository.