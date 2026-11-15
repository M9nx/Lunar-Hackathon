"""Diagnostic DEM skyline sampling for centre-ray terrain work (M2.5/M4).

Produces azimuth→horizon profiles from a south-polar stereographic DEM.
Profiles are labeled diagnostic: they do not unlock terrain-mode Clear/Blocked
until Science completes the M4 review (frame, height reference, radial coverage,
independent skyline check).
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from lunar_navigator.fsio import atomic_write_json

MOON_RADIUS_M = 1_737_400.0


@dataclass(frozen=True)
class HorizonBin:
    azimuth_deg: float
    horizon_deg: float | None
    known: bool
    sample_count: int
    limiting_range_m: float | None
    reason: str | None = None


@dataclass(frozen=True)
class HorizonProfile:
    site_id: str
    dem_path: str
    longitude_east_deg: float
    latitude_deg: float
    observer_height_m: float
    height_source: str
    max_range_m: float
    step_m: float
    azimuth_step_deg: float
    status: str
    bins: list[HorizonBin]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return payload


def _destination(lat_deg: float, lon_deg: float, az_deg: float, range_m: float, radius_m: float) -> tuple[float, float]:
    """Spherical destination: return (lat_deg, lon_east_deg)."""
    lat1 = math.radians(lat_deg)
    lon1 = math.radians(lon_deg)
    brng = math.radians(az_deg)
    ang = range_m / radius_m
    sin_lat1 = math.sin(lat1)
    cos_lat1 = math.cos(lat1)
    sin_ang = math.sin(ang)
    cos_ang = math.cos(ang)
    lat2 = math.asin(sin_lat1 * cos_ang + cos_lat1 * sin_ang * math.cos(brng))
    lon2 = lon1 + math.atan2(
        math.sin(brng) * sin_ang * cos_lat1,
        cos_ang - sin_lat1 * math.sin(lat2),
    )
    lon_deg_out = (math.degrees(lon2) + 180.0) % 360.0 - 180.0
    return math.degrees(lat2), lon_deg_out


def _latlon_to_ecef(lat_deg: float, lon_deg: float, height_m: float, radius_m: float) -> np.ndarray:
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    r = radius_m + height_m
    return np.array(
        [
            r * math.cos(lat) * math.cos(lon),
            r * math.cos(lat) * math.sin(lon),
            r * math.sin(lat),
        ],
        dtype=float,
    )


def _elevation_deg(observer_ecef: np.ndarray, target_ecef: np.ndarray) -> float:
    """Elevation of target relative to local horizontal at observer (sphere normal)."""
    up = observer_ecef / np.linalg.norm(observer_ecef)
    los = target_ecef - observer_ecef
    dist = np.linalg.norm(los)
    if dist <= 0:
        return 90.0
    los_u = los / dist
    # sin(el) = los · up for local horizontal perpendicular to radius
    s = float(np.clip(np.dot(los_u, up), -1.0, 1.0))
    return math.degrees(math.asin(s))


def sample_horizon_profile(
    dem_path: Path,
    *,
    site_id: str,
    longitude_east_deg: float,
    latitude_deg: float,
    observer_height_m: float | None = None,
    height_source: str = "dem_surface",
    max_range_m: float = 80_000.0,
    step_m: float = 500.0,
    azimuth_step_deg: float = 2.0,
) -> HorizonProfile:
    """Sample a DEM along azimuth rays and return a diagnostic horizon profile."""
    import rasterio
    from pyproj import Transformer

    dem_path = Path(dem_path)
    notes = [
        "Diagnostic only — terrain mode stays Unknown until M4 review.",
        "Centre-ray classification in the demo still uses geometric 0°.",
    ]
    with rasterio.open(dem_path) as ds:
        transformer = Transformer.from_crs(ds.crs.geodetic_crs, ds.crs, always_xy=True)
        ox, oy = transformer.transform(longitude_east_deg, latitude_deg)
        row, col = ds.index(ox, oy)
        if not (0 <= row < ds.height and 0 <= col < ds.width):
            raise ValueError(f"observer outside DEM footprint for {site_id}")
        dem_surface = float(ds.read(1, window=((row, row + 1), (col, col + 1)))[0, 0])
        if not math.isfinite(dem_surface):
            raise ValueError(f"DEM NoData at observer for {site_id}")
        if observer_height_m is None:
            observer_height_m = dem_surface
            height_source = "dem_surface"
        observer_ecef = _latlon_to_ecef(latitude_deg, longitude_east_deg, observer_height_m, MOON_RADIUS_M)
        bins: list[HorizonBin] = []
        ranges = np.arange(step_m, max_range_m + step_m * 0.5, step_m)
        az_values = np.arange(0.0, 360.0, azimuth_step_deg)
        for az in az_values:
            pts_lonlat = [
                _destination(latitude_deg, longitude_east_deg, float(az), float(r_m), MOON_RADIUS_M)
                for r_m in ranges
            ]
            xy = [transformer.transform(lon2, lat2) for lat2, lon2 in pts_lonlat]
            samples = list(ds.sample(xy))
            max_el = -math.inf
            known = 0
            limit_r = None
            for r_m, (lat2, lon2), band in zip(ranges, pts_lonlat, samples, strict=True):
                z = float(band[0])
                if not math.isfinite(z):
                    continue
                target = _latlon_to_ecef(lat2, lon2, z, MOON_RADIUS_M)
                el = _elevation_deg(observer_ecef, target)
                known += 1
                if el > max_el:
                    max_el = el
                    limit_r = float(r_m)
            if known == 0:
                bins.append(
                    HorizonBin(
                        azimuth_deg=float(az),
                        horizon_deg=None,
                        known=False,
                        sample_count=0,
                        limiting_range_m=None,
                        reason="no_valid_dem_samples",
                    )
                )
            else:
                bins.append(
                    HorizonBin(
                        azimuth_deg=float(az),
                        horizon_deg=float(max_el),
                        known=True,
                        sample_count=known,
                        limiting_range_m=limit_r,
                        reason=None,
                    )
                )

    return HorizonProfile(
        site_id=site_id,
        dem_path=str(dem_path),
        longitude_east_deg=longitude_east_deg,
        latitude_deg=latitude_deg,
        observer_height_m=float(observer_height_m),
        height_source=height_source,
        max_range_m=max_range_m,
        step_m=step_m,
        azimuth_step_deg=azimuth_step_deg,
        status="diagnostic_unreviewed",
        bins=bins,
        notes=notes,
    )


def write_profile(profile: HorizonProfile, path: Path) -> None:
    atomic_write_json(Path(path), profile.to_dict())


def profile_from_csv(
    csv_path: Path,
    *,
    site_id: str,
    azimuth_col: str = "azimuth_deg",
    horizon_col: str,
    coverage_col: str | None = None,
    notes: list[str] | None = None,
) -> HorizonProfile:
    """Load a historical/diagnostic CSV into the same profile shape."""
    import csv

    bins: list[HorizonBin] = []
    with Path(csv_path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            az = float(row[azimuth_col])
            raw = row.get(horizon_col, "")
            cov = int(float(row[coverage_col])) if coverage_col and row.get(coverage_col) not in (None, "") else 0
            if raw in ("", "nan", "NaN", None):
                bins.append(HorizonBin(az, None, False, cov, None, "missing_horizon"))
                continue
            h = float(raw)
            if not math.isfinite(h):
                bins.append(HorizonBin(az, None, False, cov, None, "nan_horizon"))
                continue
            bins.append(HorizonBin(az, h, True, cov, None, None))
    return HorizonProfile(
        site_id=site_id,
        dem_path=str(csv_path),
        longitude_east_deg=float("nan"),
        latitude_deg=float("nan"),
        observer_height_m=float("nan"),
        height_source="imported_csv",
        max_range_m=float("nan"),
        step_m=float("nan"),
        azimuth_step_deg=float("nan"),
        status="diagnostic_unreviewed",
        bins=bins,
        notes=notes
        or [
            "Imported diagnostic CSV — not an M4-reviewed skyline.",
            "Demo classification remains geometric 0°.",
        ],
    )


def normalize_azimuth(azimuth_deg: float) -> float:
    """Map any finite azimuth to [0, 360), clockwise from true north."""
    if not math.isfinite(azimuth_deg):
        raise ValueError("azimuth must be finite")
    value = azimuth_deg % 360.0
    # A tiny negative input can round to 360.0 after the modulo. Keep the half-open range.
    return 0.0 if value >= 360.0 else value


def horizon_at_azimuth(bins: list[HorizonBin], azimuth_deg: float) -> tuple[float | None, str | None]:
    """Linear horizon between the two bins that bracket an azimuth, wrapping 360° back to 0°.

    Returns (horizon_deg, None) or (None, reason). A gap in either bracketing bin gives Unknown:
    a populated neighbour does not establish continuity across the gap. Needs at least two bins
    with distinct azimuths. Diagnostic helper only; terrain mode stays Unknown until the M4 review.
    """
    if len(bins) < 2:
        return None, "insufficient_bins"
    az = normalize_azimuth(azimuth_deg)
    ordered = sorted(bins, key=lambda b: b.azimuth_deg)
    lower = None
    upper = None
    for item in ordered:
        if item.azimuth_deg <= az:
            lower = item
        if item.azimuth_deg > az and upper is None:
            upper = item
    if lower is None:
        lower = ordered[-1]  # before the first bin: bracket with the last bin, one turn earlier
    if upper is None:
        upper = ordered[0]  # after the last bin: bracket with the first bin, one turn later
    if not (lower.known and upper.known) or lower.horizon_deg is None or upper.horizon_deg is None:
        return None, "terrain_gap_in_azimuth_bracket"
    lo_az = lower.azimuth_deg if lower.azimuth_deg <= az else lower.azimuth_deg - 360.0
    hi_az = upper.azimuth_deg if upper.azimuth_deg > az else upper.azimuth_deg + 360.0
    if az == lo_az:
        return float(lower.horizon_deg), None
    t = (az - lo_az) / (hi_az - lo_az)
    return float(lower.horizon_deg + t * (upper.horizon_deg - lower.horizon_deg)), None
