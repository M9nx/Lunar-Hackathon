"use strict";

const PRACTICE_URL = "../replay/comparison.json";
const QA_URL = "qa-comparison.json";
const PRACTICE30_URL = "cases/practice-30d/comparison.json";
const PRACTICE_JAN_URL = "cases/practice-jan03-10/comparison.json";
/** Real saved-input cases the decision panel can compare. The QA fixture is synthetic and is not offered here. */
const CASES = [
  { id: "practice", url: PRACTICE_URL, label: "Practice, 48 h", button: "show-practice" },
  { id: "practice30", url: PRACTICE30_URL, label: "Practice, 30 days", button: "show-practice30" },
  { id: "jan03-10", url: PRACTICE_JAN_URL, label: "Practice, Jan 3–10", button: "show-jan03-10" },
];
const SITE_NAMES = {
  "site04-p02-practice-30d": "Site04",
  "malapert-practice-30d": "Malapert",
  "site04-p02-practice": "Site04",
  "site04-p02-practice-6h": "Site04, first 6 h",
  "malapert-practice": "Malapert",
  "qa-north": "QA North",
  "qa-south": "QA South",
};

const DEFAULT_CONTEXT_SITES = [
  { name: "Site04", longitude_east_deg: -156.4386, latitude_deg: -89.7812, role: "a" },
  { name: "Malapert", longitude_east_deg: -2.93, latitude_deg: -85.99, role: "b" },
];

const TERRAIN_PROFILE_URLS = {
  "site04-p02-practice-30d": "terrain/site04-p02-practice-dem240-horizon-diagnostic.json",
  "malapert-practice-30d": "terrain/malapert-practice-dem240-horizon-diagnostic.json",
  "site04-p02-practice": "terrain/site04-p02-practice-dem240-horizon-diagnostic.json",
  "site04-p02-practice-6h": "terrain/site04-p02-practice-dem240-horizon-diagnostic.json",
  "malapert-practice": "terrain/malapert-practice-dem240-horizon-diagnostic.json",
};

const state = {
  comparison: null,
  runs: [],
  index: 0,
  site: 0,
  lane: "sun",
  source: "practice",
  live: false,
  liveMode: null,
  partial: false,
  /** True from the Stop click until the engine reports the final cutoff. */
  stopping: false,
  /** How a live run ended early: { kind: "cancelled" | "failed", message, shared, cutoff, covered, delivered }. */
  runEnd: null,
  liveRunId: null,
  liveComparisonId: null,
  liveAbort: null,
  siteProgress: [0, 0],
  terrainProfiles: {},
  follow: true,
  view: { range: "15", trail: "off", grid: true, shade: true, labels: true, layout: "both", decimals: 6, terrain: "fill", peaks: true },
  stepSeconds: 0,
  running: false,
  playing: false,
  playTimer: null,
  preview: null,
  pvZoom: 1,
  runToken: 0,
  showTerrain: false,
  /** Selected window: { site, lane, start, end } from engine intervals, or null. */
  sel: null,
  /** Minimum clear-window length in hours for the screening filter. 0 means any length. */
  minHours: 0,
  /** Open "Why" question: "sun:0", "sun:1", "earth:0", "both" or "terrain". Null when closed. */
  why: null,
  /** Saved cases loaded for the decision panel: { [caseId]: { runs } }. */
  caseData: {},
  notice: "",
  pendingNotice: "",
};

