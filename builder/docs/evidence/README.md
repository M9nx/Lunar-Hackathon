# Evidence artifacts

Fresh acceptance logs for this repository (not historical edu outputs).

| File | Milestone | Description |
|------|-----------|-------------|
| `m0_offline_smoke.log` | M0.5 (partial) | `lunar_offline_pack.py check core` + `check-horizons` |
| `m0_4_wheels.log` | M0.4 | Offline venv install from `data/offline/wheels/cpython-314-linux-x86_64/` |
| `m0_4_open_dem.log` | M0.4 | `check core terrain --open-dem` with rasterio |
| `m0_5_observed_2026-11-14.md` | M0.5 (not a pass) | Wi-Fi still on, no backup, practice case-fit and 0° recompute |

**M0.5 still requires:** Wi-Fi disabled on the demo laptop with witness note (QA), plus a second copy of `data/`.