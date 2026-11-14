# 0° submission package

Prepared 2026-11-14 around the witnessed geometric replay. This is the shareable judging record. It is not a freeze tag, and it does not make the practice case eligible.

`web/replay/comparison.json` still reports `code_revision` `1f3fb06` and `eligible_for_submission_claim` false. Do not regenerate `web/replay/`.

M4 terrain review stays open. The +24-hour comparison is not in this build. Lead still closes eligibility, the reachable demo link, and the AI disclosure before anyone submits.

## Witnessed build

| Item | Value |
| --- | --- |
| Demo commit | `1f3fb06` |
| Branch tip that carries this note | `5b9ac34` on `m0.5-practice-replay` |
| Pull request | https://github.com/M9nx/Lunar-Hackathon/pull/1 |
| Package | `web/replay/` |
| Schema | `replay-package-1` / `run-result-1` |
| Definition | `horizons_q4_apparent_airless_target_centre` |
| Horizon | geometric 0° |
| Window | `2025-01-01T00:00:00Z` through `2025-01-03T00:00:00Z`, step 900 s |
| Policy | `left_sample_both_endpoints`; terminal sample adds 0 s |
| Site A | `site04-p02-practice`, −156.4386° E, −89.7812° N, 1.738902 km |
| Site A run | `site04-p02-practice-q4-centre-0deg-a24325ba50c4` |
| Site B | `malapert-practice`, −2.93° E, −85.99° N, 0 km |
| Site B run | `malapert-practice-q4-centre-0deg-88b9b3cfef57` |
| Offline witness | 2026-11-14T10:35:24Z, clean Chromium profile, Wi-Fi off. `m3_clean_browser.md` |
| Screenshots | `m3_clean_00.png` at 00:00; `m3_clean_15.png` at 00:15 |

| Lane | Site A | Site B | Delta (B − A) |
| --- | ---: | ---: | ---: |
| Sun-centre clear | 172800 s | 0 s | −172800 s |
| Earth-centre clear | 0 s | 0 s | — |
| Both centres clear | 0 s | 0 s | 0 s |
| Unknown, each lane | 0 s | 0 s | — |

## How to open it

From the repository root, serve the witnessed files. Do not pass `--revision` and do not regenerate the package.

```sh
python3 -m http.server 8765 --directory web/replay
```

Open `http://127.0.0.1:8765/`. That address is the demo on this laptop. It is not a link judges can open from their own machines. The GitHub repository is private. A reachable Project-tab demo link, or a recorded walkthrough in its place, is still open for Lead.

Backup copy of the Horizons inputs: `/home/m9nx/Lunar-Hackathon-data-backup`. The served directory does not include those raw files.

## Judging walkthrough

The page shows both sites at once. There is one shared playhead. Previous, the range control, Next, and the left and right arrow keys move both sites together. State names are written as `clear`, `blocked`, and `unknown`.

### 1. The decision

Say: we compare when the centres of the Sun and Earth are above the local horizontal at two lunar south-pole sites, over one 48-hour window.

Show the header “Sun-centre clearance and Earth-centre clearance”, the practice banner, and the two site cards. The window and step are in each run’s scenario. The page states horizon mode geometric 0°.

A judge can see the time range on the playhead, both observing points, and the comparison mode without opening the source.

### 2. The interface

Say: both sites stay on one UTC clock. Move the shared playhead. Each card names Sun-centre clearance, Earth-centre clearance, and Both centres clear.

Show Shared time, Previous, the range, Next, and the UTC line. Press Next once. The UTC line changes from `2025-01-01T00:00:00Z` to `2025-01-01T00:15:00Z` on both cards. This practice window has zero Unknown seconds, so there is no hatched Unknown interval to point at. The terrain line is the labeled unknown on the page: reason `terrain_not_reviewed`.

A judge can read the state words and see that both cards show the same timestamp.

### 3. One finding

Say: over these 48 hours, Site04’s Sun centre stayed above 0° and Malapert’s stayed below. Neither site had any time with both centres above 0° together.

