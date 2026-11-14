#!/usr/bin/env python3
"""Emit context pack for the active task (task_id, core_model, contracts, §9 checks, DATA_ROOT)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _harness import (  # noqa: E402
    REPO_ROOT,
    checks_for_milestone,
    data_root,
    load_handoff,
    load_master_reference,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=str, help="Override task id (default: handoff.task_id)")
    parser.add_argument("--lane", choices=("math", "impl", "qa", "all"), default="all")
    parser.add_argument("--md", action="store_true", help="Markdown summary instead of JSON")
    args = parser.parse_args()

    handoff = load_handoff()
    ref = load_master_reference()
    task_id = args.task or handoff.get("task_id")
    dr = data_root(handoff)

    pack = {
        "task_id": task_id,
        "reference_revision": ref["document"].get("reference_revision"),
        "data_root": str(dr),
        "data_root_env": os.environ.get("DATA_ROOT", str(dr)),
        "core_model": ref.get("core_model"),
        "contracts": ref.get("contracts"),
        "checks_section9": checks_for_milestone(task_id or "M0", ref),
        "handoff_checks": handoff.get("checks"),
        "handoff_objective": handoff.get("objective"),
    }

    if args.lane == "math":
        pack = {
            k: pack[k]
            for k in ("task_id", "reference_revision", "core_model", "checks_section9")
            if k in pack
        }
    elif args.lane == "impl":
        pack = {
            k: pack[k]
            for k in (
                "task_id",
                "data_root",
                "contracts",
                "core_model",
                "handoff_objective",
            )
            if k in pack
        }
    elif args.lane == "qa":
        pack = {
            k: pack[k]
            for k in (
                "task_id",
                "checks_section9",
                "handoff_checks",
                "data_root",
            )
            if k in pack
        }

    if args.md:
        print(f"# Agent context — {task_id} ({args.lane})")
        print(f"- DATA_ROOT: `{dr}`")
        print(f"- Reference: **{pack.get('reference_revision')}**")
        if handoff.get("objective"):
            print(f"- Objective: {handoff['objective']}")
        print("\n## §9 checks (subset)")
        for c in pack.get("checks_section9") or []:
            print(f"- **{c.get('test')}**: {c.get('expected_result_and_evidence', '')[:120]}…")
    else:
        print(json.dumps(pack, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())