---
name: lunar-nasa-ui-theme
description: >-
  NASA/USWDS-aligned UI patterns for the offline replay app: accessibility,
  mission-display layout, dark space theme. Use for M1.3, M2.2, M3 UI work.
---

# NASA-themed UI / UX (offline replay)

## Design principles (apply to `web/`)

Draw from [NASA Web Design System](https://nasa.github.io/nasawds-site/design-principles/) and [USWDS accessibility](https://designsystem.digital.gov/documentation/accessibility/):

- **Perceivable:** legible contrast; never state-only color; text labels for Clear / Blocked / Unknown.
- **Operable:** keyboard-focusable playhead and scenario controls; large hit targets (mission-touch style).
- **Understandable:** show UTC, mode (`geometric_0deg` / `terrain`), and data credits in chrome.
- **Robust:** replay reads versioned JSON only; offline vendored Plotly from `data/offline/vendor/`.

## Mission-control patterns (adapted from Open MCT)

[Open MCT](https://nasa.github.io/openmct/about-open-mct/) ideas for this hackathon scope:

- **Shared time conductor:** one UTC window / playhead drives all lanes (Sun, Earth, Both).
- **Fixed timespan mode** for hackathon demo (not live streaming).
- **Declarative status:** when zoomed or filtered, show if view may not match latest run (orange border idiom → “stale run id” badge if needed).

Operator-display lessons (VIPER-style, condensed): use **tabs or sections** to reduce clutter; prefer **graphics + numbers** for angles; reserve red/yellow/green for **status**, not for brand decoration.

## Visual theme (NASA space, lightweight CSS)

| Token | Suggestion | Use |
|-------|------------|-----|
| Background | `#0b0d17` – `#12182a` | Deep space shell |
| Panel | `#1a2332` + 1px `#2d3a4f` | Cards, inspector |
| Text primary | `#f0f4f8` | Body |
| Text muted | `#8b9cb3` | Labels, limits |
| Accent / links | `#1c71d8` – `#135b8a` | NASA WDS blue family |
| Unknown hatch | diagonal pattern + “Unknown” text | §5 contract |
| Clear / Blocked | green / amber outline **plus** word label | WCAG 2.0 AA target |

Credit NASA imagery and data in footer (`data/offline/assets`, PIA references). Do not ship live links to CDN plotly.

## Anti-patterns

- Infinite scroll timelines without interval totals.
- Hiding Unknown spans behind solid fills.
- Claiming “full comm window” from colour alone.

## Proof

M3.2: Wi-Fi off, clean browser, vendored assets only — record in `builder/docs/evidence/`.