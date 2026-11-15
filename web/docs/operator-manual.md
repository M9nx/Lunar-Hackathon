# Operator Manual — Lunar Landing Site Navigator (local candidate)

For the person who prepares, starts, checks, and recovers the demo machine. Users read the [User Guide](user-guide.md). Method detail is in the [Science and Data Reference](science-and-data-reference.md).

Every command below was run on the tested machine (Linux, Python 3.14.9, Chromium) from the repository root, and `builder/scripts/verify_release_package.py` runs them again against a copy of the candidate and records the outcome under `builder/docs/evidence/s3/`. Paths are relative to the repository root.

## 1. Prerequisites

| Need | For | Notes |
| --- | --- | --- |
| Python 3.10 or newer (tested: 3.14.9) | `serve`, `run`, `package`, `record_revision.py`, notebook | Standard library only. No `pip install` for these. |
| `.venv/bin/python` with `pytest`, `numpy`, `rasterio`, `pyproj` | the test suite and terrain-diagnostic code | System `python3` has no pytest. Wheels for this interpreter are cached under `data/offline/wheels/`; `builder/scripts/verify_offline_wheels.sh` checks them. |
| Chromium or Chrome | the page | Chromium at `/usr/bin/chromium` was used. |
| `chromedriver` (matching version) | only the browser checks (`builder/scripts/*browser*`, `s2_flow_check.py`) | Not needed to use the page. |
| `curl` and internet | only to *acquire* new Horizons data or DEM packs | Never needed to run or replay. |

No CDN. All page assets (including Three.js under `web/review-candidate/vendor/`) are local.

## 2. Where things are

| Path | What |
| --- | --- |
| `data/horizons/<site>/<body>-<hash>/response.json`, `provenance.json`, `angles.csv` | Saved JPL Horizons exports. Four sites: `site04-p02-practice`, `malapert-practice`, and the `-30d` pair. Not in git. Back them up. |
| `data/LOLA_*`, `data/spice`, `data/offline` | DEMs, kernels, wheel cache (terrain/M0 work only). |
| `tests/fixtures/*_scenario.json` | Scenario records: site, observer coordinates and height, window, step, body files. |
| `web/index.html` | Landing page. |
| `web/documents.html`, `web/assets/` | Rendered manual and reference viewer, shared header and footer, styles, and vendored marked, DOMPurify, and fonts (no CDN). |
| `web/review-candidate/tour.js`, `tour.css` | The in-page guide: a welcome dialog and twenty-five steps that point at every control that point at the navigator controls. Open it from the header **Guide** button or `?tour=1`. It shows once on a first visit (never under browser automation) and is silenced by "Do not show this dialog again" or `?tour=0`. |
| `web/docs/` | Served mirror of the markdown guides. The viewer fetches these files. Copy `docs/*.md` here after editing a guide. |
| `web/replay/` | Witnessed 48 h package (revision 1f3fb06). **Do not edit or regenerate in place.** `package` refuses to write here unless `--allow-replay-overwrite`. |
| `web/review-candidate/` | The navigator. `cases/practice-30d/` is the saved 30-day package. `cases/practice-jan03-10/` is the Jan 3–10 package. `qa-*.json` is the synthetic fixture. |
| `docs/notebooks/` | Notebook that traces an observation to an interval total. |
| `docs/release/` | Release notes, manifest, walkthrough. |
| `builder/docs/evidence/` | Evidence per sprint (`s1/`, `s2/`, `s3/`) and records. |
| `builder/agent_handoff.json`, `builder/docs/task-log.md`, `builder/docs/decision-log.md` | Live status. |

The M0.5 backup `/home/m9nx/Lunar-Hackathon-data-backup` was made **before** the 30-day exports existed. Copy `data/horizons/*-30d` to it, then run `python3 lunar_offline_pack.py check-horizons` (§4) to confirm.

## 3. Start and stop

**Live page (normal).**

```sh
    PYTHONPATH=src python3 -m lunar_navigator.cli --revision "$(python3 builder/scripts/record_revision.py --label)" serve --port 8766
```

