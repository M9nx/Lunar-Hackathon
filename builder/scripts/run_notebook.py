#!/usr/bin/env python3
"""Execute the code cells of an .ipynb in one fresh namespace and store the real stdout as cell outputs.

Stand-in for `jupyter nbconvert --execute`, which is not installed here. It supports plain print output only,
which is all the trace notebooks use. A failing assertion stops the run and exits 1, and the notebook on disk
is left unchanged. `--check` runs the cells without rewriting the file.

    python3 builder/scripts/run_notebook.py docs/notebooks/01_trace_observation_to_interval_total.ipynb
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("notebook", type=Path)
    parser.add_argument("--check", action="store_true", help="execute only; do not write outputs back")
    args = parser.parse_args()
    path = args.notebook if args.notebook.is_absolute() else REPO / args.notebook
    notebook = json.loads(path.read_text())
    os.chdir(REPO)
    namespace: dict = {"__name__": "__main__"}
    count = 0
    outputs: dict[int, list[dict]] = {}
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "code":
            continue
        source = "".join(cell["source"])
        count += 1
        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer):
                exec(compile(source, f"{path.name}[cell {index}]", "exec"), namespace)  # noqa: S102
        except BaseException:  # includes SystemExit from a guard cell
            sys.stdout.write(buffer.getvalue())
            traceback.print_exc()
            print(f"FAILED in cell {index}; notebook not modified", file=sys.stderr)
            return 1
        text = buffer.getvalue()
        outputs[index] = (
            [{"name": "stdout", "output_type": "stream", "text": text.splitlines(keepends=True)}] if text else []
        )
        cell["execution_count"] = count
    if not args.check:
        for index, items in outputs.items():
            notebook["cells"][index]["outputs"] = items
        path.write_text(json.dumps(notebook, indent=1) + "\n")
    print(f"executed {count} code cells OK" + (" (not written)" if args.check else f"; outputs stored in {path.relative_to(REPO)}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
