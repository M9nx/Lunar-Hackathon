"""Batch and streaming runs share one classification path."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lunar_navigator.engine import (  # noqa: E402
    comparison_document,
    run_from_scenario,
    stream_comparison,
    stream_scenario,
)
from lunar_navigator.live_server import make_server  # noqa: E402

DATA = ROOT / "data"
SITE04 = ROOT / "tests/fixtures/site04_p02_practice_scenario.json"
SITE04_6H = ROOT / "tests/fixtures/site04_p02_practice_6h_scenario.json"
MALAPERT = ROOT / "tests/fixtures/malapert_practice_scenario.json"


def _events(scenario: dict, data_root: Path, **kwargs) -> list[dict]:
    return list(stream_scenario(scenario, data_root, "test", **kwargs))


def _comparable(result: dict) -> dict:
    return {
        "samples": result["samples"],
        "intervals": result["intervals"],
        "elapsed_seconds": result["elapsed_seconds"],
        "run_id": result["run_id"],
    }


@unittest.skipUnless((DATA / "horizons").is_dir(), "local Horizons practice bundle")
class PracticeBatchAndStream(unittest.TestCase):
    def test_both_practice_sites_and_a_shorter_window(self) -> None:
        site04 = json.loads(SITE04.read_text(encoding="utf-8"))
        malapert = json.loads(MALAPERT.read_text(encoding="utf-8"))
        short = json.loads(SITE04_6H.read_text(encoding="utf-8"))
        full = run_from_scenario(site04, DATA, "test")
        other = run_from_scenario(malapert, DATA, "test")
        window = run_from_scenario(short, DATA, "test")
        self.assertEqual(full["elapsed_seconds"]["sun"]["clear"], 172800)
        self.assertEqual(other["elapsed_seconds"]["sun"]["clear"], 0)
        self.assertEqual(other["elapsed_seconds"]["both"]["blocked"], 172800)
        self.assertEqual(window["samples"][-1]["duration_seconds"], 0)
        self.assertEqual(sum(window["elapsed_seconds"]["sun"].values()), 6 * 3600)
        self.assertNotEqual(window["run_id"], full["run_id"])
        self.assertFalse(full["eligible_for_submission_claim"])
        self.assertIn("Terrain mode is Unknown", " ".join(full["limitations"]))

    def test_stream_matches_batch_and_yields_a_batch_first(self) -> None:
        scenario = json.loads(SITE04_6H.read_text(encoding="utf-8"))
        batch = run_from_scenario(scenario, DATA, "test")
        generator = stream_scenario(scenario, DATA, "test", batch_size=2)
        seen = []
        first_batch = None
        while True:
            event = next(generator)
            seen.append(event["event"])
            if event["event"] == "batch":
                first_batch = event
                break
        self.assertEqual(seen, ["stage", "metadata", "batch"])
        self.assertEqual(first_batch["batch_index"], 0)
        self.assertEqual(len(first_batch["samples"]), 2)
        self.assertLess(first_batch["samples_emitted"], len(batch["samples"]))
        rest = list(generator)
        self.assertEqual(rest[-1]["event"], "complete")
        assembled = list(first_batch["samples"])
        for event in rest:
            if event["event"] == "batch":
                assembled.extend(event["samples"])
        complete = rest[-1]["result"]
        self.assertEqual(assembled, complete["samples"])
        self.assertEqual(_comparable(complete), _comparable(batch))
        for left, right in zip(complete["samples"], batch["samples"]):
            self.assertEqual(left["sun"]["source_ref"], right["sun"]["source_ref"])
            self.assertEqual(left["earth"]["source_ref"], right["earth"]["source_ref"])
            self.assertEqual(left["sun"]["state"], right["sun"]["state"])
            self.assertEqual(left["earth"]["state"], right["earth"]["state"])

    def test_rejected_window_names_the_missing_time(self) -> None:
        scenario = json.loads(SITE04.read_text(encoding="utf-8"))
        scenario["end_utc"] = "2025-02-01T00:00:00Z"
        with self.assertRaises(ValueError) as caught:
            run_from_scenario(scenario, DATA, "test")
        self.assertIn("2025-02-01T00:00:00Z", str(caught.exception))
        self.assertIn("grid", str(caught.exception))


class StreamControl(unittest.TestCase):
    def _export(self, root: Path, body: str, target_id: int, rows: list[tuple[str, str, float | None, float | None]]) -> None:
        folder = root / "horizons" / body
        folder.mkdir(parents=True)
        lines = []
        csv_lines = ["timestamp_utc,azimuth_deg,elevation_deg,angle_status\n"]
        for stamp, utc, azimuth, elevation in rows:
            if azimuth is None or elevation is None:
                lines.append(f" {stamp},*, ,       n.a.,        n.a.,")
                csv_lines.append(f"{utc},,,missing\n")
            else:
                lines.append(f" {stamp},*, , {azimuth:.6f}, {elevation:.6f},")
                csv_lines.append(f"{utc},{azimuth},{elevation},available\n")
        result = (
            f"Target body name: {body} ({target_id}) {{source: DE441}}\n"
            "Center body name: Moon (301) {source: DE441}\n"
            "Center geodetic : 203.5614, -89.7812, 1.7389 {E-lon(deg),Lat(deg),Alt(km)}\n"
            "Center pole/equ : MEAN_ME (high precision) {East-longitude positive}\n"
            "Atmos refraction: NO (AIRLESS)\n"
            " Date__(UT)__HR:MN, , ,Azi_(a-app), Elev_(a-app),\n"
            "$$SOE\n"
            + "\n".join(lines)
            + "\n$$EOE\n"
        )
        response = folder / "response.json"
        csv_path = folder / "angles.csv"
        response.write_text(json.dumps({"result": result}), encoding="utf-8")
        csv_path.write_text("".join(csv_lines), encoding="utf-8")
        import hashlib

        provenance = {
            "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
            "raw_sha256": hashlib.sha256(response.read_bytes()).hexdigest(),
        }
        (folder / "provenance.json").write_text(json.dumps(provenance), encoding="utf-8")

    def _scenario(self) -> dict:
        return {
            "status": "practice",
            "site_id": "boundary",
            "observer": {
                "longitude_east_deg": -156.4386,
                "latitude_deg": -89.7812,
                "reference_altitude_km": 1.738902,
                "center_body_id": 301,
            },
            "start_utc": "2025-01-01T00:00:00Z",
            "end_utc": "2025-01-01T00:45:00Z",
            "step_seconds": 900,
            "observer_frame": "MEAN_ME",
            "angle_convention": "airless_apparent",
            "horizons_paths": {"sun": "horizons/sun", "earth": "horizons/earth"},
            "eligible_for_submission_claim": False,
        }

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        rows = [
            ("2025-Jan-01 00:00", "2025-01-01T00:00:00Z", 10.0, 1.0),
            ("2025-Jan-01 00:15", "2025-01-01T00:15:00Z", 11.0, 0.5),
            ("2025-Jan-01 00:30", "2025-01-01T00:30:00Z", None, None),
            ("2025-Jan-01 00:45", "2025-01-01T00:45:00Z", 12.0, -0.2),
        ]
        self._export(self.root, "sun", 10, rows)
        earth = [("2025-Jan-01 00:00", "2025-01-01T00:00:00Z", 20.0, -1.0),
                 ("2025-Jan-01 00:15", "2025-01-01T00:15:00Z", 21.0, -1.1),
                 ("2025-Jan-01 00:30", "2025-01-01T00:30:00Z", 22.0, -1.2),
                 ("2025-Jan-01 00:45", "2025-01-01T00:45:00Z", 23.0, -1.3)]
        self._export(self.root, "earth", 399, earth)
        self.scenario = self._scenario()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_batch_boundary_keeps_unknown_and_the_terminal_sample(self) -> None:
        batch = run_from_scenario(self.scenario, self.root, "test")
        events = _events(self.scenario, self.root, batch_size=1)
        batches = [event for event in events if event["event"] == "batch"]
        self.assertEqual(len(batches), 4)
        # The 00:15 sample needs the missing 00:30 row, and they are in different batches.
        self.assertEqual(batches[1]["samples"][0]["timestamp_utc"], "2025-01-01T00:15:00Z")
        self.assertEqual(batches[1]["samples"][0]["sun"]["state"], "unknown")
        self.assertEqual(batches[1]["samples"][0]["sun"]["reason"], "missing_right_endpoint")
        self.assertEqual(batches[1]["samples"][0]["sun"]["elevation_deg"], 0.5)
        self.assertEqual(batches[2]["samples"][0]["sun"]["state"], "unknown")
        self.assertEqual(batches[3]["samples"][0]["duration_seconds"], 0)
        complete = events[-1]["result"]
        self.assertEqual(complete["samples"], batch["samples"])
        self.assertEqual(complete["intervals"], batch["intervals"])
        self.assertEqual(complete["elapsed_seconds"], batch["elapsed_seconds"])

    def test_cancel_restart_and_failure_leave_partial_runs(self) -> None:
        cancel = threading.Event()
        first = stream_scenario(self.scenario, self.root, "test", batch_size=1, cancel=cancel)
        self.assertEqual(next(first)["event"], "stage")
        metadata = next(first)
        self.assertEqual(metadata["event"], "metadata")
        batch = next(first)
        self.assertEqual(batch["event"], "batch")
        cancel.set()
        cancelled = next(first)
        self.assertEqual(cancelled["event"], "cancelled")
        self.assertFalse(cancelled["complete"])
        self.assertLess(cancelled["samples_emitted"], metadata["sample_count"])

        second = _events(self.scenario, self.root, batch_size=1)
        self.assertNotEqual(second[0]["run_id"], metadata["run_id"])
        self.assertEqual(second[-1]["event"], "complete")

        failed = _events(self.scenario, self.root, batch_size=1, fail_after_batches=1)
        self.assertEqual(failed[-1]["event"], "error")
        self.assertFalse(failed[-1]["complete"])
        self.assertEqual(failed[-1]["samples_emitted"], 1)
        self.assertNotIn("complete", [event["event"] for event in failed])


class LiveServer(unittest.TestCase):
    def setUp(self) -> None:
        self.server = make_server(ROOT, DATA, "test", 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self) -> None:
        self.server.shutdown()
        self.thread.join(timeout=3)

    def _post(self, path: str, payload: dict) -> dict:
        request = urllib.request.Request(
            self.base + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))

    def _read_events(self, run_id: str) -> list[dict]:
        with urllib.request.urlopen(self.base + f"/api/runs/{run_id}/events") as response:
            body = response.read().decode("utf-8")
        return [json.loads(line) for line in body.splitlines() if line.strip()]

    @unittest.skipUnless((DATA / "horizons").is_dir(), "local Horizons practice bundle")
    def test_http_cancel_and_failure_keep_distinct_run_ids(self) -> None:
        started = self._post("/api/runs", {"scenario": "site04-6h", "batch_size": 2, "pause_seconds": 1})
        run_id = started["run_id"]
        events = []
        with urllib.request.urlopen(self.base + f"/api/runs/{run_id}/events") as response:
            while True:
                line = response.readline()
                if not line:
                    break
                event = json.loads(line.decode("utf-8"))
                events.append(event)
                if event["event"] == "batch" and event["batch_index"] == 0:
                    self._post(f"/api/runs/{run_id}/cancel", {})
        kinds = [event["event"] for event in events]
        self.assertLess(kinds.index("batch"), kinds.index("cancelled"))
        self.assertNotIn("complete", kinds)
        self.assertTrue(all(event["run_id"] == run_id for event in events))

        failed = self._post("/api/runs", {"scenario": "site04-6h", "batch_size": 2, "fail_after_batches": 1})
        failed_events = self._read_events(failed["run_id"])
        self.assertNotEqual(failed["run_id"], run_id)
        self.assertEqual(failed_events[-1]["event"], "error")
        self.assertFalse(failed_events[-1]["complete"])
        self.assertGreaterEqual(failed_events[-1]["samples_emitted"], 1)

    @unittest.skipUnless((DATA / "horizons").is_dir(), "local Horizons practice bundle")
    def test_http_comparison_batch_before_complete(self) -> None:
        started = self._post(
            "/api/comparisons",
            {
                "pair": "practice-48h",
                "batch_size_a": 2,
                "batch_size_b": 3,
                "pause_seconds": 0,
            },
        )
        comparison_id = started["comparison_id"]
        self.assertNotEqual(started["run_id_a"], started["run_id_b"])
        events = []
        with urllib.request.urlopen(self.base + f"/api/comparisons/{comparison_id}/events") as response:
            while True:
                line = response.readline()
                if not line:
                    break
                event = json.loads(line.decode("utf-8"))
                events.append(event)
                if event["event"] == "site_batch":
                    self.assertFalse(event["complete"])
                    self.assertTrue(event["partial"])
                    self.assertTrue(event["comparison_partial"])
                    break
        self.assertEqual(events[0]["event"], "stage")
        self.assertEqual(events[1]["event"], "metadata")
        self.assertEqual(events[2]["event"], "site_batch")
        self.assertLess(events[2]["shared_samples"], 193)  # full 48 h grid is larger
        # Restart path: previous consumer stopped early; a fresh start must use a new id.
        restarted = self._post("/api/comparisons", {"pair": "practice-48h", "batch_size_a": 8, "batch_size_b": 8})
        self.assertNotEqual(restarted["comparison_id"], comparison_id)
        finished = self._read_comparison_events(restarted["comparison_id"])
        self.assertEqual(finished[-1]["event"], "complete")
        comparison = finished[-1]["comparison"]
        self.assertEqual(comparison["overlap"]["sun_centre_clear_seconds"]["site_a"], 172800)
        self.assertEqual(comparison["overlap"]["sun_centre_clear_seconds"]["site_b"], 0)
        self.assertEqual(comparison["overlap"]["both_centres_clear_seconds"]["site_a"], 0)
        self.assertEqual(comparison["overlap"]["both_centres_clear_seconds"]["site_b"], 0)
        self.assertTrue(all(event.get("comparison_id") == restarted["comparison_id"] for event in finished))

    def _read_comparison_events(self, comparison_id: str) -> list[dict]:
        with urllib.request.urlopen(self.base + f"/api/comparisons/{comparison_id}/events") as response:
            body = response.read().decode("utf-8")
        return [json.loads(line) for line in body.splitlines() if line.strip()]


class PracticeComparisonStream(unittest.TestCase):
    @unittest.skipUnless((DATA / "horizons").is_dir(), "local Horizons practice bundle")
    def test_live_pair_matches_saved_totals_and_uneven_batches(self) -> None:
        site_a = json.loads(SITE04.read_text(encoding="utf-8"))
        site_b = json.loads(MALAPERT.read_text(encoding="utf-8"))
        batch_a = run_from_scenario(site_a, DATA, "test")
        batch_b = run_from_scenario(site_b, DATA, "test")
        saved = comparison_document(batch_a, batch_b, "test")
        events = list(
            stream_comparison(
                site_a,
                site_b,
                DATA,
                "test",
                batch_size_a=2,
                batch_size_b=5,
            )
        )
        self.assertEqual(events[0]["event"], "stage")
        self.assertEqual(events[1]["event"], "metadata")
        site_batches = [event for event in events if event["event"] == "site_batch"]
        self.assertGreaterEqual(len(site_batches), 2)
        self.assertEqual(site_batches[0]["role"], "site_a")
        self.assertEqual(len(site_batches[0]["samples"]), 2)
        self.assertLess(site_batches[0]["shared_samples"], len(batch_a["samples"]))
        # Uneven arrival: A flushed before B's first batch of 5.
        first_b = next(event for event in site_batches if event["role"] == "site_b")
        self.assertEqual(len(first_b["samples"]), 5)
        self.assertGreater(first_b["batch_index"], -1)
        complete = events[-1]
        self.assertEqual(complete["event"], "complete")
        self.assertFalse(complete["partial"])
        self.assertEqual(complete["comparison"]["overlap"], saved["overlap"])
        self.assertEqual(complete["result_a"]["elapsed_seconds"]["sun"]["clear"], 172800)
        self.assertEqual(complete["result_b"]["elapsed_seconds"]["sun"]["clear"], 0)
        self.assertEqual(complete["result_a"]["elapsed_seconds"]["both"]["clear"], 0)
        self.assertEqual(complete["result_b"]["elapsed_seconds"]["both"]["clear"], 0)
        self.assertEqual(complete["result_a"]["samples"], batch_a["samples"])
        self.assertEqual(complete["result_b"]["samples"], batch_b["samples"])

    @unittest.skipUnless((DATA / "horizons").is_dir(), "local Horizons practice bundle")
    def test_incompatible_grids_return_actionable_error(self) -> None:
        site_a = json.loads(SITE04.read_text(encoding="utf-8"))
        site_b = json.loads(MALAPERT.read_text(encoding="utf-8"))
        site_b = dict(site_b)
        site_b["end_utc"] = "2025-01-02T12:00:00Z"
        events = list(stream_comparison(site_a, site_b, DATA, "test"))
        self.assertEqual(events[-1]["event"], "error")
        self.assertIn("incompatible time grids", events[-1]["message"])
        self.assertIn("end_utc", events[-1]["message"])


class ComparisonControl(unittest.TestCase):
    def _export(self, root: Path, body: str, target_id: int, rows: list[tuple[str, str, float | None, float | None]]) -> None:
        folder = root / body
        folder.mkdir(parents=True)
        lines = []
        csv_lines = ["timestamp_utc,azimuth_deg,elevation_deg,angle_status\n"]
        for stamp, utc, azimuth, elevation in rows:
            if azimuth is None or elevation is None:
                lines.append(f" {stamp},*, ,       n.a.,        n.a.,")
                csv_lines.append(f"{utc},,,missing\n")
            else:
                lines.append(f" {stamp},*, , {azimuth:.6f}, {elevation:.6f},")
                csv_lines.append(f"{utc},{azimuth},{elevation},available\n")
        result = (
            f"Target body name: {body} ({target_id}) {{source: DE441}}\n"
            "Center body name: Moon (301) {source: DE441}\n"
            "Center geodetic : 203.5614, -89.7812, 1.7389 {E-lon(deg),Lat(deg),Alt(km)}\n"
            "Center pole/equ : MEAN_ME (high precision) {East-longitude positive}\n"
            "Atmos refraction: NO (AIRLESS)\n"
            " Date__(UT)__HR:MN, , ,Azi_(a-app), Elev_(a-app),\n"
            "$$SOE\n"
            + "\n".join(lines)
            + "\n$$EOE\n"
        )
        response = folder / "response.json"
        csv_path = folder / "angles.csv"
        response.write_text(json.dumps({"result": result}), encoding="utf-8")
        csv_path.write_text("".join(csv_lines), encoding="utf-8")
        import hashlib

        provenance = {
            "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
            "raw_sha256": hashlib.sha256(response.read_bytes()).hexdigest(),
        }
        (folder / "provenance.json").write_text(json.dumps(provenance), encoding="utf-8")

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        stamps = [
            ("2025-Jan-01 00:00", "2025-01-01T00:00:00Z"),
            ("2025-Jan-01 00:15", "2025-01-01T00:15:00Z"),
            ("2025-Jan-01 00:30", "2025-01-01T00:30:00Z"),
            ("2025-Jan-01 00:45", "2025-01-01T00:45:00Z"),
        ]
        # Site A: Unknown across a batch boundary (00:15 needs missing 00:30).
        sun_a = [
            (stamps[0][0], stamps[0][1], 10.0, 1.0),
            (stamps[1][0], stamps[1][1], 11.0, 0.5),
            (stamps[2][0], stamps[2][1], None, None),
            (stamps[3][0], stamps[3][1], 12.0, -0.2),
        ]
        earth_a = [
            (stamps[0][0], stamps[0][1], 20.0, -1.0),
            (stamps[1][0], stamps[1][1], 21.0, -1.1),
            (stamps[2][0], stamps[2][1], 22.0, -1.2),
            (stamps[3][0], stamps[3][1], 23.0, -1.3),
        ]
        sun_b = [
            (stamps[0][0], stamps[0][1], 30.0, 2.0),
            (stamps[1][0], stamps[1][1], 31.0, 1.5),
            (stamps[2][0], stamps[2][1], 32.0, 1.0),
            (stamps[3][0], stamps[3][1], 33.0, 0.5),
        ]
        earth_b = [
            (stamps[0][0], stamps[0][1], 40.0, -2.0),
            (stamps[1][0], stamps[1][1], 41.0, -2.1),
            (stamps[2][0], stamps[2][1], 42.0, -2.2),
            (stamps[3][0], stamps[3][1], 43.0, -2.3),
        ]
        for body, target, rows in (
            ("sun", 10, sun_a),
            ("earth", 399, earth_a),
        ):
            self._export(self.root / "horizons" / "site_a", body, target, rows)
        for body, target, rows in (
            ("sun", 10, sun_b),
            ("earth", 399, earth_b),
        ):
            self._export(self.root / "horizons" / "site_b", body, target, rows)
        self.scenario_a = {
            "status": "practice",
            "site_id": "site_a",
            "observer": {
                "longitude_east_deg": -156.4386,
                "latitude_deg": -89.7812,
                "reference_altitude_km": 1.738902,
                "center_body_id": 301,
            },
            "start_utc": "2025-01-01T00:00:00Z",
            "end_utc": "2025-01-01T00:45:00Z",
            "step_seconds": 900,
            "observer_frame": "MEAN_ME",
            "angle_convention": "airless_apparent",
            "horizons_paths": {"sun": "horizons/site_a/sun", "earth": "horizons/site_a/earth"},
            "eligible_for_submission_claim": False,
        }
        self.scenario_b = dict(self.scenario_a)
        self.scenario_b["site_id"] = "site_b"
        self.scenario_b["horizons_paths"] = {
            "sun": "horizons/site_b/sun",
            "earth": "horizons/site_b/earth",
        }

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_unknown_across_batch_boundary_and_mid_run_failure(self) -> None:
        events = list(
            stream_comparison(
                self.scenario_a,
                self.scenario_b,
                self.root,
                "test",
                batch_size_a=1,
                batch_size_b=2,
            )
        )
        site_a_batches = [event for event in events if event["event"] == "site_batch" and event["role"] == "site_a"]
        self.assertEqual(site_a_batches[1]["samples"][0]["sun"]["state"], "unknown")
        self.assertEqual(site_a_batches[1]["samples"][0]["sun"]["reason"], "missing_right_endpoint")
        self.assertEqual(events[-1]["event"], "complete")
        # Shared totals never treat pending as Unknown: before B's first batch, shared may be 0 or 1.
        early = site_a_batches[0]
        self.assertIn("overlap", early)
        self.assertEqual(early["overlap"]["unknown_seconds"]["site_a"]["sun"], 0)

        failed = list(
            stream_comparison(
                self.scenario_a,
                self.scenario_b,
                self.root,
                "test",
                batch_size_a=1,
                batch_size_b=2,
                fail_after_batches_b=1,
            )
        )
        self.assertEqual(failed[-1]["event"], "error")
        self.assertEqual(failed[-1]["role"], "site_b")
        self.assertFalse(failed[-1]["complete"])
        self.assertTrue(failed[-1]["partial"])
        self.assertGreaterEqual(failed[-1]["samples_emitted_a"], 1)
        self.assertGreaterEqual(failed[-1]["shared_samples"], 1)
        self.assertNotIn("comparison", failed[-1])

        cancel = threading.Event()
        first = stream_comparison(
            self.scenario_a,
            self.scenario_b,
            self.root,
            "test",
            batch_size_a=1,
            batch_size_b=1,
            cancel=cancel,
            pause_seconds=0.05,
        )
        self.assertEqual(next(first)["event"], "stage")
        self.assertEqual(next(first)["event"], "metadata")
        batch = next(first)
        self.assertEqual(batch["event"], "site_batch")
        cancel.set()
        cancelled = None
        for event in first:
            if event["event"] == "cancelled":
                cancelled = event
                break
        self.assertIsNotNone(cancelled)
        self.assertTrue(cancelled["partial"])
        second = list(
            stream_comparison(
                self.scenario_a,
                self.scenario_b,
                self.root,
                "test",
                batch_size_a=1,
                batch_size_b=1,
            )
        )
        self.assertNotEqual(second[0]["comparison_id"], cancelled["comparison_id"])
        self.assertEqual(second[-1]["event"], "complete")


@unittest.skipUnless(DATA.is_dir(), "local Horizons practice bundle")
class DeliveredSampleAccounting(unittest.TestCase):
    """Shared totals, cutoff and failure/cancel events count only samples already delivered."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.a = json.loads(SITE04.read_text())
        cls.b = json.loads(MALAPERT.read_text())

    def _events(self, **kwargs) -> list[dict]:
        return list(stream_comparison(self.a, self.b, DATA, "test", **kwargs))

    def test_every_event_reports_delivered_shared_samples(self) -> None:
        delivered = {"site_a": 0, "site_b": 0}
        events = self._events(batch_size_a=3, batch_size_b=4)
        for event in events:
            if event["event"] == "site_batch":
                delivered[event["role"]] += len(event["samples"])
                self.assertEqual(event["shared_samples"], min(delivered.values()))
                self.assertEqual(event["samples_emitted"], delivered[event["role"]])
                if event["shared_samples"]:
                    self.assertIsNotNone(event["cutoff_utc"])
                else:
                    self.assertIsNone(event["cutoff_utc"])
        self.assertEqual(events[-1]["event"], "complete")

    def test_failure_before_the_other_site_delivers_reports_no_shared_samples(self) -> None:
        events = self._events(batch_size_a=3, batch_size_b=4, fail_after_batches_a=1)
        failed = events[-1]
        self.assertEqual(failed["event"], "error")
        self.assertEqual(failed["samples_emitted_a"], 3)
        self.assertEqual(failed["samples_emitted_b"], 0)
        self.assertEqual(failed["shared_samples"], 0)
        self.assertIsNone(failed["cutoff_utc"])
        self.assertEqual(failed["overlap"]["sun_centre_clear_seconds"]["site_a"], 0)

    def test_failure_with_shared_samples_reports_actual_partial_result_and_cutoff(self) -> None:
        events = self._events(batch_size_a=3, batch_size_b=4, fail_after_batches_a=2)
        failed = events[-1]
        self.assertEqual(failed["event"], "error")
        self.assertEqual(failed["samples_emitted_a"], 6)
        self.assertEqual(failed["samples_emitted_b"], 4)
        self.assertEqual(failed["shared_samples"], 4)
        self.assertEqual(failed["cutoff_utc"], "2025-01-01T00:45:00Z")
        self.assertEqual(failed["covered_through_utc"], "2025-01-01T01:00:00Z")
        # Four 900 s samples: one hour of Sun-centre clearance at Site04, none at Malapert.
        self.assertEqual(failed["overlap"]["sun_centre_clear_seconds"]["site_a"], 3600)
        self.assertEqual(failed["overlap"]["sun_centre_clear_seconds"]["site_b"], 0)

    def test_cancel_reports_delivered_cutoff(self) -> None:
        cancel = threading.Event()
        stream = stream_comparison(
            self.a, self.b, DATA, "test", batch_size_a=2, batch_size_b=2, cancel=cancel, pause_seconds=0.01
        )
        seen = 0
        cancelled = None
        for event in stream:
            if event["event"] == "site_batch":
                seen += 1
                if seen == 4:
                    cancel.set()
            if event["event"] == "cancelled":
                cancelled = event
                break
        self.assertIsNotNone(cancelled)
        self.assertEqual(cancelled["shared_samples"], min(cancelled["samples_emitted_a"], cancelled["samples_emitted_b"]))
        self.assertEqual(cancelled["cutoff_utc"] is None, cancelled["shared_samples"] == 0)
        self.assertGreaterEqual(cancelled["shared_samples"], 2)

    def test_single_run_events_carry_the_cutoff(self) -> None:
        events = list(stream_scenario(self.a, DATA, "test", batch_size=5, fail_after_batches=2))
        failed = events[-1]
        self.assertEqual(failed["event"], "error")
        self.assertEqual(failed["samples_emitted"], 10)
        self.assertEqual(failed["cutoff_utc"], "2025-01-01T02:15:00Z")
        self.assertEqual(failed["covered_through_utc"], "2025-01-01T02:30:00Z")


if __name__ == "__main__":
    unittest.main()
