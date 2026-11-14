# Local review candidate

A judge-facing comparison screen for the witnessed geometric replay, plus a local on-demand calculation path. It does not replace `web/replay/`.

NASA chrome (banner, brand header, red accents, stage pipe, starfield) adapted from the educational console at `~/Documents/Learning/lunar-landing-site-navigator`. That repo stays read-only history.

The page follows one flow: **choose the case → read the result → select a window → inspect why.**

1. **Choose the case.** Practice replay or QA fixture (or a live run) in the control bar. Run options (playback speed, stage pipe, failure test) open from one button.
2. **Read the result.** A compact scenario bar (sites, UTC range, sample step, Geometric 0°) and a Sun-centre headline with both sites at equal size (practice: Site04 48 h, Malapert 0 h), then "Both centres clear · 0 h at either site". Practice and Terrain clearance unknown stay visible. Raw seconds, sample counts, Unknown durations and `terrain_not_reviewed` are under Details. Zero is "0 h"; "min" appears when minutes are needed.
3. **Select a window.** Sun / Earth / Both sits above the timeline and drives the chart, the lanes, the Windows rail and the readout together. Sun and Earth draw an A (solid) and a B (dashed) trace with direct labels on a dark plot with a labelled 0° line; the selected time is a separate pink line with a time pill. Both shows the joint lanes and the two individual centre margins at the selected time. Clicking a window (list row or lane segment) highlights its span, selects its site and moves the shared playhead to its start. A site with no clear window says "No clear window in this range." and, in Sun or Earth, offers "Closest sampled point to 0°" (if that is the final sample, it says the sample adds 0 elapsed time). **Minimum clear window** (15 min to 8 h) filters the saved clear windows and lists the qualifying ones per site; totals stay visible. Practice: 4 h Sun finds a Site04 window; 4 h Both finds none. Both come from engine intervals.
4. **Inspect why.** The readout beside the playhead gives the selected UTC, each site's state and signed margin. **View evidence** opens the exact Horizons row, source, observer, run ID and export JSON. Below, the verdict sentence and the two sky plots show the same sample.

During a live run each site shows its progress and the latest shared resolved UTC; partial totals carry that cutoff. Pending (not calculated yet) is dotted; scientific Unknown is crosshatched. At 390 px both headline numbers and the joint result come before the chart, Windows stack below the timeline, and the time controls stay in a sticky dock.

The sky stage answers "what is clear at this time": a plain-language verdict for the selected UTC, then two side-by-side polar sky plots with one shared legend. Both plots use one linear scale (centre +15°, dashed 0° ring, edge −15°; the centre is not zenith). The 0° ring is what classifies. The DEM profile (`terrain/*-dem240-horizon-diagnostic.json`, LDEM 240 m, not M4-reviewed) sits behind "Show terrain diagnostic" as a thin line, with hatching where there is no DEM data. It never changes a state; terrain stays Unknown.

Whole-window totals are a separate measure from the selected-time verdict. The rail beside the chart has two tabs. **Windows** is built from engine intervals: totals per site, clickable clear windows and Unknown spans, the minimum-duration filter, and "Closest sampled point to 0°" for a Sun or Earth lane with no clear window (the saved sample with the smallest unrounded margin). **Locations** holds the PIA13523 south-pole map (`media/pia13523_clear.jpg`) with A (circle) and B (diamond) pins; pin selection highlights that site's sky plot, timeline lane, and evidence. Sun and Earth keep yellow and blue. Pin scale matches the map's 85°S graticule ring to 1 px; orientation was checked on one landmark (Amundsen). There is no coordinate picking or distance measurement yet.

Live runs show per-site progress, "Results through <latest shared UTC>", and a Follow latest toggle that turns off when you scrub, step, or use a jump. Pending samples are not Unknown. "Playback speed" only delays how fast batches are shown; batch size and pause sent to the server are fixed, so results do not change with it. Classification stays centre-ray vs 0°. No CDN at runtime.