Open `http://127.0.0.1:8766/`. The landing page links to the navigator (`/review-candidate/`), the witnessed replay (`/replay/`), and the rendered manual and reference (`/documents.html`). The server serves `web/` and the calculation endpoints on `127.0.0.1` only. `--revision` is shown on the page and stored in runs; use the label printed by `record_revision.py`. Stop with Ctrl-C. Do not stop it while someone is using the page; a run in progress is lost.

**Replay only (no engine).**

```sh
python3 -m http.server 8766 --directory web
```

Then `http://127.0.0.1:8766/` (landing page), `http://127.0.0.1:8766/review-candidate/` (saved cases), or `http://127.0.0.1:8766/replay/` (witnessed package). **Start stream** is unavailable in this mode, by design.

**Markdown guides.** The server serves `.md` files with `Content-Type: text/markdown`, so the landing-page links to the guides display in the browser.

A port in use: change `--port` and the URL.

## 4. Verify inputs

Check file integrity, scenario fit, and event eligibility as three separate steps.

1. **File integrity, no network.**

   ```sh
   python3 lunar_offline_pack.py check-horizons
   ```

   Expect `OK` for all eight `angles.csv` files with 193 (48 h) or 721 (30 d) rows.
2. **Scenario fit.** Target, observer coordinates, height reference, frame, angle convention, UTC window, and cadence against the saved response:

   ```sh
   for f in site04_p02_practice malapert_practice site04_p02_practice_30d malapert_practice_30d; do
     python3 builder/scripts/case_fit_horizons.py --scenario tests/fixtures/${f}_scenario.json
   done
   ```

   Expect `pass=True` four times.
3. **Provenance of the raw files.**

   ```sh
   python3 builder/scripts/horizons_digest_check.py --check
   ```

   It compares raw-response SHA-256 values with the provenance records and Appendix B. The Appendix B mismatch for the original 48 h files is **open** and is kept open (see Known limits). The 30-day files are not in Appendix B and report `not_in_appendix_b`.
4. **Eligibility** is a Lead decision, not a file check. Every case is practice. `eligible_for_submission_claim` stays `false` until the Lead records a decision in `builder/docs/evidence/s2_scope_decision.md`.

The engine repeats checks on every run: it rejects a response whose hash does not match its provenance, whose frame or angle convention differs, or that has conflicting duplicate timestamps, and it gives an error naming the file. A grid with missing rows is not an error: the grid is kept and the missing samples are `unknown` with a reason.

## 5. Offline replay

1. Disconnect networking (Wi-Fi off).
2. Run `builder/scripts/wifi_off_smoke.sh` (needs the attestation file at `builder/docs/evidence/wifi_off_attestation.txt`, written by the person who turned Wi-Fi off, or `WIFI_OFF_CONFIRMED=1` for development only). It runs the pack checks without network.
3. Start the server (§3) and open the page. Nothing in the demo path fetches from the internet.

Keep **acquisition** separate:

```sh
python3 lunar_offline_pack.py horizons --practice --contact you@example.org
python3 lunar_offline_pack.py horizons --site NAME,LON,LAT,ALT_KM --start 2025-01-01T00:00Z --stop 2025-01-31T00:00Z --step-min 60 --contact you@example.org
```

Run these only on a connected machine, then repeat §4. Always give a real `--contact`; do not invent one. A failed download leaves existing files and replay unaffected. A new site also needs a scenario record and a source line in `live_server.py`; that is an engineering change, not an operator step.

## 6. Regenerate and compare the saved packages

```sh
PYTHONPATH=src python3 -m lunar_navigator.cli --revision "$(python3 builder/scripts/record_revision.py --label)" package --pair practice-30d --out /tmp/p30
PYTHONPATH=src python3 -m lunar_navigator.cli --revision "$(python3 builder/scripts/record_revision.py --label)" package --pair practice-48h --out /tmp/p48
```

To package any shared catalog window (for example the Jan 3–10 case):

```sh
PYTHONPATH=src python3 -m lunar_navigator.cli --revision "$(python3 builder/scripts/record_revision.py --label)" \
  package --catalog-window "malapert-practice__20250103T000000Z__20250110T000000Z__900s++site04-p02-practice__20250103T000000Z__20250110T000000Z__900s" \
  --out web/review-candidate/cases/practice-jan03-10
```

