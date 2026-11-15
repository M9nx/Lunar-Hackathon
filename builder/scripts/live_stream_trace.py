#!/usr/bin/env python3
"""Sprint 1 exit evidence: two-site run, forced failure, Stop trace, restart, export parity.

Starts its own loopback server on --port (never touches the 8766 review server), drives the
review-candidate UI in headless Chromium, and writes a JSON trace plus screenshots.
Needs chromedriver and /usr/bin/chromium. Inputs are the saved Horizons files; no network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from record_revision import revision_record  # noqa: E402
from review_candidate_browser_check import Driver  # noqa: E402

from lunar_navigator.engine import comparison_document, run_from_scenario  # noqa: E402

SAVED = json.loads((REPO / "web" / "replay" / "comparison.json").read_text())
SITE_A = REPO / "tests/fixtures/site04_p02_practice_scenario.json"
SITE_B = REPO / "tests/fixtures/malapert_practice_scenario.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8797)
    parser.add_argument("--driver-port", type=int, default=9541)
    parser.add_argument("--out", type=Path, default=REPO / "builder/docs/evidence/s1_live_trace.json")
    parser.add_argument("--shots", type=Path, default=REPO / "builder/docs/evidence")
    args = parser.parse_args()

    rev = revision_record()
    env = dict(os.environ, PYTHONPATH=str(REPO / "src"), PYTHONDONTWRITEBYTECODE="1")
    server = subprocess.Popen(
        [sys.executable, "-m", "lunar_navigator.cli", "--revision", rev["label"], "serve", "--port", str(args.port)],
        cwd=REPO, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1.5)
    url = f"http://127.0.0.1:{args.port}/review-candidate/"
    profile = tempfile.mkdtemp(prefix="s1trace-")
    drv = Driver(args.driver_port, 1440, 2200, profile)
    results: list[dict] = []
    trace: dict = {"revision": rev, "url": url, "steps": {}}

    def check(name: str, ok: bool, detail=None) -> None:
        results.append({"check": name, "pass": bool(ok), "detail": detail})
        print(("PASS " if ok else "FAIL ") + name + (" :: " + str(detail)[:200] if not ok else ""))

    def status() -> str:
        return drv.js("return document.getElementById('run-status').textContent")

    def load() -> None:
        drv.get(url)
        drv.wait("return document.querySelectorAll('.sky-panel').length >= 1")

    def speed(value: int) -> None:
        drv.js(
            "const s=document.getElementById('playback-speed');s.value=arguments[0];"
            "s.dispatchEvent(new Event('input',{bubbles:true}))",
            value,
        )

    SNAP_JS = """
            const t = (id) => (document.getElementById(id) || {}).textContent || '';
            const a = document.querySelector('#live-export a');
            return {status: t('run-status'), answers: t('answers'), banner: t('banner'),
                    chip: t('live-chip'), exportText: t('live-export'), exportHref: a ? a.href : null,
                    start: document.getElementById('start-run').disabled,
                    stop: document.getElementById('cancel-run').disabled,
                    stopLabel: document.getElementById('cancel-run').textContent,
                    progress: t('site-progress'), through: t('results-through')};"""

    def snapshot() -> dict:
        return drv.js(SNAP_JS)

    def watch_stopping() -> None:
        """Record the first complete page state in which the status says Stopping.

        Polling can miss a window that lasts a fraction of a second. A MutationObserver reads the page in the
        microtask after the DOM change, so every synchronous update from that Stop click has been applied.
        """
        drv.js(
            "window.__snap = () => {" + SNAP_JS + "};"
            " window.__stopSeen = null;"
            " new MutationObserver(() => {"
            "   if (!window.__stopSeen && /^Stopping/.test((document.getElementById('run-status') || {}).textContent || '')) window.__stopSeen = window.__snap();"
            " }).observe(document.body, {subtree: true, childList: true, characterData: true, attributes: true});"
        )

    def fetch_export() -> dict:
        return drv.js(
            "const a=document.querySelector('#live-export a');const x=new XMLHttpRequest();"
            "x.open('GET',a.href,false);x.send();return JSON.parse(x.responseText);"
        )

    try:
        # --- batch parity reference (engine, no UI) ---
        data = REPO / "data"
        batch_a = run_from_scenario(json.loads(SITE_A.read_text()), data, rev["label"])
        batch_b = run_from_scenario(json.loads(SITE_B.read_text()), data, rev["label"])
        batch_doc = comparison_document(batch_a, batch_b, rev["label"])
        ov = batch_doc["overlap"]
        trace["batch_reference"] = {
            "run_id_a": batch_a["run_id"], "run_id_b": batch_b["run_id"],
            "sun_clear_s": [ov["sun_centre_clear_seconds"]["site_a"], ov["sun_centre_clear_seconds"]["site_b"]],
            "both_clear_s": [ov["both_centres_clear_seconds"]["site_a"], ov["both_centres_clear_seconds"]["site_b"]],
        }
        check("batch reference: Sun-centre clear 48 h vs 0 h, both clear 0 h at either site",
              trace["batch_reference"]["sun_clear_s"] == [172800, 0] and trace["batch_reference"]["both_clear_s"] == [0, 0],
              trace["batch_reference"])
        check("batch overlap equals the witnessed replay overlap", ov == SAVED["overlap"])

        # --- A: complete two-site run ---
        load()
        speed(100)
        drv.js("document.getElementById('start-run').click()")
        first = drv.wait("return /shared \\d+/.test(document.getElementById('run-status').textContent)", 30)
        mid = snapshot()
        check("first results arrive before completion", "Calculating" in mid["status"] and mid["exportHref"] is None, mid["status"])
        drv.wait("return /^Complete/.test(document.getElementById('run-status').textContent)", 90)
        done = snapshot()
        exp = fetch_export()
        trace["steps"]["complete"] = {"status": done["status"], "export_keys": sorted(exp.keys())}
        check("complete run offers the export", done["exportHref"] is not None and "Download complete export" in done["exportText"])
        check("screen headline shows 48 h and 0 h", "48 h" in done["answers"] and "0 h" in done["answers"], done["answers"][:200])
        check("screen details equal the export seconds",
              drv.js("return document.querySelector('.result-details') ? document.querySelector('.result-details').textContent : ''").count("172800 s") >= 1)
        check("export overlap equals batch and saved overlap", exp["overlap"] == ov == SAVED["overlap"])
        check("export is the complete comparison (not partial)", exp.get("comparable") is True and not exp.get("partial"))
        run_ids_ui = sorted(r["run_id"] for r in exp["runs"])
        check("export run ids equal batch run ids", run_ids_ui == sorted([batch_a["run_id"], batch_b["run_id"]]), run_ids_ui)
        trace["steps"]["complete"]["export_sha256"] = hashlib.sha256(json.dumps(exp, sort_keys=True).encode()).hexdigest()
        drv.shot(args.shots / "s1_complete.png")

        # --- B1: forced failure before any shared sample (UI toggle: A fails after batch 1) ---
        load()
        speed(100)
        drv.js("document.getElementById('fail-test').checked = true")
        drv.js("document.getElementById('start-run').click()")
        drv.wait("return /^Failed/.test(document.getElementById('run-status').textContent)", 30)
        f0 = snapshot()
        trace["steps"]["failed_before_shared"] = f0
        check("failure before a shared sample says so, with per-site delivery",
              "before any shared sample" in f0["answers"] and "delivered 3" in f0["answers"] and "delivered 0" in f0["answers"], f0["answers"][:240])
        check("failure shows no waiting line", "Waiting for the first shared sample" not in f0["answers"], f0["answers"][:200])
        check("failure offers no export and says why", f0["exportHref"] is None and "No export" in f0["exportText"], f0["exportText"])
        check("failure re-enables Start and disables Stop", f0["start"] is False and f0["stop"] is True)
        drv.shot(args.shots / "s1_failed_no_shared.png")

        # --- B2: forced failure with shared samples (A fails after its second batch) ---
        load()
        speed(100)
        drv.js(
            "const f=window.fetch.bind(window);window.fetch=(u,o)=>{if(String(u).endsWith('/api/comparisons')&&o&&o.method==='POST'){"
            "const b=JSON.parse(o.body);b.fail_after_batches_a=2;o={...o,body:JSON.stringify(b)};}return f(u,o);};"
        )
        drv.js("document.getElementById('start-run').click()")
        drv.wait("return /^Failed/.test(document.getElementById('run-status').textContent)", 30)
        f1 = snapshot()
        trace["steps"]["failed_with_shared"] = f1
        check("failure with shared samples shows the partial result and cutoff",
              "Final cutoff 2025-01-01T00:45:00Z" in f1["status"] and "4 of 193 shared samples" in f1["status"]
              and "Partial result through" in f1["answers"] and "2025-01-01T00:45:00Z" in f1["answers"], (f1["status"], f1["answers"][:300]))
        check("failure with shared samples says covered-through and not exportable",
              "cover through 2025-01-01T01:00:00Z" in f1["status"].replace("Totals cover through", "cover through") and "Not exportable" in f1["answers"], f1["status"])
        check("failed run is not labelled complete", "Complete" not in f1["status"] and f1["exportHref"] is None and f1["chip"] == "Live failed", f1["chip"])
        drv.shot(args.shots / "s1_failed_shared.png")

        # --- C: Stop at the default speed ---
        load()
        drv.js("document.getElementById('start-run').click()")
        drv.wait("return /shared (\\d+)/.test(document.getElementById('run-status').textContent) && Number(/shared (\\d+)/.exec(document.getElementById('run-status').textContent)[1]) >= 18", 60)
        before = snapshot()
        shared_at_click = int(re.search(r"shared (\d+)", before["status"]).group(1))
        watch_stopping()
        drv.js("document.getElementById('cancel-run').click()")
        timeline = []
        t0 = time.time()
        stopping_seen = None
        while time.time() - t0 < 20:
            snap = snapshot()
            timeline.append({"t": round(time.time() - t0, 2), "chip": snap["chip"], "stop": snap["stopLabel"], "status": snap["status"][:90]})
            if stopping_seen is None and snap["status"].startswith("Stopping"):
                stopping_seen = snap
            if stopping_seen is None:
                stopping_seen = drv.js("return window.__stopSeen")
            if snap["status"].startswith("Stopped"):
                break
            time.sleep(0.05)
        final = snapshot()
        trace["steps"]["stop"] = {"shared_at_click": shared_at_click, "timeline": timeline[:60], "final": final}
        check("Stop shows Stopping with a disabled Stop button until the engine reports", stopping_seen is not None
              and stopping_seen["stopLabel"] == "Stopping…" and stopping_seen["stop"] is True and stopping_seen["chip"] == "Stopping",
              stopping_seen)
        check("Stopping headline says totals are not final", stopping_seen is not None and "not final" in stopping_seen["answers"], (stopping_seen or {}).get("answers", "")[:200])
        cut = re.search(r"Final cutoff (\S+) \((\d+) of 193 shared samples\)", final["status"])
        check("Stopped status reports the final cutoff and shared count", cut is not None, final["status"])
        if cut:
            check("final cutoff is at or after the shared count seen at the click", int(cut.group(2)) >= shared_at_click, (cut.group(2), shared_at_click))
            check("screen headline shows the same cutoff", cut.group(1) in final["answers"], final["answers"][:260])
            delivered = [int(n) for n in re.findall(r": (\d+) of 193", final["progress"])]
            check("progress strip shows per-site delivery at or above the shared count",
                  len(delivered) == 2 and min(delivered) == int(cut.group(2)), (delivered, cut.group(2)))
            check("through line agrees with the cutoff", cut.group(1) in final["through"], final["through"])
        check("stopped run offers no export", final["exportHref"] is None and "No export" in final["exportText"], final["exportText"])
        check("Stop ended with Start enabled and chip Live stopped", final["start"] is False and final["chip"] == "Live stopped", (final["start"], final["chip"]))
        drv.shot(args.shots / "s1_stopped.png")

        # --- D: restart after cancel completes and exports ---
        speed(100)
        drv.js("document.getElementById('start-run').click()")
        drv.wait("return /^Complete/.test(document.getElementById('run-status').textContent)", 90)
        again = snapshot()
        exp2 = fetch_export()
        check("restart after Stop completes, drops the stopped label and offers the export",
              again["chip"] == "Live complete" and "Stopped" not in again["answers"] and again["exportHref"] is not None, again["chip"])
        check("restart export overlap equals the saved overlap", exp2["overlap"] == SAVED["overlap"])
        old_id = re.search(r"Comparison (\w+)", final["status"]).group(1)
        new_id = re.search(r"Comparison (\w+)", again["status"]).group(1)
        check("restart is a new comparison id", old_id != new_id, (old_id, new_id))
        trace["steps"]["restart"] = {"status": again["status"]}
    finally:
        trace["results"] = results
        args.out.write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")
        drv.close()
        server.send_signal(signal.SIGTERM)
    failed = [r for r in results if not r["pass"]]
    print(f"{len(results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
