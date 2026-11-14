# M3 practice replay review

Tied to package `web/replay/` at git `4ddc29b-dirty`.

| Run | ID |
| --- | --- |
| Site A `site04-p02-practice` | `site04-p02-practice-q4-centre-0deg-a24325ba50c4` |
| Site B `malapert-practice` | `malapert-practice-q4-centre-0deg-88b9b3cfef57` |

Practice only. `eligible_for_submission_claim` is false. Appendix B raw-response file identity stays open.

## Separate reviewer

Reviewer session [centre-ray replay review](89204d16-ed87-4a7b-99b9-d1d4bc52fafb). Read-only. No Product 69 benchmark.

| Check | Result |
| --- | --- |
| Site A `2025-01-01T00:00:00Z` from `angles.csv` and `response.json` | Pass |
| Full-window totals, both sites, from the CSVs | Pass |
| `comparison.json` overlap and local export hrefs | Pass |

Site A at that instant: Sun azimuth 318.623526°, elevation 1.683925°, clear. Earth azimuth 151.799812°, elevation −6.503228°, blocked. Both blocked. Each lane sums to 172800 s. Site A Sun clear 172800 s. Site B Sun, Earth, and Both blocked 172800 s. Unknown 0 s. Sun-centre clear delta (B − A) is −172800 s. Both-centres-clear delta is 0.

The stored response lines drop one leading blank from the Horizons `$$SOE` row. The angle columns match. That is row agreement, not raw-file identity.

## Offline browser (session operator, `m9nx-83dg`)

Wi-Fi soft-blocked and `wlan0` down at 2026-11-14T10:11:45Z. Loopback stayed up. `http://127.0.0.1:8765/` loaded the package, showed both sites at `2025-01-01T00:00:00Z`, and Next moved both sites together to `2025-01-01T00:15:00Z`. The Site A export URL opened `runs/site04-p02-practice.json`. Radio restored at 2026-11-14T10:12:40Z.

This browser is the Cursor tab used in this session, not a separately attested extension-free profile.

## Commands

| Command | Exit |
| --- | --- |
| `PYTHONPATH=src python3 -m lunar_navigator.cli package --out web/replay` | 0 |
| `python3 builder/scripts/verify_result_contract.py` on both run files | 0 |
| `.venv/bin/python -m pytest tests -q` | 0 (13 passed) |
| `python3 builder/scripts/run_acceptance.py --gate M1` | 0 |
