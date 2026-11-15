"""Lunar curvature, analytic sightlines and the 359°/0° boundary for the diagnostic skyline helpers.

These use small synthetic rasters, so they run without the LOLA files. They do not review terrain.
A passing run is not an M4 pass: terrain mode stays Unknown until Science completes that review.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from lunar_navigator.terrain import (
    MOON_RADIUS_M,
    HorizonBin,
    _elevation_deg,
    _latlon_to_ecef,
    horizon_at_azimuth,
    normalize_azimuth,
    sample_horizon_profile,
)

rasterio = pytest.importorskip("rasterio")
pyproj = pytest.importorskip("pyproj")

from rasterio.crs import CRS  # noqa: E402
from rasterio.transform import from_origin  # noqa: E402

R = MOON_RADIUS_M
SOUTH_POLAR = f"+proj=stere +lat_0=-90 +lon_0=0 +k=1 +x_0=0 +y_0=0 +R={R} +units=m +no_defs"


def analytic_elevation_deg(theta_rad: float, observer_h: float, target_h: float) -> float:
    """Elevation of a target at central angle theta, from the plane of the observer's local horizontal."""
    return math.degrees(
        math.atan2((R + target_h) * math.cos(theta_rad) - (R + observer_h), (R + target_h) * math.sin(theta_rad))
    )


def write_dem(path, half_extent_m: float, pixel_m: float, height_fn=None, height: float = 0.0) -> None:
    n = int(2 * half_extent_m / pixel_m)
    x = -half_extent_m + (np.arange(n) + 0.5) * pixel_m
    y = half_extent_m - (np.arange(n) + 0.5) * pixel_m
    xx, yy = np.meshgrid(x, y)
    data = np.full((n, n), height, dtype="float32") if height_fn is None else height_fn(xx, yy).astype("float32")
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=n,
        width=n,
        count=1,
        dtype="float32",
        crs=CRS.from_proj4(SOUTH_POLAR),
        transform=from_origin(-half_extent_m, half_extent_m, pixel_m, pixel_m),
        nodata=float("nan"),
    ) as dst:
        dst.write(data, 1)


# ---- spherical geometry -------------------------------------------------------------------------


@pytest.mark.parametrize("theta_deg", [0.01, 0.5, 1.0, 3.3, 9.0])
@pytest.mark.parametrize("observer_h,target_h", [(0.0, 0.0), (1738.9, 0.0), (0.0, 4864.25), (2000.0, 3500.0)])
def test_elevation_matches_analytic_formula(theta_deg, observer_h, target_h):
    theta = math.radians(theta_deg)
    observer = _latlon_to_ecef(-80.0, 10.0, observer_h, R)
    # A point theta along a meridian: same longitude, latitude moved by theta toward the pole (stops short of it).
    target = _latlon_to_ecef(-80.0 - theta_deg, 10.0, target_h, R)
    assert _elevation_deg(observer, target) == pytest.approx(analytic_elevation_deg(theta, observer_h, target_h), abs=1e-9)


def test_flat_same_height_ground_dips_by_half_the_central_angle():
    # A flat sphere-hugging surface at the observer's height is below the local horizontal by theta / 2.
    # At 100 km that is 1.649°, which a flat-plane model would call 0°.
    theta = 100_000.0 / R
    got = analytic_elevation_deg(theta, 1738.9, 1738.9)
    assert got == pytest.approx(-math.degrees(theta) / 2.0, abs=1e-9)
    assert got == pytest.approx(-1.6489, abs=5e-4)


