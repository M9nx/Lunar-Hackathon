"use strict";

const state = { comparison: null, runs: [], index: 0 };

function text(id, value) {
  document.getElementById(id).textContent = value;
}

function showNumber(value) {
  if (value === null || value === undefined) return "null";
  return String(value);
}

function laneRow(label, body) {
  const stateName = body.state;
  return `<div class="lane">
    <span>${label}</span>
    <span class="bar" aria-hidden="true"><i class="fill ${stateName}"></i></span>
    <span class="state ${stateName}">${stateName}</span>
  </div>`;
}

function inspectorTable(sample) {
  const rows = ["sun", "earth"].map((body) => {
    const item = sample[body];
    return `<tr>
      <th scope="row">${item.label}</th>
      <td>${showNumber(item.azimuth_deg)}</td>
      <td>${showNumber(item.elevation_deg)}</td>
      <td>${showNumber(item.horizon_deg)}</td>
      <td>${showNumber(item.margin_deg)}</td>
      <td class="state ${item.state}">${item.state}</td>
      <td>${item.reason || "—"}</td>
    </tr>`;
  }).join("");
  const both = sample.both;
  return `<table>
    <thead><tr><th>Lane</th><th>Azimuth °</th><th>Elevation °</th><th>Horizon °</th><th>Margin °</th><th>State</th><th>Reason</th></tr></thead>
    <tbody>${rows}
      <tr><th scope="row">${both.label}</th><td colspan="4"></td><td class="state ${both.state}">${both.state}</td><td>${both.reason || "—"}</td></tr>
    </tbody>
  </table>
  <p class="trace">Sun response: ${sample.sun.response_line || "—"}</p>
  <p class="trace">Earth response: ${sample.earth.response_line || "—"}</p>
  <p class="trace">Sources: ${sample.sun.source_ref} · ${sample.earth.source_ref}</p>`;
}

function render() {
  const index = state.index;
  const first = state.runs[0];
  const sample = first.payload.samples[index];
  text("utc", sample.timestamp_utc);
  const playhead = document.getElementById("playhead");
  playhead.max = String(first.payload.samples.length - 1);
  playhead.value = String(index);
  playhead.setAttribute("aria-valuetext", sample.timestamp_utc);

  const overlap = state.comparison.overlap;
  document.getElementById("comparison").innerHTML = `
    <p>Sun-centre clear seconds: Site A ${overlap.sun_centre_clear_seconds.site_a}, Site B ${overlap.sun_centre_clear_seconds.site_b}, delta (B − A) ${overlap.sun_centre_clear_seconds.delta_b_minus_a}.</p>
    <p>Both centres clear seconds: Site A ${overlap.both_centres_clear_seconds.site_a}, Site B ${overlap.both_centres_clear_seconds.site_b}, delta (B − A) ${overlap.both_centres_clear_seconds.delta_b_minus_a}.</p>
    <p>Unknown seconds beside those totals — Site A both ${overlap.unknown_seconds.site_a.both}, Site B both ${overlap.unknown_seconds.site_b.both}.</p>
    <p>Run ${state.comparison.code_revision}. Comparable: ${state.comparison.comparable}.</p>`;

  document.getElementById("sites").innerHTML = state.runs.map((run, runIndex) => {
    const current = run.payload.samples[index];
    if (current.timestamp_utc !== sample.timestamp_utc) {
      return `<article class="site"><h3>${run.role}</h3><p class="banner">Timestamp grid does not match the shared playhead.</p></article>`;
    }
    const totals = run.payload.elapsed_seconds;
    return `<article class="site">
      <h3>${run.role}: ${run.payload.scenario.site_id}</h3>
      <p>Run ${run.payload.run_id}. Observer ${run.payload.scenario.observer.longitude_east_deg}° E, ${run.payload.scenario.observer.latitude_deg}° N, ${run.payload.scenario.observer.reference_altitude_km} km.</p>
      ${laneRow(current.sun.label, current.sun)}
      ${laneRow(current.earth.label, current.earth)}
      ${laneRow(current.both.label, current.both)}
      <p>Totals (s): Sun clear ${totals.sun.clear}, Earth blocked ${totals.earth.blocked}, Both clear ${totals.both.clear}, Both unknown ${totals.both.unknown}.</p>
      ${inspectorTable(current)}
    </article>`;
  }).join("");
}

function move(nextIndex) {
  const last = state.runs[0].payload.samples.length - 1;
  state.index = Math.max(0, Math.min(last, nextIndex));
  render();
}

async function main() {
  const comparison = await (await fetch("comparison.json")).json();
  state.comparison = comparison;
  state.runs = [];
  for (const run of comparison.runs) {
    const payload = await (await fetch(run.file)).json();
    state.runs.push({ ...run, payload });
  }
  document.getElementById("exports").innerHTML = comparison.runs.map((run) =>
    `<a class="export" href="${run.file}" download>${run.role} JSON</a>`
  ).join("");
  document.getElementById("prev").addEventListener("click", () => move(state.index - 1));
  document.getElementById("next").addEventListener("click", () => move(state.index + 1));
  document.getElementById("playhead").addEventListener("input", (event) => move(Number(event.target.value)));
  document.addEventListener("keydown", (event) => {
    if (event.key === "ArrowLeft") move(state.index - 1);
    if (event.key === "ArrowRight") move(state.index + 1);
  });
  render();
}

main().catch((error) => {
  document.body.insertAdjacentHTML("beforeend", `<p class="banner">${error.message}</p>`);
});
