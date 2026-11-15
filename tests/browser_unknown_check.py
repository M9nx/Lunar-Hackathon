#!/usr/bin/env python3
"""Browser acceptance check: Unknown carried from the raw Horizons row to the chart and the export.

Starts its own local server (not the 8766 one), drives the review UI headless, and compares what the page
shows with the engine's batch result. The QA case is SYNTHETIC: its Sun reply reads ``n.a.`` at 00:30 on a
15-minute grid, so the Sun lane must be Unknown from 00:15 to 00:45 (30 minutes) in the timeline, the window
list, the chart, the details and the downloaded export. Then the expanded real windows run through the same path.

    .venv/bin/python tests/browser_unknown_check.py
    .venv/bin/python tests/browser_unknown_check.py --skip-real      # QA case only

Needs chromedriver and chromium. Reuses the ``Driver`` class of builder/scripts/review_candidate_browser_check.py
(imported, not edited). Writes screenshots and ``browser_check.json`` under docs/evidence/unknown/.
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "builder" / "scripts"))

from review_candidate_browser_check import Driver  # noqa: E402

from lunar_navigator.catalog import build_catalog, default_roots, find_entry, root_path, scenario_for  # noqa: E402
from lunar_navigator.engine import run_from_scenario  # noqa: E402
from lunar_navigator.live_server import make_server  # noqa: E402

QA_NORTH = "qa-gap-north__20240601T000000Z__20240601T010000Z__900s"
QA_WINDOW_PREFIX = "qa-gap-"
MALAPERT_15M = "malapert-practice__20250103T000000Z__20250110T000000Z__900s"
SITE04_15M = "site04-p02-practice__20250103T000000Z__20250110T000000Z__900s"
REV = "browsercheck"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8771)
    parser.add_argument("--driver-port", type=int, default=9531)
    parser.add_argument("--profile", default="/tmp/lunar-unknown-profile")
    parser.add_argument("--evidence-dir", default=str(ROOT / "docs" / "evidence" / "unknown"))
    parser.add_argument("--skip-real", action="store_true")
    args = parser.parse_args()
    evidence = Path(args.evidence_dir)
    evidence.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []

    def check(name: str, ok: bool, detail=None) -> None:
        results.append({"check": name, "pass": bool(ok), "detail": detail})
        print(("PASS " if ok else "FAIL ") + name + (f" :: {detail}" if detail not in (None, "") else ""))

    roots = default_roots(ROOT, ROOT / "data")
    catalog = build_catalog(roots)

    def batch(entry_id: str, mode: str | None = None) -> dict:
        entry = find_entry(catalog, entry_id)
        scenario = scenario_for(entry)
        if mode:
            scenario = {**scenario, "horizon_mode": mode}
        return run_from_scenario(scenario, root_path(roots, entry["root_id"]), REV)

    server = make_server(ROOT, ROOT / "data", REV, args.port)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    drv = Driver(args.driver_port, 1440, 2400, args.profile)

    def norm(selector: str) -> str:
        return drv.js("const n = document.querySelector(arguments[0]); return n ? n.textContent.replace(/\\s+/g, ' ').trim() : null", selector)

    def pick(value: str, mode: str = "geometric_0deg") -> None:
        drv.js(
            "const s = document.getElementById('scenario'); s.value = arguments[0]; s.dispatchEvent(new Event('change', {bubbles: true}));"
            " const h = document.getElementById('horizon-mode'); h.value = arguments[1];",
            value,
            mode,
        )

    def run_to_end(timeout: float = 240) -> None:
        drv.js("document.getElementById('start-run').click()")
        drv.wait("return state.live && state.runs.length > 0", timeout=60)
        drv.wait("return state.live && !state.partial && !state.running", timeout=timeout)

    def lane(name: str) -> None:
        drv.js("document.querySelector(`.tool[data-key=\"lane\"][data-value=\"${arguments[0]}\"]`).click()", name)

    def exported() -> dict:
        drv.js(
            "window.__export = null; const a = document.querySelector('#live-export a.export');"
            " fetch(a.href).then(r => r.json()).then(j => { window.__export = j; });"
        )
        return drv.wait("return window.__export")

    def strip(result: dict) -> dict:
        return {k: result[k] for k in ("samples", "intervals", "elapsed_seconds", "run_id", "scenario")}

    def seconds(a: str, b: str) -> int:
        from datetime import datetime

        f = "%Y-%m-%dT%H:%M:%SZ"
        return int((datetime.strptime(b, f) - datetime.strptime(a, f)).total_seconds())

    try:
        drv.get(f"http://127.0.0.1:{args.port}/review-candidate/")
        drv.wait("return document.querySelectorAll('.sky-panel').length === 2")
        drv.wait("return catalogState.data && document.querySelectorAll('#scenario optgroup').length >= 2")
        groups = drv.js("return Array.from(document.querySelectorAll('#scenario optgroup')).map(g => g.label + ':' + g.children.length)")
        check("catalog fills the scenario picker", len(groups) >= 3, groups)
        check("synthetic cases are in their own labelled group", any("Synthetic QA" in g for g in groups), groups)

        # ===== 1. QA case: missing Sun angle at 00:30 =====
        expected = batch(QA_NORTH)
        pick("catalog:" + QA_NORTH)
        fields = drv.js("return [document.getElementById('cat-start').value, document.getElementById('cat-end').value, document.getElementById('cat-start').disabled]")
        check("catalog range defaults to the saved coverage", fields == ["2024-06-01T00:00:00Z", "2024-06-01T01:00:00Z", False], fields)
        info = norm("#cat-info")
        check("catalog info shows site, observer, cadence, gap and checksums", all(t in info for t in ("qa-gap-north", "SYNTHETIC", "every 15 min", "Sun 1", "SHA-256")), info[:240])
        run_to_end()
        lane("sun")
        got = drv.js("const r = state.runs[0].payload; return {samples: r.samples, intervals: r.intervals, elapsed_seconds: r.elapsed_seconds, run_id: r.run_id, scenario: r.scenario}")
        check("page result equals the engine batch result", got == strip(expected), {"run_id": got["run_id"]})

        # timeline
        segs = drv.js("return Array.from(document.querySelectorAll('#lanes .seg.unknown')).map(n => [n.dataset.utc, n.dataset.end])")
        check("timeline hatches one merged Unknown span 00:15 to 00:45", segs == [["2024-06-01T00:15:00Z", "2024-06-01T00:45:00Z"]], segs)
        check("the span is 30 minutes", seconds(*segs[0]) == 1800 if segs else False, segs)
        win = drv.js("return Array.from(document.querySelectorAll('#windows .win-open[data-state=\"unknown\"]')).map(n => n.textContent.replace(/\\s+/g, ' ').trim())")
        check("window list gives the duration and both reasons", len(win) == 1 and "30 min" in win[0] and "missing_right_endpoint" in win[0] and "missing_ephemeris" in win[0], win)

        # chart: band position and the broken trace
        geo = drv.js(
            "const bg = document.querySelector('#chart .ch-bg').getBoundingClientRect();"
            " const u = Array.from(document.querySelectorAll('#chart .ch-unknown')).map(n => n.getBoundingClientRect());"
            " return {x: bg.left, w: bg.width, bands: u.map(r => [r.left, r.width])}"
        )
        band = geo["bands"][0] if len(geo["bands"]) == 1 else None
        ok = band is not None and abs((band[0] - geo["x"]) / geo["w"] - 0.25) < 0.01 and abs(band[1] / geo["w"] - 0.5) < 0.01
        check("chart Unknown band covers 25% to 75% of the hour", ok, geo)
        d = drv.js("return Array.from(document.querySelectorAll('#chart .ch-trace')).map(n => n.getAttribute('d'))")
        check("chart trace is broken at the missing angle (two pieces, none at 00:30)", len(d) == 1 and d[0].count("M") == 2 and d[0].count("L") == 2, d)
        drv.js("move(2)")
        time.sleep(0.2)
        readout = norm("#readout")
        check("selected missing row shows Unknown, a reason and no invented margin", "Unknown" in readout and "missing_ephemeris" in readout and "no saved margin" in readout, readout[:240])
        check("no zero placed on the chart at the missing sample", drv.js("return document.querySelectorAll('#chart .ch-dot').length") == 0)
        why = drv.js("return explain(state.runs[0].payload.samples[2], 'sun')")
        check("explanation names the saved table, not a calculation", "no elevation" in why, why)
        drv.shot(evidence / "unknown_qa_sun.png")

        # result section: split bar, Unknown notice, lane breakdown, jump to the span
        notice = norm("#answers .res-unknown")
        check("result notice names Unknown per lane and says it is not clear or blocked",
              notice is not None and "Sun 30 min · Earth 0 h · Both 15 min" in notice and "not counted as clear or blocked" in notice, notice)
        split = drv.js("const b = document.querySelector('#answers .split'); return b ? {label: b.getAttribute('aria-label'), parts: Array.from(b.children).map(c => [c.className.split(' ').pop(), Math.round(parseFloat(c.style.width))])} : null")
        check("Sun split bar is 25% clear, 25% blocked, 50% Unknown", split is not None and split["parts"] == [["clear", 25], ["blocked", 25], ["unknown", 50]], split)
        rows = drv.js("return Array.from(document.querySelectorAll('#answers .res-break tbody tr')).map(r => Array.from(r.children).map(c => c.textContent.trim()).join('|'))")
        check("lane breakdown table: Sun, Earth, Both with Unknown separate", rows == ["Sun|15 min|15 min|30 min", "Earth|45 min|15 min|0 h", "Both|15 min|30 min|15 min"], rows)
        drv.js("document.querySelector('#answers .win-scroll').click()")
        time.sleep(0.4)
        sel = drv.js("return state.sel && [state.sel.lane, state.sel.start, state.sel.end, state.sel.state]")
        check("notice button selects the Unknown span on the timeline", sel == ["sun", "2024-06-01T00:15:00Z", "2024-06-01T00:45:00Z", "unknown"], sel)
        drv.js("window.scrollTo(0, 0)")
        drv.shot(evidence / "unknown_result_section.png")

        # per-lane counts in the details
        details = norm(".result-details")
        check("Unknown counted separately: Sun 30 min, Earth 0 h, Both 15 min", "Sun 30 min, Earth 0 h, Both 15 min" in details, details[:400])
        lane("both")
        both_segs = drv.js("return Array.from(document.querySelectorAll('#lanes .seg')).map(n => n.dataset.state + ' ' + n.dataset.utc.slice(11, 16) + '-' + n.dataset.end.slice(11, 16))")
        check("Both lane: clear, blocked, unknown, blocked", both_segs == ["clear 00:00-00:15", "blocked 00:15-00:30", "unknown 00:30-00:45", "blocked 00:45-01:00"], both_segs)
        drv.js("move(1)")
        both_note = drv.js("return explain(state.runs[0].payload.samples[1], 'both')")
        check("Earth blocker beats Sun Unknown at 00:15", "Earth centre is on or below" in both_note, both_note)
        drv.shot(evidence / "unknown_qa_both.png")

        # export
        out = exported()
        check("downloaded export equals the page and the batch result", strip(out) == strip(expected) and strip(out) == got)
        sun_unknown = [i for i in out["intervals"] if i["lane"] == "sun" and i["state"] == "unknown"]
        check(
            "export: same interval, reasons and 1800 s",
            [(i["start_utc"], i["end_utc"], i["reason"]) for i in sun_unknown]
            == [("2024-06-01T00:15:00Z", "2024-06-01T00:30:00Z", "missing_right_endpoint"), ("2024-06-01T00:30:00Z", "2024-06-01T00:45:00Z", "missing_ephemeris")]
            and sum(seconds(i["start_utc"], i["end_utc"]) for i in sun_unknown) == 1800,
        )
        check("export row for 00:30 has null angles and the raw n.a. line", out["samples"][2]["sun"]["elevation_deg"] is None and "n.a." in out["samples"][2]["sun"]["response_line"])

        # ===== 2. Terrain mode: no reviewed skyline =====
        pick("catalog:" + QA_NORTH, "terrain")
        run_to_end()
        lane("sun")
        terr = drv.js(
            "const r = state.runs[0].payload; return {mode: r.scenario.horizon_mode, terrain: r.terrain,"
            " states: r.samples.map(s => s.sun.state), reasons: r.samples.map(s => s.sun.reason),"
            " el: r.samples.map(s => s.sun.elevation_deg), hz: r.samples.map(s => s.sun.horizon_deg), mg: r.samples.map(s => s.sun.margin_deg)}"
        )
        check("terrain run: every Sun state Unknown with a terrain reason", terr["mode"] == "terrain" and set(terr["states"]) == {"unknown"} and terr["reasons"][0] == "terrain_not_reviewed", terr["reasons"])
        check("terrain run keeps the elevation and leaves horizon and margin blank", terr["el"] == [2.0, 0.4, None, -1.25, 0.0] and terr["hz"][0] is None and all(m is None for m in terr["mg"]), [terr["el"], terr["hz"], terr["mg"]])
        tsegs = drv.js("return Array.from(document.querySelectorAll('#lanes .seg')).map(n => n.dataset.state)")
        check("terrain timeline is one Unknown span", tsegs == ["unknown"], tsegs)
        heading = norm("#answers")
        check("terrain headline says Unknown, not 0 h of clearance", "Terrain mode" in heading and "Unknown" in heading and "0 h of Sun-centre" not in heading, heading[:260])
        verdict = norm("#dec-answer")
        check("terrain decision answer is Unknown, not No", verdict is not None and verdict.startswith("Unknown."), verdict)
        traces = drv.js("return Array.from(document.querySelectorAll('#chart .ch-trace')).map(n => n.getAttribute('d'))")
        zero_label = norm("#chart .ch-zero-label")
        check("terrain chart keeps the elevation trace and does not call 0° the horizon", len(traces) == 1 and traces[0].count("M") == 2 and "classifies" not in zero_label and "reference" in zero_label, [traces, zero_label])
        drv.js("move(0)")
        t_read = norm("#readout")
        check("terrain readout: Unknown, reason code, no horizon or margin", "terrain_not_reviewed" in t_read and "no horizon, no margin" in t_read, t_read[:260])
        t_details = norm(".result-details")
        check("terrain details name the reason", "terrain_not_reviewed" in t_details, t_details[-260:])
        drv.shot(evidence / "unknown_qa_terrain.png")
        t_out = exported()
        check("terrain export carries the same result and the terrain block", t_out["terrain"]["reason"] == "terrain_not_reviewed" and strip(t_out) == strip(batch(QA_NORTH, "terrain")))
        pick("catalog:" + QA_NORTH, "geometric_0deg")

        # ===== 3. QA two-site shared window =====
        qa_window = next(w for w in catalog["comparisons"] if w["a"].startswith(QA_WINDOW_PREFIX))
        pick("window:" + qa_window["id"])
        run_to_end()
        lane("sun")
        two = drv.js("return state.runs.map(r => r.payload.elapsed_seconds)")
        check("two-site QA window: Sun Unknown 1800 s at A only", two[0]["sun"]["unknown"] == 1800 and two[1]["sun"]["unknown"] == 0, [e["sun"] for e in two])
        unk = drv.js("return state.comparison.overlap.unknown_seconds")
        check("comparison counts Unknown beside the known overlap", unk["site_a"]["sun"] == 1800 and unk["site_a"]["both"] == 900 and unk["site_b"]["sun"] == 0, unk)
        drv.shot(evidence / "unknown_qa_two_site.png")

        # ===== 4. Range validation reaches the user =====
        pick("catalog:" + QA_NORTH)
        drv.js("document.getElementById('cat-start').value = '2024-06-01T00:07:00Z'; document.getElementById('start-run').click()")
        drv.wait("return /Failed to start/.test(document.getElementById('run-status').textContent)", timeout=20)
        check("an off-grid range is refused with the reason", "grid" in norm("#run-status") or "step" in norm("#run-status"), norm("#run-status"))

        if not args.skip_real:
            # ===== 5. Expanded real windows =====
            drv.get(f"http://127.0.0.1:{args.port}/review-candidate/")
            drv.wait("return catalogState.data && document.querySelectorAll('#scenario optgroup').length >= 2")
            real = batch(MALAPERT_15M)
            pick("catalog:" + MALAPERT_15M)
            drv.js("document.getElementById('start-run').click()")
            drv.wait("return state.live && state.partial && sharedSampleCount() >= 12", timeout=60)
            lane("both")
            pend = drv.js(
                "const cut = document.querySelector('#chart .ch-cutoff'); const pend = document.querySelector('#chart .ch-pending');"
                " const path = document.querySelector('#chart .ch-trace');"
                " return {cut: !!cut, pend: !!pend, unknown: document.querySelectorAll('#chart .ch-unknown').length,"
                " label: (document.querySelector('#chart .ch-band-pending') || {}).textContent || '', n: sharedSampleCount(),"
                " cutX: cut ? Number(cut.getAttribute('x1')) : null,"
                " lastX: Number(path.getAttribute('d').trim().split(' ').slice(-2)[0].replace(/[ML]/g, ''))}"
            )
            check(
                "partial real run: Pending past the cutoff, not Unknown, chart drawn through the cutoff",
                pend["cut"] and pend["pend"] and pend["unknown"] == 0 and "Pending" in pend["label"] and abs(pend["lastX"] - pend["cutX"]) < 2,
                pend,
            )
            drv.shot(evidence / "unknown_real_pending.png")
            drv.wait("return state.live && !state.partial && !state.running", timeout=240)
            r_got = drv.js("const r = state.runs[0].payload; return {samples: r.samples, intervals: r.intervals, elapsed_seconds: r.elapsed_seconds, run_id: r.run_id, scenario: r.scenario}")
            check("real window: page result equals the engine batch result", r_got == strip(real), real["run_id"])
            earth = drv.js("return mergedStates(state.runs[0], 'earth').map(s => [s.state, s.start, s.end])")
            check(
                "Malapert Earth lane: blocked until 01-03 09:00, then clear (a crossing)",
                earth == [["blocked", "2025-01-03T00:00:00Z", "2025-01-03T09:00:00Z"], ["clear", "2025-01-03T09:00:00Z", "2025-01-10T00:00:00Z"]],
                earth,
            )
            both = drv.js("return mergedStates(state.runs[0], 'both').map(s => [s.state, s.start, s.end])")
            check(
                "Malapert Both lane: blocked, then clear from 01-05 09:30",
                both == [["blocked", "2025-01-03T00:00:00Z", "2025-01-05T09:30:00Z"], ["clear", "2025-01-05T09:30:00Z", "2025-01-10T00:00:00Z"]],
                both,
            )
            drv.shot(evidence / "unknown_real_malapert_both.png")
            real_window = next(w for w in catalog["comparisons"] if w["a"] == MALAPERT_15M and w["b"] == SITE04_15M)
            pick("window:" + real_window["id"])
            run_to_end()
            unk_secs = drv.js("return state.runs.map(r => ['sun','earth','both'].map(l => r.payload.elapsed_seconds[l].unknown))")
            check("real two-site window has no Unknown (no n.a. rows in real data)", all(v == 0 for row in unk_secs for v in row), unk_secs)
            site04 = batch(SITE04_15M)
            s_got = drv.js("return state.runs.map(r => r.payload.run_id)")
            check("no Unknown notice when nothing is Unknown", drv.js("return document.querySelectorAll('#answers .res-unknown').length") == 0)
            check("two-site window runs both exports through the same engine path", s_got == [real["run_id"], site04["run_id"]], s_got)
            drv.shot(evidence / "unknown_real_two_site.png")
    finally:
        drv.close()
        server.shutdown()

    failed = [r for r in results if not r["pass"]]
    (evidence / "browser_check.json").write_text(json.dumps({"server_revision": REV, "results": results}, indent=2) + "\n", encoding="utf-8")
    print(f"{len(results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
