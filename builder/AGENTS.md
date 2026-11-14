# Lunar builder agent (worker)

This directory is the **Cursor agent worker**. It is not the hackathon product.

| Layer | Path |
|-------|------|
| **Agent worker** | `builder/` (this file, handoff, harness, skills, logs) |
| **Product** | `../src/lunar_navigator/`, `../web/`, `../tests/` |
| **Authority** | `../Master-Reference/MASTER_REFERENCE.json` **rev 0.5** |
| **Data** | `../data/` (gitignored at repo root) |

## Roles (one agent, three hats)

| Hat | Skill |
|-----|--------|
| Geometry / science | `lunar-math-geometry`, `lunar-topocentric-sun-earth`, `lunar-skyline-rays-moon`, `lunar-frames-terrain-science`, `lunar-horizons-ephemeris` |
| Implementation | `lunar-engine-impl`, `lunar-data-intake`, `lunar-result-contract` |
| UI / UX | `lunar-nasa-ui-theme`, `lunar-comparison-ux` |
| QA / routing | `lunar-qa-evidence`, `lunar-milestone-router`, `lunar-harness-loop`, `lunar-m0-offline-smoke` |
| Session context | `lunar-builder-progress` |
| Scope / pitch | `lunar-challenge-scope` |

## Active workflow

At **session start**, read skill **`lunar-builder-progress`** (paste prompt + snapshot), then:

```sh
cd builder
./scripts/run_harness_cycle.sh --lane qa
```

1. Pick lane skill (math | impl | qa | ui).
2. Run `builder/scripts/*` only — see `docs/harness.md`.
3. `python3 scripts/run_acceptance.py` from repo root venv when needed.
4. Update `docs/task-log.md`, `docs/decision-log.md`, `agent_handoff.json`.
5. Do not start **M1** until **M0.5** passes.

## Context packing

`python3 scripts/agent_context.py --lane math|impl|qa`  
UI work also load `lunar-nasa-ui-theme` + `lunar-comparison-ux`.

## External references

`docs/references-external.md` (NASA WDS, Horizons, Open MCT patterns).

## Practice data

`../data/horizons/*-practice/` — fixtures until case-fit + eligibility pass (`lunar-horizons-ephemeris`).