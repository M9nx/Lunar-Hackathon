"""Build a versioned centre-ray run from saved Horizons rows."""

from __future__ import annotations

import copy
import hashlib
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lunar_navigator.fsio import atomic_write_json
from lunar_navigator.horizons_table import (
    index_result_text,
    load_angles_csv,
    load_response_text,
    parse_response_header,
    response_angles,
)
from lunar_navigator.skyline import HorizonSource
from lunar_navigator.visibility import ClassifiedSample, both_lane, classify_margin, validate_body_id

LANE_LABELS = {
    "sun": "Sun-centre clearance",
    "earth": "Earth-centre clearance",
    "both": "Both centres clear",
}
STATES = ("clear", "blocked", "unknown")
SCHEMA_VERSION = "run-result-1"
# Horizons prints the center-geodetic line to about four decimal places.
HEADER_ANGLE_TOL_DEG = 5e-4
HEADER_ALTITUDE_TOL_KM = 5e-4


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


def joint_lane(sun_state: str, earth_state: str, sun_reason: str | None, earth_reason: str | None) -> dict:
    joint = both_lane(sun_state, earth_state)
    if joint == "unknown":
        reason = sun_reason or earth_reason or "unknown"
    elif joint == "blocked":
        blocked = [name for name, state in (("sun", sun_state), ("earth", earth_state)) if state == "blocked"]
        reason = "centre_below_or_on_horizon:" + "+".join(blocked)
    else:
        reason = None
    return {"state": joint, "reason": reason, "label": LANE_LABELS["both"]}


def classify_one(elevation, azimuth, horizon: HorizonSource | None) -> ClassifiedSample:
    """One body against the baseline or a reviewed skyline.

    A missing elevation is Unknown (missing_ephemeris). In terrain mode with no usable horizon the body is
    Unknown with the terrain reason; the elevation stays on the record, the horizon and margin stay empty.
    """
    if horizon is None or horizon.mode == "geometric_0deg":
        return classify_margin(elevation, 0.0, horizon_mode="geometric_0deg")
    if elevation is None:
        return classify_margin(None, None, horizon_mode="terrain")
    value, reason = horizon.horizon_at(azimuth)
    if value is None:
        return ClassifiedSample(elevation, None, "unknown", None, reason or "terrain_not_reviewed")
    return classify_margin(elevation, value, horizon_mode="terrain")


def classify_bodies(sun_elevation, sun_azimuth, earth_elevation, earth_azimuth, sun_ref, earth_ref, sun_line, earth_line, horizon: HorizonSource | None = None) -> dict:
    sun = classify_one(sun_elevation, sun_azimuth, horizon)
    earth = classify_one(earth_elevation, earth_azimuth, horizon)
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
        "both": joint_lane(sun.state, earth.state, sun.reason, earth.reason),
    }


def _angles_usable(azimuth, elevation) -> bool:
    return azimuth is not None and elevation is not None


def apply_both_endpoints(classified: dict, nxt: dict | None) -> None:
    """Keep the left sample's state only when the next sample has usable angles.

    The span is half-open. A missing right endpoint makes that body's interval
    Unknown. The left sample's angles stay on the record.
    """
    if nxt is None:
        return
    endpoints = (
        ("sun", "sun_azimuth_deg", "sun_elevation_deg"),
        ("earth", "earth_azimuth_deg", "earth_elevation_deg"),
    )
    for body, azimuth_key, elevation_key in endpoints:
        left_ok = _angles_usable(classified[body]["azimuth_deg"], classified[body]["elevation_deg"])
        right_ok = _angles_usable(nxt[azimuth_key], nxt[elevation_key])
        if left_ok and right_ok:
            continue
        if left_ok and classified[body]["state"] == "unknown" and classified[body]["reason"]:
            continue  # already Unknown for a terrain reason; keep that reason
        classified[body]["state"] = "unknown"
        if left_ok:
            classified[body]["reason"] = "missing_right_endpoint"
        else:
            classified[body]["reason"] = classified[body]["reason"] or "missing_ephemeris"
    classified["both"] = joint_lane(
        classified["sun"]["state"],
        classified["earth"]["state"],
        classified["sun"]["reason"],
        classified["earth"]["reason"],
    )


