#!/usr/bin/env python3
"""Follow the User Guide quick start literally and check each outcome the guide states.

This is an automated stand-in for "a teammate launches and uses the package from the guide alone".
It does NOT replace the human run listed in docs/release/TEAMMATE_CHECKLIST.md.

What it does, from the repository it lives in (the verifier runs it inside a copy of the candidate):
1. Reads docs/user-guide.md, takes the first ```sh block under "Two-minute quick start", and runs it
   unchanged except that --port 8766 is replaced by a free port (8766 may be in use; never stopped here).
2. Opens the page it served and walks quick-start steps 3 to 6 with the control names from the guide.
3. Writes screenshots and a JSON record of every check.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("rcbc", REPO / "builder/scripts/review_candidate_browser_check.py")
rcbc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rcbc)


def quick_start_command(guide: Path) -> str:
    text = guide.read_text()
    section = text.split("## Two-minute quick start", 1)[1]
    match = re.search(r"[ \t]*```sh\n(.*?)\n[ \t]*```", section, re.S)
    if not match:
        raise SystemExit("no sh block under Two-minute quick start")
    return "\n".join(line.strip() for line in match.group(1).splitlines()).strip()


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--driver-port", type=int, default=9551)
    parser.add_argument("--profile", default="/tmp/lunar-s3-walk-profile")
    parser.add_argument("--guide", default=str(REPO / "docs/user-guide.md"))
    parser.add_argument("--python", default=None, help="interpreter used by the Driver (default: this one)")
    args = parser.parse_args()
    evidence = Path(args.evidence_dir)
    evidence.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    def check(name: str, ok: bool, detail=None) -> None:
        results.append({"check": name, "pass": bool(ok), "detail": detail})
        print(("PASS " if ok else "FAIL ") + name + (f" :: {detail}" if detail not in (None, "") else ""), flush=True)

    command = quick_start_command(Path(args.guide))
    port = free_port()
    if "--port 8766" not in command:
        check("guide command has --port 8766", False, command)
        return 1
    run_command = command.replace("--port 8766", f"--port {port}")
    (evidence / "guide_command.txt").write_text(
        "from the guide:\n" + command + "\n\nrun (only deviation: a free port instead of 8766):\n" + run_command + "\n"
    )
    server = subprocess.Popen(
        ["bash", "-c", run_command],
        cwd=REPO,
        start_new_session=True,
        stdout=(evidence / "server.log").open("w"),
        stderr=subprocess.STDOUT,
    )
    base = f"http://127.0.0.1:{port}/review-candidate/"
    drv = None
    try:
        up = False
        for _ in range(80):
            try:
                if urllib.request.urlopen(base, timeout=1).status == 200:
                    up = True
                    break
            except Exception:
                time.sleep(0.25)
        check("quick start step 1-2: the guide's command serves the page", up, base)
        if not up:
            return 1

        drv = rcbc.Driver(args.driver_port, 1440, 2400, args.profile)

        def click(selector: str) -> None:
            drv.js("document.querySelector(arguments[0]).click()", selector)

        def norm(selector: str) -> str:
            return drv.js(
                "const n = document.querySelector(arguments[0]); return n ? n.textContent.replace(/\\s+/g, ' ').trim() : ''",
                selector,
            )

        def set_select(selector: str, value: str) -> None:
            drv.js(
                "const e = document.querySelector(arguments[0]); e.value = arguments[1]; e.dispatchEvent(new Event('change', {bubbles: true}))",
                selector,
                value,
            )

        drv.get(base)
        drv.wait("return document.querySelectorAll('.sky-panel').length === 2", timeout=40)
        time.sleep(0.5)

        # Step 3: the headline.
        head = norm("#answers")
        (evidence / "step3_headline.txt").write_text(head + "\n")
        check(
            "step 3: headline gives Site04 48 h Sun-centre, Malapert 0 h, both centres 0 h",
            "48 h" in head and "Site04" in head and "Malapert" in head and "0 h" in head,
            head[:240],
        )
        drv.shot(evidence / "step3_headline.png")

        # Step 4: Why Malapert 0 h?
        click('.why-q[data-why="sun:1"]')
        time.sleep(0.2)
        label = drv.js("return document.querySelector('.why-q[data-why=\"sun:1\"]').textContent.trim()")
        body = norm("#why-body")
        scope = norm("#why-result .why-scope")
        (evidence / "step4_why_malapert.txt").write_text(body + "\n")
        check("step 4: button reads 'Why Malapert 0 h?'", label == "Why Malapert 0 h?", label)
        check(
            "step 4: panel gives the rule, 193 samples, nearest sample margin -1.603613 and a source-row table",
            "193 samples" in body and "\u22121.603613" in body and "Source row" in body and "2025-01-03T00:00Z" in body,
            body[:300],
        )

        check("step 4: UTC range and mode are shown with the answer", "UTC range" in scope and "01-01" in scope and "01-03" in scope, scope[:200])

        # Step 5: decision panel, Sun, 4 h.
        set_select("#dec-lane", "sun")
        set_select("#dec-min", "4")
        time.sleep(0.2)
        sites = drv.js("return Array.from(document.querySelectorAll('#dec-answer .dec-site')).map(n => n.textContent.replace(/\\s+/g, ' ').trim())")
        closest = drv.js("return document.querySelectorAll('#dec-answer .win-closest').length")
        verdict = norm("#dec-answer")
        (evidence / "step5_decision.txt").write_text(json.dumps({"verdict": verdict, "sites": sites}, indent=2) + "\n")
        check(
            "step 5: Site04 has one window, Malapert none with a closest-sample button",
            len(sites) == 2 and "1 window" in sites[0] and "No clear window" in sites[1] and closest == 1,
            {"sites": [s[:120] for s in sites], "closest_buttons": closest},
        )
        drv.shot(evidence / "step5_decision.png")

        # Step 6: 30-day case, both sites have windows; clicking a window selects it.
        click("#show-practice30")
        drv.wait("return state.runs && state.runs.length === 2 && state.runs[0].payload.scenario.end_utc.startsWith('2025-01-31')", timeout=30)
        set_select("#dec-lane", "sun")
        set_select("#dec-min", "0")
        time.sleep(0.3)
        sites30 = drv.js("return Array.from(document.querySelectorAll('#dec-answer .dec-site')).map(n => n.textContent.replace(/\\s+/g, ' ').trim())")
        opens = drv.js("return document.querySelectorAll('#decision .win-open').length")
        check(
            "step 6: with 30 days, both sites list Sun-centre windows",
            len(sites30) == 2 and all("window" in s and "No clear window" not in s for s in sites30) and opens >= 2,
            {"sites": [s[:120] for s in sites30], "buttons": opens},
        )
        click("#decision .win-open")
        time.sleep(0.3)
        selected = drv.js("return document.querySelectorAll('#decision .win-open.is-selected, #windows .win-open.is-selected').length")
        check("step 6: clicking a window selects it", selected >= 1, selected)
        drv.shot(evidence / "step6_30d.png")
    finally:
        if drv is not None:
            drv.close()
        try:
            os.killpg(server.pid, signal.SIGTERM)
            server.wait(timeout=5)
        except Exception:
            try:
                os.killpg(server.pid, signal.SIGKILL)
            except Exception:
                pass

    passed = sum(1 for item in results if item["pass"])
    (evidence / "guide_walk.json").write_text(
        json.dumps({"passed": passed, "total": len(results), "checks": results}, indent=2) + "\n"
    )
    print(f"{passed}/{len(results)} guide-walk checks passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
