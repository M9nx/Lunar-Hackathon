# Judge Q&A — understanding check

Candid answers for NASA Space Apps 2026 judges and for the team.  
**Release claim:** geometric **0° centre-ray** on **practice** Horizons packs. Terrain clearance is **Unknown**.  
`eligible_for_submission_claim` is **true** on the January Horizons practice packs (`web/replay/`, practice-30d, practice-jan03-10) after Lead L1 (2026-11-15). QA fixtures stay false. See `builder/docs/evidence/l1_eligibility_decision.md`.

Open the navigator: [review-candidate](../web/review-candidate/).  
Related: [About this solution](about-solution.md) · [Science and data reference](science-and-data-reference.md) · [Engine reference](engine-reference.md) · [Project progress](project-progress.md).

---

## Lead note: M4 — keep current, or finish terrain?

**Prefer keeping the current 0° solution as the demo story.** It is complete *for what it claims*. Rushing terrain Clear/Blocked without M4 would make the product look finished and the science dishonest.

| | Current (0°) | Finish M4 (terrain) |
| --- | --- | --- |
| Status | Demo-ready if claims stay inside the fence | **Not** done (task log: M4.1 blocked) |
| Honest pitch | Strong | Weak until Science signs S2–S5 |
| Extra work | Lead L1–L5, demo link, disclosure | Days of Science + new Horizons heights + independent skyline |