def classify_sample(row: dict, nxt: dict | None, *, step_seconds: int, horizon: HorizonSource | None = None) -> dict:
    """Classify one sample. The next row is required for every span except the terminal sample."""
    if nxt is None:
        duration = 0
    else:
        delta = int((parse_utc(nxt["timestamp_utc"]) - parse_utc(row["timestamp_utc"])).total_seconds())
        if delta != step_seconds:
            raise ValueError(f"step at {row['timestamp_utc']} is {delta}s, expected {step_seconds}")
        duration = step_seconds
    classified = classify_bodies(
        row["sun_elevation_deg"],
        row["sun_azimuth_deg"],
        row["earth_elevation_deg"],
        row["earth_azimuth_deg"],
        row["sun_source_ref"],
        row["earth_source_ref"],
        row.get("sun_response_line"),
        row.get("earth_response_line"),
        horizon,
    )
    apply_both_endpoints(classified, nxt)
    return {"timestamp_utc": row["timestamp_utc"], "duration_seconds": duration, **classified}


def elapsed_from_samples(samples: list[dict]) -> dict[str, dict[str, int]]:
    elapsed = empty_elapsed()
    for sample in samples:
        for lane in ("sun", "earth", "both"):
            add_duration(elapsed, lane, sample[lane]["state"], sample["duration_seconds"])
    return elapsed


