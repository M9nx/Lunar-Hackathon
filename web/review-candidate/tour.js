/* Guided tour for the navigator. Offline, no dependencies.
   Reads the page and scrolls; never changes a result.
   Opens from the header Guide button or ?tour=1. First visit shows the welcome
   dialog once (never under browser automation). */
(function () {
  "use strict";

  const SEEN_KEY = "lunar-navigator-tour-seen";

  const STEPS = [
    {
      target: ".header-nav",
      title: "Move around the release",
      body: "<b>Overview</b> is the landing page. <b>Guide</b> is this tour. <b>Manual</b> and <b>Reference</b> are the written docs. <b>Replay</b> is the witnessed 0° package. The brand on the left always returns to Overview.",
    },
    {
      target: "#ctl-data",
      pick: ".ctl-group",
      title: "Choose a saved case",
      body: "Each button opens a saved comparison. <b>Practice replay</b> is the default 48 h pair (Site04 vs Malapert). The 30-day and Jan 3–10 cases use the same engine over longer windows. The <b>QA fixture</b> is synthetic and only exercises the Unknown rules.",
    },
    {
      target: "#run-more",
      title: "Live run and options",
      open: "#run-more",
      body: "Open this panel to stream a calculation from saved Horizons files. Pick a scenario, press <b>Start stream</b>, and use <b>Stop</b> to cancel. It never contacts JPL. The idle line under the bar reports what the last start or stop did.",
    },
    {
      target: "#catalog-box",
      title: "Catalog range and horizon",
      open: "#run-more",
      body: "Catalog entries let you choose a UTC From/To inside the saved coverage. Named scenarios keep their own range. <b>Horizon</b> chooses Geometric 0° (what this release claims) or Terrain (Unknown until a reviewed skyline exists).",
    },
    {
      target: ".ctl-speed",
      title: "Playback speed",
      open: "#run-more",
      body: "This slider only paces streaming and Play. It never changes a classification, a total, or an Unknown duration.",
    },
    {
      target: "#live-chip",
      title: "Replay or live",
      body: "The header chip shows whether you are looking at a <b>saved replay</b> or a <b>live</b> calculation. Practice / centre-ray / terrain Unknown labels live on the result itself, not here.",
    },
    {
      target: "#scenario-bar",
      title: "What this case is",
      body: "Sites, UTC range, sample step and horizon mode for the open case. The line under it says whether the inputs are practice evidence or a live run. Nothing here is a second copy of the totals.",
    },
    {
      target: ".ask-bar",
      title: "Clearance and window length",
      body: "This is the one place that sets what the rest of the page looks at. <b>Clearance</b> chooses Sun centre, Earth centre, or Both centres. <b>Window length</b> hides short clear windows in the decision answer and in the Windows list. Totals above stay unchanged.",
    },
    {
      target: "#answers",
      title: "Read the headline",
      body: "The big numbers are whole-window <b>Sun-centre clearance</b>. The sentence under them says which site had more. The joint line is <b>Both centres clear</b>. For every site and lane, Clear + Blocked + Unknown add up to the requested duration. A margin of 0° or less is Blocked.",
    },
    {
      target: "#answers .res-break",
      pick: ".result",
      title: "Whole window, by lane",
      body: "The table breaks Clear, Blocked and Unknown for Sun, Earth and Both at each site. Unknown is never folded into Clear or Blocked. Open <b>Details</b> under it for the raw seconds, sample counts, run IDs and the terrain reason code.",
    },
    {
      target: "#why-result",
      title: "Ask “Why this result?”",
      body: "Choose a question to see the range, the rule, and the saved Horizons rows behind the whole-window answer. The engine owns the classification. Display never recomputes a state.",
    },
    {
      target: "#decision",
      title: "Is there a clear window?",
      body: "A Yes / Partly / No / Unknown answer for the clearance and window length you set above. Each site shows a short summary and a Why? link. The full interval list lives in the Windows rail below, so it is not repeated here.",
    },
    {
      target: "#dec-cases",
      title: "Other supported cases",
      body: "The same clearance question for the other saved cases, side by side. Each row shows its own UTC range and Unknown time. <b>Open this case</b> switches the page. The QA fixture is synthetic and is not listed.",
    },
    {
      target: "#readout",
      title: "Selected UTC and margins",
      body: "The playhead time and the Clear / Blocked / Unknown state at each site for the clearance you chose. Click a site chip to select that site. When Both centres is selected, the smaller of the two margins is shown.",
    },
    {
      target: "#explore-main",
      title: "Elevation timeline",
      body: "Elevation of the chosen body (or bodies) against the 0° horizon across the shared UTC window. Click or drag to move the playhead. Solid and dashed traces are the two sites.",
    },
    {
      target: "#lanes",
      title: "Clear / Blocked / Unknown lanes",
      body: "One state track per site for the chosen clearance. Segments come from the engine intervals. Click a segment to select that window. Pending (on a live run) means not calculated yet — it is not Unknown.",
    },
    {
      target: ".windows-rail",
      title: "Windows list",
      tab: "windows",
      body: "Clear intervals for the chosen clearance, filtered by Window length. Unknown spans are listed separately. Click a row to put the playhead on its start.",
    },
    {
      target: "#panel-locations",
      title: "Locations map",
      tab: "locations",
      body: "South-pole mosaic with a pin for each observer. Click a pin to select that site. Drag on the map to change UTC. The DEM profile on this tab is diagnostic only and does not change any state.",
    },
    {
      target: "#time-dock",
      title: "Shared playhead",
      body: "Previous / Play / Next, the scrubber, jump to the previous or next change of the shown lane at the selected site, and the Step size. Keys: <kbd>←</kbd> <kbd>→</kbd> step, <kbd>Space</kbd> play, <kbd>Esc</kbd> close a card.",
    },
    {
      target: "#verdict",
      title: "Why this state?",
      body: "A plain-language reading of the selected sample: where each centre sits relative to 0°, and whether both centres are clear. This is the playhead answer. The whole-window totals above are a different measure.",
    },
    {
      target: "#scene-stage",
      title: "Sky at that moment",
      body: "Each plot shows the Sun and Earth centres at the playhead. The dashed ring is the 0° horizon that classifies. The centre of the default plot is +15°, not the zenith. Drag or use the mouse wheel to step samples.",
    },
    {
      target: "#sky-tools",
      title: "Sky view controls",
      body: "<b>Scale</b> changes the elevation range drawn (±5°, ±15°, ±30°, or full sky). <b>More view options</b> holds path trails, sites shown, decimals, and the terrain diagnostic style. <b>Reset view</b> restores the defaults. None of these change a result.",
    },
    {
      target: "#terrain-toggle",
      pick: ".sky-legend",
      title: "Terrain diagnostic",
      body: "Show the DEM skyline on the sky plots as a diagnostic only. Terrain clearance stays Unknown until a reviewed skyline passes. A populated azimuth bin does not prove radial coverage.",
    },
    {
      target: "#inspect-evidence",
      title: "View evidence",
      body: "Opens the Horizons row, observer, run ID and the JSON export for the selected sample. Use this when a number on screen needs to be traced to a saved file.",
    },
    {
      target: "#limits",
      pick: ".shell-foot",
      title: "Limits of this release",
      body: "Centre-ray only, on practice inputs. Terrain clearance is Unknown. Submission eligibility is still pending. Product 69 is long-term context and is not a check of these windows.",
    },
  ];

  let overlay = null;
  let spot = null;
  let card = null;
  let index = -1;
  let opener = null;

  const el = (tag, cls, html) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (html != null) n.innerHTML = html;
    return n;
  };

  const remember = () => {
    try { localStorage.setItem(SEEN_KEY, "1"); } catch (e) { /* storage may be blocked */ }
  };
  const seen = () => {
    try { return localStorage.getItem(SEEN_KEY) === "1"; } catch (e) { return false; }
  };

  function ensureLayer() {
    if (overlay) return;
    overlay = el("div", "tour-layer");
    overlay.setAttribute("data-tour", "");
    spot = el("div", "tour-spot");
    spot.hidden = true;
    card = el("div", "tour-card");
    card.setAttribute("role", "dialog");
    card.setAttribute("aria-modal", "false");
    card.tabIndex = -1;
    overlay.append(spot, card);
    document.body.append(overlay);
    window.addEventListener("keydown", onKey, true);
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, { passive: true });
  }

  function close(keepFocus) {
    if (!overlay) return;
    window.removeEventListener("keydown", onKey, true);
    window.removeEventListener("resize", place);
    window.removeEventListener("scroll", place);
    overlay.remove();
    overlay = spot = card = null;
    index = -1;
    document.documentElement.classList.remove("tour-on");
    if (!keepFocus && opener && document.contains(opener)) opener.focus();
  }

  function prepare(step) {
    if (step.open) {
      const node = document.querySelector(step.open);
      if (node && "open" in node) node.open = true;
    }
    if (step.tab === "locations") {
      const tab = document.getElementById("tab-locations");
      if (tab && tab.getAttribute("aria-selected") !== "true") tab.click();
    } else if (step.tab === "windows") {
      const tab = document.getElementById("tab-windows");
      if (tab && tab.getAttribute("aria-selected") !== "true") tab.click();
    }
  }

  function welcome() {
    ensureLayer();
    index = -1;
    document.documentElement.classList.add("tour-on");
    spot.hidden = true;
    overlay.classList.add("is-dim");
    card.className = "tour-card tour-welcome";
    card.setAttribute("aria-label", "Welcome");
    card.innerHTML = `
      <h2 class="tour-h">Welcome to the Lunar Landing Site Navigator</h2>
      <p>This page asks one question for two lunar south-pole sites: is the <b>centre of the Sun</b> or of <b>Earth</b> above a flat 0° horizon, and for how long? Answers come from saved JPL Horizons data. The inputs are practice inputs, and terrain is Unknown.</p>
      <p class="tour-sub">The guide walks every control on this page in ${STEPS.length} short steps. Skip any time.</p>
      <div class="tour-actions">
        <button type="button" class="tour-btn tour-primary" data-act="start">Start guide</button>
        <button type="button" class="tour-btn" data-act="skip">Skip guide</button>
      </div>
      <label class="tour-once"><input type="checkbox" id="tour-once"> Do not show this dialog again</label>`;
    card.style.cssText = "";
    card.querySelector('[data-act="start"]').addEventListener("click", () => {
      if (card.querySelector("#tour-once").checked) remember();
      go(0);
    });
    card.querySelector('[data-act="skip"]').addEventListener("click", () => {
      if (card.querySelector("#tour-once").checked) remember();
      close();
    });
    card.querySelector('[data-act="start"]').focus();
  }

  function targetFor(step) {
    let node = document.querySelector(step.target);
    if (node && step.pick) node = node.closest(step.pick) || node;
    if (!node || node.hidden || node.closest("[hidden]")) return null;
    const r = node.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) return null;
    return node;
  }

  function go(i) {
    if (!overlay) ensureLayer();
    if (i < 0) i = 0;
    if (i >= STEPS.length) { close(); return; }
    index = i;
    const step = STEPS[i];
    prepare(step);
    document.documentElement.classList.add("tour-on");
    overlay.classList.remove("is-dim");
    const node = targetFor(step);
    card.className = "tour-card";
    card.setAttribute("aria-label", `Guide step ${i + 1} of ${STEPS.length}: ${step.title}`);
    const last = i === STEPS.length - 1;
    card.innerHTML = `
      <div class="tour-head">
        <h2 class="tour-h">${step.title}</h2>
        <button type="button" class="tour-x" data-act="close" aria-label="Close the guide">×</button>
      </div>
      <p class="tour-count">Step ${i + 1} of ${STEPS.length}</p>
      <ol class="tour-dots" aria-hidden="true">${STEPS.map((_, k) => `<li class="${k < i ? "done" : k === i ? "now" : ""}"></li>`).join("")}</ol>
      <p>${step.body}</p>
      ${node ? "" : '<p class="tour-sub">This part appears once a case is loaded.</p>'}
      <div class="tour-actions">
        <button type="button" class="tour-btn" data-act="prev"${i === 0 ? " disabled" : ""}>← Prev</button>
        <button type="button" class="tour-btn tour-link" data-act="skip">Skip</button>
        <button type="button" class="tour-btn tour-primary" data-act="next">${last ? "Finish" : "Next →"}</button>
      </div>`;
    card.querySelector('[data-act="close"]').addEventListener("click", () => close());
    card.querySelector('[data-act="skip"]').addEventListener("click", () => close());
    card.querySelector('[data-act="prev"]').addEventListener("click", () => go(index - 1));
    card.querySelector('[data-act="next"]').addEventListener("click", () => go(index + 1));
    if (node) {
      const top = node.getBoundingClientRect().top + window.scrollY - 84;
      window.scrollTo({ top: Math.max(0, top), behavior: "auto" });
    }
    place();
    requestAnimationFrame(place);
    card.querySelector('[data-act="next"]').focus({ preventScroll: true });
  }

  function place() {
    if (!overlay || index < 0) return;
    const step = STEPS[index];
    const node = targetFor(step);
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const pad = 12;

    if (!node) {
      spot.hidden = true;
      overlay.classList.add("is-dim");
      card.dataset.pos = "center";
      card.style.cssText = "left:50%;top:50%;transform:translate(-50%,-50%)";
      return;
    }
    overlay.classList.remove("is-dim");

    const r = node.getBoundingClientRect();
    const top = Math.max(r.top, 4);
    const bottom = Math.min(r.bottom, vh - 4);
    const left = Math.max(r.left, 4);
    const right = Math.min(r.right, vw - 4);
    if (bottom <= top || right <= left) {
      spot.hidden = true;
    } else {
      spot.hidden = false;
      spot.style.cssText = `left:${left - 4}px;top:${top - 4}px;width:${right - left + 8}px;height:${bottom - top + 8}px`;
    }

    const narrow = vw < 700;
    card.style.cssText = "";
    delete card.dataset.pos;
    if (narrow) {
      card.dataset.pos = "sheet";
      return;
    }
    const cw = Math.min(360, vw - 2 * pad);
    card.style.width = cw + "px";
    const ch = card.offsetHeight;
    const cx = Math.min(Math.max(pad, (left + right) / 2 - cw / 2), vw - cw - pad);
    const tries = [
      ["below", bottom + pad + 6, cx, bottom + pad + 6 + ch <= vh - pad],
      ["above", top - pad - 6 - ch, cx, top - pad - 6 - ch >= pad],
      ["right", Math.min(Math.max(pad, top), vh - ch - pad), right + pad + 6, right + pad + 6 + cw <= vw - pad],
      ["left", Math.min(Math.max(pad, top), vh - ch - pad), left - pad - 6 - cw, left - pad - 6 - cw >= pad],
    ];
    const hit = tries.find((t) => t[3]);
    if (hit) {
      card.dataset.pos = hit[0];
      card.style.top = hit[1] + "px";
      card.style.left = hit[2] + "px";
      if (hit[0] === "below" || hit[0] === "above") {
        const ax = Math.min(Math.max(20, (left + right) / 2 - hit[2]), cw - 20);
        card.style.setProperty("--tour-ax", ax + "px");
      } else {
        const ay = Math.min(Math.max(20, (top + bottom) / 2 - hit[1]), ch - 20);
        card.style.setProperty("--tour-ay", ay + "px");
      }
    } else {
      card.dataset.pos = "float";
      card.style.top = Math.max(pad, vh - ch - pad) + "px";
      card.style.left = Math.max(pad, vw - cw - pad) + "px";
    }
  }

  function onKey(event) {
    if (!overlay) return;
    const k = event.key;
    if (k === "Escape") {
      event.preventDefault();
      event.stopImmediatePropagation();
      close();
      return;
    }
    if (index < 0) return;
    if (k === "ArrowRight") {
      event.preventDefault();
      event.stopImmediatePropagation();
      go(index + 1);
    } else if (k === "ArrowLeft") {
      event.preventDefault();
      event.stopImmediatePropagation();
      go(index - 1);
    }
  }

  function open(from) {
    opener = from || document.getElementById("tour-start");
    welcome();
  }

  document.addEventListener("click", (event) => {
    const btn = event.target.closest("#tour-start");
    if (btn) {
      event.preventDefault();
      opener = btn;
      if (overlay) close(true);
      welcome();
    }
  });

  const params = new URLSearchParams(location.search);
  const automated = Boolean(navigator.webdriver);
  if (params.get("tour") === "1") {
    open();
  } else if (params.get("tour") !== "0" && !automated && !seen()) {
    window.setTimeout(() => { if (!overlay) open(); }, 500);
  }

  window.NavigatorTour = { open, go, close, steps: STEPS };
})();
