# User Guide — Lunar Landing Site Navigator (local candidate)

This guide is for someone who has the project folder and wants to compare two lunar sites. It needs no Python knowledge beyond typing one command. The operator steps (data, checks, recovery) are in the [Operator Manual](operator-manual.md). The science behind each number is in the [Science and Data Reference](science-and-data-reference.md).

**What the tool answers.** At each saved time sample, is the *centre* of the Sun (or of Earth) above a flat 0° horizon at this lunar site, and for how long over the chosen UTC window? That is a **centre-ray** answer.

**What it does not answer.** Whether any part of the Sun's disc is visible, how much sunlight arrives, whether a ground station can reach Earth, or what local terrain does. Terrain is shown as **Unknown**. Every case here is a **practice** input and is **not** an eligible submission claim.

## Two-minute quick start

1. Open a terminal in the project folder and start the page:

   ```sh
   PYTHONPATH=src python3 -m lunar_navigator.cli --revision "$(python3 builder/scripts/record_revision.py --label)" serve --port 8766
   ```

   Leave it running. It listens on this computer only (`127.0.0.1`) and needs no internet.
2. Open `http://127.0.0.1:8766/` in Chromium or Chrome. The landing page links to the navigator, guides, and witnessed replay.
3. Click **Open the navigator** to go to `http://127.0.0.1:8766/review-candidate/`.
4. Read the **headline**. For the default case it shows Site04 at 48 h and Malapert at 0 h of Sun-centre clearance ("Site04 had more Sun-centre clearance than Malapert, by 48 h") and "Both centres clear · 0 h at either site".
5. Click **Why Malapert 0 h?** The panel gives the rule in words, the sample count (193), the sample nearest the horizon (2025-01-03T00:00Z, margin −1.603613°), and a table of the saved rows behind the number. The UTC range and mode are shown in the same *Why this result?* block.
6. Scroll to **Is there a clear window?** Choose *Sun-centre clearance* and *4 h or longer*. Site04 has one window; Malapert has none, and a button takes you to the closest sampled point.
7. Click **Practice, 30 days** or **Practice, Jan 3–10** in the case bar. Now both sites have Sun-centre windows (and, for Jan 3–10, Both-centre windows). Click a window to move the timeline to its start.

If you only want to look at saved results, you can serve the page without the engine: `python3 -m http.server 8766 --directory web`. The live-calculation controls will not work in that mode.

## Choosing sites and UTC dates

You can choose **only from saved data**: the three case buttons below, or any entry in the **saved data catalog** (next section). There is no free coordinate entry, because every result must come from a saved JPL Horizons table. Inside a catalog entry you can type your own UTC range.

| Case button | Sites | UTC window | Step | What it is |
| --- | --- | --- | --- | --- |
| Practice replay | Site04 (A), Malapert (B) | 2025-01-01T00:00Z → 2025-01-03T00:00Z (48 h) | 15 min | The witnessed practice package. |
| Practice, Jan 3–10 | Site04 (A), Malapert (B) | 2025-01-03T00:00Z → 2025-01-10T00:00Z (168 h) | 15 min | Both-centre windows: Malapert 110 h 30 min, Site04 92 h 45 min. |
| Practice, 30 days | Site04 (A), Malapert (B) | 2025-01-01T00:00Z → 2025-01-31T00:00Z (720 h) | 1 h | A second practice input where states change. |
| QA fixture | QA North, QA South | 2024-06-01T00:00Z → 01:00Z | 15 min | **Synthetic.** For checking transitions and Unknown. Not a result about the Moon. |

*Or calculate live* lists the same inputs (plus single sites and a 6 h slice). Pick one, press **Start stream**, and results arrive as they are computed; **Stop** ends the run. It recomputes from the saved Horizons files and does not contact JPL. A new site or a date outside the saved coverage needs a new saved export, which the operator adds (see the manual). The **Is there a clear window?** panel lists the *other* saved case with an **Open this case** button, so you can move to another time range without leaving the page.

All times are UTC, written like `2025-01-05T10:00:00Z`.

## Saved data catalog, your own range, and gaps

*Or calculate live* also lists **Saved catalog** entries. Each is one saved Sun and Earth pair for one observer: the site, observer longitude, latitude and height, the UTC coverage, the cadence, the number of rows, how many angles are missing, and a short SHA-256 of each saved file. Choose one and open **Run options**: **From (UTC)** and **To (UTC)** fill with the whole saved range. Type a narrower range on the saved grid (for example `2025-01-03T09:00:00Z`); an off-grid or out-of-range time is refused with the reason before anything runs.

- **One site** entries run alone. **Shared two-site window** entries are offered only where both sites have the same UTC grid, so the comparison is like for like.
- **Synthetic QA cases** are in their own group. They are Horizons-shaped text written by `tests/qa_horizons_case.py`. They are not JPL output and not a result about the Moon.
- **Horizon** in Run options is the 0° baseline or **Terrain**. Terrain stays Unknown until a reviewed skyline exists for that observer. Each sample keeps its saved elevation, has no horizon and no margin, and says why (`terrain_not_reviewed`, `terrain_no_skyline_for_observer`, `terrain_review_incomplete` or `terrain_gap_in_azimuth_bracket`). The 0° baseline is never substituted.

