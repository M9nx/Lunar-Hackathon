# Handoff to Lead

14 November 2026. The active decision is M0.1. Science may review terrain in parallel. This note does not decide eligibility.

## What Lead confirms

1. Is the Horizons practice case eligible for submission?
   - Site A `site04-p02-practice`: east longitude −156.4386°, latitude −89.7812°, reference altitude 1.738902 km.
   - Site B `malapert-practice`: east longitude −2.93°, latitude −85.99°, reference altitude 0 km.
   - Window `2025-01-01T00:00:00Z` through `2025-01-03T00:00:00Z`, step 900 s.
   - Sun `10`, Earth `399`, Moon observer `301`, quantity 4, airless, centre ray, geometric 0°.
2. Can the saved January 2025 practice runs support the submission? **Resolved 2026-11-15:** yes for centre-ray 0° — see `l1_eligibility_decision.md`.
3. Finish the AI-use disclosure. The organizing team requires it. Exact Project-tab fields and demo limits are still unread because the Resources guide page returned an error.

## What was checked

The 2026 listing confirms submission through the team’s Project tab by Sunday, November 15, 2026, 11:59 p.m. local event time. The Resources guide page returned an error, so the exact fields and demo limits are unverified. Lead’s captured Resources tab lists JPL Horizons. That screenshot is the source-check evidence and is not stored in this repository. The Project tab draft is approved for now in `m0_1_project_tab_draft.md`.

## What stays in place

Use commit `1f3fb06` for the witnessed 0° demo. Run IDs `site04-p02-practice-q4-centre-0deg-a24325ba50c4` and `malapert-practice-q4-centre-0deg-88b9b3cfef57`. Do not regenerate `web/replay/`.

If Lead approves a replacement case, run that case through the hardened engine and save it as a separate candidate. Leave `1f3fb06` available.

Until Science finishes the terrain review, show terrain as Unknown. Malapert 4.86425 km is a sensitivity input. Keep both raw-response digest sets. The matching angle CSVs support the replay totals. Raw-file identity stays open.

Keep the practice label. Eligibility flag flipped true on January packs after L1.

The 0° judging record is `m6_0deg_submission_package.md`. It has the launch command, the five-part walkthrough, the Horizons credit, and the disclosure starter. The local page is `http://127.0.0.1:8765/`. Judges cannot open that address from their own machines, so the reachable demo link is still part of this handoff.
