"""Labelled QA case that goes through the normal Horizons importer, including a missing (n.a.) angle.

The Horizons-shaped replies below are SYNTHETIC. They are not JPL output and say nothing about the Moon.
Each reply is passed to ``lunar_offline_pack.import_horizons_export``, the same function the downloader uses,
so the CSV, the raw file and the receipt are written by the real import path.

Sun at QA Gap North is ``n.a.`` at 00:30 on a 15-minute grid. With the left-sample, both-endpoints rule the Sun
lane is Unknown from 00:15 to 00:45 (30 minutes).

    python3 tests/qa_horizons_case.py            # rewrite tests/fixtures/qa_horizons
    python3 tests/qa_horizons_case.py --check    # exit 1 if the saved files differ from a fresh import
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import lunar_offline_pack as pack  # noqa: E402

ROOT = REPO / "tests/fixtures/qa_horizons"
START = datetime(2024, 6, 1, 0, 0, tzinfo=timezone.utc)
STOP = datetime(2024, 6, 1, 1, 0, tzinfo=timezone.utc)
STEP_MIN = 15
NOTE = "SYNTHETIC QA fixture. Horizons-shaped text written by tests/qa_horizons_case.py. Not JPL output."
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()

# (site id, east longitude, latitude, height km, {body: [(azimuth, elevation) | None, ...]})
SITES = {
    "qa-gap-north": (
        10.0, -85.0, 0.0,
        {
            "sun": [(10.0, 2.0), (20.0, 0.4), None, (40.0, -1.25), (45.0, 0.0)],
            "earth": [(200.0, 1.0), (210.0, -0.25), (220.0, 0.6), (225.0, 0.5), (230.0, 0.8)],
        },
    ),
    "qa-gap-south": (
        120.0, -80.0, 0.0,
        {
            "sun": [(80.0, -0.5), (90.0, 1.5), (100.0, 1.0), (110.0, 0.4), (120.0, 0.2)],
            "earth": [(300.0, 0.3), (310.0, 0.7), (320.0, 0.4), (330.0, -0.1), (340.0, 0.5)],
        },
    ),
}
TARGETS = {"sun": "10", "earth": "399"}
NAMES = {"sun": "Sun (10)", "earth": "Earth (399)"}


def _stamp(index: int) -> str:
    dt = START + timedelta(minutes=STEP_MIN * index)
    return f"{dt.year:04d}-{MONTHS[dt.month - 1]}-{dt.day:02d} {dt.hour:02d}:{dt.minute:02d}"


def payload(site: str, body: str) -> dict:
    lon, lat, alt, tables = SITES[site]
    lines = []
    for index, angles in enumerate(tables[body]):
        if angles is None:
            lines.append(f" {_stamp(index)}, , ,       n.a.,        n.a.,")
        else:
            az, el = angles
            lines.append(f" {_stamp(index)}, , , {az:10.6f}, {el:11.6f},")
    header = "\n".join(
        [
            "*******************************************************************************",
            "SYNTHETIC QA FIXTURE - not JPL Horizons output. Written by tests/qa_horizons_case.py.",
            "*******************************************************************************",
            f"Target body name: {NAMES[body]}                        {{source: QA}}",
            "Center body name: Moon (301)                      {source: QA}",
            "Center-site name: (user defined site below)",
            "*******************************************************************************",
            "Start time      : A.D. 2024-Jun-01 00:00:00.0000 UT",
            "Stop  time      : A.D. 2024-Jun-01 01:00:00.0000 UT",
            "Step-size       : 15 minutes",
            "*******************************************************************************",
            f"Center geodetic : {lon % 360:.2f}, {lat}, {alt}             {{E-lon(deg),Lat(deg),Alt(km)}}",
            "Center pole/equ : MEAN_ME (high precision)        {East-longitude positive}",
            "Center radii    : 1737.4, 1737.4, 1737.4 km       {Equator_a, b, pole_c}",
            "Atmos refraction: NO (AIRLESS)",
            "Table format    : Comma Separated Values (spreadsheet)",
            "*******************************************************************************",
            " Date__(UT)__HR:MN, , ,Azi_(a-app), Elev_(a-app),",
            "*************************************************",
        ]
    )
    result = header + "\n$$SOE\n" + "\n".join(lines) + "\n$$EOE\n*******************************************************************************\n"
    return {"signature": {"version": "1.2", "source": "QA synthetic"}, "result": result}


def build(root: Path) -> dict[str, dict[str, str]]:
    """Import every QA reply into root/horizons/<site>/<body>-<hash>/. Returns the folder names."""
    folders: dict[str, dict[str, str]] = {}
    for site, (lon, lat, alt, _tables) in SITES.items():
        folders[site] = {}
        for body in ("sun", "earth"):
            url = f"synthetic://qa-gap/{site}/{body}"
            key = hashlib.sha256(url.encode()).hexdigest()[:12]
            directory = root / "horizons" / site / f"{body}-{key}"
            pack.import_horizons_export(
                directory, payload(site, body), url=url, target=TARGETS[body], label=body,
                observer=(lon, lat, alt), start=START, stop=STOP, step=STEP_MIN, practice=True,
                synthetic_note=NOTE,
            )
            folders[site][body] = f"horizons/{site}/{directory.name}"
    return folders


def scenarios(folders: dict[str, dict[str, str]]) -> dict[str, dict]:
    out = {}
    for site, (lon, lat, alt, _tables) in SITES.items():
        out[site] = {
            "schema_version": "scenario-v1",
            "status": "practice",
            "synthetic": True,
            "synthetic_note": NOTE,
            "site_id": site,
            "observer": {
                "longitude_east_deg": lon,
                "latitude_deg": lat,
                "reference_altitude_km": alt,
                "center_body_id": 301,
                "coord_type": "GEODETIC",
            },
            "start_utc": "2024-06-01T00:00:00Z",
            "end_utc": "2024-06-01T01:00:00Z",
            "step_seconds": 900,
            "horizon_mode": "geometric_0deg",
            "observer_frame": "MEAN_ME",
            "angle_convention": "airless_apparent",
            "horizons_paths": folders[site],
            "expected_row_count": 5,
            "eligible_for_submission_claim": False,
            "in_appendix_b": False,
        }
    return out


def write_all(root: Path = ROOT) -> None:
    if root.exists():
        shutil.rmtree(root)
    folders = build(root)
    for site, scenario in scenarios(folders).items():
        (root / f"{site}_scenario.json").write_text(json.dumps(scenario, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        write_all()
        print(f"wrote {ROOT.relative_to(REPO)}")
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        fresh = Path(tmp) / "qa_horizons"
        write_all(fresh)
        names = sorted(p.relative_to(fresh).as_posix() for p in fresh.rglob("*") if p.is_file())
        have = sorted(p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file())
        if names != have:
            print("file lists differ")
            return 1
        bad = [n for n in names if (fresh / n).read_bytes() != (ROOT / n).read_bytes()]
        print("differs: " + ", ".join(bad) if bad else f"{len(names)} files match a fresh import")
        return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
