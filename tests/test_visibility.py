"""§9 acceptance tests for centre-ray classification."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lunar_navigator.visibility import (  # noqa: E402
    REJECT_BARY_ID,
    VALID_EARTH_ID,
    VALID_SUN_ID,
    both_lane,
    classify_margin,
    validate_body_id,
)


class BaselineSigns(unittest.TestCase):
    def test_geometric_clear_blocked(self) -> None:
        for elev, expected in ((0.5, "clear"), (0.0, "blocked"), (-0.5, "blocked")):
            s = classify_margin(elev, 0.0)
            self.assertEqual(s.state, expected)
            self.assertIsNotNone(s.margin_deg)

    def test_missing_ephemeris_unknown(self) -> None:
        s = classify_margin(None, 0.0)
        self.assertEqual(s.state, "unknown")
        self.assertEqual(s.reason, "missing_ephemeris")


class RidgeAndTerrain(unittest.TestCase):
    def test_ridge_blocked(self) -> None:
        s = classify_margin(0.8, 1.2, horizon_mode="terrain")
        self.assertEqual(s.state, "blocked")
        self.assertAlmostEqual(s.margin_deg or 0, -0.4)

    def test_terrain_gap_unknown(self) -> None:
        s = classify_margin(0.8, None, horizon_mode="terrain")
        self.assertEqual(s.state, "unknown")


class BodyIds(unittest.TestCase):
    def test_centre_targets(self) -> None:
        self.assertTrue(validate_body_id("sun", VALID_SUN_ID))
        self.assertTrue(validate_body_id("earth", VALID_EARTH_ID))
        self.assertFalse(validate_body_id("earth", REJECT_BARY_ID))


class BothLaneGaps(unittest.TestCase):
    def test_blocked_beats_unknown(self) -> None:
        self.assertEqual(both_lane("unknown", "blocked"), "blocked")

    def test_unknown_when_no_blocked(self) -> None:
        self.assertEqual(both_lane("clear", "unknown"), "unknown")


class SyntheticHourFixture(unittest.TestCase):
    """Worked comparison totals from Master Reference examples."""

    @classmethod
    def setUpClass(cls) -> None:
        ref = json.loads((ROOT / "Master-Reference" / "MASTER_REFERENCE.json").read_text())
        cls.duration = ref["examples"]["synthetic_hour"]["duration_seconds"]

    def test_geometric_both_totals(self) -> None:
        both = self.duration["both_geometric_0deg"]
        self.assertEqual(both["clear"], 2700)
        self.assertEqual(both["blocked"], 900)


if __name__ == "__main__":
    unittest.main()