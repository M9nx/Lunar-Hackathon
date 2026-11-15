# Release package — Lunar Landing Site Navigator (local candidate)

**Status: local candidate, not frozen, not submitted.** Eligibility, deliverables, the AI-use disclosure and a reachable demo link are **Lead decisions that are still pending**. Terrain stays Unknown. Nothing here claims disc visibility, power, or ground-station contact. The package has not left this machine.

## Reviewed build

<!-- BEGIN GENERATED -->
| Item | Value |
| --- | --- |
| Revision label | `f534f8c-dirty` (git HEAD `f534f8c9447b2935bb9687e6f89fa146b6d79d52`, branch `main`, dirty: true) |
| Code digest (SHA-256 over `src/ tests/ web/ builder/scripts/ Master-Reference/`) | `367c83ef1ceb9397b3691e7e41fbc421858ef371f750253573306d40ebd04ba7` |
| Witnessed replay revision | `1f3fb06` (`web/replay/` is unchanged by this release) |
| Files in manifest | 245 (docs 11, inputs 72, reference 3, replay 7, scripts 35, src 12, tests 38, web 67) |
| `docs/release/manifest.json` SHA-256 | `9bce62b934a1ab6e6612be1d3298168c37ae8ae6e858a429f9b668b4afddabe4` |
| `docs/release/MANIFEST.sha256` SHA-256 | `e4a7d695aec6d17a53bee28ed8dc7a9c5a5f1d45d79bcab127d32c4e8b71bdfd` |

Replay, export, notebook and guide checksums (full list in `MANIFEST.sha256`; check with `sha256sum -c docs/release/MANIFEST.sha256` from the repository root):

| File | SHA-256 |
| --- | --- |
| `web/index.html` | `1c1259d0f1ced14b9cf528da5256ca93e042971f2e23c5d20df60c71554a7327` |
| `web/documents.html` | `5c849af6d56455d1afb344c6c8d4d964447c91293c043bb141d17c96906a264c` |
| `web/assets/css/site.css` | `bce401fe90a168355c6026d86049d85723b17b06717b0f69569fcad8aa9627da` |
| `web/review-candidate/tour.js` | `9f2fb771ff9ccfb187f181c62a908b2d4583531f714aa61cd635c98b9de2c7f9` |
| `web/replay/comparison.json` | `0077c87f77200eca12edc003e6db2745fa0c690d4bd325cde168bb144445a028` |
| `web/replay/runs/site04-p02-practice.json` | `1eefdea5cee4e2e41da1d9319995b683d18a3f3e224fda4cf72901fee0f4a072` |
| `web/replay/runs/malapert-practice.json` | `bbcbdae2ca8987abe248d327103236905ace372c254628ed39b481678c5f17ac` |
| `web/review-candidate/cases/practice-30d/comparison.json` | `1d93773c1b6d3755cae3d14c2a959ca50c6599f6accd727482306005d136ae03` |
| `web/review-candidate/cases/practice-30d/runs/site04-p02-practice-30d.json` | `8c2240141b27c8901fb79e1bdb29f30822867a66589440800ebb24e9e815333a` |
| `web/review-candidate/cases/practice-30d/runs/malapert-practice-30d.json` | `646a440257168a808402193e69ca14baad96f5ea272112480923f7c57e9f0b34` |
| `web/review-candidate/cases/practice-jan03-10/comparison.json` | `a9ee880c3d0ccaf84f6f4ce4e1431e245036f95d2dc9b6e4667651d625e120c2` |
| `docs/notebooks/01_trace_observation_to_interval_total.ipynb` | `c837b2bfe62e012f2561d522b1937af18dc20dffe3e9e2f379d5ea5122933d55` |
| `docs/user-guide.md` | `90570cc447d5cc076ed6bfe0e886378d1d8169d7d3de6b3cd48435832d95f00f` |
| `docs/operator-manual.md` | `c5aa2624310342ff3cb402e316e4dac2913274aa23db020a42d4c389b6b91be1` |
| `docs/science-and-data-reference.md` | `25b78333ff8a99bc08a2fb6d208b7530161abf2cbe0bc6fc8194bcd3de82bb42` |
| `docs/api-reference.md` | `79560c2425a05ea7f045afd984a95bbaae38bb0f4ccb4742314c15915b746bbf` |
| `docs/engine-reference.md` | `8c895792753170eabc33366680109e6beac896606c68395e3cc4b6e9914e38ef` |
| `docs/data-research.md` | `f7a1a03657e856233edbc9b2f4de2f1bbf363f56f18907f705ce34f2bc4c823d` |
| `docs/project-progress.md` | `60e59c1cef18ffb3d73cbbb23500428b369dd2b84a65d06c657749195916d175` |
<!-- END GENERATED -->