function esc(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function show(value) {
  if (value === null || value === undefined) return "null";
  return String(value);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/** Server batch and pause are fixed. Playback speed only delays how fast results are shown. */
const LIVE_SERVER = { batch_size: 4, pause_seconds: 0.05 };

function playbackPace() {
  const raw = Number(document.getElementById("playback-speed")?.value ?? 55);
  const v = Math.max(0, Math.min(100, Number.isFinite(raw) ? raw : 55));
  if (v < 20) return { v, label: "Slowest", client_delay_ms: 700 };
  if (v < 40) return { v, label: "Slow", client_delay_ms: 260 };
  if (v < 70) return { v, label: "Normal", client_delay_ms: 90 };
  if (v < 90) return { v, label: "Fast", client_delay_ms: 15 };
  return { v, label: "Instant", client_delay_ms: 0 };
}

function syncPlaybackLabel() {
  const pace = playbackPace();
  const out = document.getElementById("playback-speed-label");
  const input = document.getElementById("playback-speed");
  if (out) out.textContent = pace.label;
  if (input) input.setAttribute("aria-valuetext", pace.label + ", display pacing only");
}

function siteName(run) {
  return SITE_NAMES[run.payload.scenario.site_id] || run.payload.scenario.site_id;
}

function parseUtc(iso) {
  return Date.parse(iso);
}

function sharedWindow() {
  const first = state.runs[0].payload.scenario;
  const mismatch = state.runs.some((run) => {
    const scenario = run.payload.scenario;
    return scenario.start_utc !== first.start_utc || scenario.end_utc !== first.end_utc || scenario.step_seconds !== first.step_seconds || scenario.horizon_mode !== first.horizon_mode;
  });
  return {
    mismatch,
    start: parseUtc(first.start_utc),
    end: parseUtc(first.end_utc),
    startUtc: first.start_utc,
    endUtc: first.end_utc,
    mode: first.horizon_mode,
  };
}

function sharedSampleCount() {
  if (!state.runs.length) return 0;
  if (state.liveMode === "comparison" && state.runs.length >= 2) {
    return Math.min(...state.runs.map((run) => run.payload.samples.length));
  }
  return state.runs[0].payload.samples.length;
}

function sampleAt(runIndex) {
  return state.runs[runIndex].payload.samples[state.index];
}

const TERRAIN_REASON_TEXT = {
  terrain_not_reviewed: "no reviewed skyline is saved for any observer",
  terrain_no_skyline_for_observer: "reviewed skylines exist, but none for this observer",
  terrain_review_incomplete: "the skyline for this observer has not completed review",
  terrain_gap_in_azimuth_bracket: "the reviewed skyline has a gap at this azimuth",
  terrain_insufficient_bins: "the reviewed skyline has too few azimuth bins",
};

function terrainMode() {
  return state.runs.length > 0 && state.runs[0].payload.scenario.horizon_mode === "terrain";
}

function isTerrainReason(reason) {
  return typeof reason === "string" && reason.startsWith("terrain_");
}

function terrainReasonText(reason) {
  return TERRAIN_REASON_TEXT[reason] || "terrain coverage or review is missing";
}

function explain(sample, lane) {
  if (lane === "both") {
    const reason = sample.both.reason;
    if (sample.both.state === "clear") return "Both centres are above the horizon at this sample.";
    if (sample.both.state === "blocked") {
      if (reason === "centre_below_or_on_horizon:earth") return "The Earth centre is on or below the horizon, so both centres are not clear.";
      if (reason === "centre_below_or_on_horizon:sun") return "The Sun centre is on or below the horizon, so both centres are not clear.";
      if (reason === "centre_below_or_on_horizon:sun+earth") return "The Sun centre and the Earth centre are each on or below the horizon.";
      return "At least one centre is on or below the horizon, so both centres are not clear.";
    }
    if (isTerrainReason(reason)) return "Terrain mode: Both is Unknown because " + terrainReasonText(reason) + ". The elevations are the saved Horizons values; no horizon or margin is shown.";
    if (reason === "missing_ephemeris") return "A saved elevation is missing, and neither centre is blocked, so both is Unknown.";
    if (reason === "missing_right_endpoint") return "The next sample has no usable angle, so this span is Unknown for both.";
    return "Both is Unknown. Saved reason: " + (reason || "not stated") + ".";
  }
  const item = sample[lane];
  const name = lane === "sun" ? "Sun centre" : "Earth centre";
  if (item.state === "unknown" && isTerrainReason(item.reason)) {
    return "The " + name + " elevation is " + show(item.elevation_deg) + "° (saved). No horizon is available because " + terrainReasonText(item.reason)
      + ". The state is Unknown; no horizon or margin is shown, and the 0° baseline is not substituted.";
  }
  if (item.state === "unknown") {
    const numbers = item.elevation_deg === null || item.elevation_deg === undefined
      ? "The saved table has no elevation for the " + name + "."
      : "The " + name + " elevation is " + show(item.elevation_deg) + "° and the horizon is " + show(item.horizon_deg) + "°.";
    if (item.reason === "missing_right_endpoint") return numbers + " The next sample has no usable angle, so this span is Unknown.";
    if (item.reason === "missing_ephemeris") return numbers + " This sample is Unknown.";
    return numbers + " The state is Unknown. Saved reason: " + (item.reason || "not stated") + ".";
  }
  if (item.state === "clear") {
    return "The " + name + " is " + show(item.margin_deg) + "° above the " + show(item.horizon_deg) + "° horizon, so the state is clear.";
  }
  if (item.margin_deg === 0) {
    return "The " + name + " is exactly on the " + show(item.horizon_deg) + "° horizon, so the state is blocked.";
  }
  const below = item.margin_deg === null || item.margin_deg === undefined ? "null" : show(Math.abs(item.margin_deg));
  return "The " + name + " is " + below + "° below the " + show(item.horizon_deg) + "° horizon, so the state is blocked.";
}

function caseLabel() {
  if (state.comparison && state.comparison.qa_fixture) return "QA fixture · synthetic";
  if (state.live) return "Live calculation · practice";
  if (state.source === "practice30") return "Practice · 30 days";
  if (state.source === "jan03-10") return "Practice · Jan 3–10";
  return "Practice";
}

/** Latest UTC that every site has resolved. Null before the first shared sample. */
function sharedCutoffUtc() {
  const n = sharedSampleCount();
  return n ? state.runs[0].payload.samples[n - 1].timestamp_utc : null;
}

/** Compact scenario bar: sites, UTC range, sample step, mode, and the case labels. */
function scenarioBarHtml() {
  if (!state.runs.length) return "";
  const win = sharedWindow();
  const sc = state.runs[0].payload.scenario;
  const names = state.runs
    .map((run, i) => `<span class="sc-site">${slotBadge(i)} <strong>${esc(siteName(run))}</strong></span>`)
    .join('<span class="sc-vs" aria-hidden="true">vs</span>');
  const terrainInfo = state.runs[0].payload.terrain;
  const mode = win.mode === "geometric_0deg"
    ? "Geometric 0°"
    : win.mode === "terrain"
      ? "Terrain · " + (terrainInfo && terrainInfo.status === "reviewed" ? "reviewed skyline" : "Unknown (" + ((terrainInfo && terrainInfo.reason) || "not reviewed") + ")")
      : String(win.mode);
  const span = (win.end - win.start) / 1000;
  return `
    <div class="sc-item sc-sites"><span class="sc-k">Sites</span><span class="sc-v">${names}</span></div>
    <div class="sc-item"><span class="sc-k">UTC range</span><span class="sc-v">${esc(shortUtc(win.startUtc))} → ${esc(shortUtc(win.endUtc))} · ${esc(fmtDuration(span))}</span></div>
    <div class="sc-item"><span class="sc-k">Sample step</span><span class="sc-v">${esc(fmtDuration(sc.step_seconds))}</span></div>
    <div class="sc-item"><span class="sc-k">Mode</span><span class="sc-v">${esc(mode)}</span></div>`;
}

/** Whole-window clear seconds per site for the two headline measures. Two sites use the engine overlap block. */
function headlineSeconds() {
  if (state.runs.length >= 2) {
    const o = state.comparison.overlap;
    return {
      sun: [o.sun_centre_clear_seconds.site_a, o.sun_centre_clear_seconds.site_b],
      both: [o.both_centres_clear_seconds.site_a, o.both_centres_clear_seconds.site_b],
      sunDelta: o.sun_centre_clear_seconds.delta_b_minus_a,
      bothDelta: o.both_centres_clear_seconds.delta_b_minus_a,
    };
  }
  const e = state.runs[0].payload.elapsed_seconds;
  return { sun: [e.sun.clear], both: [e.both.clear], sunDelta: null, bothDelta: null };
}

const SHORT_LANE = { sun: "Sun", earth: "Earth", both: "Both" };

/** One lane's whole-window split. Unknown stays its own part: it is never folded into clear or blocked. */
function splitHtml(e, label) {
  const total = e.clear + e.blocked + e.unknown;
  if (!total) return "";
  const parts = [["clear", "Clear", e.clear], ["blocked", "Blocked", e.blocked], ["unknown", "Unknown", e.unknown]];
  const aria = `${label}: ${parts.map(([, word, v]) => word + " " + fmtDuration(v)).join(", ")}`;
  const bar = parts
    .filter(([, , v]) => v > 0)
    .map(([cls, word, v]) => `<span class="split-seg chip ${cls}" style="width:${((v / total) * 100).toFixed(3)}%" title="${esc(word + " " + fmtDuration(v))}"></span>`)
    .join("");
  const legend = parts.map(([cls, word, v]) => `<span class="sl ${cls}${v ? "" : " is-zero"}">${word} ${esc(fmtDuration(v))}</span>`).join("");
  return `<div class="split" role="img" aria-label="${esc(aria)}">${bar}</div><p class="split-legend">${legend}</p>`;
}

/** Sun, Earth and Both for every site: clear, blocked and Unknown side by side. */
function breakdownHtml() {
  const two = state.runs.length >= 2;
  const rows = state.runs.map((run, i) => ["sun", "earth", "both"].map((lane) => {
    const e = run.payload.elapsed_seconds[lane];
    return `<tr class="${e.unknown ? "has-unknown" : ""}">${two ? `<th scope="row">${slotBadge(i)} ${esc(siteName(run))}</th>` : ""}<td>${esc(SHORT_LANE[lane])}</td>
      <td>${esc(fmtDuration(e.clear))}</td><td>${esc(fmtDuration(e.blocked))}</td><td class="${e.unknown ? "unk-val" : ""}">${esc(fmtDuration(e.unknown))}</td></tr>`;
  }).join("")).join("");
  return `<table class="res-break"><caption>${state.partial ? "So far, by lane" : "Whole window, by lane"} · Clear + Blocked + Unknown = the requested time</caption>
    <thead><tr>${two ? '<th scope="col">Site</th>' : ""}<th scope="col">Lane</th><th scope="col">Clear</th><th scope="col">Blocked</th><th scope="col">Unknown</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

/** Callout shown only when some lane has Unknown time. Names the amount per lane and jumps to the first Unknown span. */
function unknownNoticeHtml(terrainUnknown) {
  const per = state.runs.map((run) => {
    const e = run.payload.elapsed_seconds;
    return { run, e, total: e.sun.unknown + e.earth.unknown + e.both.unknown };
  });
  if (!per.some((p) => p.total > 0)) return "";
  const names = state.runs.map(siteName);
  const lines = per
    .map((p, i) => `${names[i]}: Sun ${fmtDuration(p.e.sun.unknown)} · Earth ${fmtDuration(p.e.earth.unknown)} · Both ${fmtDuration(p.e.both.unknown)}`)
    .join(" | ");
  let buttons = "";
  if (!terrainUnknown) {
    buttons = per.map((p, i) => {
      const lane = ["sun", "earth", "both"].find((l) => p.e[l].unknown > 0);
      if (!lane) return "";
      const span = mergedStates(p.run, lane).find((m) => m.state === "unknown");
      if (!span) return "";
      const why = span.reasons.length ? ` (${span.reasons.join(", ")})` : "";
      return `<button type="button" class="mini win-open win-scroll" data-site="${i}" data-lane="${lane}" data-utc="${esc(span.start)}" data-end="${esc(span.end)}" data-state="unknown">Show ${SHORT_LANE[lane]} Unknown on the timeline${state.runs.length > 1 ? " · " + esc(names[i]) : ""}: ${esc(compactUtc(span.start))} → ${esc(compactUtc(span.end))}${esc(why)}</button>`;
    }).join("");
  }
  const lead = terrainUnknown
    ? "Terrain mode: no reviewed skyline, so the whole window is Unknown."
    : `Unknown time${state.partial ? " so far" : " in this window"}, counted separately.`;
  return `<div class="res-unknown" role="note"><p><strong>${esc(lead)}</strong> ${esc(lines)}. Unknown is not counted as clear or blocked.</p>${buttons ? `<p class="res-unknown-go">${buttons}</p>` : ""}</div>`;
}

function answerHtml() {
  if (!state.comparison || !state.runs.length) return "";
  const two = state.runs.length >= 2;
  const names = state.runs.map(siteName);
  const { sun, both } = headlineSeconds();
  const partial = state.partial;
  const cutoff = sharedCutoffUtc();
  let lead;
  if (!two) {
    lead = `${names[0]} ${partial ? "has so far" : "had"} ${fmtDuration(sun[0])} of Sun-centre clearance.`;
  } else if (sun[0] === sun[1]) {
    lead = `${names[0]} and ${names[1]} ${partial ? "have" : "had"} the same Sun-centre clearance.`;
  } else {
    const more = sun[0] > sun[1] ? 0 : 1;
    lead = `${names[more]} ${partial ? "has" : "had"} more Sun-centre clearance than ${names[1 - more]}, by ${fmtDuration(Math.abs(sun[0] - sun[1]))}.`;
  }
  const terrainUnknown = terrainMode() && state.runs.every((run) => !run.payload.terrain || run.payload.terrain.status !== "reviewed");
  if (terrainUnknown) {
    lead = `Terrain mode: every state is Unknown (${(state.runs[0].payload.terrain && state.runs[0].payload.terrain.reason) || "terrain_not_reviewed"}). No clear or blocked time is reported.`;
  }
  const unknownSun = state.runs.map((run) => run.payload.elapsed_seconds.sun.unknown);
  const cards = names
    .map((name, i) => `<article class="site-num"><span class="sn-name">${slotBadge(i)} ${esc(name)}</span><strong class="sn-val">${esc(terrainUnknown ? "Unknown" : fmtDuration(sun[i]))}</strong>${terrainUnknown ? `<span class="sn-sub">${esc(fmtDuration(unknownSun[i]))} Unknown</span>` : ""}${splitHtml(state.runs[i].payload.elapsed_seconds.sun, name + " Sun centre")}</article>`)
    .join("");
  const joint = terrainUnknown
    ? "Both centres clear · Unknown (terrain)"
    : two && both.every((v) => v === 0)
    ? "Both centres clear · 0 h at either site"
    : "Both centres clear · " + names.map((name, i) => `${name} ${fmtDuration(both[i])}`).join(" · ");
  let status = "";
  if (partial && state.runEnd) {
    const end = state.runEnd;
    const verb = end.kind === "failed" ? "Failed" : "Stopped";
    status = `<p class="qa-banner res-status" role="status"><strong>${verb}. Incomplete run.</strong> Partial result through <strong>${esc(end.cutoff || "—")}</strong> (${esc(end.shared)} shared samples; totals cover through ${esc(end.covered || end.cutoff || "—")}). Only the shared resolved interval is counted. Not exportable.${end.kind === "failed" && end.message ? " " + esc(end.message) + "." : ""}</p>`;
  } else if (partial && state.stopping) {
    status = `<p class="qa-banner res-status" role="status"><strong>Stopping.</strong> These totals are not final until the engine reports the final cutoff.</p>`;
  } else if (partial) {
    status = `<p class="qa-banner res-status">Partial totals through <strong>${esc(cutoff || "—")}</strong>. Only the shared resolved interval is counted. Pending samples are not Unknown.</p>`;
  } else if (state.comparison.qa_fixture) {
    status = '<p class="qa-banner res-status">QA fixture. These hours are synthetic. They are not the January practice result.</p>';
  }
  return `
    <h1 id="result-heading" class="result-title">Sun-centre clearance</h1>
    <p class="result-sub">${partial ? "Partial window" : "Whole window"} · ${terrainMode() ? "centre-ray against a reviewed terrain skyline (none available)" : "centre-ray against geometric 0°"}</p>
    ${status}
    <div class="result-pair${two ? "" : " is-single"}">${cards}</div>
    <p class="result-lead">${esc(lead)}</p>
    <p class="result-joint">${esc(joint)}</p>
    ${unknownNoticeHtml(terrainUnknown)}
    ${breakdownHtml()}
    <p class="result-tags"><span class="demo-chip">${esc(caseLabel())}</span><span class="demo-chip soft">${terrainMode() ? "Terrain mode · Unknown" : "Terrain clearance unknown"}</span></p>`;
}

/** Raw seconds, sample counts, Unknown durations and the terrain reason code live behind Details. */
function answerDetailsHtml(open) {
  if (!state.comparison || !state.runs.length) return "";
  const two = state.runs.length >= 2;
  const names = state.runs.map(siteName);
  const { sun, both, sunDelta, bothDelta } = headlineSeconds();
  const secs = (arr) => arr.map((v, i) => `${names[i]} ${v} s`).join(" · ");
  const counts = state.runs.map((run, i) => `${names[i]} ${state.siteProgress[i] ?? run.payload.samples.length}`).join(" · ");
  const unknownFor = (u) => `Sun ${fmtDuration(u.sun)}, Earth ${fmtDuration(u.earth)}, Both ${fmtDuration(u.both)}`;
  let unknown;
  if (two) {
    const u = state.comparison.overlap.unknown_seconds;
    unknown = `${names[0]}: ${unknownFor(u.site_a)}. ${names[1]}: ${unknownFor(u.site_b)}.`;
  } else {
    const e = state.runs[0].payload.elapsed_seconds;
    unknown = `${names[0]}: ${unknownFor({ sun: e.sun.unknown, earth: e.earth.unknown, both: e.both.unknown })}.`;
  }
  const row = (k, v) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`;
  const rows = [
    row("Sun-centre clear, saved seconds", secs(sun) + (two ? ` · delta (${names[1]} − ${names[0]}) ${sunDelta} s` : "")),
    row("Both centres clear, saved seconds", secs(both) + (two ? ` · delta (${names[1]} − ${names[0]}) ${bothDelta} s` : "")),
    row("Samples", counts + (two ? ` · shared ${sharedSampleCount()}` : "")),
    row(terrainMode() ? "Unknown duration, terrain mode" : "Geometric Unknown duration", unknown),
    row("Terrain", terrainMode()
      ? "Terrain mode · " + (state.runs[0].payload.terrain ? state.runs[0].payload.terrain.reason + (state.runs[0].payload.terrain.detail ? " · " + state.runs[0].payload.terrain.detail : "") : "Unknown")
      : "Unknown · terrain_not_reviewed. No reviewed skyline is available. This is not the geometric Unknown duration."),
    row("Runs", state.runs.map((run, i) => `${names[i]} ${run.payload.run_id} (${run.payload.code_revision})`).join(" · ")),
  ].join("");
  return `<details class="result-details"${open ? " open" : ""}><summary>Details</summary><dl class="rd-grid">${rows}</dl></details>`;
}

/* ---------- Timeline: chart, lanes, margins, readout ---------- */

const BODY_COLOUR = { sun: "#f0cb8a", earth: "#8cc4f2" };
const PLAYHEAD_COLOUR = "#ff7ab6";

function laneBodies() {
  return state.lane === "both" ? ["sun", "earth"] : [state.lane];
}

/** Chart geometry in real pixels, so axis text stays readable on a 390 px screen. */
function chartBox() {
  const host = document.getElementById("chart");
  const measured = host ? Math.round(host.clientWidth) : 0;
  const W = Math.max(300, Math.min(1400, measured || 900));
  const narrow = W < 560;
  return {
    W,
    H: narrow ? 270 : Math.round(Math.max(280, Math.min(380, W * 0.3))),
    left: narrow ? 44 : 58,
    right: narrow ? 30 : 132,
    top: 22,
    bottom: 30,
    narrow,
  };
}

const pad2 = (n) => String(n).padStart(2, "0");

function tickLabel(ms) {
  const d = new Date(ms);
  const hh = d.getUTCHours();
  const mm = d.getUTCMinutes();
  if (!hh && !mm) return { text: pad2(d.getUTCMonth() + 1) + "-" + pad2(d.getUTCDate()), day: true };
  return { text: pad2(hh) + (mm ? ":" + pad2(mm) : "") + "Z", day: false };
}

function chartHtml() {
  const win = sharedWindow();
  if (win.mismatch) return '<p class="banner">The two runs do not share a window, so no shared elevation scale is drawn.</p>';
  const box = chartBox();
  state.chartBox = box;
  const { W, H, left, right, top, bottom, narrow } = box;
  const plotW = W - left - right;
  const plotH = H - top - bottom;
  const bodies = laneBodies();
  const series = [];
  state.runs.forEach((run, ri) => bodies.forEach((body) => series.push({ ri, body, run })));

  let lo = 0;
  let hi = 0;
  series.forEach((s) => s.run.payload.samples.forEach((sample) => {
    const e = sample[s.body].elevation_deg;
    if (typeof e !== "number") return;
    lo = Math.min(lo, e);
    hi = Math.max(hi, e);
  }));
  const padV = Math.max(0.3, (hi - lo) * 0.1);
  lo -= padV;
  hi += padV;
  const xOf = (ms) => left + ((ms - win.start) / (win.end - win.start)) * plotW;
  const yOf = (el) => top + ((hi - el) / (hi - lo)) * plotH;
  const zeroY = yOf(0);

  // Y ticks: whole-degree steps chosen so the labels never crowd.
  const ySteps = [0.5, 1, 2, 5, 10, 15, 20, 30, 45, 90];
  const maxY = Math.max(3, Math.floor(plotH / 40));
  const yStep = ySteps.find((s) => (hi - lo) / s <= maxY) || 90;
  let yGrid = "";
  for (let k = Math.ceil(lo / yStep); k <= Math.floor(hi / yStep); k += 1) {
    const v = k * yStep;
    const y = yOf(v);
    const text = v === 0 ? "0°" : (v > 0 ? "+" : "−") + Math.abs(v) + "°";
    yGrid += `<line class="ch-grid" x1="${left}" y1="${y.toFixed(1)}" x2="${left + plotW}" y2="${y.toFixed(1)}"></line>
      <text class="ch-axis${v === 0 ? " ch-axis-zero" : ""}" x="${left - 6}" y="${(y + 4).toFixed(1)}" text-anchor="end">${text}</text>`;
  }

  // X ticks: short UTC labels. Midnight shows the date.
  const tSteps = [30, 60, 120, 180, 360, 720, 1440, 2880].map((m) => m * 60000);
  const maxX = Math.max(3, Math.floor(plotW / 62));
  const tStep = tSteps.find((s) => (win.end - win.start) / s <= maxX) || tSteps[tSteps.length - 1];
  let xGrid = "";
  for (let t = Math.ceil(win.start / tStep) * tStep; t <= win.end; t += tStep) {
    const x = xOf(t);
    const lab = tickLabel(t);
    xGrid += `<line class="ch-grid${lab.day ? " ch-grid-day" : ""}" x1="${x.toFixed(1)}" y1="${top}" x2="${x.toFixed(1)}" y2="${top + plotH}"></line>
      <text class="ch-axis${lab.day ? " ch-axis-day" : ""}" x="${x.toFixed(1)}" y="${H - 11}" text-anchor="middle">${lab.text}</text>`;
  }

  // Scientific Unknown: crosshatch. Pending (not calculated yet): dotted, with a dashed cutoff line.
  let bands = "";
  state.runs.forEach((run, ri) => {
    mergedStates(run, state.lane).filter((s) => s.state === "unknown").forEach((s) => {
      const x0 = xOf(Math.max(s.startMs, win.start));
      const x1 = xOf(Math.min(s.endMs, win.end));
      bands += `<rect class="ch-unknown" x="${x0.toFixed(1)}" y="${top}" width="${Math.max(2, x1 - x0).toFixed(1)}" height="${plotH}"></rect>`;
      if (x1 - x0 > 64) bands += `<text class="ch-band-label ch-band-unknown" x="${(x0 + 5).toFixed(1)}" y="${top + 13 + ri * 12}">${SLOT_LABELS[ri]} Unknown</text>`;
    });
  });
  const cutoff = sharedCutoffUtc();
  if (state.partial && cutoff) {
    const cx = xOf(parseUtc(cutoff));
    bands += `<rect class="ch-pending" x="${cx.toFixed(1)}" y="${top}" width="${Math.max(0, left + plotW - cx).toFixed(1)}" height="${plotH}"></rect>
      <line class="ch-cutoff" x1="${cx.toFixed(1)}" y1="${top}" x2="${cx.toFixed(1)}" y2="${top + plotH}"></line>`;
    if (left + plotW - cx > 70) bands += `<text class="ch-band-label ch-band-pending" x="${(cx + 6).toFixed(1)}" y="${top + 13}">Pending · not Unknown</text>`;
  }

  // Selected window span.
  let selBand = "";
  if (state.sel && state.sel.lane === state.lane) {
    const x0 = xOf(Math.max(parseUtc(state.sel.start), win.start));
    const x1 = xOf(Math.min(parseUtc(state.sel.end), win.end));
    selBand = `<rect class="ch-sel" x="${x0.toFixed(1)}" y="${top}" width="${Math.max(3, x1 - x0).toFixed(1)}" height="${plotH}"></rect>
      <text class="ch-band-label ch-band-sel" x="${(x0 + 5).toFixed(1)}" y="${top + plotH - 7}">Selected window · ${SLOT_LABELS[state.sel.site]}</text>`;
  }

  const paths = series.map((s) => {
    let d = "";
    let drawing = false;
    s.run.payload.samples.forEach((sample) => {
      const e = sample[s.body].elevation_deg;
      if (typeof e !== "number") {
        drawing = false;
        return;
      }
      d += (drawing ? "L" : "M") + xOf(parseUtc(sample.timestamp_utc)).toFixed(1) + " " + yOf(e).toFixed(1) + " ";
      drawing = true;
    });
    return `<path class="ch-trace" d="${d}" fill="none" stroke="${BODY_COLOUR[s.body]}" stroke-width="${s.ri === state.site ? 2.8 : 1.9}"${s.ri === 0 ? "" : ' stroke-dasharray="8 5"'} clip-path="url(#ch-clip)"></path>`;
  }).join("");

  // Direct A/B labels at the end of each trace, nudged apart.
  const labels = series.map((s) => {
    const samples = s.run.payload.samples;
    let lastEl = null;
    for (let i = samples.length - 1; i >= 0; i -= 1) {
      if (typeof samples[i][s.body].elevation_deg === "number") {
        lastEl = samples[i][s.body].elevation_deg;
        break;
      }
    }
    if (lastEl === null) return null;
    const text = narrow
      ? SLOT_LABELS[s.ri] + (bodies.length > 1 ? (s.body === "sun" ? "S" : "E") : "")
      : bodies.length === 1
        ? SLOT_LABELS[s.ri] + " " + siteName(s.run)
        : SLOT_LABELS[s.ri] + " " + titleCase(s.body);
    return { text, body: s.body, y: yOf(lastEl) };
  }).filter(Boolean).sort((a, b) => a.y - b.y);
  for (let i = 1; i < labels.length; i += 1) {
    if (labels[i].y - labels[i - 1].y < 15) labels[i].y = labels[i - 1].y + 15;
  }
  const labelSvg = labels.map((l) => {
    const y = Math.min(top + plotH - 2, Math.max(top + 8, l.y));
    return `<text class="ch-label" x="${left + plotW + (narrow ? 4 : 9)}" y="${(y + 4).toFixed(1)}" fill="${BODY_COLOUR[l.body]}">${esc(l.text)}</text>`;
  }).join("");

  // Selected time: a solid pink line with a time pill, never mistaken for the dashed 0° horizon.
  const sample0 = sampleAt(0);
  const px = xOf(parseUtc(sample0.timestamp_utc));
  const dots = series.map((s) => {
    const sample = s.run.payload.samples[state.index];
    const e = sample ? sample[s.body].elevation_deg : null;
    if (typeof e !== "number") return "";
    return `<circle class="ch-dot" cx="${px.toFixed(1)}" cy="${yOf(e).toFixed(1)}" r="${s.ri === state.site ? 5.5 : 4.5}" fill="${BODY_COLOUR[s.body]}"></circle>`;
  }).join("");
  const pillDate = new Date(parseUtc(sample0.timestamp_utc));
  const pillText = { text: pad2(pillDate.getUTCHours()) + ":" + pad2(pillDate.getUTCMinutes()) + "Z" };
  const pillW = 56;
  const pillX = Math.min(left + plotW - pillW / 2, Math.max(left + pillW / 2, px));
  const zeroLabelY = zeroY - 7 > top + 12 ? zeroY - 7 : zeroY + 15;
  const terrainOn = terrainMode();
  const zeroLabel = terrainOn ? (narrow ? "0° reference" : "0° reference (not the horizon in terrain mode)") : narrow ? "0° horizon" : "0° horizon (classifies)";

  return `<svg class="chart" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="Elevation of the ${esc(laneBodies().join(" and "))} centre at each site against UTC. The dashed horizontal line is the 0 degree horizon. The pink vertical line is the selected UTC.">
    <defs>
      <pattern id="ch-below" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(-45)"><line x1="0" y1="0" x2="0" y2="9" stroke="#c9a15b" stroke-opacity="0.2" stroke-width="1"></line></pattern>
      <pattern id="ch-unknown" width="10" height="10" patternUnits="userSpaceOnUse"><path d="M0 0 L10 10 M10 0 L0 10" stroke="#c4b5fd" stroke-opacity="0.42" stroke-width="1" fill="none"></path></pattern>
      <pattern id="ch-pending" width="7" height="7" patternUnits="userSpaceOnUse"><circle cx="3.5" cy="3.5" r="0.9" fill="#8d9bb3" fill-opacity="0.6"></circle></pattern>
      <clipPath id="ch-clip"><rect x="${left}" y="${top}" width="${plotW}" height="${plotH}"></rect></clipPath>
    </defs>
    <rect class="ch-bg" x="${left}" y="${top}" width="${plotW}" height="${plotH}"></rect>
    <rect x="${left}" y="${zeroY.toFixed(1)}" width="${plotW}" height="${Math.max(0, top + plotH - zeroY).toFixed(1)}" fill="url(#ch-below)"></rect>
    ${bands}${selBand}
    ${yGrid}${xGrid}
    <line class="ch-zero" x1="${left}" y1="${zeroY.toFixed(1)}" x2="${left + plotW}" y2="${zeroY.toFixed(1)}"></line>
    <text class="ch-zero-label" x="${left + 8}" y="${zeroLabelY.toFixed(1)}">${zeroLabel}</text>
    ${paths}
    <line class="ch-play" x1="${px.toFixed(1)}" y1="${top}" x2="${px.toFixed(1)}" y2="${top + plotH}"></line>
    ${dots}
    <rect class="ch-pill" x="${(pillX - pillW / 2).toFixed(1)}" y="2" width="${pillW}" height="17" rx="2"></rect>
    <text class="ch-pill-text" x="${pillX.toFixed(1)}" y="14.5" text-anchor="middle">${esc(pillText.text)}</text>
    ${labelSvg}
  </svg>`;
}

function legendHtml() {
  const bodies = laneBodies();
  const sites = state.runs.map((run, i) => `<span class="lg-item"><i class="lg-trace${i ? " dashed" : ""}"></i> ${SLOT_LABELS[i]} ${esc(siteName(run))} ${i ? "dashed" : "solid"}</span>`).join("");
  const dots = bodies.map((b) => `<span class="lg-item"><i class="lg-dot lg-dot-${b}"></i> ${b === "sun" ? "Sun" : "Earth"} centre</span>`).join("");
  return `${sites}${dots}
    <span class="lg-item"><i class="lg-zero"></i> 0° horizon (classifies)</span>
    <span class="lg-item"><i class="lg-play"></i> Selected UTC</span>`;
}

function fraction(iso, window) {
  return (parseUtc(iso) - window.start) / (window.end - window.start);
}

function isDimmed(span, lane) {
  if (!state.minHours || span.state !== "clear") return false;
  return (span.endMs - span.startMs) / 1000 < state.minHours * 3600;
}

function isSelectedSpan(runIndex, lane, span) {
  const s = state.sel;
  return Boolean(s && s.site === runIndex && s.lane === lane && s.start === span.start);
}

/** One lane per site for the lane being shown. Selection, filter and pending all read the same engine spans. */
function lanesHtml() {
  const win = sharedWindow();
  if (win.mismatch) return "";
  const lane = state.lane;
  const play = fraction(sampleAt(0).timestamp_utc, win) * 100;
  const rows = state.runs.map((run, runIndex) => {
    const segments = mergedStates(run, lane).map((span) => {
      const left = fraction(span.start, win) * 100;
      const width = (fraction(span.end, win) - fraction(span.start, win)) * 100;
      const label = titleCase(span.state);
      const chosen = isSelectedSpan(runIndex, lane, span);
      const dim = isDimmed(span, lane);
      const cls = `seg ${span.state}${chosen ? " is-selected" : ""}${dim ? " is-dim" : ""}`;
      return `<button type="button" class="${cls}" style="left:${left}%;width:${width}%" data-site="${runIndex}" data-lane="${esc(lane)}" data-utc="${esc(span.start)}" data-end="${esc(span.end)}" data-state="${esc(span.state)}" aria-pressed="${chosen}" title="${esc(label)} ${esc(span.start)} to ${esc(span.end)}"><span>${esc(label)}</span></button>`;
    }).join("");
    const samples = run.payload.samples;
    const resolved = samples.length ? Math.min(100, fraction(samples[samples.length - 1].timestamp_utc, win) * 100) : 0;
    const pending = state.partial && resolved < 100
      ? `<span class="pending-zone" style="left:${resolved}%" title="Pending: not calculated yet. This is not Unknown."><span>Pending</span></span>`
      : "";
    const e = run.payload.elapsed_seconds[lane];
    const nKeep = mergedStates(run, lane).filter((s) => s.state === "clear" && qualifies(s)).length;
    const screen = state.minHours ? ` · ${nKeep || "no"} window${nKeep === 1 ? "" : "s"} of ${minLabel()} or longer` : "";
    return `<div class="lane-site${runIndex === state.site ? " is-selected" : ""}">
      <div class="lane-head"><span class="lane-name">${slotBadge(runIndex)} <strong>${esc(siteName(run))}</strong></span><span class="lane-sum">${esc(laneName(lane))} · clear ${esc(fmtDuration(e.clear))}${state.partial ? " so far" : ""}${e.unknown ? " · Unknown " + esc(fmtDuration(e.unknown)) : ""}${esc(screen)}</span></div>
      <div class="lane-track" data-site="${runIndex}">${segments}${pending}<span class="play-mark" style="left:${play}%"></span></div>
    </div>`;
  }).join("");
  return `${rows}
    <div class="swatches" aria-label="State patterns">
      <span class="swatch"><i class="chip clear"></i> Clear</span>
      <span class="swatch"><i class="chip blocked"></i> Blocked</span>
      <span class="swatch"><i class="chip unknown"></i> Unknown (no usable saved angle)</span>
      ${state.partial ? '<span class="swatch"><i class="chip pending"></i> Pending (not calculated yet)</span>' : ""}
    </div>`;
}

function marginText(item) {
  if (item && typeof item.margin_deg !== "number" && typeof item.elevation_deg === "number" && isTerrainReason(item.reason)) return "no horizon, no margin";
  if (!item || typeof item.margin_deg !== "number") return "no saved margin";
  return signedDeg(item.margin_deg) + "°";
}

/** Both lane: the two individual centre margins at the selected time, beside the joint state. */
function marginsHtml() {
  if (state.lane !== "both") return "";
  const samples = currentSamples();
  if (!samples.length || !samples[0]) return "";
  const rows = state.runs.map((run, i) => {
    const sample = samples[i];
    const cell = (item) => `<td><span class="state-word ${esc(item.state)}">${esc(item.state)}</span> <span class="mg-val">${esc(marginText(item))}</span></td>`;
    return `<tr class="${i === state.site ? "is-selected" : ""}"><th scope="row">${slotBadge(i)} ${esc(siteName(run))}</th>${cell(sample.sun)}${cell(sample.earth)}<td><span class="state-word ${esc(sample.both.state)}">${esc(sample.both.state)}</span></td></tr>`;
  }).join("");
  return `<table class="margins" aria-label="Centre margins at the selected time">
    <caption>Centre margins at ${esc(shortUtc(samples[0].timestamp_utc))}</caption>
    <thead><tr><th scope="col">Site</th><th scope="col">Sun centre</th><th scope="col">Earth centre</th><th scope="col">Both</th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

function selectionLine() {
  const s = state.sel;
  if (!s || !state.runs[s.site]) return "";
  const seconds = (parseUtc(s.end) - parseUtc(s.start)) / 1000;
  return `<p class="ro-sel"><strong>Selected window</strong> · ${slotBadge(s.site)} ${esc(siteName(state.runs[s.site]))} · ${esc(laneName(s.lane))} · ${esc(s.state)} · ${esc(shortUtc(s.start))} → ${esc(shortUtc(s.end))} · ${esc(fmtDuration(seconds))}</p>`;
}

/** Selected UTC, state and signed margin for each site, beside the playhead. */
function readoutHtml() {
  const samples = currentSamples();
  if (!samples.length || !samples[0]) return "";
  const lane = state.lane;
  const last = sharedSampleCount() - 1;
  const onTerminal = !state.partial && state.index === last;
  const chips = state.runs.map((run, i) => {
    const sample = samples[i];
    const item = lane === "both" ? sample.both : sample[lane];
    const margin = laneMargin(sample, lane);
    let sub = lane === "both"
      ? `smaller of two · Sun ${marginText(sample.sun)} · Earth ${marginText(sample.earth)}`
      : `${lane === "sun" ? "Sun" : "Earth"}-centre margin`;
    if (item.state === "unknown") sub = isTerrainReason(item.reason)
      ? `Unknown in terrain mode: ${item.reason}. The elevation is the saved value; there is no horizon or margin.`
      : `Unknown, not a clearance: ${item.reason || "no usable saved angle"}. Any margin shown is the saved sample value.`;
    return `<button type="button" class="ro-site${i === state.site ? " is-selected" : ""}" data-site="${i}" aria-pressed="${i === state.site}">
      <span class="ro-name">${slotBadge(i)} ${esc(siteName(run))}</span>
      <span class="status-pill status-${esc(item.state)}">${esc(titleCase(item.state))}</span>
      <span class="ro-margin">${esc(margin === null ? (isTerrainReason(item.reason) ? "no horizon, no margin" : "no saved margin") : signedDeg(margin) + "°")}</span>
      <span class="ro-sub">${esc(sub)}</span>
    </button>`;
  }).join("");
  const zero = onTerminal
    ? "Final sample: it adds 0 elapsed time."
    : state.partial
      ? `Partial run. The playhead stays inside the shared resolved samples (through ${shortUtc(sharedCutoffUtc() || "—")}). Pending is not Unknown.`
      : "";
  return `<div class="ro-top">
      <p class="ro-time"><span class="kicker">Selected UTC</span> <strong id="utc" class="utc">${esc(samples[0].timestamp_utc)}</strong></p>
    </div>
    <div class="ro-sites">${chips}</div>
    ${selectionLine()}
    <p id="zero-note" class="note ro-note${onTerminal ? " zero-on" : ""}">${esc(zero)}</p>
    ${state.notice ? `<p class="ro-notice" role="status">${esc(state.notice)}</p>` : ""}`;
}

/** One line for the sticky dock on narrow screens. */
function dockReadoutText() {
  const samples = currentSamples();
  if (!samples.length || !samples[0]) return "";
  const lane = state.lane;
  const parts = state.runs.map((run, i) => {
    const sample = samples[i];
    const item = lane === "both" ? sample.both : sample[lane];
    const margin = laneMargin(sample, lane);
    return `${SLOT_LABELS[i]} ${titleCase(item.state)} ${margin === null ? "—" : signedDeg(margin) + "°"}`;
  });
  return `${shortUtc(samples[0].timestamp_utc)} · ${parts.join(" · ")}`;
}

/* Sky plots: one linear elevation scale for every plot. Centre = +15°, 0° ring, edge = -15°. */
const SKY = { cx: 220, cy: 220, rEdge: 186, elCentre: 15, elEdge: -15 };
/** Elevation scales. Every plot uses the same one. Only "full" puts zenith at the centre. */
const SKY_RANGES = {
  "5": { centre: 5, edge: -5, rings: [3, 0, -3], label: "±5°" },
  "15": { centre: 15, edge: -15, rings: [10, 0, -10], label: "±15°" },
  "30": { centre: 30, edge: -30, rings: [20, 10, 0, -10, -20], label: "±30°" },
  full: { centre: 90, edge: -10, rings: [60, 30, 0, -10], label: "full sky" },
};

function applySkyRange() {
  const range = SKY_RANGES[state.view.range] || SKY_RANGES["15"];
  SKY.elCentre = range.centre;
  SKY.elEdge = range.edge;
  return range;
}

function degLabel(value) {
  return (value > 0 ? "+" : value < 0 ? "−" : "") + Math.abs(value) + "°";
}
const SLOT_LABELS = ["A", "B"];

function skyRadius(elevationDeg) {
  return (SKY.rEdge * (SKY.elCentre - elevationDeg)) / (SKY.elCentre - SKY.elEdge);
}

function skyXY(azimuthDeg, elevationDeg) {
  const raw = skyRadius(elevationDeg);
  const r = Math.min(SKY.rEdge, Math.max(0, raw));
  const rad = (azimuthDeg * Math.PI) / 180;
  return {
    x: SKY.cx + r * Math.sin(rad),
    y: SKY.cy - r * Math.cos(rad),
    offScale: raw < 0 || raw > SKY.rEdge,
  };
}

function terrainProfileForRun(run) {
  const siteId = run?.payload?.scenario?.site_id;
  return state.terrainProfiles[siteId] || null;
}

function interpolateHorizon(profile, azimuthDeg) {
  if (!profile?.bins?.length) return { horizon_deg: null, known: false };
  const az = ((azimuthDeg % 360) + 360) % 360;
  let best = profile.bins[0];
  let bestD = Infinity;
  for (const bin of profile.bins) {
    const d = Math.min(Math.abs(bin.azimuth_deg - az), 360 - Math.abs(bin.azimuth_deg - az));
    if (d < bestD) {
      bestD = d;
      best = bin;
    }
  }
  return best;
}

/* ---------- Terrain diagnostic drawing (DEM H(A), never changes a state) ---------- */

function terrainSorted(profile) {
  if (!profile._sorted) profile._sorted = profile.bins.slice().sort((a, b) => a.azimuth_deg - b.azimuth_deg);
  return profile._sorted;
}

function binKnown(bin) {
  return Boolean(bin && bin.known && typeof bin.horizon_deg === "number");
}

/**
 * Contiguous runs of known bins with azimuth unwrapped. One closed run when every bin is known.
 * Unknown bins split the skyline. They are never bridged or treated as 0°.
 */
function terrainRuns(profile) {
  if (!profile?.bins?.length) return [];
  const bins = terrainSorted(profile);
  const n = bins.length;
  const ok = bins.map(binKnown);
  if (ok.every(Boolean)) return [{ closed: true, pts: bins.map((b) => ({ az: b.azimuth_deg, h: b.horizon_deg })) }];
  if (!ok.some(Boolean)) return [];
  const start = ok.findIndex((v) => !v);
  const runs = [];
  let cur = null;
  for (let k = 1; k <= n; k += 1) {
    const i = (start + k) % n;
    if (!ok[i]) {
      cur = null;
      continue;
    }
    if (!cur) {
      cur = { closed: false, pts: [] };
      runs.push(cur);
    }
    cur.pts.push({ az: bins[i].azimuth_deg + (i < start ? 360 : 0), h: bins[i].horizon_deg });
  }
  return runs;
}

const f1 = (v) => v.toFixed(1);

function polyPath(xy, closed) {
  if (!xy.length) return "";
  return xy.map((p, i) => (i ? "L" : "M") + f1(p.x) + " " + f1(p.y)).join(" ") + (closed ? " Z" : "");
}

/** Catmull-Rom spline through the bin points. A visual aid only; "Raw bins" shows the saved values. */
function smoothPath(xy, closed) {
  const n = xy.length;
  if (n < 3) return polyPath(xy, closed);
  const at = (i) => (closed ? xy[(i + n) % n] : xy[Math.min(n - 1, Math.max(0, i))]);
  let d = "M" + f1(xy[0].x) + " " + f1(xy[0].y);
  const segments = closed ? n : n - 1;
  for (let i = 0; i < segments; i += 1) {
    const p0 = at(i - 1);
    const p1 = at(i);
    const p2 = at(i + 1);
    const p3 = at(i + 2);
    d += ` C${f1(p1.x + (p2.x - p0.x) / 6)} ${f1(p1.y + (p2.y - p0.y) / 6)} ${f1(p2.x - (p3.x - p1.x) / 6)} ${f1(p2.y - (p3.y - p1.y) / 6)} ${f1(p2.x)} ${f1(p2.y)}`;
  }
  return d + (closed ? " Z" : "");
}

/** Linear H at an azimuth between its two neighbouring bins. Null when either is unknown. */
function horizonLinear(profile, azimuthDeg) {
  if (!profile?.bins?.length) return null;
  const bins = terrainSorted(profile);
  const n = bins.length;
  const az = ((azimuthDeg % 360) + 360) % 360;
  let i = n - 1;
  for (let k = 0; k < n; k += 1) {
    if (bins[k].azimuth_deg <= az) i = k;
  }
  const b0 = bins[i];
  const b1 = bins[(i + 1) % n];
  if (!binKnown(b0) || !binKnown(b1)) return null;
  const span = ((b1.azimuth_deg - b0.azimuth_deg + 360) % 360) || 360;
  const t = (((az - b0.azimuth_deg) + 360) % 360) / span;
  return b0.horizon_deg + t * (b1.horizon_deg - b0.horizon_deg);
}

function rimCirclePath() {
  const { cx, cy, rEdge } = SKY;
  return `M ${cx - rEdge} ${cy} a ${rEdge} ${rEdge} 0 1 0 ${2 * rEdge} 0 a ${rEdge} ${rEdge} 0 1 0 ${-2 * rEdge} 0 Z`;
}

/** Highest and lowest known bins, the share of known azimuths above 0°, and the unknown azimuth span. */
function terrainStats(profile) {
  const bins = terrainSorted(profile);
  const known = bins.filter(binKnown);
  if (!known.length) return null;
  const step = profile.azimuth_step_deg || 2;
  const high = known.reduce((a, b) => (b.horizon_deg > a.horizon_deg ? b : a));
  const low = known.reduce((a, b) => (b.horizon_deg < a.horizon_deg ? b : a));
  const above = known.filter((b) => b.horizon_deg > 0).length;
  return { high, low, abovePct: (100 * above) / known.length, unknownDeg: (bins.length - known.length) * step, step };
}

function terrainStatsHtml(profile) {
  const s = terrainStats(profile);
  if (!s) return "";
  const range = typeof profile.max_range_m === "number" ? ` · out to ${Math.round(profile.max_range_m / 1000)} km` : "";
  return `<div class="terrain-stats" aria-label="DEM skyline summary, diagnostic">
    <span>High <b>${esc(signedDeg(s.high.horizon_deg))}°</b> at az ${esc(s.high.azimuth_deg.toFixed(0))}°</span>
    <span>Low <b>${esc(signedDeg(s.low.horizon_deg))}°</b> at az ${esc(s.low.azimuth_deg.toFixed(0))}°</span>
    <span>Above 0° over <b>${esc(s.abovePct.toFixed(0))}%</b> of known azimuths</span>
    <span>No DEM data <b>${esc(s.unknownDeg.toFixed(0))}°</b> of azimuth</span>
    <span>${esc(String(s.step))}° bins${esc(range)}</span>
  </div>`;
}

/**
 * Terrain layers for one sky plot. Returns defs (clip path, hatch is added by the caller) and body.
 * style: "fill" silhouette plus outline, "line" smooth outline, "bins" raw polyline with bin dots.
 * Skyline segments above the 0° ring use a second tint so the reader can see where the DEM rises over 0°.
 */
function terrainLayersHtml(profile, runIndex, bodies) {
  const style = state.view.terrain || "fill";
  const clipId = `sky-zero-clip-${runIndex}`;
  const hatchId = `sky-hatch-${runIndex}`;
  const r0 = skyRadius(0);
  const runs = terrainRuns(profile);
  let fills = "";
  let lines = "";
  let dots = "";
  runs.forEach((run) => {
    const xy = run.pts.map((p) => skyXY(p.az, p.h));
    const curve = style === "bins" ? polyPath(xy, run.closed) : smoothPath(xy, run.closed);
    lines += `<path class="sky-terrain-line" d="${curve}"></path>
      <path class="sky-terrain-line sky-terrain-line-hi" clip-path="url(#${clipId})" d="${curve}"></path>`;
    if (style === "bins") {
      dots += xy.map((p) => `<circle class="terr-dot" cx="${f1(p.x)}" cy="${f1(p.y)}" r="1.7"></circle>`).join("");
    }
    if (style !== "fill") return;
    let d;
    if (run.closed) {
      d = `${rimCirclePath()} ${curve}`;
    } else {
      const a0 = run.pts[0].az;
      const a1 = run.pts[run.pts.length - 1].az;
      d = curve;
      for (let a = a1; a > a0; a -= 2) {
        const e = skyXY(a, SKY.elEdge);
        d += ` L${f1(e.x)} ${f1(e.y)}`;
      }
      const e0 = skyXY(a0, SKY.elEdge);
      d += ` L${f1(e0.x)} ${f1(e0.y)} Z`;
    }
    fills += `<path class="sky-terrain-fill" fill-rule="evenodd" d="${d}"></path>
      <path class="sky-terrain-fill sky-terrain-fill-hi" fill-rule="evenodd" clip-path="url(#${clipId})" d="${d}"></path>`;
  });

  let marks = "";
  let labels = "";
  if (state.view.peaks) {
    const s = terrainStats(profile);
    if (s) {
      const extra = (bin, up) => {
        const p = skyXY(bin.azimuth_deg, bin.horizon_deg);
        if (p.offScale) return;
        const rad = (bin.azimuth_deg * Math.PI) / 180;
        const dir = up ? 1 : -1;
        const lx = p.x + dir * 13 * Math.sin(rad);
        const ly = p.y - dir * 13 * Math.cos(rad);
        const anchor = Math.abs(lx - SKY.cx) < 24 ? "middle" : lx > SKY.cx ? "start" : "end";
        marks += `<path class="terr-pk${up ? " terr-pk-high" : ""}" d="M${f1(p.x)} ${f1(p.y - 4.5)} l4 4.5 l-4 4.5 l-4 -4.5 Z"></path>`;
        labels += `<text class="terr-label" x="${f1(lx)}" y="${f1(ly + 3)}" text-anchor="${anchor}">${up ? "DEM high" : "DEM low"} ${esc(signedDeg(bin.horizon_deg))}° · az ${esc(bin.azimuth_deg.toFixed(0))}°</text>`;
      };
      // High label sits on the rim side of its marker, low label on the centre side, so neither crosses the N/E/S/W letters.
      extra(s.high, true);
      if (s.low !== s.high) extra(s.low, false);
    }
    bodies.forEach(({ key, marker, item }) => {
      if (!marker.p || typeof item.azimuth_deg !== "number") return;
      const h = horizonLinear(profile, item.azimuth_deg);
      if (h === null) return;
      const hp = skyXY(item.azimuth_deg, h);
      marks += `<line class="terr-leader terr-leader-${key}" x1="${f1(marker.p.x)}" y1="${f1(marker.p.y)}" x2="${f1(hp.x)}" y2="${f1(hp.y)}"></line>
        <circle class="terr-foot terr-foot-${key}" cx="${f1(hp.x)}" cy="${f1(hp.y)}" r="2.6"></circle>`;
    });
  }

  return {
    defs: `<clipPath id="${clipId}"><circle cx="${SKY.cx}" cy="${SKY.cy}" r="${r0.toFixed(1)}"></circle></clipPath>`,
    body: `<g class="sky-terrain">
      <g class="sky-gaps">${terrainGapWedges(profile, hatchId)}</g>
      ${fills}${lines}${dots}${marks}
    </g>`,
    labels,
  };
}

/** Hatched wedges for azimuths with no DEM data (Unknown, not zero). */
function terrainGapWedges(profile, hatchId) {
  if (!profile?.bins?.length) return "";
  const bins = profile.bins.slice().sort((a, b) => a.azimuth_deg - b.azimuth_deg);
  const step = profile.azimuth_step_deg || 2;
  const runs = [];
  let current = null;
  bins.forEach((bin) => {
    if (bin.known) {
      current = null;
      return;
    }
    if (current && bin.azimuth_deg - current.end <= step * 1.01) {
      current.end = bin.azimuth_deg;
    } else {
      current = { start: bin.azimuth_deg, end: bin.azimuth_deg };
      runs.push(current);
    }
  });
  return runs.map((run) => {
    const a0 = run.start - step / 2;
    const a1 = run.end + step / 2;
    let d = `M ${SKY.cx} ${SKY.cy}`;
    for (let a = a0; a < a1; a += 2) {
      const p = skyXY(a, SKY.elEdge);
      d += ` L ${p.x.toFixed(1)} ${p.y.toFixed(1)}`;
    }
    const e = skyXY(a1, SKY.elEdge);
    d += ` L ${e.x.toFixed(1)} ${e.y.toFixed(1)} Z`;
    return `<path class="sky-gap" d="${d}" fill="url(#${hatchId})"></path>`;
  }).join("");
}

async function loadTerrainProfiles() {
  const entries = Object.entries(TERRAIN_PROFILE_URLS);
  await Promise.all(entries.map(async ([siteId, url]) => {
    try {
      const response = await fetch(url);
      if (!response.ok) return;
      state.terrainProfiles[siteId] = await response.json();
    } catch (_error) {
      /* keep empty. The geometric view still works. */
    }
  }));
}

function fmtDeg(value) {
  if (typeof value !== "number") return "null";
  const abs = Math.abs(value);
  const text = abs !== 0 && abs < 0.01 ? abs.toFixed(6) : abs.toFixed(2);
  if (value < 0) return "−" + text;
  return text;
}

function dp() {
  return state.view.decimals;
}

/** Saved angles at the chosen number of decimals. Tiny non-zero values never collapse to 0.00. */
function signedDeg(value) {
  if (typeof value !== "number") return "null";
  let text = Math.abs(value).toFixed(dp());
  if (value !== 0 && Number(text) === 0) text = Math.abs(value).toFixed(6);
  return (value > 0 ? "+" : value < 0 ? "−" : "") + text;
}

function titleCase(word) {
  return word.charAt(0).toUpperCase() + word.slice(1);
}

/** "0 h" for zero, "min" when minutes are needed, seconds only for spans under an hour. */
function fmtDuration(seconds) {
  const total = Math.round(seconds);
  if (total === 0) return "0 h";
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const parts = [];
  if (h) parts.push(h + " h");
  if (m) parts.push(m + " min");
  if (s && !h) parts.push(s + " s");
  return parts.join(" ");
}

function shortUtc(iso) {
  return String(iso).replace(/:00Z$/, "Z");
}

/** Relative phrase for one body at one sample, for the plain-language verdict. */
function relPhrase(item) {
  if (!item) return "pending";
  const horizon = show(item.horizon_deg === undefined ? 0 : item.horizon_deg) + "°";
  if (item.state === "unknown") {
    return "Unknown (" + (item.reason || "no saved angle") + ")";
  }
  const margin = item.margin_deg;
  if (typeof margin !== "number") return "Unknown";
  if (margin === 0) return "exactly on " + horizon;
  return fmtDeg(Math.abs(margin)) + "° " + (margin > 0 ? "above " : "below ") + horizon;
}

function verdictHtml() {
  const samples = currentSamples();
  if (!samples.length || !samples[0]) return "";
  const names = state.runs.map(siteName);
  const sun = samples.map((s) => s && s.sun);
  const earth = samples.map((s) => s && s.earth);
  const both = samples.map((s) => s && s.both);
  const parts = [];
  if (samples.length === 1) {
    parts.push(`${names[0]}'s Sun centre is ${relPhrase(sun[0])}.`);
    parts.push(`Earth's centre is ${relPhrase(earth[0])}.`);
  } else {
    parts.push(`${names[0]}'s Sun centre is ${relPhrase(sun[0])}. ${names[1]}'s is ${relPhrase(sun[1])}.`);
    const known = earth.every((e) => e && e.state !== "unknown" && typeof e.margin_deg === "number");
    const direction = (e) => (e.margin_deg > 0 ? "above" : e.margin_deg < 0 ? "below" : "on");
    if (known && earth.every((e) => direction(e) === direction(earth[0]))) {
      const word = direction(earth[0]) === "on" ? "exactly on" : direction(earth[0]);
      parts.push(`Earth's centre is ${word} ${show(earth[0].horizon_deg)}° at both sites.`);
    } else {
      parts.push(`Earth's centre is ${relPhrase(earth[0])} at ${names[0]} and ${relPhrase(earth[1])} at ${names[1]}.`);
    }
  }
  const clearBoth = both.map((b, i) => (b && b.state === "clear" ? names[i] : null)).filter(Boolean);
  const bothText = clearBoth.length === 0
    ? "Neither site has both centres clear."
    : clearBoth.length === both.length
      ? "Both centres are clear at both sites."
      : `Both centres are clear at ${clearBoth.join(" and ")}.`;
  const sample = samples[0];
  const live = state.live && state.partial;
  return `<p class="verdict-time"><strong>${esc(sample.timestamp_utc)}</strong>${live ? " · selected sample, not the whole run" : ""}</p>
    <p class="verdict-text">${esc(parts.join(" "))} ${esc(bothText)}</p>
    <p class="verdict-basis">${terrainMode()
      ? "Terrain mode. Every state is Unknown until a reviewed skyline exists for the observer. Elevations are the saved Horizons values. No 0° baseline is substituted. The whole-window totals in the result above are a different measure."
      : "Centre-ray state against geometric 0°. Terrain clearance unknown. The whole-window totals in the result above are a different measure."}</p>`;
}

/** Merge adjacent intervals with the same state. Reasons can differ inside one state. */
function mergedStates(run, lane) {
  const out = [];
  run.payload.intervals
    .filter((interval) => interval.lane === lane)
    .slice()
    .sort((a, b) => parseUtc(a.start_utc) - parseUtc(b.start_utc))
    .forEach((interval) => {
      const last = out[out.length - 1];
      const startMs = parseUtc(interval.start_utc);
      const endMs = parseUtc(interval.end_utc);
      if (last && last.state === interval.state && last.endMs === startMs) {
        last.end = interval.end_utc;
        last.endMs = endMs;
        if (interval.reason && !last.reasons.includes(interval.reason)) last.reasons.push(interval.reason);
        return;
      }
      out.push({
        state: interval.state,
        start: interval.start_utc,
        end: interval.end_utc,
        startMs,
        endMs,
        reasons: interval.reason ? [interval.reason] : [],
      });
    });
  return out;
}

function nextChange(run, lane, nowIso) {
  const t = parseUtc(nowIso);
  const spans = mergedStates(run, lane);
  const index = spans.findIndex((span) => span.startMs <= t && t < span.endMs);
  if (index < 0 || index + 1 >= spans.length) return null;
  return { from: spans[index].state, to: spans[index + 1].state, start: spans[index + 1].start };
}

function laneMargin(sample, lane) {
  if (!sample) return null;
  if (lane === "both") {
    const a = sample.sun.margin_deg;
    const b = sample.earth.margin_deg;
    if (typeof a !== "number" || typeof b !== "number") return null;
    return Math.min(a, b);
  }
  const m = sample[lane].margin_deg;
  return typeof m === "number" ? m : null;
}

/** Saved sample whose unrounded margin is closest to 0°. Both uses the smaller of the two margins. */
function closestToZero(run, lane) {
  const count = Math.min(sharedSampleCount() || run.payload.samples.length, run.payload.samples.length);
  let best = null;
  for (let i = 0; i < count; i += 1) {
    const margin = laneMargin(run.payload.samples[i], lane);
    if (margin === null) continue;
    if (best === null || Math.abs(margin) < Math.abs(best.margin)) best = { index: i, margin };
  }
  return best;
}

function laneName(lane) {
  if (lane === "sun") return "Sun-centre clearance";
  if (lane === "earth") return "Earth-centre clearance";
  return "Both centres clear";
}

function resolvedEndUtc(run) {
  const samples = run.payload.samples;
  return samples.length ? samples[samples.length - 1].timestamp_utc : "—";
}

function lookNextHtml(run, runIndex, sample) {
  const rows = ["sun", "earth"].map((lane) => {
    const item = sample[lane];
    const change = nextChange(run, lane, sample.timestamp_utc);
    let tail;
    if (change) {
      tail = `Next change: ${change.to} at ${shortUtc(change.start)}. <button type="button" class="mini win-jump" data-site="${runIndex}" data-lane="${lane}" data-utc="${esc(change.start)}">Jump</button>`;
    } else {
      const spans = mergedStates(run, lane);
      const closest = spans.length <= 1 ? closestToZero(run, lane) : null;
      tail = `No change ${state.partial ? "yet in the resolved results" : "through " + shortUtc(run.payload.scenario.end_utc)}.`;
      if (closest) {
        tail += ` <button type="button" class="mini win-closest" data-site="${runIndex}" data-lane="${lane}">Closest to 0°</button>`;
      }
    }
    return `<li><strong>${lane === "sun" ? "Sun" : "Earth"}:</strong> ${tail}</li>`;
  }).join("");
  return `<ul class="look-next" aria-label="Where to look next at ${esc(siteName(run))}">${rows}</ul>`;
}

function slotBadge(runIndex) {
  return `<span class="slot-badge slot-${runIndex === 0 ? "a" : "b"}" aria-hidden="true">${SLOT_LABELS[runIndex]}</span>`;
}

function skyHtml() {
  const range = applySkyRange();
  const note = document.getElementById("scale-note");
  if (note) {
    note.textContent = `Both plots use the same angular scale. The dashed ring is 0°. The outer edge is ${degLabel(range.edge)}. The centre is ${degLabel(range.centre)}${range.centre === 90 ? " (zenith)" : ", not zenith"}.`;
  }
  const plots = state.runs.map((run, runIndex) => skyPlot(run, runIndex)).join("");
  return `<div class="sky-pair" data-layout="${esc(state.view.layout)}">${plots}</div>`;
}

/** Path of each body across the resolved samples. Past is solid, future is dotted. Dots mark 00/06/12/18 UTC. */
function trailHtml(run) {
  const mode = state.view.trail;
  if (mode === "off") return "";
  const count = sharedSampleCount();
  const samples = run.payload.samples.slice(0, count);
  const cur = Math.min(state.index, count - 1);
  let from = 0;
  let to = count - 1;
  if (mode === "window") {
    const perHour = 3600 / run.payload.scenario.step_seconds;
    from = Math.max(0, Math.round(cur - 6 * perHour));
    to = Math.min(count - 1, Math.round(cur + 6 * perHour));
  }
  return ["sun", "earth"].map((body) => {
    let past = "";
    let future = "";
    let dots = "";
    let drawP = false;
    let drawF = false;
    for (let i = from; i <= to; i += 1) {
      const item = samples[i][body];
      if (typeof item.azimuth_deg !== "number" || typeof item.elevation_deg !== "number") {
        drawP = false;
        drawF = false;
        continue;
      }
      const p = skyXY(item.azimuth_deg, item.elevation_deg);
      if (p.offScale) {
        drawP = false;
        drawF = false;
        continue;
      }
      const pt = `${p.x.toFixed(1)} ${p.y.toFixed(1)} `;
      if (i <= cur) { past += (drawP ? "L" : "M") + pt; drawP = true; }
      if (i >= cur) { future += (drawF ? "L" : "M") + pt; drawF = true; }
      const t = new Date(parseUtc(samples[i].timestamp_utc));
      if (t.getUTCMinutes() === 0 && t.getUTCSeconds() === 0 && t.getUTCHours() % 6 === 0) {
        dots += `<circle class="trail-dot" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="2"><title>${esc(samples[i].timestamp_utc)}</title></circle>`;
      }
    }
    return `<g class="trail trail-${body}" aria-hidden="true"><path class="trail-past" d="${past}"></path><path class="trail-future" d="${future}"></path>${dots}</g>`;
  }).join("");
}

const STATE_RING = {
  clear: { dash: "", colour: "#e8ebf1", width: 1.6 },
  blocked: { dash: "3 2.5", colour: "#c9a15b", width: 1.6 },
  unknown: { dash: "1 2.5", colour: "#cdbdfd", width: 1.8 },
};

/** Sun: disc with eight short rays. Earth: disc with two land shapes. A ring encodes state, so colour is not the only cue. */
function bodyGlyph(kind, state) {
  const ring = STATE_RING[state] || STATE_RING.unknown;
  const ringEl = `<circle class="mk-ring" r="${kind === "sun" ? 12.5 : 10.5}" fill="none" stroke="${ring.colour}" stroke-width="${ring.width}" stroke-dasharray="${ring.dash}"></circle>`;
  if (kind === "sun") {
    const rays = [0, 45, 90, 135, 180, 225, 270, 315]
      .map((a) => `<line class="mk-ray" x1="0" y1="-7.4" x2="0" y2="-10" transform="rotate(${a})"></line>`)
      .join("");
    return `${ringEl}<g class="mk-rays">${rays}</g><circle class="mk-dot" r="5.2"></circle>`;
  }
  return `${ringEl}<circle class="mk-dot" r="6.2"></circle>
    <path class="mk-land" d="M-4.4,-1.4 C-3.2,-4 -0.4,-4.6 1.2,-3.2 C1.6,-1.4 -0.2,-0.2 -1.4,0.8 C-2.8,0.6 -4.2,0 -4.4,-1.4Z M1.4,0.8 C3,0 4.8,1.2 4.4,2.8 C3.4,4.2 1.8,4 1,2.6 C0.8,1.8 1,1.2 1.4,0.8Z"></path>`;
}

function skyMarker(kind, item, runIndex) {
  if (typeof item.azimuth_deg !== "number" || typeof item.elevation_deg !== "number") return { mark: "", p: null };
  const p = skyXY(item.azimuth_deg, item.elevation_deg);
  const name = kind === "sun" ? "Sun" : "Earth";
  const off = p.offScale ? " (off scale)" : "";
  const label = `${name} ${signedDeg(item.elevation_deg)}°${off}`;
  const aria = `${name} centre ${item.state}: azimuth ${item.azimuth_deg}°, elevation ${item.elevation_deg}°, margin ${show(item.margin_deg)}°${off}. Press Enter for a preview.`;
  return {
    p,
    label,
    mark: `<g class="sky-marker sky-${kind} st-${esc(item.state)}${p.offScale ? " off-scale" : ""}" tabindex="0" role="button" data-site="${runIndex}" data-lane="${kind}" data-preview="body" data-body="${kind}" transform="translate(${p.x.toFixed(1)} ${p.y.toFixed(1)})" aria-label="${esc(aria)}">
      <title>${esc(name + " " + item.state + " · click for a preview")}</title>
      <circle class="mk-hit" r="16"></circle>
      ${bodyGlyph(kind, item.state)}
    </g>`,
  };
}

function fmt3(v) {
  return signedDeg(v);
}

function metricRow(label, value, unit) {
  return `<div><dt>${esc(label)}</dt><dd>${esc(value)}${unit && value !== "null" ? unit : ""}</dd></div>`;
}

/** Every saved metric for the selected sample, shown whether or not a stream is running. */
function metricsHtml(runIndex, sample, profile) {
  const cards = [["sun", "Sun centre", sample.sun], ["earth", "Earth centre", sample.earth]].map(([key, label, item]) => {
    const h = typeof item.azimuth_deg === "number" ? interpolateHorizon(profile, item.azimuth_deg) : null;
    const dem = h && h.known && typeof h.horizon_deg === "number" ? signedDeg(h.horizon_deg) : "no data";
    return `<button type="button" class="metric" data-site="${runIndex}" data-lane="${key}" data-preview="body" data-body="${key}" aria-label="${esc(label)} metrics. Open preview.">
      <span class="metric-head"><strong>${esc(label)}</strong><span class="status-pill status-${esc(item.state)}">${esc(titleCase(item.state))}</span></span>
      <dl>
        ${metricRow("Azimuth", typeof item.azimuth_deg === "number" ? item.azimuth_deg.toFixed(dp()) : "null", "°")}
        ${metricRow("Elevation", typeof item.elevation_deg === "number" ? fmt3(item.elevation_deg) : "null", "°")}
        ${metricRow("Horizon", show(item.horizon_deg), "°")}
        ${metricRow("Margin", fmt3(item.margin_deg), "°")}
        ${state.showTerrain ? metricRow("DEM (diagnostic)", dem, dem === "no data" ? "" : "°") : ""}
      </dl>
    </button>`;
  });
  const both = sample.both;
  cards.push(`<div class="metric metric-both">
    <span class="metric-head"><strong>Both centres</strong><span class="status-pill status-${esc(both.state)}">${esc(titleCase(both.state))}</span></span>
    <dl>
      ${metricRow("Sun margin", fmt3(sample.sun.margin_deg), "°")}
      ${metricRow("Earth margin", fmt3(sample.earth.margin_deg), "°")}
      ${metricRow("Reason", show(both.reason), "")}
    </dl>
  </div>`);
  return `<div class="metrics">${cards.join("")}</div>`;
}

function liveMeterHtml(runIndex) {
  if (!state.live) return "";
  const run = state.runs[runIndex];
  const total = expectedSamples(run);
  const done = state.siteProgress[runIndex] ?? run.payload.samples.length;
  const pending = Math.max(0, total - done);
  const pct = Math.min(100, (done / total) * 100);
  const latest = run.payload.samples.length ? run.payload.samples[run.payload.samples.length - 1].timestamp_utc : "—";
  const stateWord = state.partial ? "Streaming" : "Complete";
  return `<div class="plot-meter" data-streaming="${state.partial}">
    <span><strong>${stateWord}</strong> · ${esc(done)} of ${esc(total)} samples · ${pending ? esc(pending) + " pending, not Unknown" : "none pending"} · latest ${esc(shortUtc(latest))}</span>
    <i class="prog-bar"><b style="width:${pct.toFixed(1)}%"></b></i>
  </div>`;
}

function skyPlot(run, runIndex) {
  const sample = sampleAt(runIndex);
  const { cx, cy } = SKY;
  const streaming = state.live && state.partial;
  const selected = runIndex === state.site;
  const sun = sample.sun;
  const earth = sample.earth;
  const showTerrain = state.showTerrain;
  const profile = terrainProfileForRun(run);

  const rangeDef = SKY_RANGES[state.view.range] || SKY_RANGES["15"];
  const rings = rangeDef.rings.map((elev) => {
    const r = skyRadius(elev);
    const label = elev === 0 ? "0°" : degLabel(elev);
    return `<circle cx="${cx}" cy="${cy}" r="${r.toFixed(1)}" class="sky-ring${elev === 0 ? " sky-ring-geo" : ""}"></circle>
      <text x="${(cx + 4).toFixed(1)}" y="${(cy - r - 3).toFixed(1)}" class="sky-annote${elev === 0 ? " sky-annote-geo" : ""}">${label}</text>`;
  }).join("");
  const r0 = skyRadius(0);
  const below = `<path class="sky-below" fill-rule="evenodd" d="M ${cx - SKY.rEdge} ${cy} a ${SKY.rEdge} ${SKY.rEdge} 0 1 0 ${2 * SKY.rEdge} 0 a ${SKY.rEdge} ${SKY.rEdge} 0 1 0 ${-2 * SKY.rEdge} 0 Z M ${cx - r0} ${cy} a ${r0} ${r0} 0 1 1 ${2 * r0} 0 a ${r0} ${r0} 0 1 1 ${-2 * r0} 0 Z"></path>
    <text class="sky-annote" x="${cx}" y="${cy + SKY.rEdge - 8}" text-anchor="middle">below 0°</text>`;
  const ticks = Array.from({ length: 36 }, (_, i) => i * 10).map((az) => {
    const major = az % 90 === 0;
    const a = skyXY(az, SKY.elEdge);
    const rad = (az * Math.PI) / 180;
    const len = major ? 9 : az % 30 === 0 ? 6 : 3;
    return `<line class="sky-tick${major ? " sky-tick-major" : ""}" x1="${a.x.toFixed(1)}" y1="${a.y.toFixed(1)}" x2="${(a.x - len * Math.sin(rad)).toFixed(1)}" y2="${(a.y + len * Math.cos(rad)).toFixed(1)}"></line>`;
  }).join("");
  const dirs = [[0, "N"], [90, "E"], [180, "S"], [270, "W"]].map(([az, lab]) => {
    const rad = (az * Math.PI) / 180;
    const r = SKY.rEdge + 15;
    return `<text class="sky-dir" x="${(cx + r * Math.sin(rad)).toFixed(1)}" y="${(cy - r * Math.cos(rad)).toFixed(1)}" text-anchor="middle" dominant-baseline="middle">${lab}</text>`;
  }).join("");

  const sunM = skyMarker("sun", sun, runIndex);
  const earthM = skyMarker("earth", earth, runIndex);
  const labels = [];
  [sunM, earthM].forEach((m, i) => {
    if (!m.p) return;
    const right = m.p.x > cx;
    let dy = 4;
    const other = i === 1 ? sunM : null;
    if (other && other.p && Math.abs(other.p.x - m.p.x) < 80 && Math.abs(other.p.y - m.p.y) < 20) dy = 20;
    labels.push(`<text class="mk-label mk-label-${i === 0 ? "sun" : "earth"}" x="${(m.p.x + (right ? -18 : 18)).toFixed(1)}" y="${(m.p.y + dy).toFixed(1)}" text-anchor="${right ? "end" : "start"}">${esc(m.label)}</text>`);
  });
  const waves = streaming && sunM.p
    ? `<g class="sun-waves" transform="translate(${sunM.p.x.toFixed(1)} ${sunM.p.y.toFixed(1)})" aria-hidden="true">
        <circle class="sun-wave sun-wave-1" r="12"></circle>
        <circle class="sun-wave sun-wave-2" r="12"></circle>
      </g>`
    : "";

  let terrainNote = "";
  let terrainLayers = "";
  let terrainDefs = "";
  let terrainStatsBlock = "";
  if (showTerrain) {
    if (profile) {
      const layers = terrainLayersHtml(profile, runIndex, [
        { key: "sun", marker: sunM, item: sun },
        { key: "earth", marker: earthM, item: earth },
      ]);
      terrainLayers = layers.body;
      terrainDefs = layers.defs;
      terrainStatsBlock = terrainStatsHtml(profile);
      if (layers.labels) labels.push(layers.labels);
      const lines = [["Sun", sun], ["Earth", earth]].map(([name, item]) => {
        if (typeof item.azimuth_deg !== "number") return `${name}: no saved direction.`;
        const h = interpolateHorizon(profile, item.azimuth_deg);
        const dem = h.known && typeof h.horizon_deg === "number" ? signedDeg(h.horizon_deg) + "°" : "no DEM data";
        return `${name} ${signedDeg(item.elevation_deg)}° vs displayed DEM ${dem}.`;
      }).join(" ");
      terrainNote = `<p class="terrain-note">Diagnostic only, ${esc(profile.status || "unreviewed")}: ${esc(lines)} The state above is still classified against geometric 0°. Terrain stays Unknown.</p>`;
    } else {
      terrainNote = `<p class="terrain-note">No DEM profile is loaded for this site. Terrain stays Unknown.</p>`;
    }
  }

  return `<article class="sky-panel${selected ? " is-selected" : ""}" data-site="${runIndex}">
    <div class="sky-panel-head">
      <h3>${slotBadge(runIndex)} ${esc(siteName(run))}${selected ? ' <span class="sel-tag">selected</span>' : ""}</h3>
    </div>
    ${liveMeterHtml(runIndex)}
    <svg class="sky-svg" viewBox="0 0 440 440" role="img" aria-label="Polar sky for ${esc(siteName(run))}. Centre is ${rangeDef.centre} degrees elevation, the dashed ring is 0 degrees, the edge is ${rangeDef.edge} degrees.">
      <defs>
        ${terrainDefs}
        <pattern id="sky-hatch-${runIndex}" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(40)">
          <line x1="0" y1="0" x2="0" y2="6" stroke="#b7a6e8" stroke-width="1" opacity="0.55"></line>
        </pattern>
      </defs>
      <circle class="sky-disc" cx="${cx}" cy="${cy}" r="${SKY.rEdge}"></circle>
      <g class="sky-shade">${below}</g>
      <g class="sky-grid">${rings}${ticks}</g>
      ${trailHtml(run)}
      ${terrainLayers}
      <circle class="sky-geo-dash" cx="${cx}" cy="${cy}" r="${r0.toFixed(1)}"></circle>
      <path class="sky-centre" d="M ${cx - 5} ${cy} H ${cx + 5} M ${cx} ${cy - 5} V ${cy + 5}"></path>
      <text class="sky-annote sky-grid" x="${cx}" y="${cy + 17}" text-anchor="middle">centre ${degLabel(rangeDef.centre)}${rangeDef.centre === 90 ? " zenith" : ""}</text>
      ${dirs}
      ${waves}
      <g class="sky-labels">${labels.join("")}</g>
      ${sunM.mark}${earthM.mark}
    </svg>
    ${metricsHtml(runIndex, sample, profile)}
    ${lookNextHtml(run, runIndex, sample)}
    ${terrainStatsBlock}
    ${terrainNote}
  </article>`;
}

/* ---------- Preview card ---------- */

/** Small line chart of one lane's margin over the whole window. Shaded span and playhead optional. */
function sparkline(run, runIndex, lane, span) {
  const samples = run.payload.samples;
  const sc = run.payload.scenario;
  const t0 = parseUtc(sc.start_utc);
  const t1 = parseUtc(sc.end_utc);
  const W = 320;
  const H = 84;
  const pad = { l: 30, r: 6, t: 8, b: 16 };
  const vals = samples.map((s) => laneMargin(s, lane));
  const nums = vals.filter((v) => v !== null);
  if (!nums.length) return '<p class="muted">No saved margins to plot.</p>';
  let lo = Math.min(0, ...nums);
  let hi = Math.max(0, ...nums);
  const padv = Math.max(0.3, (hi - lo) * 0.12);
  lo -= padv;
  hi += padv;
  const x = (iso) => pad.l + ((parseUtc(iso) - t0) / (t1 - t0)) * (W - pad.l - pad.r);
  const y = (v) => pad.t + ((hi - v) / (hi - lo)) * (H - pad.t - pad.b);
  let d = "";
  let on = false;
  samples.forEach((s, i) => {
    if (vals[i] === null) { on = false; return; }
    d += (on ? "L" : "M") + x(s.timestamp_utc).toFixed(1) + " " + y(vals[i]).toFixed(1) + " ";
    on = true;
  });
  const shade = span
    ? `<rect class="sp-span" x="${x(span.start).toFixed(1)}" y="${pad.t}" width="${Math.max(2, x(span.end) - x(span.start)).toFixed(1)}" height="${H - pad.t - pad.b}"></rect>`
    : "";
  const cur = sampleAt(runIndex);
  const curV = cur ? laneMargin(cur, lane) : null;
  const playX = cur ? x(cur.timestamp_utc) : null;
  return `<svg class="spark" viewBox="0 0 ${W} ${H}" role="img" aria-label="Margin against 0 degrees across the window">
    ${shade}
    <line class="sp-zero" x1="${pad.l}" y1="${y(0).toFixed(1)}" x2="${W - pad.r}" y2="${y(0).toFixed(1)}"></line>
    <path class="sp-line" d="${d}"></path>
    ${playX !== null ? `<line class="sp-play" x1="${playX.toFixed(1)}" y1="${pad.t}" x2="${playX.toFixed(1)}" y2="${H - pad.b}"></line>` : ""}
    ${playX !== null && curV !== null ? `<circle class="sp-dot" cx="${playX.toFixed(1)}" cy="${y(curV).toFixed(1)}" r="3"></circle>` : ""}
    <text class="sp-axis" x="2" y="${(y(0) + 3).toFixed(1)}">0°</text>
    <text class="sp-axis" x="2" y="${(pad.t + 8).toFixed(1)}">${hi.toFixed(1)}</text>
    <text class="sp-axis" x="2" y="${H - pad.b}">${lo.toFixed(1)}</text>
    <text class="sp-axis" x="${pad.l}" y="${H - 3}">${esc(shortUtc(sc.start_utc).slice(5, 16))}</text>
    <text class="sp-axis" x="${W - pad.r}" y="${H - 3}" text-anchor="end">${esc(shortUtc(sc.end_utc).slice(5, 16))}</text>
  </svg>`;
}

function previewHtml() {
  const p = state.preview;
  if (!p || !state.runs[p.site] || sharedSampleCount() === 0) return "";
  const run = state.runs[p.site];
  const sample = sampleAt(p.site);
  if (!sample) return "";
  const name = siteName(run);
  if (p.kind === "body") {
    const item = sample[p.body];
    const row = (k, v) => `<div><dt>${esc(k)}</dt><dd>${esc(v)}</dd></div>`;
    return `<header class="pv-head">
        <div><p class="pv-kicker">${slotBadge(p.site)} ${esc(name)} · ${esc(item.label)}</p>
        <h3>${esc(p.body === "sun" ? "Sun" : "Earth")} centre <span class="status-pill status-${esc(item.state)}">${esc(titleCase(item.state))}</span></h3></div>
        <div class="pv-head-actions">${pvToolsHtml()}<button type="button" class="pv-close" aria-label="Close preview">✕</button></div>
      </header>
      <p class="pv-time">${esc(sample.timestamp_utc)} · follows the playhead</p>
      <p class="pv-text">${esc(explain(sample, p.body))}</p>
      <dl class="pv-grid">
        ${row("Azimuth", show(item.azimuth_deg) + "°")}${row("Elevation", show(item.elevation_deg) + "°")}
        ${row("Horizon", show(item.horizon_deg) + "°")}${row("Margin", show(item.margin_deg) + "°")}
        ${row("Reason", show(item.reason))}${row("Source", show(item.source_ref))}
      </dl>
      ${sparkline(run, p.site, p.body)}
      <p class="pv-foot">Centre-ray against geometric 0°. Terrain Unknown.</p>
      <div class="pv-actions"><button type="button" class="pv-evidence">Open evidence</button></div>`;
  }
  return evidencePreviewHtml(p, run, sample);
}

/** Exact saved row, source, observer and export for the selected sample. Follows the playhead. */
function evidencePreviewHtml(p, run, sample) {
  const lane = p.lane || state.lane;
  const observer = run.payload.scenario.observer;
  const rowName = state.comparison.qa_fixture ? "Synthetic row" : "Horizons row";
  const bodies = lane === "both" ? ["sun", "earth"] : [lane];
  const rows = bodies.map((body) => {
    const item = sample[body];
    return `<dt>${esc(item.label)} · azimuth</dt><dd>${esc(show(item.azimuth_deg))}°</dd>
      <dt>${esc(item.label)} · elevation, margin</dt><dd>${esc(show(item.elevation_deg))}°, ${esc(show(item.margin_deg))}°</dd>
      <dt>${esc(rowName)}</dt><dd><code>${esc(show(item.response_line))}</code></dd>
      <dt>Source</dt><dd><code>${esc(show(item.source_ref))}</code></dd>
      <dt>Saved reason code</dt><dd><code>${esc(show(item.reason))}</code></dd>`;
  }).join("");
  const exports = state.runs.filter((item) => item.sourceUrl && item.sourceUrl !== "#").map((item) => `<a class="export" href="${esc(item.sourceUrl)}" target="_blank" rel="noopener">${esc(siteName(item))} JSON</a>`).join("");
  return `<header class="pv-head">
      <div><p class="pv-kicker">${slotBadge(p.site)} ${esc(siteName(run))} · ${esc(laneName(lane))}</p>
      <h3>Evidence</h3></div>
      <div class="pv-head-actions">${pvToolsHtml()}<button type="button" class="pv-close" aria-label="Close evidence">✕</button></div>
    </header>
    <p class="pv-time" id="evidence">${esc(sample.timestamp_utc)} · follows the playhead</p>
    <dl class="evidence">
      ${rows}
      <dt>Observer</dt><dd>${esc(observer.longitude_east_deg)}° E, ${esc(observer.latitude_deg)}° N, ${esc(observer.reference_altitude_km)} km. Centre body ${esc(observer.center_body_id)}.</dd>
      <dt>Run ID</dt><dd><code>${esc(run.payload.run_id)}</code></dd>
      <dt>code_revision</dt><dd><code>${esc(run.payload.code_revision)}</code></dd>
    </dl>
    <div class="exports">${exports || '<span class="muted">Export is available after the live run completes.</span>'}</div>
    <p class="pv-foot">Centre-ray against geometric 0°. Terrain clearance unknown.</p>`;
}

const PV_ZOOM_MIN = 0.7;
const PV_ZOOM_MAX = 2;
const PV_ZOOM_STEP = 0.15;

function pvToolsHtml() {
  return `<div class="pv-tools" role="group" aria-label="Zoom the card">
      <button type="button" class="pv-zoom-btn" data-pv-zoom="out" aria-label="Zoom out" title="Zoom out (Ctrl + wheel)">−</button>
      <button type="button" class="pv-zoom-label" data-pv-zoom="reset" aria-label="Reset zoom" title="Reset zoom">${Math.round(state.pvZoom * 100)}%</button>
      <button type="button" class="pv-zoom-btn" data-pv-zoom="in" aria-label="Zoom in" title="Zoom in (Ctrl + wheel)">+</button>
    </div>`;
}

/** Zoom the centred card. Display only; nothing in the engine result changes. */
function setPreviewZoom(value) {
  const next = Math.min(PV_ZOOM_MAX, Math.max(PV_ZOOM_MIN, Math.round(value * 100) / 100));
  state.pvZoom = next;
  const host = document.getElementById("preview");
  if (host) {
    host.style.setProperty("--pvz", String(next));
    const label = host.querySelector(".pv-zoom-label");
    if (label) label.textContent = `${Math.round(next * 100)}%`;
  }
}

/** The preview card is a centred dialog over a dimmed page. It follows the playhead and can be zoomed. */
function renderPreview() {
  const host = document.getElementById("preview");
  const backdrop = document.getElementById("preview-backdrop");
  if (!host) return;
  const html = state.preview ? previewHtml() : "";
  host.hidden = !html;
  if (backdrop) backdrop.hidden = !html;
  document.body.classList.toggle("has-preview", Boolean(html));
  host.style.setProperty("--pvz", String(state.pvZoom));
  const scroll = host.querySelector(".pv-zoom-body");
  const top = scroll ? host.scrollTop : 0;
  host.innerHTML = html ? `<div class="pv-zoom-body">${html}</div>` : "";
  if (top) host.scrollTop = top;
}

function openPreview(spec) {
  const wasOpen = Boolean(state.preview);
  state.preview = spec;
  renderPreview();
  const close = document.querySelector("#preview .pv-close");
  if (!wasOpen && close) close.focus();
}

function closePreview() {
  state.preview = null;
  renderPreview();
}

/* ---------- Playback ---------- */

function playDelayMs() {
  const label = playbackPace().label;
  return { Slowest: 700, Slow: 320, Normal: 150, Fast: 60, Instant: 25 }[label];
}

function syncControls() {
  const start = document.getElementById("start-run");
  const cancel = document.getElementById("cancel-run");
  const play = document.getElementById("play-toggle");
  if (start) {
    start.disabled = state.running;
    start.querySelector(".btn-label").textContent = state.running ? "Streaming…" : "Start stream";
  }
  if (cancel) {
    cancel.disabled = !state.running || state.stopping;
    cancel.textContent = state.stopping ? "Stopping…" : "Stop";
  }
  if (play) {
    play.setAttribute("aria-pressed", String(state.playing));
    play.querySelector(".btn-label").textContent = state.playing ? "Pause" : "Play";
    play.querySelector(".btn-icon").textContent = state.playing ? "❚❚" : "▶";
    play.disabled = sharedSampleCount() < 2;
  }
}

function setRunning(value) {
  state.running = value;
  const more = document.getElementById("run-more");
  if (value && more) more.open = true;
  syncControls();
}

function stopPlayback() {
  state.playing = false;
  if (state.playTimer) clearTimeout(state.playTimer);
  state.playTimer = null;
  syncControls();
}

function tickPlayback() {
  if (!state.playing) return;
  const last = sharedSampleCount() - 1;
  if (state.index >= last) {
    if (state.live && state.partial) {
      state.playTimer = setTimeout(tickPlayback, playDelayMs());
      return;
    }
    stopPlayback();
    return;
  }
  move(state.index + stepSamples());
  state.playTimer = setTimeout(tickPlayback, playDelayMs());
}

function togglePlayback() {
  if (state.playing) {
    stopPlayback();
    return;
  }
  const last = sharedSampleCount() - 1;
  if (last < 1) return;
  if (state.index >= last && !(state.live && state.partial)) state.index = 0;
  state.playing = true;
  syncControls();
  state.playTimer = setTimeout(tickPlayback, 0);
}

function expectedSamples(run) {
  const s = run.payload.scenario;
  return Math.floor((parseUtc(s.end_utc) - parseUtc(s.start_utc)) / 1000 / s.step_seconds) + 1;
}

function updateStageStatus() {
  const through = document.getElementById("results-through");
  const progress = document.getElementById("site-progress");
  const follow = document.getElementById("follow-latest");
  const live = document.getElementById("stage-live");
  if (!through || !state.runs.length) return;
  const shared = sharedSampleCount();
  const latest = shared ? state.runs[0].payload.samples[shared - 1].timestamp_utc : null;
  const streaming = state.live && state.partial;
  through.textContent = latest
    ? "Results through " + latest + (streaming ? "" : state.live ? " · complete" : " · saved replay")
    : "Results through — · waiting for the first shared sample";
  if (live) live.dataset.live = streaming ? "true" : "false";
  if (follow) {
    follow.disabled = !streaming;
    follow.checked = streaming ? state.follow : false;
  }
  if (progress) {
    if (!state.live) {
      progress.innerHTML = "";
    } else {
      progress.innerHTML = state.runs.map((run, i) => {
        const total = expectedSamples(run);
        const done = state.siteProgress[i] ?? run.payload.samples.length;
        const pct = Math.min(100, (done / total) * 100);
        const pending = Math.max(0, total - done);
        return `<div class="prog"><span>${slotBadge(i)} ${esc(siteName(run))}: ${esc(done)} of ${esc(total)} samples${pending ? ` · ${esc(pending)} pending, not Unknown` : " · done"}</span><i class="prog-bar"><b style="width:${pct.toFixed(1)}%"></b></i></div>`;
      }).join("");
    }
  }
}

/** "01-01 13:15Z": month, day and UTC time, for dense lists. The year is in the scenario bar. */
function compactUtc(iso) {
  return String(iso).slice(5, 16).replace("T", " ") + "Z";
}

/** Compact Windows rail for the lane being shown. Every row comes from the engine intervals. */
function windowsHtml() {
  if (!state.runs.length) return "";
  const lane = state.lane;
  const sites = state.runs.map((run, runIndex) => {
    const elapsed = run.payload.elapsed_seconds[lane];
    const spans = mergedStates(run, lane);
    const clear = spans.filter((s) => s.state === "clear");
    const unknown = spans.filter((s) => s.state === "unknown");
    const row = (span) => {
      const chosen = isSelectedSpan(runIndex, lane, span);
      const reasons = span.state === "unknown" && span.reasons.length ? " · " + span.reasons.join(", ") : "";
      return `<li><button type="button" class="win-open${chosen ? " is-selected" : ""}" aria-pressed="${chosen}" data-site="${runIndex}" data-lane="${lane}" data-utc="${esc(span.start)}" data-end="${esc(span.end)}" data-state="${esc(span.state)}" aria-label="${esc(titleCase(span.state))} window ${esc(shortUtc(span.start))} to ${esc(shortUtc(span.end))}"><span class="win-range">${esc(compactUtc(span.start))} → ${esc(compactUtc(span.end))}</span><span class="win-len">${esc(fmtDuration((span.endMs - span.startMs) / 1000))}${esc(reasons)}</span></button></li>`;
    };
    const keep = clear.filter(qualifies);
    let clearBlock;
    if (clear.length && state.minHours && !keep.length) {
      const longest = Math.max(...clear.map((s) => s.endMs - s.startMs)) / 1000;
      clearBlock = `<p class="win-empty">No clear window of ${esc(minLabel())} or longer.</p>
        <p class="win-hint">Longest clear window: ${esc(fmtDuration(longest))}. Full-window totals above are unchanged.</p>`;
    } else if (clear.length) {
      clearBlock = `<ul class="win-list">${keep.map(row).join("")}</ul>
        ${state.minHours && keep.length < clear.length ? `<p class="win-hint">${keep.length} of ${clear.length} clear windows are ${esc(minLabel())} or longer.</p>` : ""}`;
    } else {
      const closest = lane !== "both" ? closestToZero(run, lane) : null;
      clearBlock = `<p class="win-empty">No clear window in this range.</p>
        ${state.partial ? '<p class="win-hint">Only resolved samples are counted. Pending is not Unknown.</p>' : ""}
        ${closest ? `<button type="button" class="mini win-closest" data-site="${runIndex}" data-lane="${lane}">Closest sampled point to 0°</button><span class="win-hint">saved sample, margin ${esc(signedDeg(closest.margin))}°</span>` : ""}`;
    }
    return `<article class="win-site${runIndex === state.site ? " is-selected" : ""}" data-site="${runIndex}">
      <h3>${slotBadge(runIndex)} ${esc(siteName(run))}</h3>
      <p class="win-tot">Clear <b>${esc(fmtDuration(elapsed.clear))}</b> · Blocked <b>${esc(fmtDuration(elapsed.blocked))}</b> · Unknown <b>${esc(fmtDuration(elapsed.unknown))}</b>${state.partial ? " so far" : ""}</p>
      <h4>Clear windows</h4>
      ${clearBlock}
      ${unknown.length ? `<h4>Unknown spans</h4><ul class="win-list">${unknown.map(row).join("")}</ul>` : ""}
    </article>`;
  }).join("");
  return `<p class="rail-sub">${esc(laneName(lane))}. From engine intervals. ${terrainMode() ? "Terrain mode: no reviewed skyline, so no window is named." : "Centre-ray against geometric 0° only."} Click a window to select it.</p>
    ${screenSummaryHtml()}
    ${sites}`;
}

/** Qualifying clear windows per site for the minimum-duration filter. Reads the same engine intervals as the list. */
function qualifies(span) {
  return !state.minHours || (span.endMs - span.startMs) / 1000 >= state.minHours * 3600;
}

/** 0.25 → "15 min", 8 → "8 h", 168 → "7 days". */
function minText(hours) {
  if (hours >= 48 && hours % 24 === 0) return `${hours / 24} days`;
  return hours >= 1 ? `${hours} h` : `${Math.round(hours * 60)} min`;
}

function minLabel() {
  return minText(state.minHours);
}

function screenSummaryHtml() {
  if (!state.minHours) return "";
  const lane = state.lane;
  const parts = state.runs.map((run, i) => {
    const n = mergedStates(run, lane).filter((s) => s.state === "clear" && qualifies(s)).length;
    return `${slotBadge(i)} ${esc(siteName(run))} <strong>${n ? n + (n === 1 ? " window" : " windows") : "none"}</strong>`;
  });
  return `<p class="filter-summary" role="status"><span class="fs-k">${esc(laneName(lane))} · ${esc(minLabel())} or longer</span>${parts.join('<span class="fs-sep" aria-hidden="true">·</span>')}</p>`;
}

/** Samples per Previous/Next/Play step. 0 means one saved sample. */
function stepSamples() {
  const run = state.runs[0];
  if (!run) return 1;
  const base = run.payload.scenario.step_seconds;
  return Math.max(1, Math.round((state.stepSeconds || base) / base));
}

function changeTimes(runIndex, lane) {
  return mergedStates(state.runs[runIndex], lane).slice(1).map((span) => span.start);
}

function changeTarget(direction) {
  if (!state.runs[state.site] || sharedSampleCount() === 0) return null;
  const now = parseUtc(sampleAt(state.site).timestamp_utc);
  const times = changeTimes(state.site, state.lane);
  return direction > 0
    ? times.find((t) => parseUtc(t) > now) || null
    : times.slice().reverse().find((t) => parseUtc(t) < now) || null;
}

function jumpChange(direction) {
  const target = changeTarget(direction);
  if (target) jumpToUtc(state.site, state.lane, target);
}

function syncTools() {
  document.querySelectorAll(".tool[data-key]").forEach((btn) => {
    const key = btn.dataset.key;
    const on = key === "lane" ? state.lane === btn.dataset.value : String(state.view[key]) === btn.dataset.value;
    btn.setAttribute("aria-pressed", String(on));
  });
  document.querySelectorAll(".tool[data-toggle]").forEach((btn) => {
    btn.setAttribute("aria-pressed", String(Boolean(state.view[btn.dataset.toggle])));
  });
  const host = document.getElementById("sky-stage");
  if (host) {
    host.dataset.grid = state.view.grid ? "on" : "off";
    host.dataset.shade = state.view.shade ? "on" : "off";
    host.dataset.labels = state.view.labels ? "on" : "off";
  }
  const ready = sharedSampleCount() > 0;
  const set = (id, disabled) => { const el = document.getElementById(id); if (el) el.disabled = disabled; };
  set("jump-start", !ready || state.index === 0);
  set("jump-end", !ready || state.index >= sharedSampleCount() - 1);
  set("jump-prev-change", !ready || !changeTarget(-1));
  set("jump-next-change", !ready || !changeTarget(1));
  const end = document.getElementById("jump-end");
  if (end) end.querySelector(".btn-label").textContent = state.live && state.partial ? "Latest" : "End";
}

function bindTools() {
  const handler = (event) => {
    const keyBtn = event.target.closest(".tool[data-key]");
    const toggle = event.target.closest(".tool[data-toggle]");
    if (keyBtn) {
      const { key, value } = keyBtn.dataset;
      if (key === "lane") {
        if (state.lane !== value) state.sel = null;
        state.lane = value;
        state.notice = "";
      } else state.view[key] = key === "decimals" ? Number(value) : value;
    } else if (toggle) {
      state.view[toggle.dataset.toggle] = !state.view[toggle.dataset.toggle];
    } else if (event.target.closest("#view-reset")) {
      state.view = { range: "15", trail: "off", grid: true, shade: true, labels: true, layout: "both", decimals: 6, terrain: "fill", peaks: true };
      state.showTerrain = false;
      document.getElementById("terrain-toggle").checked = false;
      document.querySelector(".stage").classList.remove("terrain-on");
    } else {
      return;
    }
    if (sharedSampleCount()) render();
    else syncTools();
  };
  document.getElementById("sky-tools").addEventListener("click", handler);
  document.getElementById("lane-tools").addEventListener("click", handler);
  document.getElementById("time-tools").addEventListener("click", (event) => {
    if (event.target.closest("#jump-start")) { move(0); return; }
    if (event.target.closest("#jump-end")) { move(sharedSampleCount() - 1); return; }
    if (event.target.closest("#jump-prev-change")) { jumpChange(-1); return; }
    if (event.target.closest("#jump-next-change")) { jumpChange(1); return; }
    handler(event);
  });
  document.getElementById("step-size").addEventListener("change", (event) => {
    state.stepSeconds = Number(event.target.value);
    syncTools();
  });
}

function jumpToSample(runIndex, lane, index) {
  state.site = runIndex;
  if (lane) state.lane = lane;
  move(index);
}

function jumpToUtc(runIndex, lane, utc) {
  const samples = state.runs[runIndex].payload.samples;
  let index = samples.findIndex((s) => s.timestamp_utc === utc);
  if (index < 0) {
    const t = parseUtc(utc);
    index = samples.findIndex((s) => parseUtc(s.timestamp_utc) >= t);
  }
  if (index < 0) return;
  jumpToSample(runIndex, lane, index);
}

/** Clicking a window (list row or lane segment): highlight its span, select its site, move the shared playhead to its start. */
function selectWindow(runIndex, lane, start, end, stateWord) {
  state.sel = { site: runIndex, lane, start, end, state: stateWord };
  jumpToUtc(runIndex, lane, start);
}

/** Jump to the saved sample whose margin is closest to 0°. Says so when that is the final sample. */
function jumpToClosest(runIndex, lane) {
  const best = closestToZero(state.runs[runIndex], lane);
  if (!best) return;
  const run = state.runs[runIndex];
  const sample = run.payload.samples[best.index];
  const final = !state.partial && best.index === sharedSampleCount() - 1;
  state.pendingNotice = `Closest sampled point to 0° for ${siteName(run)}: ${sample.timestamp_utc}, margin ${signedDeg(best.margin)}°.`
    + (final ? " This is the final sample, so it adds 0 elapsed time." : "");
  jumpToSample(runIndex, lane, best.index);
}

function updateStreamSkyInfo() {
  updateStageStatus();
}

function setRunStatus(text) {
  const status = document.getElementById("run-status");
  if (status) status.textContent = text;
}

function setPipeStage(stage) {
  const pipe = document.getElementById("calc-pipe");
  if (!pipe) return;
  const order = ["idle", "loading", "calculating", "shared", "complete"];
  const current = order.indexOf(stage);
  // Stage strip is for live runs only. Saved replays leave it hidden.
  pipe.hidden = !(state.live || state.running);
  pipe.querySelectorAll("li").forEach((item) => {
    const index = order.indexOf(item.dataset.stage);
    item.classList.toggle("is-focus", item.dataset.stage === stage);
    item.classList.toggle("is-live", index >= 0 && current >= 0 && index <= current && item.dataset.stage !== stage);
  });
}

/** PIA13523: south polar stereographic, 400 m/pixel, 1521 px, 0° longitude up, east right.
 * Checked against the 85°S graticule ring (r = 151.8 km, 49.9% of the half-width) and Amundsen. */
const MAP = { radiusM: 1737400, mPerPixel: 400, pixels: 1521 };

function polarPin(lonEast, latDeg) {
  const colat = Math.max(0, (90 + latDeg) * Math.PI / 180);
  const rM = 2 * MAP.radiusM * Math.tan(colat / 2);
  const halfM = (MAP.pixels * MAP.mPerPixel) / 2;
  const radius = Math.min(49, (rM / halfM) * 50);
  const rad = (lonEast * Math.PI) / 180;
  return {
    x: 50 + radius * Math.sin(rad),
    y: 50 - radius * Math.cos(rad),
  };
}

function contextSitesFromRuns() {
  if (!state.runs.length) return DEFAULT_CONTEXT_SITES;
  return state.runs.slice(0, 2).map((run, index) => {
    const observer = run.payload.scenario.observer;
    return {
      name: siteName(run),
      longitude_east_deg: observer.longitude_east_deg,
      latitude_deg: observer.latitude_deg,
      role: index === 0 ? "a" : "b",
    };
  });
}

function currentSamples() {
  const count = sharedSampleCount();
  if (!count) return [];
  const index = Math.max(0, Math.min(count - 1, state.index));
  return state.runs.map((run) => run.payload.samples[index] || null);
}

function setLiveChip() {
  const chip = document.getElementById("live-chip");
  if (!chip) return;
  if (state.live && state.runEnd) {
    chip.textContent = state.runEnd.kind === "failed" ? "Live failed" : "Live stopped";
    chip.classList.remove("soft");
  } else if (state.live && state.stopping) {
    chip.textContent = "Stopping";
    chip.classList.remove("soft");
  } else if (state.live && state.partial) {
    chip.textContent = "Live stream";
    chip.classList.remove("soft");
  } else if (state.live) {
    chip.textContent = "Live complete";
    chip.classList.remove("soft");
  } else if (state.source === "qa") {
    chip.textContent = "QA fixture";
    chip.classList.add("soft");
  } else {
    chip.textContent = "Replay";
    chip.classList.add("soft");
  }
}

function scenePayload(extra) {
  return Object.assign({
    sites: contextSitesFromRuns(),
    selectedSite: state.site,
    sampleIndex: state.index,
    samples: currentSamples(),
    sharedCount: sharedSampleCount(),
    partial: state.partial,
    live: state.live,
  }, extra || {});
}

function updateContextMap() {
  const skyHost = document.getElementById("sky-stage");
  if (skyHost && state.runs.length) skyHost.innerHTML = skyHtml();
  const svg = document.getElementById("context-pins");
  const sites = contextSitesFromRuns();
  if (svg) {
    svg.innerHTML = sites.map((site, index) => {
      const point = polarPin(site.longitude_east_deg, site.latitude_deg);
      const selected = index === state.site ? " is-selected" : "";
      const x = point.x.toFixed(2);
      const y = point.y.toFixed(2);
      const shape = index === 0
        ? `<circle class="pin-shape" cx="${x}" cy="${y}" r="3.6"></circle>`
        : `<rect class="pin-shape" x="${(point.x - 3.4).toFixed(2)}" y="${(point.y - 3.4).toFixed(2)}" width="6.8" height="6.8" transform="rotate(45 ${x} ${y})"></rect>`;
      return `<g class="pin-hit${selected}" data-site="${index}" tabindex="0" role="button" aria-label="Select site ${SLOT_LABELS[index]}, ${esc(site.name)}">
        ${shape}
        <text class="pin-letter" x="${x}" y="${(point.y + 1.3).toFixed(2)}" text-anchor="middle">${SLOT_LABELS[index]}</text>
        <text class="pin-name" x="${(point.x + 5.4).toFixed(2)}" y="${(point.y + 1.2).toFixed(2)}">${esc(site.name)}</text>
      </g>`;
    }).join("");
  }
  const key = document.getElementById("pin-key");
  if (key) {
    key.innerHTML = sites.map((site, index) => `<li class="${index === state.site ? "is-selected" : ""}"><button type="button" class="pin-key-btn" data-site="${index}"><i class="pin-icon pin-icon-${index === 0 ? "a" : "b"}">${SLOT_LABELS[index]}</i> <span>${esc(site.name)} · ${esc(site.latitude_deg)}° lat, ${esc(site.longitude_east_deg)}° E</span></button></li>`).join("");
  }
  setLiveChip();
  updateStreamSkyInfo();
  publishSceneEvent("lunar:scene-updated", scenePayload());
}

function publishSceneEvent(name, detail) {
  const stage = document.getElementById("scene-stage");
  if (!stage) return;
  stage.dispatchEvent(new CustomEvent(name, { detail, bubbles: true }));
}

function selectSiteFromScene(siteIndex) {
  if (!state.runs[siteIndex]) return;
  state.site = siteIndex;
  publishSceneEvent("lunar:site-select", {
    site: siteIndex,
    sampleIndex: state.index,
    run_id: state.runs[siteIndex].payload.run_id,
  });
  render();
}

function scrubFromSceneFraction(fractionValue) {
  if (!sharedSampleCount()) return;
  move(indexForFraction(fractionValue));
  publishSceneEvent("lunar:scene-scrub", {
    sampleIndex: state.index,
    fraction: fractionValue,
  });
}

function initStarfield() {
  const canvas = document.querySelector("#starfield");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const stars = [];
  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    stars.length = 0;
    const count = Math.floor((canvas.width * canvas.height) / 9000);
    for (let i = 0; i < count; i += 1) {
      stars.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        r: Math.random() * 1.2,
        a: 0.25 + Math.random() * 0.6,
        tw: Math.random() * Math.PI * 2,
        sp: 0.004 + Math.random() * 0.01,
      });
    }
  }
  function drawFrame() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (const star of stars) {
      if (!reducedMotion) star.tw += star.sp;
      const alpha = reducedMotion ? star.a : star.a * (0.55 + 0.45 * Math.sin(star.tw));
      ctx.fillStyle = "rgba(230,230,240," + alpha + ")";
      ctx.beginPath();
      ctx.arc(star.x, star.y, star.r, 0, Math.PI * 2);
      ctx.fill();
    }
    requestAnimationFrame(drawFrame);
  }
  resize();
  requestAnimationFrame(drawFrame);
  window.addEventListener("resize", resize);
}

