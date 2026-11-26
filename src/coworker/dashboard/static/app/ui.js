// Shared building blocks. Everything is built with DOM nodes and textContent,
// never innerHTML, because prompts, tool arguments and file paths are shown
// verbatim and must not be parsed as markup.

const SVG_NS = "http://www.w3.org/2000/svg";

export function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  add(el, kids);
  return el;
}

function add(el, kids) {
  for (const kid of kids.flat(Infinity)) {
    if (kid == null || kid === false) continue;
    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
}

export function svg(tag, attrs, ...kids) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs || {})) if (v != null) el.setAttribute(k, v);
  add(el, kids);
  return el;
}

// ── Formatting ───────────────────────────────────────────────────────────────

const nf = new Intl.NumberFormat("en-US");
const DASH = "–"; // shown for "not recorded"; never 0

export const fmt = {
  n: (v) => (v == null ? DASH : nf.format(Math.round(v))),
  compact(v) {
    if (v == null) return DASH;
    const a = Math.abs(v);
    if (a >= 1e9) return (v / 1e9).toFixed(a >= 1e10 ? 0 : 1) + "B";
    if (a >= 1e6) return (v / 1e6).toFixed(a >= 1e7 ? 0 : 1) + "M";
    if (a >= 1e4) return (v / 1e3).toFixed(0) + "k";
    return nf.format(Math.round(v));
  },
  pct: (v, digits = 1) => (v == null ? DASH : (v * 100).toFixed(v > 0 && v < 0.0995 ? digits : 0) + "%"),
  money: (v) => (v == null || v === 0 ? DASH : "$" + v.toFixed(2)),
  ms(v) {
    if (v == null) return DASH;
    return v >= 60000 ? (v / 60000).toFixed(1) + " min" : v >= 1000 ? (v / 1000).toFixed(1) + " s" : Math.round(v) + " ms";
  },
  mins(v) {
    if (v == null || v === 0) return DASH;
    return v >= 60 ? Math.floor(v / 60) + " h " + Math.round(v % 60) + " m" : Math.round(v) + " min";
  },
  date(iso) {
    if (!iso) return DASH;
    const d = new Date(iso);
    if (isNaN(d)) return String(iso).slice(0, 10);
    return d.toLocaleDateString("en-CA") + " " + d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  },
  day(iso) {
    if (!iso) return DASH;
    const d = new Date(iso);
    return isNaN(d) ? String(iso).slice(0, 10) : d.toLocaleDateString("en-CA");
  },
  ago(iso) {
    if (!iso) return DASH;
    const s = (Date.now() - new Date(iso).getTime()) / 1000;
    if (isNaN(s)) return DASH;
    if (s < 3600) return Math.max(1, Math.round(s / 60)) + " min ago";
    if (s < 86400) return Math.round(s / 3600) + " h ago";
    if (s < 86400 * 60) return Math.round(s / 86400) + " d ago";
    return Math.round(s / 86400 / 30) + " mo ago";
  },
  id: (s) => (s && s.length > 13 ? s.slice(0, 8) + "…" + s.slice(-4) : s || DASH),
};

// ── Layout pieces ────────────────────────────────────────────────────────────

export function section(title, lead, ...kids) {
  return h("section", { class: "sec", id: "sec-" + title.toLowerCase().replace(/[^a-z0-9]+/g, "-") },
    h("h2", null, title), lead ? h("p", { class: "lead" }, lead) : null, kids);
}

// A finding: one sentence with the number in it. tone: good | warn | bad | plain
export function finding(tone, ...text) {
  return h("p", { class: "finding tone-" + (tone || "plain") }, h("span", { class: "dot", "aria-hidden": "true" }), h("span", null, text));
}

export const strong = (t) => h("strong", null, t);

export function note(...text) {
  return h("p", { class: "note" }, text);
}

export function empty(text, hint) {
  return h("div", { class: "empty" }, h("p", null, text), hint ? h("p", { class: "note" }, hint) : null);
}

export function pill(text, tone) {
  return h("span", { class: "pill" + (tone ? " pill-" + tone : "") }, text);
}

// Small bar inside a table cell: value on the left, bar scaled to `max`.
export function meter(value, max, label, tone) {
  const w = max > 0 && value != null ? Math.max(value > 0 ? 2 : 0, Math.round((value / max) * 100)) : 0;
  return h("span", { class: "meter" },
    h("span", { class: "meter-num" }, label),
    h("span", { class: "meter-track" }, h("span", { class: "meter-fill" + (tone ? " fill-" + tone : ""), style: { width: w + "%" } })));
}