Show the Comparison block: Sun-centre clear seconds 172800 and 0, delta −172800; Both centres clear seconds 0 and 0; Unknown seconds 0 and 0.

At `2025-01-01T00:00:00Z` on Site A, read the inspector:

| Lane | Azimuth ° | Elevation ° | Horizon ° | Margin ° | State |
| --- | ---: | ---: | ---: | ---: | --- |
| Sun-centre clearance | 318.623526 | 1.683925 | 0 | 1.683925 | clear |
| Earth-centre clearance | 151.799812 | −6.503228 | 0 | −6.503228 | blocked |
| Both centres clear | — | — | — | — | blocked, reason `centre_below_or_on_horizon:earth` |

Margin is elevation minus the 0° horizon. A positive margin is clear. Zero or negative is blocked. Both is blocked because Earth is blocked.

Press Next. Site A at `2025-01-01T00:15:00Z` reads Sun 318.49656° / 1.683516° clear, Earth 151.802892° / −6.497028° blocked, Both blocked for the same Earth reason.

Open Export → Site A JSON and Site B JSON. Those links are `runs/site04-p02-practice.json` and `runs/malapert-practice.json`, the files the page loaded. Each file repeats `code_revision` `1f3fb06` and the same run id shown on the card.

### 4. Inputs and validation

Say: the angles are saved NASA/JPL Horizons quantity 4, apparent airless azimuth and elevation of the target centre. Sun command `10`, Earth command `399`, Moon observer `301`. We checked one row against the response line printed under the table.

Show Site A’s Sun response line `2025-Jan-01 00:00,*, , 318.623526,     1.683925,` and source `horizons/site04-p02-practice/sun-8a039d445c7f/angles.csv#row=2`. Earth source is `horizons/site04-p02-practice/earth-167962cea6a2/angles.csv#row=3` at the next step, and `…#row=2` at 00:00.

The clean-profile witness moved this playhead and opened both exports with Wi-Fi off. Record: `m3_clean_browser.md`.

Terrain is not an input to these states. The page says geometric 0° and terrain Unknown.

### 5. Limits and next step

Say: this build supports centre-ray clearance of the Sun and Earth against a flat 0° horizon. It does not support terrain clearance, disc visibility, received power, or a ground-station contact.

Show the terrain line and the practice banner. Do not mention a +24-hour shift; that comparison is not in this build. Malapert’s 0 km altitude is the practice observer height. 4.86425 km is a sensitivity input and is not this run. Product 69 is long-term context, not a check of this window. Two raw-response digest sets remain on file; the angle tables support these totals.

A judge can see which claims this version supports: the 48-hour 0° centre-ray comparison, labeled practice until Lead records eligibility.

## Source credits

- NASA/JPL Horizons, quantity 4 apparent airless azimuth and elevation. https://ssd.jpl.nasa.gov/horizons/
- Targets and observer used in the saved tables: Sun `10`, Earth `399`, Moon `301`.
- Lead’s captured Resources tab lists JPL Horizons. That screenshot is not in this repository.
- The replay footer repeats the quantity, the body ids, and the Product 69 limit.
- Product 69 is cited only as context. It is not a source of these sample states.
- No photograph is served with this package. Do not add the south-pole context image unless it is vendored into the offline page.

## AI disclosure

Starter, not the submitted disclosure:

Cursor agents implemented, tested, and reviewed the offline replay. The centre-ray states come from saved NASA/JPL Horizons tables. Lead finishes this disclosure against the organizer’s guide before it is submitted.

Organizer requirement: https://github.com/nasa/spaceapps/discussions/1849

## Still open before submission

| Item | Owner |
| --- | --- |
| Whether the January 2025 practice runs can support the submission | Lead |
| Exact Project-tab fields and demo limits | Lead |
| A demo link judges can open, or a recording that stands in for one | Lead |
| Finish the AI disclosure | Lead |
| Terrain frame, height reference, radial coverage, and one independent skyline | Science |
| Raw-response file identity | Data + Science |
