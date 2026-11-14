---
name: lunar-m0-offline-smoke
description: >-
  Runs M0.4/M0.5 offline runtime and smoke checks: wheel install, imports,
  pack verification, Wi-Fi-off witness, backup copy, clean browser replay.
---

# M0 offline smoke (M0.4 / M0.5 / M3)

## M0.4 — Runtime

1. Wheel tag: `data/offline/wheels/cpython-314-linux-x86_64/`.
2. `builder/scripts/verify_offline_wheels.sh` → repo `.venv`.
3. Record Python version in `builder/docs/task-log.md`.

## M0.5 — Wi-Fi off (demo laptop)

**Environment:** network interfaces **disabled** (not just idle); **loopback** OK for `python3 -m http.server` on replay directory.

1. Create `builder/docs/evidence/wifi_off_attestation.txt`:
   `witness=<name> utc=<ISO8601Z> laptop=<id> wifi=off`
2. `builder/scripts/wifi_off_smoke.sh` (or `WIFI_OFF_CONFIRMED=1` dev-only — not for freeze).
3. `builder/scripts/offline_pack.sh check core` + `check-horizons`.
4. With venv: open DEM window smoke (`check core terrain --open-dem`).
5. **Backup:** confirm second copy of `data/` bundle exists; note path in handoff `backup_copy_noted`.

### Clean browser profile (M0.5 minimum)

- No extensions; no cached CDN assets.
- Load vendored Plotly from `data/offline/vendor/` only when UI shell exists (M1.3+); until then, asset hash check is sufficient.

## M3.2 — Repeat with replay

Same Wi-Fi-off discipline on:

- Frozen `web/` replay directory
- Shared playhead + export file open
- No external network requests (DevTools / browser network panel empty)

## Separate

- **Missing core** (Horizons practice, core DEM, vendored JS) → block.
- **Missing optional** packs (spice, visuals, upgrade 20 m) → document only.

## Evidence

`builder/docs/evidence/` + `agent_handoff.json` → `report.evidence_refs`.