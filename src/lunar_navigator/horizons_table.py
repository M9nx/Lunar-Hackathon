"""Read saved Horizons quantity-4 tables and the raw response lines they came from."""

from __future__ import annotations

import csv
import json
from pathlib import Path

MONTHS = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


def horizons_stamp_to_utc(stamp: str) -> str:
    """Convert a Horizons calendar stamp to ISO 8601 UTC.

    The month token is mapped explicitly so a non-English locale cannot change it.
    """
    date_part, time_part = stamp.split()
    year_s, month_s, day_s = date_part.split("-")
    hour_s, minute_s = time_part.split(":")
    month = MONTHS[month_s]
    return f"{int(year_s):04d}-{month:02d}-{int(day_s):02d}T{int(hour_s):02d}:{int(minute_s):02d}:00Z"


def parse_response_line(line: str) -> tuple[str, float, float] | None:
    """Return UTC, azimuth, elevation from one Horizons CSV result line."""
    stripped = line.strip()
    if not stripped or not stripped[0].isdigit():
        return None
    parts = [part.strip() for part in line.split(",")]
    if len(parts) < 5:
        return None
    try:
        azimuth = float(parts[3])
        elevation = float(parts[4])
        utc = horizons_stamp_to_utc(parts[0])
    except (KeyError, ValueError):
        return None
    return utc, azimuth, elevation


def load_angles_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    parsed: list[dict] = []
    for row in rows:
        status = row.get("angle_status", "available")
        elevation = row.get("elevation_deg", "")
        azimuth = row.get("azimuth_deg", "")
        parsed.append(
            {
                "timestamp_utc": row["timestamp_utc"],
                "azimuth_deg": float(azimuth) if azimuth not in ("", "null") and status == "available" else None,
                "elevation_deg": float(elevation) if elevation not in ("", "null") and status == "available" else None,
                "angle_status": status,
            }
        )
    return parsed


def index_response(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = payload.get("result")
    if not isinstance(result, str):
        raise ValueError(f"{path} has no Horizons result text")
    indexed: dict[str, str] = {}
    for line in result.splitlines():
        parsed = parse_response_line(line)
        if parsed is None:
            continue
        utc, _azimuth, _elevation = parsed
        if utc in indexed:
            raise ValueError(f"duplicate Horizons timestamp {utc} in {path}")
        indexed[utc] = line.strip()
    return indexed


def response_angles(line: str) -> tuple[float, float]:
    parsed = parse_response_line(line)
    if parsed is None:
        raise ValueError("response line is not a quantity-4 data row")
    _utc, azimuth, elevation = parsed
    return azimuth, elevation
