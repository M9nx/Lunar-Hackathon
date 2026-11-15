// Fills the result and site tables, and places the site pins, from the saved Jan 3-10 package.
// The static HTML already holds the same values; this keeps the page tied to the files.
(async function () {
  const CASE = "review-candidate/cases/practice-jan03-10/";
  const NAMES = { "malapert-practice": "Malapert", "site04-p02-practice": "Site04" };
  const MAP = { radiusM: 1737400, mPerPixel: 400, pixels: 1521 }; // PIA13523, as in the navigator

  const hm = (seconds) => {
    const minutes = Math.round(seconds / 60);
    const h = Math.floor(minutes / 60), m = minutes % 60;
    return m ? `${h} h ${m} min` : `${h} h`;
  };
  const fmt = (v, d) => (v < 0 ? "−" : "") + Math.abs(v).toFixed(d);
  const pin = (lon, lat) => {
    const colat = Math.max(0, (90 + lat) * Math.PI / 180);
    const rM = 2 * MAP.radiusM * Math.tan(colat / 2);
    const radius = Math.min(49, (rM / ((MAP.pixels * MAP.mPerPixel) / 2)) * 50);
    const rad = lon * Math.PI / 180;
    return { x: 50 + radius * Math.sin(rad), y: 50 - radius * Math.cos(rad) };
  };

  try {
    const comparison = await (await fetch(CASE + "comparison.json")).json();
    const runs = [];
    for (const r of comparison.runs) runs.push(await (await fetch(CASE + r.file)).json());
    const rows = runs.map((run, i) => {
      const id = run.scenario.site_id || run.scenario.site || "";
      const key = i === 0 ? "site_a" : "site_b";
      return {
        name: NAMES[id] || id,
        sun: comparison.overlap.sun_centre_clear_seconds[key],
        both: comparison.overlap.both_centres_clear_seconds[key],
        unknown: comparison.overlap.unknown_seconds[key].both,
        obs: run.scenario.observer,
        i
      };
    });
    document.querySelector("#result-table tbody").innerHTML = rows.map((r) =>
      `<tr><th scope="row">${r.name}</th><td class="num">${hm(r.sun)}</td><td class="num">${hm(r.both)}</td><td class="num">${hm(r.unknown)}</td></tr>`).join("");
    document.querySelector("#sites-table tbody").innerHTML = rows.map((r) =>
      `<tr><th scope="row">${r.name}</th><td class="num">${fmt(r.obs.latitude_deg, 4)}°</td><td class="num">${fmt(r.obs.longitude_east_deg, 4)}°</td><td class="num">${r.obs.reference_altitude_km} km</td></tr>`).join("");
    const stage = document.getElementById("map-stage");
    rows.forEach((r) => {
      const p = pin(r.obs.longitude_east_deg, r.obs.latitude_deg);
      const dot = document.createElement("span");
      dot.className = "pin";
      dot.style.left = p.x + "%"; dot.style.top = p.y + "%";
      const label = document.createElement("span");
      label.className = "pin-label" + (r.name === "Site04" ? " left" : "");
      label.style.left = p.x + "%"; label.style.top = p.y + "%";
      label.textContent = r.name;
      stage.append(dot, label);
    });
  } catch (error) {
    // Opened without the local server: keep the static tables and show the map without pins.
  }
})();
