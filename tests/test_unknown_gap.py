"""Unknown carried from the raw Horizons row to the batch result, the stream and the export.

The QA case is SYNTHETIC. Its Sun reply reads ``n.a.`` at 00:30 on a 15-minute grid. With the left-sample,
both-endpoints rule that is 30 minutes of Sun Unknown, 00:15 to 00:45, and the same span, reason and duration
must appear in the batch result, the stream's final result, the packaged export and the comparison document.
"""

from __future__ import annotations

import copy
import csv
import hashlib
import json
import shutil
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import lunar_offline_pack as pack  # noqa: E402
import qa_horizons_case as qa  # noqa: E402
from lunar_navigator import cli  # noqa: E402
from lunar_navigator.catalog import (  # noqa: E402
    build_catalog,
    comparison_window_scenarios,
    find_entry,
    scenario_for,
    validate_window,
)
from lunar_navigator.engine import comparison_document, run_from_scenario, stream_comparison, stream_scenario  # noqa: E402
from lunar_navigator.horizons_table import index_result_text, parse_response_line, response_angles  # noqa: E402
from lunar_navigator.live_server import make_server  # noqa: E402
from lunar_navigator.skyline import REASON_GAP, horizon_at_azimuth  # noqa: E402
from lunar_navigator.terrain import HorizonBin, horizon_at_azimuth as terrain_horizon_at_azimuth  # noqa: E402

QA_ROOT = ROOT / "tests/fixtures/qa_horizons"
NORTH = json.loads((QA_ROOT / "qa-gap-north_scenario.json").read_text(encoding="utf-8"))
SOUTH = json.loads((QA_ROOT / "qa-gap-south_scenario.json").read_text(encoding="utf-8"))
GAP_START, GAP_END = "2024-06-01T00:15:00Z", "2024-06-01T00:45:00Z"


def _strip(result: dict) -> dict:
    result = copy.deepcopy(result)
    result.pop("code_revision", None)
    return result


def _seconds(interval: dict) -> int:
    start = datetime.strptime(interval["start_utc"], "%Y-%m-%dT%H:%M:%SZ")
    end = datetime.strptime(interval["end_utc"], "%Y-%m-%dT%H:%M:%SZ")
    return int((end - start).total_seconds())


def _complete(events: list[dict]) -> dict:
    assert events[-1]["event"] == "complete", events[-1]
    return events[-1]["result"]


