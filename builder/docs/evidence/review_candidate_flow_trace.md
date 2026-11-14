# Review flow trace: choose the case → read the result → select a window → inspect why (2026-11-15)

Practice replay, code revision `1f3fb06`. Centre-ray against geometric 0°. Terrain clearance unknown. Not an eligible submission claim. Every step below was run in the headless browser (`review_candidate_browser.log`, 139 checks).

## Reviewer question 1: which site has more Sun-centre clearance?

| Step | Where | Value |
|---|---|---|
| 1. First screen | `#answers` | Sun-centre clearance: **Site04 48 h**, **Malapert 0 h** (equal-size cards). Lead line: "Site04 had more Sun-centre clearance than Malapert, by 48 h." |
| 2. Saved totals | `web/replay/comparison.json` → `overlap.sun_centre_clear_seconds` | `site_a 172800, site_b 0` |
| 3. Details disclosure | `#answers-details` | Raw seconds (172800 s, 0 s), sample counts, Unknown durations, `terrain_not_reviewed` |

## Reviewer question 2: is there a 4 h joint window?

| Step | Where | Value |
|---|---|---|
| 1. Joint line | `#answers .result-joint` | "Both centres clear · 0 h at either site" |
| 2. Filter | Show **Both**, Minimum clear window **4 h or longer** | Summary "Site04 none · Malapert none"; no window rows |
| 3. Engine | `runs/*.json` → `intervals` lane `both` | Site04 and Malapert both have one Blocked interval, no Clear interval (`elapsed_seconds.both.clear` 0) |
| 4. Contrast | Show **Sun**, **4 h or longer** | "Site04 1 window · Malapert none". The Site04 window is the 48 h interval `2025-01-01T00:00Z → 2025-01-03T00:00Z` |

The filter reads the same merged engine intervals as the list, lanes and totals. It hides rows only. Full-window totals, the headline numbers and the joint line do not change.

## Reviewer question 3: trace one selected state to its Horizons row

Selected UTC `2025-01-01T13:00:00Z`, Show **Sun**.

| Step | Where | Value |
|---|---|---|
| 1. Readout | `#readout` | A Site04 Clear +1.661532°. B Malapert Blocked −2.216453° |
| 2. View evidence | `#preview` (kind evidence), Site04 | Horizons row `2025-Jan-01 13:00,*, , 312.021592,     1.661532,` |
| 3. Saved sample | `runs/site04-p02-practice.json` → `samples[52].sun` | `margin_deg 1.661532`, `state clear`, `source_ref horizons/site04-p02-practice/sun-8a039d445c7f/angles.csv#row=54` |
| 4. Run | evidence card | Run ID `site04-p02-practice-q4-centre-0deg-a24325ba50c4`, `code_revision 1f3fb06`, JSON export link |

Malapert at the same time: `2025-Jan-01 13:00, , , 158.508524,    -2.216453,`, `source_ref horizons/malapert-practice/sun-d10bfb555ec3/angles.csv#row=54`, run ID `malapert-practice-q4-centre-0deg-88b9b3cfef57`.

## Window with no clear time, and the final sample

Malapert, Sun lane: "No clear window in this range." and **Closest sampled point to 0°**.

| Step | Where | Value |
|---|---|---|
| 1. Button | Windows rail → Malapert | Playhead moves to `2025-01-03T00:00:00Z` (index 192 of 192) |
| 2. Notice | readout | "...margin −1.603613°. This is the final sample, so it adds 0 elapsed time." |
| 3. Saved sample | `runs/malapert-practice.json` → `samples[192].sun` | `margin_deg -1.603613`, `duration_seconds 0` |
| 4. Horizons row | evidence | `2025-Jan-03 00:00, ,i, 140.746429,    -1.603613,` at `horizons/malapert-practice/sun-d10bfb555ec3/angles.csv#row=194` |

The closest point is a navigation aid. It adds no window and says nothing about disc visibility.

## QA fixture (synthetic)

`qa-north.json` / `qa-south.json`, labelled "QA fixture · synthetic". The Sun lane gives Clear 15 min, one merged Unknown span (`missing_right_endpoint`, then `missing_ephemeris`), then Blocked. Checks: clicking the clear window moves the playhead to `2024-06-01T00:00:00Z` from sample 3; clicking Unknown lands on `00:15Z`; the readout says "Unknown, not a clearance: missing_right_endpoint" and, at `00:30Z`, "no saved margin". The 15 min filter keeps one window per site; the 1 h filter shows "No clear window of 1 h or longer." and "Longest clear window: 15 min" and dims the clear segments. Both lane order from the engine: clear, blocked, unknown, blocked.

## Live

Per-site progress with "pending, not Unknown", "Results through <latest shared UTC>", partial headline labelled "Partial totals through <that UTC>", pending zone dotted and Unknown crosshatched, playhead `max` equal to the shared resolved sample count, scrubbing turns Follow latest off. Fast and slow playback give byte-identical engine results.

## Layout

Desktop (1440 px): chart 850 px or wider, Windows rail under 400 px. 390 px: scenario bar, both headline numbers on one row, joint line, then lane picker, readout, chart, lanes, Windows; the time dock is sticky at the bottom with a one-line UTC / state / margin readout. No horizontal overflow at either width. Screenshots: `review_candidate_stage_desktop.png`, `_both.png`, `_filter.png`, `_qa.png`, `_390.png`, `_390_dock.png`, `_390_qa.png`.

`git status --short web/replay` and `git diff --stat -- web/replay` are empty.
