"""Build a versioned centre-ray run from saved Horizons rows."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lunar_navigator.horizons_table import index_response, load_angles_csv, response_angles
from lunar_navigator.visibility import both_lane, classify_margin

LANE_LABELS = {
    "sun": "Sun-centre clearance",
    "earth": "Earth-centre clearance",
    "both": "Both centres clear",
}
STATES = ("clear", "blocked", "unknown")
SCHEMA_VERSION = "run-result-1"


def parse_utc(value: str) -> datetime:
    if not value.endswith("Z"):
        raise ValueError(f"time must end with Z: {value}")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def empty_elapsed() -> dict[str, dict[str, int]]:
    return {lane: {state: 0 for state in STATES} for lane in ("sun", "earth", "both")}


def add_duration(elapsed: dict[str, dict[str, int]], lane: str, state: str, seconds: int) -> None:
    elapsed[lane][state] += seconds


def build_intervals(samples: list[dict], lane: str) -> list[dict]:
    intervals: list[dict] = []
    for sample in samples:
        seconds = sample["duration_seconds"]
        if seconds == 0:
            continue
        state = sample[lane]["state"]
        start = parse_utc(sample["timestamp_utc"])
        end = format_utc(start + timedelta(seconds=seconds))
        reason = sample[lane].get("reason")
        if intervals and intervals[-1]["state"] == state and intervals[-1]["end_utc"] == sample["timestamp_utc"] and intervals[-1].get("reason") == reason:
            intervals[-1]["end_utc"] = end
            continue
        row = {
            "start_utc": sample["timestamp_utc"],
            "end_utc": end,
            "lane": lane,
            "state": state,
        }
        if reason:
            row["reason"] = reason
        intervals.append(row)
    return intervals


def classify_bodies(sun_elevation, sun_azimuth, earth_elevation, earth_azimuth, sun_ref, earth_ref, sun_line, earth_line) -> dict:
    sun = classify_margin(sun_elevation, 0.0, horizon_mode="geometric_0deg")
    earth = classify_margin(earth_elevation, 0.0, horizon_mode="geometric_0deg")
    joint = both_lane(sun.state, earth.state)
    reason = None
    if joint == "unknown":
        reason = sun.reason or earth.reason or "unknown"
    elif joint == "blocked":
        blocked = [name for name, state in (("sun", sun.state), ("earth", earth.state)) if state == "blocked"]
        reason = "centre_below_or_on_horizon:" + "+".join(blocked)
    return {
        "sun": {
            "azimuth_deg": sun_azimuth,
            "elevation_deg": sun_elevation,
            "horizon_deg": sun.horizon_deg,
            "margin_deg": sun.margin_deg,
            "state": sun.state,
            "reason": sun.reason,
            "label": LANE_LABELS["sun"],
            "source_ref": sun_ref,
            "response_line": sun_line,
        },
        "earth": {
            "azimuth_deg": earth_azimuth,
            "elevation_deg": earth_elevation,
            "horizon_deg": earth.horizon_deg,
            "margin_deg": earth.margin_deg,
            "state": earth.state,
            "reason": earth.reason,
            "label": LANE_LABELS["earth"],
            "source_ref": earth_ref,
            "response_line": earth_line,
        },
        "both": {
            "state": joint,
            "reason": reason,
            "label": LANE_LABELS["both"],
        },
    }


def geometric_run_from_rows(
    *,
    site_id: str,
    observer: dict,
    start_utc: str,
    end_utc: str,
    step_seconds: int,
    rows: list[dict],
    run_id: str,
    code_revision: str | None,
    practice: bool,
    eligible_for_submission_claim: bool,
    inputs: dict,
    limitations: list[str],
    trace_utc: str | None = None,
) -> dict:
    if not rows:
        raise ValueError("no samples")
    if rows[0]["timestamp_utc"] != start_utc:
        raise ValueError(f"first timestamp {rows[0]['timestamp_utc']} != {start_utc}")
    if rows[-1]["timestamp_utc"] != end_utc:
        raise ValueError(f"last timestamp {rows[-1]['timestamp_utc']} != {end_utc}")

    samples: list[dict] = []
    elapsed = empty_elapsed()
    for index, row in enumerate(rows):
        terminal = index == len(rows) - 1
        if not terminal:
            nxt = parse_utc(rows[index + 1]["timestamp_utc"])
            current = parse_utc(row["timestamp_utc"])
            delta = int((nxt - current).total_seconds())
            if delta != step_seconds:
                raise ValueError(f"step at {row['timestamp_utc']} is {delta}s, expected {step_seconds}")
            duration = step_seconds
        else:
            duration = 0
        classified = classify_bodies(
            row["sun_elevation_deg"],
            row["sun_azimuth_deg"],
            row["earth_elevation_deg"],
            row["earth_azimuth_deg"],
            row["sun_source_ref"],
            row["earth_source_ref"],
            row.get("sun_response_line"),
            row.get("earth_response_line"),
        )
        for lane in ("sun", "earth", "both"):
            add_duration(elapsed, lane, classified[lane]["state"], duration)
        samples.append({"timestamp_utc": row["timestamp_utc"], "duration_seconds": duration, **classified})

    requested = int((parse_utc(end_utc) - parse_utc(start_utc)).total_seconds())
    for lane, totals in elapsed.items():
        if sum(totals.values()) != requested:
            raise ValueError(f"{lane} duration {sum(totals.values())} != requested {requested}")

    chosen = trace_utc or start_utc
    trace_sample = next(sample for sample in samples if sample["timestamp_utc"] == chosen)
    traces = []
    for body in ("sun", "earth"):
        item = trace_sample[body]
        traces.append(
            {
                "body": body,
                "label": LANE_LABELS[body],
                "timestamp_utc": chosen,
                "azimuth_deg": item["azimuth_deg"],
                "elevation_deg": item["elevation_deg"],
                "horizon_deg": item["horizon_deg"],
                "margin_deg": item["margin_deg"],
                "state": item["state"],
                "source_ref": item["source_ref"],
                "response_line": item["response_line"],
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "code_revision": code_revision,
        "practice": practice,
        "eligible_for_submission_claim": eligible_for_submission_claim,
        "definition": "horizons_q4_apparent_airless_target_centre",
        "labels": LANE_LABELS,
        "scenario": {
            "site_id": site_id,
            "horizon_mode": "geometric_0deg",
            "start_utc": start_utc,
            "end_utc": end_utc,
            "step_seconds": step_seconds,
            "observer": observer,
        },
        "interval_policy": {
            "id": "left_sample_both_endpoints",
            "boundary_type": "start_inclusive_end_exclusive",
            "terminal_sample_adds_seconds": 0,
        },
        "inputs": inputs,
        "samples": samples,
        "intervals": [interval for lane in ("sun", "earth", "both") for interval in build_intervals(samples, lane)],
        "elapsed_seconds": elapsed,
        "traces": traces,
        "limitations": limitations,
    }


def _match_response(utc: str, csv_azimuth: float | None, csv_elevation: float | None, line: str) -> None:
    if csv_azimuth is None or csv_elevation is None:
        return
    azimuth, elevation = response_angles(line)
    if abs(azimuth - csv_azimuth) > 1e-6 or abs(elevation - csv_elevation) > 1e-6:
        raise ValueError(f"{utc} CSV angles do not match the raw Horizons response line")


def run_from_scenario(scenario: dict, data_root: Path, code_revision: str | None) -> dict:
    observer = scenario["observer"]
    sun_dir = data_root / scenario["horizons_paths"]["sun"]
    earth_dir = data_root / scenario["horizons_paths"]["earth"]
    sun_csv = sun_dir / "angles.csv"
    earth_csv = earth_dir / "angles.csv"
    sun_response = sun_dir / "response.json"
    earth_response = earth_dir / "response.json"
    sun_rows = load_angles_csv(sun_csv)
    earth_rows = load_angles_csv(earth_csv)
    if [row["timestamp_utc"] for row in sun_rows] != [row["timestamp_utc"] for row in earth_rows]:
        raise ValueError("Sun and Earth timestamp grids differ")
    sun_lines = index_response(sun_response)
    earth_lines = index_response(earth_response)

    joined = []
    for index, (sun, earth) in enumerate(zip(sun_rows, earth_rows)):
        utc = sun["timestamp_utc"]
        sun_line = sun_lines.get(utc)
        earth_line = earth_lines.get(utc)
        if sun_line is None or earth_line is None:
            raise ValueError(f"raw Horizons response is missing {utc}")
        _match_response(utc, sun["azimuth_deg"], sun["elevation_deg"], sun_line)
        _match_response(utc, earth["azimuth_deg"], earth["elevation_deg"], earth_line)
        joined.append(
            {
                "timestamp_utc": utc,
                "sun_azimuth_deg": sun["azimuth_deg"],
                "sun_elevation_deg": sun["elevation_deg"],
                "earth_azimuth_deg": earth["azimuth_deg"],
                "earth_elevation_deg": earth["elevation_deg"],
                "sun_source_ref": f"{scenario['horizons_paths']['sun']}/angles.csv#row={index + 2}",
                "earth_source_ref": f"{scenario['horizons_paths']['earth']}/angles.csv#row={index + 2}",
                "sun_response_line": sun_line,
                "earth_response_line": earth_line,
            }
        )

    sun_prov = json.loads((sun_dir / "provenance.json").read_text(encoding="utf-8"))
    earth_prov = json.loads((earth_dir / "provenance.json").read_text(encoding="utf-8"))
    sun_csv_sha = sha256_file(sun_csv)
    earth_csv_sha = sha256_file(earth_csv)
    sun_raw_sha = sha256_file(sun_response)
    earth_raw_sha = sha256_file(earth_response)
    if sun_csv_sha != sun_prov.get("csv_sha256") or earth_csv_sha != earth_prov.get("csv_sha256"):
        raise ValueError("angle CSV SHA-256 does not match provenance")
    if sun_raw_sha != sun_prov.get("raw_sha256") or earth_raw_sha != earth_prov.get("raw_sha256"):
        raise ValueError("response.json SHA-256 does not match provenance")

    practice = scenario.get("status") == "practice" or scenario.get("eligible_for_submission_claim") is False
    eligible = bool(scenario.get("eligible_for_submission_claim", False))
    limitations = [
        "Centre-ray clearance of the target centre against the 0° local horizontal plane.",
        "Quantity 4 apparent airless angles. This is not disc visibility, received power, or ground-station contact.",
        "Terrain mode is Unknown until the M4 review. This run does not classify terrain.",
        "Appendix B raw-response digests and on-disk response.json digests are both retained. File identity of the appendix digest stays open.",
    ]
    if practice or not eligible:
        limitations.insert(0, "Practice evidence. Not an eligible submission claim.")

    return geometric_run_from_rows(
        site_id=scenario["site_id"],
        observer={
            "longitude_east_deg": observer["longitude_east_deg"],
            "latitude_deg": observer["latitude_deg"],
            "reference_altitude_km": observer["reference_altitude_km"],
            "center_body_id": observer.get("center_body_id", 301),
        },
        start_utc=scenario["start_utc"],
        end_utc=scenario["end_utc"],
        step_seconds=scenario["step_seconds"],
        rows=joined,
        run_id=f"{scenario['site_id']}-q4-centre-0deg-{sun_csv_sha[:12]}",
        code_revision=code_revision,
        practice=practice,
        eligible_for_submission_claim=eligible,
        inputs={
            "sun_csv_sha256": sun_csv_sha,
            "earth_csv_sha256": earth_csv_sha,
            "sun_response_sha256": sun_raw_sha,
            "earth_response_sha256": earth_raw_sha,
            "sun_response_matches_provenance": True,
            "earth_response_matches_provenance": True,
            "appendix_b_raw_sha256": "open_mismatch_preserved",
        },
        limitations=limitations,
        trace_utc=scenario["start_utc"],
    )


def comparison_document(site_a: dict, site_b: dict, code_revision: str | None) -> dict:
    def same(key_path: tuple[str, ...]) -> bool:
        left: object = site_a
        right: object = site_b
        for key in key_path:
            left = left[key]
            right = right[key]
        return left == right

    comparable = (
        same(("scenario", "start_utc"))
        and same(("scenario", "end_utc"))
        and same(("scenario", "step_seconds"))
        and same(("scenario", "horizon_mode"))
        and same(("interval_policy", "id"))
    )
    sun_a = site_a["elapsed_seconds"]["sun"]["clear"]
    sun_b = site_b["elapsed_seconds"]["sun"]["clear"]
    both_a = site_a["elapsed_seconds"]["both"]["clear"]
    both_b = site_b["elapsed_seconds"]["both"]["clear"]
    return {
        "schema_version": "replay-package-1",
        "practice": True,
        "eligible_for_submission_claim": False,
        "code_revision": code_revision,
        "definition": site_a["definition"],
        "labels": LANE_LABELS,
        "comparable": comparable,
        "runs": [
            {"role": "Site A", "file": f"runs/{site_a['scenario']['site_id']}.json", "run_id": site_a["run_id"]},
            {"role": "Site B", "file": f"runs/{site_b['scenario']['site_id']}.json", "run_id": site_b["run_id"]},
        ],
        "overlap": {
            "sun_centre_clear_seconds": {"site_a": sun_a, "site_b": sun_b, "delta_b_minus_a": sun_b - sun_a},
            "both_centres_clear_seconds": {"site_a": both_a, "site_b": both_b, "delta_b_minus_a": both_b - both_a},
            "unknown_seconds": {
                "site_a": {lane: site_a["elapsed_seconds"][lane]["unknown"] for lane in ("sun", "earth", "both")},
                "site_b": {lane: site_b["elapsed_seconds"][lane]["unknown"] for lane in ("sun", "earth", "both")},
            },
        },
        "limitations": [
            "Practice pair. Submission eligibility is pending.",
            "Comparison uses centre-ray 0° totals only.",
            "Product 69 is long-term context and is not a check of these windows.",
        ],
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
