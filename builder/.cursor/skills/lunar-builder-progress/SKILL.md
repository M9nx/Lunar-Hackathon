---
name: lunar-builder-progress
description: >-
  Session handoff snapshot for Lunar-Hackathon: what is built, active task, blockers,
  and a paste-ready context prompt. Use at chat start, after closing a milestone gate,
  or when the user asks what is done so far.
disable-model-invocation: true
---

# Builder progress and session handoff

## When to use

- **Start of a new agent session** (read this skill before `lunar-milestone-router`).
- After **M0.5**, **M1**, or any gate moves to `passed`.
- When the user asks for status, “what’s done”, or context for a new thread.

## Authority order

1. `builder/agent_handoff.json` — active `task_id`, checks, blockers  
2. `builder/docs/task-log.md` + `builder/docs/decision-log.md`  
3. **This skill** — human-readable snapshot (update when the table below goes stale)  
4. Master Reference **0.5** — requirements; embedded handoff is `example_only`

## Maintenance

After a milestone pass or major repo change, update **Snapshot** (date, rows, prompt block). Keep one screenful; move detail to task/decision logs.

Run before claiming “repo healthy”:

```sh
cd builder && ./scripts/run_harness_cycle.sh --lane qa
builder/scripts/install_git_hooks.sh   # once per clone
```

---

## Snapshot (2026-11-14)

| Area | State |
|------|--------|
| **Active task** | **M2.5** terrain audit — not started. 0° replay is the verified package |
| **M0** | M0.5 **passed** (Wi-Fi off 2026-11-14T09:54:24Z, backup `/home/m9nx/Lunar-Hackathon-data-backup`). M0.1 Resources tab still HTTP 500. M0.2 practice pair selected for replay; eligibility open |
| **M1–M3** | Practice 0° package **passed** with open decisions. Runs `site04-p02-practice-q4-centre-0deg-a24325ba50c4` and `malapert-practice-q4-centre-0deg-88b9b3cfef57` |
| **Product** | `src/lunar_navigator/` centre-ray engine; `web/replay/` offline shell |
| **Agent worker** | `builder/` handoff, 16 skills, harness scripts, guardrails in `lunar-guardrails.mdc` |
| **Data** | Local `data/` ~5.5 GB **gitignored**; practice Horizons under `data/horizons/*-practice/` |
| **Git** | `https://github.com/M9nx/Lunar-Hackathon` (private); human-only commits; no Cursor `Co-authored-by` |
| **Reference** | `Master-Reference/` rev **0.5** synced; schedule from JSON (workbook has no Tasks tab) |
| **Result definition** | **Centre-ray only.** Labels: Sun-centre clearance, Earth-centre clearance, Both centres clear. Product 69 is long-term any-disc context, not a centre-ray benchmark. |

### Delivered this phase (builder + repo)

- Fresh repo layout: product `src/`, `web/`, `tests/` vs worker `builder/`.
- Harness: `validate_handoff`, `next_task`, `run_acceptance`, `harness_cycle`, M0 smoke, case-fit, result-contract check.
- **Guardrails** expanded: Unknown/Both lane, offline replay, milestone gates, input/evidence rules, **Time and angles**, **Terrain gate**, **Git attribution**.
- **Centre-ray decision (2026-11-14):** M1–M3 keep quantity-4 target-centre math and the three clearance labels. Product 69 stays context. Any-disc comparison is a later separate metric. Appendix B raw-response hash mismatch stays open. Detail: `builder/docs/decision-log.md`.
- **Git hygiene**: `prepare-commit-msg` strips AI co-authors; `commit-msg` blocks; `check_commit_coauthors.py` in harness cycle.
- Initial GitHub push; history scrubbed of Cursor co-author on root commit.

### Next (in order)

1. M2.5 stays blocked until Science reviews frame, height, coverage, and one skyline. Keep the 0° replay.
2. Lead: Resources tab and submission eligibility. Appendix B raw-response hash stays open.
3. Replay: `python3 -m http.server 8765 --directory web/replay`.

---

## Paste-ready prompt (new session)

Copy the block below into a new chat so the agent loads context without re-deriving history.

```markdown
## Lunar Landing Site Navigator — session context

You are the **lunar builder agent** (worker in `builder/`, not the product). Read `builder/AGENTS.md`, `builder/agent_handoff.json`, and skill **`lunar-builder-progress`**.

**Master Reference:** revision **0.5** at `Master-Reference/MASTER_REFERENCE.json`.  
**Fresh repo only** — `~/Documents/Learning/lunar-landing-site-navigator` is read-only history.

**Active work:** M0.5 passed. Practice 0° replay is in `web/replay/` at git `4ddc29b-dirty`. Run IDs `site04-p02-practice-q4-centre-0deg-a24325ba50c4` and `malapert-practice-q4-centre-0deg-88b9b3cfef57`. Next open task is **M2.5** terrain, which stays gated. Submission eligibility and the Appendix B raw-response hash stay open.

**Repo:** `Lunar-Hackathon` on GitHub (private). Product: `src/lunar_navigator/`, `tests/`, `web/`. Worker: `builder/` (scripts, handoff, skills, evidence). Local `data/` is gitignored.

**Guardrails:** follow `builder/.cursor/rules/lunar-guardrails.mdc` always (centre-ray labels only, Product 69 as long-term context, Unknown mandatory, Both lane, terrain gate until M4, no Cursor co-author on commits). Use `builder/scripts/*` only for harness checks.

**Result definition (2026-11-14):** Keep the centre-ray calculation. Label **Sun-centre clearance**, **Earth-centre clearance**, and **Both centres clear**. The practice 48-hour 0° totals stay valid under that policy. Product 69 is a long-term any-portion-of-disc fraction, not a timestamped or like-for-like check of those windows. Any-disc comparison is a later metric and must match period, cadence, location, height, terrain, and visibility definition first. Leave the Product 69 simulation bounds and the Appendix B raw-response hash mismatch unresolved. Submission eligibility stays pending.

**Open decisions:** Resources tab still HTTP 500; submission eligibility open; Malapert reference altitude 0 km; Appendix B raw-response hash open; M3.3 pitch not started. Practice pair is the replay, not a submission claim.

**Your first commands:**

```sh
cd /home/m9nx/Lunar-Hackathon/builder
./scripts/run_harness_cycle.sh --lane qa
python3 scripts/validate_handoff.py
python3 scripts/next_task.py
```

Then continue M0.5 closure or route per `lunar-milestone-router` after reading handoff blockers.
```

---

## Related skills

| Need | Skill |
|------|--------|
| Route next task | `lunar-milestone-router` |
| QA evidence | `lunar-qa-evidence` |
| Loop after implement | `lunar-harness-loop` |
| Scope / judging | `lunar-challenge-scope` |