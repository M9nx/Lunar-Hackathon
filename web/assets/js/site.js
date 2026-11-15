(function () {
  const root = document.body.dataset.root || "";
  const doc = new URLSearchParams(location.search).get("doc") || "";
  const found = (window.NAVIGATOR_DOCS || []).find((d) => d.file === doc);
  let page = document.body.dataset.page || "";
  if (page === "docs") page = found ? found.group : "manual";

  const nav = [
    { id: "overview", href: "", label: "Overview" },
    { id: "guide", href: "review-candidate/?tour=1", label: "Guide" },
    { id: "navigator", href: "review-candidate/", label: "Navigator" },
    { id: "replay", href: "replay/", label: "Replay" },
    { id: "manual", href: "documents.html?doc=operator-manual.md", label: "Manual" },
    { id: "reference", href: "documents.html?doc=engine-reference.md", label: "Reference" }
  ];

  const header = document.getElementById("site-header");
  const footer = document.getElementById("site-footer");

  if (header) {
    const links = nav.map((item) => {
      const current = item.id === page ? ' aria-current="page"' : "";
      return `<a href="${root}${item.href}"${current}>${item.label}</a>`;
    }).join("");
    header.innerHTML = `
      <div class="header-inner">
        <a class="brand" href="${root}">
          <span class="brand-name">Lunar Landing Site Navigator<small>NASA Space Apps Challenge 2026</small></span>
        </a>
        <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="site-nav">Menu</button>
        <nav id="site-nav" class="site-nav" aria-label="Primary">${links}</nav>
      </div>`;
    const toggle = header.querySelector(".nav-toggle");
    const navEl = document.getElementById("site-nav");
    toggle.addEventListener("click", () => {
      const open = navEl.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", String(open));
    });
  }

  if (footer) {
    footer.innerHTML = `
      <div class="wrap footer-grid">
        <div>
          <div class="footer-brand">Lunar Landing Site Navigator</div>
          <p>A NASA Space Apps Challenge 2026 team project. It compares when the centre of the Sun and of Earth is above a flat 0° horizon at lunar south-pole sites, from saved JPL Horizons data. This is not an official NASA website.</p>
        </div>
        <div class="footer-col">
          <h2>Use it</h2>
          <ul>
            <li><a href="${root}review-candidate/?tour=1">Step-by-step guide</a></li>
            <li><a href="${root}review-candidate/">Navigator</a></li>
            <li><a href="${root}replay/">Witnessed 0° replay</a></li>
            <li><a href="${root}documents.html?doc=operator-manual.md">Operator manual</a></li>
          </ul>
        </div>
        <div class="footer-col">
          <h2>Reference</h2>
          <ul>
            <li><a href="${root}documents.html?doc=api-reference.md">API</a></li>
            <li><a href="${root}documents.html?doc=engine-reference.md">Engine</a></li>
            <li><a href="${root}documents.html?doc=science-and-data-reference.md">Science and data</a></li>
            <li><a href="${root}documents.html?doc=data-research.md">Data and research</a></li>
            <li><a href="${root}documents.html?doc=project-progress.md">Project progress</a></li>
          </ul>
        </div>
      </div>
      <div class="wrap footer-legal">Served from this repository, offline. Practice inputs; terrain clearance is Unknown; nothing here is an eligible submission claim. Imagery: NASA, NASA/SDO, NASA/GSFC/Arizona State University.</div>`;
  }
})();
