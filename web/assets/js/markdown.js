(function () {
  const DOCS = window.NAVIGATOR_DOCS || [];
  const GROUPS = window.NAVIGATOR_DOC_GROUPS || {};
  const allowed = new Set(DOCS.map((doc) => doc.file));
  const params = new URLSearchParams(location.search);
  const requested = params.get("doc") || DOCS[0].file;
  if (requested === "user-guide.md") { location.replace("review-candidate/?tour=1"); return; }
  const current = allowed.has(requested) ? requested : DOCS[0].file;
  const index = DOCS.findIndex((doc) => doc.file === current);
  const meta = DOCS[index];
  const href = (file, hash) => `documents.html?doc=${encodeURIComponent(file)}${hash || ""}`;

  const navEl = document.getElementById("doc-links");
  const selectEl = document.getElementById("doc-select");
  const articleEl = document.getElementById("doc-article");
  const tocEl = document.getElementById("doc-toc-list");
  const crumbEl = document.getElementById("breadcrumb");

  const slug = (text) => text.toLowerCase().trim().replace(/[^\w\s-]/g, "").replace(/\s+/g, "-").slice(0, 80);

  // Left list, grouped: Manual, Reference.
  if (navEl) {
    let html = "";
    let last = "";
    DOCS.forEach((doc) => {
      if (doc.group !== last) { html += `<h2>${GROUPS[doc.group] || doc.group}</h2>`; last = doc.group; }
      const cur = doc.file === current ? ' aria-current="page"' : "";
      html += `<a href="${href(doc.file)}"${cur}>${doc.title}</a>`;
    });
    navEl.innerHTML = html;
  }
  if (selectEl) {
    selectEl.innerHTML = DOCS.map((doc) => `<option value="${doc.file}"${doc.file === current ? " selected" : ""}>${GROUPS[doc.group]}: ${doc.title}</option>`).join("");
    selectEl.addEventListener("change", () => { location.href = href(selectEl.value); });
  }
  if (crumbEl) {
    crumbEl.innerHTML = `<ol><li><a href="./">Overview</a></li><li>${GROUPS[meta.group]}</li><li aria-current="page">${meta.title}</li></ol>`;
  }

  function rewriteLinks(container) {
    container.querySelectorAll("a[href]").forEach((a) => {
      const raw = a.getAttribute("href") || "";
      const m = raw.match(/^(?:\.\/)?([\w-]+\.md)(#[\w-]+)?$/i);
      if (m && m[1] === "user-guide.md") a.setAttribute("href", "review-candidate/?tour=1");
      else if (m && allowed.has(m[1])) a.setAttribute("href", href(m[1], m[2]));
      else if (raw.startsWith("#")) a.setAttribute("href", href(current, raw));
    });
  }

  function addHeadingIds(container) {
    const used = new Set();
    container.querySelectorAll("h1, h2, h3, h4").forEach((h) => {
      const base = h.id || slug(h.textContent || "section");
      let id = base, n = 2;
      while (used.has(id)) { id = `${base}-${n}`; n += 1; }
      used.add(id);
      h.id = id;
    });
  }

  function buildToc(container) {
    if (!tocEl) return;
    const heads = [...container.querySelectorAll("h2, h3")];
    tocEl.innerHTML = heads.length
      ? heads.map((h) => `<a href="${href(current, "#" + h.id)}" data-id="${h.id}"${h.tagName === "H3" ? ' class="sub"' : ""}>${h.textContent}</a>`).join("")
      : "<p class='doc-loading'>No sections</p>";
    const links = [...tocEl.querySelectorAll("a")];
    const onScroll = () => {
      let active = null;
      heads.forEach((h) => { if (h.getBoundingClientRect().top < 140) active = h.id; });
      links.forEach((l) => l.classList.toggle("is-active", l.dataset.id === active));
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  // Tables: wrap, keep short cells on one line, say when the table scrolls sideways.
  function styleTables(container) {
    container.querySelectorAll("table").forEach((table) => {
      const wrap = document.createElement("div");
      wrap.className = "table-wrap";
      table.parentNode.insertBefore(wrap, table);
      wrap.appendChild(table);
      table.querySelectorAll("th, td").forEach((cell) => {
        const text = cell.textContent.trim();
        if (text.length <= 16 && !/\s{2,}/.test(text)) cell.classList.add("nw");
      });
      requestAnimationFrame(() => wrap.classList.toggle("scrolls", wrap.scrollWidth > wrap.clientWidth + 2));
    });
  }

  function promoteMermaidBlocks(container) {
    container.querySelectorAll("pre > code.language-mermaid").forEach((code) => {
      const pre = code.parentElement;
      const div = document.createElement("div");
      div.className = "mermaid";
      div.textContent = code.textContent || "";
      pre.replaceWith(div);
    });
  }

  async function renderMermaid(container) {
    if (!window.mermaid) return;
    const nodes = container.querySelectorAll(".mermaid");
    if (!nodes.length) return;
    window.mermaid.initialize({
      startOnLoad: false,
      theme: "neutral",
      securityLevel: "strict",
      flowchart: { htmlLabels: true, curve: "basis" },
      sequence: { actorMargin: 48, messageMargin: 40 },
    });
    try {
      await window.mermaid.run({ nodes: [...nodes] });
    } catch (err) {
      nodes.forEach((node) => {
        if (node.querySelector("svg")) return;
        const note = document.createElement("p");
        note.className = "doc-error";
        note.textContent = "Diagram could not be rendered in the browser.";
        node.insertAdjacentElement("afterend", note);
      });
      console.warn("Mermaid render failed", err);
    }
  }

  function addCopyButtons(container) {
    container.querySelectorAll("pre").forEach((block) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "copy-btn";
      button.textContent = "Copy";
      button.addEventListener("click", async () => {
        const text = block.querySelector("code")?.textContent || block.textContent || "";
        try { await navigator.clipboard.writeText(text); button.textContent = "Copied"; }
        catch { button.textContent = "Copy failed"; }
        setTimeout(() => { button.textContent = "Copy"; }, 1500);
      });
      block.appendChild(button);
    });
  }

  function pager() {
    const prev = DOCS[index - 1];
    const next = DOCS[index + 1];
    return `<nav class="doc-pager" aria-label="Previous and next document">
      ${prev ? `<a class="prev" href="${href(prev.file)}"><small>Previous</small><strong>← ${prev.title}</strong></a>` : "<span></span>"}
      ${next ? `<a class="next" href="${href(next.file)}"><small>Next</small><strong>${next.title} →</strong></a>` : ""}
    </nav>`;
  }

  async function render() {
    document.title = `${meta.title} · Lunar Landing Site Navigator`;
    try {
      const response = await fetch(`docs/${current}`);
      if (!response.ok) throw new Error(`Could not load ${current}`);
      const markdown = await response.text();
      const html = window.DOMPurify.sanitize(window.marked.parse(markdown, { gfm: true, breaks: false }), { USE_PROFILES: { html: true } });
      articleEl.innerHTML = html;
      const h1 = articleEl.querySelector("h1");
      if (h1) document.title = `${meta.title} · Lunar Landing Site Navigator`;
      promoteMermaidBlocks(articleEl);
      addHeadingIds(articleEl);
      rewriteLinks(articleEl);
      styleTables(articleEl);
      buildToc(articleEl);
      addCopyButtons(articleEl);
      await renderMermaid(articleEl);
      articleEl.insertAdjacentHTML("beforeend", pager());
      if (location.hash) document.getElementById(decodeURIComponent(location.hash.slice(1)))?.scrollIntoView();
    } catch (error) {
      articleEl.innerHTML = `<h1>${meta.title}</h1><p class="doc-error">The viewer could not load this document. Start the local server (see the operator manual) or open the Markdown file directly.</p><p><a href="docs/${current}">Open docs/${current}</a></p>`;
    }
  }

  (function start() {
    if (window.marked && window.DOMPurify && window.mermaid) { render(); return; }
    setTimeout(start, 40);
  })();
})();
