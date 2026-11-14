"""Diagnostic DEM skyline helpers — not an M4 terrain-mode pass."""

from pathlib import Path

from lunar_navigator.terrain import HorizonBin, sample_horizon_profile

ROOT = Path(__file__).resolve().parents[1]
DEM = ROOT / "data" / "LOLA_20mpp" / "LDEM_60S_240MPP_ADJ.TIF"
PROFILE = ROOT / "web" / "review-candidate" / "terrain" / "site04-p02-practice-dem240-horizon-diagnostic.json"


def test_diagnostic_profile_artifact_exists():
    assert PROFILE.is_file()
    text = PROFILE.read_text()
    assert "diagnostic_unreviewed" in text
    assert "site04-p02-practice" in text


def test_sample_horizon_profile_smoke():
    if not DEM.is_file():
        return
    profile = sample_horizon_profile(
        DEM,
        site_id="site04-p02-practice",
        longitude_east_deg=-156.4386,
        latitude_deg=-89.7812,
        observer_height_m=1738.902,
        max_range_m=8000,
        step_m=2000,
        azimuth_step_deg=90,
    )
    assert profile.status == "diagnostic_unreviewed"
    assert len(profile.bins) == 4
    assert all(isinstance(bin_, HorizonBin) for bin_ in profile.bins)
    assert any(bin_.known and bin_.horizon_deg is not None for bin_ in profile.bins)
