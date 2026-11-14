# Evidence artifacts

Fresh acceptance logs for this repository (not historical edu outputs).

| File | Milestone | Description |
|------|-----------|-------------|
| `m0_offline_smoke.log` | M0.5 (partial) | `lunar_offline_pack.py check core` + `check-horizons` |
| `m0_4_wheels.log` | M0.4 | Offline venv install from `data/offline/wheels/cpython-314-linux-x86_64/` |
| `m0_4_open_dem.log` | M0.4 | `check core terrain --open-dem` with rasterio |
| `m0_5_observed_2026-11-14.md` | M0.5 (earlier) | Wi-Fi was on before the witness |
| `wifi_off_attestation.txt` | M0.5 | `witness=m9nx utc=2026-11-14T09:54:24Z laptop=m9nx-83dg wifi=off` |
| `m0_5_wifi_off.log` | M0.5 | Radio off, smoke exit 0, radio restored |
| `m0_5_backup_checksums.log` | M0.5 | Core and Horizons checks on `data/` and the backup |
| `m3_review.md` | M3 | Separate reviewer plus offline browser notes |

**Backup:** `/home/m9nx/Lunar-Hackathon-data-backup`.