def test_sampler_reproduces_curvature_at_100_km(tmp_path):
    dem = tmp_path / "flat.tif"
    write_dem(dem, half_extent_m=200_000.0, pixel_m=1000.0, height=0.0)
    profile = sample_horizon_profile(
        dem,
        site_id="synthetic-flat",
        longitude_east_deg=0.0,
        latitude_deg=-89.0,
        observer_height_m=0.0,
        height_source="test",
        max_range_m=100_000.0,
        step_m=100_000.0,
        azimuth_step_deg=90.0,
    )
    expected = -math.degrees(100_000.0 / R) / 2.0
    assert len(profile.bins) == 4
    for item in profile.bins:
        assert item.known and item.sample_count == 1
        assert item.horizon_deg == pytest.approx(expected, abs=1e-6)
    assert profile.status == "diagnostic_unreviewed"


def test_sampler_height_offset_matches_analytic_sightline(tmp_path):
    # Raised plateau everywhere (3000 m) seen from a 1000 m observer, one sample at 20 km.
    dem = tmp_path / "plateau.tif"
    write_dem(dem, half_extent_m=120_000.0, pixel_m=1000.0, height=3000.0)
    profile = sample_horizon_profile(
        dem,
        site_id="synthetic-plateau",
        longitude_east_deg=0.0,
        latitude_deg=-89.0,
        observer_height_m=1000.0,
        height_source="test",
        max_range_m=20_000.0,
        step_m=20_000.0,
        azimuth_step_deg=120.0,
    )
    expected = analytic_elevation_deg(20_000.0 / R, 1000.0, 3000.0)
    assert [round(b.horizon_deg, 6) for b in profile.bins] == [round(expected, 6)] * 3


# ---- the 359° / 0° boundary --------------------------------------------------------------------


def bearing_and_distance(lat0, lon0, lat, lon):
    """Initial great-circle bearing (deg clockwise from north) and distance on the sphere, vectorised."""
    p0, p = np.radians(lat0), np.radians(lat)
    dl = np.radians(lon - lon0)
    y = np.sin(dl) * np.cos(p)
    x = np.cos(p0) * np.sin(p) - np.sin(p0) * np.cos(p) * np.cos(dl)
    bearing = np.degrees(np.arctan2(y, x)) % 360.0
    a = np.sin((p - p0) / 2) ** 2 + np.cos(p0) * np.cos(p) * np.sin(dl / 2) ** 2
    return bearing, 2 * R * np.arcsin(np.sqrt(a))


@pytest.fixture(scope="module")
def north_ridge_profile(tmp_path_factory):
    """A ridge 8–12 km away that spans bearings -4°..+4° (356°..4°), and flat ground elsewhere."""
    lat0, lon0 = -89.0, 0.0
    transformer = pyproj.Transformer.from_crs(CRS.from_proj4(SOUTH_POLAR).geodetic_crs, CRS.from_proj4(SOUTH_POLAR), always_xy=True)
    inverse = pyproj.Transformer.from_crs(CRS.from_proj4(SOUTH_POLAR), CRS.from_proj4(SOUTH_POLAR).geodetic_crs, always_xy=True)

    def ridge(xx, yy):
        lon, lat = inverse.transform(xx, yy)
        bearing, dist = bearing_and_distance(lat0, lon0, lat, lon)
        off = (bearing + 180.0) % 360.0 - 180.0
        return np.where((np.abs(off) <= 4.0) & (dist >= 8_000.0) & (dist <= 12_000.0), 2000.0, 0.0)

    path = tmp_path_factory.mktemp("ridge") / "ridge.tif"
    write_dem(path, half_extent_m=60_000.0, pixel_m=100.0, height_fn=ridge)
    del transformer
    return sample_horizon_profile(
        path,
        site_id="synthetic-north-ridge",
        longitude_east_deg=lon0,
        latitude_deg=lat0,
        observer_height_m=0.0,
        height_source="test",
        max_range_m=15_000.0,
        step_m=100.0,
        azimuth_step_deg=1.0,
    )