function setPointerReadout(text) {
  const node = document.getElementById("pointer-readout");
  if (!node) return;
  if (!text) {
    node.hidden = true;
    node.textContent = "";
    return;
  }
  node.hidden = false;
  node.textContent = text;
}

/** Az / el under the pointer, from the inverse of the plot mapping. Adds the DEM value when the diagnostic is on. */
function cursorReadout(event) {
  const svg = event.target.closest && event.target.closest(".sky-svg");
  if (!svg || !svg.getScreenCTM) return "";
  const pt = svg.createSVGPoint();
  pt.x = event.clientX;
  pt.y = event.clientY;
  const loc = pt.matrixTransform(svg.getScreenCTM().inverse());
  const dx = loc.x - SKY.cx;
  const dy = SKY.cy - loc.y;
  const r = Math.hypot(dx, dy);
  if (r > SKY.rEdge) return "";
  const az = ((Math.atan2(dx, dy) * 180) / Math.PI + 360) % 360;
  const el = SKY.elCentre - (r / SKY.rEdge) * (SKY.elCentre - SKY.elEdge);
  const panel = svg.closest(".sky-panel");
  const run = panel ? state.runs[Number(panel.dataset.site)] : null;
  let text = `Cursor · az ${az.toFixed(1)}° · el ${signedDeg(Number(el.toFixed(3)))}°`;
  const profile = state.showTerrain && run ? terrainProfileForRun(run) : null;
  if (profile) {
    const h = interpolateHorizon(profile, az);
    text += h.known && typeof h.horizon_deg === "number" ? ` · DEM ${signedDeg(h.horizon_deg)}° (diagnostic)` : " · no DEM data";
  }
  return text;
}

