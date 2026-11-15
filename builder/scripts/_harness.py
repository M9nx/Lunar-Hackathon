"""Shared helpers for lunar-builder harness scripts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

BUILDER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BUILDER_ROOT.parent
MASTER_REF = REPO_ROOT / "Master-Reference" / "MASTER_REFERENCE.json"
HANDOFF_PATH = BUILDER_ROOT / "agent_handoff.json"
TASK_LOG = BUILDER_ROOT / "docs" / "task-log.md"

# Evidence-backed pass. Only these earn verified-pass credit.
CREDIT_STATUSES = frozenset({"passed", "complete"})
# Work done, a decision still open. Satisfies dependencies; counted separately.
CONDITIONAL_STATUSES = frozenset({"passed_with_open_decisions"})
COMPLETE_STATUSES = CREDIT_STATUSES | CONDITIONAL_STATUSES
# "skipped" earns no credit and does not satisfy a dependency. Only an approved
# scope change in handoff["scope_changes"] can release a dependency.
_RANK = {"credit": 3, "conditional": 2, "other": 0}
CHECK_STATUS = frozenset({"pass", "fail", "pending"})
HANDOFF_REQUIRED_KEYS = (
    "handoff_version",
    "reference_revision",
    "task_id",
    "owner_role",
    "depends_on",
    "checks",
    "report",
)


def load_master_reference() -> dict[str, Any]:
    return json.loads(MASTER_REF.read_text(encoding="utf-8"))


def load_handoff(path: Path | None = None) -> dict[str, Any]:
    return json.loads((path or HANDOFF_PATH).read_text(encoding="utf-8"))


def schedule_tasks(ref: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    ref = ref or load_master_reference()
    return ref["schedule"]["tasks"]


def parse_task_log_statuses() -> dict[str, str]:
    """Parse docs/task-log.md table rows: | M0.3 | passed | ..."""
    if not TASK_LOG.is_file():
        return {}
    text = TASK_LOG.read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for line in text.splitlines():
        if not line.startswith("|") or line.startswith("| Task"):
            continue
        parts = [p.strip() for p in line.split("|") if p.strip()]
        if len(parts) < 2:
            continue
        task_id = parts[0].replace("*", "")
        if not re.match(r"^(M\d+\.\d+|Rest)$", task_id):
            continue
        out[task_id] = parts[1].lower().replace(" ", "_")
    return out


def approved_descopes(handoff: dict[str, Any] | None = None) -> set[str]:
    """Task IDs released by an explicit approved scope change (no completion credit)."""
    handoff = handoff or load_handoff()
    out: set[str] = set()
    for change in handoff.get("scope_changes") or []:
        if (
            (change.get("status") or "").lower() == "approved"
            and change.get("approved_by")
            and change.get("approved_utc")
        ):
            out.update(change.get("tasks") or [])
    return out


def _class_of(status: str) -> str:
    status = (status or "").lower()
    if status in CREDIT_STATUSES:
        return "credit"
    if status in CONDITIONAL_STATUSES:
        return "conditional"
    return "other"


def recorded_statuses(handoff: dict[str, Any] | None = None) -> dict[str, str]:
    """Recorded status per task. If handoff and task log disagree, keep the less complete one."""
    handoff = handoff or load_handoff()
    recorded: dict[str, str] = {}
    sources = [
        {tid: (m.get("status") or "").lower() for tid, m in (handoff.get("prior_tasks") or {}).items()},
        parse_task_log_statuses(),
    ]
    for source in sources:
        for tid, status in source.items():
            if tid not in recorded or _RANK[_class_of(status)] < _RANK[_class_of(recorded[tid])]:
                recorded[tid] = status
    return recorded


def effective_statuses(handoff: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """Per scheduled task: recorded status, effective class and dependency check.

    class is one of: verified | conditional | invalid_credit | descoped | blocked |
    in_progress | skipped | planned. invalid_credit means the task was recorded as done
    while a prerequisite is not satisfied; it earns no credit.
    """
    handoff = handoff or load_handoff()
    recorded = recorded_statuses(handoff)
    descoped = approved_descopes(handoff)
    out: dict[str, dict[str, Any]] = {}
    satisfied: set[str] = {"Kickoff"}
    for task in schedule_tasks():
        tid = task["task_id"]
        status = recorded.get(tid, "planned")
        cls = _class_of(status)
        unmet = [d for d in task.get("depends_on") or [] if d not in satisfied]
        if tid in descoped:
            kind = "descoped"
        elif cls != "other" and unmet:
            kind = "invalid_credit"
        elif cls == "credit":
            kind = "verified"
        elif cls == "conditional":
            kind = "conditional"
        elif status in ("blocked", "in_progress", "skipped"):
            kind = status
        else:
            kind = "planned"
        if kind in ("verified", "conditional", "descoped"):
            satisfied.add(tid)
        out[tid] = {"recorded": status, "class": kind, "unmet": unmet}
    return out


def completed_tasks(handoff: dict[str, Any] | None = None) -> set[str]:
    """Tasks that satisfy dependencies (verified, conditional, or approved descope)."""
    eff = effective_statuses(handoff)
    return {"Kickoff"} | {t for t, v in eff.items() if v["class"] in ("verified", "conditional", "descoped")}


def deps_satisfied(task: dict[str, Any], done: set[str]) -> bool:
    return all(dep in done for dep in task.get("depends_on") or [])


def next_ready_tasks(
    handoff: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], set[str]]:
    handoff = handoff or load_handoff()
    done = completed_tasks(handoff)
    current = handoff.get("task_id")
    ready: list[dict[str, Any]] = []
    for task in schedule_tasks():
        tid = task["task_id"]
        if tid in done:
            continue
        if not deps_satisfied(task, done):
            continue
        ready.append(task)
    # If current task still active (not in done), prefer it first
    if current and current not in done:
        ready.sort(key=lambda t: (0 if t["task_id"] == current else 1, t["task_id"]))
    return ready, done


def checks_for_milestone(task_id: str, ref: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Subset of §9 checks relevant to a milestone gate (heuristic)."""
    ref = ref or load_master_reference()
    all_checks = ref.get("checks") or []
    gate = task_id.split(".")[0] if "." in task_id else task_id
    slices: dict[str, slice] = {
        "M0": slice(0, 2),
        "M1": slice(0, 8),
        "M2": slice(0, 10),
        "M3": slice(10, 14),
        "M4": slice(8, 12),
        "M5": slice(0, 16),
        "M6": slice(12, 17),
    }
    sl = slices.get(gate, slice(0, len(all_checks)))
    return all_checks[sl]


def data_root(handoff: dict[str, Any] | None = None) -> Path:
    handoff = handoff or load_handoff()
    rel = handoff.get("data_root") or "data"
    return (REPO_ROOT / rel).resolve()