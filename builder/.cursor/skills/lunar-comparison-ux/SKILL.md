---
name: lunar-comparison-ux
description: >-
  Two-site comparison UX: shared playhead, inspector, export parity, demo flow
  per Master Reference §3 and §10 judging walkthrough.
---

# Comparison UX (product §3)

## Core demo flow

1. Open saved comparison — site labels, horizon mode, UTC window visible.
2. Show Sun, Earth, Both **durations** + **unknown** time separately.
3. Move **shared playhead** — inspector shows body, azimuth, elevation, horizon, margin, state, reason/source.
4. Export matches screen (same JSON the UI loaded).
5. Optional +24 h shift uses **elapsed alignment** with both UTC timestamps labeled.

## Layout (M1.3 → M2.2)

| Zone | Content |
|------|---------|
| Scenario bar | Site A / B, mode badge, UTC range |
| Time conductor | Playhead, lane totals, unknown chip |
| Lanes | Sun, Earth, Both — hatched Unknown |
| Inspector | Selected instant; broken lines for missing values |
| Provenance drawer | Horizons row ref, run id, schema version |

## Judging verification (§10)

Judges should read states **without color alone**, reproduce selected instant from displayed numbers, open matching export.

## Implementation lane

- UI reads **states from result JSON**; no client-side recompute of science.
- Use `lunar-nasa-ui-theme` for tokens and a11y.
- Synthetic fixtures labeled until M1.4 real case connected.

## QA checklist

- Two sites share one UTC axis (not two independent clocks).
- Unknown reason string visible at least once in demo path.