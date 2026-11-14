# Offline centre-ray replay

Practice package. Submission eligibility is pending. The pages read saved run JSON and do not recompute states.

Regenerate the results from the saved Horizons tables:

```sh
cd /home/m9nx/Lunar-Hackathon
PYTHONPATH=src python3 -m lunar_navigator.cli package --out web/replay
```

Serve the package on loopback:

```sh
python3 -m http.server 8765 --directory web/replay
```

Open `http://127.0.0.1:8765/`. Move the shared playhead. The export links are the same `runs/*.json` files the page loaded.

Labels are Sun-centre clearance, Earth-centre clearance, and Both centres clear. Terrain stays Unknown until M4.