function bindSceneInteractions() {
  const stage = document.getElementById("scene-stage");
  const map = document.getElementById("context-map");
  const pins = document.getElementById("context-pins");
  if (!stage) return;
  const scrub = { active: false, host: null };

  const onSite = (event) => {
    const hit = event.target.closest("[data-site]");
    if (!hit) return;
    const lane = hit.dataset.lane;
    if (lane === "sun" || lane === "earth" || lane === "both") state.lane = lane;
    selectSiteFromScene(Number(hit.dataset.site));
  };
  stage.addEventListener("click", onSite);
  stage.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const hit = event.target.closest("[data-site]");
    if (!hit) return;
    event.preventDefault();
    onSite(event);
  });
  if (pins) {
    pins.addEventListener("click", onSite);
    pins.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" && event.key !== " ") return;
      const hit = event.target.closest("[data-site]");
      if (!hit) return;
      event.preventDefault();
      onSite(event);
    });
  }

  stage.addEventListener("pointermove", (event) => {
    const hit = event.target.closest("[data-lane][data-site]");
    if (!hit) {
      if (!scrub.active) setPointerReadout(cursorReadout(event));
      return;
    }
    setPointerReadout(hit.getAttribute("aria-label") || "");
  });
  stage.addEventListener("pointerleave", () => {
    if (!scrub.active) setPointerReadout("");
  });

  function fractionFromEvent(host, event) {
    const rect = host.getBoundingClientRect();
    if (!rect.width) return 0;
    return Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
  }
  function beginScrub(host, event) {
    if (event.target.closest("[data-lane][data-site], .pin-hit, button, a, input, summary")) return;
    if (event.button != null && event.button !== 0) return;
    scrub.active = true;
    scrub.host = host;
    host.classList.add("is-scrubbing");
    try { host.setPointerCapture(event.pointerId); } catch (_e) { /* ignore */ }
    scrubFromSceneFraction(fractionFromEvent(host, event));
    setPointerReadout("Scrub · " + (document.getElementById("utc")?.textContent || ""));
    event.preventDefault();
  }
  function moveScrub(event) {
    if (!scrub.active || !scrub.host) return;
    scrubFromSceneFraction(fractionFromEvent(scrub.host, event));
    setPointerReadout("Scrub · " + (document.getElementById("utc")?.textContent || ""));
  }
  function endScrub(event) {
    if (!scrub.active) return;
    scrub.active = false;
    scrub.host?.classList.remove("is-scrubbing");
    try { scrub.host?.releasePointerCapture(event.pointerId); } catch (_e) { /* ignore */ }
    scrub.host = null;
    setPointerReadout("");
  }
  [map, stage].filter(Boolean).forEach((host) => {
    host.addEventListener("pointerdown", (event) => beginScrub(host, event));
    host.addEventListener("pointermove", moveScrub);
    host.addEventListener("pointerup", endScrub);
    host.addEventListener("pointercancel", endScrub);
    host.addEventListener("wheel", (event) => {
      if (!sharedSampleCount()) return;
      event.preventDefault();
      move(state.index + (event.deltaY > 0 ? 1 : -1));
      setPointerReadout("Step · " + (document.getElementById("utc")?.textContent || ""));
    }, { passive: false });
  });

  const speed = document.getElementById("playback-speed");
  if (speed) {
    syncPlaybackLabel();
    speed.addEventListener("input", syncPlaybackLabel);
  }

  publishSceneEvent("lunar:scene-ready", {
    host: "sky-stage",
    interim: "pia13523-clear+trek-wac",
    supports: ["site-select", "stream-target", "scrub", "playback-speed", "follow-latest"],
  });
}

