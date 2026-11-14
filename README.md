# Lunar Landing Site Navigator — Hackathon builder

Fresh repository for the NASA Space Apps **Lunar Landing Site Navigator** build. Master Reference **revision 0.5** lives in `Master-Reference/`.

## Quick start (M0)

```sh
export DATA_ROOT="$(pwd)/data"
cd builder && python3 scripts/validate_handoff.py && python3 scripts/next_task.py
python3 builder/scripts/run_acceptance.py --offline --gate M0
builder/scripts/verify_offline_wheels.sh
```

| Layer | Path |
|-------|------|
| **Product** | `src/`, `web/`, `tests/` |
| **Agent worker** | `builder/` (handoff, harness, skills) |

- **Agent charter:** `builder/AGENTS.md`
- **Handoff:** `builder/agent_handoff.json`
- **Harness index:** `builder/docs/harness.md`

Local `data/` is staged offline (~5.5 GB) and is **not** committed to Git.

## Educational reference (read-only)

`~/Documents/Learning/lunar-landing-site-navigator` — historical notes and synthetic prototype; do not copy into submission build.