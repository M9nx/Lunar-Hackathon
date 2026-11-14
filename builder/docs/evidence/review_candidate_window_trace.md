# Window explorer trace: interval and sample to export (updated 2026-11-15)

Practice replay, code revision `1f3fb06`. Centre-ray against geometric 0°. Terrain clearance unknown. Not an eligible submission claim. The full reviewer walkthrough, including the 4 h filter, is in `review_candidate_flow_trace.md`.

## Interval

| Step | Where | Value |
|---|---|---|
| 1. Windows rail, Site04, Sun | `#windows` list built from `payload.intervals` (no recomputation in the browser) | Clear window `01-01 00:00Z → 01-03 00:00Z`, 48 h |
| 2. Engine interval | `web/replay/runs/site04-p02-practice.json` → `intervals[0]` | `{"lane":"sun","state":"clear","start_utc":"2025-01-01T00:00:00Z","end_utc":"2025-01-03T00:00:00Z"}` |
| 3. Total shown | same file → `elapsed_seconds.sun` | `clear 172800, blocked 0, unknown 0` (sums to the 172800 s window) |
| 4. Comparison export | `web/replay/comparison.json` → `overlap.sun_centre_clear_seconds` | `site_a 172800, site_b 0, delta_b_minus_a -172800` |

Run ID `site04-p02-practice-q4-centre-0deg-a24325ba50c4`. Clicking the window row (or its lane segment) highlights the span in the chart, lane and list, selects Site04 and moves the playhead to the start.

## Sample ("Closest sampled point to 0°")

Site04 has a clear window, so the button is not offered there. Malapert Sun has no clear window, so the rail shows "No clear window in this range." and the button. It picks the saved sample with the smallest unrounded `|margin_deg|`.

| Step | Where | Value |
|---|---|---|
| 1. Button | Windows rail → Malapert → Sun → Closest sampled point to 0° | Playhead moves to `2025-01-03T00:00:00Z` |
| 2. Saved sample | `runs/malapert-practice.json` → `samples[192]` | `margin_deg -1.603613`, `duration_seconds 0` (terminal sample) |
| 3. Source row | `sun.source_ref` | `horizons/malapert-practice/sun-d10bfb555ec3/angles.csv#row=194` |
| 4. Saved Horizons line | `sun.response_line` | `2025-Jan-03 00:00, ,i, 140.746429,    -1.603613,` |

The readout says this is the final sample and adds 0 elapsed time. View evidence shows the same row, source, observer, run ID, `code_revision` and a JSON export link.

The nearest-to-0° sample is a navigation aid only. It does not add a window, a transition, or any claim about disc visibility.

## QA fixture (labelled synthetic)

`web/review-candidate/qa-north.json`, Sun lane: Clear `2024-06-01T00:00Z → 00:15Z`, then Unknown `00:15Z → 00:45Z` (`missing_right_endpoint`, then `missing_ephemeris`, merged for display), then Blocked. `elapsed_seconds.sun` is clear 900, blocked 900, unknown 1800. The browser check confirms the list, the totals, and that each row lands on the interval start.

Browser results: `review_candidate_browser.json` and `review_candidate_browser.log`. Command: `.venv/bin/python builder/scripts/review_candidate_browser_check.py` with the local server on port 8766 running.
