#!/usr/bin/env python3
"""Run §9 acceptance gate: unit tests + optional offline pack smoke."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

BUILDER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BUILDER_ROOT.parent
SCRIPTS = Path(__file__).resolve().parent


def run_pytest(extra: list[str]) -> int:
    venv_py = REPO_ROOT / ".venv" / "bin" / "python"
    python = str(venv_py if venv_py.is_file() else sys.executable)
    cmd = [python, "-m", "pytest", str(REPO_ROOT / "tests"), "-q", *extra]
    print("+", " ".join(cmd))
    return subprocess.call(cmd, cwd=REPO_ROOT)


def run_offline_smoke() -> int:
    script = SCRIPTS / "run_m0_offline_smoke.sh"
    if not script.is_file():
        print("skip offline smoke (script missing)")
        return 0
    return subprocess.call(["bash", str(script)], cwd=REPO_ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Include lunar_offline_pack smoke")
    parser.add_argument("--gate", type=str, default="M1", help="Milestone label for reporting only")
    parser.add_argument("pytest_args", nargs="*", help="Extra pytest arguments")
    args = parser.parse_args()

    print(f"acceptance_gate={args.gate}")
    code = run_pytest(args.pytest_args)
    if code != 0:
        return code
    if args.offline:
        code = run_offline_smoke()
    print("acceptance=PASS" if code == 0 else "acceptance=FAIL")
    return code


if __name__ == "__main__":
    raise SystemExit(main())