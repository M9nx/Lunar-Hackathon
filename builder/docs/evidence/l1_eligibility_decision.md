# Lead L1 — submission eligibility decision

**Decision:** APPROVE  
**Role:** Lead (recorded at Lead’s instruction in-chat, 2026-11-15)  
**UTC:** 2026-11-15T09:11:00Z (approx.; local recording)

## Question

Are the saved January 2025 Horizons practice runs eligible to **support a Space Apps submission claim**, or rehearsal only?

## Answer

**Eligible to support a submission claim** for the geometric **0° centre-ray** product on these packs:

| Pack | Path |
| --- | --- |
| Witnessed 48 h | `web/replay/` (`code_revision` `1f3fb06`) |
| Practice 30 days | `web/review-candidate/cases/practice-30d/` |
| Practice Jan 3–10 | `web/review-candidate/cases/practice-jan03-10/` |

`eligible_for_submission_claim` is set **true** on those comparison and run JSON files. QA fixtures stay **false** (synthetic).

## Sites and method (unchanged)

- Site04 `site04-p02-practice`: −156.4386° E, −89.7812°, 1.738902 km  
- Malapert `malapert-practice`: −2.93° E, −85.99°, **0 km** (practice height; Lead accepts this for the claim)  
- Sun `10`, Earth `399`, observer `301`, Q4 airless, centre-ray, geometric 0°  
- Ephemeris: JPL Horizons saved under `data/horizons/`

## Risks Lead accepts (still open, not blockers for this flag)

1. Malapert 0 km vs DEM surface — Science S3 still open for terrain; 0° claim uses the saved Horizons height.  
2. Appendix B vs on-disk `response.json` hash — open; angle CSVs support the totals.  
3. Terrain Clear/Blocked — **not** claimed; M4 still blocked.  
4. L2–L5 (Resources format, AI disclosure, demo build choice, public URL) — still Lead follow-ups; L1 alone does not finish the Project tab.

## Not claimed

Disc visibility, received power, ground-station contact, terrain clearance, Product 69 like-for-like match.

## Follow-up

- Fill L2–L5 when Resources/demo packaging is ready.  
- Science may still approve SC-1 / S1–S5 separately; L1 does not close M4.
