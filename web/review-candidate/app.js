"use strict";

const PRACTICE_URL = "../replay/comparison.json";
const QA_URL = "qa-comparison.json";
const SITE_NAMES = {
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
  liveRunId: null,
  liveComparisonId: null,
  liveAbort: null,
  siteProgress: [0, 0],
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

function hoursFromSeconds(seconds) {
  const hours = seconds / 3600;
  const text = Number.isInteger(hours) ? String(hours) : String(Math.round(hours * 1000) / 1000);
  return text + " h";
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
    if (reason === "missing_ephemeris") return "A saved elevation is missing, and neither centre is blocked, so both is Unknown.";
    if (reason === "missing_right_endpoint") return "The next sample has no usable angle, so this span is Unknown for both.";
    return "Both is Unknown. Saved reason: " + (reason || "not stated") + ".";
  }
  const item = sample[lane];
  const name = lane === "sun" ? "Sun centre" : "Earth centre";
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

function answerHtml() {
  if (state.live) return liveAnswerHtml();
  const overlap = state.comparison.overlap;
  const nameA = siteName(state.runs[0]);
  const nameB = siteName(state.runs[1]);
  const sunA = overlap.sun_centre_clear_seconds.site_a;
  const sunB = overlap.sun_centre_clear_seconds.site_b;
  const bothA = overlap.both_centres_clear_seconds.site_a;
  const bothB = overlap.both_centres_clear_seconds.site_b;
  let sunLead;
  if (sunA === sunB) sunLead = nameA + " and " + nameB + " had the same Sun-centre clearance.";
  else if (sunA > sunB) sunLead = nameA + " had more Sun-centre clearance than " + nameB + ".";
  else sunLead = nameB + " had more Sun-centre clearance than " + nameA + ".";
  const bothLead = bothA === 0 && bothB === 0
    ? "Neither site had both centres clear."
    : "Saved simultaneous clearance is shown for each site.";
  const unknown = state.comparison.overlap.unknown_seconds;
  const qa = state.comparison.qa_fixture
    ? '<p class="qa-banner">QA fixture. These hours are synthetic. They are not the January practice result.</p>'
    : "";
  return qa + `
    <h2 id="answers-heading">Which site had more Sun-centre clearance?</h2>
    <div class="answers">
      <article class="stat">
        <h3>Sun-centre clearance</h3>
        <p>${esc(sunLead)}</p>
        <strong>${esc(nameA)} ${esc(hoursFromSeconds(sunA))}</strong>
        <p>${esc(nameB)} ${esc(hoursFromSeconds(sunB))}</p>
        <p class="muted">Saved seconds: ${esc(sunA)} and ${esc(sunB)}. Delta (${esc(nameB)} − ${esc(nameA)}): ${esc(overlap.sun_centre_clear_seconds.delta_b_minus_a)} s.</p>
      </article>
      <article class="stat">
        <h3>Both centres clear</h3>
        <p>${esc(bothLead)}</p>
        <strong>${esc(nameA)} ${esc(hoursFromSeconds(bothA))}</strong>
        <p>${esc(nameB)} ${esc(hoursFromSeconds(bothB))}</p>
        <p class="muted">Saved seconds: ${esc(bothA)} and ${esc(bothB)}.</p>
      </article>
    </div>
    <p>Geometric Unknown duration — ${esc(nameA)} Sun ${esc(hoursFromSeconds(unknown.site_a.sun))}, Earth ${esc(hoursFromSeconds(unknown.site_a.earth))}, Both ${esc(hoursFromSeconds(unknown.site_a.both))}. ${esc(nameB)} Sun ${esc(hoursFromSeconds(unknown.site_b.sun))}, Earth ${esc(hoursFromSeconds(unknown.site_b.earth))}, Both ${esc(hoursFromSeconds(unknown.site_b.both))}.</p>
    <p>Terrain: Unknown. Reason: terrain_not_reviewed. No reviewed skyline is available. This is not the geometric Unknown duration above.</p>`;
}

function liveAnswerHtml() {
  if (state.liveMode === "comparison" && state.runs.length >= 2) {
    return liveComparisonAnswerHtml();
  }
  const run = state.runs[0];
  const name = siteName(run);
  const elapsed = run.payload.elapsed_seconds;
  const label = state.partial ? "Partial totals. This run is incomplete." : "Complete totals.";
  return `
    <h2 id="answers-heading">Sun-centre clearance for this run</h2>
    <p class="${state.partial ? "qa-banner" : "banner"}">${esc(label)}</p>
    <article class="stat">
      <h3>${esc(name)}</h3>
      <strong>Sun-centre clear ${esc(hoursFromSeconds(elapsed.sun.clear))}</strong>
      <p>Both centres clear ${esc(hoursFromSeconds(elapsed.both.clear))}</p>
      <p class="muted">Saved seconds: Sun clear ${esc(elapsed.sun.clear)}, Both clear ${esc(elapsed.both.clear)}, Unknown ${esc(elapsed.both.unknown)}.</p>
    </article>
    <p>Terrain: Unknown. Reason: terrain_not_reviewed. This is not the geometric Unknown duration.</p>`;
}

function liveComparisonAnswerHtml() {
  const nameA = siteName(state.runs[0]);
  const nameB = siteName(state.runs[1]);
  const overlap = state.comparison.overlap;
  const sunA = overlap.sun_centre_clear_seconds.site_a;
  const sunB = overlap.sun_centre_clear_seconds.site_b;
  const bothA = overlap.both_centres_clear_seconds.site_a;
  const bothB = overlap.both_centres_clear_seconds.site_b;
  const unknown = overlap.unknown_seconds;
  const label = state.partial
    ? "Partial comparison totals. Only the shared resolved interval is counted. Pending samples are not Unknown."
    : "Complete comparison totals.";
  const progress = `${nameA} ${state.siteProgress[0]} samples. ${nameB} ${state.siteProgress[1]} samples. Shared ${sharedSampleCount()}.`;
  return `
    <h2 id="answers-heading">Which site had more Sun-centre clearance?</h2>
    <p class="${state.partial ? "qa-banner" : "banner"}">${esc(label)}</p>
    <p class="muted">${esc(progress)}</p>
    <div class="answers">
      <article class="stat">
        <h3>Sun-centre clearance</h3>
        <strong>${esc(nameA)} ${esc(hoursFromSeconds(sunA))}</strong>
        <p>${esc(nameB)} ${esc(hoursFromSeconds(sunB))}</p>
        <p class="muted">Seconds: ${esc(sunA)} and ${esc(sunB)}. Delta (${esc(nameB)} − ${esc(nameA)}): ${esc(overlap.sun_centre_clear_seconds.delta_b_minus_a)} s.</p>
      </article>
      <article class="stat">
        <h3>Both centres clear</h3>
        <strong>${esc(nameA)} ${esc(hoursFromSeconds(bothA))}</strong>
        <p>${esc(nameB)} ${esc(hoursFromSeconds(bothB))}</p>
        <p class="muted">Seconds: ${esc(bothA)} and ${esc(bothB)}.</p>
      </article>
    </div>
    <p>Geometric Unknown duration — ${esc(nameA)} Sun ${esc(hoursFromSeconds(unknown.site_a.sun))}, Earth ${esc(hoursFromSeconds(unknown.site_a.earth))}, Both ${esc(hoursFromSeconds(unknown.site_a.both))}. ${esc(nameB)} Sun ${esc(hoursFromSeconds(unknown.site_b.sun))}, Earth ${esc(hoursFromSeconds(unknown.site_b.earth))}, Both ${esc(hoursFromSeconds(unknown.site_b.both))}.</p>
    <p>Terrain: Unknown. Reason: terrain_not_reviewed. No reviewed skyline is available. This is not the geometric Unknown duration above.</p>`;
}

function extent() {
  let min = 0;
  let max = 0;
  state.runs.forEach((run) => {
    run.payload.samples.forEach((sample) => {
      ["sun", "earth"].forEach((body) => {
        const elevation = sample[body].elevation_deg;
        if (typeof elevation !== "number") return;
        min = Math.min(min, elevation);
        max = Math.max(max, elevation);
      });
    });
  });
  const pad = Math.max(0.4, (max - min) * 0.12);
  return { min: min - pad, max: max + pad };
}

function chartHtml() {
  const window = sharedWindow();
  if (window.mismatch) return "<p class=\"banner\">The two runs do not share a window, so no shared elevation scale is drawn.</p>";
  const box = { width: 960, height: 280, left: 56, right: 16, top: 16, bottom: 36 };
  const plotWidth = box.width - box.left - box.right;
  const plotHeight = box.height - box.top - box.bottom;
  const range = extent();
  const xOf = (iso) => box.left + ((parseUtc(iso) - window.start) / (window.end - window.start)) * plotWidth;
  const yOf = (elevation) => box.top + ((range.max - elevation) / (range.max - range.min)) * plotHeight;
  const series = [
    [0, "sun", ""],
    [0, "earth", ""],
  ];
  if (state.runs[1]) {
    series.push([1, "sun", "6 4"], [1, "earth", "2 3"]);
  }
  const paths = series.map(([runIndex, body, dash]) => {
    let d = "";
    let drawing = false;
    state.runs[runIndex].payload.samples.forEach((sample) => {
      const elevation = sample[body].elevation_deg;
      if (typeof elevation !== "number") {
        drawing = false;
        return;
      }
      d += (drawing ? "L" : "M") + xOf(sample.timestamp_utc).toFixed(1) + " " + yOf(elevation).toFixed(1) + " ";
      drawing = true;
    });
    const colour = body === "sun" ? "#f0cb8a" : "#9cc4ff";
    return `<path d="${d}" fill="none" stroke="${colour}" stroke-width="2" stroke-dasharray="${dash}"></path>`;
  }).join("");
  const zeroY = yOf(0);
  const playX = xOf(sampleAt(0).timestamp_utc);
  const ticks = [range.min, 0, range.max].map((value) => {
    const y = yOf(value);
    return `<text x="8" y="${y + 4}">${value === 0 ? "0°" : value.toFixed(1) + "°"}</text>`;
  }).join("");
  return `<svg class="chart" viewBox="0 0 ${box.width} ${box.height}" role="img" aria-label="Shared elevation chart. The dashed horizontal line is the 0 degree horizon. Solid lines are Site A. Dashed lines are Site B.">
    <line x1="${box.left}" y1="${zeroY}" x2="${box.width - box.right}" y2="${zeroY}" stroke="#f0f4f8" stroke-dasharray="4 4"></line>
    <text x="${box.left + 8}" y="${zeroY > box.top + 18 ? zeroY - 6 : zeroY + 14}">0° horizon</text>
    ${paths}
    <line x1="${playX}" y1="${box.top}" x2="${playX}" y2="${box.height - box.bottom}" stroke="#ffffff"></line>
    ${ticks}
    <text x="${box.left}" y="${box.height - 10}">${esc(window.startUtc)}</text>
    <text x="${box.width - 210}" y="${box.height - 10}">${esc(window.endUtc)} · 0 s</text>
  </svg>`;
}

function legendHtml() {
  const nameA = siteName(state.runs[0]);
  const lines = [
    `<span>${esc(nameA)} Sun — solid gold</span>`,
    `<span>${esc(nameA)} Earth — solid blue</span>`,
  ];
  if (state.runs[1]) {
    const nameB = siteName(state.runs[1]);
    lines.push(`<span>${esc(nameB)} Sun — dashed gold</span>`, `<span>${esc(nameB)} Earth — dashed blue</span>`);
  }
  return lines.join("");
}

function fraction(iso, window) {
  return (parseUtc(iso) - window.start) / (window.end - window.start);
}

function lanesHtml() {
  const window = sharedWindow();
  if (window.mismatch) return "";
  const play = fraction(sampleAt(0).timestamp_utc, window) * 100;
  return state.runs.map((run, runIndex) => {
    const rows = ["sun", "earth", "both"].map((lane) => {
      const intervals = run.payload.intervals.filter((interval) => interval.lane === lane);
      const segments = intervals.map((interval) => {
        const left = fraction(interval.start_utc, window) * 100;
        const width = (fraction(interval.end_utc, window) - fraction(interval.start_utc, window)) * 100;
        const label = interval.state.charAt(0).toUpperCase() + interval.state.slice(1);
        return `<button type="button" class="seg ${esc(interval.state)}" style="left:${left}%;width:${width}%" data-site="${runIndex}" data-lane="${esc(lane)}" data-utc="${esc(interval.start_utc)}" title="${esc(label)} ${esc(interval.start_utc)} to ${esc(interval.end_utc)}"><span>${esc(label)}</span></button>`;
      }).join("");
      return `<div class="lane-row"><span>${esc(lane === "both" ? "Both" : lane === "sun" ? "Sun" : "Earth")}</span><div class="lane-track" data-site="${runIndex}">${segments}<span class="play-mark" style="left:${play}%"></span></div></div>`;
    }).join("");
    return `<div class="site-lanes"><h3>${esc(siteName(run))}</h3>${rows}</div>`;
  }).join("") + `
    <div class="swatches" aria-label="State patterns">
      <span class="swatch"><i class="chip clear"></i> Clear</span>
      <span class="swatch"><i class="chip blocked"></i> Blocked</span>
      <span class="swatch"><i class="chip unknown"></i> Unknown</span>
    </div>`;
}

function fact(label, value) {
  const shown = show(value);
  const text = shown === "null" ? "null" : shown + "°";
  return `<div><span>${esc(label)}</span><strong>${esc(text)}</strong></div>`;
}

function bodyFacts(item) {
  return `<div class="facts">${fact("Elevation", item.elevation_deg)}${fact("Horizon", item.horizon_deg)}${fact("Margin", item.margin_deg)}</div>`;
}

function whyHtml() {
  const cards = state.runs.map((run, runIndex) => {
    const sample = sampleAt(runIndex);
    const selected = runIndex === state.site;
    const item = sample[state.lane];
    const extra = state.lane === "both"
      ? "<p>Sun centre</p>" + bodyFacts(sample.sun) + "<p>Earth centre</p>" + bodyFacts(sample.earth)
      : bodyFacts(item);
    return `<article class="card why-card${selected ? " selected" : ""}">
      <h3>${esc(siteName(run))}</h3>
      <p>${esc(item.label || "Both centres clear")} · <span class="state-word ${esc(item.state)}">${esc(item.state)}</span></p>
      ${extra}
      <p>${esc(explain(sample, state.lane))}</p>
      <button type="button" class="select-site" data-site="${runIndex}">Use ${esc(siteName(run))} for the evidence panel</button>
    </article>`;
  }).join("");
  const selectedRun = state.runs[state.site];
  const selectedSample = sampleAt(state.site);
  const sky = skyHtml();
  const evidence = evidenceHtml(selectedRun, selectedSample);
  return `<div class="why-layout"><div class="why-cards">${cards}</div><div>${sky}</div></div>${evidence}`;
}

function skyHtml() {
  const plots = state.runs.map((run, runIndex) => skyPlot(run, runIndex)).join("");
  return `<h3>Sky position</h3><div class="sky-pair">${plots}</div><p class="muted">Azimuth clockwise from north. The dashed circle is 0°. Markers outside it are below the horizon. No terrain skyline is drawn.</p>`;
}

function skyPlot(run, runIndex) {
  const sample = sampleAt(runIndex);
  const markers = ["sun", "earth"].map((body) => {
    const item = sample[body];
    if (typeof item.azimuth_deg !== "number" || typeof item.elevation_deg !== "number") {
      return `<text x="70" y="${body === "sun" ? 20 : 34}">${body === "sun" ? "Sun" : "Earth"} position unknown</text>`;
    }
    const horizon = 78;
    let radius = horizon * (1 - item.elevation_deg / 15);
    radius = Math.max(16, Math.min(108, radius));
    const rad = item.azimuth_deg * Math.PI / 180;
    const x = 120 + radius * Math.sin(rad);
    const y = 120 - radius * Math.cos(rad);
    const selected = runIndex === state.site && state.lane === body;
    const stroke = selected ? "#ffffff" : "#8b9cb3";
    const shape = body === "sun"
      ? `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="6" fill="#f0cb8a" stroke="${stroke}" stroke-width="2"></circle>`
      : `<rect x="${(x - 5).toFixed(1)}" y="${(y - 5).toFixed(1)}" width="10" height="10" fill="#9cc4ff" stroke="${stroke}" stroke-width="2"></rect>`;
    return `<g tabindex="0" role="button" data-site="${runIndex}" data-lane="${body}" aria-label="${body === "sun" ? "Sun" : "Earth"} at ${esc(siteName(run))}">${shape}</g>`;
  }).join("");
  const caption = ["sun", "earth"].map((body) => {
    const item = sample[body];
    const shape = body === "sun" ? "circle" : "square";
    const name = body === "sun" ? "Sun" : "Earth";
    if (typeof item.azimuth_deg !== "number" || typeof item.elevation_deg !== "number") return name + " " + shape + ": position unknown";
    return name + " " + shape + ": azimuth " + item.azimuth_deg + "°, elevation " + item.elevation_deg + "°";
  }).join("<br>");
  return `<figure class="sky-figure"><svg class="sky" viewBox="0 0 240 240" role="group" aria-label="Sky position for ${esc(siteName(run))}">
    <circle cx="120" cy="120" r="108" fill="#12182a"></circle>
    <circle cx="120" cy="120" r="78" fill="#1a2332"></circle>
    <circle cx="120" cy="120" r="78" fill="none" stroke="#f0f4f8" stroke-dasharray="4 3"></circle>
    <text x="112" y="16">N</text><text x="214" y="124">E</text><text x="112" y="232">S</text><text x="6" y="124">W</text>
    <text x="128" y="48">0°</text>
    ${markers}
  </svg>
  <figcaption><strong>${esc(siteName(run))}</strong><br>${caption}</figcaption>
  </figure>`;
}

function evidenceHtml(run, sample) {
  const observer = run.payload.scenario.observer;
  const rowName = state.comparison.qa_fixture ? "Synthetic row" : "Horizons row";
  const bodies = state.lane === "both" ? ["sun", "earth"] : [state.lane];
  const rows = bodies.map((body) => {
    const item = sample[body];
    return `<dt>${esc(item.label)} azimuth</dt><dd>${esc(show(item.azimuth_deg))}°</dd>
      <dt>${esc(rowName)}</dt><dd><code>${esc(show(item.response_line))}</code></dd>
      <dt>Source</dt><dd><code>${esc(show(item.source_ref))}</code></dd>`;
  }).join("");
  const exports = state.runs.filter((item) => item.sourceUrl).map((item) => `<a class="export" href="${esc(item.sourceUrl)}" target="_blank" rel="noopener">${esc(siteName(item))} JSON</a>`).join("");
  return `<details id="evidence">
    <summary>Evidence: azimuth, ${esc(rowName.toLowerCase())}, observer, run ID, and JSON export</summary>
    <dl class="evidence">
      ${rows}
      <dt>Observer</dt><dd>${esc(observer.longitude_east_deg)}° E, ${esc(observer.latitude_deg)}° N, ${esc(observer.reference_altitude_km)} km. Centre body ${esc(observer.center_body_id)}.</dd>
      <dt>Run ID</dt><dd><code>${esc(run.payload.run_id)}</code></dd>
      <dt>code_revision</dt><dd><code>${esc(run.payload.code_revision)}</code></dd>
      <dt>Saved reason code</dt><dd><code>${esc(show(sample[state.lane].reason))}</code></dd>
    </dl>
    <div class="exports">${exports}</div>
  </details>`;
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
  pipe.querySelectorAll("li").forEach((item) => {
    const index = order.indexOf(item.dataset.stage);
    item.classList.toggle("is-focus", item.dataset.stage === stage);
    item.classList.toggle("is-live", index >= 0 && current >= 0 && index <= current && item.dataset.stage !== stage);
  });
}

function polarPin(lonEast, latDeg) {
  const colat = Math.max(0.05, 90 + latDeg);
  const radius = Math.min(42, colat * 4.8);
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

function updateContextMap() {
  const svg = document.getElementById("context-pins");
  const caption = document.getElementById("context-caption");
  if (!svg) return;
  const sites = contextSitesFromRuns();
  svg.innerHTML = sites.map((site, index) => {
    const point = polarPin(site.longitude_east_deg, site.latitude_deg);
    const fill = site.role === "a" ? "#e3b34a" : "#5ba8d8";
    const selected = index === state.site ? " is-selected" : "";
    return `<g class="pin-hit${selected}" data-site="${index}" tabindex="0" role="button" aria-label="Select ${esc(site.name)}">
      <circle cx="${point.x.toFixed(2)}" cy="${point.y.toFixed(2)}" r="3.2" fill="${fill}" stroke="#fff" stroke-width="0.6"></circle>
      <text x="${(point.x + 3.6).toFixed(2)}" y="${(point.y + 1.1).toFixed(2)}" fill="#f6f6f6" font-size="3.2">${esc(site.name)}</text>
    </g>`;
  }).join("");
  if (caption) {
    const labels = sites.map((site) => `${site.name} ${site.longitude_east_deg}°E, ${site.latitude_deg}°N`).join(" · ");
    caption.textContent = "South-pole context · approximate pins · click to select site · not a DEM · " + labels;
  }
  publishSceneEvent("lunar:scene-updated", {
    sites,
    selectedSite: state.site,
    sampleIndex: state.index,
    partial: state.partial,
    live: state.live,
  });
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

function bindSceneInteractions() {
  const stage = document.getElementById("scene-stage");
  const pins = document.getElementById("context-pins");
  if (!stage || !pins) return;
  pins.addEventListener("click", (event) => {
    const hit = event.target.closest("[data-site]");
    if (!hit) return;
    selectSiteFromScene(Number(hit.dataset.site));
  });
  pins.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const hit = event.target.closest("[data-site]");
    if (!hit) return;
    event.preventDefault();
    selectSiteFromScene(Number(hit.dataset.site));
  });
  stage.addEventListener("click", (event) => {
    if (event.target.closest("[data-site]")) return;
    const host = document.getElementById("context-map");
    if (!host) return;
    const rect = host.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    if (x < 0 || y < 0 || x > 1 || y > 1) return;
    // Horizontal position maps to shared playhead; vertical reserved for future 3D elevation look.
    scrubFromSceneFraction(x);
  });
  publishSceneEvent("lunar:scene-ready", {
    host: "scene-3d",
    interim: "pia13523-context",
    supports: ["site-select", "scrub-fraction", "stream-target"],
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
    samples: [],
    intervals: [],
    elapsed_seconds: emptyElapsed(),
  };
}

function abortLiveConsumer() {
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
      }),
    }];
    state.index = 0;
    state.site = 0;
    state.lane = "sun";
    state.siteProgress = [0];
    setLiveExport(null);
    setRunStatus("Calculating. Run " + event.run_id + ". Result " + event.result_run_id + ".");
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
    state.index = Math.max(0, payload.samples.length - 1);
    setRunStatus("Calculating. Run " + event.run_id + ". Samples " + event.samples_emitted + ".");
    render();
    return;
  }
  if (event.event === "complete") {
    setPipeStage("complete");
    state.partial = false;
    state.runs[0].payload = event.result;
    state.runs[0].sourceUrl = "#";
    state.siteProgress = [event.result.samples.length];
    setLiveExport(event.result);
    setRunStatus("Complete. Run " + event.run_id + ". Result " + event.result_run_id + ".");
    render();
    return;
  }
  if (event.event === "cancelled") {
    setPipeStage("shared");
    state.partial = true;
    if (state.runs[0]) {
      state.runs[0].payload.elapsed_seconds = event.elapsed_seconds || state.runs[0].payload.elapsed_seconds;
      state.runs[0].payload.intervals = event.intervals || state.runs[0].payload.intervals;
    }
    setRunStatus("Cancelled. Run " + event.run_id + ". Partial samples " + event.samples_emitted + ".");
    render();
    return;
  }
  if (event.event === "error") {
    setPipeStage("shared");
    state.partial = true;
    if (state.runs[0] && event.elapsed_seconds) {
      state.runs[0].payload.elapsed_seconds = event.elapsed_seconds;
      state.runs[0].payload.intervals = event.intervals || state.runs[0].payload.intervals;
    }
    setRunStatus("Failed. Run " + event.run_id + ". " + (event.message || "error"));
    render();
  }
}

