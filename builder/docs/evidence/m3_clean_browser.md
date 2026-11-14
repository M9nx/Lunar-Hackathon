# M3.2 clean-profile offline replay

| Field | Value |
| --- | --- |
| Verdict | passed |
| Laptop | `m9nx-83dg` |
| Opened | 2026-11-14T10:34:43Z |
| Candidate | engine commit `1f3fb06` |
| Package `code_revision` | `1f3fb06` |
| Run IDs | `site04-p02-practice-q4-centre-0deg-a24325ba50c4`, `malapert-practice-q4-centre-0deg-88b9b3cfef57` |
| Browser | Chromium headless, new user-data dir `/tmp/lunar-m3-clean-profile-offline`, extensions disabled |
| Radio | Wi-Fi soft-blocked, `wlan0` down, no default route. Loopback stayed up. |
| Restored | `wlan0` connected again and the default route via `wlan0` returned after the check |

`ip link set wlan0 down` returned “Operation not permitted”. `rfkill block wifi` had already left `wlan0` down and removed the default route. Local docker bridges stayed up. The page requested only `http://127.0.0.1:8765/` resources.

The shared playhead opened at `2025-01-01T00:00:00Z`. Next moved both sites to `2025-01-01T00:15:00Z`. Site A at that step: Sun 318.49656° / +1.683516°, clear; Earth 151.802892° / −6.497028°, blocked; Both blocked. Both export URLs opened the run files above, each stamped `code_revision` `1f3fb06`.

Screenshots: `m3_clean_00.png`, `m3_clean_15.png`. Raw log: `m3_clean_browser.log`.