def test_ridge_straddling_north_raises_both_sides_of_zero(north_ridge_profile):
    by_az = {int(b.azimuth_deg): b.horizon_deg for b in north_ridge_profile.bins}
    flat = by_az[90]
    for az in (357, 358, 359, 0, 1, 2, 3):
        assert by_az[az] > flat + 5.0, az  # a ridge top at 8 km and 2 km high is about 14° up
    for az in (20, 180, 340):
        assert by_az[az] == pytest.approx(flat, abs=0.2), az
    assert by_az[359] == pytest.approx(by_az[1], abs=0.5)  # symmetric about north
    assert by_az[358] == pytest.approx(by_az[2], abs=0.5)


def test_interpolation_wraps_between_359_and_0(north_ridge_profile):
    bins = north_ridge_profile.bins
    h359 = next(b for b in bins if b.azimuth_deg == 359.0).horizon_deg
    h0 = next(b for b in bins if b.azimuth_deg == 0.0).horizon_deg
    mid, reason = horizon_at_azimuth(bins, 359.5)
    assert reason is None
    assert mid == pytest.approx((h359 + h0) / 2.0, abs=1e-9)
    assert horizon_at_azimuth(bins, 359.5) == horizon_at_azimuth(bins, -0.5)  # -0.5° is 359.5°
    assert horizon_at_azimuth(bins, 0.0)[0] == pytest.approx(h0, abs=1e-12)
    assert horizon_at_azimuth(bins, 360.0)[0] == pytest.approx(h0, abs=1e-12)


# ---- helper rules, with no raster -------------------------------------------------------------


def make_bins(values, step=90.0):
    return [
        HorizonBin(azimuth_deg=i * step, horizon_deg=v, known=v is not None, sample_count=1 if v is not None else 0,
                   limiting_range_m=None, reason=None if v is not None else "no_valid_dem_samples")
        for i, v in enumerate(values)
    ]


def test_normalize_azimuth_half_open():
    assert normalize_azimuth(0.0) == 0.0
    assert normalize_azimuth(360.0) == 0.0
    assert normalize_azimuth(-0.0) == 0.0
    assert normalize_azimuth(-1e-18) == 0.0  # would round to 360.0 and break [0, 360)
    assert normalize_azimuth(-90.0) == 270.0
    assert normalize_azimuth(725.0) == 5.0
    with pytest.raises(ValueError):
        normalize_azimuth(float("nan"))


def test_wrap_at_the_seam_with_four_bins():
    bins = make_bins([10.0, 20.0, 30.0, 40.0])  # 0, 90, 180, 270
    assert horizon_at_azimuth(bins, 315.0)[0] == pytest.approx(25.0)  # halfway 270 -> 360(=0)
    assert horizon_at_azimuth(bins, 359.0)[0] == pytest.approx(40.0 + (10.0 - 40.0) * 89.0 / 90.0)
    assert horizon_at_azimuth(bins, 1.0)[0] == pytest.approx(10.0 + 10.0 / 90.0)


def test_gap_in_a_bracketing_bin_is_unknown_not_interpolated():
    bins = make_bins([10.0, None, 30.0, 40.0])
    assert horizon_at_azimuth(bins, 45.0) == (None, "terrain_gap_in_azimuth_bracket")
    assert horizon_at_azimuth(bins, 135.0) == (None, "terrain_gap_in_azimuth_bracket")
    # The gap is at 90°, so the seam bracket (270°, 0°) is unaffected.
    assert horizon_at_azimuth(bins, 315.0)[0] == pytest.approx(25.0)


def test_gap_at_zero_makes_both_sides_of_north_unknown():
    bins = make_bins([None, 20.0, 30.0, 40.0])
    assert horizon_at_azimuth(bins, 359.0) == (None, "terrain_gap_in_azimuth_bracket")
    assert horizon_at_azimuth(bins, 1.0) == (None, "terrain_gap_in_azimuth_bracket")
    assert horizon_at_azimuth(bins, 180.0)[0] == pytest.approx(30.0)


def test_too_few_bins_is_unknown():
    assert horizon_at_azimuth(make_bins([10.0]), 0.0) == (None, "insufficient_bins")