function setLiveExport(result, filename) {
  const holder = document.getElementById("live-export");
  if (!holder) return;
  if (!result) {
    holder.innerHTML = "";
    return;
  }
  const blob = new Blob([JSON.stringify(result, null, 2) + "\n"], { type: "application/json" });
  const href = URL.createObjectURL(blob);
  const name = filename || (result.run_id ? result.run_id + ".json" : "comparison.json");
  holder.innerHTML = `<a class="export" href="${href}" download="${esc(name)}">Download complete export</a>`;
}

function emptyOverlap() {
  return {
    sun_centre_clear_seconds: { site_a: 0, site_b: 0, delta_b_minus_a: 0 },
    both_centres_clear_seconds: { site_a: 0, site_b: 0, delta_b_minus_a: 0 },
    unknown_seconds: {
      site_a: { sun: 0, earth: 0, both: 0 },
      site_b: { sun: 0, earth: 0, both: 0 },
    },
  };
}

function emptyRunPayload(siteMeta) {
  return {
    schema_version: "run-result-1",
    run_id: siteMeta.result_run_id,
    code_revision: siteMeta.code_revision,
    practice: siteMeta.practice,
    eligible_for_submission_claim: siteMeta.eligible_for_submission_claim,
    labels: siteMeta.labels,
    scenario: siteMeta.scenario,
    terrain: siteMeta.terrain,
    samples: [],
    intervals: [],
    elapsed_seconds: emptyElapsed(),
  };
}