A label ending `-dirty` means the working tree has uncommitted changes. The code digest identifies exactly which code was tested. To name a revision by commit, a human teammate commits (human author only, no AI trailer), then regenerates the manifest. Evidence recorded under an earlier digest stays tied to that digest.

## What is in the package

| Part | Where |
| --- | --- |
| Landing page | `web/index.html`, `web/landing.css` |
| Navigator (saved cases and live calculation from saved data) | `web/review-candidate/` |
| Witnessed 48 h replay, unchanged | `web/replay/` (revision 1f3fb06) |
| Engine, server, CLI | `src/lunar_navigator/` |
| Tests | `tests/` (run with `.venv/bin/python -m pytest tests -q -p no:cacheprovider`) |
| Saved Horizons inputs (not in git) | `data/horizons/` (hashes in the manifest) |
| Guides and reference | `docs/user-guide.md`, `docs/operator-manual.md`, `docs/science-and-data-reference.md`, `docs/api-reference.md`, `docs/engine-reference.md`, `docs/data-research.md`, `docs/project-progress.md` |
| Notebook tracing a row to an interval total | `docs/notebooks/01_trace_observation_to_interval_total.ipynb` |
| Demo walkthrough, teammate checklist | `docs/release/WALKTHROUGH.md`, `docs/release/TEAMMATE_CHECKLIST.md` |
| Checksums | `docs/release/manifest.json`, `docs/release/MANIFEST.sha256` |
| Evidence | `builder/docs/evidence/s1/`, `s2/`, `s3/` |

Check the files: `sha256sum -c docs/release/MANIFEST.sha256` from the repository root (needs `data/horizons` for the input lines), or `python3 builder/scripts/make_release_manifest.py --check`. Reproduce the release from the candidate: `python3 builder/scripts/verify_release_package.py` (Operator Manual §9).

## Known limitations

1. Centre-ray only: the centre of the body against a flat 0° horizon at saved samples (15 min or 1 h). Not disc, power, or contact.
2. Terrain is Unknown everywhere. The M4 review has not passed; M2.5 is blocked.
3. All inputs are practice (Site04 and Malapert, January 2025). `eligible_for_submission_claim` is `false`.
4. Malapert practice height is 0 km above the 1737.4 km sphere, about 4.85 km below the DEM surface there. The 4.86425 km capture is reported but was not re-queried.
5. The raw-file hash of the original 48 h Horizons exports differs from Master Reference Appendix B. The mismatch is open and both digest sets are kept.
6. Product 69 is context only; no comparison is made with it.
7. Saved cases are a fixed list. A new site or date needs a new saved export and a scenario record.
8. The 30-day Horizons exports exist only in `data/horizons/` on this machine and in no backup made before this sprint (Operator Manual §2).
9. Revision is `-dirty` until a human commits.

## Lead's confirmed submission requirements

**Not confirmed.** The listing says submission is through the team's Project tab by **Sunday, 15 November, 11:59 p.m. local event time**. The organizers' Resources page returned an error when last checked, so required fields and demo limits are unverified (`builder/docs/evidence/m0_1_project_tab_draft.md`). The Lead fills in:

| # | Item | Lead's answer |
| --- | --- | --- |
| L1 | Are the practice runs eligible for a submission claim, or rehearsal only? | _pending_ |
| L2 | Required deliverables and format (Resources page) | _pending_ |
| L3 | AI-use disclosure wording | _pending_ |
| L4 | Build to demonstrate: witnessed `1f3fb06` replay or this candidate | _pending_ |
| L5 | Reachable demo link or recording, if required | _pending_ |

Science decisions S1–S5 (scope approval, frame tie, observer height, radial coverage, tolerance) are also pending: `builder/docs/evidence/s2_scope_decision.md`.

## AI disclosure

Starter text only. The Lead finishes and approves it against the organizers' guide:

> Cursor agents implemented, tested, and reviewed the offline replay. The centre-ray states come from saved NASA/JPL Horizons tables. Lead finishes this disclosure against the organizer's guide before it is submitted.

This release also used Cursor agents to draft the guides, the notebook, the evidence scripts and this package. Human teammates review and approve them. Git commits carry human authors only.

## Verification record

See `builder/docs/evidence/s3/summary.txt` (sprint evidence run at the recorded digest) and `builder/docs/evidence/s3/release_verify/` (QA-style reproduction from a clone of the candidate). The teammate-from-guide check is a human step and is **pending** until `TEAMMATE_CHECKLIST.md` is filled in.
