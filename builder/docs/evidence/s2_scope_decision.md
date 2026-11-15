# Sprint 2 scope decision record (SC-1)

**Status: PENDING. Nothing here is approved.** The Lead and Science approvals below are blank on purpose. A builder run cannot supply them. The handoff keeps `SC-1` as `proposed` with `approved_by: null`, and M2.5 keeps its prior status until a human fills this page in.

## What is proposed

Release the **geometric 0° centre-ray scope** for the local candidate while the terrain review stays open.

| Item | Proposal |
| --- | --- |
| Product claim | Sun-centre, Earth-centre and Both-centres clearance against a flat 0° horizon, at the saved Horizons samples. |
| Terrain | Unknown (`terrain_not_reviewed`) everywhere. No terrain-mode total is produced or shown. |
| Not claimed | Disc visibility, received power, ground-station contact, terrain clearance. (L1: practice packs are eligible for a centre-ray 0° submission claim; see `l1_eligibility_decision.md`.) |
| Affected task | M2.5 (terrain preflight and review). It would stay open, not be marked passed. M4 would remain blocked behind it. |
| Cases in the package | Practice 48 h (witnessed replay, `1f3fb06`), practice 30 days (new, this sprint), and the labelled QA fixture. |

If SC-1 is **not** approved, the geometric result still works as it does today, but the project cannot describe the 0° scope as a chosen release scope.

## Decisions needed from Lead

| # | Decision | Evidence to look at | Answer (Lead fills in) |
| --- | --- | --- | --- |
| L1 | Are the saved January 2025 practice runs eligible to support a submission claim, or are they rehearsal only? | `m0_1_lead_handoff.md`; `l1_eligibility_decision.md` | **APPROVE** — eligible for centre-ray 0° claim on `web/replay/`, practice-30d, practice-jan03-10. QA stays false. Recorded 2026-11-15. |
| L2 | Required deliverables and format from the official Resources page. | The Resources page; `m0_1_project_tab_draft.md` | _pending_ |
| L3 | Final AI-use disclosure wording. | Starter sentence in `m0_1_project_tab_draft.md` | _pending_ |
| L4 | Which build is demonstrated: the witnessed `1f3fb06` replay, or the local candidate? | `web/replay/` (witness) vs `web/review-candidate/` | _pending_ |
| L5 | A reachable demo link or recording, if the format asks for one. | none yet | _pending_ |

## Decisions needed from Science

| # | Decision | Evidence | Answer (Science fills in) |
| --- | --- | --- | --- |
| S1 | Approve the geometric 0° scope as a release scope with terrain Unknown. | `s2_science_review.md` | _pending_ |
| S2 | Frame tie: Horizons observer frame `MEAN_ME` and the DEM's PGDA description `MOON_ME/DE421`. | `s2_science_review.md` §1 | _pending_ |
| S3 | Observer height reference for each site, including Malapert 0 km versus the DEM surface. | `s2_malapert_reference_altitude.md` | _pending_ |
| S4 | Radial coverage and range for the skyline, including the near-field step. | `s2_science_review.md` §3 | _pending_ |
| S5 | Tolerance and acceptance of the independent skyline directions. | `s2/terrain_independent_skyline.json` | _pending_ |

## Approval block

| Role | Name | Decision (approve / reject / defer) | UTC | Note |
| --- | --- | --- | --- | --- |
| Lead | (in-chat instruction) | approve L1 only | 2026-11-15 | L2–L5 and SC-1 Science still pending. See `l1_eligibility_decision.md`. | |
| Science | | | | |

To record an approval: fill in the table above, then set `scope_changes[SC-1].status` to `approved`, add `approved_by` and `approved_utc` in `builder/agent_handoff.json`, and run `builder/scripts/task_counts.py`. Until then the task counts treat M2.5 at its recorded status and count nothing from SC-1.
