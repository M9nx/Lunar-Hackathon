"""The trace notebook must still run from a clean namespace against the saved files."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "docs/notebooks/01_trace_observation_to_interval_total.ipynb"
RUNNER = ROOT / "builder/scripts/run_notebook.py"


@unittest.skipUnless((ROOT / "data/horizons/malapert-practice-30d").is_dir(), "local 30-day Horizons exports")
class TraceNotebook(unittest.TestCase):
    def test_runs_without_writing_and_asserts_hold(self) -> None:
        before = NOTEBOOK.read_bytes()
        done = subprocess.run(
            [sys.executable, "-B", str(RUNNER), "--check", str(NOTEBOOK)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=ROOT,
        )
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("executed 7 code cells OK", done.stdout)
        self.assertEqual(NOTEBOOK.read_bytes(), before, "--check must not modify the notebook")

    def test_stored_outputs_are_present_and_free_of_errors(self) -> None:
        notebook = json.loads(NOTEBOOK.read_text())
        code = [c for c in notebook["cells"] if c["cell_type"] == "code"]
        self.assertEqual(len(code), 7)
        for cell in code:
            self.assertIsNotNone(cell["execution_count"])
            self.assertTrue(cell["outputs"], "run builder/scripts/run_notebook.py to store outputs")
            for out in cell["outputs"]:
                self.assertEqual(out["output_type"], "stream")
        joined = "".join("".join(o["text"]) for c in code for o in c["outputs"])
        self.assertIn("saved package equals the engine and the trace.", joined)


if __name__ == "__main__":
    unittest.main()
