# Local review candidate

A judge-facing comparison screen for the witnessed geometric replay, plus a local on-demand calculation path. It does not replace `web/replay/`.

NASA chrome (banner, brand header, red accents, stage pipe, starfield) adapted from the educational console at `~/Documents/Learning/lunar-landing-site-navigator`. That repo stays read-only history.

The sky stage is a dual zenith-centred polar map (edu-console style): geometric 0° ring, display-only terrain silhouette textured with `PIA13523`, Unknown hatch, centre-ray Sun/Earth markers, and animated sun waves during stream or when Sun is clear. A compact PIA south-pole map sits in a drawer. Classification stays centre-ray vs geometric 0°. Terrain stays Unknown. No CDN. No Moon Trek globe on the demo path.

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
