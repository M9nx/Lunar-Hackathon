# Local review candidate

A judge-facing comparison screen for the witnessed geometric replay, plus a local on-demand calculation path. It does not replace `web/replay/`.

NASA chrome (banner, brand header, red accents, stage pipe, starfield) and the south-pole context panel are adapted from the educational console at `~/Documents/Learning/lunar-landing-site-navigator`. That repo stays read-only history. No CDN fonts or Three.js: the context image is vendored `PIA13523`. The page is full-width with a sticky action rail. `#scene-stage` / `#scene-3d` are the interaction surface for site select, scrub, and future streamed 3D once Three.js is vendored offline.

## Replay only

Serve the `web` directory so this page and the saved runs share one origin:

```sh
python3 -m http.server 8766 --directory web
```

Open `http://127.0.0.1:8766/review-candidate/`.

## Local calculation and streaming

Acquisition stays a separate step (`lunar_offline_pack.py horizons ...`). This path only classifies saved Horizons files.

```sh
PYTHONPATH=src python3 -m lunar_navigator.cli --revision test serve --port 8766
```

Open `http://127.0.0.1:8766/review-candidate/`. Use Start and Cancel. The page posts to `/api/runs` and reads NDJSON from `/api/runs/<run_id>/events`.

Batch and stream from the terminal:

```sh
PYTHONPATH=src python3 -m lunar_navigator.cli --revision test run \
  --scenario tests/fixtures/site04_p02_practice_scenario.json \
  --out /tmp/site04-batch.json

PYTHONPATH=src python3 -m lunar_navigator.cli --revision test stream \
  --scenario tests/fixtures/site04_p02_practice_6h_scenario.json \
  --batch-size 2
```

The practice view reads `../replay/comparison.json` and the two run files. The QA fixture button loads synthetic transitions in this directory. Terrain stays Unknown. No skyline is drawn.

The witnessed package remains `code_revision` `1f3fb06` with `eligible_for_submission_claim` false.
