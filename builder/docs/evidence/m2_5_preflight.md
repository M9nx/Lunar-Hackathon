# M2.5 terrain preflight

14 November 2026. Diagnostic evidence for Science and Data. This is not a terrain-mode result. The replay stays the witnessed 0° practice package.

## Replay to keep

PR #1 (head `4cd9a52`, squash-merged into `main` as `d40d575`). Clean-profile witness 2026-11-14T10:35:24Z. Engine revision in the package: `1f3fb06`. Run IDs `site04-p02-practice-q4-centre-0deg-a24325ba50c4` and `malapert-practice-q4-centre-0deg-88b9b3cfef57`. That package was not regenerated for this preflight.

## Raw-response digests

On this laptop, the four `data/horizons` `response.json` files hash to the raw digests stored in the PR run inputs:

| Body | On disk and in the PR export | Appendix B |
| --- | --- | --- |
| Site04 Sun | `2a2de2cf21f3af5ab9389f49a93113c8bcaf4b77b48b598c6e5b9fc93a6bbe5e` | `5780cd3a9408d40422c19abf6d261dd0a12b75082cf6452d45af4a380c85d6a0` |
| Site04 Earth | `ab2d2e3637f0167c1a4d8571c4111454456c1180dad9937f4f96ca699391333b` | `958d9df566e14dda443911bbfc2807b1cd3c2ca6d0735241fdaa17172d6a4293` |
| Malapert Sun | `23728e4272ee5c9a9ff577d649882e749d5df29c660c1ee7fa004f91744f4666` | `ebe7f553f36d19b17142b687d4bce78b2e086118a902e912fe49325eed89cbfc` |
| Malapert Earth | `30f9514e69c710a2905c31bb9ee903bc94f2a7ac208222c7af18d3f28ba073b3` | `3e4896bd984beee030b60af3d6a4892348ce34739a7e2d91b65b8e60345eb115` |

A separate local rerun reported the opposite file identity: workspace responses matching Appendix B, and the four PR raw hashes differing. Both digest sets stay. Angle CSV hashes match the PR results and Appendix B. Pytest on this laptop: 19 passed after the frame check, including the practice totals. That is angle agreement, not raw-file identity.

## DEM screen

`data/LOLA_20mpp/LDEM_60S_240MPP_ADJ.TIF`, SHA-256 `3f9663257b63022f2b0d5a623482ff3cadddceb91594a4e4ca14a94d8cec8b34`. Recomputed here: 7760×7760, 240 m posting, `AREA_OR_POINT=Area`, NoData NaN. The projected CRS authority is IAU 30135, south-polar stereographic, sphere radius 1,737,400 m. The nested geographic datum authority in the same WKT is IAU 30100. PGDA documents the large-area DEMs in MOON_ME/DE421. Saved Horizons headers report MEAN_ME for the observer and DE441 as the ephemeris source. Those fields have different roles. Science still confirms the frame tie and the DEM height reference.

The row and column indices below were supplied with the preflight. This check read those pixels. It did not reproject the practice coordinates.

| Site | Raster row, col | Pixel height | 3×3 height range | Practice Horizons reference altitude |
| --- | --- | ---: | ---: | ---: |
| Site04 | 3905, 3868 | 1,734.31 m | 1,673.64–1,734.31 m | 1,738.902 m |
| Malapert | 3373, 3854 | 4,864.25 m | 4,793.33–4,911.73 m | 0 m |

The Malapert neighborhood is a reason to review the 0 km observer before treating it as a surface point. **4.86425 km is a sensitivity input**, not the practice altitude and not a reviewed surface height.

## Reported altitude sensitivity

Not re-queried on this laptop. The reported capture used Malapert longitude −2.93° east, latitude −85.99°, altitude 4.864250 km, the same 48-hour grid, quantity 4, Sun 10 and Earth 399. Both bodies stayed Blocked. 0 of 193 samples changed state at 0°. 172,800 s Blocked and 0 s Unknown per lane. Diagnostic run ID `malapert-product90-altitude-diagnostic-q4-centre-0deg-1011167ec2ed`.

| Export directory suffix | Response SHA-256 | Angle CSV SHA-256 |
| --- | --- | --- |
| `sun-3f867c10f51b` | `b1abd721a7f98050c02203faebd5a854479f24f77d3dd5d2ac163e35d4111ca0` | `1011167ec2ed6b7829d6e285cc11f20d05af4822bc887feecc7ff1dc37c4fc0d` |
| `earth-f7817e66ad4b` | `012101444f5e6264b71b72ca72a47b4db4f740051323a391ffbfd07eed5f61f5` | `d8a760a43498db6ffb7dbcc47e46e411160a2184f2816cdcb8ef328fb8e644f8` |

Those directories are not under this laptop’s `data/horizons/`. A later query can hash differently. Keep each receipt with its capture. Reproduce with `lunar_offline_pack.py horizons` and the team contact value, then `check-horizons`.

## Reported skyline diagnostic

Not re-run here. The report sampled 835 points from 0 to 100 km at each of 193 azimuths per site and body, 644,620 queries, all in valid cells. At Site04 Sun azimuth 318.623526°, a separate geodesic from 1 to 100 km gave a diagnostic maximum of about −2.482407° near 53.50 km, using observer height 1,738.902 m and DEM heights as radial offsets on the raster sphere. Two forms of that same geometry agreed to within 1.2×10⁻¹¹°. An independently traversed profile with reviewed conventions and range is still required for M4. Terrain stays Unknown in the replay.

## Intake check added

The production path now requires the scenario’s `observer_frame` and `angle_convention`. The raw header must declare that frame and airless apparent columns (`Atmos refraction: NO (AIRLESS)`, `Azi_(a-app)`, `Elev_(a-app)`). A copy that changes MEAN_ME to MOON_PA, or the airless markers to refracted markers, is rejected after its receipt hash is updated. Practice scenarios declare `MEAN_ME` and `airless_apparent`. The witnessed replay headers were not edited.
