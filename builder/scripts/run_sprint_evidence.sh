#!/usr/bin/env bash
# Run the full evidence set at one recorded revision and refuse to publish it if the code changed meanwhile.
# Usage: builder/scripts/run_sprint_evidence.sh <tag>      (outputs under builder/docs/evidence/<tag>/)
# Starts its own loopback servers on 8797/8798. It never touches the 8766 review server or web/replay.
set -u
TAG="${1:?usage: run_sprint_evidence.sh <tag>}"
cd "$(dirname "$0")/../.."
OUT="builder/docs/evidence/$TAG"
mkdir -p "$OUT/browser"
PY=".venv/bin/python"; [ -x "$PY" ] || PY=python3
export PYTHONDONTWRITEBYTECODE=1

$PY builder/scripts/record_revision.py > "$OUT/revision_before.json"
LABEL=$($PY builder/scripts/record_revision.py --label)
REPLAY_BEFORE=$(sha256sum web/replay/comparison.json web/replay/runs/*.json | sha256sum | cut -d' ' -f1)

echo "## pytest" | tee "$OUT/commands.txt"
echo "$PY -m pytest tests -q -p no:cacheprovider" >> "$OUT/commands.txt"
$PY -m pytest tests -q -p no:cacheprovider > "$OUT/pytest.log" 2>&1; PYTEST=$?

echo "$PY builder/scripts/live_stream_trace.py --out $OUT/live_trace.json --shots $OUT" >> "$OUT/commands.txt"
$PY builder/scripts/live_stream_trace.py --out "$OUT/live_trace.json" --shots "$OUT" > "$OUT/live_trace.log" 2>&1; TRACE=$?

PYTHONPATH=src $PY -m lunar_navigator.cli --revision "$LABEL" serve --port 8798 >/dev/null 2>&1 &
SP=$!; sleep 1.5
echo "$PY builder/scripts/review_candidate_browser_check.py --base http://127.0.0.1:8798/review-candidate/ --evidence-dir $OUT/browser" >> "$OUT/commands.txt"
$PY builder/scripts/review_candidate_browser_check.py --base http://127.0.0.1:8798/review-candidate/ \
  --evidence-dir "$OUT/browser" --driver-port 9542 --profile "/tmp/lunar-rc-profile-$TAG" > "$OUT/browser/review_candidate_browser.log" 2>&1; BROWSER=$?
kill $SP 2>/dev/null

# Sprint 2 and later: the Why/decision/30-day walkthrough, the independent skyline, and the notebook.
FLOW=skipped; SKY=skipped; NB=skipped
if [ "$TAG" != "s1" ]; then
  PYTHONPATH=src $PY -m lunar_navigator.cli --revision "$LABEL" serve --port 8798 >/dev/null 2>&1 &
  SP2=$!; sleep 1.5
  echo "$PY builder/scripts/s2_flow_check.py --base http://127.0.0.1:8798/review-candidate/ --evidence-dir $OUT/flow" >> "$OUT/commands.txt"
  $PY builder/scripts/s2_flow_check.py --base http://127.0.0.1:8798/review-candidate/ --evidence-dir "$OUT/flow" \
    --driver-port 9544 --profile "/tmp/lunar-s2-profile-$TAG" > "$OUT/flow_check.log" 2>&1; FLOW=$?
  kill $SP2 2>/dev/null
  echo "$PY builder/scripts/s2_independent_skyline.py --out $OUT/terrain_independent_skyline.json" >> "$OUT/commands.txt"
  $PY builder/scripts/s2_independent_skyline.py --out "$OUT/terrain_independent_skyline.json" > "$OUT/skyline.log" 2>&1; SKY=$?
  echo "$PY builder/scripts/run_notebook.py --check docs/notebooks/01_trace_observation_to_interval_total.ipynb" >> "$OUT/commands.txt"
  $PY builder/scripts/run_notebook.py --check docs/notebooks/01_trace_observation_to_interval_total.ipynb > "$OUT/notebook.log" 2>&1; NB=$?
fi

$PY builder/scripts/horizons_digest_check.py --md "$OUT/horizons_digest_provenance.md" --json "$OUT/horizons_digest_provenance.json" > "$OUT/digest.log" 2>&1
$PY builder/scripts/task_counts.py > "$OUT/task_counts.txt" 2>&1; COUNTS=$?
$PY builder/scripts/validate_handoff.py > "$OUT/handoff.txt" 2>&1; HANDOFF=$?
$PY builder/scripts/check_commit_coauthors.py > "$OUT/coauthors.txt" 2>&1

$PY builder/scripts/record_revision.py > "$OUT/revision_after.json"
REPLAY_AFTER=$(sha256sum web/replay/comparison.json web/replay/runs/*.json | sha256sum | cut -d' ' -f1)
SAME=$(python3 - "$OUT" <<'PY'
import json,sys
b=json.load(open(sys.argv[1]+"/revision_before.json")); a=json.load(open(sys.argv[1]+"/revision_after.json"))
print("yes" if b.get("code_digest_sha256")==a.get("code_digest_sha256") and b["head"]==a["head"] else "no")
PY
)
{
  echo "revision=$LABEL"
  echo "code_unchanged_during_run=$SAME"
  echo "witnessed_replay_unchanged=$([ "$REPLAY_BEFORE" = "$REPLAY_AFTER" ] && echo yes || echo no)"
  echo "pytest_exit=$PYTEST ($(tail -1 "$OUT/pytest.log"))"
  echo "live_trace_exit=$TRACE ($(tail -1 "$OUT/live_trace.log"))"
  echo "browser_exit=$BROWSER ($(tail -1 "$OUT/browser/review_candidate_browser.log"))"
  echo "s2_flow_exit=$FLOW ($(tail -1 "$OUT/flow_check.log" 2>/dev/null)) skyline_exit=$SKY notebook_exit=$NB"
  echo "task_counts_exit=$COUNTS handoff_exit=$HANDOFF"
} | tee "$OUT/summary.txt"
[ "$PYTEST" = 0 ] && [ "$TRACE" = 0 ] && [ "$BROWSER" = 0 ] && [ "$SAME" = yes ] \
  && { [ "$FLOW" = skipped ] || [ "$FLOW" = 0 ]; } && { [ "$SKY" = skipped ] || [ "$SKY" = 0 ]; } && { [ "$NB" = skipped ] || [ "$NB" = 0 ]; }
