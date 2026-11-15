#!/usr/bin/env python3
"""Build docs/notebooks/01_trace_observation_to_interval_total.ipynb from the cells below (stdlib only).

Jupyter is not installed on the build machine, so the notebook is written as plain nbformat-4 JSON and
executed by builder/scripts/run_notebook.py, which stores the real outputs. Re-run both after any change:

    python3 builder/scripts/build_notebook.py
    python3 builder/scripts/run_notebook.py docs/notebooks/01_trace_observation_to_interval_total.ipynb
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs/notebooks/01_trace_observation_to_interval_total.ipynb"

CELLS: list[tuple[str, str]] = [
    ("markdown", """\
# Trace one observation to an interval total

This notebook follows a single saved Horizons row from the raw file to the number on the result screen.
It uses only the Python standard library for the trace, then compares that trace with the engine.

**What it shows.** The *centre-ray* rule: the apparent airless elevation of the Sun's centre (Horizons quantity 4,
body `10`) from a lunar observer (`301`), compared with a flat 0° horizon. A margin of 0° or less is Blocked.

**What it does not show.** Disc visibility, received power, a ground-station link, terrain, or an eligible
submission claim. The inputs are a *practice* export. Terrain stays Unknown.

The case is Malapert, 30 days at a 1 h step (`malapert-practice-30d`). Run this from the repository root with the saved
exports under `data/` (see the Operator Manual). Nothing here contacts JPL.
"""),
    ("code", """\
import hashlib, json, math, re, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path.cwd()
while not (ROOT / "src" / "lunar_navigator").is_dir():
    if ROOT.parent == ROOT:
        raise SystemExit("run this from inside the repository")
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT / "src"))

SCENARIO = json.loads((ROOT / "tests/fixtures/malapert_practice_30d_scenario.json").read_text())
SUN_DIR = ROOT / "data" / SCENARIO["horizons_paths"]["sun"]
print("scenario  :", SCENARIO["site_id"], "|", SCENARIO["start_utc"], "->", SCENARIO["end_utc"], "| step", SCENARIO["step_seconds"], "s")
print("mode      :", SCENARIO["horizon_mode"], "| frame", SCENARIO["observer_frame"], "|", SCENARIO["angle_convention"])
print("observer  :", SCENARIO["observer"])
print("raw folder:", SUN_DIR.relative_to(ROOT))
"""),
    ("markdown", """\
## 1. The raw file is the source

Check the saved receipt first. `provenance.json` records the request and the SHA-256 of the response; the digest is
recomputed here from the file on disk. A match says the file is the one that was saved. It does not say anything about
the older 48 h exports, whose raw-file identity is a separate open item.
"""),
    ("code", """\
raw_path = SUN_DIR / "response.json"
provenance = json.loads((SUN_DIR / "provenance.json").read_text())
digest = hashlib.sha256(raw_path.read_bytes()).hexdigest()
print("request   :", provenance["request_url"].split("?", 1)[1][:150], "...")
print("on disk   :", digest)
print("receipt   :", provenance["raw_sha256"])
assert digest == provenance["raw_sha256"], "raw response does not match its receipt"

text = json.loads(raw_path.read_text())["result"]
for needle in ("Target body name", "Center body name", "Center geodetic", "Center pole/equ", "Atmos refraction", "Azi_(a-app)"):
    line = next(l for l in text.splitlines() if needle in l)
    print("header    :", line.strip())
assert "NO (AIRLESS)" in text and "Elev_(a-app)" in text, "not an airless apparent-elevation table"
assert "MEAN_ME" in text, "unexpected observer frame"
"""),
    ("markdown", """\
## 2. Parse the rows

Rows sit between `$$SOE` and `$$EOE`. Each is `date, flag, flag, azimuth, elevation`. The flag columns are ignored:
the rule below uses only the elevation. Angles are degrees; azimuth is clockwise from local north; times are UT.
An empty elevation is *unavailable*, never `0`.
"""),
    ("code", """\
