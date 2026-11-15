#!/usr/bin/env python3
"""Compare the two raw-response digest sets and record their provenance.

Set 1 is Master Reference Appendix B (examples.practice_horizons). Set 2 is the file on disk
under data/horizons plus its provenance.json. Both are kept. A matching angle CSV does not
close a raw-response mismatch, so this script never reports the mismatch as resolved.
Read-only on data and the reference. Writes only the files named by --md and --json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _harness import REPO_ROOT, load_master_reference  # noqa: E402

DATA = REPO_ROOT / "data" / "horizons"
SITE_DIRS = {
    "site04-p02-practice": {"sun": "sun-8a039d445c7f", "earth": "earth-167962cea6a2"},
    "malapert-practice": {"sun": "sun-d10bfb555ec3", "earth": "earth-062e67d0fdf0"},
}


# Acquired 2026-11-15 with `lunar_offline_pack.py horizons --site ... --step-min 60`. Not in Appendix B,
# so there is no second digest set to compare. They keep their own provenance receipts.
EXTRA_SITES = {
    "site04-p02-practice-30d": {"sun": "sun-80eafb942730", "earth": "earth-67a08fde71c1"},
    "malapert-practice-30d": {"sun": "sun-0ebf1cb6ff30", "earth": "earth-64da8e67c3e9"},
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect() -> list[dict]:
    ref = load_master_reference()
    sites = ref["examples"]["practice_horizons"]["sites"]
    rows = []
    for site in sites:
        site_id = site.get("site_id") or site.get("id")
        for body, meta in site["bodies"].items():
            folder = DATA / site_id / SITE_DIRS[site_id][body]
            prov = json.loads((folder / "provenance.json").read_text())
            response = json.loads((folder / "response.json").read_text())
            stamp = re.search(r"API_USER (.+?) Pasadena", response["result"])
            rows.append(
                {
                    "site_id": site_id,
                    "body": body,
                    "folder": str(folder.relative_to(REPO_ROOT)),
                    "appendix_b_raw_sha256": meta["raw_sha256"],
                    "on_disk_raw_sha256": sha256(folder / "response.json"),
                    "provenance_raw_sha256": prov["raw_sha256"],
                    "appendix_b_csv_sha256": meta["csv_sha256"],
                    "on_disk_csv_sha256": sha256(folder / "angles.csv"),
                    "provenance_csv_sha256": prov["csv_sha256"],
                    "api_version": prov["api_version"],
                    "request_url": prov["request_url"],
                    "observer_lon_lat_alt_km": prov["observer"],
                    "response_generated_stamp": stamp.group(1) if stamp else None,
                    "raw_matches_appendix_b": sha256(folder / "response.json") == meta["raw_sha256"],
                    "raw_matches_provenance": sha256(folder / "response.json") == prov["raw_sha256"],
                    "csv_matches_appendix_b": sha256(folder / "angles.csv") == meta["csv_sha256"],
                    "csv_matches_provenance": sha256(folder / "angles.csv") == prov["csv_sha256"],
                }
            )
    for site_id, dirs in EXTRA_SITES.items():
        for body, name in dirs.items():
            folder = DATA / site_id / name
            if not folder.is_dir():
                continue
            prov = json.loads((folder / "provenance.json").read_text())
            response = json.loads((folder / "response.json").read_text())
            stamp = re.search(r"API_USER (.+?) Pasadena", response["result"])
            rows.append(
                {
                    "site_id": site_id,
                    "body": body,
                    "folder": str(folder.relative_to(REPO_ROOT)),
                    "appendix_b_raw_sha256": None,
                    "on_disk_raw_sha256": sha256(folder / "response.json"),
                    "provenance_raw_sha256": prov["raw_sha256"],
                    "appendix_b_csv_sha256": None,
                    "on_disk_csv_sha256": sha256(folder / "angles.csv"),
                    "provenance_csv_sha256": prov["csv_sha256"],
                    "api_version": prov["api_version"],
                    "request_url": prov["request_url"],
                    "observer_lon_lat_alt_km": prov["observer"],
                    "response_generated_stamp": stamp.group(1) if stamp else None,
                    "raw_matches_appendix_b": None,
                    "raw_matches_provenance": sha256(folder / "response.json") == prov["raw_sha256"],
                    "csv_matches_appendix_b": None,
                    "csv_matches_provenance": sha256(folder / "angles.csv") == prov["csv_sha256"],
                }
            )
    return rows


def render_md(rows: list[dict]) -> str:
    compared = [r for r in rows if r["raw_matches_appendix_b"] is not None]
    open_raw = [r for r in compared if not r["raw_matches_appendix_b"]]
    lines = [
        "# Horizons raw-response digest sets and provenance",
        "",
        "Generated by `builder/scripts/horizons_digest_check.py` (read-only). Both digest sets are kept.",
        "",
        f"**Status:** raw-file identity is **{'OPEN' if open_raw else 'closed by file check'}**. "
        f"{len(open_raw)} of {len(compared)} raw digests differ from Master Reference Appendix B. "
        "On-disk raw digests equal the project provenance receipts. Angle-CSV digests "
        f"{'all match' if all(r['csv_matches_appendix_b'] for r in compared) else 'do not all match'} Appendix B. "
        "Matching angle rows support the replay totals; they do not prove the Appendix B raw file is the file on disk.",
        "",
        "## Digest sets",
        "",
        "| Site | Body | Set 1: Appendix B raw | Set 2: on-disk raw (= provenance) | Raw match | CSV match |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        if r["raw_matches_appendix_b"] is None:
            lines.append(
                f"| {r['site_id']} | {r['body']} | not in Appendix B | `{r['on_disk_raw_sha256']}` | n/a | n/a |"
            )
            continue
        lines.append(
            f"| {r['site_id']} | {r['body']} | `{r['appendix_b_raw_sha256']}` | `{r['on_disk_raw_sha256']}` | "
            f"{'yes' if r['raw_matches_appendix_b'] else '**no**'} | {'yes' if r['csv_matches_appendix_b'] else '**no**'} |"
        )
    lines += [
        "",
        "## Provenance of the on-disk files",
        "",
        "| Site | Body | Folder | Horizons API | Generated stamp inside the response | Observer (E lon, lat, alt km) |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r['site_id']} | {r['body']} | `{r['folder']}` | {r['api_version']} | {r['response_generated_stamp']} | "
            f"{r['observer_lon_lat_alt_km']} |"
        )
    lines += ["", "## Saved request URLs", ""]
    for r in rows:
        lines.append(f"- `{r['site_id']}` {r['body']}: `{r['request_url']}`")
    lines += [
        "",
        "## Reading this",
        "",
        "- Rows marked 'not in Appendix B' are the 30-day practice case acquired on 2026-11-15 (hourly step, "
        "2025-01-01 to 2025-01-31). They have only their own provenance receipts. They are not a second digest set.",
        "- The on-disk `response.json` files carry a generation stamp in the Horizons header. A response fetched again "
        "would carry a different stamp and therefore a different digest. That is a **hypothesis** for the mismatch; "
        "it is not verified and is not used to close the item.",
        "- To close it: show the original Appendix B raw file (or a signed receipt) hashing to Set 1, or Lead and Science "
        "accept Set 2 as the reference and Appendix B is revised. Until then keep both sets and the open label.",
        "- Run results record `appendix_b_raw_sha256: open_mismatch_preserved` for the same reason.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--md", type=Path, default=REPO_ROOT / "builder/docs/evidence/horizons_digest_provenance.md")
    parser.add_argument("--json", type=Path, default=REPO_ROOT / "builder/docs/evidence/horizons_digest_provenance.json")
    parser.add_argument("--check", action="store_true", help="Print status only; write nothing")
    args = parser.parse_args()
    rows = collect()
    open_raw = [r for r in rows if r["raw_matches_appendix_b"] is False]
    broken = [r for r in rows if not (r["raw_matches_provenance"] and r["csv_matches_provenance"])]
    print(f"raw_mismatch_vs_appendix_b={len(open_raw)}/{len([r for r in rows if r['raw_matches_appendix_b'] is not None])} provenance_broken={len(broken)}")
    if not args.check:
        args.md.write_text(render_md(rows), encoding="utf-8")
        args.json.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.md}")
    return 1 if broken else 0


if __name__ == "__main__":
    raise SystemExit(main())