The outputs are the same as the saved packages apart from `code_revision`. `verify_release_package.py` checks this. Never write into `web/replay` (guarded) and never run `package` with `--out web/review-candidate/cases/practice-30d` unless you intend to replace that package; it is published atomically (§8).

Other checks:

```sh
.venv/bin/python -m pytest tests -q -p no:cacheprovider
python3 builder/scripts/validate_handoff.py
python3 builder/scripts/check_commit_coauthors.py
builder/scripts/run_sprint_evidence.sh s3     # full evidence run at the current revision
python3 builder/scripts/run_notebook.py --check docs/notebooks/01_trace_observation_to_interval_total.ipynb   # run it, change nothing
```

`run_sprint_evidence.sh` takes several minutes, runs in the foreground, and refuses to publish if the code digest changes while it runs. `build_notebook.py` rewrites the notebook from source **without outputs**; follow it with `run_notebook.py <notebook>` (no `--check`) to store the outputs, because `tests/test_notebook.py` requires them. `--check` runs the notebook without saving.

## 7. Record the tested revision

```sh
python3 builder/scripts/record_revision.py --label     # e.g. f534f8c-dirty
python3 builder/scripts/record_revision.py             # JSON: git head, dirty flag, code digest
```

The digest covers `src/`, `tests/`, `web/`, `builder/scripts/`, `Master-Reference/`. Documentation is *not* in it; the release manifest hashes the documents separately. A label ending in `-dirty` means uncommitted changes. To name an exact revision for QA, **commit first** (a human author; no AI trailer; run `builder/scripts/install_git_hooks.sh` once after clone), then regenerate the manifest. Any edit to the digested directories changes the digest and makes older evidence refer to an older digest. Never restate old evidence under a new digest.

## 8. Recovery

**A live run failed, was stopped, or the page was closed.**
Live runs exist only in the server's memory. Press **Start stream** again. A failed or stopped run shows partial numbers marked partial and has no export; that is intended. If *Stopping…* does not turn into *Stopped*, wait for the current batch; if the server is unresponsive, restart it (§3). Nothing on disk changes during a live run.

**`package` or `run` was interrupted (Ctrl-C, power loss, disk full).**
Output files are staged to hidden temporary files beside the target (`.NAME.XXXX.tmp`) and renamed into place, entry file (`comparison.json`) last. A failure while staging leaves the previous package whole. After a hard kill, delete leftover `.*.tmp` files, then check the package:

```sh
ls -a web/review-candidate/cases/practice-30d/ web/review-candidate/cases/practice-30d/runs/
PYTHONPATH=src .venv/bin/python -m pytest tests/test_practice_30d.py tests/test_atomic_io.py -q -p no:cacheprovider
```

A rename that fails midway through a multi-file publish is the only case that can mix files from two runs; the tests above (saved package equals engine output) will fail. Fix by re-running `package`.

**A Horizons file fails integrity.** Do not edit it. Restore it from the backup, or re-acquire (§5) into a new folder; the hash in the folder name and the provenance file make a silent swap visible. Never replace a DEM, frame, height reference, or ephemeris silently; record the change in `builder/docs/decision-log.md`.

**Port busy / server will not start.** `ss -ltnp | grep 8766`. Use another port. Do not kill a server you did not start.

**Page shows an old version.** Hard-reload (Ctrl-Shift-R). Static files are served without caching changes but the browser may keep them.

## 9. Reproduce the release (QA)

```sh
python3 builder/scripts/make_release_manifest.py          # write docs/release/manifest.json, MANIFEST.sha256 and the RELEASE.md block
.venv/bin/python builder/scripts/verify_release_package.py   # clone, overlay, verify, run the documented commands
```

`verify_release_package.py` clones the repository into a temporary folder, applies the candidate's uncommitted files, copies `data/horizons` (use `--data-from <folder>` to test a backup), and checks that every file matches `docs/release/manifest.json` and that `record_revision.py` in the copy reports the same label and code digest. It then runs §4 and §6 in the copy, the test suite, the notebook, the guide walk (it runs the User Guide quick-start command as written, on a free port) and the three browser checks, and writes `builder/docs/evidence/s3/release_verify/`. It takes several minutes and does not touch a server on 8766. `--skip-browser` records the browser checks as skipped; a skipped check is not a pass.

