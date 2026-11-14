#!/usr/bin/env python3
"""Verify saved Horizons exports against a scenario record."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

BUILDER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BUILDER_ROOT.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lunar_navigator.visibility import validate_body_id  # noqa: E402


def parse_horizons_url(url: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in url.split("&"):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        out[k] = unquote(v).strip("'")
    return out


def command_id(params: dict[str, str]) -> int | None:
    cmd = params.get("COMMAND", "")
    m = re.search(r"(\d+)", cmd)
    return int(m.group(1)) if m else None


def load_csv_grid(path: Path) -> tuple[list[str], int]:
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return [], 0
    times = [r["timestamp_utc"] for r in rows]
    return times, len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, default=REPO_ROOT / "data")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    scenario = json.loads(args.scenario.read_text(encoding="utf-8"))
    obs = scenario["observer"]
    errors: list[str] = []
    report: dict = {"scenario": scenario.get("site_id"), "bodies": {}}

    for body, rel in scenario["horizons_paths"].items():
        folder = args.data_root / rel
        prov_path = folder / "provenance.json"
        csv_path = folder / "angles.csv"
        body_report: dict = {"path": str(folder)}
        if not prov_path.is_file():
            errors.append(f"missing provenance: {prov_path}")
            continue
        prov = json.loads(prov_path.read_text(encoding="utf-8"))
        params = parse_horizons_url(prov.get("request_url", ""))

        if params.get("CENTER") != "coord@301":
            errors.append(f"{body}: expected CENTER=coord@301 got {params.get('CENTER')}")
        if params.get("COORD_TYPE") != "GEODETIC":
            errors.append(f"{body}: COORD_TYPE not GEODETIC")
        if params.get("QUANTITIES") != "4":
            errors.append(f"{body}: QUANTITIES not 4")

        cid = command_id(params)
        if cid is None or not validate_body_id(body, cid):
            errors.append(f"{body}: COMMAND id {cid} invalid for centre-ray")

        # Observer tuple in provenance
        o = prov.get("observer")
        if o and len(o) == 3:
            if abs(o[0] - obs["longitude_east_deg"]) > 1e-4:
                errors.append(f"{body}: longitude mismatch")
            if abs(o[1] - obs["latitude_deg"]) > 1e-4:
                errors.append(f"{body}: latitude mismatch")
            if abs(o[2] - obs["reference_altitude_km"]) > 1e-6:
                errors.append(f"{body}: altitude mismatch")

        if csv_path.is_file():
            times, count = load_csv_grid(csv_path)
            body_report["row_count"] = count
            step = scenario.get("step_seconds", 900)
            if count != scenario.get("expected_row_count"):
                errors.append(f"{body}: row_count {count} != expected {scenario.get('expected_row_count')}")
            if times:
                body_report["first_utc"] = times[0]
                body_report["last_utc"] = times[-1]
                if times[0] != scenario["start_utc"]:
                    errors.append(f"{body}: first timestamp {times[0]} != {scenario['start_utc']}")

        # Hash integrity vs provenance
        if csv_path.is_file() and prov.get("csv_sha256"):
            digest = hashlib.sha256(csv_path.read_bytes()).hexdigest()
            if digest != prov["csv_sha256"]:
                errors.append(f"{body}: csv sha256 mismatch")

        body_report["practice"] = prov.get("practice", False)
        report["bodies"][body] = body_report

    report["eligible_for_submission_claim"] = scenario.get("eligible_for_submission_claim", False)
    report["errors"] = errors
    report["pass"] = not errors

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"site={report['scenario']} pass={report['pass']}")
        for e in errors:
            print(f"  FAIL {e}")

    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())