#!/usr/bin/env python3
"""Validate agent_handoff.json schema, check statuses, and reference revision."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

BUILDER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BUILDER_ROOT.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _harness import (  # noqa: E402
    CHECK_STATUS,
    HANDOFF_REQUIRED_KEYS,
    HANDOFF_PATH,
    MASTER_REF,
    load_handoff,
    load_master_reference,
)


def fail(msg: str, errors: list[str]) -> None:
    errors.append(msg)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", type=Path, default=HANDOFF_PATH)
    args = parser.parse_args()

    errors: list[str] = []
    handoff = json.loads(args.handoff.read_text(encoding="utf-8"))
    ref = load_master_reference()

    for key in HANDOFF_REQUIRED_KEYS:
        if key not in handoff:
            fail(f"missing required key: {key}", errors)

    rev = handoff.get("reference_revision")
    ref_rev = ref["document"].get("reference_revision")
    if rev != ref_rev:
        fail(f"reference_revision mismatch handoff={rev} master={ref_rev}", errors)

    md = (REPO_ROOT / "Master-Reference" / "MASTER_REFERENCE.md").read_text(encoding="utf-8")
    md_sha = hashlib.sha256(md.encode()).hexdigest()
    if md_sha != ref["document"].get("markdown_sha256"):
        fail("MASTER_REFERENCE.md sha256 does not match JSON markdown_sha256", errors)

    checks = handoff.get("checks") or {}
    if not isinstance(checks, dict):
        fail("checks must be an object", errors)
    else:
        for name, status in checks.items():
            if status not in CHECK_STATUS:
                fail(f"check {name!r} invalid status {status!r}", errors)

    report = handoff.get("report") or {}
    if report.get("status") not in (None, "pending", "complete", "blocked"):
        fail(f"report.status invalid: {report.get('status')}", errors)

    pending = [k for k, v in checks.items() if v == "pending"]
    failed = [k for k, v in checks.items() if v == "fail"]
    if failed:
        fail(f"checks failed: {', '.join(failed)}", errors)

    tid = handoff.get("task_id")
    for dep in handoff.get("depends_on") or []:
        if dep == "Kickoff":
            continue
        prior = (handoff.get("prior_tasks") or {}).get(dep, {})
        st = (prior.get("status") or "").lower()
        if st not in ("passed", "passed_with_open_decisions", "complete", "skipped") and dep not in (
            handoff.get("parallel_completed") or []
        ):
            fail(f"task {tid} depends on {dep} but prior_tasks does not show complete", errors)

    if errors:
        print("HANDOFF INVALID")
        for e in errors:
            print(f"  - {e}")
        if pending:
            print(f"pending_checks={pending}")
        return 1

    print("HANDOFF OK")
    print(f"task_id={tid} reference_revision={rev}")
    if pending:
        print(f"pending_checks={pending} (allowed while in progress)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())