function applyLiveComparisonEvent(event) {
  if (state.liveComparisonId && event.comparison_id && event.comparison_id !== state.liveComparisonId) return;
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
    setLiveExport(null);
    setRunStatus("Calculating. Comparison " + event.comparison_id + ".");
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
    state.index = Math.max(0, shared - 1);
    setRunStatus(
      "Calculating. Comparison " + event.comparison_id
      + ". " + siteName(state.runs[0]) + " " + state.siteProgress[0]
      + ", " + siteName(state.runs[1]) + " " + state.siteProgress[1]
      + ", shared " + shared + "."
    );
    publishSceneEvent("lunar:stream-batch", {
      comparison_id: event.comparison_id,
      role: event.role,
      shared_samples: shared,
      partial: true,
    });
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
    state.index = Math.max(0, sharedSampleCount() - 1);
    setLiveExport(event.comparison, event.comparison_id + "-comparison.json");
    setRunStatus(
      "Complete. Comparison " + event.comparison_id
      + ". Results " + event.result_run_id_a + " / " + event.result_run_id_b + "."
    );
    publishSceneEvent("lunar:stream-complete", {
      comparison_id: event.comparison_id,
      result_run_id_a: event.result_run_id_a,
      result_run_id_b: event.result_run_id_b,
    });
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
    state.siteProgress = [event.samples_emitted_a || state.siteProgress[0] || 0, event.samples_emitted_b || state.siteProgress[1] || 0];
    setLiveExport(null);
    const kind = event.event === "cancelled" ? "Cancelled" : "Failed";
    setRunStatus(
      kind + ". Comparison " + event.comparison_id + ". "
      + (event.message || "") + " Shared samples " + (event.shared_samples || 0) + "."
    );
    render();
  }
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
      if (line) onEvent(JSON.parse(line));
      newline = buffer.indexOf("\n");
    }
  }
  const trailing = buffer.trim();
  if (trailing) onEvent(JSON.parse(trailing));
}

