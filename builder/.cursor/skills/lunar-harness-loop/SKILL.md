---
name: lunar-harness-loop
description: >-
  Standard agent loop: context → implement → acceptance → handoff → next task.
  Use at session start/end and for /loop QA rehearsals.
disable-model-invocation: true
---

# Harness loop

## Live handoff vs Master Reference

| Record | Path |
|--------|------|
| **Live task** | `builder/agent_handoff.json` only |
| **Example template** | `Master-Reference/MASTER_REFERENCE.json` → `agent_handoff` with `"example_only": true` |

Never sync live state into the reference bundle. `check_handoff_separation.py` enforces this.

## Session start (preferred entry)

```sh
cd builder
./scripts/run_harness_cycle.sh --lane qa
```

Or stepwise: `validate_handoff.py` → `check_handoff_separation.py` → `check_m0_closure.py` → `agent_context.py` → `next_task.py`

## After each slice

1. `run_acceptance.py --gate <M#>` [and `--offline` at M0/M3]
2. `verify_result_contract.py` when run JSON exists (`lunar-result-contract`)
3. Update `builder/docs/task-log.md` and **live** handoff only
4. `next_task.py`

## Long QA / rehearsal

Use Cursor `/loop` only for:

`./scripts/run_harness_cycle.sh --acceptance --offline --case-fit`

Not for unbounded implementation without gates.