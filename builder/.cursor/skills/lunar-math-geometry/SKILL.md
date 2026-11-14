---
name: lunar-math-geometry
description: >-
  Reviews centre-ray math, margins, Both-lane priority, and §9 fixtures before
  implementation merges. Use for M1.2+, terrain geometry (M4), and acceptance
  failures.
disable-model-invocation: true
---

# Math / geometry lane

## Before changing classification

1. Load context: `python3 scripts/agent_context.py --lane math --md`
2. Run: `python3 scripts/run_acceptance.py --gate M1`
3. Spot-check: `python3 scripts/classify_fixture.py --elevation 0.5 --elevation 0 --elevation -0.5`
4. Ridge teaching check: `python3 scripts/skyline_check.py`

## Rules (§6)

- Margin `m = elevation_deg - horizon_deg`; `m > 0` → clear; `m ≤ 0` → blocked.
- Both: **blocked** > **unknown** > **clear**.
- Terrain horizon `null` → unknown with reason (never coerce to 0°).

## Sign-off

Math lane approves when `run_acceptance.py` passes and handoff lists evidence paths. Impl lane merges only after that for visibility logic changes.