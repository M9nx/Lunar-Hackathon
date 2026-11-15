"""Reviewed terrain skylines for terrain mode, and the reasons terrain mode gives when one is not available.

Terrain mode needs a skyline that was reviewed for *this observer*: a reviewed frame, a reviewed vertical
reference, radial coverage for the direction used, and one independently checked skyline direction. A
populated azimuth bin alone does not establish continuity. When any of that is missing the horizon is unknown
and the engine reports Unknown with a reason, keeping the elevation but no horizon or margin.

A reviewed skyline is a JSON file ``<data_root>/terrain/reviewed/<name>.json``::

    {"schema_version": "reviewed-skyline-1", "site_id": "...",
     "observer": {"longitude_east_deg": .., "latitude_deg": .., "reference_altitude_km": ..},
     "review": {"status": "approved", "reviewer": "...", "reviewed_utc": "...", "frame": "...",
                "vertical_reference": "...", "radial_coverage_m": [min, max], "independent_check": "..."},
     "bins": [{"azimuth_deg": 0.0, "horizon_deg": -1.2, "known": true}, ...]}

No reviewed skyline exists yet (the M4 review has not passed), so every real terrain-mode run is Unknown.
This module has no numpy dependency.
"""

from __future__ import annotations

import json
from pathlib import Path

REVIEW_FIELDS = ("status", "reviewer", "frame", "vertical_reference", "radial_coverage_m", "independent_check")
REASON_NOT_REVIEWED = "terrain_not_reviewed"
REASON_NO_MATCH = "terrain_no_skyline_for_observer"
REASON_REVIEW_INCOMPLETE = "terrain_review_incomplete"
REASON_GAP = "terrain_gap_in_azimuth_bracket"
REASON_FEW_BINS = "terrain_insufficient_bins"
OBSERVER_TOLERANCE = 1e-6


def _same_observer(a: dict, b: dict) -> bool:
    keys = ("longitude_east_deg", "latitude_deg", "reference_altitude_km")
    try:
        lon_error = abs((float(a[keys[0]]) - float(b[keys[0]]) + 180.0) % 360.0 - 180.0)
        return (
            lon_error <= OBSERVER_TOLERANCE
            and abs(float(a[keys[1]]) - float(b[keys[1]])) <= OBSERVER_TOLERANCE
            and abs(float(a[keys[2]]) - float(b[keys[2]])) <= OBSERVER_TOLERANCE
        )
    except (KeyError, TypeError, ValueError):
        return False


def review_problem(document: dict) -> str | None:
    review = document.get("review")
    if not isinstance(review, dict) or any(not review.get(field) for field in REVIEW_FIELDS):
        return "the review record is missing required fields: " + ", ".join(REVIEW_FIELDS)
    if review.get("status") != "approved":
        return f"review status is {review.get('status')!r}, not 'approved'"
    if not isinstance(document.get("bins"), list) or len(document["bins"]) < 2:
        return "the skyline has fewer than two azimuth bins"
    return None


def load_reviewed_skyline(observer: dict, data_root: Path | None) -> tuple[dict | None, str | None, str | None]:
    """Return (skyline, reason, detail). ``skyline`` is None unless one reviewed file matches this observer."""
    folder = Path(data_root) / "terrain" / "reviewed" if data_root else None
    files = sorted(folder.glob("*.json")) if folder and folder.is_dir() else []
    if not files:
        return None, REASON_NOT_REVIEWED, "no reviewed skyline is saved for any observer"
    incomplete: str | None = None
    for path in files:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not _same_observer(document.get("observer", {}), observer):
            continue
        problem = review_problem(document)
        if problem:
            incomplete = f"{path.name}: {problem}"
            continue
        return document, None, None
    if incomplete:
        return None, REASON_REVIEW_INCOMPLETE, incomplete
    return None, REASON_NO_MATCH, "reviewed skylines exist, none for this observer"


def normalize_azimuth(azimuth_deg: float) -> float:
    return azimuth_deg % 360.0


def horizon_at_azimuth(bins: list[dict], azimuth_deg: float) -> tuple[float | None, str | None]:
    """Linear interpolation between the two bins around the azimuth, wrapping 359 to 0. A gap gives a reason."""
    if len(bins) < 2:
        return None, REASON_FEW_BINS
    az = normalize_azimuth(azimuth_deg)
    ordered = sorted(bins, key=lambda b: normalize_azimuth(float(b["azimuth_deg"])))
    stamps = [normalize_azimuth(float(b["azimuth_deg"])) for b in ordered]
    for index, left_az in enumerate(stamps):
        right_index = (index + 1) % len(ordered)
        right_az = stamps[right_index]
        span = (right_az - left_az) % 360.0 or 360.0
        offset = (az - left_az) % 360.0
        if offset <= span:
            left, right = ordered[index], ordered[right_index]
            if not left.get("known", True) or left.get("horizon_deg") is None:
                return None, REASON_GAP
            if not right.get("known", True) or right.get("horizon_deg") is None:
                return None, REASON_GAP
            fraction = offset / span
            return float(left["horizon_deg"]) + fraction * (float(right["horizon_deg"]) - float(left["horizon_deg"])), None
    return None, REASON_GAP


class HorizonSource:
    """What the engine classifies against: the flat 0 degree baseline, or a reviewed skyline if there is one."""

    def __init__(self, mode: str, skyline: dict | None = None, reason: str | None = None, detail: str | None = None) -> None:
        self.mode = mode
        self.skyline = skyline
        self.reason = reason
        self.detail = detail

    @classmethod
    def geometric(cls) -> "HorizonSource":
        return cls("geometric_0deg")

    @classmethod
    def for_observer(cls, mode: str, observer: dict, data_root: Path | None) -> "HorizonSource":
        if mode == "geometric_0deg":
            return cls.geometric()
        if mode != "terrain":
            raise ValueError(f"unknown horizon_mode {mode!r}; use geometric_0deg or terrain")
        skyline, reason, detail = load_reviewed_skyline(observer, data_root)
        return cls("terrain", skyline, reason, detail)

    def horizon_at(self, azimuth_deg: float | None) -> tuple[float | None, str | None]:
        """Horizon elevation for a body at this azimuth, or (None, reason) when terrain cannot supply one."""
        if self.mode == "geometric_0deg":
            return 0.0, None
        if self.skyline is None:
            return None, self.reason
        if azimuth_deg is None:
            return None, "missing_ephemeris"
        return horizon_at_azimuth(self.skyline["bins"], azimuth_deg)

    def describe(self) -> dict | None:
        """The ``terrain`` block of a terrain-mode result. Geometric results carry none."""
        if self.mode == "geometric_0deg":
            return None
        block = {
            "status": "reviewed" if self.skyline else "unknown",
            "reason": self.reason,
            "detail": self.detail,
            "skyline": None,
        }
        if self.skyline:
            review = self.skyline["review"]
            block["skyline"] = {
                "site_id": self.skyline.get("site_id"),
                "reviewer": review["reviewer"],
                "frame": review["frame"],
                "vertical_reference": review["vertical_reference"],
                "radial_coverage_m": review["radial_coverage_m"],
                "independent_check": review["independent_check"],
            }
        return block