body = text.split("$$SOE", 1)[1].split("$$EOE", 1)[0].strip().splitlines()
MONTHS = {m: i for i, m in enumerate(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"], 1)}

def parse(line):
    cells = [c.strip() for c in line.split(",")]
    stamp = re.match(r"(\\d{4})-([A-Za-z]{3})-(\\d{2}) (\\d{2}):(\\d{2})$", cells[0])
    when = datetime(int(stamp[1]), MONTHS[stamp[2]], int(stamp[3]), int(stamp[4]), int(stamp[5]), tzinfo=timezone.utc)
    azimuth = float(cells[3]) if cells[3] else None
    elevation = float(cells[4]) if cells[4] else None
    return when, azimuth, elevation, line.strip()

rows = [parse(l) for l in body]
print(len(rows), "rows,", rows[0][0].isoformat(), "->", rows[-1][0].isoformat())
steps = {int((b[0] - a[0]).total_seconds()) for a, b in zip(rows, rows[1:])}
print("distinct steps (s):", steps)
assert steps == {SCENARIO["step_seconds"]} and len(rows) == SCENARIO["expected_row_count"]
for r in rows:
    if r[0].isoformat().startswith(("2025-01-05T09:00", "2025-01-05T10:00")):
        print(r[3])
"""),
    ("markdown", """\
## 3. Classify one sample

margin = elevation − horizon, with the horizon fixed at 0° (`geometric_0deg`). The rule uses the unrounded value:

| margin | state |
|---|---|
| `> 0` | clear |
| `<= 0` | blocked (exact contact counts) |
| no elevation | unknown |

The Sun's centre crosses 0° between 09:00 and 10:00 on 5 January. Look at the two rows on either side.
"""),
    ("code", """\
HORIZON = 0.0

def classify(elevation):
    if elevation is None:
        return "unknown", None
    margin = elevation - HORIZON
    return ("clear" if margin > 0 else "blocked"), margin

by_time = {r[0]: r for r in rows}
before = by_time[datetime(2025, 1, 5, 9, tzinfo=timezone.utc)]
after = by_time[datetime(2025, 1, 5, 10, tzinfo=timezone.utc)]
for label, row in (("09:00Z", before), ("10:00Z", after)):
    state, margin = classify(row[2])
    print(f"{label}  elevation {row[2]:+.6f}  margin {margin:+.6f}  ->  {state}")
assert classify(before[2])[0] == "blocked" and classify(after[2])[0] == "clear"
assert classify(0.0)[0] == "blocked" and classify(None)[0] == "unknown"
"""),
    ("markdown", """\
## 4. From samples to an interval total

Each sample covers the half-open interval `[t, t + step)`. The last sample covers nothing, so it adds 0 s. Adding up the
samples therefore covers exactly `[start, end)`: Clear + Blocked + Unknown equals the requested window.
"""),
    ("code", """\
start = datetime.fromisoformat(SCENARIO["start_utc"].replace("Z", "+00:00"))
end = datetime.fromisoformat(SCENARIO["end_utc"].replace("Z", "+00:00"))
step = SCENARIO["step_seconds"]
window = int((end - start).total_seconds())

samples = []
for index, (when, azimuth, elevation, line) in enumerate(rows):
    duration = step if index < len(rows) - 1 else 0
    state, margin = classify(elevation)
    samples.append({"utc": when, "state": state, "margin": margin, "duration": duration, "line": line})

totals = {"clear": 0, "blocked": 0, "unknown": 0}
for s in samples:
    totals[s["state"]] += s["duration"]
print("totals (s):", totals, "| window", window, "s")
assert sum(totals.values()) == window
print("clear hours:", totals["clear"] / 3600)

# Merge neighbouring samples with the same state into intervals.
intervals = []
for s in samples[:-1]:
    t0 = s["utc"]; t1 = t0 + timedelta(seconds=step)
    if intervals and intervals[-1]["state"] == s["state"] and intervals[-1]["end"] == t0:
        intervals[-1]["end"] = t1
    else:
        intervals.append({"state": s["state"], "start": t0, "end": t1})
for iv in intervals:
    hours = (iv["end"] - iv["start"]).total_seconds() / 3600
    print(f'{iv["state"]:8} {iv["start"].strftime("%Y-%m-%dT%H:%MZ")} -> {iv["end"].strftime("%Y-%m-%dT%H:%MZ")}  {hours:g} h')
"""),
    ("markdown", """\
## 5. Trace one observation all the way

Take the sample at `2025-01-05T10:00Z`. This cell walks it from the raw line to the total, and shows what happens at the
very end of the window, where the final sample adds 0 s even though it has a state.
"""),
    ("code", """\
pick = datetime(2025, 1, 5, 10, tzinfo=timezone.utc)
sample = next(s for s in samples if s["utc"] == pick)
interval = next(iv for iv in intervals if iv["start"] <= pick < iv["end"])
clear_intervals = [iv for iv in intervals if iv["state"] == "clear"]
print("1 raw line       :", sample["line"])
print("2 margin / state :", f'{sample["margin"]:+.6f}', sample["state"])
print("3 it covers      :", pick.isoformat(), "->", (pick + timedelta(seconds=step)).isoformat(), f"({sample['duration']} s)")
print("4 interval       :", interval["state"], interval["start"].isoformat(), "->", interval["end"].isoformat())
print("5 contributes    :", sample["duration"], "s to the clear total of", totals["clear"], "s")
n_clear = sum(1 for s in samples if s["state"] == "clear")
print("6 clear samples  :", n_clear, "x", step, "s =", n_clear * step, "s")
assert n_clear * step == totals["clear"] == 436 * 3600
assert len(clear_intervals) == 1 and clear_intervals[0]["start"] == pick

final = samples[-1]
print("final sample     :", final["utc"].isoformat(), final["state"], "adds", final["duration"], "s")
assert final["duration"] == 0 and final["utc"] == end
"""),
    ("markdown", """\
## 6. Compare with the engine and the saved package

The trace above never imported the engine. Now run the engine on the same files and compare sample by sample, then
compare with the saved replay package that the browser reads.
"""),
    ("code", """\
from lunar_navigator.engine import run_from_scenario

engine = run_from_scenario(SCENARIO, ROOT / "data", "notebook")
assert len(engine["samples"]) == len(samples)
mismatches = [
    (a["timestamp_utc"], a["sun"]["state"], b["state"])
    for a, b in zip(engine["samples"], samples)
    if a["sun"]["state"] != b["state"]
    or a["duration_seconds"] != b["duration"]
    or (b["margin"] is not None and abs(a["sun"]["margin_deg"] - b["margin"]) > 1e-12)
]
print("sample-by-sample mismatches:", len(mismatches))
assert not mismatches
assert engine["elapsed_seconds"]["sun"] == totals, (engine["elapsed_seconds"]["sun"], totals)
print("engine Sun-centre totals equal the trace:", engine["elapsed_seconds"]["sun"])

saved = json.loads((ROOT / "web/review-candidate/cases/practice-30d/runs/malapert-practice-30d.json").read_text())
assert saved["elapsed_seconds"]["sun"] == totals
assert saved["run_id"] == engine["run_id"]
print("saved package run_id:", saved["run_id"])
print("saved package equals the engine and the trace.")
"""),
    ("markdown", """\
## What this establishes, and what it does not

* One saved row, the 0° rule, the half-open interval and the 0 s final sample produce the total shown on screen: 436 h of
  Sun-centre clearance for Malapert across 1–31 January 2025 (practice input).
* The engine and the saved package agree with this separate trace.
* It does **not** show that any part of the Sun's disc is visible, that a link or power is available, or what terrain does.
  Around 5 January the centre is within about 0.02° of the plane; part of the disc can lie above the plane while the centre
  is below it. That does not change the centre-ray state.
* The raw-file identity for the original 48 h exports stays open. This notebook checked only the 30-day receipt.
"""),
]


def main() -> None:
    cells = []
    for kind, source in CELLS:
        lines = source.rstrip("\n").splitlines(keepends=True)
        if kind == "markdown":
            cells.append({"cell_type": "markdown", "metadata": {}, "source": lines})
        else:
            cells.append({"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines})
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(notebook, indent=1) + "\n")
    print("wrote", OUT.relative_to(REPO), f"({len(cells)} cells)")


if __name__ == "__main__":
    main()
