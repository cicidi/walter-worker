// Shell: navigation, the global filter bar, routing and data access.
import { h, empty } from "./ui.js";
import { overview, sessionsPage, toolsPage, filesPage, projectsPage, healthPage } from "./pages-core.js";
import { insightsPage } from "./pages-insights.js";
import { memoryPage, evolutionPage } from "./pages-memory.js";

const PAGES = [
  { path: "", label: "Overview", render: overview, filtered: true },
  { path: "insights", label: "Insights", render: insightsPage, filtered: true },
  { path: "memory", label: "Memory", render: memoryPage, filtered: false },
  { path: "sessions", label: "Sessions", render: sessionsPage, filtered: true },
  { path: "tools", label: "Tools and skills", render: toolsPage, filtered: true },
  { path: "files", label: "Files", render: filesPage, filtered: true },
  { path: "projects", label: "Projects", render: projectsPage, filtered: true },
  { path: "evolution", label: "Evolution", render: evolutionPage, filtered: false },
  { path: "health", label: "Data health", render: healthPage, filtered: false },
];
const RANGES = [[0, "All time"], [7, "7 days"], [30, "30 days"], [90, "90 days"]];
const FILTER_KEYS = ["ide", "model", "project", "days"];

export const state = { filters: { ide: "", model: "", project: "", days: 0 } };

// ── Data access ──────────────────────────────────────────────────────────────

function query(params) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params || {})) if (v !== "" && v != null && v !== 0) q.set(k, v);
  const s = q.toString();
  return s ? "?" + s : "";
}

async function read(res) {
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch { /* body was not JSON */ }
    throw new Error(`${res.status} ${detail}`);
  }
  return res.json();
}

// GET /api/<path>. `filtered` adds the global filters; `params` can override them.
export function api(path, params = {}, { filtered = false } = {}) {
  const all = filtered ? { ...state.filters, ...params } : params;
  return fetch("/api/" + path + query(all)).then(read);
}

// State-changing calls carry the header the server requires on every POST.
export function post(path, params = {}) {
  return fetch("/api/" + path + query(params), { method: "POST", headers: { "X-Coworker-Dashboard": "1" } }).then(read);
}

// ── Routing ──────────────────────────────────────────────────────────────────

function parseHash() {
  const raw = location.hash.replace(/^#\/?/, "");
  const [path, qs] = raw.split("?");
  const q = new URLSearchParams(qs || "");
  const filters = { ide: q.get("ide") || "", model: q.get("model") || "", project: q.get("project") || "", days: Number(q.get("days")) || 0 };
  const extra = {};
  for (const [k, v] of q) if (!FILTER_KEYS.includes(k)) extra[k] = v;
  return { path: path || "", filters, extra };
}

export function href(path, extra = {}) {
  return "#/" + path + query({ ...state.filters, ...extra });
}

function setFilters(next) {
  state.filters = { ...state.filters, ...next };
  const { path, extra } = parseHash();
  location.hash = "/" + path + query({ ...state.filters, ...extra });
}

let renderToken = 0;

async function render() {
  const { path, filters, extra } = parseHash();
  state.filters = filters;
  const page = PAGES.find((p) => p.path === path) || PAGES[0];
  const token = ++renderToken;
  drawNav(page);
  drawFilters(page);
  const main = document.getElementById("main");
  main.replaceChildren(h("p", { class: "note loading" }, "Loading…"));
  document.title = `${page.label} · Coworker`;
  try {
    const node = await page.render(extra);
    if (token !== renderToken) return; // the user moved on while this loaded
    main.replaceChildren(node);
    main.scrollTop = 0;
    if (extra.at) document.getElementById(extra.at)?.scrollIntoView();
  } catch (e) {
    if (token !== renderToken) return;
    main.replaceChildren(empty("This page could not load.", e.message));
  }
}

function drawNav(current) {
  const nav = document.getElementById("nav");
  nav.replaceChildren(
    h("a", { class: "brand", href: href("") }, h("span", { class: "brand-mark", "aria-hidden": "true" }), "Coworker"),
    h("ul", null, PAGES.map((p) =>
      h("li", null, h("a", { href: href(p.path), "aria-current": p === current ? "page" : null }, p.label)))));
}

let options = null;

function select(label, key, items) {
  const el = h("select", { "aria-label": label, onchange: (e) => setFilters({ [key]: e.target.value }) },
    h("option", { value: "" }, "All " + label.toLowerCase() + "s"),
    items.map((i) => h("option", { value: i.value, selected: state.filters[key] === i.value }, `${i.value} (${i.count})`)));
  return h("label", { class: "filter" }, h("span", null, label), el);
}

async function drawFilters(page) {
  const bar = document.getElementById("filters");
  if (!page.filtered) {
    bar.replaceChildren(h("p", { class: "note" }, "This page always shows everything; the filters apply to the other pages."));
    return;
  }
  if (!options) {
    try { options = await api("v2/filters"); } catch { options = { ides: [], models: [], projects: [] }; }
  }
  const active = FILTER_KEYS.some((k) => state.filters[k]);
  bar.replaceChildren(...[
    select("Agent", "ide", options.ides),
    select("Model", "model", options.models),
    select("Project", "project", options.projects),
    h("div", { class: "seg", role: "group", "aria-label": "Time range" }, RANGES.map(([d, label]) =>
      h("button", { type: "button", "aria-pressed": String(state.filters.days === d), onclick: () => setFilters({ days: d }) }, label))),
    active ? h("button", { type: "button", class: "clear", onclick: () => setFilters({ ide: "", model: "", project: "", days: 0 }) }, "Clear filters") : null].filter(Boolean));
}

window.addEventListener("hashchange", render);
render();
