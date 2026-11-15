#!/usr/bin/env python3
"""Sprint 2 browser walkthrough: "Why?" panels, the decision flow, the 30-day case and the QA fixture.

Reuses the WebDriver client from review_candidate_browser_check.py. Needs chromedriver + chromium and a
running `lunar_navigator.cli serve` on --base. It never touches the 8766 server or web/replay.

Expected values come from the saved run JSON and, where present, from the raw Horizons response files
under data/, so the screen is compared with a source that the page does not read.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("rcbc", REPO / "builder/scripts/review_candidate_browser_check.py")
rcbc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rcbc)

CASE30 = REPO / "web/review-candidate/cases/practice-30d"


def ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def merged(run: dict, lane: str) -> list[list[str]]:
    out: list[list[str]] = []
    for item in run["intervals"]:
        if item["lane"] != lane:
            continue
        if out and out[-1][2] == item["state"]:
            out[-1][1] = item["end_utc"]
        else:
            out.append([item["start_utc"], item["end_utc"], item["state"]])
    return out


def nearest(run: dict, lane: str) -> dict:
    best = None
    for s in run["samples"]:
        m = s[lane]["margin_deg"]
        if m is not None and (best is None or abs(m) < abs(best["margin_deg"])):
            best = {**s[lane], "utc": s["timestamp_utc"]}
    return best


def raw_line(site_dir: str, body_dir: str, stamp: str) -> str | None:
    """Row text from the raw Horizons response, which the page does not read."""
    path = REPO / "data" / "horizons" / site_dir / body_dir / "response.json"
    if not path.exists():
        return None
    text = json.loads(path.read_text())["result"]
    for line in text.splitlines():
        if line.strip().startswith(stamp):
            return line.strip()
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://127.0.0.1:8798/review-candidate/")
    parser.add_argument("--evidence-dir", required=True)
    parser.add_argument("--driver-port", type=int, default=9547)
    parser.add_argument("--profile", default="/tmp/lunar-s2-profile")
    args = parser.parse_args()
    evidence = Path(args.evidence_dir)
    evidence.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    def check(name: str, ok: bool, detail=None) -> None:
        results.append({"check": name, "pass": bool(ok), "detail": detail})
        print(("PASS " if ok else "FAIL ") + name + (f" :: {detail}" if detail not in (None, "") else ""))

    drv = rcbc.Driver(args.driver_port, 1440, 2400, args.profile)

    def click(selector: str) -> None:
        drv.js("document.querySelector(arguments[0]).click()", selector)

    def norm(selector: str) -> str:
        return drv.js(
            "const n = document.querySelector(arguments[0]); return n ? n.textContent.replace(/\\s+/g, ' ').trim() : ''", selector
        )

    def set_select(selector: str, value: str) -> None:
        drv.js(
            "const e = document.querySelector(arguments[0]); e.value = arguments[1]; e.dispatchEvent(new Event('change', {bubbles: true}))",
            selector,
            value,
        )

    def why(key: str) -> str:
        drv.js("state.why = null; renderWhy();")
        click(f'.why-q[data-why="{key}"]')
        time.sleep(0.15)
        return norm("#why-body")

    try:
        drv.get(args.base)
        drv.wait("return document.querySelectorAll('.sky-panel').length === 2 && state.caseData.practice30 !== undefined", timeout=40)

        site04 = load(REPO / "web/replay/runs/site04-p02-practice.json")
        malapert = load(REPO / "web/replay/runs/malapert-practice.json")

        # ===== 1. Why 48 h / Why 0 h / Why terrain Unknown on the 48 h result screen =====
        buttons = drv.js("return Array.from(document.querySelectorAll('.why-q')).map(b => b.textContent.trim())")
        check(
            "result screen offers Why Site04 48 h, Why Malapert 0 h, both-centres and terrain questions",
            buttons == ["Why Site04 48 h?", "Why Malapert 0 h?", "Why both centres 0 h?", "Why terrain Unknown?"],
            buttons,
        )
        scope = norm(".why-scope")
        check(
            "scope line shows the UTC range, duration, mode and terrain state",
            "2025-01-01T00:00Z → 2025-01-03T00:00Z" in scope and "48 h" in scope and "Geometric 0°" in scope and "Terrain Unknown" in scope,
            scope,
        )
        text = why("sun:0")
        near0 = nearest(site04, "sun")
        check(
            "Why Site04 48 h: states 193 samples above 0° and 192 intervals of 15 min",
            "all 193 samples" in text and "192 intervals of 15 min give 48 h" in text and "final sample adds 0 s" in text,
            text[:260],
        )
        check(
            "Why Site04 48 h: source row carries the nearest sample's UTC, saved Horizons row, elevation and state",
            near0["utc"] in text and ws(near0["response_line"]) in text and f"{near0['elevation_deg']:.6f}" in text and " clear " in text,
            {"utc": near0["utc"], "row": near0["response_line"]},
        )
        text = why("sun:1")
        near1 = nearest(malapert, "sun")
        check(
            "Why Malapert 0 h: all 193 samples on or below 0°, blocked rule, 0 h",
            "all 193 samples" in text and "on or below the 0° horizon" in text and "including exact contact" in text and "0 h" in text,
            text[:260],
        )
        check(
            "Why Malapert 0 h: source row is the sample nearest the horizon with its margin",
            near1["utc"] in text and ws(near1["response_line"]) in text and f"{abs(near1['elevation_deg']):.6f}" in text,
            {"utc": near1["utc"], "elev": near1["elevation_deg"]},
        )
        text = why("both")
        check(
            "Why both centres 0 h: states both-above-same-sample rule and the blocked-beats-unknown order",
            "same sample" in text and "Blocked beats Unknown" in text and text.count("Site04:") >= 1 and text.count("Malapert:") >= 1,
            text[:300],
        )
        text = why("terrain")
        check(
            "Why terrain Unknown: reason code, M4 requirements, diagnostic not a result, observer altitudes",
            "terrain_not_reviewed" in text and "reviewed lunar frame" in text and "independently checked skyline" in text
            and "diagnostic" in text and "Site04 1.738902 km" in text and "Malapert 0 km" in text,
            text[:300],
        )
        click('.why-q[data-why="terrain"]')
        time.sleep(0.1)
        check("a second click on the open question closes it", "Choose a question" in norm("#why-body"), norm("#why-body")[:80])
        drv.js("window.scrollTo(0, document.getElementById('why-result').getBoundingClientRect().top + window.scrollY - 20)")
        click('.why-q[data-why="sun:1"]')
        time.sleep(0.3)
        drv.shot(evidence / "s2_why_malapert_0h.png")

        # ===== 2. Decision panel on the 48 h case =====
        verdict = norm(".dec-verdict")
        check("decision: Sun-centre, any length -> Partly, only Site04", verdict.startswith("Partly. Only Site04 has a Sun-centre clearance window"), verdict)
        click('.ask-bar .tool[data-key="lane"][data-value="both"]')
        verdict = norm(".dec-verdict")
        check("decision: Both centres clear -> No, neither site", verdict.startswith("No. Neither site has a Both centres clear window"), verdict)
        closest = drv.js("return document.querySelectorAll('#dec-answer .win-closest').length")
        check("decision: zero result offers the closest sampled point to 0° for each site", closest == 2, closest)
        click('#dec-answer .dec-site:nth-of-type(2) .win-closest')
        time.sleep(0.2)
        landed = drv.js("return {site: state.site, utc: sampleAt(state.site).timestamp_utc, lane: state.lane}")
        want = min(malapert["samples"], key=lambda s: abs(min(s["sun"]["margin_deg"], s["earth"]["margin_deg"])))
        check("decision: closest-point button lands on the saved sample (Malapert, both lane)", landed["site"] == 1 and landed["utc"] == want["timestamp_utc"], {"landed": landed, "want": want["timestamp_utc"]})
        click('#dec-answer .dec-site:nth-of-type(1) .why-open')
        time.sleep(0.2)
        check("decision: Why? opens the same why panel with the joint rule", state_why(drv) == "both" and "same sample" in norm("#why-body"), state_why(drv))
        other = norm("#dec-cases")
        e30 = load(CASE30 / "runs/site04-p02-practice-30d.json")
        m30 = load(CASE30 / "runs/malapert-practice-30d.json")
        check(
            "decision: other supported case lists the 30-day pair with its own answer and an open button",
            "Practice, 30 days" in other and "2025-01-01T00:00Z → 2025-01-31T00:00Z" in other and "Open this case" in other and "Practice, 48 h" not in other,
            other[:300],
        )

        # ===== 3. Second case: 30 days with a real transition =====
        click("#decision .case-open")
        drv.wait("return state.source === 'practice30' && document.querySelectorAll('.sky-panel').length === 2", timeout=40)
        check("30-day case loads from the saved package, not the witnessed replay", drv.js("return state.comparison.runs[0].file") == "runs/site04-p02-practice-30d.json", None)
        check("30-day case is labelled practice and not an eligible claim", "Practice · 30 days" in norm("#answers") and drv.js("return state.comparison.eligible_for_submission_claim") is False, norm("#answers .result-tags"))
        scope = norm(".why-scope")
        check("30-day scope line: 2025-01-01 → 2025-01-31, 720 h", "2025-01-01T00:00Z → 2025-01-31T00:00Z" in scope and "720 h" in scope, scope)
        sun_sites = drv.js("return state.runs.map(r => r.payload.elapsed_seconds.sun.clear)")
        check(
            "30-day totals equal the engine result (Site04 720 h, Malapert 436 h)",
            sun_sites == [e30["elapsed_seconds"]["sun"]["clear"], m30["elapsed_seconds"]["sun"]["clear"]] == [2592000, 1569600],
            sun_sites,
        )
        verdict = norm(".dec-verdict")
        check("30-day decision: Sun-centre any length -> Yes, both sites", verdict.startswith("Yes. Both sites have a Sun-centre clearance window"), verdict)
        set_select("#min-duration", "168")
        verdict = norm(".dec-verdict")
        sun_m = [w for w in merged(m30, "sun") if w[2] == "clear"]
        check(
            "30-day decision: 7 days or longer still has both sites (Malapert window 2025-01-05T10:00Z → 2025-01-23T14:00Z)",
            verdict.startswith("Yes.") and sun_m == [["2025-01-05T10:00:00Z", "2025-01-23T14:00:00Z", "clear"]] and "01-05" in norm("#dec-answer") and "10:00" in norm("#dec-answer"),
            {"verdict": verdict, "answer": norm("#dec-answer")[:240]},
        )
        click('.ask-bar .tool[data-key="lane"][data-value="earth"]')
        set_select("#min-duration", "24")
        verdict = norm(".dec-verdict")
        check("30-day decision: Earth centre 24 h -> Yes, both", verdict.startswith("Yes."), verdict)
        set_select("#min-duration", "168")
        verdict = norm(".dec-verdict")
        e_s04 = [w for w in merged(e30, "earth") if w[2] == "clear"]
        check(
            "30-day decision: Earth centre 7 days -> Yes (Site04 and Malapert each have one window longer than 7 days)",
            verdict.startswith("Yes.") and len(e_s04) == 1,
            verdict,
        )
        click('.ask-bar .tool[data-key="lane"][data-value="sun"]')
        set_select("#min-duration", "0")
        # Transition: Malapert Sun-centre blocked -> clear at 2025-01-05T10:00Z
        text = why("sun:1")
        before = next(s for s in m30["samples"] if s["timestamp_utc"] == "2025-01-05T09:00:00Z")["sun"]
        after = next(s for s in m30["samples"] if s["timestamp_utc"] == "2025-01-05T10:00:00Z")["sun"]
        check(
            "Why Malapert (30 d): shows the sample before and at the 2025-01-05T10:00Z change",
            "2025-01-05T09:00:00Z" in text and "2025-01-05T10:00:00Z" in text and "blocked" in text and "clear" in text,
            text[:320],
        )
        check(
            "transition rows: margin ≤ 0 is blocked at 09:00 and > 0 is clear at 10:00 in the saved samples",
            before["margin_deg"] <= 0 < after["margin_deg"] and before["state"] == "blocked" and after["state"] == "clear",
            {"09:00": before["margin_deg"], "10:00": after["margin_deg"]},
        )
        raw_b = raw_line("malapert-practice-30d", "sun-0ebf1cb6ff30", "2025-Jan-05 09:00")
        raw_a = raw_line("malapert-practice-30d", "sun-0ebf1cb6ff30", "2025-Jan-05 10:00")
        if raw_a and raw_b:
            check(
                "transition rows equal the raw Horizons response lines (read from data/, not from the page)",
                raw_b == before["response_line"].strip() and raw_a == after["response_line"].strip()
                and ws(before["response_line"]) in text and ws(after["response_line"]) in text,
                {"raw_09": raw_b, "raw_10": raw_a},
            )
        else:
            check("transition rows equal the raw Horizons response lines", False, "raw response not found under data/")
        drv.js("window.scrollTo(0, document.getElementById('why-result').getBoundingClientRect().top + window.scrollY - 20)")
        time.sleep(0.3)
        drv.shot(evidence / "s2_why_malapert_30d_transition.png")
        click(".why-jump")
        time.sleep(0.3)
        check("Show this sample in the timeline moves the shared playhead to 10:00Z", drv.js("return sampleAt(1).timestamp_utc") == "2025-01-05T10:00:00Z", None)
        drv.js("window.scrollTo(0, document.getElementById('decision').getBoundingClientRect().top + window.scrollY - 20)")
        time.sleep(0.3)
        drv.shot(evidence / "s2_decision_30d.png")

        # ===== 4. Back to the witnessed 48 h case: unchanged =====
        click("#show-practice")
        drv.wait("return state.source === 'practice' && document.querySelectorAll('.sky-panel').length === 2")
        replay_runs = drv.js("return state.comparison.runs.map(r => r.file)")
        check("48 h button still loads the witnessed replay files", replay_runs == ["runs/site04-p02-practice.json", "runs/malapert-practice.json"] , replay_runs)

        # ===== 5. QA fixture: transitions and Unknown =====
        click("#show-qa")
        drv.wait("return state.source === 'qa' && document.querySelectorAll('.sky-panel').length === 2")
        text = why("sun:0")
        check(
            "QA Why (Sun, QA North): mixed result with changes, Unknown separate from clear and blocked, saved reason",
            "clear at 1 of 5 samples" in text and "unknown at" in text and "Unknown is not clear and not blocked" in text and "missing_right_endpoint" in text and "Changes: clear from" in text,
            text[:420],
        )
        case_names = drv.js("return Array.from(document.querySelectorAll('#dec-cases .dec-case strong')).map(n => n.textContent)")
        check(
            "QA fixture is labelled synthetic on screen and is not offered as a decision case",
            "QA fixture" not in case_names and "Practice, 48 h" in case_names and "Practice, 30 days" in case_names and drv.js("return state.comparison.qa_fixture") is True and "synthetic" in norm("#answers").lower(),
            case_names,
        )
        click('.ask-bar .tool[data-key="lane"][data-value="both"]')
        set_select("#min-duration", "1")
        verdict = norm(".dec-verdict")
        check("QA decision: both centres 1 h -> No (transitions are 15 min long)", verdict.startswith("No."), verdict)
        set_select("#min-duration", "0.25")
        verdict = norm(".dec-verdict")
        check("QA decision: both centres 15 min -> Yes (the 15 min clear sample)", verdict.startswith("Yes."), verdict)
        text = why("both")
        check("QA Why (Both): Unknown reason is listed, not hidden", "missing_ephemeris" in text and "Unknown is not clear and not blocked" in text, text[:300])
        qa_unknown = drv.js("return state.runs.map(r => r.payload.elapsed_seconds.both.unknown)")
        check("QA fixture Unknown seconds are non-zero and shown separately", all(v > 0 for v in qa_unknown), qa_unknown)

        # ===== 6. 390 px: no overflow with Why + decision panels =====
        click("#show-practice30")
        drv.wait("return state.source === 'practice30' && document.querySelectorAll('.sky-panel').length === 2", timeout=40)
        click('.why-q[data-why="sun:1"]')
        drv.size(390, 2600)
        time.sleep(0.6)
        narrow = drv.js(
            "return {sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth,"
            " table: (() => { const w = document.querySelector('.src-wrap'); return w ? [w.scrollWidth, w.clientWidth] : null; })(),"
            " over: Array.from(document.querySelectorAll('.why-result, .decision, .dec-site, .dec-case, .why-q')).filter(n => n.scrollWidth > n.clientWidth + 1).map(n => n.className)}"
        )
        check("390 px: why and decision panels cause no page overflow; the source table scrolls inside its own box", narrow["sw"] <= narrow["cw"] and narrow["table"] and narrow["table"][0] >= narrow["table"][1] and not narrow["over"], narrow)
        drv.js("window.scrollTo(0, document.getElementById('decision').getBoundingClientRect().top + window.scrollY - 10)")
        time.sleep(0.3)
        drv.shot(evidence / "s2_decision_390.png")
        drv.size(1440, 2400)
        time.sleep(0.4)

        # ===== 7. Live 30-day comparison equals the saved package =====
        drv.js("document.getElementById('playback-speed').value = 100; document.getElementById('playback-speed').dispatchEvent(new Event('input', {bubbles: true}))")
        set_select("#scenario", "practice-30d")
        click("#start-run")
        drv.wait("return state.live && state.partial && sharedSampleCount() >= 2", timeout=40)
        drv.wait("return state.live && !state.partial", timeout=240)
        live = drv.js(
            "return JSON.stringify({o: state.comparison.overlap, e: state.runs.map(r => r.payload.elapsed_seconds), n: state.runs.map(r => r.payload.samples.length),"
            " iv: state.runs.map(r => r.payload.intervals)})"
        )
        live = json.loads(live)
        saved = load(CASE30 / "comparison.json")
        check("live 30-day stream: overlap equals the saved package", live["o"] == saved["overlap"], {"live": live["o"]["sun_centre_clear_seconds"], "saved": saved["overlap"]["sun_centre_clear_seconds"]})
        check("live 30-day stream: per-site totals, sample counts and intervals equal the saved runs", live["e"] == [e30["elapsed_seconds"], m30["elapsed_seconds"]] and live["n"] == [721, 721] and live["iv"] == [e30["intervals"], m30["intervals"]], live["n"])
        text = why("sun:1")
        check("live run: Why panel reads the same result as the saved one", "2025-01-05T10:00:00Z" in text and "blocked" in text, text[:200])
        verdict = norm(".dec-verdict")
        check("live run: decision verdict matches the saved case (Yes, both sites)", verdict.startswith("Yes. Both sites"), verdict)
    finally:
        out = evidence / "s2_flow_check.json"
        out.write_text(json.dumps(results, indent=2) + "\n")
        drv.close()
    failed = [r for r in results if not r["pass"]]
    print(f"{len(results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


def state_why(drv) -> str | None:
    return drv.js("return state.why")


if __name__ == "__main__":
    sys.exit(main())
