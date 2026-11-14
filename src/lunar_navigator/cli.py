"""Write practice centre-ray runs and the offline replay manifest.

Each command checks response SHA-256 against provenance, then checks the raw
Horizons header so the target id and observer match the scenario.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from lunar_navigator.engine import comparison_document, run_from_scenario, write_json

REPO_ROOT = Path(__file__).resolve().parents[2]


def code_revision(explicit: str | None) -> str:
    if explicit:
        return explicit
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT,
            text=True,
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT,
            text=True,
        )
        return revision if not status.strip() else f"{revision}-dirty"
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def load_scenario(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def package(out_dir: Path, data_root: Path, revision: str) -> None:
    site_a = run_from_scenario(
        load_scenario(REPO_ROOT / "tests/fixtures/site04_p02_practice_scenario.json"),
        data_root,
        revision,
    )
    site_b = run_from_scenario(
        load_scenario(REPO_ROOT / "tests/fixtures/malapert_practice_scenario.json"),
        data_root,
        revision,
    )
    write_json(out_dir / "runs" / f"{site_a['scenario']['site_id']}.json", site_a)
    write_json(out_dir / "runs" / f"{site_b['scenario']['site_id']}.json", site_b)
    write_json(out_dir / "comparison.json", comparison_document(site_a, site_b, revision))
    print(f"run_id_a={site_a['run_id']}")
    print(f"run_id_b={site_b['run_id']}")
    print(f"package={out_dir}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=REPO_ROOT / "data")
    parser.add_argument("--revision", default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Write one scenario result")
    run.add_argument("--scenario", type=Path, required=True)
    run.add_argument("--out", type=Path, required=True)

    packed = sub.add_parser("package", help="Write Site A, Site B, and comparison.json")
    packed.add_argument("--out", type=Path, default=REPO_ROOT / "web" / "replay")

    args = parser.parse_args(argv)
    revision = code_revision(args.revision)
    if args.command == "run":
        result = run_from_scenario(load_scenario(args.scenario), args.data_root, revision)
        write_json(args.out, result)
        print(result["run_id"])
        return 0
    package(args.out, args.data_root, revision)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