function abortLiveConsumer() {
  if (state.running && (state.liveComparisonId || state.liveRunId)) {
    const target = state.liveMode === "comparison" && state.liveComparisonId
      ? "/api/comparisons/" + state.liveComparisonId + "/cancel"
      : "/api/runs/" + state.liveRunId + "/cancel";
    fetch(target, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" }).catch(() => {});
  }
  state.stopping = false;
  setRunning(false);
  stopPlayback();
  if (state.liveAbort) {
    state.liveAbort.abort();
    state.liveAbort = null;
  }
}

function emptyElapsed() {
  return {
    sun: { clear: 0, blocked: 0, unknown: 0 },
    earth: { clear: 0, blocked: 0, unknown: 0 },
    both: { clear: 0, blocked: 0, unknown: 0 },
  };
}

function applyLiveEvent(event) {
  if (state.liveMode === "comparison") {
    applyLiveComparisonEvent(event);
    return;
  }
  if (state.liveRunId && event.run_id && event.run_id !== state.liveRunId) return;
  if (["complete", "cancelled", "error"].includes(event.event)) {
    state.stopping = false;
    setRunning(false);
  }
  if (event.event === "stage") {
    setPipeStage("loading");
    setRunStatus("Loading inputs. Run " + event.run_id + ".");
    return;
  }
  if (event.event === "metadata") {
    setPipeStage("calculating");
    state.live = true;
    state.liveMode = "single";
    state.partial = true;
    state.runEnd = null;
    state.source = "live";
    state.comparison = {
      practice: event.practice,
      qa_fixture: false,
      eligible_for_submission_claim: event.eligible_for_submission_claim,
      limitations: [
        "Live local calculation from saved Horizons inputs. This is not a Horizons download.",
        "Terrain mode is Unknown until the M4 review.",
      ],
    };
    state.runs = [{
      role: "Live",
      sourceUrl: "#",
      payload: emptyRunPayload({
        result_run_id: event.result_run_id,
        code_revision: event.code_revision,
        practice: event.practice,
        eligible_for_submission_claim: event.eligible_for_submission_claim,
        labels: event.labels,
        scenario: event.scenario,
        terrain: event.terrain,
      }),
    }];
    state.index = 0;
    state.site = 0;
    state.lane = "sun";
    state.siteProgress = [0];
    state.follow = true;
    state.sel = null;
    state.notice = "";
    setLiveExport(null);
    setRunStatus("Calculating. Run " + event.run_id + ". Result " + event.result_run_id + ".");
    renderWaiting();
    return;
  }
  if (event.event === "batch") {
    setPipeStage("calculating");
    const payload = state.runs[0].payload;
    payload.samples = payload.samples.concat(event.samples);
    payload.intervals = event.intervals;
    payload.elapsed_seconds = event.elapsed_seconds;
    state.partial = true;
    state.siteProgress = [event.samples_emitted];
    if (state.follow) state.index = Math.max(0, payload.samples.length - 1);
    setRunStatus("Calculating. Run " + event.run_id + ". Samples " + event.samples_emitted + ".");
    publishSceneEvent("lunar:stream-batch", scenePayload());
    render();
    return;
  }
  if (event.event === "complete") {
    setPipeStage("complete");
    state.partial = false;
    state.runs[0].payload = event.result;
    state.runs[0].sourceUrl = "#";
    state.siteProgress = [event.result.samples.length];
    state.runEnd = null;
    setLiveExport(event.result);
    setRunStatus("Complete. Run " + event.run_id + ". Result " + event.result_run_id + ".");
    render();
    return;
  }
  if (event.event === "cancelled" || event.event === "error") {
    setPipeStage("shared");
    state.partial = true;
    if (state.runs[0]) {
      state.runs[0].payload.elapsed_seconds = event.elapsed_seconds || state.runs[0].payload.elapsed_seconds;
      state.runs[0].payload.intervals = event.intervals || state.runs[0].payload.intervals;
    }
    state.runEnd = {
      kind: event.event === "cancelled" ? "cancelled" : "failed",
      message: event.message || "",
      shared: event.samples_emitted || 0,
      cutoff: event.cutoff_utc || null,
      covered: event.covered_through_utc || null,
      delivered: [event.samples_emitted || 0],
    };
    setLiveExportUnavailable();
    setRunStatus(runEndStatus("Run " + event.run_id));
    render();
  }
}

function applyLiveComparisonEvent(event) {
  if (state.liveComparisonId && event.comparison_id && event.comparison_id !== state.liveComparisonId) return;
  if (["complete", "cancelled", "error"].includes(event.event)) {
    state.stopping = false;
    setRunning(false);
  }
  if (event.event === "stage") {
    setPipeStage("loading");
    setRunStatus("Loading inputs. Comparison " + event.comparison_id + ". Runs " + event.run_id_a + " / " + event.run_id_b + ".");
    return;
  }
  if (event.event === "metadata") {
    setPipeStage("calculating");
    state.live = true;
    state.liveMode = "comparison";
    state.partial = true;
    state.runEnd = null;
    state.source = "live";
    state.comparison = {
      practice: event.practice,
      qa_fixture: false,
      eligible_for_submission_claim: false,
      comparable: true,
      overlap: emptyOverlap(),
      limitations: [
        "Live local two-site calculation from saved Horizons inputs. This is not a Horizons download.",
        "Comparison totals use only the shared resolved interval until both sites finish.",
        "Pending samples are not scientific Unknown.",
        "Terrain mode is Unknown until the M4 review.",
      ],
      runs: event.sites.map((site) => ({
        role: site.role === "site_a" ? "Site A" : "Site B",
        file: "#",
        run_id: site.result_run_id,
      })),
    };
    state.runs = event.sites.map((site, index) => ({
      role: site.role === "site_a" ? "Site A" : "Site B",
      sourceUrl: "#",
      payload: emptyRunPayload(site),
    }));
    state.index = 0;
    state.site = 0;
    state.lane = "sun";
    state.siteProgress = [0, 0];
    state.follow = true;
    state.sel = null;
    state.notice = "";
    setLiveExport(null);
    setRunStatus("Calculating. Comparison " + event.comparison_id + ".");
    renderWaiting();
    return;
  }
  if (event.event === "site_batch") {
    setPipeStage(event.shared_samples > 0 ? "shared" : "calculating");
    const runIndex = event.role === "site_b" ? 1 : 0;
    const payload = state.runs[runIndex].payload;
    payload.samples = payload.samples.concat(event.samples);
    payload.intervals = event.intervals;
    payload.elapsed_seconds = event.elapsed_seconds;
    state.siteProgress[runIndex] = event.samples_emitted;
    state.comparison.overlap = event.overlap;
    state.partial = true;
    const shared = sharedSampleCount();
    if (state.follow) state.index = Math.max(0, shared - 1);
    setRunStatus(
      "Calculating. Comparison " + event.comparison_id
      + ". " + siteName(state.runs[0]) + " " + state.siteProgress[0]
      + ", " + siteName(state.runs[1]) + " " + state.siteProgress[1]
      + ", shared " + shared + "."
    );
    publishSceneEvent("lunar:stream-batch", scenePayload({
      comparison_id: event.comparison_id,
      role: event.role,
      shared_samples: shared,
    }));
    render();
    return;
  }
  if (event.event === "complete") {
    setPipeStage("complete");
    state.partial = false;
    state.runs[0].payload = event.result_a;
    state.runs[1].payload = event.result_b;
    state.comparison = event.comparison;
    state.comparison.limitations = (event.comparison.limitations || []).concat([
      "Live local two-site calculation from saved Horizons inputs. This is not a Horizons download.",
      "Terrain mode is Unknown until the M4 review.",
    ]);
    state.siteProgress = [event.result_a.samples.length, event.result_b.samples.length];
    if (state.follow) state.index = Math.max(0, sharedSampleCount() - 1);
    state.runEnd = null;
    setLiveExport(event.comparison, event.comparison_id + "-comparison.json");
    setRunStatus(
      "Complete. Comparison " + event.comparison_id
      + ". Results " + event.result_run_id_a + " / " + event.result_run_id_b + "."
    );
    publishSceneEvent("lunar:stream-complete", scenePayload({
      comparison_id: event.comparison_id,
      result_run_id_a: event.result_run_id_a,
      result_run_id_b: event.result_run_id_b,
    }));
    render();
    return;
  }
  if (event.event === "cancelled" || event.event === "error") {
    setPipeStage("shared");
    state.partial = true;
    if (state.runs[0] && event.elapsed_seconds_a) {
      state.runs[0].payload.elapsed_seconds = event.elapsed_seconds_a;
      state.runs[0].payload.intervals = event.intervals_a || state.runs[0].payload.intervals;
    }
    if (state.runs[1] && event.elapsed_seconds_b) {
      state.runs[1].payload.elapsed_seconds = event.elapsed_seconds_b;
      state.runs[1].payload.intervals = event.intervals_b || state.runs[1].payload.intervals;
    }
    if (event.overlap) state.comparison.overlap = event.overlap;
    state.siteProgress = [event.samples_emitted_a || 0, event.samples_emitted_b || 0];
    state.runEnd = {
      kind: event.event === "cancelled" ? "cancelled" : "failed",
      message: event.message || "",
      shared: event.shared_samples || 0,
      cutoff: event.cutoff_utc || null,
      covered: event.covered_through_utc || null,
      delivered: [event.samples_emitted_a || 0, event.samples_emitted_b || 0],
    };
    setLiveExportUnavailable();
    setRunStatus(runEndStatus("Comparison " + event.comparison_id));
    render();
  }
}

/** Status sentence for a run that ended early. It names the final cutoff and says no export exists. */
function runEndStatus(label) {
  const end = state.runEnd;
  const lead = end.kind === "failed" ? "Failed" : "Stopped";
  const reason = end.kind === "failed" && end.message ? " " + end.message + "." : "";
  const total = state.runs.length ? Math.max(...state.runs.map(expectedSamples)) : 0;
  const cut = end.cutoff
    ? " Final cutoff " + end.cutoff + " (" + end.shared + " of " + total + " shared samples). Totals cover through "
      + (end.covered || end.cutoff) + "."
    : " No shared sample was delivered, so there is no partial result.";
  const per = end.delivered.length > 1
    ? " Delivered: " + state.runs.map((run, i) => siteName(run) + " " + end.delivered[i]).join(", ") + "."
    : "";
  return lead + ". " + label + "." + reason + cut + per + " No export: the run did not complete.";
}

function setLiveExportUnavailable() {
  const holder = document.getElementById("live-export");
  if (holder) holder.innerHTML = '<span class="note">No export: the run did not complete.</span>';
}

async function readNdjson(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let newline = buffer.indexOf("\n");
    while (newline >= 0) {
      const line = buffer.slice(0, newline).trim();
      buffer = buffer.slice(newline + 1);
      if (line) {
        const event = JSON.parse(line);
        onEvent(event);
        const delay = playbackPace().client_delay_ms;
        if (delay > 0 && !state.stopping && (event.event === "batch" || event.event === "site_batch")) {
          await sleep(delay);
        }
      }
      newline = buffer.indexOf("\n");
    }
  }
  const trailing = buffer.trim();
  if (trailing) onEvent(JSON.parse(trailing));
}

/* ---------- Saved data catalog ---------- */

const catalogState = { data: null };

function catalogEntry(id) {
  return catalogState.data && catalogState.data.entries.find((e) => e.id === id);
}

function catalogWindow(id) {
  return catalogState.data && catalogState.data.comparisons.find((w) => w.id === id);
}

function shortSha(value) {
  return value ? String(value).slice(0, 12) : "none";
}