class ImporterAcceptsGaps(unittest.TestCase):
    def test_n_a_row_is_kept_not_dropped(self) -> None:
        self.assertEqual(parse_response_line(" 2024-Jun-01 00:30, , ,       n.a.,        n.a.,"), ("2024-06-01T00:30:00Z", None, None))
        self.assertEqual(response_angles(" 2024-Jun-01 00:30, , ,       n.a.,        n.a.,"), (None, None))
        index = index_result_text(qa.payload("qa-gap-north", "sun")["result"], "x")
        self.assertIn("2024-06-01T00:30:00Z", index)
        self.assertEqual(len(index), 5)

    def test_saved_files_come_from_the_normal_importer(self) -> None:
        folder = QA_ROOT / NORTH["horizons_paths"]["sun"]
        receipt = json.loads((folder / "provenance.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["missing_row_count"], 1)
        self.assertEqual(receipt["missing_timestamps"], ["2024-06-01T00:30:00Z"])
        self.assertTrue(receipt["synthetic"])
        rows = list(csv.DictReader((folder / "angles.csv").open(encoding="utf-8")))
        gap = next(row for row in rows if row["timestamp_utc"] == "2024-06-01T00:30:00Z")
        self.assertEqual((gap["azimuth_deg"], gap["elevation_deg"], gap["angle_status"]), ("", "", "missing"))
        self.assertEqual(hashlib.sha256((folder / "response.json").read_bytes()).hexdigest(), receipt["raw_sha256"])

    def test_fresh_import_matches_the_committed_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            folders = qa.build(Path(tmp))
            for site, bodies in folders.items():
                for body, relative in bodies.items():
                    for name in ("response.json", "angles.csv", "provenance.json"):
                        self.assertEqual(
                            (Path(tmp) / relative / name).read_bytes(), (QA_ROOT / relative / name).read_bytes(), f"{site} {body} {name}"
                        )


class ImporterStillRejects(unittest.TestCase):
    start, stop = qa.START, qa.STOP

    def _import(self, payload: dict, **overrides) -> None:
        args = dict(url="synthetic://x", target="10", label="sun", observer=(10.0, -85.0, 0.0), start=self.start,
                    stop=self.stop, step=15, practice=True)
        args.update(overrides)
        with tempfile.TemporaryDirectory() as tmp:
            pack.import_horizons_export(Path(tmp) / "x", payload, **args)

    def test_clean_reply_imports(self) -> None:
        self._import(qa.payload("qa-gap-north", "sun"))

    def test_wrong_observer(self) -> None:
        with self.assertRaisesRegex(ValueError, "observer"):
            self._import(qa.payload("qa-gap-north", "sun"), observer=(11.0, -85.0, 0.0))

    def test_wrong_target(self) -> None:
        with self.assertRaisesRegex(ValueError, "target"):
            self._import(qa.payload("qa-gap-north", "sun"), target="399")

    def test_off_grid_timestamp(self) -> None:
        payload = qa.payload("qa-gap-north", "sun")
        payload["result"] = payload["result"].replace("2024-Jun-01 00:15,", "2024-Jun-01 00:16,")
        with self.assertRaisesRegex(ValueError, "timestamp"):
            self._import(payload)

    def test_duplicate_timestamp(self) -> None:
        payload = qa.payload("qa-gap-north", "sun")
        payload["result"] = payload["result"].replace("2024-Jun-01 00:30,", "2024-Jun-01 00:15,")
        with self.assertRaisesRegex(ValueError, "timestamp"):
            self._import(payload)

    def test_malformed_number(self) -> None:
        payload = qa.payload("qa-gap-north", "sun")
        payload["result"] = payload["result"].replace("20.000000", "twenty")
        with self.assertRaises(ValueError):
            self._import(payload)


class EngineRejects(unittest.TestCase):
    def _copy(self) -> Path:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        shutil.copytree(QA_ROOT, tmp / "d")
        return tmp / "d"

    def test_bad_checksum(self) -> None:
        root = self._copy()
        csv_path = root / NORTH["horizons_paths"]["earth"] / "angles.csv"
        csv_path.write_text(csv_path.read_text(encoding="utf-8").replace("1.0,", "1.5,", 1), encoding="utf-8")
        with self.assertRaises(ValueError):
            run_from_scenario(NORTH, root, "t")

    def test_wrong_observer_in_scenario(self) -> None:
        scenario = copy.deepcopy(NORTH)
        scenario["observer"]["longitude_east_deg"] = 11.0
        with self.assertRaises(ValueError):
            run_from_scenario(scenario, QA_ROOT, "t")

    def test_incompatible_time_grids(self) -> None:
        scenario = copy.deepcopy(NORTH)
        scenario["step_seconds"] = 1800
        scenario["expected_row_count"] = 3
        with self.assertRaises(ValueError):
            run_from_scenario(scenario, QA_ROOT, "t")

    def test_csv_missing_but_raw_line_present_is_rejected(self) -> None:
        root = self._copy()
        folder = root / NORTH["horizons_paths"]["earth"]
        rows = (folder / "angles.csv").read_text(encoding="utf-8").splitlines()
        rows[2] = rows[2].split(",")[0] + ",,,missing"
        text = "\n".join(rows) + "\n"
        (folder / "angles.csv").write_text(text, encoding="utf-8")
        receipt = json.loads((folder / "provenance.json").read_text(encoding="utf-8"))
        receipt["csv_sha256"] = hashlib.sha256(text.encode()).hexdigest()
        (folder / "provenance.json").write_text(json.dumps(receipt), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "CSV row is missing but the raw Horizons line is present"):
            run_from_scenario(NORTH, root, "t")


class SunGapAcceptance(unittest.TestCase):
    """The acceptance test: 30 minutes of Sun Unknown, 00:15 to 00:45, the same everywhere."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.batch = run_from_scenario(NORTH, QA_ROOT, "t")

    def test_batch_interval_reason_and_duration(self) -> None:
        sun = [i for i in self.batch["intervals"] if i["lane"] == "sun" and i["state"] == "unknown"]
        self.assertEqual([(i["start_utc"], i["end_utc"], i["reason"]) for i in sun],
                         [(GAP_START, "2024-06-01T00:30:00Z", "missing_right_endpoint"),
                          ("2024-06-01T00:30:00Z", GAP_END, "missing_ephemeris")])
        self.assertEqual(sum(_seconds(i) for i in sun), 1800)
        self.assertEqual(self.batch["elapsed_seconds"]["sun"], {"clear": 900, "blocked": 900, "unknown": 1800})

    def test_unknown_is_counted_separately_per_lane(self) -> None:
        e = self.batch["elapsed_seconds"]
        self.assertEqual((e["sun"]["unknown"], e["earth"]["unknown"], e["both"]["unknown"]), (1800, 0, 900))
        for lane in ("sun", "earth", "both"):
            self.assertEqual(sum(e[lane].values()), 3600, lane)

    def test_confirmed_blocker_beats_unknown_in_both(self) -> None:
        by_time = {s["timestamp_utc"]: s for s in self.batch["samples"]}
        at_0015 = by_time[GAP_START]
        self.assertEqual(at_0015["sun"]["state"], "unknown")
        self.assertEqual(at_0015["earth"]["state"], "blocked")
        self.assertEqual(at_0015["both"]["state"], "blocked")
        at_0030 = by_time["2024-06-01T00:30:00Z"]
        self.assertEqual((at_0030["sun"]["state"], at_0030["earth"]["state"], at_0030["both"]["state"]), ("unknown", "clear", "unknown"))

    def test_missing_angle_is_null_not_zero(self) -> None:
        gap = next(s for s in self.batch["samples"] if s["timestamp_utc"] == "2024-06-01T00:30:00Z")["sun"]
        self.assertIsNone(gap["azimuth_deg"])
        self.assertIsNone(gap["elevation_deg"])
        self.assertIsNone(gap["margin_deg"])
        self.assertIn("n.a.", gap["response_line"])
        self.assertTrue(gap["source_ref"].endswith("#row=4"))

    def test_stream_matches_batch_at_every_batch_size(self) -> None:
        for size in (1, 2, 3, 5, 50):
            result = _complete(list(stream_scenario(NORTH, QA_ROOT, "t", batch_size=size)))
            self.assertEqual(_strip(result), _strip(self.batch), f"batch_size={size}")

    def test_stream_batches_carry_the_same_unknown_before_completion(self) -> None:
        events = list(stream_scenario(NORTH, QA_ROOT, "t", batch_size=1))
        streamed = [s for e in events if e["event"] == "batch" for s in e["samples"]]
        self.assertEqual(streamed, self.batch["samples"])

    def test_export_carries_the_same_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "run.json"
            cli.main(["--data-root", str(QA_ROOT), "--revision", "t", "run", "--scenario",
                      str(QA_ROOT / "qa-gap-north_scenario.json"), "--out", str(out)])
            exported = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(_strip(exported), _strip(self.batch))
        sun = [i for i in exported["intervals"] if i["lane"] == "sun" and i["state"] == "unknown"]
        self.assertEqual(sum(_seconds(i) for i in sun), 1800)

    def test_comparison_document_counts_unknown_beside_known(self) -> None:
        south = run_from_scenario(SOUTH, QA_ROOT, "t")
        doc = comparison_document(self.batch, south, "t")
        unknown = doc["overlap"]["unknown_seconds"]
        self.assertEqual(unknown["site_a"], {"sun": 1800, "earth": 0, "both": 900})
        self.assertEqual(unknown["site_b"], {"sun": 0, "earth": 0, "both": 0})
        events = list(stream_comparison(NORTH, SOUTH, QA_ROOT, "t", batch_size_a=1, batch_size_b=2))
        self.assertEqual(events[-1]["event"], "complete")
        streamed = events[-1]["comparison"] if "comparison" in events[-1] else None
        if streamed is not None:
            self.assertEqual(streamed["overlap"]["unknown_seconds"], unknown)


class CatalogAndApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.roots = [{"id": "qa", "label": "QA", "path": str(QA_ROOT), "synthetic": True}]
        cls.catalog = build_catalog(cls.roots)

    def test_entries_carry_site_observer_coverage_and_checksums(self) -> None:
        self.assertEqual(self.catalog["problems"], [])
        entry = find_entry(self.catalog, "qa-gap-north__20240601T000000Z__20240601T010000Z__900s")
        self.assertTrue(entry["synthetic"])
        self.assertEqual(entry["observer"]["latitude_deg"], -85.0)
        self.assertEqual(entry["coverage"], {"start_utc": "2024-06-01T00:00:00Z", "end_utc": "2024-06-01T01:00:00Z", "step_seconds": 900, "samples": 5})
        self.assertEqual(entry["angles"]["sun"]["missing_utc"], ["2024-06-01T00:30:00Z"])
        self.assertEqual(len(entry["sources"]["sun"]["raw_sha256"]), 64)
        self.assertEqual(len(entry["sources"]["earth"]["csv_sha256"]), 64)

    def test_shared_window_needs_matching_grid(self) -> None:
        windows = self.catalog["comparisons"]
        self.assertEqual(len(windows), 1)
        self.assertEqual((windows[0]["start_utc"], windows[0]["end_utc"], windows[0]["step_seconds"]), ("2024-06-01T00:00:00Z", "2024-06-01T01:00:00Z", 900))

    def test_window_validation(self) -> None:
        entry = self.catalog["entries"][0]
        validate_window(entry, "2024-06-01T00:15:00Z", "2024-06-01T00:45:00Z")
        for start, end in (("2024-06-01T00:16:00Z", None), ("2024-05-31T23:45:00Z", None), (None, "2024-06-01T01:15:00Z"),
                           ("2024-06-01T00:45:00Z", "2024-06-01T00:15:00Z"), ("not a time", None)):
            with self.assertRaises(ValueError, msg=f"{start} {end}"):
                validate_window(entry, start, end)

    def test_sub_window_scenario_is_labelled_and_never_eligible(self) -> None:
        scenario = scenario_for(self.catalog["entries"][0], "2024-06-01T00:15:00Z", "2024-06-01T00:45:00Z")
        self.assertFalse(scenario["eligible_for_submission_claim"])
        self.assertTrue(scenario["synthetic"])
        self.assertFalse(scenario["in_appendix_b"])
        result = run_from_scenario(scenario, QA_ROOT, "t")
        self.assertEqual([s["timestamp_utc"] for s in result["samples"]], ["2024-06-01T00:15:00Z", "2024-06-01T00:30:00Z", "2024-06-01T00:45:00Z"])
        self.assertEqual(result["elapsed_seconds"]["sun"]["unknown"], 1800)

    def test_tampered_source_is_a_catalog_problem_not_an_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copytree(QA_ROOT, Path(tmp) / "d")
            csv_path = Path(tmp) / "d" / NORTH["horizons_paths"]["earth"] / "angles.csv"
            csv_path.write_text(csv_path.read_text(encoding="utf-8").replace("1.0,", "1.5,", 1), encoding="utf-8")
            catalog = build_catalog([{"id": "t", "label": "t", "path": str(Path(tmp) / "d"), "synthetic": True}])
        self.assertTrue(catalog["problems"])
        self.assertNotIn("qa-gap-north", " ".join(e["site_id"] for e in catalog["entries"]))

    def test_comparison_window_scenarios(self) -> None:
        window_id = self.catalog["comparisons"][0]["id"]
        a, b, _ = comparison_window_scenarios(self.catalog, window_id, "2024-06-01T00:00:00Z", "2024-06-01T00:30:00Z")
        self.assertEqual((a["step_seconds"], b["step_seconds"]), (900, 900))
        with self.assertRaises(ValueError):
            comparison_window_scenarios(self.catalog, window_id, "2024-05-31T00:00:00Z", None)

    def test_http_catalog_runs_and_400s(self) -> None:
        server = make_server(ROOT, QA_ROOT, "t", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close()))
        base = f"http://127.0.0.1:{server.server_address[1]}"

        def call(path: str, body: dict | None = None):
            request = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(),
                                             headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    return response.status, response.read().decode()
            except urllib.error.HTTPError as error:
                return error.code, error.read().decode()

        status, text = call("/api/catalog")
        self.assertEqual(status, 200)
        catalog = json.loads(text)
        entry = next(e for e in catalog["entries"] if e["site_id"] == "qa-gap-north")
        status, text = call("/api/runs", {"catalog": entry["id"], "start_utc": "2024-06-01T00:00:00Z", "end_utc": "2024-06-01T01:00:00Z", "batch_size": 1})
        self.assertEqual(status, 200, text)
        run_id = json.loads(text)["run_id"]
        with urllib.request.urlopen(base + f"/api/runs/{run_id}/events", timeout=30) as response:
            events = [json.loads(line) for line in response.read().decode().splitlines() if line.strip()]
        streamed = _complete(events)
        self.assertEqual(streamed["elapsed_seconds"]["sun"]["unknown"], 1800)
        for bad in ({"catalog": entry["id"], "start_utc": "2024-06-01T00:07:00Z"}, {"catalog": "nope"},
                    {"catalog": entry["id"], "horizon_mode": "mars"}):
            status, text = call("/api/runs", bad)
            self.assertEqual(status, 400, text)
            self.assertIn("error", json.loads(text))
        status, text = call("/api/comparisons", {"catalog_window": catalog["comparisons"][0]["id"], "start_utc": "2023-01-01T00:00:00Z"})
        self.assertEqual(status, 400, text)


class TerrainMode(unittest.TestCase):
    def _terrain(self, scenario: dict) -> dict:
        return {**scenario, "horizon_mode": "terrain"}

    def test_no_reviewed_skyline_is_unknown_with_a_reason_and_keeps_elevation(self) -> None:
        result = run_from_scenario(self._terrain(NORTH), QA_ROOT, "t")
        self.assertEqual(result["scenario"]["horizon_mode"], "terrain")
        self.assertEqual(result["terrain"]["status"], "unknown")
        self.assertEqual(result["terrain"]["reason"], "terrain_not_reviewed")
        for sample in result["samples"]:
            for lane in ("sun", "earth"):
                item = sample[lane]
                self.assertEqual(item["state"], "unknown")
                # A body with no saved angle keeps its own reason; every other sample names the terrain reason.
                missing = item["elevation_deg"] is None
                self.assertEqual(item["reason"], "missing_ephemeris" if missing else "terrain_not_reviewed")
                self.assertIsNone(item["margin_deg"])
                if not missing:
                    self.assertIsNone(item["horizon_deg"])
            self.assertEqual(sample["both"]["state"], "unknown")
        elevations = [s["sun"]["elevation_deg"] for s in result["samples"]]
        self.assertEqual(elevations, [2.0, 0.4, None, -1.25, 0.0])
        self.assertEqual(result["elapsed_seconds"]["sun"], {"clear": 0, "blocked": 0, "unknown": 3600})
        self.assertNotEqual(result["run_id"], run_from_scenario(NORTH, QA_ROOT, "t")["run_id"])

    def test_terrain_stream_matches_batch(self) -> None:
        scenario = self._terrain(NORTH)
        batch = run_from_scenario(scenario, QA_ROOT, "t")
        streamed = _complete(list(stream_scenario(scenario, QA_ROOT, "t", batch_size=2)))
        self.assertEqual(_strip(streamed), _strip(batch))

    def _data_with_skyline(self, bins: list[dict], observer: dict | None = None, review: dict | None = None) -> Path:
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, True)
        shutil.copytree(QA_ROOT, tmp / "d")
        (tmp / "d" / "terrain" / "reviewed").mkdir(parents=True)
        document = {
            "schema_version": "reviewed-skyline-1",
            "site_id": "qa-gap-north",
            "synthetic": True,
            "observer": observer or {k: NORTH["observer"][k] for k in ("longitude_east_deg", "latitude_deg", "reference_altitude_km")},
            "review": review or {"status": "approved", "reviewer": "QA synthetic", "reviewed_utc": "2024-06-01T00:00:00Z",
                                 "frame": "MEAN_ME", "vertical_reference": "QA", "radial_coverage_m": [0, 8000],
                                 "independent_check": "QA synthetic"},
            "bins": bins,
        }
        (tmp / "d" / "terrain" / "reviewed" / "qa.json").write_text(json.dumps(document), encoding="utf-8")
        return tmp / "d"

    def test_reviewed_skyline_for_the_observer_gives_real_states(self) -> None:
        bins = [{"azimuth_deg": a, "horizon_deg": h, "known": True} for a, h in ((0, 0.5), (90, 0.5), (180, 0.0), (270, 0.0))]
        root = self._data_with_skyline(bins)
        result = run_from_scenario(self._terrain(NORTH), root, "t")
        self.assertEqual(result["terrain"]["status"], "reviewed")
        sun0 = result["samples"][0]["sun"]
        self.assertEqual((sun0["state"], sun0["horizon_deg"], sun0["margin_deg"]), ("clear", 0.5, 1.5))
        # Sun at 00:15 is 0.4 deg: clear against 0 deg, below this 0.5 deg skyline. Its span is Unknown because 00:30 is n.a.
        sun1 = result["samples"][1]["sun"]
        self.assertEqual((sun1["state"], sun1["reason"]), ("unknown", "missing_right_endpoint"))
        self.assertAlmostEqual(sun1["margin_deg"], -0.1, places=6)
        self.assertEqual(result["samples"][3]["sun"]["state"], "blocked")
        self.assertEqual(result["samples"][2]["sun"]["reason"], "missing_ephemeris")
        self.assertNotEqual(_strip(result)["samples"], _strip(run_from_scenario(NORTH, QA_ROOT, "t"))["samples"])

    def test_gap_in_the_bracket_is_unknown_with_that_reason_not_zero(self) -> None:
        bins = [{"azimuth_deg": 0, "horizon_deg": 0.0, "known": True}, {"azimuth_deg": 90, "horizon_deg": 0.0, "known": True},
                {"azimuth_deg": 180, "horizon_deg": 0.0, "known": True}, {"azimuth_deg": 270, "horizon_deg": None, "known": False}]
        result = run_from_scenario(self._terrain(NORTH), self._data_with_skyline(bins), "t")
        earth = result["samples"][0]["earth"]  # azimuth 200 sits between the 180 and 270 bins
        self.assertEqual((earth["state"], earth["reason"], earth["horizon_deg"]), ("unknown", REASON_GAP, None))
        self.assertEqual(earth["elevation_deg"], 1.0)
        self.assertEqual(result["samples"][0]["sun"]["state"], "clear")

    def test_skyline_for_a_different_observer_is_not_used(self) -> None:
        bins = [{"azimuth_deg": a, "horizon_deg": 0.0, "known": True} for a in (0, 180)]
        root = self._data_with_skyline(bins, observer={"longitude_east_deg": 99.0, "latitude_deg": -85.0, "reference_altitude_km": 0.0})
        result = run_from_scenario(self._terrain(NORTH), root, "t")
        self.assertEqual(result["terrain"]["reason"], "terrain_no_skyline_for_observer")
        self.assertEqual(result["samples"][0]["sun"]["state"], "unknown")

    def test_incomplete_review_is_not_used(self) -> None:
        bins = [{"azimuth_deg": a, "horizon_deg": 0.0, "known": True} for a in (0, 180)]
        root = self._data_with_skyline(bins, review={"status": "draft", "reviewer": "x", "frame": "f", "vertical_reference": "v",
                                                     "radial_coverage_m": [0, 1], "independent_check": "c"})
        result = run_from_scenario(self._terrain(NORTH), root, "t")
        self.assertEqual(result["terrain"]["reason"], "terrain_review_incomplete")

    def test_azimuth_wrap_and_parity_with_the_diagnostic_helper(self) -> None:
        raw = [(0.0, 1.0), (90.0, 2.0), (180.0, -1.0), (270.0, 0.0), (350.0, 3.0)]
        ours = [{"azimuth_deg": a, "horizon_deg": h, "known": True} for a, h in raw]
        theirs = [HorizonBin(a, h, True, 1, 100.0) for a, h in raw]
        self.assertAlmostEqual(horizon_at_azimuth(ours, 355.0)[0], 2.0)
        self.assertAlmostEqual(horizon_at_azimuth(ours, 359.0)[0], 1.2)
        for az in (0.0, 0.5, 45.0, 90.0, 179.9, 180.0, 269.0, 270.0, 300.0, 349.99, 350.0, 355.0, 359.9, 360.0, 361.0, -5.0):
            self.assertEqual(horizon_at_azimuth(ours, az), terrain_horizon_at_azimuth(theirs, az), az)
        gapped = [dict(b) for b in ours]
        gapped[2]["known"] = False
        gapped_theirs = [HorizonBin(a, h, a != 180.0, 1, 100.0) for a, h in raw]
        for az in (100.0, 200.0, 180.0):
            self.assertEqual(horizon_at_azimuth(gapped, az)[1], terrain_horizon_at_azimuth(gapped_theirs, az)[1], az)


class GeometricOutputsAreUnchanged(unittest.TestCase):
    @unittest.skipUnless((ROOT / "data" / "horizons").is_dir() and (ROOT / "web/replay/comparison.json").is_file(), "local practice bundle")
    def test_packages_equal_the_saved_replay(self) -> None:
        for pair, saved in (("practice-48h", ROOT / "web/replay"), ("practice-30d", ROOT / "web/review-candidate/cases/practice-30d")):
            with tempfile.TemporaryDirectory() as tmp:
                cli.package(Path(tmp) / "p", ROOT / "data", "t", pair=pair)
                for path in sorted((Path(tmp) / "p").rglob("*.json")):
                    fresh = json.loads(path.read_text(encoding="utf-8"))
                    kept = json.loads((saved / path.relative_to(Path(tmp) / "p")).read_text(encoding="utf-8"))

                    def strip(value):
                        if isinstance(value, dict):
                            return {k: strip(v) for k, v in value.items() if k != "code_revision"}
                        if isinstance(value, list):
                            return [strip(v) for v in value]
                        return value

                    self.assertEqual(strip(fresh), strip(kept), f"{pair} {path.name}")


if __name__ == "__main__":
    unittest.main()
