#!/usr/bin/env python3
"""Ensure live handoff (builder/) is not mirrored into Master Reference as operational state."""

from __future__ import annotations

import json
import sys
from pathlib import Path

BUILDER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BUILDER_ROOT.parent
LIVE = BUILDER_ROOT / "agent_handoff.json"
MASTER = REPO_ROOT / "Master-Reference" / "MASTER_REFERENCE.json"


def main() -> int:
    live = json.loads(LIVE.read_text(encoding="utf-8"))
    ref = json.loads(MASTER.read_text(encoding="utf-8"))
    embedded = ref.get("agent_handoff") or {}

    if embedded.get("example_only") is not True:
        print("FAIL embedded agent_handoff must set example_only: true")
        return 1

    if embedded.get("task_id") == live.get("task_id") and embedded.get("report") == live.get("report"):
        print("FAIL embedded handoff matches live task_id and report — use example template only")
        return 1

    print("HANDOFF SEPARATION OK (live=builder/agent_handoff.json, master=example)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())