function catalogEntryInfo(entry) {
  const o = entry.observer;
  const cov = entry.coverage;
  const gaps = entry.angles.sun.missing + entry.angles.earth.missing;
  return `${entry.site_id}${entry.synthetic ? " · SYNTHETIC QA, not JPL output" : ""} · observer ${o.longitude_east_deg}°E, ${o.latitude_deg}°, ${o.reference_altitude_km} km`
    + ` · ${cov.start_utc} → ${cov.end_utc} · every ${fmtDuration(cov.step_seconds)} · ${cov.samples} rows`
    + ` · missing angles: Sun ${entry.angles.sun.missing}, Earth ${entry.angles.earth.missing}${gaps ? " (kept as Unknown)" : ""}`
    + ` · SHA-256 Sun ${shortSha(entry.sources.sun.raw_sha256)}, Earth ${shortSha(entry.sources.earth.raw_sha256)}`;
}

function syncCatalogInputs(reset) {
  const value = document.getElementById("scenario").value;
  const start = document.getElementById("cat-start");
  const end = document.getElementById("cat-end");
  const info = document.getElementById("cat-info");
  if (!start || !end || !info) return;
  let range = null;
  let text = "A named scenario uses its own saved range. Pick a catalog entry to choose your own.";
  if (value.startsWith("catalog:")) {
    const entry = catalogEntry(value.slice(8));
    if (entry) {
      range = entry.coverage;
      text = catalogEntryInfo(entry);
    }
  } else if (value.startsWith("window:")) {
    const win = catalogWindow(value.slice(7));
    if (win) {
      range = win;
      const a = catalogEntry(win.a);
      const b = catalogEntry(win.b);
      text = `Shared UTC grid: ${win.start_utc} → ${win.end_utc} · every ${fmtDuration(win.step_seconds)} · ${win.samples} rows. A: ${a ? catalogEntryInfo(a) : win.a}. B: ${b ? catalogEntryInfo(b) : win.b}.`;
    }
  }
  info.textContent = text;
  start.disabled = end.disabled = !range;
  start.classList.remove("is-bad");
  end.classList.remove("is-bad");
  if (!range) {
    start.value = "";
    end.value = "";
  } else if (reset) {
    start.value = range.start_utc;
    end.value = range.end_utc;
    document.getElementById("run-more").open = true;
  }
}

async function loadCatalog() {
  let data;
  try {
    const response = await fetch("/api/catalog");
    if (!response.ok) return;
    data = await response.json();
  } catch (error) {
    return;
  }
  catalogState.data = data;
  const select = document.getElementById("scenario");
  const group = (label, items) => {
    if (!items.length) return;
    const g = document.createElement("optgroup");
    g.label = label;
    items.forEach(([value, text]) => {
      const o = document.createElement("option");
      o.value = value;
      o.textContent = text;
      g.appendChild(o);
    });
    select.appendChild(g);
  };
  const entryLabel = (e) => e.label + (e.angles.sun.missing + e.angles.earth.missing ? " · has gaps" : "");
  group("Saved catalog · one site", data.entries.filter((e) => !e.synthetic).map((e) => ["catalog:" + e.id, entryLabel(e)]));
  const isSynthetic = (w) => [w.a, w.b].some((id) => (catalogEntry(id) || {}).synthetic);
  group("Saved catalog · shared two-site window", data.comparisons.filter((w) => !isSynthetic(w)).map((w) => ["window:" + w.id, w.label]));
  group("Synthetic QA cases · not JPL output", [
    ...data.entries.filter((e) => e.synthetic).map((e) => ["catalog:" + e.id, "SYNTHETIC · " + entryLabel(e)]),
    ...data.comparisons.filter(isSynthetic).map((w) => ["window:" + w.id, "SYNTHETIC · " + w.label]),
  ]);
  syncCatalogInputs(false);
}

/** Request fields for the chosen catalog range and horizon, or an error message. */
function catalogRequest(kind) {
  const body = {};
  if (kind) {
    const start = document.getElementById("cat-start");
    const end = document.getElementById("cat-end");
    body.start_utc = start.value.trim();
    body.end_utc = end.value.trim();
  }
  const mode = document.getElementById("horizon-mode").value;
  if (mode !== "geometric_0deg") body.horizon_mode = mode;
  return body;
}

