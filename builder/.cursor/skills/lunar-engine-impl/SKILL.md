---
name: lunar-engine-impl
description: >-
  Implements engine, parsers, and CLI in src/lunar_navigator using §5 contracts.
  Use for M1.2+ after math fixtures pass.
disable-model-invocation: true
---

# Implementation lane

## Context

```sh
python3 scripts/agent_context.py --lane impl --md
export DATA_ROOT="$(pwd)/data"
```

## Workflow

1. Implement in `src/lunar_navigator/`; tests in `tests/`.
2. Horizons intake: `python3 scripts/case_fit_horizons.py --scenario tests/fixtures/site04_p02_practice_scenario.json`
3. `python3 scripts/run_acceptance.py --gate M1`
4. Update `agent_handoff.json` `report.commands_run` and `evidence_refs`.

## Imports

Add repo root / `src` to path in CLI entrypoints; keep calculation pure (no network in engine core).