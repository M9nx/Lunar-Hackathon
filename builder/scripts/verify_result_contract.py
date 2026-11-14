#!/usr/bin/env python3
"""Validate a run-result JSON file against Master Reference §5 shape (minimal gate)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BUILDER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BUILDER_ROOT.parent

REQUIRED_TOP = (
    "schema_version",
    "run_id",
    "scenario",
    "intervals",
    "elapsed_seconds",
)
SCENARIO_KEYS = ("site_id", "horizon_mode", "start_utc", "end_utc", "step_seconds")
LANES = ("sun", "earth", "both")
STATES = frozenset({"clear", "blocked", "unknown"})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    data = json.loads(args.path.read_text(encoding="utf-8"))

    for key in REQUIRED_TOP:
        if key not in data:
            errors.append(f"missing top-level key: {key}")

    scenario = data.get("scenario") or {}
    for key in SCENARIO_KEYS:
        if key not in scenario:
            errors.append(f"scenario missing {key}")

    if scenario.get("horizon_mode") not in ("geometric_0deg", "terrain"):
        errors.append("scenario.horizon_mode must be geometric_0deg or terrain")

    for ts_key in ("start_utc", "end_utc"):
        ts = scenario.get(ts_key, "")
        if not str(ts).endswith("Z"):
            errors.append(f"{ts_key} must be ISO UTC with Z suffix")

    elapsed = data.get("elapsed_seconds") or {}
    for lane in LANES:
        if lane not in elapsed:
            errors.append(f"elapsed_seconds missing lane {lane}")
            continue
        for st in ("clear", "blocked", "unknown"):
            if st not in elapsed[lane]:
                errors.append(f"elapsed_seconds.{lane} missing {st}")

    for i, iv in enumerate(data.get("intervals") or []):
        if iv.get("state") not in STATES:
            errors.append(f"interval[{i}] invalid state")
        if not iv.get("start_utc") or not iv.get("end_utc"):
            errors.append(f"interval[{i}] needs start_utc and end_utc")

    if errors:
        print("CONTRACT INVALID")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("CONTRACT OK", args.path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())