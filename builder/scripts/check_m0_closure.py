#!/usr/bin/env python3
"""Reconcile M0.2 observer/window scope with M0.3 bundle and M0.5 offline evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BUILDER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BUILDER_ROOT.parent

HANDOFF = BUILDER_ROOT / "agent_handoff.json"
DECISION_LOG = BUILDER_ROOT / "docs/decision-log.md"
PRACTICE_SCENARIO = REPO_ROOT / "tests/fixtures/site04_p02_practice_scenario.json"


def main() -> int:
    handoff = json.loads(HANDOFF.read_text(encoding="utf-8"))
    warnings: list[str] = []
    errors: list[str] = []

    m02 = (handoff.get("prior_tasks") or {}).get("M0.2", {})
    m03 = (handoff.get("prior_tasks") or {}).get("M0.3", {})
    checks = handoff.get("checks") or {}

    # M0.3 passed with generic bundle; M0.2 still open
    if m03.get("status") == "passed" and m02.get("status") == "in_progress":
        if PRACTICE_SCENARIO.is_file():
            warnings.append(
                "M0.3 evidence covers staged bundle; M0.2 submission case still open — "
                "practice site04_p02 is NOT submission until case-fit + eligibility"
            )

    if checks.get("wifi_disabled_on_demo_laptop") == "pending":
        warnings.append("M0.5 pending: Wi-Fi-off witness (builder/docs/evidence/wifi_off_attestation.txt)")

    if checks.get("backup_copy_noted") == "pending":
        warnings.append("M0.5 pending: backup copy of data bundle on demo laptop")

    for b in handoff.get("report", {}).get("blockers") or []:
        if "M0.1" in b and "brief" in b.lower():
            warnings.append(f"M0.1 open: record whether brief affects eligibility/submission — {b}")

    if not DECISION_LOG.is_file():
        errors.append("missing builder/docs/decision-log.md")

    print("M0 CLOSURE REVIEW")
    for w in warnings:
        print(f"  WARN {w}")
    for e in errors:
        print(f"  FAIL {e}")

    if errors:
        return 1
    print("  status=review_complete (warnings do not block script exit)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())