#!/usr/bin/env python3
"""CLI for centre-ray classification against a fixture or literal angles."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BUILDER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BUILDER_ROOT.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from lunar_navigator.visibility import ClassifiedSample, classify_margin, both_lane  # noqa: E402


def sample_to_dict(s: ClassifiedSample) -> dict:
    return {
        "state": s.state,
        "margin_deg": s.margin_deg,
        "elevation_deg": s.elevation_deg,
        "horizon_deg": s.horizon_deg,
        "reason": s.reason,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--elevation", type=float, action="append", dest="elevations")
    parser.add_argument("--horizon", type=float, default=0.0)
    parser.add_argument("--mode", default="geometric_0deg")
    parser.add_argument("--both", nargs=2, metavar=("SUN", "EARTH"), help="Two states for Both lane")
    parser.add_argument("--classified-sample", type=Path, help="JSON fixture from Master Reference")
    args = parser.parse_args()

    if args.classified_sample:
        data = json.loads(args.classified_sample.read_text(encoding="utf-8"))
        s = classify_margin(
            data.get("elevation_deg"),
            data.get("horizon_deg"),
            horizon_mode=data.get("horizon_mode", "terrain"),
        )
        print(json.dumps(sample_to_dict(s), indent=2))
        return 0 if s.state == data.get("state") else 1

    if not args.elevations:
        parser.error("provide --elevation or --classified-sample")

    for e in args.elevations:
        s = classify_margin(e, args.horizon, horizon_mode=args.mode)
        print(f"elev={e} -> {json.dumps(sample_to_dict(s))}")

    if args.both:
        print(f"both={both_lane(args.both[0], args.both[1])}")  # type: ignore[arg-type]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())