The guide walk is an automated stand-in. The human check is `docs/release/TEAMMATE_CHECKLIST.md`.

## 10a. Catalog, gaps, and the expanded real cases

**List what is saved.**

```sh
PYTHONPATH=src python3 -m lunar_navigator.cli catalog            # one line per entry and shared window
PYTHONPATH=src python3 -m lunar_navigator.cli catalog --out /tmp/catalog.json
```

An entry is listed only if its saved files pass the checks (response and CSV SHA-256 against `provenance.json`, target, observer, frame, airless convention, grid). A failing export is reported under `problems`, not offered. Roots searched: `data/` and the labelled synthetic QA fixture `tests/fixtures/qa_horizons`.

**Run a catalog entry, or a sub-range, from the shell.**

```sh
PYTHONPATH=src python3 -m lunar_navigator.cli run --catalog <entry-id> --start 2025-01-03T09:00:00Z --end 2025-01-05T09:30:00Z --out /tmp/run.json
PYTHONPATH=src python3 -m lunar_navigator.cli package --catalog-window <window-id> --out /tmp/pkg
PYTHONPATH=src python3 -m lunar_navigator.cli outcomes --entry <entry-id> --out /tmp/outcomes.json
```

The live page does the same through `GET /api/catalog` and `POST /api/runs` (`catalog`, `start_utc`, `end_utc`, `horizon_mode`) or `POST /api/comparisons` (`catalog_window`, ...). A bad range, an unknown entry or an unknown `horizon_mode` returns HTTP 400 with an `error`.

**Add a saved window.** `lunar_offline_pack.py horizons --site NAME,LON,LAT,ALT_KM --start ... --stop ... --step-min N --contact <email or https URL>` saves one Sun and one Earth table per site through `import_horizons_export`. The `--contact` text goes into JPL's User-Agent; use your own. The expanded real cases were fetched with the repository URL as the contact. An `n.a.` row is a valid gap: it keeps its UTC row with an empty angle and `angle_status=missing`, and the receipt records `missing_row_count` and `missing_timestamps`. A wrong target, a wrong observer, an off-grid or duplicate time, or a malformed number is still refused. The engine also refuses a CSV row marked missing when the raw line has numbers, and the reverse.

**Saved real windows (practice sites, JPL Horizons).** Six-hour scans of Site04 and Malapert, 2025-01-01 to 2025-04-01, and 15-minute re-fetches of three seven-day windows (01-03 to 01-10, 01-20 to 01-27, 03-08 to 03-15). The 15-minute window 01-03 to 01-10 holds all four outcomes. `docs/real-case-trace.md` lists each span and state change with the saved raw rows on both sides, re-read from `response.json` by a separate parser. Regenerate or verify it with:

```sh
.venv/bin/python tests/real_case_trace.py --check
.venv/bin/python tests/real_case_trace.py --write
```

**Browser check of the Unknown path** (own server on its own port; does not touch 8766):

```sh
.venv/bin/python tests/browser_unknown_check.py
```

It runs the synthetic Sun-gap case through the page, compares the page, the downloaded export and the engine batch result, checks the chart band and broken trace, terrain-mode Unknown, a streaming Pending state, and the real windows. Evidence is written under `docs/evidence/unknown/`.

**The release manifest is stale.** The S3 release manifest (`docs/release/manifest.json`, `MANIFEST.sha256`) and the digest recorded under `builder/docs/evidence/s3/` describe the tree before these changes. Regenerate the manifest and re-run the release verification at freeze. Until then the S3 evidence describes the earlier revision only.

## 10. Known limits (operator view)

* Centre-ray only; terrain Unknown; all inputs are practice; `eligible_for_submission_claim` is `false`.
* The raw-file hash of the original 48 h Horizons exports differs from Appendix B of the reference. Matching angle rows do not close this. It stays open until a file-level comparison is done by the team.
* The Malapert practice case uses reference altitude 0 km. The alternative value 4.86425 km has **not** been re-queried; it needs the team's JPL contact and Lead/Science choice.
* Lead decisions L1–L5 and Science decisions S1–S5 in `builder/docs/evidence/s2_scope_decision.md` are **pending**. See `docs/release/RELEASE.md`.
