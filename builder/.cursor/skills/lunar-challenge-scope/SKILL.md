---
name: lunar-challenge-scope
description: >-
  NASA Space Apps 2026 Lunar Landing Site Navigator challenge scope, eligible
  claims, and demo story. Use when scoping features, pitch, or M0.1/M6 judging.
---

# Challenge scope (Space Apps 2026)

## What judges expect (paraphrase official brief)

- Compare **lunar south-pole landing sites and dates** for planners, educators, or public.
- Show **Sun and Earth relative to the local horizon** to inform **solar illumination** and **direct-to-Earth visibility** thinking — not guaranteed power or comm links.
- Prefer **intuitive** site/date selection and comparison over opaque expert tools.

Sources: [Challenge hub](https://www.spaceappschallenge.org/2026/), [Lunar Landing Site Navigator](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/) (confirm live wording at kickoff).

## What this repo implements (Master Reference §3)

- **Centre-ray clearance** vs `0°` or reviewed terrain skyline.
- **Saved JPL Horizons** (Q4 apparent airless) as primary ephemeris for offline demo.
- **Two scenarios**, shared UTC playhead, Sun / Earth / Both lanes, explicit **Unknown**.
- **Wi-Fi-off replay** of versioned JSON results.

## Out of scope unless upgraded (§10)

- Full power models, DSN link budgets, finite-disc, station-specific Earth contacts.
- Multi-DEM stacks without frame/height review.

## NASA data eligibility

Global Awards: cite ≥1 NASA source from the challenge **Resources** tab when claiming eligibility. Record `asset_id` and credits in run manifest (§5).

## Agent rule

Scope changes go through `builder/docs/decision-log.md` and may affect pitch (M6.3) — not silent UI copy changes.