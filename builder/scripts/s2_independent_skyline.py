#!/usr/bin/env python3
"""Independent skyline cross-check for Science review (diagnostic, not a terrain pass).

Compares the DEM240 diagnostic profile (src/lunar_navigator/terrain.py, 240 m posting) with a separately
written sightline traced on the 20 m DEM. Differences from terrain.py:

  * other raster:       LDEM_80S_20MPP_ADJ.TIF (20 m) instead of LDEM_60S_240MPP_ADJ.TIF (240 m);
  * other ray geometry: pyproj spherical Geod.fwd for the ray points, not terrain._destination;
  * other elevation:    local East/North/Up basis at the observer, elevation = atan2(up, hypot(east, north)),
                        not the dot product with the sphere normal, and the ray's azimuth is recovered from
                        the same vectors to prove each sample lies along the requested azimuth.

It also checks the analytic flat-ground curvature case. It does not settle the frame, the vertical
reference, or radial coverage. It reports differences and states no tolerance: Science sets that.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from lunar_navigator.terrain import MOON_RADIUS_M as R  # noqa: E402  (a constant, not geometry code)
from lunar_navigator.terrain import HorizonBin, horizon_at_azimuth  # noqa: E402

DEM20 = REPO / "data/LOLA_20mpp/LDEM_80S_20MPP_ADJ.TIF"
SITES = {
    "site04-p02-practice": {
        "lon": -156.4386,
        "lat": -89.7812,
        "height_m": None,  # taken from the DEM240 profile so both traces use one observer height
        "profile": "web/review-candidate/terrain/site04-p02-practice-dem240-horizon-diagnostic.json",
    },
    "malapert-practice": {
        "lon": -2.93,
        "lat": -85.99,
        "height_m": None,
        "profile": "web/review-candidate/terrain/malapert-practice-dem240-horizon-diagnostic.json",
    },
}
AZIMUTHS = [0.0, 90.0, 180.0, 270.0, 359.0, 1.0, 318.623526]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def enu_basis(lat_deg: float, lon_deg: float):
    lat, lon = math.radians(lat_deg), math.radians(lon_deg)
    east = np.array([-math.sin(lon), math.cos(lon), 0.0])
    north = np.array([-math.sin(lat) * math.cos(lon), -math.sin(lat) * math.sin(lon), math.cos(lat)])
    up = np.array([math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)])
    return east, north, up


def ecef(lat_deg: float, lon_deg: float, height_m: float) -> np.ndarray:
    lat, lon, r = math.radians(lat_deg), math.radians(lon_deg), R + height_m
    return np.array([r * math.cos(lat) * math.cos(lon), r * math.cos(lat) * math.sin(lon), r * math.sin(lat)])


def trace(ds, transformer, geod, site: dict, azimuth_deg: float, max_range_m: float, step_m: float):
    """Maximum elevation along one azimuth, with the ray azimuth recovered from the vectors."""
    ranges = np.arange(step_m, max_range_m + step_m / 2, step_m)
    lons, lats, _ = geod.fwd(np.full_like(ranges, site["lon"]), np.full_like(ranges, site["lat"]),
                             np.full_like(ranges, azimuth_deg), ranges)
    xs, ys = transformer.transform(lons, lats)
    heights = np.array([v[0] for v in ds.sample(zip(xs, ys))], dtype=float)
    east, north, up = enu_basis(site["lat"], site["lon"])
    origin = ecef(site["lat"], site["lon"], site["height_m"])
    best = None
    worst_az_error = 0.0
    valid = 0
    for r, lon, lat, z in zip(ranges, lons, lats, heights):
        if not math.isfinite(z):
            continue
        valid += 1
        v = ecef(lat, lon, z) - origin
        e, n, u = float(v @ east), float(v @ north), float(v @ up)
        elevation = math.degrees(math.atan2(u, math.hypot(e, n)))
        recovered = math.degrees(math.atan2(e, n)) % 360.0
        diff = abs((recovered - azimuth_deg + 180.0) % 360.0 - 180.0)
        # A chord to a far point departs from the great-circle azimuth by a tiny amount; track the worst.
        worst_az_error = max(worst_az_error, diff)
        if best is None or elevation > best["elevation_deg"]:
            best = {"elevation_deg": elevation, "range_m": float(r), "height_m": float(z)}
    return best, valid, len(ranges), worst_az_error


def analytic_flat_check() -> dict:
    theta = 100_000.0 / R
    el = math.degrees(math.atan2((R + 1738.9) * math.cos(theta) - (R + 1738.9), (R + 1738.9) * math.sin(theta)))
    return {"range_m": 100000.0, "analytic_deg": el, "expected_minus_half_theta_deg": -math.degrees(theta) / 2}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True, help="JSON result path")
    parser.add_argument("--max-range-m", type=float, default=50_000.0, help="match the DEM240 profile range")
    parser.add_argument("--step-m", type=float, default=100.0)
    args = parser.parse_args()
    if not DEM20.is_file():
        print(f"missing {DEM20}; cannot run the independent check", file=sys.stderr)
        return 2
    import rasterio
    from pyproj import Geod, Transformer

    geod = Geod(a=R, b=R)
    results = {"dem20": {"path": str(DEM20.relative_to(REPO)), "sha256": sha256(DEM20)}, "sites": {}, "analytic": analytic_flat_check()}
    ok = abs(results["analytic"]["analytic_deg"] - results["analytic"]["expected_minus_half_theta_deg"]) < 1e-9
    with rasterio.open(DEM20) as ds:
        results["dem20"].update({"width": ds.width, "height": ds.height, "res_m": list(ds.res), "nodata": None if ds.nodata is None else str(ds.nodata)})
        transformer = Transformer.from_crs(ds.crs.geodetic_crs, ds.crs, always_xy=True)
        for site_id, site in SITES.items():
            profile = json.loads((REPO / site["profile"]).read_text())
            site = {**site, "height_m": profile["observer_height_m"]}
            bins = [HorizonBin(**b) for b in profile["bins"]]
            rows = []
            for az in AZIMUTHS:
                best, valid, total, az_err = trace(ds, transformer, geod, site, az, args.max_range_m, args.step_m)
                grid, grid_valid, grid_total, _ = trace(ds, transformer, geod, site, az, profile["max_range_m"], profile["step_m"])
                h240, reason = horizon_at_azimuth(bins, az)
                row = {
                    "azimuth_deg": az,
                    "dem20_horizon_deg": None if best is None else best["elevation_deg"],
                    "dem20_limiting_range_m": None if best is None else best["range_m"],
                    "dem20_valid_samples": f"{valid}/{total}",
                    "ray_azimuth_error_deg": az_err,
                    "dem20_same_radial_grid_horizon_deg": None if grid is None else grid["elevation_deg"],
                    "dem20_same_radial_grid_range_m": None if grid is None else grid["range_m"],
                    "dem240_horizon_deg": h240,
                    "dem240_note": reason,
                    "difference_deg": None if best is None or h240 is None else best["elevation_deg"] - h240,
                    "difference_same_radial_grid_deg": None if grid is None or h240 is None else grid["elevation_deg"] - h240,
                }
                rows.append(row)
                ok = ok and best is not None and valid == total and grid_valid == grid_total and az_err < 0.05
            results["sites"][site_id] = {
                "observer": {k: site[k] for k in ("lon", "lat", "height_m")},
                "observer_height_source": "DEM240 profile observer_height_m (Site04 equals the practice altitude; Malapert is the DEM surface, not the practice 0 km)",
                "native_trace": {"max_range_m": args.max_range_m, "step_m": args.step_m},
                "profile_range_m": profile["max_range_m"],
                "profile_azimuth_step_deg": profile["azimuth_step_deg"],
                "rows": rows,
            }
        # What the practice request's 0 km observer would see: it sits inside the Malapert terrain.
        probe_site = {**SITES["malapert-practice"], "height_m": 0.0}
        probe, _, _, _ = trace(ds, transformer, geod, probe_site, 0.0, 2_000.0, args.step_m)
        results["malapert_practice_altitude_probe"] = {
            "observer_height_m": 0.0,
            "azimuth_deg": 0.0,
            "max_range_m": 2000.0,
            "max_elevation_deg": probe["elevation_deg"],
            "at_range_m": probe["range_m"],
            "terrain_height_m_there": probe["height_m"],
            "reading": "A 0 m observer is inside the DEM here. This is not a usable skyline and is shown only to size the height-reference question.",
        }
    results["checks_ok"] = bool(ok)
    results["note"] = (
        "Diagnostic cross-check. Differences are reported without a tolerance. Science sets the tolerance and decides "
        "whether this is an acceptable independent skyline direction. The frame, vertical reference and radial coverage "
        "are not decided here."
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=2) + "\n")
    print(f"analytic flat 100 km: {results['analytic']['analytic_deg']:.6f} deg")
    for site_id, block in results["sites"].items():
        print(site_id)
        for r in block["rows"]:
            print(
                f"  az {r['azimuth_deg']:>10.6f}  dem240 {r['dem240_horizon_deg']:+.4f}  "
                f"dem20@same-grid {r['dem20_same_radial_grid_horizon_deg']:+.4f} (diff {r['difference_same_radial_grid_deg']:+.4f})  "
                f"dem20@100m {r['dem20_horizon_deg']:+.4f} at {r['dem20_limiting_range_m']:.0f} m (diff {r['difference_deg']:+.4f})  "
                f"ray_az_err {r['ray_azimuth_error_deg']:.1e}"
            )
    print("checks_ok", results["checks_ok"])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