def intervals_from_samples(samples: list[dict]) -> list[dict]:
    return [interval for lane in ("sun", "earth", "both") for interval in build_intervals(samples, lane)]


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
    horizon: HorizonSource | None = None,
) -> dict:
    if not rows:
        raise ValueError("no samples")
    if rows[0]["timestamp_utc"] != start_utc:
        raise ValueError(f"first timestamp {rows[0]['timestamp_utc']} != {start_utc}")
    if rows[-1]["timestamp_utc"] != end_utc:
        raise ValueError(f"last timestamp {rows[-1]['timestamp_utc']} != {end_utc}")

    samples = [
        classify_sample(row, None if index == len(rows) - 1 else rows[index + 1], step_seconds=step_seconds, horizon=horizon)
        for index, row in enumerate(rows)
    ]
    elapsed = elapsed_from_samples(samples)
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

    terrain_block = horizon.describe() if horizon is not None else None
    result = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "code_revision": code_revision,
        "practice": practice,
        "eligible_for_submission_claim": eligible_for_submission_claim,
        "definition": "horizons_q4_apparent_airless_target_centre",
        "labels": LANE_LABELS,
        "scenario": {
            "site_id": site_id,
            "horizon_mode": horizon.mode if horizon is not None else "geometric_0deg",
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
    if terrain_block is not None:
        result["terrain"] = terrain_block
    return result


def _east_longitude_delta_deg(left: float, right: float) -> float:
    return abs((left - right + 180.0) % 360.0 - 180.0)


def verify_response_belongs_to_case(
    result: str,
    *,
    body: str,
    observer: dict,
    observer_frame: str,
    angle_convention: str,
) -> None:
    """Reject a response whose target, observer, frame, or angles are not the scenario's case.

    SHA-256 checks that the bytes match provenance. This check reads the raw
    header so a swapped Sun and Earth export, or a reframed or refracted table,
    cannot pass on checksums alone.
    """
    meta = parse_response_header(result)
    if not validate_body_id(body, meta["target_id"]):
        raise ValueError(f"{body} response target id {meta['target_id']} does not match the scenario")
    expected_center = int(observer.get("center_body_id", 301))
    if expected_center == 3 or meta["center_body_id"] != expected_center:
        raise ValueError(
            f"{body} response center body {meta['center_body_id']} does not match the scenario observer"
        )
    if _east_longitude_delta_deg(meta["longitude_east_deg"], float(observer["longitude_east_deg"])) > HEADER_ANGLE_TOL_DEG:
        raise ValueError(f"{body} response longitude does not match the scenario observer")
    if abs(meta["latitude_deg"] - float(observer["latitude_deg"])) > HEADER_ANGLE_TOL_DEG:
        raise ValueError(f"{body} response latitude does not match the scenario observer")
    if abs(meta["reference_altitude_km"] - float(observer["reference_altitude_km"])) > HEADER_ALTITUDE_TOL_KM:
        raise ValueError(f"{body} response altitude does not match the scenario observer")
    if not observer_frame or meta["observer_frame"] != observer_frame:
        raise ValueError(
            f"{body} response observer frame {meta['observer_frame']} does not match the scenario"
        )
    if angle_convention != "airless_apparent" or not meta["airless_apparent"]:
        raise ValueError(f"{body} response angle convention does not match the scenario")


def _match_response(utc: str, csv_azimuth: float | None, csv_elevation: float | None, line: str) -> None:
    """The saved CSV row and the raw Horizons line must agree, including that both have no angle."""
    azimuth, elevation = response_angles(line)
    csv_missing = csv_azimuth is None or csv_elevation is None
    raw_missing = azimuth is None or elevation is None
    if csv_missing != raw_missing:
        raise ValueError(
            f"{utc} CSV row is {'missing' if csv_missing else 'present'} but the raw Horizons line is "
            f"{'missing' if raw_missing else 'present'}"
        )
    if csv_missing:
        return
    if abs(azimuth - csv_azimuth) > 1e-6 or abs(elevation - csv_elevation) > 1e-6:
        raise ValueError(f"{utc} CSV angles do not match the raw Horizons response line")


def select_time_window(rows: list[dict], start_utc: str, end_utc: str, step_seconds: int) -> list[dict]:
    """Keep the saved rows that fall on the scenario's inclusive UTC window."""
    stamps = [row["timestamp_utc"] for row in rows]
    if start_utc not in stamps:
        raise ValueError(f"saved Horizons grid does not include scenario start {start_utc}")
    if end_utc not in stamps:
        raise ValueError(f"saved Horizons grid does not include scenario end {end_utc}")
    start_index = stamps.index(start_utc)
    end_index = stamps.index(end_utc)
    if end_index <= start_index:
        raise ValueError(f"scenario end {end_utc} is not after start {start_utc} on the saved grid")
    selected = rows[start_index : end_index + 1]
    for left, right in zip(selected, selected[1:]):
        delta = int((parse_utc(right["timestamp_utc"]) - parse_utc(left["timestamp_utc"])).total_seconds())
        if delta != int(step_seconds):
            raise ValueError(f"time grid step at {left['timestamp_utc']} is {delta}s, expected {step_seconds}s")
    return selected


def content_run_id(site_id: str, sun_csv_sha: str, *, full_grid: bool, start_utc: str, end_utc: str, mode: str = "geometric_0deg") -> str:
    base = f"{site_id}-q4-centre-0deg-{sun_csv_sha[:12]}" if mode == "geometric_0deg" else f"{site_id}-q4-centre-terrain-{sun_csv_sha[:12]}"
    if full_grid:
        return base
    start = start_utc.replace("-", "").replace(":", "")
    end = end_utc.replace("-", "").replace(":", "")
    return f"{base}-{start}-{end}"


def load_scenario_inputs(scenario: dict, data_root: Path, code_revision: str | None) -> dict:
    """Read and check saved Horizons inputs. This does not classify samples."""
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
    sun_text = load_response_text(sun_response)
    earth_text = load_response_text(earth_response)
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
    verify_response_belongs_to_case(
        sun_text,
        body="sun",
        observer=observer,
        observer_frame=scenario.get("observer_frame", ""),
        angle_convention=scenario.get("angle_convention", ""),
    )
    verify_response_belongs_to_case(
        earth_text,
        body="earth",
        observer=observer,
        observer_frame=scenario.get("observer_frame", ""),
        angle_convention=scenario.get("angle_convention", ""),
    )
    sun_lines = index_result_text(sun_text, sun_response)
    earth_lines = index_result_text(earth_text, earth_response)

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
    horizon = HorizonSource.for_observer(scenario.get("horizon_mode", "geometric_0deg"), observer, data_root)
    full_grid = True
    if joined[0]["timestamp_utc"] != scenario["start_utc"] or joined[-1]["timestamp_utc"] != scenario["end_utc"]:
        joined = select_time_window(joined, scenario["start_utc"], scenario["end_utc"], scenario["step_seconds"])
        full_grid = False

    eligible = bool(scenario.get("eligible_for_submission_claim", False))
    practice = scenario.get("status") == "practice" or not eligible
    limitations = [
        "Centre-ray clearance of the target centre against the 0° local horizontal plane.",
        "Quantity 4 apparent airless angles. This is not disc visibility, received power, or ground-station contact.",
        "Terrain mode is Unknown until the M4 review. This run does not classify terrain.",
        "Appendix B raw-response digests and on-disk response.json digests are both retained. File identity of the appendix digest stays open.",
    ]
    if not eligible:
        limitations.insert(0, "Practice evidence. Not an eligible submission claim.")
    elif practice:
        limitations.insert(
            0,
            "Lead approved these Horizons practice runs for a submission claim. Centre-ray 0° only; terrain Unknown; disc/power/contact not claimed.",
        )
    if horizon.mode == "terrain" and horizon.skyline is None:
        limitations.insert(
            0,
            f"Terrain mode requested. {horizon.reason}: {horizon.detail}. Every state is Unknown. The saved Horizons "
            "elevation is kept; no horizon or margin is shown and no 0 degree baseline is substituted.",
        )
    synthetic = bool(scenario.get("synthetic", False))
    if synthetic:
        limitations.insert(
            0, scenario.get("synthetic_note") or "SYNTHETIC QA fixture. Not Horizons output and not a result about the Moon."
        )

    return {
        "site_id": scenario["site_id"],
        "observer": {
            "longitude_east_deg": observer["longitude_east_deg"],
            "latitude_deg": observer["latitude_deg"],
            "reference_altitude_km": observer["reference_altitude_km"],
            "center_body_id": observer.get("center_body_id", 301),
        },
        "start_utc": scenario["start_utc"],
        "end_utc": scenario["end_utc"],
        "step_seconds": scenario["step_seconds"],
        "rows": joined,
        "horizon": horizon,
        "run_id": content_run_id(
            scenario["site_id"],
            sun_csv_sha,
            full_grid=full_grid and horizon.mode == "geometric_0deg",
            start_utc=scenario["start_utc"],
            end_utc=scenario["end_utc"],
            mode=horizon.mode,
        ),
        "code_revision": code_revision,
        "practice": practice,
        "eligible_for_submission_claim": eligible,
        "inputs": {
            "sun_csv_sha256": sun_csv_sha,
            "earth_csv_sha256": earth_csv_sha,
            "sun_response_sha256": sun_raw_sha,
            "earth_response_sha256": earth_raw_sha,
            "sun_response_matches_provenance": True,
            "earth_response_matches_provenance": True,
            "appendix_b_raw_sha256": (
                "open_mismatch_preserved" if scenario.get("in_appendix_b", True) else "not_in_appendix_b"
            ),
            **({"synthetic": True} if synthetic else {}),
        },
        "limitations": limitations,
        "trace_utc": scenario["start_utc"],
    }


def run_from_scenario(scenario: dict, data_root: Path, code_revision: str | None) -> dict:
    """Classify one scenario from matching saved Horizons inputs."""
    prepared = load_scenario_inputs(scenario, data_root, code_revision)
    rows = prepared.pop("rows")
    return geometric_run_from_rows(rows=rows, **prepared)


def assert_comparable_grids(left: dict, right: dict) -> None:
    """Reject two scenarios that do not share a UTC grid and horizon mode."""
    checks = (
        ("start_utc", left.get("start_utc"), right.get("start_utc")),
        ("end_utc", left.get("end_utc"), right.get("end_utc")),
        ("step_seconds", left.get("step_seconds"), right.get("step_seconds")),
        ("horizon_mode", left.get("horizon_mode", "geometric_0deg"), right.get("horizon_mode", "geometric_0deg")),
    )
    for name, left_value, right_value in checks:
        if left_value != right_value:
            raise ValueError(f"incompatible time grids: {name} {left_value} != {right_value}")


def overlap_from_elapsed(elapsed_a: dict, elapsed_b: dict) -> dict:
    sun_a = elapsed_a["sun"]["clear"]
    sun_b = elapsed_b["sun"]["clear"]
    both_a = elapsed_a["both"]["clear"]
    both_b = elapsed_b["both"]["clear"]
    return {
        "sun_centre_clear_seconds": {"site_a": sun_a, "site_b": sun_b, "delta_b_minus_a": sun_b - sun_a},
        "both_centres_clear_seconds": {"site_a": both_a, "site_b": both_b, "delta_b_minus_a": both_b - both_a},
        "unknown_seconds": {
            "site_a": {lane: elapsed_a[lane]["unknown"] for lane in ("sun", "earth", "both")},
            "site_b": {lane: elapsed_b[lane]["unknown"] for lane in ("sun", "earth", "both")},
        },
    }


def shared_elapsed(emitted_a: list[dict], emitted_b: list[dict]) -> tuple[int, dict, dict]:
    """Totals only over the UTC prefix both sites have resolved."""
    shared = min(len(emitted_a), len(emitted_b))
    for index in range(shared):
        if emitted_a[index]["timestamp_utc"] != emitted_b[index]["timestamp_utc"]:
            raise ValueError(
                "incompatible time grids: shared sample "
                f"{emitted_a[index]['timestamp_utc']} != {emitted_b[index]['timestamp_utc']}"
            )
    return shared, elapsed_from_samples(emitted_a[:shared]), elapsed_from_samples(emitted_b[:shared])


def cutoff_fields(samples: list[dict]) -> dict:
    """Last resolved sample and the end of its interval. Both are null before any sample.

    Totals through a cutoff count each sample for its own interval, so they cover
    [start, covered_through_utc). The terminal sample adds 0 s.
    """
    if not samples:
        return {"cutoff_utc": None, "covered_through_utc": None}
    last = samples[-1]
    end = parse_utc(last["timestamp_utc"]) + timedelta(seconds=last["duration_seconds"])
    return {"cutoff_utc": last["timestamp_utc"], "covered_through_utc": format_utc(end)}


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
    eligible = bool(site_a.get("eligible_for_submission_claim") and site_b.get("eligible_for_submission_claim"))
    eligibility_note = (
        "Lead approved this practice pair for a submission claim. Centre-ray 0° only; terrain Unknown; disc/power/contact not claimed."
        if eligible
        else "Practice pair. Submission eligibility is pending."
    )
    return {
        "schema_version": "replay-package-1",
        "practice": bool(site_a.get("practice") or site_b.get("practice")),
        "eligible_for_submission_claim": eligible,
        "code_revision": code_revision,
        "definition": site_a["definition"],
        "labels": LANE_LABELS,
        "comparable": comparable,
        "runs": [
            {"role": "Site A", "file": f"runs/{site_a['scenario']['site_id']}.json", "run_id": site_a["run_id"]},
            {"role": "Site B", "file": f"runs/{site_b['scenario']['site_id']}.json", "run_id": site_b["run_id"]},
        ],
        "overlap": overlap_from_elapsed(site_a["elapsed_seconds"], site_b["elapsed_seconds"]),
        "limitations": [
            eligibility_note,
            "Comparison uses centre-ray 0° totals only.",
            "Product 69 is long-term context and is not a check of these windows.",
        ],
    }


def write_json(path: Path, payload: dict) -> None:
    """Atomic: a failed or interrupted write keeps the previous valid file."""
    atomic_write_json(path, payload)


def _batch_event(run_id: str, result_run_id: str, batch_index: int, batch: list[dict], emitted: list[dict]) -> dict:
    return {
        "event": "batch",
        "run_id": run_id,
        "result_run_id": result_run_id,
        "batch_index": batch_index,
        "stage": "calculating",
        "complete": False,
        "partial": True,
        "samples": batch,
        "samples_emitted": len(emitted),
        "elapsed_seconds": copy.deepcopy(elapsed_from_samples(emitted)),
        "intervals": intervals_from_samples(emitted),
        **cutoff_fields(emitted),
    }


def stream_scenario(
    scenario: dict,
    data_root: Path,
    code_revision: str | None,
    *,
    batch_size: int = 4,
    cancel=None,
    fail_after_batches: int | None = None,
    pause_seconds: float = 0,
    run_id: str | None = None,
):
    """Yield loading, metadata, ordered batches, then complete, cancelled, or error.

    A sample is emitted only after the next timestamp has been seen, except the
    terminal sample. ``cancel`` is a threading.Event. ``pause_seconds`` waits
    between batches so a caller can cancel before the next batch.
    """
    if batch_size < 1:
        raise ValueError("batch_size must be at least 1")
    run_id = run_id or uuid.uuid4().hex[:12]
    yield {"event": "stage", "run_id": run_id, "stage": "loading_inputs", "complete": False, "partial": True}
    try:
        prepared = load_scenario_inputs(scenario, data_root, code_revision)
    except ValueError as exc:
        yield {
            "event": "error",
            "run_id": run_id,
            "stage": "failed",
            "complete": False,
            "partial": True,
            "message": str(exc),
            "samples_emitted": 0,
        }
        return

    rows = prepared["rows"]
    result_run_id = prepared["run_id"]
    yield {
        "event": "metadata",
        "run_id": run_id,
        "result_run_id": result_run_id,
        "stage": "calculating",
        "complete": False,
        "partial": True,
        "sample_count": len(rows),
        "code_revision": prepared["code_revision"],
        "labels": LANE_LABELS,
        **({"terrain": prepared["horizon"].describe()} if prepared["horizon"].describe() else {}),
        "scenario": {
            "site_id": prepared["site_id"],
            "horizon_mode": prepared["horizon"].mode,
            "start_utc": prepared["start_utc"],
            "end_utc": prepared["end_utc"],
            "step_seconds": prepared["step_seconds"],
            "observer": prepared["observer"],
        },
        "practice": prepared["practice"],
        "eligible_for_submission_claim": prepared["eligible_for_submission_claim"],
    }

    emitted: list[dict] = []
    batch: list[dict] = []
    batch_index = 0

    def cancelled_event() -> dict:
        return {
            "event": "cancelled",
            "run_id": run_id,
            "result_run_id": result_run_id,
            "stage": "cancelled",
            "complete": False,
            "partial": True,
            "message": "run cancelled",
            "samples_emitted": len(emitted),
            "elapsed_seconds": copy.deepcopy(elapsed_from_samples(emitted)),
            "intervals": intervals_from_samples(emitted),
            **cutoff_fields(emitted),
        }

    def failed_event() -> dict:
        return {
            "event": "error",
            "run_id": run_id,
            "result_run_id": result_run_id,
            "stage": "failed",
            "complete": False,
            "partial": True,
            "message": f"calculation failed after batch {batch_index}",
            "samples_emitted": len(emitted),
            "elapsed_seconds": copy.deepcopy(elapsed_from_samples(emitted)),
            "intervals": intervals_from_samples(emitted),
            **cutoff_fields(emitted),
        }

    for index, row in enumerate(rows):
        if cancel is not None and cancel.is_set():
            yield cancelled_event()
            return
        if pause_seconds and emitted and not batch:
            if cancel is not None and cancel.wait(pause_seconds):
                yield cancelled_event()
                return
            if cancel is None:
                time.sleep(pause_seconds)
        nxt = None if index == len(rows) - 1 else rows[index + 1]
        sample = classify_sample(row, nxt, step_seconds=prepared["step_seconds"], horizon=prepared["horizon"])
        batch.append(sample)
        emitted.append(sample)
        if len(batch) == batch_size:
            yield _batch_event(run_id, result_run_id, batch_index, batch, emitted)
            if fail_after_batches is not None and batch_index + 1 >= fail_after_batches:
                yield failed_event()
                return
            batch = []
            batch_index += 1

    if batch:
        yield _batch_event(run_id, result_run_id, batch_index, batch, emitted)
        if fail_after_batches is not None and batch_index + 1 >= fail_after_batches:
            yield failed_event()
            return
    finished = geometric_run_from_rows(rows=rows, **{key: value for key, value in prepared.items() if key != "rows"})
    yield {
        "event": "complete",
        "run_id": run_id,
        "result_run_id": result_run_id,
        "stage": "complete",
        "complete": True,
        "partial": False,
        "result": finished,
    }


def _site_batch_event(
    *,
    comparison_id: str,
    role: str,
    run_id: str,
    result_run_id: str,
    batch_index: int,
    batch: list[dict],
    emitted: list[dict],
    emitted_a: list[dict],
    emitted_b: list[dict],
) -> dict:
    shared, elapsed_a, elapsed_b = shared_elapsed(emitted_a, emitted_b)
    return {
        "event": "site_batch",
        "comparison_id": comparison_id,
        "role": role,
        "run_id": run_id,
        "result_run_id": result_run_id,
        "batch_index": batch_index,
        "stage": "calculating",
        "complete": False,
        "partial": True,
        "samples": batch,
        "samples_emitted": len(emitted),
        "elapsed_seconds": copy.deepcopy(elapsed_from_samples(emitted)),
        "intervals": intervals_from_samples(emitted),
        "shared_samples": shared,
        **cutoff_fields(emitted_a[:shared]),
        "comparison_partial": True,
        "comparison_elapsed": {
            "site_a": copy.deepcopy(elapsed_a),
            "site_b": copy.deepcopy(elapsed_b),
        },
        "overlap": overlap_from_elapsed(elapsed_a, elapsed_b),
    }


def stream_comparison(
    scenario_a: dict,
    scenario_b: dict,
    data_root: Path,
    code_revision: str | None,
    *,
    batch_size_a: int = 4,
    batch_size_b: int = 4,
    cancel=None,
    fail_after_batches_a: int | None = None,
    fail_after_batches_b: int | None = None,
    pause_seconds: float = 0,
    comparison_id: str | None = None,
    run_id_a: str | None = None,
    run_id_b: str | None = None,
):
    """Yield a two-site live run on a shared UTC grid.

    Comparison totals use only the shared resolved sample prefix. Pending samples
    are not scientific Unknown. A complete comparison export is emitted only when
    both sites finish.
    """
    if batch_size_a < 1 or batch_size_b < 1:
        raise ValueError("batch_size must be at least 1")
    comparison_id = comparison_id or uuid.uuid4().hex[:12]
    run_id_a = run_id_a or uuid.uuid4().hex[:12]
    run_id_b = run_id_b or uuid.uuid4().hex[:12]
    yield {
        "event": "stage",
        "comparison_id": comparison_id,
        "run_id_a": run_id_a,
        "run_id_b": run_id_b,
        "stage": "loading_inputs",
        "complete": False,
        "partial": True,
    }
    try:
        assert_comparable_grids(
            {
                "start_utc": scenario_a.get("start_utc"),
                "end_utc": scenario_a.get("end_utc"),
                "step_seconds": scenario_a.get("step_seconds"),
                "horizon_mode": scenario_a.get("horizon_mode", "geometric_0deg"),
            },
            {
                "start_utc": scenario_b.get("start_utc"),
                "end_utc": scenario_b.get("end_utc"),
                "step_seconds": scenario_b.get("step_seconds"),
                "horizon_mode": scenario_b.get("horizon_mode", "geometric_0deg"),
            },
        )
        prepared_a = load_scenario_inputs(scenario_a, data_root, code_revision)
        prepared_b = load_scenario_inputs(scenario_b, data_root, code_revision)
        assert_comparable_grids(
            {
                "start_utc": prepared_a["start_utc"],
                "end_utc": prepared_a["end_utc"],
                "step_seconds": prepared_a["step_seconds"],
                "horizon_mode": prepared_a["horizon"].mode,
            },
            {
                "start_utc": prepared_b["start_utc"],
                "end_utc": prepared_b["end_utc"],
                "step_seconds": prepared_b["step_seconds"],
                "horizon_mode": prepared_b["horizon"].mode,
            },
        )
        stamps_a = [row["timestamp_utc"] for row in prepared_a["rows"]]
        stamps_b = [row["timestamp_utc"] for row in prepared_b["rows"]]
        if stamps_a != stamps_b:
            raise ValueError("incompatible time grids: sample timestamps differ")
    except ValueError as exc:
        yield {
            "event": "error",
            "comparison_id": comparison_id,
            "run_id_a": run_id_a,
            "run_id_b": run_id_b,
            "stage": "failed",
            "complete": False,
            "partial": True,
            "message": str(exc),
            "samples_emitted_a": 0,
            "samples_emitted_b": 0,
            "shared_samples": 0,
            **cutoff_fields([]),
        }
        return

    rows_a = prepared_a["rows"]
    rows_b = prepared_b["rows"]
    result_run_id_a = prepared_a["run_id"]
    result_run_id_b = prepared_b["run_id"]

    def site_meta(prepared: dict, role: str, run_id: str, result_run_id: str) -> dict:
        return {
            "role": role,
            "run_id": run_id,
            "result_run_id": result_run_id,
            "sample_count": len(prepared["rows"]),
            "code_revision": prepared["code_revision"],
            "labels": LANE_LABELS,
            "scenario": {
                "site_id": prepared["site_id"],
                "horizon_mode": prepared["horizon"].mode,
                "start_utc": prepared["start_utc"],
                "end_utc": prepared["end_utc"],
                "step_seconds": prepared["step_seconds"],
                "observer": prepared["observer"],
            },
            "practice": prepared["practice"],
            "eligible_for_submission_claim": prepared["eligible_for_submission_claim"],
            **({"terrain": prepared["horizon"].describe()} if prepared["horizon"].describe() else {}),
        }

    yield {
        "event": "metadata",
        "comparison_id": comparison_id,
        "run_id_a": run_id_a,
        "run_id_b": run_id_b,
        "stage": "calculating",
        "complete": False,
        "partial": True,
        "sites": [
            site_meta(prepared_a, "site_a", run_id_a, result_run_id_a),
            site_meta(prepared_b, "site_b", run_id_b, result_run_id_b),
        ],
        "practice": prepared_a["practice"] or prepared_b["practice"],
        "eligible_for_submission_claim": bool(
            prepared_a["eligible_for_submission_claim"] and prepared_b["eligible_for_submission_claim"]
        ),
        "labels": LANE_LABELS,
    }

    emitted_a: list[dict] = []
    emitted_b: list[dict] = []
    batch_a: list[dict] = []
    batch_b: list[dict] = []
    batch_index_a = 0
    batch_index_b = 0

    def cancelled_event() -> dict:
        shared, elapsed_shared_a, elapsed_shared_b = shared_elapsed(emitted_a, emitted_b)
        return {
            "event": "cancelled",
            "comparison_id": comparison_id,
            "run_id_a": run_id_a,
            "run_id_b": run_id_b,
            "stage": "cancelled",
            "complete": False,
            "partial": True,
            "message": "comparison cancelled",
            "samples_emitted_a": len(emitted_a),
            "samples_emitted_b": len(emitted_b),
            "shared_samples": shared,
            **cutoff_fields(emitted_a[:shared]),
            "elapsed_seconds_a": copy.deepcopy(elapsed_from_samples(emitted_a)),
            "elapsed_seconds_b": copy.deepcopy(elapsed_from_samples(emitted_b)),
            "intervals_a": intervals_from_samples(emitted_a),
            "intervals_b": intervals_from_samples(emitted_b),
            "overlap": overlap_from_elapsed(elapsed_shared_a, elapsed_shared_b),
        }

    def failed_event(role: str, batch_index: int) -> dict:
        shared, elapsed_shared_a, elapsed_shared_b = shared_elapsed(emitted_a, emitted_b)
        return {
            "event": "error",
            "comparison_id": comparison_id,
            "run_id_a": run_id_a,
            "run_id_b": run_id_b,
            "role": role,
            "stage": "failed",
            "complete": False,
            "partial": True,
            "message": f"calculation failed after batch {batch_index} on {role}",
            "samples_emitted_a": len(emitted_a),
            "samples_emitted_b": len(emitted_b),
            "shared_samples": shared,
            **cutoff_fields(emitted_a[:shared]),
            "elapsed_seconds_a": copy.deepcopy(elapsed_from_samples(emitted_a)),
            "elapsed_seconds_b": copy.deepcopy(elapsed_from_samples(emitted_b)),
            "intervals_a": intervals_from_samples(emitted_a),
            "intervals_b": intervals_from_samples(emitted_b),
            "overlap": overlap_from_elapsed(elapsed_shared_a, elapsed_shared_b),
        }

    def maybe_pause() -> bool:
        if not pause_seconds:
            return False
        if cancel is not None and cancel.wait(pause_seconds):
            return True
        if cancel is None:
            time.sleep(pause_seconds)
        return False

    for index in range(len(rows_a)):
        if cancel is not None and cancel.is_set():
            yield cancelled_event()
            return
        nxt_a = None if index == len(rows_a) - 1 else rows_a[index + 1]
        nxt_b = None if index == len(rows_b) - 1 else rows_b[index + 1]
        sample_a = classify_sample(rows_a[index], nxt_a, step_seconds=prepared_a["step_seconds"], horizon=prepared_a["horizon"])
        sample_b = classify_sample(rows_b[index], nxt_b, step_seconds=prepared_b["step_seconds"], horizon=prepared_b["horizon"])
        # emitted_a and emitted_b hold only samples already sent in a site_batch event,
        # so every shared total and cutoff matches what the client has received.
        batch_a.append(sample_a)
        batch_b.append(sample_b)

        if len(batch_a) == batch_size_a:
            if maybe_pause():
                yield cancelled_event()
                return
            emitted_a.extend(batch_a)
            yield _site_batch_event(
                comparison_id=comparison_id,
                role="site_a",
                run_id=run_id_a,
                result_run_id=result_run_id_a,
                batch_index=batch_index_a,
                batch=batch_a,
                emitted=emitted_a,
                emitted_a=emitted_a,
                emitted_b=emitted_b,
            )
            if fail_after_batches_a is not None and batch_index_a + 1 >= fail_after_batches_a:
                yield failed_event("site_a", batch_index_a)
                return
            batch_a = []
            batch_index_a += 1

        if len(batch_b) == batch_size_b:
            if maybe_pause():
                yield cancelled_event()
                return
            emitted_b.extend(batch_b)
            yield _site_batch_event(
                comparison_id=comparison_id,
                role="site_b",
                run_id=run_id_b,
                result_run_id=result_run_id_b,
                batch_index=batch_index_b,
                batch=batch_b,
                emitted=emitted_b,
                emitted_a=emitted_a,
                emitted_b=emitted_b,
            )
            if fail_after_batches_b is not None and batch_index_b + 1 >= fail_after_batches_b:
                yield failed_event("site_b", batch_index_b)
                return
            batch_b = []
            batch_index_b += 1

    if batch_a:
        if maybe_pause():
            yield cancelled_event()
            return
        emitted_a.extend(batch_a)
        yield _site_batch_event(
            comparison_id=comparison_id,
            role="site_a",
            run_id=run_id_a,
            result_run_id=result_run_id_a,
            batch_index=batch_index_a,
            batch=batch_a,
            emitted=emitted_a,
            emitted_a=emitted_a,
            emitted_b=emitted_b,
        )
        if fail_after_batches_a is not None and batch_index_a + 1 >= fail_after_batches_a:
            yield failed_event("site_a", batch_index_a)
            return
    if batch_b:
        if maybe_pause():
            yield cancelled_event()
            return
        emitted_b.extend(batch_b)
        yield _site_batch_event(
            comparison_id=comparison_id,
            role="site_b",
            run_id=run_id_b,
            result_run_id=result_run_id_b,
            batch_index=batch_index_b,
            batch=batch_b,
            emitted=emitted_b,
            emitted_a=emitted_a,
            emitted_b=emitted_b,
        )
        if fail_after_batches_b is not None and batch_index_b + 1 >= fail_after_batches_b:
            yield failed_event("site_b", batch_index_b)
            return

    finished_a = geometric_run_from_rows(
        rows=rows_a, **{key: value for key, value in prepared_a.items() if key != "rows"}
    )
    finished_b = geometric_run_from_rows(
        rows=rows_b, **{key: value for key, value in prepared_b.items() if key != "rows"}
    )
    comparison = comparison_document(finished_a, finished_b, code_revision)
    yield {
        "event": "complete",
        "comparison_id": comparison_id,
        "run_id_a": run_id_a,
        "run_id_b": run_id_b,
        "result_run_id_a": result_run_id_a,
        "result_run_id_b": result_run_id_b,
        "stage": "complete",
        "complete": True,
        "partial": False,
        "result_a": finished_a,
        "result_b": finished_b,
        "comparison": comparison,
        "shared_samples": len(emitted_a),
        "overlap": comparison["overlap"],
    }
