"""Name what a saved run shows: Sun-only, Earth-only, Both-clear, and the crossings between states.

Reads an engine result (``samples`` with their saved Horizons lines). It adds no classification of its own: it
groups the engine's per-sample states and points at the saved rows on each side of every change.
"""

from __future__ import annotations

from datetime import timedelta

from lunar_navigator.engine import format_utc, parse_utc

OUTCOMES = ("both_clear", "sun_only", "earth_only", "neither", "unknown")
OUTCOME_TEXT = {
    "both_clear": "Both centres clear",
    "sun_only": "Sun centre clear, Earth centre blocked",
    "earth_only": "Earth centre clear, Sun centre blocked",
    "neither": "Both centres blocked",
    "unknown": "Unknown (a body has no usable angle; see the lane reasons)",
}


def sample_outcome(sample: dict) -> str:
    sun, earth = sample["sun"]["state"], sample["earth"]["state"]
    if sun == "unknown" or earth == "unknown":
        return "unknown"
    if sun == "clear" and earth == "clear":
        return "both_clear"
    if sun == "clear":
        return "sun_only"
    if earth == "clear":
        return "earth_only"
    return "neither"


def _line(sample: dict, body: str) -> dict:
    item = sample[body]
    return {"utc": sample["timestamp_utc"], "elevation_deg": item["elevation_deg"], "state": item["state"],
            "source_ref": item["source_ref"], "response_line": item["response_line"]}


def outcome_spans(run: dict) -> list[dict]:
    """Consecutive samples with the same outcome, half-open like the engine's intervals."""
    spans: list[dict] = []
    for sample in run["samples"]:
        seconds = sample["duration_seconds"]
        if seconds == 0:
            continue
        outcome = sample_outcome(sample)
        end = format_utc(parse_utc(sample["timestamp_utc"]) + timedelta(seconds=seconds))
        if spans and spans[-1]["outcome"] == outcome and spans[-1]["end_utc"] == sample["timestamp_utc"]:
            spans[-1]["end_utc"] = end
            spans[-1]["seconds"] += seconds
            spans[-1]["samples"] += 1
            continue
        spans.append({"outcome": outcome, "start_utc": sample["timestamp_utc"], "end_utc": end, "seconds": seconds, "samples": 1})
    return spans


def crossings(run: dict, lane: str) -> list[dict]:
    """Every change of a lane's state, with the saved row before and after (Sun and Earth lanes carry their lines)."""
    out: list[dict] = []
    previous = None
    for sample in run["samples"]:
        if sample["duration_seconds"] == 0:  # the terminal sample covers no time
            continue
        if previous is not None and sample[lane]["state"] != previous[lane]["state"]:
            item = {"lane": lane, "from": previous[lane]["state"], "to": sample[lane]["state"],
                    "last_before_utc": previous["timestamp_utc"], "first_after_utc": sample["timestamp_utc"]}
            if lane in ("sun", "earth"):
                item["before"] = _line(previous, lane)
                item["after"] = _line(sample, lane)
            else:
                item["before"] = {"sun": _line(previous, "sun"), "earth": _line(previous, "earth")}
                item["after"] = {"sun": _line(sample, "sun"), "earth": _line(sample, "earth")}
            out.append(item)
        previous = sample
    return out


def summarize(run: dict) -> dict:
    spans = outcome_spans(run)
    totals = {name: 0 for name in OUTCOMES}
    for span in spans:
        totals[span["outcome"]] += span["seconds"]
    return {
        "site_id": run["scenario"]["site_id"],
        "start_utc": run["scenario"]["start_utc"],
        "end_utc": run["scenario"]["end_utc"],
        "step_seconds": run["scenario"]["step_seconds"],
        "outcome_seconds": totals,
        "spans": spans,
        "crossings": {lane: crossings(run, lane) for lane in ("sun", "earth", "both")},
    }