**What M4 is:** our milestone for “terrain clearance is allowed.” Needs reviewed frame, vertical reference, radial coverage, and one independently checked skyline direction. See [Data research — M4 next attempt](data-research.md#m4-concrete-next-attempt) and project progress Science S2–S5.

**How long (honest):**

- **One Site04 direction (318.623526°), paper trail only:** ~0.5–1 focused Science day if DEM SHA/CRS and observer height are already agreed.
- **Site04 accepted skyline + UI still Unknown until freeze:** ~2–4 Science days including tolerance debate.
- **Malapert too (new height → re-query Horizons → matching skyline):** add ~2–5 days; blocked today by 0 km vs DEM surface ([Malapert altitude note](../builder/docs/evidence/s2_malapert_reference_altitude.md)).
- **Lead/QA freeze that terrain Clear/Blocked may be shown:** only after Science accept — not a same-afternoon checkbox.

**How (short):** verify LDEM 240 m file → lock observer frame/height → independent radial trace at Site04 Sun azimuth 318.623526° (2025-01-01T00:00Z) → compare two methods → Science sets tolerance → then Malapert after height decision. Until then: DEM plots = diagnostic only.

---

## A. Challenge fit and claims

### A1. What problem does this solve?

**Answer.** Compare two lunar south-pole–class sites over a shared UTC window for when the **centre** of the Sun and of Earth is above a **flat local horizon**.

**Explanation.** Useful for illumination / Earth-geometry *thinking*. Not power, not radio links, not disc-weighted lighting.

**Evidence.** Challenge framing: [About §1](about-solution.md#1-what-real-problem-are-we-solving-and-for-whom) · [Science §1 claim scope](science-and-data-reference.md#1-claim-scope) · in-app tour `?tour=1`.

---

### A2. Are you solving the actual Space Apps challenge?

**Answer.** Yes for the core “compare sites and dates for Sun/Earth vs horizon” — under a deliberate **centre-ray / 0°** cut. Terrain and submission eligibility are still open.

**Explanation.** Overclaiming terrain or eligibility fails Relevance and Validity. We hit the brief with an honest thin slice.

**Evidence.** [About §3](about-solution.md#3-which-challenge-requirements-does-the-current-demo-address-and-which-are-still-open) · [Project progress — open Lead/Science](project-progress.md).

---

### A3. Who benefits?

**Answer.** Judges, educators, and planners who want an **inspectable** two-site timeline with receipts. Not flight ops replacing STK.

**Evidence.** [About §1](about-solution.md#1-what-real-problem-are-we-solving-and-for-whom).

---

### A4. What do you explicitly not claim?

**Answer.** Disc visibility, received power, radio-link / ground-station contact, Product 69 as a like-for-like check of these windows, terrain Clear/Blocked.

**Explanation.** Centre below the plane can still leave part of a disc above it; that does not change centre-ray state.

**Evidence.** Guardrails / [Science §1](science-and-data-reference.md#1-claim-scope) · [Project progress — what the release shows](project-progress.md#what-the-release-shows) · UI limits copy on the navigator.

---

## B. Method and engine

### B1. What is “centre-ray”?

**Answer.** Horizons quantity **4**: apparent **airless** elevation of the **target centre** (Sun `10`, Earth `399`) as seen from a lunar surface observer (`301@301`).

**Explanation.** We classify that elevation against the selected horizon (here: geometric 0°). We do not integrate over the solar/Earth disc.

**Evidence.** [Engine reference](engine-reference.md) · sample rows under `data/horizons/site04-p02-practice/` · worked sample in engine reference.

---

### B2. How do you decide Clear / Blocked / Unknown?

**Answer.** `margin = elevation − horizon`. Classify on the **unrounded** margin: `> 0` → clear; `≤ 0` (including contact) → blocked; missing elevation or required horizon → unknown. Round only for display.

**Explanation.** Clear + Blocked + Unknown duration equals the requested window (half-open intervals; terminal sample adds 0 duration).

**Evidence.** [Engine reference](engine-reference.md) · pytest / browser checks · Details panel raw seconds in the UI.

---

### B3. What does the Both lane mean?

**Answer.** Both **centres** clear. Rule: if either body is Blocked → Both Blocked; else if either Unknown → Both Unknown; else Clear only if both Clear.

**Evidence.** Engine Both-lane tests · UI Clearance “Both centres” · [Engine reference](engine-reference.md).

---

### B4. Does “Minimum clear window” change the Clear totals?

**Answer.** No. It filters continuous Clear spans for lists / questions. Headline Clear totals still count every Clear second.

**Evidence.** Control label/title on `#min-duration` · result panel `.res-windows` · `tests/browser_unknown_check.py` (Both + 1 h filter checks).

---

### B5. Does the UI recompute science?

**Answer.** No. The engine owns classification. The UI formats one versioned result (timeline, inspector, totals, export).

**Evidence.** [Engine reference](engine-reference.md) · exported run JSON matches on-screen Details seconds.

---

## C. Data and validity

### C1. What data do you actually use for the demo numbers?

**Answer.** Saved JPL Horizons packs under **`data/horizons/`** (`response.json`, `provenance.json`, `angles.csv`). Packaged comparisons under `web/replay/` (48 h witnessed) and `web/review-candidate/cases/` (30 d, Jan 3–10).

**Explanation.** At classify time the engine does **not** call JPL. Live stream still classifies saved files via the local API.

**Evidence.** Open any `data/horizons/*/provenance.json` · [Engine reference — intake](engine-reference.md) · practice `comparison.json` files.

---

### C2. What about DEM / LOLA / Product 69 / SPICE under `/data`?

**Answer.**

| Path | Role in the claim |
| --- | --- |
| `data/horizons/` | **Primary** — clearance numbers |
| `data/offline/` | Offline wheels/vendor — runtime support |
| `data/LOLA_*`, Product 69 | Present; **not** used to claim clearance |
| `data/spice/` | Present; demo ephemeris path is Horizons tables |

**Explanation.** DEM skyline in the UI is an opt-in **diagnostic**. Product 69 is long-term context, not a timestamped centre-ray benchmark.

**Evidence.** [Data research](data-research.md) · [Science — Product 69](science-and-data-reference.md) · terrain diagnostic toggle behaviour.

---

### C3. Are the January inputs submission-eligible?

**Answer.** They are labeled **practice** and Lead-approved for a centre-ray 0° submission claim. Manifest/runs on the three January packs carry `eligible_for_submission_claim: true` (L1, 2026-11-15). QA stays false.

**Evidence.** `web/replay/comparison.json` · [Lead handoff](../builder/docs/evidence/m0_1_lead_handoff.md) · [Project progress L1](project-progress.md).

---

### C4. Can we trust the arithmetic?

**Answer.** For traced 0° practice runs: yes — case-fit on packs, engine tests, notebook/trace path, witnessed revision for 48 h. Not closed for production terrain or for “any NASA product averages match.”

**Caveats to say out loud.** Appendix B vs on-disk `response.json` hash mismatch still **open**; Malapert practice height is a practice choice.

**Evidence.** [About §4](about-solution.md#4-how-reliable-are-the-data-and-calculations-for-the-claims-we-make) · `docs/notebooks/01_trace_observation_to_interval_total.ipynb` · `docs/evidence/` · [raw-file identity](science-and-data-reference.md).

---

### C5. How do we prove one number on screen?

**Answer.** Select the sample → View evidence → Horizons row / `source_ref` into `angles.csv`. Same run JSON feeds export.

**Evidence.** Navigator “View evidence” · `source_ref` fields in run samples · [Engine worked sample](engine-reference.md).

---

## D. Terrain and M4

### D1. Why is terrain Unknown?

**Answer.** M4 review has not passed (frame, height, radial coverage, independent direction). Engine returns `unknown` / `terrain_not_reviewed` in terrain mode.

**Evidence.** [Science §1](science-and-data-reference.md) · [Project progress Science S2–S5](project-progress.md) · `builder/docs/task-log.md` (M4.1 blocked).

---

### D2. Why show a DEM line at all?

**Answer.** Diagnostic only — so reviewers see we are not hiding topography. It must not change Clear/Blocked until M4.

**Evidence.** Terrain toggle copy in UI · [decision log terrain diagnostic](../builder/docs/decision-log.md) · profiles under `web/review-candidate/terrain/`.

---

### D3. What would closing M4 take?

**Answer.** See Lead note above and [M4 concrete next attempt](data-research.md#m4-concrete-next-attempt): Site04 318.623526° independent skyline first; Malapert only after height + re-query.

**Evidence.** `builder/docs/evidence/s2/terrain_independent_skyline.json` · `s2_science_review.md` · `s2_malapert_reference_altitude.md`.

---

## E. Demo practicality

### E1. How do judges / teammates run it?

**Answer.** Local serve of `web/` + API on `127.0.0.1` (default port 8766). Open `/review-candidate/`. Practice cases need no JPL call.

**Explanation.** Reachable **public** demo URL/recording is still Lead L5 if the event requires it — localhost alone is not enough for remote judges.

**Evidence.** [Operator manual](operator-manual.md) · [Release WALKTHROUGH](release/WALKTHROUGH.md) · [Lead handoff](../builder/docs/evidence/m0_1_lead_handoff.md).

---

### E2. Offline / Wi‑Fi off?

**Answer.** Designed for offline replay of saved inputs and vendored assets; Wi‑Fi-off smoke was recorded for M0.5-era evidence. Re-verify on the machine you claim.

**Evidence.** `docs/evidence/m0_5_wifi_off.log` · `docs/evidence/wifi_off_attestation.txt` (confirm files on the build you ship).

---

### E3. What should a one-minute demo show?

**Answer.** Practice 48 h → Site04 more Sun-centre clear than Malapert → Both 0 h → switch Clearance / min window → open Details or evidence for one sample → say the fence (0°, practice, terrain Unknown).

**Evidence.** In-app Guide · [About §5–6](about-solution.md).

---

### E4. Why is there still a `web/replay/` folder?

**Answer.** Frozen witnessed 48 h package (revision `1f3fb06`); Practice replay loads `../replay/comparison.json`. It is data + witness, not the primary judge UI.

**Evidence.** `web/replay/comparison.json` · operator manual packaging rules · decision log: do not regenerate in place.

---

## F. Creativity and process

### F1. What is actually different vs “just use Horizons”?

**Answer.** Two-site shared playhead, Both-lane rules, explicit Unknown, versioned JSON, Wi‑Fi-off path, and refusal to ship terrain totals without review.

**Evidence.** [About §2](about-solution.md#2-what-is-genuinely-creative-or-different-compared-with-existing-tools).

---

### F2. How does the team split ownership?

**Answer.** Science owns scientific acceptance of claims. Lead owns eligibility / disclosure / demo packaging. QA/Lead own freeze. Engine owns classification; UI formats.

**Evidence.** [Project progress](project-progress.md) · `builder/docs/decision-log.md` · `builder/agent_handoff.json`.

---

### F3. Did AI build this? What do we disclose?

**Answer.** Tools were used in development; exact Project-tab disclosure wording is **Lead L3 pending**. Do not improvise a final legal disclosure in the pitch until Lead records it.

**Evidence.** [Lead handoff](../builder/docs/evidence/m0_1_lead_handoff.md) · project progress L3.

---

## G. Trap questions (say this, then stop)

| Trap | Say |
| --- | --- |
| “So you know when the base has power?” | No. Centre-ray ≠ power. |
| “So Earth is visible for comms?” | No. Centre above 0° ≠ ground station. |
| “Your DEM shows a ridge — why Unknown?” | Diagnostic plot; M4 not passed. |
| “Match Product 69?” | Different metric and period; not our benchmark. |
| “Eligible NASA submission data?” | Practice packs; eligibility false until Lead L1. |
| “Live ephemeris?” | Saved tables; no JPL at classify time. |

---

## Quick evidence index

| Topic | Path |
| --- | --- |
| Claim fence | `docs/science-and-data-reference.md` |
| Engine math | `docs/engine-reference.md` |
| Horizons packs | `data/horizons/` |
| Witnessed 48 h | `web/replay/` (`1f3fb06`) |
| Longer practice | `web/review-candidate/cases/` |
| Open decisions | `docs/project-progress.md`, `builder/docs/decision-log.md` |
| Lead handoff | `builder/docs/evidence/m0_1_lead_handoff.md` |
| M4 how-to | `docs/data-research.md` (§ M4) |
| Unknown browser evidence | `docs/evidence/unknown/` |
| Pitch deck (optional) | Excalidraw scene linked from team chat |

---

*If an answer here disagrees with a newer Lead/Science decision record, the decision record wins — update this file after the decision is written.*
