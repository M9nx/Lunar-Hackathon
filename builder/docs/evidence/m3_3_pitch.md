# M3.3 pitch draft

Practice replay. Not a submission claim. Terrain stays out of the demo while Science reviews M2.5.

## Problem

A planner comparing two lunar south-pole sites needs one shared window that shows whether the Sun centre and the Earth centre are above the local horizontal. The comparison does not establish solar power or a radio link.

## One observed difference

Over the same 48-hour practice window, Site04’s Sun centre stayed above the 0° reference at every sample. At Malapert, it stayed below. Both sites had zero time with the Sun and Earth centres above the reference together. Move the shared playhead to trace a result from the displayed angles back to JPL Horizons.

| | Site A `site04-p02-practice` | Site B `malapert-practice` |
| --- | --- | --- |
| Run ID | `site04-p02-practice-q4-centre-0deg-a24325ba50c4` | `malapert-practice-q4-centre-0deg-88b9b3cfef57` |
| Sun-centre clear | 172800 s | 0 s |
| Earth-centre clear | 0 s | 0 s |
| Both centres clear | 0 s | 0 s |
| Unknown, each lane | 0 s | 0 s |

Window `2025-01-01T00:00:00Z` through `2025-01-03T00:00:00Z`, step 900 s. At `2025-01-01T00:00:00Z`, Site A shows Sun azimuth 318.623526°, elevation +1.683925°, clear, and Earth azimuth 151.799812°, elevation −6.503228°, blocked.

## Sources

- JPL Horizons quantity 4, apparent airless azimuth and elevation of the target centre.
- Sun command `10`, Earth command `399`, lunar observer `coord@301`.
- Saved practice exports under `data/horizons/site04-p02-practice/` and `data/horizons/malapert-practice/`.
- Geometric horizon 0°. The replay reads the versioned JSON in `web/replay/`.

## Limits

- Lead still owns submission eligibility. The Resources tab and the required deliverables were not verified. Keep the practice label.
- The 2026 listing gives Sunday, November 15 at 11:59 p.m. local event time as the submission deadline. That deadline is recorded as reported.
- Malapert’s reference altitude is 0 km and is not a reviewed surface height.
- Centre-ray clearance is not disc visibility, received power, or a ground-station contact.
- Appendix B raw-response digests still differ from the on-disk `response.json` hashes. Both records stay.
- Product 69 remains long-term context. Its simulation start and end stay unresolved.

## Screenshots

Clean-profile offline pass at 2026-11-14T10:34:43Z, commit `1f3fb06`. `m3_clean_00.png` is the shared playhead at `2025-01-01T00:00:00Z`. `m3_clean_15.png` is the next step, `2025-01-01T00:15:00Z`. Record: `m3_clean_browser.md`.