Controls follow one flow: 1 Data (Practice replay / QA fixture), 2 Live run (scenario, Start stream, Stop; Start is disabled while a run is active and Stop only works then), 3 Playback speed. The stage has Previous, Play/Pause, Next and a playhead (`←` `→` step, `Space` play, `Esc` closes the preview). Every saved metric (azimuth, elevation, horizon, margin, DEM diagnostic, Both reason) shows under each plot, also while streaming, next to a per-plot stream meter. Clicking a Sun or Earth marker or a metric card opens a preview card (follows the playhead; margin chart; Open evidence). Clicking a window or lane segment selects it instead (see step 3). Sun and Earth glyphs carry a state ring (solid clear, dashed blocked, dotted unknown), so state is not colour-only.

Sky tools (one row above the plots, all client-side display settings that never change engine results): **Scale** ±5° / ±15° / ±30° / Full sky (only Full sky puts zenith at the centre; the scale note and centre label update), **Path** (Sun and Earth track across ±6 h or the full window, with dots at 00/06/12/18 UTC), **Layers** (grid, shading, labels, plus the terrain diagnostic), **Sites** (both or selected only), **Decimals** (2 / 3 / 6, default 6 so saved fractions such as 1.661532° show in full; the headline verdict stays at 2), and Reset view. Time tools sit with the playhead: Start, previous or next change of the focus lane, End (Latest while streaming), a Step size (1 sample, 1 h, 6 h, 1 day) that Previous, Next, arrow keys and Play all use. The Sun / Earth / Both picker sits above the timeline. Hovering a plot shows the azimuth and elevation under the cursor, plus the DEM value when the diagnostic is on.

Terrain shapes (only with "Show terrain diagnostic" on; display only, never a state): **Silhouette** (default) fills the ground outside the DEM skyline and draws a smooth outline; **Outline** draws the smooth outline only; **Raw bins** joins the saved DEM bins with straight lines and one dot per bin, so nothing is interpolated. The skyline is sand where it lies below the 0° ring and rust where it rises above it (yellow and blue stay reserved for Sun and Earth). **Peaks & leaders** marks the highest and lowest saved bin, and draws a dotted leader from the Sun and Earth markers to the skyline at their azimuth. Hatched wedges stay for azimuths with no DEM data, and the skyline is never bridged across them. A chip row under each plot gives the high and low bins, the share of known azimuths above 0°, the azimuth span with no DEM data, and the bin size and range. The smooth outline is a spline through the bins and is a visual aid; the Raw bins view and the numbers show the saved values.

Browser walkthrough: `builder/scripts/review_candidate_browser_check.py` (needs chromedriver, chromium, and the local server running).

## Replay only

Serve the `web` directory so this page and the saved runs share one origin:

```sh
python3 -m http.server 8766 --directory web
```

Open `http://127.0.0.1:8766/review-candidate/`.

## Local calculation and streaming

Acquisition stays a separate step (`lunar_offline_pack.py horizons ...`). This path only classifies saved Horizons files.

```sh
PYTHONPATH=src python3 -m lunar_navigator.cli --revision test serve --port 8766
```

Open `http://127.0.0.1:8766/review-candidate/`. Use Start and Cancel. The page posts to `/api/runs` and reads NDJSON from `/api/runs/<run_id>/events`.

Batch and stream from the terminal:

```sh
PYTHONPATH=src python3 -m lunar_navigator.cli --revision test run \
  --scenario tests/fixtures/site04_p02_practice_scenario.json \
  --out /tmp/site04-batch.json

PYTHONPATH=src python3 -m lunar_navigator.cli --revision test stream \
  --scenario tests/fixtures/site04_p02_practice_6h_scenario.json \
  --batch-size 2
```

The practice view reads `../replay/comparison.json` and the two run files. The QA fixture button loads synthetic transitions in this directory. Terrain stays Unknown. The DEM profile is drawn only as an opt-in diagnostic.

The witnessed package remains `code_revision` `1f3fb06` with `eligible_for_submission_claim` false.
