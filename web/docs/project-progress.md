# Project Progress — Lunar Landing Site Navigator (local candidate)

Where the local release stands, what was verified, and what remains open before any submission claim.

## Verified local build

| Item | Value |
|------|-------|
| Repository | `Lunar-Hackathon` (private, `https://github.com/M9nx/Lunar-Hackathon`) |
| Master Reference | rev 0.5 |
| Code revision label | `f534f8c-dirty` (git HEAD `f534f8c9447b2935bb9687e6f89fa146b6d79d52`, branch `main`, dirty: true) |
| Witnessed replay revision | `1f3fb06` (`web/replay/` unchanged) |
| Python | 3.14.9 (system) / `.venv` with pytest, numpy, rasterio, pyproj |
| Data backup | `/home/m9nx/Lunar-Hackathon-data-backup` (5.2 GB, made before the Jan 3–10 package was added) |

## Tests that ran on this build

| Check | Command | Result |
|-------|---------|--------|
| Test suite | `.venv/bin/python -m pytest tests -q -p no:cacheprovider` | 96 passed (Sprint 2 record; run again after this session) |
| Offline pack core | `python3 lunar_offline_pack.py --root data check core` | OK |
| Offline pack Horizons | `python3 lunar_offline_pack.py --root data check-horizons` | 8 CSVs OK (193 or 721 rows) |
| Case fit | `python3 builder/scripts/case_fit_horizons.py` for each practice scenario | `pass=True` |
| Raw digest check | `python3 builder/scripts/horizons_digest_check.py --check` | On-disk digests match PR inputs; Appendix B mismatch remains open |
| Handoff validation | `python3 builder/scripts/validate_handoff.py` | OK |
| Notebook trace | `python3 builder/scripts/run_notebook.py --check docs/notebooks/01_trace_observation_to_interval_total.ipynb` | Exit 0 |
| Browser walkthrough | `builder/scripts/run_sprint_evidence.sh s3` (automated stand-in) | Evidence under `builder/docs/evidence/s3/` |
| Release verification | `python3 builder/scripts/verify_release_package.py` | Evidence under `builder/docs/evidence/s3/release_verify/` |

## Packaged cases

| Case | Location | Window | Step | Notes |
|------|----------|--------|------|-------|
| Witnessed practice 48 h | `web/replay/` | 2025-01-01 → 2025-01-03 | 15 min | Revision `1f3fb06`; do not regenerate. |
| Practice 30 days | `web/review-candidate/cases/practice-30d/` | 2025-01-01 → 2025-01-31 | 60 min | New this sprint; reproduces from catalog. |
| Practice Jan 3–10 | `web/review-candidate/cases/practice-jan03-10/` | 2025-01-03 → 2025-01-10 | 15 min | Packaged in this session for the landing page result. |
| QA fixture | `web/review-candidate/qa-comparison.json` | 2024-06-01 00:00 → 01:00 | 15 min | Synthetic; exercises Unknown and transitions. |

## New in this session

- `web/index.html` — landing page.
- `web/review-candidate/tour.js`, `tour.css` — the 25-step in-page guide for the navigator.
- `web/documents.html`, `web/assets/` — rendered manual and reference viewer, shared styles, vendored marked, DOMPurify, and fonts.
- `web/review-candidate/cases/practice-jan03-10/` — Jan 3–10 package.
- `web/review-candidate/app.js` and `index.html` — added Jan 3–10 case button.
- `src/lunar_navigator/live_server.py` — serves `/` from `web/index.html`; serves `.md` as `text/markdown`.
- `docs/api-reference.md`, `docs/engine-reference.md`, `docs/data-research.md`, `docs/project-progress.md`.
- `web/docs/` mirror of the markdown guides for the served UI.

## Open decisions

### Lead (M0.1 / M6)

| # | Item | Status |
|---|------|--------|
| L1 | Are the January 2025 practice runs eligible for a submission claim, or rehearsal only? | Pending |
| L2 | Required deliverables and format from the official Resources page | Pending (Resources page returned HTTP 500 on last check) |
| L3 | Final AI-use disclosure wording | Pending |
| L4 | Demonstrated build: witnessed `1f3fb06` replay or this candidate? | Pending |
| L5 | Reachable demo link or recording, if required | Pending |

### Science (M2.5 / M4)

| # | Item | Status |
|---|------|--------|
| S1 | Approve the geometric 0° scope as a release scope with terrain Unknown | Pending (SC-1 proposed, not approved) |
| S2 | Frame tie: Horizons `MEAN_ME`/DE441 vs DEM `MOON_ME`/DE421 | Open |
| S3 | Observer height reference, including Malapert 0 km vs DEM surface | Open |
| S4 | Radial coverage and range for the skyline | Open |
| S5 | Tolerance and acceptance of an independent skyline direction | Open |

### Data / QA

| Item | Status |
|------|--------|
| Raw-response SHA-256 identity against Master Reference Appendix B | Open; both digest sets kept |
| Product 90 far-field coverage and seam acceptance | Open |
| Product 69 comparison (B6) | Open; no date-matched reference available |

## What the release shows

- **Geometric 0°** is the release calculation.
- **Terrain clearance is Unknown** everywhere until M4 review passes.
- **Practice inputs** are used; Lead set `eligible_for_submission_claim` true on the January packs (L1, 2026-11-15). QA stays false.
- **No claim** is made about disc visibility, received power, radio-link availability, or ground-station contact.

## Next steps

1. Lead fills L1–L5 in `builder/docs/evidence/s2_scope_decision.md` and records the final AI disclosure.
2. Science runs the Site04 318.623526° independent skyline trace and decides on frame/height/coverage/tolerance.
3. If a new Malapert surface height is chosen, re-query Horizons and build a matching skyline.
4. Human teammate commits the verified tree, regenerates `docs/release/manifest.json`, and runs `verify_release_package.py`.
5. Run `builder/scripts/run_acceptance.py --gate M1` and update `builder/agent_handoff.json`.

## Evidence paths

- `builder/docs/evidence/s1/` — engine, stream, evidence.
- `builder/docs/evidence/s2/` — science scope, decision flow, terrain diagnostics.
- `builder/docs/evidence/s3/` — release package verification.
- `builder/agent_handoff.json` — active task, checks, blockers.
- `builder/docs/task-log.md` and `builder/docs/decision-log.md` — dated decisions.
