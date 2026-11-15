#!/usr/bin/env python3
"""Headless-browser walkthrough of web/review-candidate against a running local server.

Needs: chromedriver + chromium on PATH, and `lunar_navigator.cli serve` on --base.
No Selenium: talks W3C WebDriver over HTTP. Writes screenshots and a JSON result.

Flow under test: choose the case -> read the result -> select a window -> inspect why.
"""
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EVIDENCE = REPO / "builder" / "docs" / "evidence"


class Driver:
    def __init__(self, port: int, width: int, height: int, profile: str) -> None:
        self.proc = subprocess.Popen(
            ["chromedriver", f"--port={port}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        self.base = f"http://127.0.0.1:{port}"
        for _ in range(50):
            try:
                self._req("GET", "/status")
                break
            except Exception:
                time.sleep(0.1)
        caps = {
            "capabilities": {
                "alwaysMatch": {
                    "browserName": "chrome",
                    "goog:chromeOptions": {
                        "binary": "/usr/bin/chromium",
                        "args": [
                            "--headless=new",
                            "--no-sandbox",
                            "--disable-gpu",
                            f"--user-data-dir={profile}",
                            f"--window-size={width},{height}",
                        ],
                    },
                }
            }
        }
        self.sid = self._req("POST", "/session", caps)["value"]["sessionId"]
        self.size(width, height)

    def _req(self, method: str, path: str, body: dict | None = None):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.base + path, data=data, method=method)
        request.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read())

    def _s(self, method: str, path: str, body: dict | None = None):
        return self._req(method, f"/session/{self.sid}{path}", body)["value"]

    def get(self, url: str) -> None:
        self._s("POST", "/url", {"url": url})

    def js(self, script: str, *args):
        return self._s("POST", "/execute/sync", {"script": script, "args": list(args)})

    def size(self, width: int, height: int) -> None:
        self._s("POST", "/window/rect", {"width": width, "height": height})

    def shot(self, path: Path) -> None:
        path.write_bytes(base64.b64decode(self._s("GET", "/screenshot")))

    def wait(self, script: str, timeout: float = 30.0, step: float = 0.15):
        end = time.time() + timeout
        value = None
        while time.time() < end:
            value = self.js(script)
            if value:
                return value
            time.sleep(step)
        raise TimeoutError(script)

    def close(self) -> None:
        try:
            self._req("DELETE", f"/session/{self.sid}")
        finally:
            self.proc.terminate()


