
(function () {
  function renderMermaid() {
    if (!window.mermaid) return;
    document.querySelectorAll("pre.mermaid").forEach(function (el) {
      if (!el.dataset.src) el.dataset.src = el.textContent;
      el.removeAttribute("data-processed");
      el.textContent = el.dataset.src;
    });
    try {
      mermaid.initialize({ startOnLoad: false, theme: "neutral", securityLevel: "loose" });
      mermaid.run({ querySelector: "pre.mermaid" }).catch(function () {});
    } catch (e) {}
  }

  window.addEventListener("load", renderMermaid);
})();
