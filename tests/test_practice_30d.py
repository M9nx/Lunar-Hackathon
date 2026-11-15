"""Second practice case: 30 days at 1 h. A real Malapert Sun-centre transition, traced to its raw Horizons row.

Practice input, labelled as such. Passing here says the engine reproduces the saved 30-day rows. It does not
make the case an eligible submission claim and it says nothing about terrain.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lunar_navigator.engine import (  # noqa: E402
    comparison_document,
    run_from_scenario,
    stream_comparison,
)

DATA = ROOT / "data"
SITE04 = ROOT / "tests/fixtures/site04_p02_practice_30d_scenario.json"
MALAPERT = ROOT / "tests/fixtures/malapert_practice_30d_scenario.json"
PACKAGE = ROOT / "web/review-candidate/cases/practice-30d"
WINDOW_S = 30 * 86400


def _scenario(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _raw_row(scenario: dict, body: str, stamp: str) -> str:
    folder = DATA / scenario["horizons_paths"][body]
    result = json.loads((folder / "response.json").read_text(encoding="utf-8"))["result"]
    matches = [line.strip() for line in result.splitlines() if line.strip().startswith(stamp)]
    assert len(matches) == 1, (stamp, matches)
    return matches[0]


def _merged(run: dict, lane: str) -> list[tuple[str, str, str]]:
    out: list[list[str]] = []
    for item in run["intervals"]:
        if item["lane"] != lane:
            continue
        if out and out[-1][2] == item["state"]:
            out[-1][1] = item["end_utc"]
        else:
            out.append([item["start_utc"], item["end_utc"], item["state"]])
    return [tuple(row) for row in out]


@unittest.skipUnless((DATA / "horizons/site04-p02-practice-30d").is_dir(), "local 30-day Horizons exports")
class Practice30Day(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scenario_a = _scenario(SITE04)
        cls.scenario_b = _scenario(MALAPERT)
        cls.a = run_from_scenario(cls.scenario_a, DATA, "test")
        cls.b = run_from_scenario(cls.scenario_b, DATA, "test")

    def test_grid_and_labels(self) -> None:
        for run in (self.a, self.b):
            self.assertEqual(len(run["samples"]), 721)
            self.assertEqual(run["samples"][0]["timestamp_utc"], "2025-01-01T00:00:00Z")
            self.assertEqual(run["samples"][-1]["timestamp_utc"], "2025-01-31T00:00:00Z")
            self.assertEqual(run["samples"][-1]["duration_seconds"], 0)
            self.assertTrue(run["practice"])
            self.assertTrue(run["eligible_for_submission_claim"])
            self.assertEqual(run["inputs"]["appendix_b_raw_sha256"], "not_in_appendix_b")
            for lane in ("sun", "earth", "both"):
                self.assertEqual(sum(run["elapsed_seconds"][lane].values()), WINDOW_S)

    def test_totals(self) -> None:
        self.assertEqual(self.a["elapsed_seconds"]["sun"], {"clear": 2592000, "blocked": 0, "unknown": 0})
        self.assertEqual(self.b["elapsed_seconds"]["sun"], {"clear": 1569600, "blocked": 1022400, "unknown": 0})
        self.assertEqual(self.a["elapsed_seconds"]["both"]["clear"], 1090800)
        self.assertEqual(self.b["elapsed_seconds"]["both"]["clear"], 1432800)

    def test_both_lane_never_exceeds_either_body(self) -> None:
        for run in (self.a, self.b):
            for sample in run["samples"]:
                sun, earth, both = sample["sun"]["state"], sample["earth"]["state"], sample["both"]["state"]
                if "blocked" in (sun, earth):
                    self.assertEqual(both, "blocked")
                elif "unknown" in (sun, earth):
                    self.assertEqual(both, "unknown")
                else:
                    self.assertEqual(both, "clear")

    def test_malapert_sun_transition_is_traced_to_the_raw_rows(self) -> None:
        samples = {s["timestamp_utc"]: s for s in self.b["samples"]}
        before, after = samples["2025-01-05T09:00:00Z"]["sun"], samples["2025-01-05T10:00:00Z"]["sun"]
        # Margin is elevation minus the 0° horizon, from the unrounded saved angle.
        self.assertLessEqual(before["margin_deg"], 0.0)
        self.assertGreater(after["margin_deg"], 0.0)
        self.assertEqual(before["state"], "blocked")
        self.assertEqual(after["state"], "clear")
        self.assertEqual(before["response_line"].strip(), _raw_row(self.scenario_b, "sun", "2025-Jan-05 09:00"))
        self.assertEqual(after["response_line"].strip(), _raw_row(self.scenario_b, "sun", "2025-Jan-05 10:00"))
        self.assertEqual(before["elevation_deg"], -0.011369)
        self.assertEqual(after["elevation_deg"], 0.021266)
        self.assertEqual(
            _merged(self.b, "sun"),
            [
                ("2025-01-01T00:00:00Z", "2025-01-05T10:00:00Z", "blocked"),
                ("2025-01-05T10:00:00Z", "2025-01-23T14:00:00Z", "clear"),
                ("2025-01-23T14:00:00Z", "2025-01-31T00:00:00Z", "blocked"),
            ],
        )
        # 2025-01-05T10:00Z through 2025-01-23T14:00Z is 436 h.
        self.assertEqual(436 * 3600, self.b["elapsed_seconds"]["sun"]["clear"])

    def test_site04_sun_is_clear_throughout_and_the_both_lane_follows_earth(self) -> None:
        self.assertEqual(_merged(self.a, "sun"), [("2025-01-01T00:00:00Z", "2025-01-31T00:00:00Z", "clear")])
        self.assertEqual(_merged(self.a, "both"), _merged(self.a, "earth"))
        self.assertIn(("2025-01-06T04:00:00Z", "2025-01-18T19:00:00Z", "clear"), _merged(self.a, "earth"))

    def test_stream_equals_batch_for_the_pair(self) -> None:
        events = list(stream_comparison(self.scenario_a, self.scenario_b, DATA, "test", batch_size_a=7, batch_size_b=11))
        complete = events[-1]
        self.assertEqual(complete["event"], "complete")
        self.assertFalse(complete["partial"])
        self.assertEqual(complete["shared_samples"], 721)
        batch = comparison_document(self.a, self.b, "test")
        self.assertEqual(complete["comparison"]["overlap"], batch["overlap"])
        self.assertEqual(complete["result_a"]["samples"], self.a["samples"])
        self.assertEqual(complete["result_b"]["samples"], self.b["samples"])
        self.assertEqual(complete["result_a"]["intervals"], self.a["intervals"])
        self.assertEqual(complete["result_b"]["intervals"], self.b["intervals"])
        self.assertEqual(complete["result_a"]["elapsed_seconds"], self.a["elapsed_seconds"])
        self.assertEqual(complete["result_b"]["elapsed_seconds"], self.b["elapsed_seconds"])

    @unittest.skipUnless(PACKAGE.is_dir(), "30-day case package not generated")
    def test_saved_package_matches_the_engine(self) -> None:
        saved = json.loads((PACKAGE / "comparison.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["overlap"], comparison_document(self.a, self.b, "test")["overlap"])
        self.assertTrue(saved["eligible_for_submission_claim"])
        for run, name in ((self.a, "site04-p02-practice-30d"), (self.b, "malapert-practice-30d")):
            on_disk = json.loads((PACKAGE / "runs" / f"{name}.json").read_text(encoding="utf-8"))
            self.assertEqual(on_disk["run_id"], run["run_id"])
            self.assertEqual(on_disk["samples"], run["samples"])
            self.assertEqual(on_disk["intervals"], run["intervals"])
            self.assertEqual(on_disk["elapsed_seconds"], run["elapsed_seconds"])


if __name__ == "__main__":
    unittest.main()
