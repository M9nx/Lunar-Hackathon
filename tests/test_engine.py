"""Centre-ray engine: synthetic hour, saved practice rows, and replay package."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lunar_navigator.engine import (  # noqa: E402
    geometric_run_from_rows,
    run_from_scenario,
)
from lunar_navigator.horizons_table import parse_response_line  # noqa: E402

DATA = ROOT / "data"
SITE_A = DATA / "horizons" / "site04-p02-practice"
PACKAGE = ROOT / "web" / "replay"


def _row(utc, sun_el, earth_el, sun_az=90.0, earth_az=150.0):
    return {
        "timestamp_utc": utc,
        "sun_azimuth_deg": sun_az,
        "sun_elevation_deg": sun_el,
        "earth_azimuth_deg": earth_az,
        "earth_elevation_deg": earth_el,
        "sun_source_ref": f"synthetic# {utc}",
        "earth_source_ref": f"synthetic# {utc}",
        "sun_response_line": None,
        "earth_response_line": None,
    }


class SyntheticHour(unittest.TestCase):
    def test_geometric_totals_and_terminal_sample(self) -> None:
        rows = [
            _row("2025-01-01T00:00:00Z", 0.8, 0.4),
            _row("2025-01-01T00:15:00Z", 0.9, 0.3),
            _row("2025-01-01T00:30:00Z", 0.7, -0.2),
            _row("2025-01-01T00:45:00Z", 0.6, 0.4),
            _row("2025-01-01T01:00:00Z", 0.7, 0.5),
        ]
        result = geometric_run_from_rows(
            site_id="synthetic-hour",
            observer={"longitude_east_deg": 0, "latitude_deg": 0, "reference_altitude_km": 0},
            start_utc=rows[0]["timestamp_utc"],
            end_utc=rows[-1]["timestamp_utc"],
            step_seconds=900,
            rows=rows,
            run_id="synthetic-hour",
            code_revision="test",
            practice=True,
            eligible_for_submission_claim=False,
            inputs={},
            limitations=["synthetic"],
        )
        both = result["elapsed_seconds"]["both"]
        self.assertEqual(both, {"clear": 2700, "blocked": 900, "unknown": 0})
        self.assertEqual(result["samples"][-1]["duration_seconds"], 0)
        self.assertEqual(sum(sample["duration_seconds"] for sample in result["samples"]), 3600)
        self.assertEqual(result["labels"]["both"], "Both centres clear")

    def test_missing_right_endpoint_is_unknown(self) -> None:
        rows = [
            _row("2025-01-01T00:00:00Z", 0.8, 0.4),
            _row("2025-01-01T00:15:00Z", None, 0.4),
        ]
        result = geometric_run_from_rows(
            site_id="missing-right",
            observer={"longitude_east_deg": 0, "latitude_deg": 0, "reference_altitude_km": 0},
            start_utc=rows[0]["timestamp_utc"],
            end_utc=rows[-1]["timestamp_utc"],
            step_seconds=900,
            rows=rows,
            run_id="missing-right",
            code_revision="test",
            practice=True,
            eligible_for_submission_claim=False,
            inputs={},
            limitations=["synthetic"],
        )
        self.assertEqual(result["elapsed_seconds"]["sun"], {"clear": 0, "blocked": 0, "unknown": 900})
        self.assertEqual(result["elapsed_seconds"]["earth"], {"clear": 900, "blocked": 0, "unknown": 0})
        self.assertEqual(result["elapsed_seconds"]["both"], {"clear": 0, "blocked": 0, "unknown": 900})
        opening = result["samples"][0]
        self.assertEqual(opening["sun"]["state"], "unknown")
        self.assertEqual(opening["sun"]["reason"], "missing_right_endpoint")
        self.assertAlmostEqual(opening["sun"]["elevation_deg"], 0.8)
        self.assertEqual(opening["earth"]["state"], "clear")
        self.assertEqual(opening["both"]["state"], "unknown")
        self.assertEqual(result["samples"][-1]["duration_seconds"], 0)
        self.assertEqual(result["intervals"][0]["lane"], "sun")
        self.assertEqual(result["intervals"][0]["state"], "unknown")


class ResponseLine(unittest.TestCase):
    def test_horizons_stamp(self) -> None:
        parsed = parse_response_line(" 2025-Jan-01 00:00,*, , 318.623526,     1.683925,")
        self.assertIsNotNone(parsed)
        utc, azimuth, elevation = parsed
        self.assertEqual(utc, "2025-01-01T00:00:00Z")
        self.assertAlmostEqual(azimuth, 318.623526)
        self.assertAlmostEqual(elevation, 1.683925)


@unittest.skipUnless(SITE_A.is_dir(), "local Horizons practice bundle")
class PracticeSiteA(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        scenario = json.loads((ROOT / "tests/fixtures/site04_p02_practice_scenario.json").read_text())
        cls.result = run_from_scenario(scenario, DATA, "test")

    def test_traced_rows_match_saved_angles(self) -> None:
        sun, earth = self.result["traces"]
        self.assertEqual(sun["timestamp_utc"], "2025-01-01T00:00:00Z")
        self.assertAlmostEqual(sun["elevation_deg"], 1.683925)
        self.assertEqual(sun["state"], "clear")
        self.assertIn("318.623526", sun["response_line"])
        self.assertAlmostEqual(earth["elevation_deg"], -6.503228)
        self.assertEqual(earth["state"], "blocked")
        self.assertIn("-6.503228", earth["response_line"].replace(" ", ""))
        self.assertEqual(self.result["samples"][0]["both"]["state"], "blocked")

    def test_duration_identity(self) -> None:
        for lane, totals in self.result["elapsed_seconds"].items():
            self.assertEqual(sum(totals.values()), 172800, lane)
        self.assertEqual(self.result["elapsed_seconds"]["sun"]["clear"], 172800)
        self.assertEqual(self.result["elapsed_seconds"]["earth"]["blocked"], 172800)
        self.assertEqual(self.result["elapsed_seconds"]["both"]["unknown"], 0)
        self.assertTrue(self.result["eligible_for_submission_claim"])
        self.assertEqual(self.result["inputs"]["appendix_b_raw_sha256"], "open_mismatch_preserved")


@unittest.skipUnless((PACKAGE / "comparison.json").is_file(), "replay package not built")
class ReplayPackage(unittest.TestCase):
    def test_package_files_and_offline_shell(self) -> None:
        comparison = json.loads((PACKAGE / "comparison.json").read_text())
        self.assertTrue(comparison["comparable"])
        self.assertTrue(comparison["eligible_for_submission_claim"])
        self.assertEqual(comparison["overlap"]["sun_centre_clear_seconds"]["delta_b_minus_a"], -172800)
        html = (PACKAGE / "index.html").read_text(encoding="utf-8")
        script = (PACKAGE / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("cdn.", html.lower() + script.lower())
        self.assertIn("Sun-centre clearance", html)
        for run in comparison["runs"]:
            path = PACKAGE / run["file"]
            payload = json.loads(path.read_text())
            self.assertEqual(payload["run_id"], run["run_id"])
            self.assertEqual(payload["schema_version"], "run-result-1")


def _write_export(folder: Path, *, target_name: str, target_id: int, azimuth: float, elevation: float) -> None:
    folder.mkdir(parents=True)
    stamps = (
        ("2025-Jan-01 00:00", "2025-01-01T00:00:00Z", azimuth, elevation),
        ("2025-Jan-01 00:15", "2025-01-01T00:15:00Z", azimuth + 1.0, elevation),
    )
    data_lines = [f" {stamp},*, , {az:.6f}, {el:.6f}," for stamp, _utc, az, el in stamps]
    result = (
        f"Target body name: {target_name} ({target_id}) {{source: DE441}}\n"
        "Center body name: Moon (301) {source: DE441}\n"
        "Center geodetic : 203.5614, -89.7812, 1.7389 {E-lon(deg),Lat(deg),Alt(km)}\n"
        "Center pole/equ : MEAN_ME (high precision) {East-longitude positive}\n"
        "Atmos refraction: NO (AIRLESS)\n"
        " Date__(UT)__HR:MN, , ,Azi_(a-app), Elev_(a-app),\n"
        "$$SOE\n"
        + "\n".join(data_lines)
        + "\n$$EOE\n"
    )
    response = folder / "response.json"
    csv_path = folder / "angles.csv"
    response.write_text(json.dumps({"result": result}), encoding="utf-8")
    csv_body = "timestamp_utc,azimuth_deg,elevation_deg,angle_status\n" + "".join(
        f"{utc},{az:.6f},{el:.6f},available\n" for _stamp, utc, az, el in stamps
    )
    csv_path.write_text(csv_body, encoding="utf-8")
    provenance = {
        "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "raw_sha256": hashlib.sha256(response.read_bytes()).hexdigest(),
    }
    (folder / "provenance.json").write_text(json.dumps(provenance), encoding="utf-8")


def _two_sample_scenario(sun_rel: str, earth_rel: str) -> dict:
    return {
        "status": "practice",
        "site_id": "header-check",
        "observer": {
            "longitude_east_deg": -156.4386,
            "latitude_deg": -89.7812,
            "reference_altitude_km": 1.738902,
            "center_body_id": 301,
        },
        "start_utc": "2025-01-01T00:00:00Z",
        "end_utc": "2025-01-01T00:15:00Z",
        "step_seconds": 900,
        "observer_frame": "MEAN_ME",
        "angle_convention": "airless_apparent",
        "horizons_paths": {"sun": sun_rel, "earth": earth_rel},
        "eligible_for_submission_claim": False,
    }


class ResponseCaseIdentity(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.sun_rel = "horizons/sun"
        self.earth_rel = "horizons/earth"
        _write_export(
            self.root / self.sun_rel,
            target_name="Sun",
            target_id=10,
            azimuth=318.623526,
            elevation=1.683925,
        )
        _write_export(
            self.root / self.earth_rel,
            target_name="Earth",
            target_id=399,
            azimuth=151.799812,
            elevation=-6.503228,
        )
        self.scenario = _two_sample_scenario(self.sun_rel, self.earth_rel)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_matching_headers_keep_each_body(self) -> None:
        result = run_from_scenario(self.scenario, self.root, "test")
        sun, earth = result["traces"]
        self.assertAlmostEqual(sun["elevation_deg"], 1.683925)
        self.assertAlmostEqual(earth["elevation_deg"], -6.503228)
        self.assertEqual(result["elapsed_seconds"]["both"]["clear"], 0)
        self.assertEqual(result["elapsed_seconds"]["both"]["blocked"], 900)

    def test_swapped_sun_and_earth_files_are_rejected(self) -> None:
        swapped = json.loads(json.dumps(self.scenario))
        swapped["horizons_paths"] = {"sun": self.earth_rel, "earth": self.sun_rel}
        with self.assertRaises(ValueError) as caught:
            run_from_scenario(swapped, self.root, "test")
        message = str(caught.exception)
        self.assertIn("sun", message)
        self.assertIn("399", message)

    def _replace_sun_header(self, old: str, new: str) -> None:
        folder = self.root / self.sun_rel
        path = folder / "response.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["result"] = payload["result"].replace(old, new)
        path.write_text(json.dumps(payload), encoding="utf-8")
        provenance_path = folder / "provenance.json"
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
        provenance["raw_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        provenance_path.write_text(json.dumps(provenance), encoding="utf-8")

    def test_observer_frame_mismatch_is_rejected(self) -> None:
        self._replace_sun_header("MEAN_ME", "MOON_PA")
        with self.assertRaises(ValueError) as caught:
            run_from_scenario(self.scenario, self.root, "test")
        message = str(caught.exception)
        self.assertIn("MOON_PA", message)
        self.assertIn("frame", message)

    def test_refracted_angle_convention_is_rejected(self) -> None:
        self._replace_sun_header("NO (AIRLESS)", "YES")
        self._replace_sun_header("Azi_(a-app)", "Azi_(a-appr)")
        self._replace_sun_header("Elev_(a-app)", "Elev_(a-appr)")
        with self.assertRaises(ValueError) as caught:
            run_from_scenario(self.scenario, self.root, "test")
        self.assertIn("angle convention", str(caught.exception))

    def test_observer_longitude_must_match_header(self) -> None:
        shifted = json.loads(json.dumps(self.scenario))
        shifted["observer"]["longitude_east_deg"] = -10.0
        with self.assertRaises(ValueError) as caught:
            run_from_scenario(shifted, self.root, "test")
        self.assertIn("longitude", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
