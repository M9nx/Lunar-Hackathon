#!/usr/bin/env python3
"""Earliest unfinished schedule task whose dependencies are satisfied."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _harness import HANDOFF_PATH, next_ready_tasks, load_handoff


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", type=str, default=str(HANDOFF_PATH))
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    args = parser.parse_args()

    handoff = load_handoff()
    if args.handoff != str(HANDOFF_PATH):
        handoff = json.loads(open(args.handoff, encoding="utf-8").read())

    ready, done = next_ready_tasks(handoff)
    active = handoff.get("task_id")

    if args.json:
        print(
            json.dumps(
                {
                    "active_handoff_task_id": active,
                    "completed": sorted(done),
                    "ready_tasks": [
                        {
                            "task_id": t["task_id"],
                            "owner_role": t.get("owner_role"),
                            "work_item": t.get("work_item"),
                            "depends_on": t.get("depends_on"),
                            "acceptance": t.get("acceptance"),
                        }
                        for t in ready
                    ],
                    "earliest": ready[0]["task_id"] if ready else None,
                },
                indent=2,
            )
        )
    else:
        print(f"completed={len(done)} tasks")
        print(f"handoff.task_id={active}")
        if not ready:
            print("earliest=None (no tasks ready)")
            return 0
        first = ready[0]
        print(f"earliest={first['task_id']} owner={first.get('owner_role')}")
        print(f"depends_on={first.get('depends_on')}")
        print(f"acceptance={first.get('acceptance')}")
        if len(ready) > 1:
            print("also_ready=" + ",".join(t["task_id"] for t in ready[1:6]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())