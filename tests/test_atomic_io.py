"""Atomic publication, interruption, and input-change behaviour (Master Reference §9)."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lunar_navigator import cli, fsio  # noqa: E402
from lunar_navigator.engine import run_from_scenario, write_json  # noqa: E402

DATA = ROOT / "data"
SITE04 = ROOT / "tests/fixtures/site04_p02_practice_scenario.json"
HAVE_DATA = (DATA / "horizons" / "site04-p02-practice").is_dir()


def _leftovers(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.rglob("*") if p.name.endswith(".tmp"))


class AtomicWrite(unittest.TestCase):
    def test_previous_file_survives_unserializable_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run.json"
            write_json(path, {"v": 1})
            before = path.read_bytes()
            with self.assertRaises(TypeError):
                write_json(path, {"v": {1, 2}})
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(_leftovers(Path(tmp)), [])

    def test_interrupt_while_staging_keeps_previous_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run.json"
            write_json(path, {"v": 1})
            before = path.read_bytes()
            with mock.patch.object(fsio.os, "fsync", side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    write_json(path, {"v": 2})
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(json.loads(path.read_text())["v"], 1)
            self.assertEqual(_leftovers(Path(tmp)), [])

    def test_interrupt_before_publish_keeps_previous_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run.json"
            write_json(path, {"v": 1})
            before = path.read_bytes()
            with mock.patch.object(fsio.os, "replace", side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    write_json(path, {"v": 2})
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(_leftovers(Path(tmp)), [])

    def test_new_file_is_complete_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "run.json"
            write_json(path, {"v": 3})
            self.assertEqual(json.loads(path.read_text()), {"v": 3})
            self.assertEqual(path.stat().st_mode & 0o777, 0o644)

    def test_set_failure_while_staging_leaves_whole_previous_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            items = [(out / "a.json", {"n": 1}), (out / "b.json", {"n": 1}), (out / "comparison.json", {"n": 1})]
            fsio.atomic_write_json_set(items)
            before = {p.name: p.read_bytes() for p, _ in items}
            bad = [(out / "a.json", {"n": 2}), (out / "b.json", {"n": 2}), (out / "comparison.json", {"n": {1}})]
            with self.assertRaises(TypeError):
                fsio.atomic_write_json_set(bad)
            self.assertEqual({p.name: p.read_bytes() for p, _ in items}, before)
            self.assertEqual(_leftovers(out), [])

    def test_set_interrupt_on_last_staged_file_leaves_whole_previous_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            items = [(out / "a.json", {"n": 1}), (out / "comparison.json", {"n": 1})]
            fsio.atomic_write_json_set(items)
            before = {p.name: p.read_bytes() for p, _ in items}
            real = fsio.stage_text
            calls = {"n": 0}

            def flaky(path: Path, text: str) -> Path:
                calls["n"] += 1
                if calls["n"] == 2:
                    raise KeyboardInterrupt
                return real(path, text)

            with mock.patch.object(fsio, "stage_text", side_effect=flaky):
                with self.assertRaises(KeyboardInterrupt):
                    fsio.atomic_write_json_set([(out / "a.json", {"n": 2}), (out / "comparison.json", {"n": 2})])
            self.assertEqual({p.name: p.read_bytes() for p, _ in items}, before)
            self.assertEqual(_leftovers(out), [])


@unittest.skipUnless(HAVE_DATA, "local Horizons practice bundle")
class PackageSafety(unittest.TestCase):
    def test_package_refuses_the_witnessed_replay(self) -> None:
        replay = ROOT / "web" / "replay" / "comparison.json"
        before = hashlib.sha256(replay.read_bytes()).hexdigest()
        with self.assertRaises(SystemExit):
            cli.package(cli.WITNESSED_REPLAY, DATA, "test")
        self.assertEqual(hashlib.sha256(replay.read_bytes()).hexdigest(), before)

    def test_interrupted_package_keeps_previous_valid_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pkg"
            cli.package(out, DATA, "first")
            files = sorted(out.rglob("*.json"))
            self.assertEqual(len(files), 3)
            before = {str(p): p.read_bytes() for p in files}
            real = fsio.stage_text
            calls = {"n": 0}

            def flaky(path: Path, text: str) -> Path:
                calls["n"] += 1
                if calls["n"] == 3:
                    raise KeyboardInterrupt
                return real(path, text)

            with mock.patch.object(fsio, "stage_text", side_effect=flaky):
                with self.assertRaises(KeyboardInterrupt):
                    cli.package(out, DATA, "second")
            self.assertEqual({str(p): p.read_bytes() for p in files}, before)
            self.assertEqual(_leftovers(out), [])
            self.assertIn('"first"', (out / "comparison.json").read_text())

    def test_complete_package_is_republished_whole(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "pkg"
            cli.package(out, DATA, "first")
            cli.package(out, DATA, "second")
            self.assertIn('"second"', (out / "comparison.json").read_text())
            self.assertEqual(_leftovers(out), [])


@unittest.skipUnless(HAVE_DATA, "local Horizons practice bundle")
class InputChangeInvalidation(unittest.TestCase):
    """The run path has no result cache. Every run re-reads the inputs, so a changed
    input is rejected or yields a new run id; a stale result cannot be served."""

    def _copy(self, tmp: str) -> Path:
        root = Path(tmp) / "data"
        shutil.copytree(DATA / "horizons" / "site04-p02-practice", root / "horizons" / "site04-p02-practice")
        return root

    def test_changed_csv_byte_fails_integrity(self) -> None:
        scenario = json.loads(SITE04.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            root = self._copy(tmp)
            sun_csv = root / scenario["horizons_paths"]["sun"] / "angles.csv"
            text = sun_csv.read_text()
            sun_csv.write_text(text.replace("1.683925", "1.683926", 1))
            with self.assertRaises(ValueError) as ctx:
                run_from_scenario(scenario, root, "test")
            self.assertIn("SHA-256", str(ctx.exception))

    def test_run_id_is_a_pure_function_of_the_input_hashes(self) -> None:
        scenario = json.loads(SITE04.read_text())
        first = run_from_scenario(scenario, DATA, "one")
        second = run_from_scenario(scenario, DATA, "two")
        self.assertEqual(first["run_id"], second["run_id"])
        self.assertTrue(first["run_id"].endswith(first["inputs"]["sun_csv_sha256"][:12]))


if __name__ == "__main__":
    unittest.main()
