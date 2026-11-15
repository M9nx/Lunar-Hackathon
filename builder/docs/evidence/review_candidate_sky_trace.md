> **SUPERSEDED (2026-11-15, audit reconciliation).** This trace describes a "Sky Scene" UI (`#scene-utc`, `#verdict-line`, `.site-verdict` cards, a side-view inset) that is **not in the code** at any recorded revision after `0b2a7db`; `rg` finds none of those ids in `web/review-candidate/`. Its "163 checks" claim cannot be reproduced: the committed log `review_candidate_browser.log` reports 139. The files `review_candidate_sky_*.png` show that retired UI. Do not cite this page as acceptance evidence. The current flow, rerun at a recorded revision, is `s1_reconciliation.md` and `s1_browser/review_candidate_browser.log`. The numeric examples below (13:00Z Site04 +1.66°, Malapert −2.22°; sample 147 Malapert −1.836316°) still equal the saved runs and are kept for reference only.

# Sky Scene trace: compare the sites → select a body → see why (2026-11-15)

Practice replay, code revision `1f3fb06` plus the local review candidate. Centre-ray against geometric 0°. Terrain clearance unknown. Not an eligible submission claim. Every step below ran in the headless browser (`review_candidate_browser.log`, 163 checks, 0 failed). Server `http://127.0.0.1:8766/review-candidate/`.

## Teammate check 1: which site clears the Sun centre?

| Step | Where | Value (13:00Z, 2025-01-01) |
|---|---|---|
| 1. Shared UTC | `#scene-utc` above both plots | `2025-01-01T13:00:00Z` |
| 2. One-line verdict | `#verdict-line` | "Sun centre clear at Site04, blocked at Malapert · Earth centre blocked at both sites · Both centres clear at neither site" |
| 3. Equal cards | `.site-verdict` ×2 | Same width, height and type size. Site04 Sun Clear +1.66°. Malapert Sun Blocked −2.22° |
| 4. Saved states | `web/replay/runs/*.json` → `samples[52]` | Site04 sun clear, earth blocked, both blocked. Malapert sun blocked, earth blocked, both blocked. Cards equal them |

Answer: **Site04** clears the Sun centre at that sample. Malapert does not.

## Teammate check 2: explain Malapert's blocked state with the inset

Sample 147, `2025-01-02T12:45:00Z`. Click the Malapert Sun marker, or Tab to it and press Enter.

| Panel part | Shown |
|---|---|
| Site / Body / UTC | Malapert / Sun centre / `2025-01-02T12:45:00Z` |
| Equation | −1.84° elevation − 0.00° horizon = −1.84° margin |
| Verdict | Blocked at geometric 0°, with the pill "Terrain clearance unknown" |
| Inset | Side view: strong 0° horizon, Sun below it, dimension line "margin −1.84°", state word BLOCKED |
| Sentence | The Sun centre is 1.84° below the horizon, so it is Blocked. Margin at or below 0 is Blocked. |
| View evidence (closed by default) | Exact angles (−1.836316°), the saved Horizons row (`response_line`), source, run ID, observer, export JSON |

The saved sample (`malapert-practice.json`, `samples[147].sun`) has elevation −1.836316, horizon 0, margin −1.836316, state `blocked`.

## Teammate check 3: verdict equals the saved state with the DEM overlay on and off

Twelve selections: overlay off, on, off again × (Site04, Malapert) × (Sun, Earth) at sample 147. For each, the panel verdict text, the inset state word and the site verdict card all equal the saved `state`. With the overlay on, the inset adds a note "DEM diagnostic −7.21° at this azimuth (off this scale, not drawn) · unreviewed, not used for the state." and the page still shows "Terrain clearance unknown". The DEM never changes a state.

## Layout and scale

| Check | Result |
|---|---|
| 0° ring | Solid white, 3.2 px, dark halo. Other rings and ticks 0.8–1.4 px. Terrain lines stay thinner than the ring with the DEM on |
| Scale | One linear scale in both plots. Centre labelled "centre +15°", scale note says "The centre is +15°, not zenith" |
| Markers | Compact Sun and Earth glyphs, two-decimal labels (Sun +1.66°, Earth −6.13°, Sun −2.22°, Earth −1.93°) |
| Precision near 0° | `labelDeg(0.004)` → +0.004, `labelDeg(-0.0004)` → −0.0004, `labelDeg(0)` → 0.00 |
| "0° horizon" label | Placed on the ring at the angle farthest from both bodies |
| Counts and extrema | Not on the plots. Under Details (193 of 193 samples, closest to 0°). DEM high and low appear there when the diagnostic is on |
| Why panel, desktop ≥1200 px | Docked beside the plots (sticky), covers neither plot |
| Why panel, below 1200 px | In flow under the plots, scrolled into view |
| 390 px | Both verdict cards visible, one plot at card width, Site04 / Malapert switch. Switching keeps the UTC and the sample index (147). An open panel follows the switch. No horizontal overflow |

## Evidence files

`review_candidate_browser.log` / `.json`, `review_candidate_pytest.log` (34 passed), `review_candidate_sky_why.png`, `review_candidate_sky_why_dem.png`, `review_candidate_sky_390.png`, `review_candidate_sky_390_why.png`, `review_candidate_stage_*.png`.

## Not claimed

Disc visibility, received power, radio-link availability or ground-station contact. Terrain Clear or Blocked. The DEM is unreviewed (M4 not passed) and display-only.
