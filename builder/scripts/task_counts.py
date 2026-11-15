#!/usr/bin/env python3
"""Verified task counts from the canonical schedule, handoff and task log.

A skipped task earns no credit. A task recorded as done while a prerequisite is
unmet is reported as invalid_credit and earns none. Only an approved entry in
handoff["scope_changes"] releases a dependency, and it still earns no credit.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _harness import effective_statuses, schedule_tasks

# Core local product: M0-M4 (terrain review included even when blocked) plus the
# M6.1 freeze. Optional M5, rest, and pitch/submission tasks M6.2-M6.5 are roadmap only.
CORE_PREFIXES = ("M0.", "M1.", "M2.", "M3.", "M4.")
CORE_EXTRA = ("M6.1",)


def is_core(task_id: str) -> bool:
    return task_id.startswith(CORE_PREFIXES) or task_id in CORE_EXTRA


def summarize(tasks: list[str], eff: dict) -> dict:
    counts = Counter(eff[t]["class"] for t in tasks)
    total = len(tasks)
    verified = counts.get("verified", 0)
    conditional = counts.get("conditional", 0)
    return {
        "total": total,
        "verified": verified,
        "verified_pct": round(100 * verified / total, 1) if total else 0.0,
        "verified_plus_conditional": verified + conditional,
        "verified_plus_conditional_pct": round(100 * (verified + conditional) / total, 1) if total else 0.0,
        "classes": dict(sorted(counts.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    eff = effective_statuses()
    ids = [t["task_id"] for t in schedule_tasks()]
    core = [t for t in ids if is_core(t)]
    report = {
        "full_roadmap": summarize(ids, eff),
        "core_local_product": summarize(core, eff),
        "by_class": {k: [t for t in ids if eff[t]["class"] == k] for k in sorted({v["class"] for v in eff.values()})},
        "invalid_credit": {t: eff[t] for t in ids if eff[t]["class"] == "invalid_credit"},
    }
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    for name in ("full_roadmap", "core_local_product"):
        r = report[name]
        print(
            f"{name}: verified {r['verified']}/{r['total']} ({r['verified_pct']}%)"
            f" | verified+conditional {r['verified_plus_conditional']}/{r['total']}"
            f" ({r['verified_plus_conditional_pct']}%) | {r['classes']}"
        )
    for klass, members in report["by_class"].items():
        print(f"  {klass}: {', '.join(members)}")
    for tid, meta in report["invalid_credit"].items():
        print(f"INVALID CREDIT {tid}: recorded {meta['recorded']} but unmet prerequisites {meta['unmet']}")
    return 1 if report["invalid_credit"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
