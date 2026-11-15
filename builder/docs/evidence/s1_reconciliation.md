# Sprint 1: dependable engine, stream and evidence (2026-11-15)

**Tested revision:** `f534f8c-dirty` (HEAD `f534f8c`, working tree with the Sprint 1 changes). Code digest `222bce15095b1ad37b7d6781c92500134c293d045f504fc8448109958882c6a3` over `src/ tests/ web/ builder/scripts/ Master-Reference/`, recorded before and after the run and equal (`s1/revision_before.json`, `s1/revision_after.json`). The witnessed replay `web/replay` (revision `1f3fb06`) was not touched: its digest was equal before and after (`s1/summary.txt`). Nothing was committed or pushed. Local only.

Run command: `builder/scripts/run_sprint_evidence.sh s1`. Output: `builder/docs/evidence/s1/`.

## 1. Dependency accounting

| Item | Before | After | Why |
|---|---|---|---|
| Harness | `skipped` counted as complete | `skipped` earns no credit and releases nothing | `_harness.COMPLETE_STATUSES` no longer contains it |
| M3.4 | `passed_with_open_decisions` | `blocked` | Depends on M2.5, which is blocked. Was invalid credit |
| M5.1 | `skipped` (counted complete) | `planned` | Depends on M4.4, which is not met |
| M0.3 | `passed` | `passed_with_open_decisions` | Appendix B raw digest mismatch is open (`horizons_digest_provenance.md`) |
| Scope change | none | `SC-1` **proposed, not approved** | Releasing M2.5 for a geometric 0° scope needs Lead and Science. See `s2_scope_decision.md` |

New: `builder/scripts/task_counts.py` (verified / conditional / invalid_credit / descoped / blocked / planned), `tests/test_harness_accounting.py` (7 tests). Only an `approved` entry in `scope_changes` with `approved_by` and `approved_utc` can release a dependency, and it still earns no credit.

Verified counts now (`s1/task_counts.txt`): full roadmap 14/32 verified (43.8%), 17/32 with conditionals (53.1%); core local product 14/24 verified (58.3%), 17/24 with conditionals (70.8%). Blocked 3 (M2.5, M3.4, M4.1). Conditional 3 (M0.1, M0.2, M0.3). In progress 1 (M6.1). No invalid credit remains.

## 2. Failure and Stop feedback

Root cause of the wrong headline: the engine counted samples it had **computed** for the other site but not yet **delivered**. After Site04's first batch, `shared_samples` said 3 while the client had no Malapert samples, so the screen said "Waiting for the first shared sample" beside a status that said "Shared samples 3". Fix in `engine.py`: events count delivered samples only, and carry `cutoff_utc` (last shared sample) and `covered_through_utc` (end of that sample's interval; the terminal sample adds 0 s).

UI (`web/review-candidate/app.js`):

- Failed or stopped with shared samples: banner "Stopped|Failed. Incomplete run. Partial result through `<cutoff>` (N shared samples; totals cover through `<covered>`). Not exportable." Status line adds the per-site delivery.
- Failed before any shared sample: "Failed before any shared sample was delivered. Site04 delivered 3, Malapert delivered 0. There is no partial result and no export."
- Stop: the button reads "Stopping…" (disabled), the chip reads "Stopping", the headline says totals are not final, and buffered batches drain without playback delay. The final text appears only on the engine's `cancelled` event.
- Export link exists only after `complete`. Failed and stopped runs show "No export: the run did not complete."

Trace (`s1/live_trace.json`, 28 checks, 0 failed):

| Case | Result |
|---|---|
| Stop at default speed | 20 shared at the click. `Stopping` at t=0.01 s. Stopped at t=0.15 s: "Final cutoff 2025-01-01T08:45:00Z (36 of 193 shared samples). Totals cover through 2025-01-01T09:00:00Z". The engine ran ahead of the paced display; the screen shows the engine's cutoff, not the click-time count |
| Failure, A fails after batch 1 | Cutoff `2025-01-01T00:45:00Z`, 4 of 193 shared, delivered Site04 6 and Malapert 4 |
| Failure before a shared sample | Delivered Site04 3, Malapert 0. No waiting line, no export |
| Restart after Stop | New comparison id, completes, export overlap equals the saved overlap |

Screens: `s1/s1_stopped.png`, `s1/s1_failed_shared.png`, `s1/s1_failed_no_shared.png`, `s1/s1_complete.png`.

## 3. Atomic writes and invalidation

- `lunar_navigator/fsio.py`: temp file in the same directory, `fsync`, `os.replace`, directory `fsync`. `write_json` and `terrain.write_profile` use it. `package` stages all three files, then publishes with renames and puts `comparison.json` last.
- `package --out` now **refuses** `web/replay` unless `--allow-replay-overwrite` is given. The default `--out` used to be the witnessed replay.
- `tests/test_atomic_io.py` (11 tests): unserializable payload, interrupt while staging, interrupt before publish, set staged then interrupted, an interrupted `package` keeps the previous valid export byte for byte and leaves no `.tmp`, and the guard on `web/replay`.
- Cache: the run path has **no cache**. Every run re-reads inputs and checks the CSV and raw digests against provenance. A changed CSV byte fails with "angle CSV SHA-256 does not match provenance". The run id ends with the Sun CSV digest prefix, so it is a pure function of the inputs (tested).
- Residual: the publish phase is `os.replace` per file. A kill between two renames could mix files from two builds for a few microseconds. Documented, not eliminated.

## 4. Sky trace reconciliation

`review_candidate_sky_trace.md` described a Sky Scene UI that is not in the code (`scene-utc`, `verdict-line`, `site-verdict`: zero matches in `web/review-candidate/`) and claimed 163 checks; the committed log says 139. It is now marked **superseded** at the top. The current UI was rerun at the recorded revision: 139 of 139 (`s1/browser/review_candidate_browser.log`), plus the 28-check live trace. `review_candidate_flow_trace.md` remains the description of the current flow; its revision line (`1f3fb06`) is the replay revision, not the tested UI revision.

## 5. Raw Horizons digest sets

`builder/scripts/horizons_digest_check.py` writes `s1/horizons_digest_provenance.md` and the committed copy `horizons_digest_provenance.md`. Both sets are kept: Appendix B and the on-disk files. All four raw digests differ from Appendix B (4 of 4); all four equal their provenance receipts; all four CSV digests equal Appendix B. Status stays **open**. The response header carries a generation stamp, which is a hypothesis for the difference and is not used to close the item.

## Exit evidence checklist

| Required | Evidence | Result |
|---|---|---|
| Reproducible two-site run | `live_trace.json` complete run; `run_id_a/b` `site04-p02-practice-q4-centre-0deg-a24325ba50c4` / `malapert-practice-q4-centre-0deg-88b9b3cfef57` | pass |
| Batch/stream parity | engine batch overlap equals the live export overlap equals `web/replay/comparison.json` overlap; `tests/test_stream.py` | pass |
| Forced failure | two cases above | pass |
| Cancellation trace | Stop timeline in `live_trace.json` | pass |
| Screen equals export | headline 48 h / 0 h, details 172800 s, export overlap | pass |
| 48 h vs 0 h Sun-centre, 0 h joint | `batch_reference`: `[172800, 0]` and `[0, 0]` | pass |
| One recorded revision | `f534f8c-dirty`, digest before = after | pass |
| Pytest | 57 passed (`s1/pytest.log`) | pass |

Not closed: Appendix B raw digest identity (open). Terrain (M2.5). Lead eligibility and deliverables (M0.1).
