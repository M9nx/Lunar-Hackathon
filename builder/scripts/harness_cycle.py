#!/usr/bin/env python3
"""Run the standard builder harness cycle (validate → separation → M0 review → context → next_task → optional gates)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
BUILDER = SCRIPTS.parent
REPO = BUILDER.parent


def run(name: str, cmd: list[str]) -> int:
    print(f"\n=== {name} ===")
    print("+", " ".join(cmd))
    return subprocess.call(cmd, cwd=BUILDER)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", default="all", choices=("math", "impl", "qa", "all"))
    parser.add_argument("--acceptance", action="store_true", help="Run run_acceptance.py")
    parser.add_argument("--gate", default="M0")
    parser.add_argument("--offline", action="store_true", help="Pass --offline to acceptance")
    parser.add_argument("--case-fit", action="store_true", help="Run practice Horizons case-fit")
    parser.add_argument("--contract", type=Path, help="Run verify_result_contract on path")
    args = parser.parse_args()

    py = sys.executable
    steps: list[tuple[str, list[str], bool]] = [
        ("validate_handoff", [py, str(SCRIPTS / "validate_handoff.py")], True),
        ("check_handoff_separation", [py, str(SCRIPTS / "check_handoff_separation.py")], True),
        ("check_m0_closure", [py, str(SCRIPTS / "check_m0_closure.py")], False),
        ("agent_context", [py, str(SCRIPTS / "agent_context.py"), "--md", "--lane", args.lane], False),
        ("next_task", [py, str(SCRIPTS / "next_task.py")], False),
    ]

    if args.case_fit:
        scenario = REPO / "tests/fixtures/site04_p02_practice_scenario.json"
        steps.insert(
            -1,
            (
                "case_fit_horizons",
                [py, str(SCRIPTS / "case_fit_horizons.py"), "--scenario", str(scenario)],
                False,
            ),
        )

    if args.contract:
        steps.append(
            (
                "verify_result_contract",
                [py, str(SCRIPTS / "verify_result_contract.py"), str(args.contract)],
                False,
            ),
        )

    if args.acceptance:
        acc = [py, str(SCRIPTS / "run_acceptance.py"), "--gate", args.gate]
        if args.offline:
            acc.append("--offline")
        steps.append(("run_acceptance", acc, False))

    code = 0
    for name, cmd, fail_fast in steps:
        rc = run(name, cmd)
        if rc != 0 and fail_fast:
            print(f"\nharness_cycle=STOPPED at {name} exit={rc}")
            return rc
        code = max(code, rc)

    print(f"\nharness_cycle=DONE exit={code}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())