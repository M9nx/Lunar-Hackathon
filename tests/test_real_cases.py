"""The expanded real cases: four outcomes and their crossings traced to saved Horizons rows."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

import real_case_trace as trace  # noqa: E402

NEEDED = [ROOT / "data" / "horizons" / "site04-p02-practice", ROOT / "data" / "horizons" / "malapert-practice"]


@unittest.skipUnless(all(p.is_dir() for p in NEEDED), "local Horizons exports (data/horizons is not in git)")
class RealCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = trace.trace()  # raises AssertionError on any row that disagrees with the saved file

    def test_four_outcomes_exist_with_known_spans(self) -> None:
        by_label = {case["label"]: case for case in self.result["cases"]}
        self.assertEqual(set(by_label), {"Sun-only", "Earth-only", "Both-clear (Malapert)", "Both-clear (Site04)"})
        self.assertEqual(by_label["Earth-only"]["seconds"], 174600)
        self.assertEqual(by_label["Sun-only"]["seconds"], 270900)
        for case in self.result["cases"]:
            self.assertGreater(case["rows_checked"], 100)

    def test_crossings_are_traced_on_both_sides(self) -> None:
        self.assertGreaterEqual(len(self.result["crossings"]), 3)
        for item in self.result["crossings"]:
            before, after = item["rows"]
            self.assertEqual(before["state"], item["from"])
            self.assertEqual(after["state"], item["to"])
            self.assertLess(before["utc"], after["utc"])

    def test_six_hour_scans_cover_all_four_outcomes(self) -> None:
        both = {}
        for scan in self.result["scans"]:
            for name, seconds in scan["outcome_seconds"].items():
                both[name] = both.get(name, 0) + seconds
            self.assertEqual(sum(scan["outcome_seconds"].values()), 90 * 86400)
            self.assertGreater(scan["both_crossings"], 0)
        for outcome in ("both_clear", "sun_only", "earth_only", "neither"):
            self.assertGreater(both[outcome], 0, outcome)

    def test_committed_trace_document_is_current(self) -> None:
        self.assertEqual((ROOT / "docs" / "real-case-trace.md").read_text(encoding="utf-8"), trace.markdown(self.result))


if __name__ == "__main__":
    unittest.main()