def main() -> int:
    global EVIDENCE
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8766/review-candidate/")
    parser.add_argument("--out", default=None, help="Result JSON (default: <evidence-dir>/review_candidate_browser.json)")
    parser.add_argument("--evidence-dir", default=str(EVIDENCE), help="Where screenshots and the result JSON are written")
    parser.add_argument("--driver-port", type=int, default=9517)
    parser.add_argument("--profile", default="/tmp/lunar-rc-profile")
    args = parser.parse_args()
    EVIDENCE = Path(args.evidence_dir)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    out_path = Path(args.out) if args.out else EVIDENCE / "review_candidate_browser.json"
    results: list[dict] = []

    def check(name: str, ok: bool, detail=None) -> None:
        results.append({"check": name, "pass": bool(ok), "detail": detail})
        print(("PASS " if ok else "FAIL ") + name + (f" :: {detail}" if detail not in (None, "") else ""))

    drv = Driver(args.driver_port, 1440, 2400, args.profile)

    def click(selector: str) -> None:
        drv.js("document.querySelector(arguments[0]).click()", selector)

    def tool(key: str, value: str) -> None:
        click(f'.tool[data-key="{key}"][data-value="{value}"]')

    def norm(selector: str) -> str:
        """textContent with collapsed whitespace, so hidden Details content is also readable."""
        return drv.js(
            "const n = document.querySelector(arguments[0]); return n ? n.textContent.replace(/\\s+/g, ' ').trim() : null", selector
        )

    def count(selector: str) -> int:
        return drv.js("return document.querySelectorAll(arguments[0]).length", selector)

    def pick_lane(lane: str) -> None:
        tool("lane", lane)

    try:
        drv.get(args.base)
        drv.wait("return document.querySelectorAll('.sky-panel').length === 2")

        practice_sun = json.loads((REPO / "web/replay/runs/site04-p02-practice.json").read_text())
        malapert = json.loads((REPO / "web/replay/runs/malapert-practice.json").read_text())

        # ===== 1. Clear first screen =====
        drv.js("move(52)")
        bar = norm("#scenario-bar")
        check(
            "scenario bar: two sites, UTC range, sample step, Geometric 0°",
            all(t in bar for t in ("Site04", "Malapert", "2025-01-01T00:00Z", "2025-01-03T00:00Z", "48 h", "15 min", "Geometric 0°")),
            bar,
        )
        check("scenario bar is one compact row", drv.js("return document.getElementById('scenario-bar').getBoundingClientRect().height") < 120)
        cards = drv.js(
            "return Array.from(document.querySelectorAll('#answers .site-num')).map(c => [c.querySelector('.sn-name').textContent.replace(/\\s+/g, ' ').trim(), c.querySelector('.sn-val').textContent.trim()])"
        )
        check(
            "Sun-centre headline: Site04 48 h and Malapert 0 h, equal footing",
            cards == [["A Site04", "48 h"], ["B Malapert", "0 h"]] and norm("#answers .result-title") == "Sun-centre clearance",
            cards,
        )
        size = drv.js("return Array.from(document.querySelectorAll('#answers .sn-val')).map(n => getComputedStyle(n).fontSize + '/' + Math.round(n.getBoundingClientRect().width))")
        check("both site numbers share one size and width", len(set(size)) == 1, size)
        check("joint line: Both centres clear · 0 h at either site", norm("#answers .result-joint") == "Both centres clear · 0 h at either site", norm("#answers .result-joint"))
        head = norm("#answers")
        check("Practice and Terrain clearance unknown visible on the first screen", "Practice" in head and "Terrain clearance unknown" in head)
        check("header also keeps Practice and Terrain clearance unknown", "Practice" in norm("header") and "Terrain clearance unknown" in norm("header"))
        first = drv.js("return Array.from(document.getElementById('answers').querySelectorAll('.result-title, .sn-val, .result-joint, .result-tags')).every(n => n.getBoundingClientRect().bottom < 1000)")
        check("first screen holds result and joint line without scrolling", first)
        raw = drv.js("return document.getElementById('answers').innerText")
        check("first screen has no raw seconds, sample counts or reason codes", all(t not in raw for t in ("172800", " s ", "terrain_not_reviewed", "samples")), raw[:200])
        details = norm("#answers-details")
        check(
            "Details hold raw seconds, sample counts and terrain_not_reviewed",
            all(t in details for t in ("172800 s", "0 s", "terrain_not_reviewed", "Samples", "193")) and not drv.js("return document.querySelector('#answers-details details').open"),
            details[:300],
        )
        check("zero shows as 0 h, never 0 s", "0 h" in head and " 0 s" not in head and "0 min" not in head)
        drv.shot(EVIDENCE / "review_candidate_stage_desktop.png")

        # ===== 2. Timeline and window list work together =====
        check("lane picker sits above the timeline", drv.js("return document.getElementById('lane-tools').getBoundingClientRect().bottom <= document.getElementById('chart').getBoundingClientRect().top"))
        labels = drv.js("return Array.from(document.querySelectorAll('#chart .ch-label')).map(n => n.textContent)")
        check("Sun chart: two site traces with direct A/B labels", count("#chart .ch-trace") == 2 and labels == ["A Site04", "B Malapert"], labels)
        check("0° reference is labelled", "0° horizon" in norm("#chart") and count("#chart .ch-zero") == 1)
        check("selected-time marker is a separate pink line with a time pill", count("#chart .ch-play") == 1 and norm("#chart .ch-pill-text") == "13:00Z", norm("#chart .ch-pill-text"))
        marker = drv.js("return [getComputedStyle(document.querySelector('.ch-play')).stroke, getComputedStyle(document.querySelector('.ch-zero')).stroke, getComputedStyle(document.querySelector('.ch-zero')).strokeDasharray, getComputedStyle(document.querySelector('.ch-play')).strokeDasharray]")
        check("selected-time marker differs from the 0° horizon", marker[0] != marker[1] and marker[2] != "none" and marker[3] == "none", marker)
        ticks = drv.js("return Array.from(document.querySelectorAll('#chart .ch-axis')).map(n => n.textContent).filter(t => /Z$|^\\d\\d-\\d\\d$/.test(t))")
        check("short UTC ticks", ticks and all(len(t) <= 6 for t in ticks) and "01-02" in ticks, ticks)
        bg = drv.js("const r = document.querySelector('.ch-bg'); const a = getComputedStyle(r).fill.match(/\\d+/g).map(Number); const t = getComputedStyle(document.querySelector('.ch-axis')).fill.match(/\\d+/g).map(Number); return [a, t]")
        lum = lambda c: 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
        check("dark plot with bright axis labels", lum(bg[0]) < 30 and lum(bg[1]) > 170, bg)

        ro = norm("#readout")
        check("readout shows selected UTC, each site state and signed margin", "2025-01-01T13:00:00Z" in ro and "Clear" in ro and "+1.661532°" in ro and "Blocked" in ro and "−2.216453°" in ro, ro)

        # Windows rail: one selection updates chart, lanes and list.
        wins = norm("#windows")
        check("Windows rail: Site04 clear window, Malapert none", "01-01 00:00Z → 01-03 00:00Z" in wins and "No clear window in this range." in wins, wins[:260])
        check("Windows rail is compact beside the chart", drv.js("const r = document.getElementById('windows').closest('.windows-rail').getBoundingClientRect(), c = document.getElementById('explore-main').getBoundingClientRect(); return r.width < 400 && c.width > 2.2 * r.width && r.left >= c.right - 1"))
        drv.js("move(5)")
        click("#windows .win-open")
        s1 = drv.js(
            "return {sel: state.sel, site: state.site, index: state.index, utc: document.getElementById('utc').textContent,"
            " chartBand: document.querySelectorAll('#chart .ch-sel').length, seg: document.querySelectorAll('#lanes .seg.is-selected').length,"
            " row: document.querySelectorAll('#windows .win-open.is-selected').length, ro: document.getElementById('readout').querySelector('.ro-sel').textContent}"
        )
        check(
            "click a window: highlight span, select site, playhead to start",
            s1["sel"]["site"] == 0 and s1["index"] == 0 and s1["utc"] == "2025-01-01T00:00:00Z" and s1["chartBand"] == 1 and s1["seg"] == 1 and s1["row"] == 1,
            s1,
        )
        check("selected window line names site, state, span", all(t in s1["ro"] for t in ("Site04", "clear", "48 h")), s1["ro"])
        pick_lane("earth")
        check("changing the lane clears the window selection and updates chart, lanes and list", drv.js("return state.sel") is None and "Earth" in norm("#windows") and count("#chart .ch-sel") == 0 and "Earth" in norm("#lanes"), norm("#windows")[:120])
        el = norm("#windows")
        check("Earth lane: no clear window at either site", el.count("No clear window in this range.") == 2, el[:200])
        check("Earth lane offers Closest sampled point to 0° per site", count("#windows .win-closest") == 2)
        pick_lane("sun")

        # Both lane
        drv.js("state.site = 0; move(52)")
        pick_lane("both")
        both_labels = drv.js("return Array.from(document.querySelectorAll('#chart .ch-label')).map(n => n.textContent)")
        check("Both: joint lanes for each site", count("#lanes .lane-site") == 2 and "Both" in norm("#lanes"), norm("#lanes")[:120])
        # The Both-lane readout shows each centre's margin; the separate margins table was removed as a duplicate.
        mg = norm("#readout")
        check(
            "Both: individual Sun and Earth centre margins at the selected time",
            all(t in mg for t in ("+1.661532°", "−2.216453°")) and "Sun" in mg and "Earth" in mg,
            mg[:280],
        )
        check("Both: chart carries Sun and Earth traces per site", count("#chart .ch-trace") == 4 and len(both_labels) == 4, both_labels)
        check("Both: no Closest offer", count("#windows .win-closest") == 0 and "No clear window in this range." in norm("#windows"))
        drv.shot(EVIDENCE / "review_candidate_stage_both.png")
        pick_lane("sun")

        # Closest sampled point to 0°: Malapert Sun is always blocked; the closest sample is the final one.
        closest = min(
            enumerate(malapert["samples"]), key=lambda item: abs(item[1]["sun"]["margin_deg"])
        )
        click('#windows .win-closest[data-site="1"]')
        s2 = drv.js(
            "return {site: state.site, index: state.index, utc: document.getElementById('utc').textContent,"
            " notice: (document.querySelector('.ro-notice')||{}).textContent, zero: document.getElementById('zero-note').textContent,"
            " last: sharedSampleCount() - 1}"
        )
        check("Closest sampled point to 0° jumps to the saved sample", s2["site"] == 1 and s2["utc"] == closest[1]["timestamp_utc"], {"ui": s2["utc"], "saved": closest[1]["timestamp_utc"], "margin": closest[1]["sun"]["margin_deg"]})
        check(
            "final sample says it adds 0 elapsed time",
            closest[0] == s2["last"] and s2["index"] == s2["last"] and "adds 0 elapsed time" in (s2["notice"] or "") and "adds 0 elapsed time" in s2["zero"],
            s2,
        )

        # Inspect why: trace the selected state to its Horizons row.
        click("#open-evidence")
        ev = drv.js("const p = document.getElementById('preview'); return {hidden: p.hidden, text: p.innerText, line: (p.querySelector('dl.evidence code:nth-of-type(1)')||{}).textContent, all: Array.from(p.querySelectorAll('code')).map(c => c.textContent)}")
        saved_row = malapert["samples"][closest[0]]["sun"]["response_line"]
        check("View evidence opens the Horizons row for the selected state", not ev["hidden"] and saved_row in ev["all"], {"row": saved_row, "shown": ev["all"][:2]})
        check("evidence shows run ID, observer, source and export", all(t in ev["text"].lower() for t in ("run id", "observer", "source", "json")), ev["text"][:200])
        drv.shot(EVIDENCE / "review_candidate_stage_preview.png")
        drv.js("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}))")
        check("Esc closes evidence", drv.js("return document.getElementById('preview').hidden"))
        drv.js("move(52)")
        check("Evidence is not on the main flow until opened", drv.js("return document.getElementById('preview').hidden"))

        # ===== 4. Screening control: minimum clear-window length =====
        from datetime import datetime

        def utc_ms(text: str) -> float:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp() * 1000

        def clear_hours(payload: dict, lane: str) -> list[float]:
            spans: list[list] = []
            for item in payload["intervals"]:
                if item["lane"] != lane:
                    continue
                if spans and spans[-1][2] == item["state"] and spans[-1][1] == item["start_utc"]:
                    spans[-1][1] = item["end_utc"]
                else:
                    spans.append([item["start_utc"], item["end_utc"], item["state"]])
            return [(utc_ms(s[1]) - utc_ms(s[0])) / 3_600_000 for s in spans if s[2] == "clear"]

        def set_min(value: str) -> None:
            drv.js(
                "const s = document.getElementById('min-duration'); s.value = arguments[0]; s.dispatchEvent(new Event('change', {bubbles: true}))",
                value,
            )

        drv.js("state.site = 0; move(52)")
        check("filter defaults to any length", drv.js("return document.getElementById('min-duration').value") == "0" and not count("#windows .filter-summary"))
        base_totals = norm("#answers .result-pair")
        set_min("4")
        pick_lane("sun")
        expect = {
            "sun": [len([h for h in clear_hours(p, "sun") if h >= 4]) for p in (practice_sun, malapert)],
            "both": [len([h for h in clear_hours(p, "both") if h >= 4]) for p in (practice_sun, malapert)],
        }
        summary = norm("#windows .filter-summary")
        check("4 h Sun filter finds a Site04 window and none at Malapert", expect["sun"] == [1, 0] and "Site04 1 window" in summary and "Malapert none" in summary, {"engine": expect["sun"], "ui": summary})
        listed = drv.js("return Array.from(document.querySelectorAll('#windows .win-site')).map(s => s.querySelectorAll('.win-open').length)")
        check("qualifying windows listed per site, from engine intervals", listed == expect["sun"], listed)
        site_card = norm("#windows .win-site")
        check("full-window totals stay visible beside the filtered list", "Clear 48 h" in site_card and "Blocked 0 h" in site_card and "01-01 00:00Z → 01-03 00:00Z" in site_card, site_card)
        check("headline totals unchanged by the filter", norm("#answers .result-pair") == base_totals and norm("#answers .result-joint") == "Both centres clear · 0 h at either site")
        check("lane header shows the qualifying count", "1 window of 4 h or longer" in norm("#lanes") and "no windows of 4 h or longer" in norm("#lanes"), norm("#lanes")[:200])
        pick_lane("both")
        both_summary = norm("#windows .filter-summary")
        check("4 h Both filter finds no joint window", expect["both"] == [0, 0] and "Site04 none" in both_summary and "Malapert none" in both_summary and count("#windows .win-open") == 0, {"engine": expect["both"], "ui": both_summary})
        drv.shot(EVIDENCE / "review_candidate_stage_filter.png")
        pick_lane("sun")
        click("#windows .win-open")
        check("filtered window still selects and moves the playhead", drv.js("return state.sel && state.sel.site") == 0 and drv.js("return state.index") == 0)
        set_min("0")
        check("Any length restores the full list and removes the summary", not count("#windows .filter-summary") and count("#windows .win-open") == 1)
        drv.js("move(52)")

        # Filter on the QA fixture: 15 min windows pass 15 min, fail 1 h; the longest clear window is named.
        click("#show-qa")
        drv.wait("return state.source === 'qa' && document.querySelectorAll('.sky-panel').length === 2")
        check("filter resets when the case changes", drv.js("return document.getElementById('min-duration').value") == "0" and drv.js("return state.minHours") == 0)
        pick_lane("sun")
        set_min("0.25")
        q15 = norm("#windows .filter-summary")
        check("QA 15 min filter keeps the 15 min clear windows", "QA North 1 window" in q15 and "QA South 1 window" in q15, q15)
        set_min("1")
        q1 = norm("#windows")
        check("QA 1 h filter: no qualifying window, longest clear window named", q1.count("No clear window of 1 h or longer.") == 2 and "Longest clear window: 15 min" in q1 and "Clear 15 min" in q1, q1[:300])
        dimmed = drv.js("return document.querySelectorAll('#lanes .seg.clear.is-dim').length")
        check("lane segments shorter than the minimum are dimmed, labels still readable", dimmed == 2 and "Clear" in norm("#lanes"), dimmed)
        check("Unknown spans stay listed under the filter", "Unknown spans" in norm("#windows") and "missing_right_endpoint" in norm("#windows"))
        set_min("0")
        click("#show-practice")
        drv.wait("return state.source === 'practice' && document.querySelectorAll('.sky-panel').length === 2")
        drv.js("state.site = 0; move(52)")

        # Reviewer questions on the practice case
        drv.js("state.site = 0; render()")
        check("reviewer: which site has more Sun-centre clearance", "Site04 had more Sun-centre clearance than Malapert, by 48 h." in norm("#answers"), norm("#answers .result-lead"))

        # ===== Dock and navigation =====
        drv.js("move(10)")
        drv.js("const sel = document.getElementById('step-size'); sel.value = '3600'; sel.dispatchEvent(new Event('change', {bubbles: true})); document.getElementById('next').click()")
        check("Step 1 hour advances four 15-minute samples", drv.js("return state.index") == 14)
        drv.js("const sel = document.getElementById('step-size'); sel.value = '0'; sel.dispatchEvent(new Event('change', {bubbles: true}));")
        click("#jump-end")
        end_i = drv.js("return {i: state.index, last: sharedSampleCount() - 1, disabled: document.getElementById('jump-end').disabled}")
        check("End jumps to the last shared sample", end_i["i"] == end_i["last"] and end_i["disabled"], end_i)
        click("#jump-start")
        check("Start jumps to the first sample", drv.js("return state.index") == 0)
        drv.js("move(52)")

        drv.js(
            "const svg = document.querySelector('#chart svg'); const r = svg.getBoundingClientRect(); const b = state.chartBox;"
            " const x = r.left + (b.left + 0.25 * (b.W - b.left - b.right)) * (r.width / b.W);"
            " const host = document.getElementById('chart');"
            " host.dispatchEvent(new PointerEvent('pointerdown', {bubbles: true, button: 0, clientX: x, clientY: r.top + 60, pointerId: 1}));"
            " host.dispatchEvent(new PointerEvent('pointerup', {bubbles: true, pointerId: 1}));"
        )
        quarter = drv.js("return state.index")
        check("clicking the chart moves the shared playhead", abs(quarter - 48) <= 2, quarter)
        drv.js("move(52)")

        # ===== Sky stage: scale, path, layers, sites, cursor =====
        verdict = drv.js("return document.getElementById('verdict').innerText")
        check("verdict 13:00 selected UTC", "2025-01-01T13:00:00Z" in verdict, verdict.splitlines()[0])
        check(
            "verdict sentence",
            "Site04's Sun centre is 1.66° above 0°. Malapert's is 2.22° below 0°." in verdict and "Earth's centre is below 0° at both sites." in verdict,
            verdict,
        )
        pills = drv.js("return Array.from(document.querySelectorAll('.sky-panel')).map(p => p.querySelector('.sky-pills').innerText)")
        check("Malapert Sun Blocked at geometric 0°", "Sun · Blocked at geometric 0°" in pills[1] and "Terrain clearance unknown" in pills[1], pills[1])
        check("Site04 Sun Clear at geometric 0°", "Sun · Clear at geometric 0°" in pills[0], pills[0])
        check("terrain diagnostic off by default", count(".sky-terrain-line") == 0)
        metrics = drv.js("return Array.from(document.querySelectorAll('.sky-panel')).map(p => p.querySelector('.metrics').innerText.toLowerCase())")
        check(
            "every metric shown under both plots",
            all(all(k in m for k in ("azimuth", "elevation", "horizon", "margin", "dem (diagnostic)", "both centres")) for m in metrics),
            metrics[1].replace("\n", " | "),
        )
        glyph = drv.js(
            "const sun = document.querySelector('.sky-sun'); const earth = document.querySelector('.sky-earth');"
            " return {sunRays: sun.querySelectorAll('.mk-ray').length, earthLand: earth.querySelectorAll('.mk-land').length,"
            " clearDash: document.querySelector('.sky-panel[data-site=\"0\"] .sky-sun .mk-ring').getAttribute('stroke-dasharray'),"
            " blockedDash: document.querySelector('.sky-panel[data-site=\"1\"] .sky-sun .mk-ring').getAttribute('stroke-dasharray')}"
        )
        check("body glyphs with state rings (clear solid, blocked dashed)", glyph["sunRays"] == 8 and glyph["earthLand"] == 1 and glyph["clearDash"] == "" and glyph["blockedDash"] == "3 2.5", glyph)

        dm = drv.js("return document.querySelector('.sky-panel[data-site=\"1\"] .metrics').innerText")
        check("full saved fractions shown by default", "−2.216453" in dm and "158.508524" in dm, dm.replace("\n", " | ")[:200])
        click('.tool[data-key="decimals"][data-value="2"]')
        dm2 = drv.js("return document.querySelector('.sky-panel[data-site=\"1\"] .metrics').innerText")
        check("Decimals 2 shortens metric values", "−2.22" in dm2 and "−2.216453" not in dm2)
        check("Decimals 2 shortens the readout margin too", "−2.22°" in norm("#readout") and "−2.216453" not in norm("#readout"), norm("#readout")[:160])
        click('.tool[data-key="decimals"][data-value="6"]')

        radii = {}
        for rng in ("5", "15", "30", "full"):
            tool("range", rng)
            radii[rng] = drv.js(
                "return {rings: Array.from(document.querySelectorAll('.sky-svg')).map(s => Array.from(s.querySelectorAll('.sky-ring')).map(c => c.getAttribute('r')).join(',')),"
                " note: document.getElementById('scale-note').textContent, centre: document.querySelector('.sky-svg text.sky-grid').textContent}"
            )
        check("every scale keeps both plots identical", all(len(set(v["rings"])) == 1 for v in radii.values()), {k: v["rings"][0] for k, v in radii.items()})
        check("only Full sky calls the centre zenith", "zenith" in radii["full"]["centre"] and all("zenith" not in radii[k]["centre"] for k in ("5", "15", "30")), {k: v["centre"] for k, v in radii.items()})
        tool("range", "15")
        tool("trail", "full")
        trail = drv.js("return {paths: document.querySelectorAll('.trail path').length, dots: document.querySelectorAll('.trail-dot').length}")
        check("path across the window drawn", trail["paths"] == 8 and trail["dots"] > 4, trail)
        drv.shot(EVIDENCE / "review_candidate_stage_tools.png")
        tool("trail", "off")
        click('.tool[data-toggle="grid"]')
        grid_off = drv.js("const g = document.querySelector('.sky-grid'); return {data: document.getElementById('sky-stage').dataset.grid, shown: getComputedStyle(g).display}")
        check("Grid layer toggles off", grid_off["data"] == "off" and grid_off["shown"] == "none", grid_off)
        click('.tool[data-toggle="grid"]')
        tool("layout", "single")
        single = drv.js("return Array.from(document.querySelectorAll('.sky-panel')).filter(p => getComputedStyle(p).display !== 'none').length")
        check("Selected-site layout shows one plot", single == 1, single)
        tool("layout", "both")
        cur = drv.js(
            "const svg = document.querySelector('.sky-svg'); const r = svg.getBoundingClientRect();"
            " svg.dispatchEvent(new PointerEvent('pointermove', {bubbles: true, clientX: r.left + r.width * 0.75, clientY: r.top + r.height / 2}));"
            " const n = document.getElementById('pointer-readout'); return {hidden: n.hidden, text: n.textContent}"
        )
        check("pointer readout gives az and el under the cursor", not cur["hidden"] and "Cursor · az" in cur["text"], cur)
        tool("range", "30")
        click('.tool[data-key="decimals"][data-value="2"]')
        click("#view-reset")
        reset = drv.js("return {v: state.view, terrain: state.showTerrain}")
        check("Reset view restores defaults", reset["v"] == {"range": "15", "trail": "off", "grid": True, "shade": True, "labels": True, "layout": "both", "decimals": 6, "terrain": "fill", "peaks": True} and reset["terrain"] is False, reset)

        drv.js("document.querySelector('.sky-panel[data-site=\"1\"] .sky-sun').dispatchEvent(new MouseEvent('click', {bubbles: true}))")
        pv = drv.js("const p = document.getElementById('preview'); return {hidden: p.hidden, text: p.innerText, spark: !!p.querySelector('svg.spark')}")
        check("marker click opens preview with chart", not pv["hidden"] and "Sun centre" in pv["text"] and "−2.216453" in pv["text"].replace("-", "−") and pv["spark"], pv["text"][:160])
        drv.js("move(53)")
        pv2 = drv.js("return document.getElementById('preview').innerText")
        check("preview follows the playhead", "2025-01-01T13:15:00Z" in pv2)
        drv.js("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}))")
        drv.js("move(52)")

        # ===== Playback =====
        drv.js("move(0); document.getElementById('playback-speed').value = 100; document.getElementById('playback-speed').dispatchEvent(new Event('input', {bubbles: true}));")
        click("#play-toggle")
        time.sleep(0.8)
        advanced = drv.js("return {i: state.index, playing: state.playing, label: document.querySelector('#play-toggle .btn-label').textContent}")
        check("Play advances the playhead", advanced["i"] > 3 and advanced["playing"] and advanced["label"] == "Pause", advanced)
        click("#play-toggle")
        paused_at = drv.js("return state.index")
        time.sleep(0.4)
        check("Pause holds the playhead", drv.js("return state.index") == paused_at and not drv.js("return state.playing"))
        drv.js("document.getElementById('playback-speed').value = 55; document.getElementById('playback-speed').dispatchEvent(new Event('input', {bubbles: true})); move(52)")
        ctl = drv.js("return {start: document.getElementById('start-run').disabled, cancel: document.getElementById('cancel-run').disabled}")
        check("idle: Start enabled, Stop disabled", ctl == {"start": False, "cancel": True}, ctl)
        opts = drv.js("const d = document.getElementById('run-more'); const open = d.open; d.open = true; const shown = document.getElementById('playback-speed').offsetParent !== null; d.open = open; return {open, shown}")
        check("run options tuck away until opened", opts == {"open": False, "shown": True}, opts)

        # ===== Terrain toggle =====
        click('.tool[data-key="decimals"][data-value="2"]')
        check("terrain style tools hidden while diagnostic is off", drv.js("return document.querySelector('.terrain-only').offsetParent === null"))
        click("#terrain-toggle")
        notes = drv.js("return Array.from(document.querySelectorAll('.terrain-note')).map(n => n.innerText)")
        check("terrain style tools shown when diagnostic is on", drv.js("return document.querySelector('.terrain-only').offsetParent !== null"))
        check("terrain line drawn when toggled", count(".sky-terrain-line") == 4)
        check("Malapert Sun vs displayed DEM", "Sun −2.22° vs displayed DEM −9.37°" in notes[1], notes[1])
        verdict_after = drv.js("return document.getElementById('verdict').innerText")
        pills_after = drv.js("return Array.from(document.querySelectorAll('.sky-panel')).map(p => p.querySelector('.sky-pills').innerText)")
        check("verdict unchanged by terrain toggle", verdict_after == verdict and pills_after == pills)
        check("terrain stays Unknown", "Terrain clearance unknown" in pills_after[1] and "Terrain stays Unknown" in notes[1])
        drv.shot(EVIDENCE / "review_candidate_stage_terrain.png")
        check("silhouette: filled skyline plus above-0° tint per plot", count(".sky-terrain-fill") == 4 and count(".sky-terrain-fill-hi") == 2)
        clips = drv.js("return Array.from(document.querySelectorAll('clipPath')).map(c => c.id).filter(id => id !== 'ch-clip')")
        check("clip and hatch ids are unique per plot", len(clips) == 2 and len(set(clips)) == 2 and drv.js("return new Set(Array.from(document.querySelectorAll('.sky-svg pattern')).map(p => p.id)).size") == 2, clips)
        stats = drv.js("return Array.from(document.querySelectorAll('.terrain-stats')).map(s => s.innerText)")
        check("skyline summary chips per plot", len(stats) == 2 and all("Above 0° over" in s and "No DEM data" in s and "bins" in s for s in stats), stats)
        check("Site04 summary matches the saved profile (high 0.95°, low −4.52°)", "0.95°" in stats[0] and "−4.52°" in stats[0], stats[0])
        check("peaks: DEM high/low labels and Sun/Earth leaders", count(".terr-label") == 4 and count(".terr-leader") == 4 and count(".terr-foot") == 4)
        click('.tool[data-toggle="peaks"]')
        check("Peaks & leaders toggle removes them", count(".terr-label") == 0 and count(".terr-leader") == 0 and count(".terrain-stats") == 2)
        click('.tool[data-toggle="peaks"]')
        tool("terrain", "line")
        check("outline: no fill, smooth curve", count(".sky-terrain-fill") == 0 and count(".sky-terrain-line") == 4 and count(".terr-dot") == 0)
        tool("terrain", "bins")
        check("raw bins: one dot per saved DEM bin (72 per plot)", count(".terr-dot") == 144 and count(".sky-terrain-fill") == 0, count(".terr-dot"))
        drv.shot(EVIDENCE / "review_candidate_stage_terrain_bins.png")
        same = drv.js("return document.getElementById('verdict').innerText") == verdict and drv.js(
            "return Array.from(document.querySelectorAll('.sky-panel')).map(p => p.querySelector('.sky-pills').innerText)"
        ) == pills
        check("terrain styles never change the verdict or pills", same)
        tool("terrain", "fill")
        pressed = drv.js("return Array.from(document.querySelectorAll('.tool[data-key=\"terrain\"]')).map(b => b.dataset.value + ':' + b.getAttribute('aria-pressed')).join(' ')")
        check("terrain style buttons reflect the active style", pressed == "fill:true line:false bins:false", pressed)
        tool("range", "30")
        time.sleep(0.3)
        drv.shot(EVIDENCE / "review_candidate_stage_terrain_30.png")
        tool("range", "15")
        click("#terrain-toggle")
        click('.tool[data-key="decimals"][data-value="6"]')
        check("terrain toggle leaves totals, lanes and windows alone", norm("#answers .result-joint") == "Both centres clear · 0 h at either site" and count("#lanes .lane-site") == 2)

        # ===== Locations: pin selection =====
        click("#tab-locations")
        check("Locations tab swaps the rail", not drv.js("return document.getElementById('panel-locations').hidden") and drv.js("return document.getElementById('windows').closest('[role=tabpanel]').hidden"))
        pin_letters = drv.js("return Array.from(document.querySelectorAll('.pin-letter')).map(n => n.textContent)")
        check("pins labelled A and B", pin_letters == ["A", "B"], pin_letters)
        drv.js("document.querySelector('.pin-hit[data-site=\"1\"]').dispatchEvent(new MouseEvent('click', {bubbles: true}))")
        sel = drv.js(
            "return {sky: document.querySelector('.sky-panel.is-selected')?.dataset.site,"
            " lane: Array.from(document.querySelectorAll('.lane-site')).findIndex(n => n.classList.contains('is-selected')),"
            " state: state.site, ev: document.getElementById('why').innerText.includes('Malapert'),"
            " ro: document.querySelector('.ro-site.is-selected')?.dataset.site,"
            " pin: document.querySelector('.pin-hit.is-selected')?.dataset.site}"
        )
        check("pin B selects sky panel, lane, readout, evidence", sel["sky"] == "1" and sel["lane"] == 1 and sel["state"] == 1 and sel["pin"] == "1" and sel["ro"] == "1" and sel["ev"], sel)
        drv.shot(EVIDENCE / "review_candidate_stage_locations.png")
        click("#tab-windows")
        drv.js("selectSiteFromScene(0)")

        # ===== QA fixture: transitions and Unknown =====
        click("#show-qa")
        drv.wait("return state.source === 'qa' && document.querySelectorAll('.sky-panel').length === 2")
        qa_north = json.loads((REPO / "web/review-candidate/qa-north.json").read_text())
        check("QA fixture is labelled synthetic", "QA fixture" in norm("#scenario-bar") + norm("#answers") and "synthetic" in norm("#answers").lower(), norm("#answers")[:200])
        pick_lane("sun")
        qa_win = norm("#windows .win-site")
        check("QA windows: clear and Unknown spans with reasons", all(t in qa_win for t in ("Clear windows", "Unknown spans", "missing_right_endpoint", "missing_ephemeris")), qa_win)
        check("QA Sun totals from engine intervals", "Clear 15 min" in qa_win and "Unknown 30 min" in qa_win and "Blocked 15 min" in qa_win, qa_win)
        drv.js("move(3)")
        click("#windows .win-site .win-open")
        first_clear = next(i for i in qa_north["intervals"] if i["lane"] == "sun" and i["state"] == "clear")
        qa_utc = drv.js("return document.getElementById('utc').textContent")
        check("QA clear window jumps to its start", qa_utc == first_clear["start_utc"], qa_utc)
        check("QA clear window is highlighted in chart, lane and list", count("#chart .ch-sel") == 1 and count("#lanes .seg.is-selected") == 1 and count("#windows .win-open.is-selected") == 1)
        check("QA Unknown crosshatched in chart and lanes", count("#chart .ch-unknown") >= 1 and count("#lanes .seg.unknown") >= 1)
        unk_btns = drv.js("return Array.from(document.querySelectorAll('#windows .win-site')[0].querySelectorAll('.win-open')).filter(b => b.dataset.state === 'unknown').length")
        check("QA Unknown merged into one span", unk_btns == 1, unk_btns)
        drv.js("document.querySelector('#windows .win-site .win-open[data-state=\"unknown\"]').click()")
        unk = drv.js("return state.runs[0].payload.samples[state.index].sun.state")
        check("Unknown span jumps to an Unknown sample", unk == "unknown", unk)
        ro_unk = norm("#readout")
        check("readout labels Unknown with its reason, not as a clearance", "Unknown" in ro_unk and "missing_right_endpoint" in ro_unk and "not a clearance" in ro_unk, ro_unk[:300])
        drv.js("move(2)")
        ro_null = norm("#readout")
        check("Unknown with no saved angle shows no margin number", "no saved margin" in ro_null and "missing_ephemeris" in ro_null, ro_null[:300])
        check("state names readable without colour", all(w in norm("#lanes") for w in ("Clear", "Blocked", "Unknown")), norm("#lanes")[:160])
        unk_style = drv.js("const u = document.querySelector('#lanes .seg.unknown'); const c = document.querySelector('#lanes .seg.clear'); return [getComputedStyle(u).backgroundImage, getComputedStyle(c).backgroundImage]")
        check("Unknown and Clear use different patterns", unk_style[0] != unk_style[1] and "linear-gradient" in unk_style[0] and "radial-gradient" in unk_style[1], unk_style)
        pick_lane("both")
        check("QA Both lane: Unknown and Blocked kept distinct", "Unknown" in norm("#lanes") and "Blocked" in norm("#lanes"))
        qa_both = drv.js("return state.runs[0].payload.intervals.filter(i => i.lane === 'both').map(i => i.state).join(',')")
        check("QA Both lane order from engine (clear, blocked, unknown, blocked)", qa_both == "clear,blocked,unknown,blocked", qa_both)
        drv.shot(EVIDENCE / "review_candidate_stage_qa.png")
        pick_lane("sun")
        click("#show-practice")
        drv.wait("return state.source === 'practice' && document.querySelectorAll('.sky-panel').length === 2")

        # ===== 3. Live feedback =====
        def live_run(speed: int) -> None:
            drv.js(
                "const s = document.getElementById('playback-speed'); s.value = arguments[0];"
                " s.dispatchEvent(new Event('input', {bubbles: true}));"
                " document.getElementById('scenario').value = 'practice-48h';"
                " document.getElementById('start-run').click();",
                speed,
            )

        live_run(40)
        drv.wait("return state.live && state.partial && sharedSampleCount() >= 4", timeout=30)
        follow_on = drv.js("return state.follow && document.getElementById('follow-latest').checked")
        check("follow latest on at stream start", follow_on, norm("#results-through"))
        ctl_live = drv.js("return {start: document.getElementById('start-run').disabled, cancel: document.getElementById('cancel-run').disabled}")
        check("streaming: Start disabled, Stop enabled", ctl_live["start"] and not ctl_live["cancel"], ctl_live)
        prog = norm("#site-progress")
        check("per-site progress shown with pending, not Unknown", "Site04" in prog and "Malapert" in prog and "pending, not Unknown" in prog, prog)
        snap = drv.js("return {cut: sharedCutoffUtc(), through: document.getElementById('results-through').textContent, answers: document.getElementById('answers').textContent.replace(/\\s+/g, ' ')}")
        check("latest shared resolved UTC is shown", snap["cut"] and snap["cut"] in snap["through"], snap["through"])
        check("partial totals are labelled with the cutoff", "Partial totals through" in snap["answers"] and snap["cut"] in snap["answers"], snap["answers"][:260])
        live_win = norm("#windows")
        check("windows rail says only resolved samples are counted", "Pending is not Unknown" in live_win or "so far" in live_win, live_win[:200])
        lane_pend = drv.js("return {zones: document.querySelectorAll('#lanes .pending-zone').length, chart: document.querySelectorAll('#chart .ch-pending').length, unknown: document.querySelectorAll('#lanes .seg.unknown').length}")
        check("pending is dotted and separate from scientific Unknown", lane_pend["zones"] >= 1 and lane_pend["chart"] == 1 and lane_pend["unknown"] == 0, lane_pend)
        pend_style = drv.js("const p = document.querySelector('#lanes .pending-zone'); return [getComputedStyle(p).backgroundImage, getComputedStyle(p).borderLeftStyle]")
        check("pending zone uses a dotted pattern, not the Unknown crosshatch", "radial-gradient" in pend_style[0] and "linear-gradient" not in pend_style[0], pend_style)
        rng = drv.js("const p = document.getElementById('playhead'); return {max: Number(p.max), shared: sharedSampleCount() - 1, n: state.runs[0].payload.samples.length}")
        check("playhead stays within the shared available range", rng["max"] == rng["shared"] and rng["max"] <= rng["n"] - 1, rng)
        drv.js("const p = document.getElementById('playhead'); p.value = 1; p.dispatchEvent(new Event('input', {bubbles: true}));")
        time.sleep(0.8)
        after = drv.js(
            "return {follow: state.follow, checked: document.getElementById('follow-latest').checked, index: state.index,"
            " shared: sharedSampleCount(), max: Number(document.getElementById('playhead').max)}"
        )
        check("scrubbing pauses Follow latest", after["follow"] is False and after["checked"] is False and after["index"] == 1 and after["shared"] > 4, after)
        check("playhead max grows with the shared range", after["max"] == after["shared"] - 1, after)
        drv.shot(EVIDENCE / "review_candidate_stage_live.png")
        click("#follow-latest")
        resumed = drv.js("return {index: state.index, shared: sharedSampleCount(), follow: state.follow}")
        check("Follow latest resumes at newest shared sample", resumed["follow"] and resumed["index"] == resumed["shared"] - 1, resumed)
        drv.wait("return state.live && !state.partial", timeout=120)
        ctl_done = drv.js("return {start: document.getElementById('start-run').disabled, cancel: document.getElementById('cancel-run').disabled}")
        check("complete: Start enabled again, Stop disabled", ctl_done == {"start": False, "cancel": True}, ctl_done)
        done_head = norm("#answers")
        check("complete run drops the partial label and keeps both headline numbers", "Partial totals" not in done_head and "48 h" in done_head and "0 h" in done_head, done_head[:220])
        snap_fast = drv.js(
            "return JSON.stringify({a: state.runs.map(r => [r.payload.samples, r.payload.intervals, r.payload.elapsed_seconds]),"
            " o: state.comparison.overlap, ids: state.runs.map(r => r.payload.run_id)})"
        )

        click("#show-practice")
        drv.wait("return state.source === 'practice' && !state.live")
        live_run(10)
        drv.wait("return state.live && state.partial && sharedSampleCount() >= 2", timeout=30)
        drv.wait("return state.live && !state.partial", timeout=180)
        snap_slow = drv.js(
            "return JSON.stringify({a: state.runs.map(r => [r.payload.samples, r.payload.intervals, r.payload.elapsed_seconds]),"
            " o: state.comparison.overlap, ids: state.runs.map(r => r.payload.run_id)})"
        )
        check("playback speed leaves engine results unchanged", snap_fast == snap_slow, {"fast_len": len(snap_fast), "slow_len": len(snap_slow)})
        totals = drv.js("return state.runs.map(r => { const e = r.payload.elapsed_seconds; return ['sun','earth','both'].map(l => e[l].clear + e[l].blocked + e[l].unknown) })")
        check("Clear + Blocked + Unknown = window per lane", all(v == 172800 for row in totals for v in row), totals)

        # ===== Layout: desktop and 390 px =====
        click("#show-practice")
        drv.wait("return state.source === 'practice' && document.querySelectorAll('.sky-panel').length === 2")
        drv.js("move(52)")
        time.sleep(0.3)
        desk = drv.js(
            "return {sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth,"
            " over: Array.from(document.querySelectorAll('.sky-panel, .verdict, .stage-bar, .sky-pills, .ro-site, .win-site, .scenario-bar')).filter(n => n.scrollWidth > n.clientWidth + 1).length,"
            " chartW: document.getElementById('chart').getBoundingClientRect().width, rail: document.querySelector('.windows-rail').getBoundingClientRect().width}"
        )
        check("desktop: no horizontal overflow", desk["sw"] <= desk["cw"] and desk["over"] == 0, desk)
        check("desktop: chart takes most of the width, rail compact", desk["chartW"] > 850 and desk["rail"] < 400, desk)

        drv.size(390, 2600)
        time.sleep(0.5)
        drv.js("move(52)")
        time.sleep(0.3)
        narrow = drv.js(
            "const r = (id) => document.querySelector(id).getBoundingClientRect();"
            " return {sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth,"
            " over: Array.from(document.querySelectorAll('.sky-panel, .verdict, .stage-bar, .sky-pills, .win-site, .ro-site, .scenario-bar, .result-joint, .site-num')).filter(n => n.scrollWidth > n.clientWidth + 1).map(n => n.className),"
            " cols: getComputedStyle(document.querySelector('.sky-pair')).gridTemplateColumns.split(' ').length,"
            " nums: Array.from(document.querySelectorAll('#answers .sn-val')).map(n => n.getBoundingClientRect().top),"
            " joint: r('#answers .result-joint').top, chart: r('#chart').top, windows: r('#windows').top, chartBottom: r('#chart').bottom,"
            " lanesTop: r('#lanes').top, dock: getComputedStyle(document.getElementById('time-dock')).position}"
        )
        check("390 px: no horizontal overflow, plots stack", narrow["sw"] <= narrow["cw"] and not narrow["over"] and narrow["cols"] == 1, narrow)
        check("390 px: both headline numbers and the joint result come before the chart", max(narrow["nums"]) < narrow["chart"] and narrow["joint"] < narrow["chart"], narrow)
        check("390 px: Windows stacked below the timeline", narrow["windows"] > narrow["chartBottom"] and narrow["windows"] > narrow["lanesTop"], narrow)
        check("390 px: both headline numbers share one row", abs(narrow["nums"][0] - narrow["nums"][1]) < 2, narrow["nums"])
        drv.size(390, 844)
        time.sleep(0.4)
        drv.js("window.scrollTo(0, document.getElementById('chart').getBoundingClientRect().top + window.scrollY - 40)")
        time.sleep(0.3)
        dock = drv.js(
            "const d = document.getElementById('time-dock').getBoundingClientRect();"
            " return {position: getComputedStyle(document.getElementById('time-dock')).position, bottom: d.bottom, vh: innerHeight,"
            " text: document.getElementById('dock-readout').textContent, prev: !!document.getElementById('prev').offsetParent, play: !!document.getElementById('play-toggle').offsetParent,"
            " slider: !!document.getElementById('playhead').offsetParent}"
        )
        check("390 px: shared time controls stay in view (sticky dock)", dock["position"] == "sticky" and dock["bottom"] <= dock["vh"] + 1 and dock["bottom"] > dock["vh"] - 8 and dock["prev"] and dock["play"] and dock["slider"], dock)
        check("390 px: dock carries the selected UTC, state and margin", "2025-01-01T13:00Z" in dock["text"] and "+1.661532°" in dock["text"] and "−2.216453°" in dock["text"], dock["text"])
        chart_px = drv.js("const s = document.querySelector('#chart svg').getBoundingClientRect(); return [s.width, s.height, parseFloat(getComputedStyle(document.querySelector('.ch-axis')).fontSize)]")
        check("390 px: chart drawn at real size with readable axis text", chart_px[0] > 300 and chart_px[1] > 220 and chart_px[2] >= 10, chart_px)
        drv.shot(EVIDENCE / "review_candidate_stage_390_dock.png")
        drv.size(390, 2600)
        time.sleep(0.4)
        drv.js("window.scrollTo(0, 0)")
        drv.shot(EVIDENCE / "review_candidate_stage_390.png")
        scales = drv.js("return Array.from(document.querySelectorAll('.sky-svg')).map(s => Array.from(s.querySelectorAll('.sky-ring')).map(c => c.getAttribute('r')).join(','))")
        check("identical angular scaling on both plots", len(set(scales)) == 1, scales)
        # QA at 390 px
        click("#show-qa")
        drv.wait("return state.source === 'qa' && document.querySelectorAll('.sky-panel').length === 2")
        drv.js("document.querySelector('#windows .win-site .win-open[data-state=\"unknown\"]').click()")
        qa_narrow = drv.js("return {sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, utc: document.getElementById('utc').textContent}")
        check("390 px QA fixture: no overflow, Unknown span selectable", qa_narrow["sw"] <= qa_narrow["cw"] and qa_narrow["utc"] == "2024-06-01T00:15:00Z", qa_narrow)
        drv.js("window.scrollTo(0, document.getElementById('explore').getBoundingClientRect().top + window.scrollY)")
        time.sleep(0.3)
        drv.shot(EVIDENCE / "review_candidate_stage_390_qa.png")
    finally:
        out_path.write_text(json.dumps(results, indent=2) + "\n")
        drv.close()
    failed = [r for r in results if not r["pass"]]
    print(f"{len(results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
