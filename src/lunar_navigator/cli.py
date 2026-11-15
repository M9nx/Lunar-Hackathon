"""Write practice centre-ray runs and the offline replay manifest.

Each command checks response SHA-256 against provenance, then checks the raw
Horizons header so the target, observer, frame, and airless angle convention
match the scenario.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from lunar_navigator.catalog import (
    build_catalog,
    comparison_window_scenarios,
    default_roots,
    find_entry,
    root_path,
    scenario_for,
    summary_lines,
)
from lunar_navigator.engine import (
    comparison_document,
    run_from_scenario,
    stream_comparison,
    stream_scenario,
    write_json,
)
from lunar_navigator.fsio import atomic_write_json, atomic_write_json_set
from lunar_navigator.outcomes import summarize
from lunar_navigator.live_server import serve

REPO_ROOT = Path(__file__).resolve().parents[2]
WITNESSED_REPLAY = REPO_ROOT / "web" / "replay"


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


# Saved two-site pairs. Each entry is (Site A scenario, Site B scenario), relative to the repo.
PAIRS = {
    "practice-48h": (
        "tests/fixtures/site04_p02_practice_scenario.json",
        "tests/fixtures/malapert_practice_scenario.json",
    ),
    "practice-30d": (
        "tests/fixtures/site04_p02_practice_30d_scenario.json",
        "tests/fixtures/malapert_practice_30d_scenario.json",
    ),
}


def package(
    out_dir: Path,
    data_root: Path,
    revision: str,
    allow_replay: bool = False,
    pair: str = "practice-48h",
    catalog_window: str | None = None,
    start_utc: str | None = None,
    end_utc: str | None = None,
) -> None:
    if out_dir.resolve() == WITNESSED_REPLAY.resolve() and not allow_replay:
        raise SystemExit(
            "refusing to overwrite the witnessed replay (web/replay, 1f3fb06). "
            "Choose another --out, or pass --allow-replay-overwrite deliberately."
        )
    if catalog_window:
        roots = default_roots(REPO_ROOT, data_root)
        catalog = build_catalog(roots)
        scenario_a, scenario_b, window = comparison_window_scenarios(catalog, catalog_window, start_utc, end_utc)
        window_root = root_path(roots, find_entry(catalog, window["a"])["root_id"])
        site_a = run_from_scenario(scenario_a, window_root, revision)
        site_b = run_from_scenario(scenario_b, window_root, revision)
    else:
        path_a, path_b = PAIRS[pair]
        site_a = run_from_scenario(load_scenario(REPO_ROOT / path_a), data_root, revision)
        site_b = run_from_scenario(load_scenario(REPO_ROOT / path_b), data_root, revision)
    # Stage everything, then publish with renames. comparison.json goes last.
    atomic_write_json_set(
        [
            (out_dir / "runs" / f"{site_a['scenario']['site_id']}.json", site_a),
            (out_dir / "runs" / f"{site_b['scenario']['site_id']}.json", site_b),
            (out_dir / "comparison.json", comparison_document(site_a, site_b, revision)),
        ]
    )
    print(f"run_id_a={site_a['run_id']}")
    print(f"run_id_b={site_b['run_id']}")
    print(f"package={out_dir}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=REPO_ROOT / "data")
    parser.add_argument("--revision", default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Write one scenario result")
    run.add_argument("--scenario", type=Path, default=None)
    run.add_argument("--catalog", default=None, help="catalog entry id (see the catalog command) instead of --scenario")
    run.add_argument("--start", default=None, help="UTC start inside the saved coverage")
    run.add_argument("--end", default=None, help="UTC end inside the saved coverage")
    run.add_argument("--out", type=Path, required=True)

    packed = sub.add_parser("package", help="Write Site A, Site B, and comparison.json")
    packed.add_argument("--out", type=Path, default=REPO_ROOT / "web" / "replay")
    packed.add_argument("--pair", choices=sorted(PAIRS), default="practice-48h")
    packed.add_argument("--catalog-window", default=None, help="shared two-site window id from the catalog command")
    packed.add_argument("--start", default=None, help="UTC start inside the shared window")
    packed.add_argument("--end", default=None, help="UTC end inside the shared window")
    packed.add_argument(
        "--allow-replay-overwrite",
        action="store_true",
        help="Permit writing into web/replay, the witnessed 1f3fb06 package",
    )

    streamed = sub.add_parser("stream", help="Print NDJSON events for one local scenario")
    streamed.add_argument("--scenario", type=Path, required=True)
    streamed.add_argument("--batch-size", type=int, default=4)
    streamed.add_argument("--fail-after-batches", type=int, default=None)

    compared = sub.add_parser("stream-comparison", help="Print NDJSON events for a two-site live pair")
    compared.add_argument("--scenario-a", type=Path, required=True)
    compared.add_argument("--scenario-b", type=Path, required=True)
    compared.add_argument("--batch-size-a", type=int, default=4)
    compared.add_argument("--batch-size-b", type=int, default=4)
    compared.add_argument("--fail-after-batches-a", type=int, default=None)
    compared.add_argument("--fail-after-batches-b", type=int, default=None)

    listed = sub.add_parser("catalog", help="List saved Horizons data, windows and shared two-site ranges")
    listed.add_argument("--out", type=Path, default=None, help="also write the catalog JSON here (atomic)")

    seen = sub.add_parser("outcomes", help="Name Sun-only, Earth-only, Both-clear spans and crossings, with saved rows")
    seen.add_argument("--entry", required=True, help="catalog entry id")
    seen.add_argument("--start", default=None)
    seen.add_argument("--end", default=None)
    seen.add_argument("--out", type=Path, default=None, help="write the outcome summary JSON here")

    served = sub.add_parser("serve", help="Serve the review UI and local run API on loopback")
    served.add_argument("--port", type=int, default=8766)

    args = parser.parse_args(argv)
    revision = code_revision(args.revision)
    if args.command == "catalog":
        catalog = build_catalog(default_roots(REPO_ROOT, args.data_root))
        print("\n".join(summary_lines(catalog)))
        if args.out:
            atomic_write_json(args.out, catalog)
        return 1 if catalog["problems"] else 0
    if args.command == "outcomes":
        roots = default_roots(REPO_ROOT, args.data_root)
        entry = find_entry(build_catalog(roots), args.entry)
        result = run_from_scenario(scenario_for(entry, args.start, args.end), root_path(roots, entry["root_id"]), revision)
        report = summarize(result)
        for name, seconds in report["outcome_seconds"].items():
            print(f"{name:11s} {seconds / 3600:9.2f} h")
        for span in report["spans"]:
            print(f"  {span['outcome']:10s} {span['start_utc']} -> {span['end_utc']}  {span['seconds'] / 3600:.2f} h")
        if args.out:
            atomic_write_json(args.out, report)
        return 0
    if args.command == "run":
        if bool(args.scenario) == bool(args.catalog):
            parser.error("give exactly one of --scenario or --catalog")
        if args.catalog:
            roots = default_roots(REPO_ROOT, args.data_root)
            entry = find_entry(build_catalog(roots), args.catalog)
            result = run_from_scenario(scenario_for(entry, args.start, args.end), root_path(roots, entry["root_id"]), revision)
        else:
            result = run_from_scenario(load_scenario(args.scenario), args.data_root, revision)
        write_json(args.out, result)
        print(result["run_id"])
        return 0
    if args.command == "stream":
        status = 0
        for event in stream_scenario(
            load_scenario(args.scenario),
            args.data_root,
            revision,
            batch_size=args.batch_size,
            fail_after_batches=args.fail_after_batches,
        ):
            print(json.dumps(event), flush=True)
            if event["event"] == "error":
                status = 1
            elif event["event"] == "cancelled":
                status = 2
        return status
    if args.command == "stream-comparison":
        status = 0
        for event in stream_comparison(
            load_scenario(args.scenario_a),
            load_scenario(args.scenario_b),
            args.data_root,
            revision,
            batch_size_a=args.batch_size_a,
            batch_size_b=args.batch_size_b,
            fail_after_batches_a=args.fail_after_batches_a,
            fail_after_batches_b=args.fail_after_batches_b,
        ):
            print(json.dumps(event), flush=True)
            if event["event"] == "error":
                status = 1
            elif event["event"] == "cancelled":
                status = 2
        return status
    if args.command == "serve":
        serve(REPO_ROOT, args.data_root, revision, args.port)
        return 0
    package(
        args.out,
        args.data_root,
        revision,
        allow_replay=args.allow_replay_overwrite,
        pair=args.pair,
        catalog_window=args.catalog_window,
        start_utc=args.start,
        end_utc=args.end,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
