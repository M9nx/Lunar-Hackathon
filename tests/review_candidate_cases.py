"""Synthetic QA package for the local review candidate.

The rows are not Horizons output. geometric_run_from_rows classifies them so
the fixture uses the same interval policy as the engine.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lunar_navigator.engine import geometric_run_from_rows  # noqa: E402

START = "2024-06-01T00:00:00Z"
END = "2024-06-01T01:00:00Z"
STEP = 900

LIMITATIONS = [
    "QA fixture. Synthetic angles, not a Horizons table and not a landing-site result.",
    "Exercises clear, blocked, and unknown, including a missing right endpoint.",
    "The last sample adds zero elapsed seconds.",
    "No reviewed skyline. Terrain is not classified.",
    "This is not disc visibility, received power, or ground-station contact.",
]


def _row(stamp, sun_az, sun_el, earth_az, earth_el, sun_n, earth_n):
    return {
        "timestamp_utc": stamp,
        "sun_azimuth_deg": sun_az,
        "sun_elevation_deg": sun_el,
        "earth_azimuth_deg": earth_az,
        "earth_elevation_deg": earth_el,
        "sun_source_ref": f"qa-fixture/qa-north/sun#sample={sun_n}" if sun_n < 10 else f"qa-fixture/qa-south/sun#sample={sun_n}",
        "earth_source_ref": f"qa-fixture/qa-north/earth#sample={earth_n}" if earth_n < 10 else f"qa-fixture/qa-south/earth#sample={earth_n}",
        "sun_response_line": f"QA-SYNTHETIC {stamp} sun az {sun_az} el {sun_el}",
        "earth_response_line": f"QA-SYNTHETIC {stamp} earth az {earth_az} el {earth_el}",
    }


def north_rows() -> list[dict]:
    return [
        _row("2024-06-01T00:00:00Z", 10.0, 2.0, 200.0, 1.0, 1, 1),
        _row("2024-06-01T00:15:00Z", 20.0, 0.4, 210.0, -0.25, 2, 2),
        _row("2024-06-01T00:30:00Z", None, None, 220.0, 0.6, 3, 3),
        _row("2024-06-01T00:45:00Z", 40.0, -1.25, None, None, 4, 4),
        _row("2024-06-01T01:00:00Z", 45.0, 0.0, 230.0, 0.8, 5, 5),
    ]


def south_rows() -> list[dict]:
    return [
        _row("2024-06-01T00:00:00Z", 80.0, -0.5, 300.0, 0.3, 11, 11),
        _row("2024-06-01T00:15:00Z", 90.0, 1.5, 310.0, 0.7, 12, 12),
        _row("2024-06-01T00:30:00Z", 100.0, 1.0, 320.0, 0.4, 13, 13),
        _row("2024-06-01T00:45:00Z", None, None, 330.0, -0.1, 14, 14),
        _row("2024-06-01T01:00:00Z", 120.0, 0.2, 340.0, 0.5, 15, 15),
    ]


def _run(site_id: str, run_id: str, longitude: float, rows: list[dict]) -> dict:
    # Source refs above encode the site in the sample number. Rewrite south refs.
    if site_id == "qa-south":
        for row in rows:
            row["sun_source_ref"] = row["sun_source_ref"].replace("qa-north", "qa-south")
            row["earth_source_ref"] = row["earth_source_ref"].replace("qa-north", "qa-south")
    run = geometric_run_from_rows(
        site_id=site_id,
        observer={
            "longitude_east_deg": longitude,
            "latitude_deg": -89.0,
            "reference_altitude_km": 0.0,
            "center_body_id": 301,
        },
        start_utc=START,
        end_utc=END,
        step_seconds=STEP,
        rows=rows,
        run_id=run_id,
        code_revision="qa-fixture",
        practice=False,
        eligible_for_submission_claim=False,
        inputs={
            "sun_csv_sha256": "synthetic-qa-fixture",
            "earth_csv_sha256": "synthetic-qa-fixture",
            "sun_response_sha256": "synthetic-qa-fixture",
            "earth_response_sha256": "synthetic-qa-fixture",
            "sun_response_matches_provenance": False,
            "earth_response_matches_provenance": False,
            "appendix_b_raw_sha256": "not_applicable",
        },
        limitations=LIMITATIONS,
    )
    run["definition"] = "synthetic_qa_fixture"
    return run


def build_runs() -> tuple[dict, dict]:
    north = _run("qa-north", "qa-north-synthetic-transitions", 0.0, north_rows())
    south = _run("qa-south", "qa-south-synthetic-transitions", 10.0, south_rows())
    return north, south


def build_comparison(north: dict, south: dict) -> dict:
    sun_a = north["elapsed_seconds"]["sun"]["clear"]
    sun_b = south["elapsed_seconds"]["sun"]["clear"]
    both_a = north["elapsed_seconds"]["both"]["clear"]
    both_b = south["elapsed_seconds"]["both"]["clear"]
    return {
        "schema_version": "replay-package-1",
        "practice": False,
        "qa_fixture": True,
        "eligible_for_submission_claim": False,
        "code_revision": "qa-fixture",
        "definition": "synthetic_qa_fixture",
        "labels": north["labels"],
        "comparable": True,
        "runs": [
            {"role": "Site A", "file": "qa-north.json", "run_id": north["run_id"]},
            {"role": "Site B", "file": "qa-south.json", "run_id": south["run_id"]},
        ],
        "overlap": {
            "sun_centre_clear_seconds": {"site_a": sun_a, "site_b": sun_b, "delta_b_minus_a": sun_b - sun_a},
            "both_centres_clear_seconds": {"site_a": both_a, "site_b": both_b, "delta_b_minus_a": both_b - both_a},
            "unknown_seconds": {
                "site_a": {lane: north["elapsed_seconds"][lane]["unknown"] for lane in ("sun", "earth", "both")},
                "site_b": {lane: south["elapsed_seconds"][lane]["unknown"] for lane in ("sun", "earth", "both")},
            },
        },
        "limitations": LIMITATIONS,
    }
