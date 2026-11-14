---
name: lunar-milestone-router
description: >-
  Routes lunar-builder work to the earliest Master Reference task whose
  prerequisites are met. Use when starting a session, advancing handoff, or
  checking M0-M6 dependencies.
---

# Lunar milestone router

## Read first

1. `builder/agent_handoff.json` (live — **not** Master Reference embedded example).
2. `Master-Reference/MASTER_REFERENCE.json` → `schedule.tasks`.
3. `builder/docs/task-log.md` and `builder/docs/decision-log.md`.

## Dependency rules (M0)

- **M0.1** after Kickoff.
- **M0.2** and **M0.4** in parallel after **M0.1**.
- **M0.3** after **M0.2**.
- **M0.5** after **M0.3** and **M0.4**.
- **M1\*** only after **M0.5** passed with Wi-Fi-off evidence.

## M0.2 → M0.3 → M0.5 reconciliation

Before closing **M0.5**:

1. Run `python3 scripts/check_m0_closure.py`.
2. If **M0.3** passed on staged bundle but **M0.2** submission case is still **open**, treat practice Horizons (Site04-P02 / Malapert) as **fixtures only** until case-fit + eligibility pass.
3. When observers and UTC window are chosen in M0.2, re-run `case_fit_horizons.py` on the **submission** scenario (not practice) and attach evidence to M0.3/M1.1.
4. If bundle install precedes final case, record **Lead-approved scope change** in `builder/docs/decision-log.md`.

QA may collect offline pack evidence **now**; closing M0.5 still requires Wi-Fi-off witness + backup note.

## M0.1 open brief

If challenge brief / submission format is unverified, record in decision log:

- Does uncertainty affect **eligible NASA sources** or **submission format**?
- Block **promotion** of practice exports to demo claims until Lead answers.

## On task completion

1. Set checks to `pass`/`fail` with `evidence_refs`.
2. Update `builder/docs/task-log.md` (UTC).
3. Advance `task_id` only when deps satisfied.
4. **Do not** copy live handoff into `MASTER_REFERENCE.json` (example only).

## Harness

```sh
cd builder && ./scripts/run_harness_cycle.sh --acceptance --offline --gate M0
```

## Do not

- Skip to M1.1 while M0.5 is open.
- Mark `passed` without evidence paths.