// Click-to-open block. `body` is a node or a function returning a node/promise.
export function disclosure(summary, body, { open = false } = {}) {
  const box = h("div", { class: "disc-body", hidden: !open });
  let loaded = false;
  const btn = h("button", { class: "disc-btn", type: "button", "aria-expanded": String(open) },
    h("span", { class: "caret", "aria-hidden": "true" }), summary);
  const fill = async () => {
    if (loaded) return;
    loaded = true;
    try {
      const node = typeof body === "function" ? await body() : body;
      box.replaceChildren(node);
    } catch (e) {
      box.replaceChildren(empty("Could not load this.", e.message));
      loaded = false;
    }
  };
  btn.addEventListener("click", () => {
    const now = box.hidden;
    box.hidden = !now;
    btn.setAttribute("aria-expanded", String(now));
    if (now) fill();
  });
  if (open) fill();
  return h("div", { class: "disc" }, btn, box);
}

// ── Table with sortable columns and expandable rows ──────────────────────────
// cols: [{ key, label, num, render(row), sort(row), width }]
// expand(row) -> node | promise<node>; rows open in place under the row.
export function table({ cols, rows, expand, emptyText = "Nothing recorded for this filter.", limit = 0, sortBy, sortDir = -1 }) {
  if (!rows || !rows.length) return empty(emptyText);
  let sort = sortBy ? { key: sortBy, dir: sortDir } : null;
  let shown = limit || rows.length;
  const tbody = h("tbody");
  const more = h("button", { class: "more", type: "button" });
  const val = (col, row) => (col.sort ? col.sort(row) : row[col.key]);

  function draw() {
    let list = rows;
    if (sort) {
      const col = cols.find((c) => c.key === sort.key);
      list = [...rows].sort((a, b) => {
        const x = val(col, a), y = val(col, b);
        if (x == null && y == null) return 0;
        if (x == null) return 1; // unknown values sort last in either direction
        if (y == null) return -1;
        return (x > y ? 1 : x < y ? -1 : 0) * sort.dir;
      });
    }
    tbody.replaceChildren();
    for (const row of list.slice(0, shown)) {
      const tr = h("tr", { class: expand ? "can-open" : null });
      cols.forEach((c, i) => {
        const cell = c.render ? c.render(row) : row[c.key];
        const td = h("td", { class: c.num ? "num" : null }, cell == null || cell === "" ? DASH : cell);
        if (i === 0 && expand) td.prepend(h("span", { class: "caret", "aria-hidden": "true" }));
        tr.append(td);
      });
      tbody.append(tr);
      if (expand) {
        const detail = h("tr", { class: "detail", hidden: true }, h("td", { colspan: cols.length }));
        let loaded = false;
        const toggle = async () => {
          const opening = detail.hidden;
          detail.hidden = !opening;
          tr.classList.toggle("is-open", opening);
          tr.setAttribute("aria-expanded", String(opening));
          if (opening && !loaded) {
            loaded = true;
            const td = detail.firstChild;
            td.replaceChildren(h("p", { class: "note" }, "Loading…"));
            try { td.replaceChildren(await expand(row)); }
            catch (e) { td.replaceChildren(empty("Could not load this.", e.message)); loaded = false; }
          }
        };
        tr.tabIndex = 0;
        tr.setAttribute("aria-expanded", "false");
        tr.addEventListener("click", (e) => { if (!e.target.closest("a,button,input,select")) toggle(); });
        tr.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggle(); } });
        tbody.append(detail);
      }
    }
    more.hidden = shown >= list.length;
    more.textContent = `Show ${Math.min(limit || 50, list.length - shown)} more of ${list.length - shown}`;
  }

  const head = h("tr", null, cols.map((c) => {
    const th = h("th", { class: c.num ? "num" : null, style: c.width ? { width: c.width } : null, scope: "col" });
    const btn = h("button", { type: "button", class: "th-btn", title: c.title || null }, c.label);
    btn.addEventListener("click", () => {
      sort = sort && sort.key === c.key ? { key: c.key, dir: -sort.dir } : { key: c.key, dir: c.num ? -1 : 1 };
      head.querySelectorAll("th").forEach((x) => x.removeAttribute("aria-sort"));
      th.setAttribute("aria-sort", sort.dir === 1 ? "ascending" : "descending");
      draw();
    });
    th.append(btn);
    return th;
  }));
  more.addEventListener("click", () => { shown += limit || 50; draw(); });
  draw();
  return h("div", { class: "table-wrap" }, h("table", null, h("thead", null, head), tbody), more);
}

// ── Charts (plain SVG and CSS, no library) ───────────────────────────────────

// Horizontal bars: [{ label, value, sub, tone }]
export function bars(items, { format = fmt.n, max, wide = false } = {}) {
  if (!items.length) return empty("Nothing recorded for this filter.");
  const top = max ?? Math.max(...items.map((i) => i.value || 0), 1);
  return h("div", { class: "bars" + (wide ? " wide" : "") }, items.map((i) =>
    h("div", { class: "bar-row" },
      h("span", { class: "bar-label", title: i.label }, i.label),
      h("span", { class: "bar-track" },
        h("span", { class: "bar-fill" + (i.tone ? " fill-" + i.tone : ""), style: { width: Math.max(i.value > 0 ? 0.6 : 0, (i.value / top) * 100) + "%" } })),
      h("span", { class: "bar-value" }, format(i.value), i.sub ? h("span", { class: "bar-sub" }, " " + i.sub) : null))));
}

