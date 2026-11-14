"""The local review candidate keeps the witnessed replay and a synthetic QA fixture."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from review_candidate_cases import build_comparison, build_runs  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "web" / "review-candidate"
REPLAY = ROOT / "web" / "replay" / "comparison.json"


def test_witnessed_replay_package_is_unchanged():
    package = json.loads(REPLAY.read_text())
    assert package["code_revision"] == "1f3fb06"
    assert package["eligible_for_submission_claim"] is False
    assert package["practice"] is True


def test_qa_fixture_matches_the_engine_and_uses_every_state():
    north, south = build_runs()
    saved_north = json.loads((CANDIDATE / "qa-north.json").read_text())
    saved_south = json.loads((CANDIDATE / "qa-south.json").read_text())
    saved_comparison = json.loads((CANDIDATE / "qa-comparison.json").read_text())
    assert saved_north["samples"] == north["samples"]
    assert saved_north["intervals"] == north["intervals"]
    assert saved_north["elapsed_seconds"] == north["elapsed_seconds"]
    assert saved_south["elapsed_seconds"] == south["elapsed_seconds"]
    assert saved_comparison == build_comparison(north, south)
    assert saved_north["samples"][-1]["duration_seconds"] == 0
    assert saved_south["samples"][-1]["duration_seconds"] == 0
    assert saved_comparison["qa_fixture"] is True
    assert saved_comparison["practice"] is False
    assert saved_comparison["eligible_for_submission_claim"] is False
    states = {sample[lane]["state"] for sample in north["samples"] for lane in ("sun", "earth", "both")}
    assert states == {"clear", "blocked", "unknown"}
    assert any(sample["sun"]["reason"] == "missing_right_endpoint" and sample["sun"]["elevation_deg"] == 0.4 for sample in north["samples"])


def test_candidate_page_does_not_fetch_a_cdn():
    script = (CANDIDATE / "app.js").read_text().lower()
    markup = (CANDIDATE / "index.html").read_text().lower()
    assert "cdn" not in script and "cdn" not in markup
    assert "plotly" not in script
    assert "http://" not in script
    assert "https://" not in script and "https://" not in markup
    assert 'id="sky-stage"' in (CANDIDATE / "index.html").read_text()
    assert "sun-wave" in script
    assert "pia13523-south-pole.jpg" in script
    assert (CANDIDATE / "media" / "PIA13523-south-pole.jpg").is_file()
    # No Three.js module on the demo path (polar sky stage only).
    assert "scene.js" not in markup
