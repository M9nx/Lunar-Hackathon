# About this solution — judge’s lens

Short, candid read for NASA Space Apps 2026 reviewers. This team project is **not** an official NASA product. Claims below match the **geometric 0° centre-ray** demo unless stated otherwise. **Terrain clearance is not demonstrated** (M4 review not passed; engine returns `unknown` / `terrain_not_reviewed` in terrain mode).

Official challenge (confirm live wording): [Lunar Landing Site Navigator](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/).

---

## 1. What real problem are we solving, and for whom?

**Verdict: Clear for a narrow slice; oversold if read as comms or power planning.**

**Reason.** The tool helps compare **when the centre of the Sun and of Earth** is above a **flat local horizon** at **lunar south-pole-class sites**, on a shared UTC timeline—useful for **thinking about illumination and direct Earth geometry**, not for link budgets or surface lighting models. The audience is **hackathon judges, educators, and planners** who want an inspectable, offline replay—not operators replacing STK or Horizons alone.

**Evidence**

- Problem framing on the landing page and guide: [Open navigator with tour](../web/review-candidate/?tour=1) · [Operator manual — what the app does](operator-manual.md)
- Claim boundaries (centre-ray, not disc/contact/power): [Science and data reference §1](science-and-data-reference.md#1-claim-scope)

---

## 2. What is genuinely creative or different compared with existing tools?

**Verdict: Moderate differentiation—offline traceability and honesty about limits, not a new ephemeris.**

**Reason.** JPL Horizons already supplies angles; the contribution is **pairing two sites on one playhead**, **classifying intervals with explicit Unknown**, **versioned JSON exports**, and a **Wi‑Fi‑off replay path** so judges can follow one sample to a saved Horizons row. Terrain is **shown as unavailable** rather than implied from an unreviewed DEM. Diagnostic skyline plots are display-only and do not drive classification until M4.

**Evidence**

- Two-site comparison UX and exports: [User guide path via tour](../web/review-candidate/?tour=1) · witnessed [comparison.json](../web/replay/comparison.json)
- Engine rules (Both lane, terminal sample, unrounded margin): [Engine reference](engine-reference.md)
- Terrain gate: [Science and data reference §1](science-and-data-reference.md#1-claim-scope) · [Project progress — Science M4](project-progress.md#science-m25--m4)

---

## 3. Which challenge requirements does the current demo address, and which are still open?

**Verdict: Core “compare south-pole sites over time” is addressable at 0°; several Global Awards / submission items are open.**

| Theme (paraphrase brief) | Status | Notes |
| --- | --- | --- |
| Compare sites and dates near the lunar south pole | **Addressed** (0° mode) | Site04 and Malapert practice cases; Jan 3–10 package on landing page |
| Sun / Earth relative to local horizon for planning intuition | **Addressed** (centre-ray) | Not disc-weighted illumination |
| Accessible comparison for non-experts | **Partially addressed** | 25-step in-page tour; labels for practice inputs |
| NASA data cited for eligibility | **Partial** | Horizons Q4 exports on disk; formal `asset_id` / credits in release manifest—**Lead sign-off pending** |
| Terrain / realistic horizon | **Open** | Selectable in UI/API but **M4 not passed**; results **Unknown** |
| Submission eligibility, deliverables, demo URL, AI disclosure | **Open** | Recorded as pending Lead decisions |

**Evidence**

- Packaged cases and open Lead items: [Project progress](project-progress.md) · [Release package status](release/RELEASE.md)
- Handoff: `practice_case_eligible_for_submission` **pending** — `builder/agent_handoff.json` (Unverified without opening file; mirrored in [Project progress](project-progress.md))
- Challenge scope skill (internal): Master Reference §3 / §10 — [Data and research — challenge fit](data-research.md)

---

## 4. How reliable are the data and calculations for the claims we make?

**Verdict: Strong for traced 0° practice runs with tests; not closed for production or terrain claims.**

**Reason.** Classification is **reproducible from saved Horizons CSV/JSON** with SHA-checked pack checks, pytest coverage on the engine, and an independent notebook trace. Practice exports pass case-fit scripts. **Caveats:** January 2025 inputs are **practice** and Lead-approved for a centre-ray 0° claim (`eligible_for_submission_claim: true` on those packs); **Appendix B vs on-disk `response.json` hash mismatch remains open**; Malapert observer height is a practice value; **terrain and Product 69 comparisons are not accepted**.

**Evidence**

- Provenance and method: [Science and data reference §2–3](science-and-data-reference.md#2-data-provenance-jpl-horizons)
- Worked Site04 sample: [Engine reference — worked sample](engine-reference.md#worked-sample-site04-2025-01-01t000000z)
- Witnessed 48 h runs (revision `1f3fb06`, do not regenerate): [site04 run](../web/replay/runs/site04-p02-practice.json) · [malapert run](../web/replay/runs/malapert-practice.json)
- Verification log (may lag current HEAD): [Project progress — tests](project-progress.md#tests-that-ran-on-this-build) · notebook `docs/notebooks/01_trace_observation_to_interval_total.ipynb`
- Open digest issue: [Science and data reference — raw-file identity](science-and-data-reference.md#raw-file-identity-open)

---

## 5. What can we demonstrate today, and what still needs work?

**Verdict: A coherent offline 0° demo; terrain and submission story incomplete.**

**Demonstrate today**

- Landing summary (Jan 3–10 practice window): [Overview](../web/index.html)
- Live navigator (catalog, stream, two-site compare, lane totals): [Navigator](../web/review-candidate/)
- Witnessed 48 h replay (frozen JSON): [Replay](../web/replay/)
- Local API + streamed NDJSON: [API reference](api-reference.md)
- Offline docs (manual, science, engine): [Documents viewer](../web/documents.html)
- Wi‑Fi‑off smoke recorded: `docs/evidence/m0_5_wifi_off.log` · `docs/evidence/wifi_off_attestation.txt` (**Unverified** unless file checked on judge machine)

**Still needs work**

- **M4 terrain review** (frame, height reference, radial skyline, independent direction check)—terrain mode stays Unknown
- **Lead decisions** on submission eligibility, required deliverables, demo link/recording, AI disclosure
- **Science closure** on SC-1 (0° scope sign-off), Malapert height reference, Horizons–DEM frame tie
- Re-run **release verify** after latest digest (handoff notes manifest verify stale vs current tree)

**Evidence**

- [Project progress — what the release shows](project-progress.md) · [Release WALKTHROUGH](release/WALKTHROUGH.md)
- Terrain status: [Project progress §Science](project-progress.md#science-m25--m4) · `builder/docs/evidence/m3_review.md` (**Unverified** path exists in builder tree)

---

## 6. Can a first-time viewer understand the problem, result, and limits within a minute?

**Verdict: Possible with the guide; easy to miss limits without reading science docs.**

**Reason.** The hero and landing table state **centre vs 0°** and **practice / terrain Unknown** in copy. The **25-step tour** walks lanes, playhead, and exports. There is **no single splash screen** that lists every non-claim (disc visibility, DSN, power); a hurried judge could confuse “Earth clear” with “ground station contact.”

**Evidence**

- One-minute path: [Start tour](../web/review-candidate/?tour=1) → first timeline readout (~1 min if skipped fast)
- Limits in UI copy: [Landing page](../web/index.html) · lane labels in navigator
- Full limits: [Science and data reference §1](science-and-data-reference.md#1-claim-scope)

---

## Geometric 0° demo — what it does and does not show

**Does show:** Time intervals when Horizons Q4 **centre** apparent airless elevation is above **0°**, for Sun (`10`) and Earth (`399`), for two saved south-pole practice observers, with **Both** lane logic and **Unknown** when angles or interval rules fail.

**Does not show:** Terrain-blocked clearance, disc illumination, power, or station contact. **Terrain mode** in the UI is intentionally **Unknown** until reviewed skyline data feeds `HorizonSource`.

**Evidence:** [Engine reference — geometric calculation](engine-reference.md) · [Science and data reference §3](science-and-data-reference.md#3-the-0-centre-ray-method)

---

## Three highest-impact fixes before judging

1. **Lead + Science sign-off on scope and eligibility** — Decide whether January 2025 practice runs may support a submission claim; approve SC-1 (0°-only release with terrain Unknown) or narrow the pitch further. *Blocks honest Global Awards wording.*  
   → [Project progress — open decisions](project-progress.md#open-decisions)

2. **Close or front-and-centre the Horizons raw-file identity gap** — Either reconcile Appendix B vs on-disk `response.json` SHA-256 or state the mismatch plainly in the demo script so judges do not doubt the 48 h witness runs.  
   → [Science and data reference — raw-file identity](science-and-data-reference.md#raw-file-identity-open)

3. **Re-verify the release package on the commit judges will see** — Regenerate manifest, run `builder/scripts/verify_release_package.py`, refresh pytest count, and attach a **reachable offline walkthrough** (URL or recording) per official deliverables.  
   → [Release package](release/RELEASE.md) · [Teammate checklist](release/TEAMMATE_CHECKLIST.md)

---

*Last aligned with repository docs as of the local candidate on `main`; numbers in [Project progress](project-progress.md) may be newer than this page until someone refreshes it.*