// Vertical columns over time. series: [{ x, parts: [{ value, tone, name }] }]
// Built from plain boxes so labels keep their shape at any width.
export function columns(series, { height = 120, format = fmt.n, every } = {}) {
  if (!series.length) return empty("Nothing recorded for this filter.");
  const totals = series.map((s) => s.parts.reduce((a, p) => a + (p.value || 0), 0));
  const top = Math.max(...totals, 0);
  if (!top) return empty("Nothing recorded for this filter.");
  const step = every || Math.ceil(series.length / 8);
  const dense = series.length > 45;
  return h("div", { class: "chart" },
    h("p", { class: "chart-max" }, "Tallest bar: " + format(top)),
    h("div", { class: "cols" + (dense ? " dense" : ""), style: { height: height + "px" }, role: "img" }, series.map((s, i) => {
      const tip = `${s.x}: ` + (s.parts.filter((p) => p.value).map((p) => `${p.name ? p.name + " " : ""}${format(p.value)}`).join(", ") || "0");
      return h("div", { class: "col", title: tip },
        s.parts.filter((p) => p.value > 0).reverse().map((p) =>
          h("span", { class: "fill-" + (p.tone || "accent"), style: { height: (p.value / top) * 100 + "%" } })));
    })),
    h("div", { class: "cols-x" + (dense ? " dense" : "") }, series.map((s, i) =>
      h("span", null, i % step === 0 ? (String(s.x).length > 7 ? String(s.x).slice(5) : String(s.x)) : ""))));
}

export function spark(values, tone = "accent") {
  if (!values.length) return h("span");
  const W = 96, H = 22, top = Math.max(...values, 1);
  const pts = values.map((v, i) => `${(i / Math.max(values.length - 1, 1)) * W},${H - 2 - (v / top) * (H - 4)}`).join(" ");
  return svg("svg", { viewBox: `0 0 ${W} ${H}`, class: "spark stroke-" + tone, "aria-hidden": "true" },
    svg("polyline", { points: pts, fill: "none" }));
}

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

// Weekday × hour grid. cells: [{ dow, hour, c }]
export function heatmap(cells) {
  const grid = Array.from({ length: 7 }, () => Array(24).fill(0));
  let top = 0;
  for (const c of cells) { grid[c.dow][c.hour] = c.c; top = Math.max(top, c.c); }
  const order = [1, 2, 3, 4, 5, 6, 0]; // Monday first
  const el = h("div", { class: "heat", role: "img", "aria-label": "Prompts by weekday and hour" });
  el.append(h("span"));
  for (let hr = 0; hr < 24; hr++) el.append(h("span", { class: "heat-hour" }, hr % 3 === 0 ? String(hr).padStart(2, "0") : ""));
  for (const d of order) {
    el.append(h("span", { class: "heat-day" }, DAYS[d]));
    for (let hr = 0; hr < 24; hr++) {
      const v = grid[d][hr];
      const level = v === 0 ? 0 : Math.min(5, 1 + Math.floor((v / top) * 4.999));
      el.append(h("span", { class: "heat-cell lv" + level, title: `${DAYS[d]} ${String(hr).padStart(2, "0")}:00, ${v} prompts` }));
    }
  }
  return el;
}

// Stages narrowing downward: [{ stage, value }]
export function funnel(stages) {
  const top = Math.max(...stages.map((s) => s.value || 0), 1);
  return h("ol", { class: "funnel" }, stages.map((s) =>
    h("li", null,
      h("span", { class: "funnel-num" }, s.value == null ? DASH : fmt.n(s.value)),
      h("span", { class: "funnel-bar", style: { width: (s.value == null ? 0 : Math.max(1.5, Math.sqrt(s.value / top) * 100)) + "%" } }),
      h("span", { class: "funnel-label" }, s.stage))));
}

// A row of plain figures separated by hairlines.
export function ledger(items) {
  return h("dl", { class: "ledger" }, items.map((i) =>
    h("div", null, h("dt", null, i.label), h("dd", null, i.value, i.spark || null), i.sub ? h("p", { class: "ledger-sub" }, i.sub) : null)));
}

export function link(text, href, cls) {
  return h("a", { href, class: cls || null }, text);
}

export function pre(text) {
  return h("pre", { class: "raw" }, text == null || text === "" ? "(empty)" : text);
}

// Tool arguments are stored as JSON text; show them indented when they parse.
export function pretty(text) {
  try { return JSON.stringify(JSON.parse(text), null, 2); } catch { return text; }
}
