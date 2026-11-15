"""Task accounting: a skipped task earns no credit and an unmet prerequisite voids a pass."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "builder" / "scripts"))

import _harness  # noqa: E402


def _classes(prior: dict, log: dict, scope_changes: list | None = None) -> dict:
    handoff = {"prior_tasks": {k: {"status": v} for k, v in prior.items()}, "scope_changes": scope_changes or []}
    with mock.patch.object(_harness, "parse_task_log_statuses", return_value=log):
        return {t: v["class"] for t, v in _harness.effective_statuses(handoff).items()}


class DependencyAccounting(unittest.TestCase):
    def test_skipped_earns_no_credit_and_blocks_dependants(self) -> None:
        classes = _classes({"M0.1": "passed"}, {"M0.2": "skipped", "M0.3": "passed"})
        self.assertEqual(classes["M0.1"], "verified")
        self.assertEqual(classes["M0.2"], "skipped")
        self.assertEqual(classes["M0.3"], "invalid_credit")

    def test_pass_with_unmet_prerequisite_is_invalid_credit(self) -> None:
        classes = _classes({"M3.4": "passed_with_open_decisions", "M2.5": "blocked"}, {})
        self.assertEqual(classes["M3.4"], "invalid_credit")

    def test_open_decisions_count_as_conditional_not_verified(self) -> None:
        classes = _classes({"M0.1": "passed_with_open_decisions"}, {})
        self.assertEqual(classes["M0.1"], "conditional")

    def test_conflicting_records_keep_the_less_complete_status(self) -> None:
        classes = _classes({"M0.1": "passed"}, {"M0.1": "blocked"})
        self.assertEqual(classes["M0.1"], "blocked")

    def test_only_an_approved_scope_change_releases_a_dependency(self) -> None:
        base = {"M2.5": "blocked", "M3.4": "passed_with_open_decisions"}
        proposed = [{"status": "proposed", "tasks": ["M2.5"], "approved_by": None, "approved_utc": None}]
        self.assertEqual(_classes(base, {}, proposed)["M2.5"], "blocked")
        self.assertEqual(_classes(base, {}, proposed)["M3.4"], "invalid_credit")
        approved = [{"status": "approved", "tasks": ["M2.5"], "approved_by": "Lead+Science", "approved_utc": "2026-11-15T00:00:00Z"}]
        released = _classes({"M0.1": "passed", "M1.5": "passed", **base}, {}, approved)
        self.assertEqual(released["M2.5"], "descoped")

    def test_descope_is_not_verified_credit(self) -> None:
        approved = [{"status": "approved", "tasks": ["M2.5"], "approved_by": "Lead", "approved_utc": "2026-11-15T00:00:00Z"}]
        handoff = {"prior_tasks": {}, "scope_changes": approved}
        with mock.patch.object(_harness, "parse_task_log_statuses", return_value={}):
            self.assertNotIn("M2.5", {t for t, v in _harness.effective_statuses(handoff).items() if v["class"] == "verified"})

    def test_repository_records_have_no_invalid_credit(self) -> None:
        eff = _harness.effective_statuses()
        bad = {t: v for t, v in eff.items() if v["class"] == "invalid_credit"}
        self.assertEqual(bad, {})
        self.assertNotEqual(eff["M5.1"]["class"], "verified")
        self.assertNotEqual(eff["M3.4"]["class"], "verified")


if __name__ == "__main__":
    unittest.main()