async function startLiveRun() {
  abortLiveConsumer();
  state.why = null;
  state.runEnd = null;
  state.stopping = false;
  setRunning(true);
  const scenario = document.getElementById("scenario").value;
  const fail = document.getElementById("fail-test").checked;
  setLiveExport(null);
  if (scenario.startsWith("window:")) {
    await startLiveComparison(fail, null, { catalog_window: scenario.slice(7), ...catalogRequest(true) });
    return;
  }
  if (scenario === "practice-48h" || scenario === "practice-30d") {
    await startLiveComparison(fail, scenario, catalogRequest(false));
    return;
  }
  const body = {
    batch_size: LIVE_SERVER.batch_size,
    pause_seconds: LIVE_SERVER.pause_seconds,
    ...(scenario.startsWith("catalog:") ? { catalog: scenario.slice(8), ...catalogRequest(true) } : { scenario, ...catalogRequest(false) }),
  };
  if (fail) body.fail_after_batches = 1;
  setRunStatus("Starting " + scenario + ".");
  state.liveMode = "single";
  state.liveComparisonId = null;
  const started = await (await fetch("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })).json();
  if (!started.run_id) {
    setRunStatus("Failed to start. " + (started.error || "no run id"));
    return;
  }
  state.liveRunId = started.run_id;
  state.liveAbort = new AbortController();
  const response = await fetch("/api/runs/" + started.run_id + "/events", { signal: state.liveAbort.signal });
  await readNdjson(response, applyLiveEvent);
}

async function startLiveComparison(fail, pair = "practice-48h", extra = {}) {
  const body = {
    ...(pair ? { pair } : {}),
    ...extra,
    batch_size_a: 3,
    batch_size_b: LIVE_SERVER.batch_size,
    pause_seconds: LIVE_SERVER.pause_seconds,
  };
  if (fail) body.fail_after_batches_a = 1;
  setRunStatus("Starting " + (pair || extra.catalog_window) + " comparison.");
  state.liveMode = "comparison";
  state.liveRunId = null;
  const started = await (await fetch("/api/comparisons", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  })).json();
  if (!started.comparison_id) {
    setRunStatus("Failed to start. " + (started.error || "no comparison id"));
    return;
  }
  state.liveComparisonId = started.comparison_id;
  state.liveRunId = started.comparison_id;
  setRunStatus(
    "Started comparison " + started.comparison_id
    + ". Runs " + started.run_id_a + " / " + started.run_id_b + "."
  );
  state.liveAbort = new AbortController();
  const response = await fetch("/api/comparisons/" + started.comparison_id + "/events", {
    signal: state.liveAbort.signal,
  });
  await readNdjson(response, applyLiveEvent);
}

async function cancelLiveRun() {
  if (!state.liveRunId && !state.liveComparisonId) {
    setRunStatus("No active run to cancel.");
    return;
  }
  if (!state.running || state.stopping) return;
  const comparison = state.liveMode === "comparison" && state.liveComparisonId;
  const id = comparison ? state.liveComparisonId : state.liveRunId;
  // Stopping holds until the engine sends the cancelled event with its final cutoff.
  state.stopping = true;
  syncControls();
  setLiveChip();
  setRunStatus("Stopping. " + (comparison ? "Comparison " : "Run ") + id + ". Waiting for the engine to report the final cutoff.");
  if (state.runs.length && sharedSampleCount() > 0) render();
  try {
    const response = await fetch((comparison ? "/api/comparisons/" : "/api/runs/") + id + "/cancel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    if (!response.ok) throw new Error("HTTP " + response.status);
  } catch (error) {
    state.stopping = false;
    syncControls();
    setLiveChip();
    setRunStatus("Stop failed. " + error + ". The run is still going.");
  }
}

/** Live run started but no shared sample yet: show the scenario, the progress, and an honest waiting line. */
function renderWaiting() {
  document.getElementById("scenario-info").innerHTML = scenarioBarHtml();
  const end = state.runEnd;
  document.getElementById("banner").textContent = end
    ? (end.kind === "failed" ? "Run failed before any shared sample. Nothing to show." : "Run stopped before any shared sample. Nothing to show.")
    : "Calculating from saved Horizons inputs. Pending is not Unknown.";
  const detail = end
    ? `${end.kind === "failed" ? "Failed" : "Stopped"} before any shared sample was delivered. ${state.runs.map((run, i) => `${esc(siteName(run))} delivered ${esc(end.delivered[i] ?? 0)}`).join(", ")}. There is no partial result and no export.`
    : state.stopping
      ? "Stopping. Waiting for the engine to report the final cutoff."
      : "Waiting for the first shared sample. Pending is not Unknown.";
  document.getElementById("answers").innerHTML = `<h1 id="result-heading" class="result-title">Sun-centre clearance</h1>
    <p class="result-sub">${detail}</p>`;
  document.getElementById("answers-details").innerHTML = "";
  setLiveChip();
  updateStageStatus();
}


/* ---------- Why this result? ---------- */

/** Samples that count toward the result now. A partial run counts only the shared resolved samples. */
function resolvedCount(run) {
  return Math.min(run.payload.samples.length, state.partial ? sharedSampleCount() : run.payload.samples.length);
}

/** Counts per state for one lane, the sample closest to the horizon, and the Unknown reasons. */
function laneStats(run, lane, count) {
  const samples = run.payload.samples.slice(0, count);
  const out = { n: samples.length, clear: 0, blocked: 0, unknown: 0, reasons: [], near: null };
  samples.forEach((sample, index) => {
    const item = sample[lane];
    out[item.state] += 1;
    if (item.state === "unknown" && item.reason && !out.reasons.includes(item.reason)) out.reasons.push(item.reason);
    const margin = laneMargin(sample, lane);
    if (margin !== null && (out.near === null || Math.abs(margin) < Math.abs(out.near.margin))) out.near = { index, margin };
  });
  return out;
}

function stateTransitions(run, lane, limit) {
  const spans = mergedStates(run, lane);
  const shown = spans.slice(0, limit).map((span) => `${span.state} from ${shortUtc(span.start)}`);
  return shown.join(", then ") + (spans.length > limit ? ", …" : "");
}

/** Saved rows for the chosen samples: Horizons row text, elevation, horizon, margin and state. */
function sourceRowsHtml(run, runIndex, lane, indices, caption) {
  const bodies = lane === "both" ? ["sun", "earth"] : [lane];
  const rows = [];
  indices.forEach((index) => {
    const sample = run.payload.samples[index];
    if (!sample) return;
    bodies.forEach((body) => {
      const item = sample[body];
      rows.push(`<tr>
        <td class="mono">${esc(sample.timestamp_utc)}</td>
        <td>${body === "sun" ? "Sun centre" : "Earth centre"}</td>
        <td class="mono">${esc(item.response_line || "no saved row")}</td>
        <td class="num">${esc(signedDeg(item.elevation_deg))}°</td>
        <td class="num">${esc(show(item.horizon_deg))}°</td>
        <td class="num">${esc(signedDeg(item.margin_deg))}°</td>
        <td><span class="state-word ${esc(item.state)}">${esc(item.state)}</span></td>
        <td class="mono">${esc(item.source_ref || "")}</td>
      </tr>`);
    });
    if (lane === "both") {
      rows.push(`<tr class="src-joint"><td class="mono">${esc(sample.timestamp_utc)}</td><td>Both centres</td><td colspan="4">${esc(sample.both.reason ? "reason " + sample.both.reason : "no blocking or unknown reason")}</td><td><span class="state-word ${esc(sample.both.state)}">${esc(sample.both.state)}</span></td><td></td></tr>`);
    }
  });
  const jump = indices.length
    ? `<button type="button" class="mini why-jump" data-site="${runIndex}" data-lane="${lane}" data-index="${indices[indices.length - 1]}">Show this sample in the timeline</button>`
    : "";
  return `<div class="src-wrap"><table class="src-table"><caption>${esc(caption)}</caption>
    <thead><tr><th>UTC</th><th>Body</th><th>Saved Horizons row</th><th>Elevation</th><th>Horizon</th><th>Margin</th><th>State</th><th>Source</th></tr></thead>
    <tbody>${rows.join("")}</tbody></table></div>${jump}`;
}

/** Which saved samples show the answer: the nearest to the horizon, or the sample before and at the first transition. */
function evidenceIndices(run, lane, stats) {
  if (stats.n === 0) return [];
  const mixed = stats.clear > 0 && stats.clear < stats.n;
  if (mixed) {
    const first = run.payload.samples.findIndex((sample) => sample[lane].state === "clear");
    const at = first <= 0 ? 0 : first;
    return at > 0 ? [at - 1, at] : [at];
  }
  return stats.near ? [stats.near.index] : [0];
}

function whyLaneHtml(runIndex, lane) {
  const run = state.runs[runIndex];
  if (!run) return "";
  const count = resolvedCount(run);
  const stats = laneStats(run, lane, count);
  const name = siteName(run);
  const elapsed = run.payload.elapsed_seconds[lane];
  const step = run.payload.scenario.step_seconds;
  const total = fmtDuration(elapsed.clear);
  const partial = state.partial ? " so far" : "";
  const body = lane === "sun" ? "Sun's centre" : lane === "earth" ? "Earth's centre" : "the Sun's or Earth's centre";
  const near = stats.near ? ` The sample nearest the horizon is ${shortUtc(run.payload.samples[stats.near.index].timestamp_utc)}, margin ${signedDeg(stats.near.margin)}°.` : "";
  const interval = `Each sample counts for its own ${fmtDuration(step)} interval, and the final sample adds 0 s.`;
  const paragraphs = [];
  if (stats.n === 0) {
    paragraphs.push("No sample has been resolved yet. Pending is not Unknown.");
  } else if (lane === "both") {
    const sun = laneStats(run, "sun", count);
    const earth = laneStats(run, "earth", count);
    paragraphs.push(`${name}: the Sun centre is clear at ${sun.clear} of ${stats.n} samples and the Earth centre at ${earth.clear}. Both centres clear needs both above the horizon in the same sample, so it is clear at ${stats.clear}${partial}. ${interval} That is ${total}.`);
    paragraphs.push("Blocked beats Unknown, and Unknown beats Clear: if either centre is blocked the joint state is blocked.");
    if (stats.clear === 0) {
      const limiting = sun.clear <= earth.clear ? "Sun" : "Earth";
      paragraphs.push(`The ${limiting} centre is the limit here. It is clear at ${Math.min(sun.clear, earth.clear)} samples.${near}`);
    }
  } else if (stats.clear === stats.n) {
    paragraphs.push(`${name}: ${body} is above the 0° horizon at all ${stats.n} samples${stats.near ? ", with a smallest margin of " + signedDeg(stats.near.margin) + "°" : ""}. ${interval} ${stats.n - 1} intervals of ${fmtDuration(step)} give ${total}${partial}.`);
  } else if (stats.blocked === stats.n) {
    paragraphs.push(`${name}: ${body} is on or below the 0° horizon at all ${stats.n} samples. A margin of 0° or less is blocked, including exact contact, so no time counts as clear: ${total}${partial}.${near}`);
  } else {
    paragraphs.push(`${name}: ${body} is clear at ${stats.clear} of ${stats.n} samples (${total}${partial}), blocked at ${stats.blocked} and unknown at ${stats.unknown}. ${interval}`);
    paragraphs.push(`Changes: ${stateTransitions(run, lane, 4)}.`);
  }
  if (stats.unknown) {
    paragraphs.push(`Unknown is not clear and not blocked. It is counted separately (${fmtDuration(elapsed.unknown)}). Saved reasons: ${stats.reasons.join(", ") || "not stated"}.`);
  }
  const indices = evidenceIndices(run, lane, stats);
  const caption = indices.length > 1 ? "Source rows: the last sample before the change and the first after it" : "Source row";
  const label = lane === "both" ? "Both centres clear" : laneName(lane);
  return `<div class="why-body-in"><h3>${slotBadge(runIndex)} ${esc(name)} · ${esc(label)} · ${esc(total)}${esc(partial)}</h3>
    ${paragraphs.map((text) => `<p>${esc(text)}</p>`).join("")}
    ${indices.length ? sourceRowsHtml(run, runIndex, lane, indices, caption) : ""}</div>`;
}

function whyTerrainHtml() {
  const heights = state.runs.map((run) => {
    const observer = run.payload.scenario.observer;
    return `${siteName(run)} ${show(observer.reference_altitude_km)} km`;
  }).join(" · ");
  const modes = state.runs.map((run) => run.payload.scenario.horizon_mode).filter((v, i, a) => a.indexOf(v) === i).join(", ");
  const tinfo = state.runs[0] && state.runs[0].payload.terrain;
  const lead = terrainMode()
    ? `<p>This is a terrain-mode run. Terrain clearance is Unknown because ${esc(terrainReasonText(tinfo && tinfo.reason))}. The reason code is ${esc((tinfo && tinfo.reason) || "terrain_not_reviewed")}${tinfo && tinfo.detail ? " (" + esc(tinfo.detail) + ")" : ""}. Each sample keeps the saved Horizons elevation and has no horizon or margin. The 0° baseline is not substituted. Unknown is not Pending: it is a finished answer.</p>`
    : `<p>Terrain clearance is Unknown because no reviewed skyline is accepted. The reason code is terrain_not_reviewed. Every result on this screen uses the labelled geometric 0° baseline (${esc(modes)}), not terrain.</p>`;
  return `<div class="why-body-in"><h3>Terrain clearance · Unknown</h3>
    ${lead}
    <p>A terrain result needs a reviewed lunar frame, a reviewed vertical reference, radial coverage in the direction and range used, and one independently checked skyline direction. Until the M4 review passes, terrain is shown as Unknown and no terrain-mode total is produced.</p>
    <p>The DEM240 profile on the Locations tab is a diagnostic. It does not change any state or any total. It is not the geometric Unknown duration, which is the 0 h or other value in Details.</p>
    <p>Observer reference altitude in the saved inputs: ${esc(heights)}. These are the practice request values and not a reviewed surface height.</p></div>`;
}

function whyKey(lane, runIndex) {
  return lane === "both" ? "both" : `${lane}:${runIndex}`;
}

function whyBodyHtml() {
  const key = state.why;
  if (!key) return '<p class="why-hint">Choose a question to see the range, the rule, and the saved rows behind it.</p>';
  if (key === "terrain") return whyTerrainHtml();
  if (key === "both") return state.runs.map((run, i) => whyLaneHtml(i, "both")).join("");
  const [lane, site] = key.split(":");
  return whyLaneHtml(Number(site), lane);
}

function whyResultHtml() {
  if (!state.runs.length || !sharedSampleCount()) return "";
  const { sun, both } = headlineSeconds();
  const names = state.runs.map(siteName);
  const buttons = [];
  names.forEach((name, i) => buttons.push({ key: whyKey("sun", i), text: `Why ${name} ${terrainMode() ? "Unknown" : fmtDuration(sun[i])}?` }));
  const bothLabel = both.every((v) => v === both[0]) ? fmtDuration(both[0]) : both.map(fmtDuration).join(" / ");
  buttons.push({ key: "both", text: `Why both centres ${bothLabel}?` });
  buttons.push({ key: "terrain", text: "Why terrain Unknown?" });
  if (state.why && !buttons.some((b) => b.key === state.why)) {
    const [lane, site] = state.why.split(":");
    buttons.push({ key: state.why, text: `Why ${siteName(state.runs[Number(site)] || state.runs[0])} ${laneName(lane)}?` });
  }
  const chips = buttons
    .map((b) => `<button type="button" class="why-q" data-why="${esc(b.key)}" aria-pressed="${state.why === b.key}">${esc(b.text)}</button>`)
    .join("");
  return `<section class="why-result" aria-label="Why this result?"><h2 class="why-h">Why this result?</h2>
    <div class="why-qs" role="group" aria-label="Questions">${chips}</div>
    <div class="why-body" id="why-body" aria-live="polite">${whyBodyHtml()}</div></section>`;
}

function renderWhy() {
  const host = document.getElementById("why-result");
  if (host) host.innerHTML = whyResultHtml();
}

/* ---------- Decision: is there a clear window? ---------- */

/** Clear-window facts for one run, lane and minimum length. Reads the engine intervals only. */
function windowSummary(run, lane, minHours, count) {
  const spans = mergedStates(run, lane);
  const clear = spans.filter((span) => span.state === "clear");
  const keep = clear.filter((span) => !minHours || (span.endMs - span.startMs) / 1000 >= minHours * 3600);
  const longest = clear.length ? Math.max(...clear.map((span) => span.endMs - span.startMs)) / 1000 : 0;
  const elapsed = run.payload.elapsed_seconds[lane];
  return { clear, keep, longest, elapsed, count };
}

function minPhrase(minHours) {
  if (!minHours) return "";
  return ` of ${minText(minHours)} or longer`;
}

function decisionSiteHtml(run, runIndex, sum, lane) {
  const name = siteName(run);
  const min = state.minHours;
  let body;
  if (sum.keep.length) {
    const first = sum.keep[0];
    body = `<p><strong>${sum.keep.length} ${sum.keep.length === 1 ? "window" : "windows"}</strong>${esc(minPhrase(min))}. Longest ${esc(fmtDuration(sum.longest))}.</p>
      <p class="win-hint">Open the Windows list below for every interval. First matching window:
        <button type="button" class="mini win-open" data-site="${runIndex}" data-lane="${lane}" data-utc="${esc(first.start)}" data-end="${esc(first.end)}" data-state="clear">${esc(compactUtc(first.start))} → ${esc(compactUtc(first.end))}</button></p>`;
  } else if (sum.clear.length) {
    body = `<p><strong>No clear window${esc(minPhrase(min))}.</strong> Longest clear window ${esc(fmtDuration(sum.longest))}. Choose a shorter minimum in <b>Window length</b> above.</p>`;
  } else if (sum.elapsed.clear === 0 && sum.elapsed.blocked === 0 && sum.elapsed.unknown > 0) {
    body = `<p><strong>Unknown.</strong> Every sample is Unknown (${esc(fmtDuration(sum.elapsed.unknown))}). No clear window can be named, and none is ruled out.</p>`;
  } else {
    const closest = closestToZero(run, lane);
    body = `<p><strong>No clear window.</strong> Clear 0 h · Blocked ${esc(fmtDuration(sum.elapsed.blocked))} · Unknown ${esc(fmtDuration(sum.elapsed.unknown))}.</p>
      ${closest ? `<button type="button" class="mini win-closest" data-site="${runIndex}" data-lane="${lane}">Closest sampled point to 0°</button> <span class="win-hint">margin ${esc(signedDeg(closest.margin))}°</span>` : ""}`;
  }
  const why = `<button type="button" class="mini why-open" data-why="${esc(whyKey(lane, runIndex))}">Why?</button>`;
  return `<article class="dec-site"><h3>${slotBadge(runIndex)} ${esc(name)} ${why}</h3>${body}</article>`;
}

function decisionHtml() {
  const lane = state.lane;
  const min = state.minHours;
  const sums = state.runs.map((run) => windowSummary(run, lane, min, resolvedCount(run)));
  const names = state.runs.map(siteName);
  const ok = sums.map((sum) => sum.keep.length > 0);
  const what = `${laneName(lane)} window${minPhrase(min)}`;
  const lead = state.partial ? "So far, " : "";
  let verdict;
  if (ok.every(Boolean)) verdict = `${lead}Yes. ${names.length > 1 ? "Both sites have" : names[0] + " has"} a ${what}.`;
  else if (ok.some(Boolean)) verdict = `${lead}Partly. Only ${names.filter((_, i) => ok[i]).join(" and ")} has a ${what}. ${names.filter((_, i) => !ok[i]).join(" and ")} has none.`;
  else if (sums.every((sum) => sum.elapsed.clear === 0 && sum.elapsed.blocked === 0 && sum.elapsed.unknown > 0)) verdict = `${lead}Unknown. Every sample is Unknown, so no ${what} can be named and none is ruled out.`;
  else verdict = `${lead}No. ${names.length > 1 ? "Neither site has" : names[0] + " has no"} a ${what}.`;
  const sites = state.runs.map((run, i) => decisionSiteHtml(run, i, sums[i], lane)).join("");
  return { verdict, sites, ok };
}

/** The same question for the other saved cases, so a user can pick another supported site pair or time range. */
function decisionCasesHtml() {
  const lane = state.lane;
  const min = state.minHours;
  const others = CASES.filter((c) => !(state.source === c.id && !state.live));
  const items = others.map((c) => {
    const data = state.caseData[c.id];
    if (!data) return `<li class="dec-case"><strong>${esc(c.label)}</strong> · loading saved results…</li>`;
    const first = data.runs[0].payload.scenario;
    const range = `${shortUtc(first.start_utc)} → ${shortUtc(first.end_utc)}, step ${fmtDuration(first.step_seconds)}`;
    const per = data.runs.map((run) => {
      const sum = windowSummary(run, lane, min, run.payload.samples.length);
      const text = sum.keep.length
        ? `yes, ${sum.keep.length} ${sum.keep.length === 1 ? "window" : "windows"}, longest ${fmtDuration(sum.longest)}`
        : sum.clear.length ? `no, longest clear ${fmtDuration(sum.longest)}` : "no clear time";
      return `${siteName(run)} ${text}`;
    }).join(" · ");
    return `<li class="dec-case"><div><strong>${esc(c.label)}</strong> <span class="win-hint">${esc(range)}</span></div><div>${esc(laneName(lane))}${esc(minPhrase(min))}: ${esc(per)}</div><button type="button" class="mini case-open" data-case="${esc(c.id)}">Open this case</button></li>`;
  }).join("");
  return `<h3 class="dec-sub">Other supported cases</h3><ul class="dec-cases">${items}</ul>
    <p class="win-hint">Only saved Horizons inputs are offered. Each case is a practice input, and none is an eligible submission claim. The QA fixture is synthetic and is not listed.</p>`;
}

async function ensureCaseData(c) {
  if (state.caseData[c.id]) return state.caseData[c.id];
  const comparisonUrl = new URL(c.url, document.baseURI);
  const comparison = await (await fetch(comparisonUrl)).json();
  const runs = [];
  for (const run of comparison.runs) {
    const payload = await (await fetch(new URL(run.file, comparisonUrl))).json();
    runs.push({ ...run, payload });
  }
  state.caseData[c.id] = { comparison, runs };
  return state.caseData[c.id];
}

function prefetchCases() {
  return Promise.all(CASES.map((c) => ensureCaseData(c).catch(() => null))).then(() => {
    if (state.runs.length && sharedSampleCount()) renderDecision();
  });
}

function renderDecision() {
  const host = document.getElementById("decision");
  if (!host) return;
  const ready = state.runs.length > 0 && sharedSampleCount() > 0;
  host.hidden = !ready;
  if (!ready) return;
  const view = decisionHtml();
  document.getElementById("dec-answer").innerHTML = `<p class="dec-verdict" role="status">${esc(view.verdict)}</p><div class="dec-sites">${view.sites}</div>`;
  document.getElementById("dec-cases").innerHTML = decisionCasesHtml();
  const minValue = String(state.minHours);
  const railMin = document.getElementById("min-duration");
  if (railMin) railMin.value = minValue;
}

async function openCase(id) {
  const c = CASES.find((item) => item.id === id);
  if (!c) return;
  abortLiveConsumer();
  state.liveRunId = null;
  state.liveComparisonId = null;
  state.liveMode = null;
  setLiveExport(null);
  setPipeStage("idle");
  setRunStatus("Idle. Showing " + c.label + ".");
  await loadPackage(c.url, id);
  setCaseHash(id);
}

/** Keep the open case in the address (#case=...) without adding history entries, so Back leaves the navigator. */
function setCaseHash(id) {
  try {
    history.replaceState(null, "", id === "practice" ? location.pathname + location.search : "#case=" + id);
  } catch (error) { /* file:// or sandboxed frames */ }
}

function requestedCase() {
  const match = /case=([\w-]+)/.exec(location.hash);
  return match && CASES.some((item) => item.id === match[1]) ? match[1] : null;
}

function render() {
  if (!state.runs.length || !state.runs[0].payload.samples.length || sharedSampleCount() === 0) {
    document.getElementById("show-practice").setAttribute("aria-pressed", String(state.source === "practice"));
    document.getElementById("show-qa").setAttribute("aria-pressed", String(state.source === "qa"));
    document.getElementById("show-practice30").setAttribute("aria-pressed", String(state.source === "practice30"));
    document.getElementById("show-jan03-10").setAttribute("aria-pressed", String(state.source === "jan03-10"));
    renderDecision();
    renderWhy();
    if (state.live && state.runs.length) renderWaiting();
    return;
  }
  const detailsWasOpen = document.querySelector("#answers-details .result-details")?.open ?? false;
  const last = sharedSampleCount() - 1;
  state.index = Math.max(0, Math.min(last, state.index));
  const sample = sampleAt(0);
  const onTerminal = !state.partial && state.index === last;
  const playhead = document.getElementById("playhead");
  playhead.max = String(last);
  playhead.value = String(state.index);
  playhead.setAttribute("aria-valuetext", sample.timestamp_utc + (onTerminal ? ". This sample adds 0 elapsed time." : ""));
  document.getElementById("scenario-info").innerHTML = scenarioBarHtml();
  const banner = document.getElementById("banner");
  if (state.partial && state.runEnd) {
    banner.textContent = (state.runEnd.kind === "failed" ? "Failed run. " : "Stopped run. ") + "Incomplete. Totals cover only the shared resolved interval.";
  } else if (state.partial && state.stopping) {
    banner.textContent = "Stopping. Totals are not final until the engine reports the cutoff.";
  } else if (state.partial) {
    banner.textContent = state.liveMode === "comparison"
      ? "Partial comparison. Totals cover only the shared resolved interval."
      : "Partial totals. This run is incomplete.";
  } else if (state.comparison && state.comparison.qa_fixture) {
    banner.textContent = "QA fixture. Synthetic transitions for review. Not the January practice comparison.";
  } else if (state.live) {
    banner.textContent = "Local calculation from saved Horizons inputs. Not an eligible submission claim.";
  } else {
    banner.textContent = "Practice evidence. Not an eligible submission claim.";
  }
  document.getElementById("answers").innerHTML = answerHtml();
  document.getElementById("answers-details").innerHTML = answerDetailsHtml(detailsWasOpen);
  renderWhy();
  renderDecision();
  document.getElementById("readout").innerHTML = readoutHtml();
  renderTimeline();
  document.getElementById("windows").innerHTML = windowsHtml();
  document.getElementById("verdict").innerHTML = verdictHtml();
  updateContextMap();
  renderPreview();
  syncControls();
  syncTools();
  if (!state.live) setPipeStage("complete");
  const limits = state.comparison.limitations || [];
  document.getElementById("limits").textContent = limits.join(" ");
  document.getElementById("show-practice").setAttribute("aria-pressed", String(state.source === "practice"));
  document.getElementById("show-qa").setAttribute("aria-pressed", String(state.source === "qa"));
  document.getElementById("show-practice30").setAttribute("aria-pressed", String(state.source === "practice30"));
  document.getElementById("show-jan03-10").setAttribute("aria-pressed", String(state.source === "jan03-10"));
}

/** Chart, lanes, margins and the sticky dock line. These depend on the container width, so resize re-runs them. */
function renderTimeline() {
  document.getElementById("chart").innerHTML = chartHtml();
  document.getElementById("legend").innerHTML = legendHtml();
  document.getElementById("lanes").innerHTML = lanesHtml();
  const box = state.chartBox;
  const main = document.getElementById("explore-main");
  if (main && box) {
    main.style.setProperty("--plot-left", box.left + "px");
    main.style.setProperty("--plot-right", box.right + "px");
  }
  const dock = document.getElementById("dock-readout");
  if (dock) dock.textContent = dockReadoutText();
}

/** Every call comes from the user (buttons, slider, wheel, scrub, jump). Scrubbing pauses Follow latest. */
function move(index) {
  if (state.live && state.partial) state.follow = false;
  const last = sharedSampleCount() - 1;
  state.index = Math.max(0, Math.min(last, index));
  state.notice = state.pendingNotice;
  state.pendingNotice = "";
  render();
}

function indexForFraction(fractionValue) {
  const count = sharedSampleCount();
  const samples = state.runs[0].payload.samples.slice(0, count);
  const start = parseUtc(samples[0].timestamp_utc);
  const end = parseUtc(samples[samples.length - 1].timestamp_utc);
  const target = start + Math.min(1, Math.max(0, fractionValue)) * (end - start);
  let best = 0;
  let bestDistance = Infinity;
  samples.forEach((sample, index) => {
    const distance = Math.abs(parseUtc(sample.timestamp_utc) - target);
    if (distance < bestDistance) {
      best = index;
      bestDistance = distance;
    }
  });
  return best;
}

async function loadPackage(url, source) {
  const comparisonUrl = new URL(url, document.baseURI);
  const comparison = await (await fetch(comparisonUrl)).json();
  const runs = [];
  for (const run of comparison.runs) {
    const sourceUrl = new URL(run.file, comparisonUrl);
    const payload = await (await fetch(sourceUrl)).json();
    runs.push({ ...run, payload, sourceUrl: sourceUrl.href });
  }
  stopPlayback();
  state.preview = null;
  state.sel = null;
  state.minHours = 0;
  state.why = null;
  const minSelect = document.getElementById("min-duration");
  if (minSelect) minSelect.value = "0";
  state.notice = "";
  state.pendingNotice = "";
  state.comparison = comparison;
  state.runs = runs;
  state.index = 0;
  state.site = 0;
  state.lane = "sun";
  state.source = source;
  state.live = false;
  state.liveMode = null;
  state.partial = false;
  state.runEnd = null;
  state.stopping = false;
  state.liveComparisonId = null;
  setLiveExport(null);
  state.siteProgress = state.runs.map((run) => run.payload.samples.length);
  render();
}

function selectTab(tabId) {
  document.querySelectorAll(".tab").forEach((tab) => {
    const on = tab.id === tabId;
    tab.setAttribute("aria-selected", String(on));
    tab.tabIndex = on ? 0 : -1;
    document.getElementById(tab.getAttribute("aria-controls")).hidden = !on;
  });
}

function bind() {
  bindTools();
  document.getElementById("terrain-toggle").addEventListener("change", (event) => {
    state.showTerrain = event.target.checked;
    document.getElementById("inspect").classList.toggle("terrain-on", state.showTerrain);
    render();
  });
  document.getElementById("follow-latest").addEventListener("change", (event) => {
    state.follow = event.target.checked;
    if (state.follow && state.live && state.partial && sharedSampleCount()) {
      state.index = sharedSampleCount() - 1;
    }
    render();
  });
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => selectTab(tab.id));
    tab.addEventListener("keydown", (event) => {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      event.preventDefault();
      const tabs = Array.from(document.querySelectorAll(".tab"));
      const next = tabs[(tabs.indexOf(tab) + (event.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
      selectTab(next.id);
      next.focus();
    });
  });
  document.getElementById("pin-key").addEventListener("click", (event) => {
    const hit = event.target.closest("[data-site]");
    if (hit) selectSiteFromScene(Number(hit.dataset.site));
  });
  const jumpHandler = (event) => {
    const jump = event.target.closest(".win-jump");
    if (jump) {
      jumpToUtc(Number(jump.dataset.site), jump.dataset.lane, jump.dataset.utc);
      return true;
    }
    const closest = event.target.closest(".win-closest");
    if (closest) {
      jumpToClosest(Number(closest.dataset.site), closest.dataset.lane);
      return true;
    }
    const open = event.target.closest(".win-open");
    if (open) {
      selectWindow(Number(open.dataset.site), open.dataset.lane, open.dataset.utc, open.dataset.end, open.dataset.state);
      return true;
    }
    return false;
  };
  document.getElementById("min-duration").addEventListener("change", (event) => {
    state.minHours = Number(event.target.value);
    if (state.sel && state.sel.state === "clear" && state.minHours && (parseUtc(state.sel.end) - parseUtc(state.sel.start)) / 1000 < state.minHours * 3600) state.sel = null;
    if (sharedSampleCount()) render();
  });
  document.getElementById("windows").addEventListener("click", jumpHandler);
  document.getElementById("answers").addEventListener("click", (event) => {
    if (!jumpHandler(event)) return;
    if (event.target.closest(".win-scroll")) document.getElementById("explore").scrollIntoView({ behavior: "smooth", block: "start" });
  });
  document.getElementById("decision").addEventListener("click", (event) => {
    if (jumpHandler(event)) return;
    const why = event.target.closest(".why-open");
    if (why) {
      state.why = why.dataset.why;
      renderWhy();
      document.getElementById("why-result").scrollIntoView({ block: "start" });
      return;
    }
    const open = event.target.closest(".case-open");
    if (open) openCase(open.dataset.case).catch((error) => setRunStatus("Failed to load. " + error));
  });
  document.getElementById("why-result").addEventListener("click", (event) => {
    const question = event.target.closest(".why-q");
    if (question) {
      state.why = state.why === question.dataset.why ? null : question.dataset.why;
      renderWhy();
      return;
    }
    const jump = event.target.closest(".why-jump");
    if (jump) jumpToSample(Number(jump.dataset.site), jump.dataset.lane, Number(jump.dataset.index));
  });
  document.getElementById("sky-stage").addEventListener("click", jumpHandler);
  document.getElementById("readout").addEventListener("click", (event) => {
    const chip = event.target.closest(".ro-site");
    if (!chip) return;
    state.site = Number(chip.dataset.site);
    render();
  });
  document.getElementById("prev").addEventListener("click", () => move(state.index - stepSamples()));
  document.getElementById("next").addEventListener("click", () => move(state.index + stepSamples()));
  document.getElementById("playhead").addEventListener("input", (event) => move(Number(event.target.value)));
  document.getElementById("show-practice").addEventListener("click", () => {
    abortLiveConsumer();
    state.liveRunId = null;
    state.liveComparisonId = null;
    state.liveMode = null;
    setLiveExport(null);
    setPipeStage("idle");
    setRunStatus("Idle. Showing the witnessed practice comparison.");
    loadPackage(PRACTICE_URL, "practice").then(() => setCaseHash("practice"));
  });
  document.getElementById("show-practice30").addEventListener("click", () => {
    openCase("practice30").catch((error) => setRunStatus("Failed to load. " + error));
  });
  document.getElementById("show-jan03-10").addEventListener("click", () => {
    openCase("jan03-10").catch((error) => setRunStatus("Failed to load. " + error));
  });
  document.getElementById("show-qa").addEventListener("click", () => {
    abortLiveConsumer();
    state.liveRunId = null;
    state.liveComparisonId = null;
    state.liveMode = null;
    setLiveExport(null);
    setPipeStage("idle");
    setRunStatus("Idle. Showing the QA fixture.");
    loadPackage(QA_URL, "qa");
  });
  document.getElementById("start-run").addEventListener("click", () => {
    document.getElementById("run-more").open = false;
    setPipeStage("loading");
    const token = ++state.runToken;
    startLiveRun()
      .catch((error) => {
        if (error && error.name === "AbortError") return;
        setPipeStage("idle");
        setRunStatus("Failed. " + error);
      })
      .finally(() => {
        if (token === state.runToken) setRunning(false);
      });
  });
  document.getElementById("play-toggle").addEventListener("click", togglePlayback);
  document.addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-preview]");
    if (trigger) {
      openPreview({ kind: "body", site: Number(trigger.dataset.site), body: trigger.dataset.body });
      return;
    }
    const evidence = event.target.closest("[data-evidence]");
    if (evidence && state.runs.length) {
      const site = evidence.dataset.site !== undefined ? Number(evidence.dataset.site) : state.site;
      openPreview({ kind: "evidence", site });
      return;
    }
    const zoomBtn = event.target.closest("[data-pv-zoom]");
    if (zoomBtn) {
      const kind = zoomBtn.dataset.pvZoom;
      setPreviewZoom(kind === "in" ? state.pvZoom + PV_ZOOM_STEP : kind === "out" ? state.pvZoom - PV_ZOOM_STEP : 1);
      return;
    }
    if (event.target.closest(".pv-close") || event.target.id === "preview-backdrop") {
      closePreview();
      return;
    }
    if (event.target.closest(".pv-evidence") && state.preview) {
      openPreview({ kind: "evidence", site: state.preview.site, lane: state.preview.body });
    }
  });
  document.getElementById("cancel-run").addEventListener("click", () => {
    cancelLiveRun().catch((error) => setRunStatus("Cancel failed. " + error));
  });
  document.getElementById("lanes").addEventListener("click", (event) => {
    const segment = event.target.closest(".seg");
    const track = event.target.closest(".lane-track");
    if (!track) return;
    if (segment) {
      selectWindow(Number(segment.dataset.site), segment.dataset.lane, segment.dataset.utc, segment.dataset.end, segment.dataset.state);
      return;
    }
    state.site = Number(track.dataset.site);
    const rect = track.getBoundingClientRect();
    move(indexForFraction((event.clientX - rect.left) / rect.width));
  });
  // Chart: click or drag to move the shared playhead. Fraction is measured against the plot area only.
  const chartHost = document.getElementById("chart");
  const chartIndex = (event) => {
    const svg = chartHost.querySelector("svg");
    const box = state.chartBox;
    if (!svg || !box) return null;
    const rect = svg.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * box.W;
    return indexForFraction((x - box.left) / (box.W - box.left - box.right));
  };
  let chartDrag = false;
  chartHost.addEventListener("pointerdown", (event) => {
    if (event.button != null && event.button !== 0) return;
    const index = chartIndex(event);
    if (index === null) return;
    chartDrag = true;
    try { chartHost.setPointerCapture(event.pointerId); } catch (_e) { /* ignore */ }
    move(index);
  });
  chartHost.addEventListener("pointermove", (event) => {
    if (!chartDrag) return;
    const index = chartIndex(event);
    if (index !== null && index !== state.index) move(index);
  });
  const endChartDrag = (event) => {
    chartDrag = false;
    try { chartHost.releasePointerCapture(event.pointerId); } catch (_e) { /* ignore */ }
  };
  chartHost.addEventListener("pointerup", endChartDrag);
  chartHost.addEventListener("pointercancel", endChartDrag);
  let resizeTimer = null;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      if (state.runs.length && sharedSampleCount()) renderTimeline();
    }, 120);
  });
  document.getElementById("preview").addEventListener("wheel", (event) => {
    if (!event.ctrlKey) return;
    event.preventDefault();
    setPreviewZoom(state.pvZoom + (event.deltaY < 0 ? PV_ZOOM_STEP : -PV_ZOOM_STEP));
  }, { passive: false });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && state.preview) {
      closePreview();
      return;
    }
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    if (event.key === " " && !event.target.closest("input, textarea, select, a, summary, button, [role='button'], details")) {
      event.preventDefault();
      togglePlayback();
      return;
    }
    if (event.target.closest("input, textarea, select, a, summary")) return;
    if (event.key === "ArrowRight") {
      event.preventDefault();
      move(state.index + stepSamples());
    }
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      move(state.index - stepSamples());
    }
  });
}

bind();
document.getElementById("scenario").addEventListener("change", () => syncCatalogInputs(true));
loadCatalog();
initStarfield();
bindSceneInteractions();
updateContextMap();
setPipeStage("idle");
loadTerrainProfiles()
  .then(() => loadPackage(PRACTICE_URL, "practice"))
  .then(() => {
    const wanted = requestedCase();
    return wanted && wanted !== "practice" ? openCase(wanted) : null;
  })
  .then(() => prefetchCases())
  .catch((error) => {
    document.getElementById("banner").textContent = "The saved replay did not load. Serve the web directory and open /review-candidate/. " + error;
  });