**When Horizons has no angle for a row** (`n.a.`), the row is kept, not dropped. The angles are empty (`null`, never `0`). With the left-sample, both-endpoints rule one missing angle at 00:30 on a 15-minute grid makes that body **Unknown from 00:15 to 00:45** (30 minutes): the span that ends at 00:30 and the span that starts at 00:30. The timeline hatches it, the window list gives the duration and both reasons (`missing_right_endpoint`, `missing_ephemeris`), the chart breaks that body's trace instead of drawing through a zero, and the export carries the same intervals. Unknown is counted separately for Sun, Earth and Both (see **Details**). A confirmed blocker still makes **Both** blocked when the other centre is Unknown.

**Pending is not Unknown.** While a run is streaming, the chart draws results through the shared cutoff and dots the rest as Pending.

The real data have no `n.a.` rows. The gap behaviour is exercised by the synthetic QA case (QA Gap North, Sun missing at 2024-06-01T00:30Z).

## Reading the sky and the windows

* **Sky plots** (A and B side by side). The dashed ring is the 0° horizon. Both plots use one scale: the centre is +15°, the edge −15°, so the centre is **not** the zenith. Yellow is the Sun's centre, blue is Earth's centre. A solid ring means clear, dashed means blocked, dotted means unknown, so state is not colour-only.
* **Verdict sentence.** It describes the *selected* time only. The whole-window totals above are a different measure.
* **Timeline.** *Show* Sun, Earth or Both. A is the solid line, B is dashed, and the dotted line is 0°. Drag the pink playhead, or use Previous, Next, Play, and the arrow keys. *Step* sets how far each press moves.
* **Windows tab.** Each row is a stretch where the state does not change, taken from the engine's intervals. Click one to select it and move the playhead to its start. *Unknown spans* are listed separately.
* **Minimum clear window.** Hides clear windows shorter than your minimum. Totals do not change.
* **Closest sampled point to 0°.** For a lane with no clear window, jumps to the saved sample with the smallest margin. It adds no window and makes no claim.
* **Locations tab.** A map of the two sites. It is orientation only.

### The three lanes

| Lane | Meaning |
| --- | --- |
| Sun-centre clearance | The Sun's centre is above the 0° horizon. |
| Earth-centre clearance | Earth's centre is above the 0° horizon. |
| Both centres clear | Both are above 0° in the same sample. If either is blocked it is blocked; if neither is blocked and either is unknown it is unknown. |

A margin of **0° or less is blocked**, including exact contact. A centre just below the line can still leave part of the disc above it. That does not change the centre-ray state, and this tool does not claim anything about the disc.

## Interpreting "48 h", "0 h" and "Unknown"

* **48 h** means: the centre was above 0° at *every* saved sample in a 48-hour window. There are 193 samples at 15 min. Each sample counts for its own 15 minutes and the last sample adds 0 s, so 192 × 15 min = 48 h.
* **0 h** means: no sample was clear. It is a real zero, not missing data. The panel shows the sample closest to the horizon, so you can see how far below it was (Malapert: −1.6° at the nearest sample).
* **Unknown** means a saved angle was missing for that body and time, so the tool will not guess. Unknown time is shown separately and never counted as clear or blocked. In the practice cases it is 0 h. The QA fixture has some, so you can see it.
* **Terrain Unknown** is a different thing. No reviewed skyline exists yet, so the tool does not say anything about terrain. Click **Why terrain Unknown?** for the details. It is not the same as the geometric Unknown duration.
* **Pending** appears only during a live run: samples not calculated yet. Pending is not Unknown.

## "Why this result?"

Under the headline, the four question buttons open the answer in place: the UTC range and mode, the rule in words, the counts, and a table of saved rows. A row shows the UTC time, the Horizons line, elevation, horizon, margin and state. If a lane changes state, you see the last sample before the change and the first after it. **Show this sample in the timeline** moves the playhead there. To check by hand, compare that Horizons line with `data/horizons/<site>/<body>/response.json`.

## Exporting

* **Saved cases.** *View evidence* (in the *Why this state?* panel) shows the exact row, source, observer, run ID and revision, with links to each site's JSON (`runs/*.json`). Those are the exports.
* **Live runs.** When a run completes, **Download complete export** appears. A stopped or failed run shows *No export: the run did not complete* and its partial numbers are labelled as partial.
* Times are ISO 8601 UTC with `Z`. Azimuth is clockwise from true north, 0 to under 360°. An unavailable number is `null`; `0` is a real angle.

## Troubleshooting

| What you see | What to do |
| --- | --- |
| "The saved replay did not load" | The page must be served from the `web` folder (see the quick start). Opening `index.html` as a file does not work. |
| The page does not open | Check the terminal for an error. If the port is busy, use `--port 8767` and the matching URL. |
| **Start stream** does nothing or fails at once | You are on the file-only server, or the Horizons files are missing. Use the full `serve` command. `python3 lunar_offline_pack.py check-horizons` lists missing files. |
| Stop says *Stopping…* | The engine is finishing its current batch. It becomes *Stopped* with a final cutoff in a moment. Partial totals cover only the shared samples up to that cutoff. |
| *Failed* with a partial result | The numbers are real for the samples shown and marked partial. Press **Start stream** again for a full run. |
| No export link | Exports exist only for a completed run or a saved case. |
| Numbers look different from a live run | They should not. Start the same case live and compare the totals (the Details block). A difference is a bug; tell the operator. |
| Text or plots look cramped on a phone | The layout works at 390 px: the result comes first, Windows stack below the timeline, and the time controls stay at the bottom. |

## Known limits

Centre-ray only. Terrain Unknown. Practice inputs. Three saved cases. Raw-file identity of the original 48 h exports against the reference document is an open item. See the [Science and Data Reference](science-and-data-reference.md) and `docs/release/RELEASE.md`.
