"""Trace the four outcomes in the expanded real cases back to saved Horizons rows.

The engine result is not trusted here. For each state change this script re-reads the saved ``response.json``,
finds the two raw lines on each side of the change with its own small parser, and checks that

  * the raw line equals the engine's ``response_line``,
  * the raw elevation has the sign the engine's state needs (margin <= 0 is blocked, exact contact included),
  * the saved file still hashes to its provenance receipt.

    python3 tests/real_case_trace.py            # print the trace as Markdown
    python3 tests/real_case_trace.py --write    # write docs/real-case-trace.md
    python3 tests/real_case_trace.py --check    # exit 1 if docs/real-case-trace.md differs

The data are real JPL Horizons exports for the practice sites. They are centre-ray clearances only. They say
nothing about disc visibility, received power, or radio contact, and the cases stay ineligible for submission.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from lunar_navigator.catalog import build_catalog, default_roots, find_entry, root_path, scenario_for  # noqa: E402
from lunar_navigator.engine import run_from_scenario  # noqa: E402
from lunar_navigator.outcomes import crossings as lane_crossings, summarize  # noqa: E402

DOC = REPO / "docs" / "real-case-trace.md"
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()

SITE04_15M = "site04-p02-practice__20250103T000000Z__20250110T000000Z__900s"
MALAPERT_15M = "malapert-practice__20250103T000000Z__20250110T000000Z__900s"
SITE04_6H = "site04-p02-practice__20250101T000000Z__20250401T000000Z__21600s"
MALAPERT_6H = "malapert-practice__20250101T000000Z__20250401T000000Z__21600s"

# (label, entry id, outcome, expected span start, expected span end)
OUTCOME_CASES = [
    ("Sun-only", SITE04_15M, "sun_only", "2025-01-03T00:00:00Z", "2025-01-06T03:15:00Z"),
    ("Earth-only", MALAPERT_15M, "earth_only", "2025-01-03T09:00:00Z", "2025-01-05T09:30:00Z"),
    ("Both-clear (Malapert)", MALAPERT_15M, "both_clear", "2025-01-05T09:30:00Z", "2025-01-10T00:00:00Z"),
    ("Both-clear (Site04)", SITE04_15M, "both_clear", "2025-01-06T03:15:00Z", "2025-01-10T00:00:00Z"),
]


def raw_line(root: Path, source_path: str, utc: str) -> tuple[str, float, float]:
    """The saved Horizons line for one UTC time, read straight from response.json."""
    year, month, rest = utc[:4], int(utc[5:7]), utc[8:]
    stamp = f"{year}-{MONTHS[month - 1]}-{rest[:2]} {rest[3:5]}:{rest[6:8]}"
    text = json.loads((root / source_path / "response.json").read_text(encoding="utf-8"))["result"]
    body = text.split("$$SOE", 1)[1].split("$$EOE", 1)[0]
    for line in body.splitlines():
        if line.strip().startswith(stamp + ","):
            fields = [part.strip() for part in line.split(",")]
            return line.strip(), float(fields[3]), float(fields[4])
    raise KeyError(f"{utc} is not in {source_path}/response.json")


def file_matches_provenance(root: Path, source_path: str) -> bool:
    directory = root / source_path
    receipt = json.loads((directory / "provenance.json").read_text(encoding="utf-8"))
    return (
        hashlib.sha256((directory / "response.json").read_bytes()).hexdigest() == receipt["raw_sha256"]
        and hashlib.sha256((directory / "angles.csv").read_bytes()).hexdigest() == receipt["csv_sha256"]
    )


def run_entry(entry_id: str):
    roots = default_roots(REPO, REPO / "data")
    catalog = build_catalog(roots)
    entry = find_entry(catalog, entry_id)
    root = root_path(roots, entry["root_id"])
    return entry, root, run_from_scenario(scenario_for(entry), root, "trace")


def _state_for(elevation: float) -> str:
    return "clear" if elevation > 0.0 else "blocked"


def check_row(entry: dict, root: Path, body: str, item: dict) -> dict:
    """One engine row against the raw line. Returns the evidence record, or raises AssertionError."""
    source = entry["sources"][body]["path"]
    line, azimuth, elevation = raw_line(root, source, item["utc"])
    assert line == item["response_line"].strip(), f"{item['utc']} {body}: raw line differs from the engine's response_line"
    assert abs(elevation - item["elevation_deg"]) < 1e-6, f"{item['utc']} {body}: elevation differs"
    assert _state_for(elevation) == item["state"], f"{item['utc']} {body}: raw elevation {elevation} does not give {item['state']}"
    assert file_matches_provenance(root, source), f"{source}: saved file no longer matches provenance.json"
    return {"utc": item["utc"], "body": body, "state": item["state"], "raw_line": line, "source": source}


def trace() -> dict:
    """Run the four outcome cases and the six-hour scans. Raises AssertionError on any mismatch."""
    cases = []
    for label, entry_id, outcome, start, end in OUTCOME_CASES:
        entry, root, run = run_entry(entry_id)
        summary = summarize(run)
        span = next(
            (s for s in summary["spans"] if s["outcome"] == outcome and s["start_utc"] == start and s["end_utc"] == end),
            None,
        )
        assert span is not None, f"{label}: no {outcome} span {start} -> {end} in {entry_id}"
        # Every sample in the span, checked against its saved raw lines.
        checked = []
        for sample in run["samples"]:
            if not (start <= sample["timestamp_utc"] < end):
                continue
            for body in ("sun", "earth"):
                checked.append(check_row(entry, root, body, {**sample[body], "utc": sample["timestamp_utc"]}))
        cases.append({"label": label, "entry": entry_id, "outcome": outcome, "start_utc": start, "end_utc": end,
                      "seconds": span["seconds"], "rows_checked": len(checked)})
    crossings = []
    for entry_id in (SITE04_15M, MALAPERT_15M):
        entry, root, run = run_entry(entry_id)
        for lane in ("sun", "earth"):
            for change in lane_crossings(run, lane):
                rows = [check_row(entry, root, lane, change[side]) for side in ("before", "after")]
                crossings.append({"entry": entry_id, "lane": lane, "from": change["from"], "to": change["to"], "rows": rows})
    scans = []
    for entry_id in (SITE04_6H, MALAPERT_6H):
        entry, root, run = run_entry(entry_id)
        summary = summarize(run)
        for change in summary["crossings"]["both"]:
            for side in ("before", "after"):
                for body in ("sun", "earth"):
                    check_row(entry, root, body, change[side][body])
        scans.append({"entry": entry_id, "outcome_seconds": summary["outcome_seconds"], "spans": len(summary["spans"]),
                      "both_crossings": len(summary["crossings"]["both"])})
    return {"cases": cases, "crossings": crossings, "scans": scans}


def markdown(result: dict) -> str:
    out = [
        "# Real-case trace",
        "",
        "Generated by `tests/real_case_trace.py`. Each row below was re-read from the saved Horizons `response.json`",
        "with a separate parser and matched to the engine's classification. Centre-ray clearance only: this says",
        "nothing about disc visibility, received power, or ground-station contact. The data are practice inputs and",
        "the cases are not eligible for submission claims.",
        "",
        "## The four outcomes (15-minute cadence)",
        "",
        "| Outcome | Saved export | UTC span (half-open) | Duration | Saved rows checked |",
        "| --- | --- | --- | --- | --- |",
    ]
    for case in result["cases"]:
        out.append(f"| {case['label']} | `{case['entry']}` | {case['start_utc']} → {case['end_utc']} | {case['seconds'] // 3600} h {case['seconds'] % 3600 // 60} min | {case['rows_checked']} |")
    out += ["", "## State changes in those windows", "",
            "| Export | Lane | Change | Last row before | First row after |", "| --- | --- | --- | --- | --- |"]
    for item in result["crossings"]:
        before, after = item["rows"]
        out.append(
            f"| `{item['entry'].split('__')[0]}` {item['entry'].split('__')[1]} | {item['lane']} | {item['from']} → {item['to']}"
            f" | `{before['raw_line']}` | `{after['raw_line']}` |"
        )
    out += ["", "## Six-hour scans, 2025-01-01 to 2025-04-01", "",
            "| Export | Spans | Both-lane changes | Seconds by outcome |", "| --- | --- | --- | --- |"]
    for scan in result["scans"]:
        seconds = ", ".join(f"{k} {v}" for k, v in scan["outcome_seconds"].items() if v)
        out.append(f"| `{scan['entry']}` | {scan['spans']} | {scan['both_crossings']} | {seconds} |")
    out += ["", "Every Both-lane change in the scans was traced to the raw rows on both sides.", ""]
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    text = markdown(trace())
    if args.write:
        DOC.write_text(text, encoding="utf-8")
        print(f"wrote {DOC}")
        return 0
    if args.check:
        if not DOC.exists() or DOC.read_text(encoding="utf-8") != text:
            print(f"{DOC} differs from a fresh trace")
            return 1
        print("real-case trace matches")
        return 0
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