async function startLiveRun() {
  abortLiveConsumer();
  const scenario = document.getElementById("scenario").value;
  const fail = document.getElementById("fail-test").checked;
  setLiveExport(null);
  if (scenario === "practice-48h") {
    await startLiveComparison(fail);
    return;
  }
  const body = {
    scenario,
    batch_size: 4,
    pause_seconds: 0.05,
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

async function startLiveComparison(fail) {
  const body = {
    pair: "practice-48h",
    batch_size_a: 3,
    batch_size_b: 5,
    pause_seconds: 0.02,
  };
  if (fail) body.fail_after_batches_a = 1;
  setRunStatus("Starting practice-48h comparison.");
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
  if (state.liveMode === "comparison" && state.liveComparisonId) {
    await fetch("/api/comparisons/" + state.liveComparisonId + "/cancel", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
    setRunStatus("Cancel requested for comparison " + state.liveComparisonId + ".");
    return;
  }
  await fetch("/api/runs/" + state.liveRunId + "/cancel", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: "{}",
  });
  setRunStatus("Cancel requested for run " + state.liveRunId + ".");
}

function render() {
  if (!state.runs.length || !state.runs[0].payload.samples.length || sharedSampleCount() === 0) {
    document.getElementById("show-practice").setAttribute("aria-pressed", String(state.source === "practice"));
    document.getElementById("show-qa").setAttribute("aria-pressed", String(state.source === "qa"));
    return;
  }
  const evidenceWasOpen = document.getElementById("evidence")?.open ?? false;
  const last = sharedSampleCount() - 1;
  state.index = Math.max(0, Math.min(last, state.index));
  const sample = sampleAt(0);
  const onTerminal = !state.partial && state.index === last;
  document.getElementById("utc").textContent = sample.timestamp_utc;
  const playhead = document.getElementById("playhead");
  playhead.max = String(last);
  playhead.value = String(state.index);
  playhead.setAttribute("aria-valuetext", sample.timestamp_utc + (onTerminal ? ". This sample adds 0 elapsed seconds." : ""));
  const zero = document.getElementById("zero-note");
  zero.textContent = state.partial
    ? "Partial run. Playhead stays inside the shared resolved samples. Pending is not Unknown."
    : "The last sample adds 0 elapsed seconds.";
  zero.className = onTerminal && !state.partial ? "note zero-on" : "note";
  const window = sharedWindow();
  const mode = document.getElementById("mode");
  const modeName = window.mode === "geometric_0deg" ? "geometric 0°" : window.mode;
  mode.textContent = "Horizon mode: " + modeName + ". Terrain: Unknown — terrain_not_reviewed. Window " + window.startUtc + " to " + window.endUtc + ".";
  const banner = document.getElementById("banner");
  if (state.partial) {
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
  document.getElementById("chart").innerHTML = chartHtml();
  document.getElementById("legend").innerHTML = legendHtml();
  document.getElementById("lanes").innerHTML = lanesHtml();
  document.getElementById("why").innerHTML = whyHtml();
  updateContextMap();
  if (!state.live) setPipeStage("complete");
  if (evidenceWasOpen) document.getElementById("evidence").open = true;
  const limits = state.comparison.limitations || [];
  document.getElementById("limits").textContent = limits.join(" ");
  document.getElementById("show-practice").setAttribute("aria-pressed", String(state.source === "practice"));
  document.getElementById("show-qa").setAttribute("aria-pressed", String(state.source === "qa"));
}

function move(index) {
  const last = sharedSampleCount() - 1;
  state.index = Math.max(0, Math.min(last, index));
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
  state.comparison = comparison;
  state.runs = runs;
  state.index = 0;
  state.site = 0;
  state.lane = "sun";
  state.source = source;
  state.live = false;
  state.liveMode = null;
  state.partial = false;
  state.liveComparisonId = null;
  state.siteProgress = state.runs.map((run) => run.payload.samples.length);
  render();
}

function bind() {
  document.getElementById("prev").addEventListener("click", () => move(state.index - 1));
  document.getElementById("next").addEventListener("click", () => move(state.index + 1));
  document.getElementById("playhead").addEventListener("input", (event) => move(Number(event.target.value)));
  document.getElementById("show-practice").addEventListener("click", () => {
    abortLiveConsumer();
    state.liveRunId = null;
    state.liveComparisonId = null;
    state.liveMode = null;
    setLiveExport(null);
    setPipeStage("idle");
    setRunStatus("Idle. Showing the witnessed practice comparison.");
    loadPackage(PRACTICE_URL, "practice");
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
    setPipeStage("loading");
    startLiveRun().catch((error) => {
      setPipeStage("idle");
      setRunStatus("Failed. " + error);
    });
  });
  document.getElementById("cancel-run").addEventListener("click", () => {
    cancelLiveRun().catch((error) => setRunStatus("Cancel failed. " + error));
  });
  document.getElementById("lanes").addEventListener("click", (event) => {
    const segment = event.target.closest(".seg");
    const track = event.target.closest(".lane-track");
    if (!track) return;
    if (segment) {
      state.site = Number(segment.dataset.site);
      state.lane = segment.dataset.lane;
    } else {
      state.site = Number(track.dataset.site);
    }
    const rect = track.getBoundingClientRect();
    move(indexForFraction((event.clientX - rect.left) / rect.width));
  });
  document.getElementById("why").addEventListener("click", (event) => {
    const siteButton = event.target.closest(".select-site");
    if (siteButton) {
      state.site = Number(siteButton.dataset.site);
      render();
      return;
    }
    const marker = event.target.closest("[data-lane]");
    if (!marker) return;
    state.site = Number(marker.dataset.site);
    state.lane = marker.dataset.lane;
    render();
  });
  document.getElementById("why").addEventListener("keydown", (event) => {
    if (event.key !== "Enter" && event.key !== " ") return;
    const marker = event.target.closest("[data-lane]");
    if (!marker) return;
    event.preventDefault();
    state.site = Number(marker.dataset.site);
    state.lane = marker.dataset.lane;
    render();
  });
  document.getElementById("chart").addEventListener("click", (event) => {
    const svg = event.target.closest("svg");
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const viewWidth = 960;
    const left = 56;
    const right = 16;
    const plotWidth = viewWidth - left - right;
    const x = ((event.clientX - rect.left) / rect.width) * viewWidth;
    move(indexForFraction((x - left) / plotWidth));
  });
  document.addEventListener("keydown", (event) => {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    if (event.target.closest("input, textarea, select, a, summary")) return;
    if (event.key === "ArrowRight") {
      event.preventDefault();
      move(state.index + 1);
    }
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      move(state.index - 1);
    }
  });
}

bind();
initStarfield();
bindSceneInteractions();
updateContextMap();
setPipeStage("idle");
loadPackage(PRACTICE_URL, "practice").catch((error) => {
  document.getElementById("banner").textContent = "The saved replay did not load. Serve the web directory and open /review-candidate/. " + error;
});
