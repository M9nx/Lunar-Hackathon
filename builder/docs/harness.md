# Agent harness — scripts reference

Agents **must** use these entrypoints (do not improvise `lunar_offline_pack.py` flags).

All paths relative to **`builder/`** (run from this directory).

| Script | Purpose |
|--------|---------|
| `scripts/next_task.py` | Earliest unfinished task with deps met (`--json`) |
| `scripts/validate_handoff.py` | Handoff schema + revision + check statuses |
| `scripts/agent_context.py` | Context pack (`--lane math\|impl\|qa`) |
| `scripts/case_fit_horizons.py` | Scenario vs saved Horizons provenance/CSV |
| `scripts/run_acceptance.py` | §9 pytest gate (`--offline` for pack smoke) |
| `scripts/classify_fixture.py` | Centre-ray classification CLI |
| `scripts/skyline_check.py` | Ridge / skyline teaching comparator |
| `scripts/offline_pack.sh` | `lunar_offline_pack.py` with `DATA_ROOT` |
| `scripts/wifi_off_smoke.sh` | M0.5 offline + attestation file |
| `scripts/run_m0_offline_smoke.sh` | Core + horizons static checks |
| `scripts/verify_offline_wheels.sh` | M0.4 venv install |
| `scripts/run_harness_cycle.sh` | **Preferred:** full cycle (flags below) |
| `scripts/harness_cycle.py` | validate → separation → M0 review → context → next_task [+ gates] |
| `scripts/check_handoff_separation.py` | Live handoff ≠ Master Reference example |
| `scripts/check_m0_closure.py` | M0.2/M0.3/M0.5 warnings |
| `scripts/verify_result_contract.py` | Run-result JSON shape (M1+) |

## Preferred entry

```sh
cd builder
./scripts/run_harness_cycle.sh --lane qa
./scripts/run_harness_cycle.sh --acceptance --offline --gate M0 --case-fit
python3 scripts/verify_result_contract.py ../tests/fixtures/run_result_geometric_0deg_minimal.json
```

## Loop

`run_harness_cycle → implement → run_acceptance → update handoff → next_task`

See `.cursor/skills/lunar-harness-loop/SKILL.md`.