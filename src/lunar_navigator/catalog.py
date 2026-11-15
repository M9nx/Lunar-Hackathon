"""Catalog of saved Horizons data: what exists, where, and which windows can be run or compared.

One entry is one site, one UTC window and cadence, with a Sun and an Earth export for the same observer.
The catalog reads only saved files. It never calls Horizons. The engine still verifies every checksum, the
observer and the time grid when a run starts; the catalog records what the receipts say and whether the files
on disk match them, so a bad pair is listed under ``problems`` instead of being offered.

Two-site windows are offered only where both sites share the same cadence and a grid-aligned UTC range.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

CATALOG_SCHEMA = "data-catalog-1"
SCOPE_NOTE = (
    "Saved Horizons exports only. Centre-ray against geometric 0 degrees. Practice and synthetic inputs are labelled. "
    "Nothing here is an eligible submission claim."
)

# The only entries whose raw digests are compared with Master Reference Appendix B (the witnessed 48 h pair).
APPENDIX_B_SITES = {"site04-p02-practice", "malapert-practice"}
APPENDIX_B_WINDOW = ("2025-01-01T00:00:00Z", "2025-01-03T00:00:00Z", 900)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse(stamp: str) -> datetime:
    return datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _fmt(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _inspect_export(folder: Path, root: Path) -> dict:
    """Read one export folder. Raises ValueError with a reason if it cannot be used."""
    prov_path, raw_path, csv_path = folder / "provenance.json", folder / "response.json", folder / "angles.csv"
    for needed in (prov_path, raw_path, csv_path):
        if not needed.is_file():
            raise ValueError(f"missing {needed.name}")
    prov = json.loads(prov_path.read_text(encoding="utf-8"))
    raw_sha, csv_sha = _sha256(raw_path), _sha256(csv_path)
    if raw_sha != prov.get("raw_sha256"):
        raise ValueError("response.json SHA-256 does not match the receipt")
    if csv_sha != prov.get("csv_sha256"):
        raise ValueError("angles.csv SHA-256 does not match the receipt")
    rows = _read_csv(csv_path)
    if not rows:
        raise ValueError("angles.csv has no rows")
    if len(rows) != prov.get("row_count"):
        raise ValueError(f"angles.csv has {len(rows)} rows but the receipt says {prov.get('row_count')}")
    stamps = [row["timestamp_utc"] for row in rows]
    step = int(prov["step_minutes"]) * 60
    for left, right in zip(stamps, stamps[1:]):
        if int((_parse(right) - _parse(left)).total_seconds()) != step:
            raise ValueError(f"time grid breaks between {left} and {right}")
    missing = [row["timestamp_utc"] for row in rows if row.get("angle_status", "available") != "available"]
    return {
        "body": prov["target"],
        "observer": [float(v) for v in prov["observer"]],
        "step_seconds": step,
        "stamps": stamps,
        "path": folder.relative_to(root).as_posix(),
        "raw_sha256": raw_sha,
        "csv_sha256": csv_sha,
        "request_url": prov.get("request_url"),
        "rows": len(rows),
        "missing": missing,
        "synthetic": bool(prov.get("synthetic", False)),
        "practice": bool(prov.get("practice", False)),
    }


def _entry_id(site: str, start: str, end: str, step: int) -> str:
    compact = lambda s: s.replace("-", "").replace(":", "")  # noqa: E731
    return f"{site}__{compact(start)}__{compact(end)}__{step}s"


def build_catalog(roots: list[dict]) -> dict:
    """``roots``: [{"id": "data", "path": Path, "label": str, "synthetic": bool}]. Returns the catalog document."""
    entries: list[dict] = []
    problems: list[dict] = []
    for root in roots:
        base = Path(root["path"])
        horizons = base / "horizons"
        if not horizons.is_dir():
            continue
        for site_dir in sorted(p for p in horizons.iterdir() if p.is_dir()):
            exports: dict[str, list[dict]] = {"sun": [], "earth": []}
            for folder in sorted(p for p in site_dir.iterdir() if p.is_dir()):
                try:
                    info = _inspect_export(folder, base)
                except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
                    problems.append({"root": root["id"], "path": folder.relative_to(base).as_posix(), "problem": str(exc)})
                    continue
                if info["body"] in exports:
                    exports[info["body"]].append(info)
            for sun in exports["sun"]:
                for earth in exports["earth"]:
                    if sun["stamps"] != earth["stamps"] or sun["observer"] != earth["observer"]:
                        continue
                    stamps = sun["stamps"]
                    start, end = stamps[0], stamps[-1]
                    step = sun["step_seconds"]
                    lon, lat, alt = sun["observer"]
                    synthetic = bool(root.get("synthetic")) or sun["synthetic"] or earth["synthetic"]
                    practice = sun["practice"] or earth["practice"]
                    entries.append(
                        {
                            "id": _entry_id(site_dir.name, start, end, step),
                            "site_id": site_dir.name,
                            "root_id": root["id"],
                            "root_label": root["label"],
                            "label": f"{site_dir.name} · {start[:16]}Z → {end[:16]}Z · {step // 60} min · {len(stamps)} samples",
                            "synthetic": synthetic,
                            "practice": practice,
                            "observer": {
                                "longitude_east_deg": lon,
                                "latitude_deg": lat,
                                "reference_altitude_km": alt,
                                "center_body_id": 301,
                            },
                            "coverage": {"start_utc": start, "end_utc": end, "step_seconds": step, "samples": len(stamps)},
                            "angles": {
                                "sun": {"rows": sun["rows"], "missing": len(sun["missing"]), "missing_utc": sun["missing"]},
                                "earth": {"rows": earth["rows"], "missing": len(earth["missing"]), "missing_utc": earth["missing"]},
                            },
                            "sources": {
                                body: {
                                    "path": info["path"],
                                    "raw_sha256": info["raw_sha256"],
                                    "csv_sha256": info["csv_sha256"],
                                    "request_url": info["request_url"],
                                }
                                for body, info in (("sun", sun), ("earth", earth))
                            },
                            "checks": {"checksums_match_receipts": True, "grids_equal": True, "observers_equal": True},
                            "in_appendix_b": site_dir.name in APPENDIX_B_SITES and (start, end, step) == APPENDIX_B_WINDOW,
                        }
                    )
    entries.sort(key=lambda e: (e["root_id"], e["site_id"], e["coverage"]["start_utc"], e["coverage"]["end_utc"], e["coverage"]["step_seconds"]))
    return {
        "schema_version": CATALOG_SCHEMA,
        "scope_note": SCOPE_NOTE,
        "roots": [{"id": r["id"], "label": r["label"], "synthetic": bool(r.get("synthetic"))} for r in roots],
        "entries": entries,
        "comparisons": comparison_windows(entries),
        "problems": problems,
    }


def comparison_windows(entries: list[dict]) -> list[dict]:
    """Windows where two different sites share a cadence and a grid-aligned UTC range (two samples or more)."""
    windows: list[dict] = []
    for i, left in enumerate(entries):
        for right in entries[i + 1:]:
            if left["root_id"] != right["root_id"] or left["site_id"] == right["site_id"]:
                continue
            lc, rc = left["coverage"], right["coverage"]
            step = lc["step_seconds"]
            if step != rc["step_seconds"]:
                continue
            ls, rs = _parse(lc["start_utc"]), _parse(rc["start_utc"])
            if int((rs - ls).total_seconds()) % step:
                continue
            start = max(ls, rs)
            end = min(_parse(lc["end_utc"]), _parse(rc["end_utc"]))
            span = int((end - start).total_seconds())
            if span < step:
                continue
            windows.append(
                {
                    "id": f"{left['id']}++{right['id']}",
                    "a": left["id"],
                    "b": right["id"],
                    "start_utc": _fmt(start),
                    "end_utc": _fmt(end),
                    "step_seconds": step,
                    "samples": span // step + 1,
                    "label": f"{left['site_id']} vs {right['site_id']} · {_fmt(start)[:16]}Z → {_fmt(end)[:16]}Z · {step // 60} min",
                }
            )
    return windows


def find_entry(catalog: dict, entry_id: str) -> dict:
    for entry in catalog["entries"]:
        if entry["id"] == entry_id:
            return entry
    raise ValueError(f"no catalog entry {entry_id!r}")


def validate_window(entry: dict, start_utc: str | None, end_utc: str | None) -> tuple[str, str]:
    """Return a checked (start, end). Raises ValueError with an actionable message."""
    cov = entry["coverage"]
    start = start_utc or cov["start_utc"]
    end = end_utc or cov["end_utc"]
    try:
        s, e = _parse(start), _parse(end)
    except ValueError as exc:
        raise ValueError("use UTC times like 2025-01-05T10:00:00Z") from exc
    first, last, step = _parse(cov["start_utc"]), _parse(cov["end_utc"]), cov["step_seconds"]
    if s < first or e > last:
        raise ValueError(f"window must lie inside the saved coverage {cov['start_utc']} to {cov['end_utc']}")
    if e <= s:
        raise ValueError("end must be after start")
    if int((s - first).total_seconds()) % step or int((e - first).total_seconds()) % step:
        raise ValueError(f"start and end must fall on the saved {step // 60}-minute grid")
    return _fmt(s), _fmt(e)


def scenario_for(entry: dict, start_utc: str | None = None, end_utc: str | None = None) -> dict:
    """Scenario record for the engine, derived from a catalog entry. Labelled practice, never eligible."""
    start, end = validate_window(entry, start_utc, end_utc)
    cov = entry["coverage"]
    scenario = {
        "schema_version": "scenario-v1",
        "status": "practice",
        "site_id": entry["site_id"],
        "catalog_entry": entry["id"],
        "observer": {**entry["observer"], "coord_type": "GEODETIC"},
        "start_utc": start,
        "end_utc": end,
        "step_seconds": cov["step_seconds"],
        "horizon_mode": "geometric_0deg",
        "observer_frame": "MEAN_ME",
        "angle_convention": "airless_apparent",
        "horizons_paths": {"sun": entry["sources"]["sun"]["path"], "earth": entry["sources"]["earth"]["path"]},
        "expected_row_count": int((_parse(end) - _parse(start)).total_seconds() // cov["step_seconds"]) + 1,
        "eligible_for_submission_claim": False,
        "in_appendix_b": bool(entry["in_appendix_b"]),
    }
    if entry["synthetic"]:
        scenario["synthetic"] = True
        scenario["synthetic_note"] = (
            "SYNTHETIC QA fixture. Horizons-shaped text written by tests/qa_horizons_case.py. Not JPL output and not a result about the Moon."
        )
    return scenario


def comparison_window_scenarios(catalog: dict, window_id: str, start_utc: str | None, end_utc: str | None) -> tuple[dict, dict, dict]:
    """Scenarios for both sites of a shared window. ``start``/``end`` default to the whole shared range."""
    window = next((w for w in catalog["comparisons"] if w["id"] == window_id), None)
    if window is None:
        raise ValueError(f"no shared window {window_id!r}")
    a, b = find_entry(catalog, window["a"]), find_entry(catalog, window["b"])
    start, end = start_utc or window["start_utc"], end_utc or window["end_utc"]
    if _parse(start) < _parse(window["start_utc"]) or _parse(end) > _parse(window["end_utc"]):
        raise ValueError(f"window must lie inside the shared range {window['start_utc']} to {window['end_utc']}")
    return scenario_for(a, start, end), scenario_for(b, start, end), window


QA_ROOT = "tests/fixtures/qa_horizons"


def default_roots(repo: Path, data_root: Path) -> list[dict]:
    """The saved real data, plus the labelled synthetic QA root when it is present."""
    roots = [{"id": "data", "path": Path(data_root), "label": "Saved Horizons exports", "synthetic": False}]
    qa = Path(repo) / QA_ROOT
    if qa.is_dir():
        roots.append({"id": "qa", "path": qa, "label": "QA fixture (synthetic, not Horizons output)", "synthetic": True})
    return roots


def root_path(roots: list[dict], root_id: str) -> Path:
    for root in roots:
        if root["id"] == root_id:
            return Path(root["path"])
    raise ValueError(f"unknown data root {root_id!r}")


def summary_lines(catalog: dict) -> list[str]:
    lines = [f"{len(catalog['entries'])} entries, {len(catalog['comparisons'])} shared two-site windows, {len(catalog['problems'])} problems"]
    for e in catalog["entries"]:
        gaps = e["angles"]["sun"]["missing"] + e["angles"]["earth"]["missing"]
        flag = " SYNTHETIC" if e["synthetic"] else (" practice" if e["practice"] else "")
        lines.append(f"  {e['id']}  {e['label']}  gaps={gaps}{flag}")
    for w in catalog["comparisons"]:
        lines.append(f"  shared  {w['label']}  {w['samples']} samples")
    for p in catalog["problems"]:
        lines.append(f"  PROBLEM {p['root']}:{p['path']}  {p['problem']}")
    return lines
