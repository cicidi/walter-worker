// Overview, Sessions, Tools and skills, Files, Projects, Data health.
import { api, href, state } from "./main.js";
import { h, fmt, section, finding, strong, note, empty, pill, meter, disclosure, table, bars, columns, spark, heatmap, ledger, link, pre, pretty } from "./ui.js";

const AGENT_TONE = { "claude-code": "accent", opencode: "blue" };
const agentTone = (ide) => AGENT_TONE[ide] || "muted";

function scopeText() {
  const f = state.filters, parts = [];
  if (f.ide) parts.push(f.ide);
  if (f.model) parts.push(f.model);
  if (f.project) parts.push("project " + f.project);
  parts.push(f.days ? `last ${f.days} days` : "all time");
  return parts.join(", ");
}

export function pageHead(title, ...lead) {
  return h("header", { class: "page-head" }, h("h1", null, title), lead.length ? h("p", { class: "lead" }, lead) : null);
}

// ── Session detail (shared by every table that lists sessions) ───────────────

const KIND = { message: "said", tool_call: "tool", file_op: "file" };

export async function sessionDetail(row) {
  const id = row.id || row.session_id;
  const events = await api(`sessions/${encodeURIComponent(id)}/timeline`);
  const prompts = events.filter((e) => e.kind === "message" && e.subtype === "user" && e.detail && !e.detail.trimStart().startsWith("<") && e.detail.trim());
  const rows = events.filter((e) => e.kind !== "file_op");
  return h("div", { class: "detail-body" },
    h("p", { class: "note" }, "Session ", h("code", null, id), row.branch ? [" on branch ", h("code", null, row.branch)] : null),
    prompts.length ? disclosure(`${prompts.length} prompts you wrote`, () =>
      h("ol", { class: "prompt-list" }, prompts.map((p) => h("li", null, h("time", null, fmt.date(p.ts)), h("p", null, p.detail)))), { open: prompts.length <= 4 }) : null,
    disclosure(`Full timeline, ${fmt.n(rows.length)} events`, () => table({
      limit: 60,
      cols: [
        { key: "ts", label: "When", render: (e) => fmt.date(e.ts), width: "9.5rem" },
        { key: "subtype", label: "What", render: (e) => e.kind === "tool_call" ? pill(e.subtype) : pill(e.subtype === "user" ? "you" : "agent", e.subtype === "user" ? "accent" : null), width: "9rem" },
        { key: "detail", label: KIND.message, render: (e) => h("span", { class: "clip" }, (e.detail || "").slice(0, 180)) },
      ],
      rows,
      expand: (e) => pre(e.kind === "tool_call" ? pretty(e.detail) : e.detail),
    })));
}

export function sessionCols(extra = []) {
  return [
    { key: "created_at", label: "Started", render: (r) => fmt.date(r.created_at), width: "9.5rem" },
    { key: "project", label: "Project" },
    { key: "ide", label: "Agent", render: (r) => pill(r.ide || "unknown", agentTone(r.ide)) },
    { key: "model", label: "Model", render: (r) => (r.model === "unknown" ? null : r.model) },
    ...extra,
  ];
}

// ── Overview ─────────────────────────────────────────────────────────────────

function busiestWindow(cells) {
  const byHour = Array(24).fill(0);
  let total = 0;
  for (const c of cells) { byHour[c.hour] += c.c; total += c.c; }
  if (!total) return null;
  let best = 0, sum = -1;
  for (let s = 0; s < 24; s++) {
    const w = byHour[s] + byHour[(s + 1) % 24] + byHour[(s + 2) % 24];
    if (w > sum) { sum = w; best = s; }
  }
  const hh = (x) => String(x % 24).padStart(2, "0") + ":00";
  return { from: hh(best), to: hh(best + 3), share: sum / total };
}

function standouts(fr, ad) {
  const out = [];
  const known = fr.tools.filter((t) => t.known >= 20);
  const most = known[0];
  if (most) out.push(finding("warn", strong(most.tool), ` fails more than any other tool: ${fmt.n(most.errors)} of ${fmt.n(most.known)} calls (${fmt.pct(most.rate)}). `, link("See why", href("insights", { at: "sec-where-tools-fail" }))));
  const worst = known.filter((t) => t.known >= 100).sort((a, b) => b.rate - a.rate)[0];
  if (worst && worst !== most && worst.rate >= 0.05) out.push(finding("warn", strong(worst.tool), ` has the highest failure rate: ${fmt.pct(worst.rate)} of ${fmt.n(worst.known)} calls. `, link("See why", href("insights", { at: "sec-where-tools-fail" }))));
  const rare = ad.features.filter((f) => ["plan", "subagents", "workflows", "memory", "worktrees"].includes(f.key) && f.share != null && f.share < 0.05);
  for (const f of rare.slice(0, 3)) out.push(finding("plain", strong(f.label), ` shows up in ${fmt.n(f.sessions)} of ${fmt.n(ad.total_sessions)} sessions (${fmt.pct(f.share)}). `, link("Compare features", href("insights", { at: "sec-features-you-use" }))));
  return out;
}

export async function overview() {
  const [p, fr, ad] = await Promise.all([api("v2/pulse", {}, { filtered: true }), api("v2/friction", {}, { filtered: true }), api("v2/adoption", {}, { filtered: true })]);
  const k = p.kpis;
  if (!k.sessions) return h("div", null, pageHead("Nothing matches these filters"), empty("No sessions were recorded for this combination.", "Clear a filter above to widen the view."));
  const win = busiestWindow(p.heatmap);
  const cacheShare = k.tokens_cache_read ? k.tokens_cache_read / (k.tokens_cache_read + (k.tokens_input || 0)) : null;
  const series = (key) => p.daily.map((d) => d[key]);

  const stand = h("div", { class: "findings" }, standouts(fr, ad));
  // Memory evidence comes from another store and takes about a second; add it when it arrives.
  api("v2/memory-roi").then((m) => {
    for (const v of m.verdicts.filter((x) => x.tone === "bad").slice(0, 2)) stand.append(finding("bad", v.text + " ", link("Open Memory", href("memory"))));
  }).catch(() => {});

  const ides = [...new Set(p.by_ide.map((r) => r.ide))].sort();
  const dayMap = {};
  for (const r of p.by_ide) (dayMap[r.day] ||= {})[r.ide] = r.c;
  const daily = p.daily.map((d) => ({ x: d.day, parts: ides.map((i) => ({ value: dayMap[d.day]?.[i] || 0, tone: agentTone(i), name: i })) }));

  return h("div", null,
    pageHead(`${fmt.n(k.sessions)} sessions, ${fmt.n(k.prompts)} prompts, ${fmt.n(k.tool_calls)} tool calls`,
      `Across ${fmt.n(k.projects)} projects. Showing ${scopeText()}.`, k.active ? ` ${k.active} active in the last 30 minutes.` : null),
    h("section", { class: "sec hero" },
      h("h2", null, "When you work"),
      win ? h("p", { class: "lead" }, `${fmt.pct(win.share, 0)} of your prompts are written between ${win.from} and ${win.to}.`) : null,
      heatmap(p.heatmap),
      note("Each square is one hour of one weekday, in your local time. Brighter means more prompts.")),
    ledger([
      { label: "Sessions", value: fmt.n(k.sessions), spark: spark(series("sessions")) },
      { label: "Prompts", value: fmt.n(k.prompts), spark: spark(series("prompts")) },
      { label: "Tool calls", value: fmt.n(k.tool_calls), spark: spark(series("tools")) },
      { label: "Active time", value: fmt.mins(k.active_minutes), sub: "idle gaps over 30 min left out" },
      { label: "Output tokens", value: fmt.compact(k.tokens_output) },
      { label: "Served from cache", value: fmt.pct(cacheShare, 1), sub: "of input tokens" },
      { label: "Cost", value: fmt.money(k.cost), sub: "OpenCode sessions only" },
      { label: "Tool failures", value: fmt.pct(k.error_rate), sub: `${fmt.n(k.errors)} of ${fmt.n(k.calls_known)} with a known outcome` },
    ]),
    section("What stands out", null, stand),
    section("Sessions per day", `The last ${p.daily.length} days.`,
      columns(daily),
      h("p", { class: "legend" }, ides.map((i) => h("span", null, h("i", { class: "swatch fill-" + agentTone(i) }), i)))),
    section("Latest sessions", null,
      table({
        cols: sessionCols([
          { key: "prompts", label: "Prompts", num: true, render: (r) => fmt.n(r.prompts) },
          { key: "tool_count", label: "Tool calls", num: true, render: (r) => fmt.n(r.tool_count) },
          { key: "duration_min", label: "Active", num: true, render: (r) => fmt.mins(r.duration_min) },
        ]),
        rows: p.recent, expand: sessionDetail,
      }),
      h("p", null, link("All sessions", href("sessions")))));
}

// ── Sessions ─────────────────────────────────────────────────────────────────

const SORTS = [["recent", "Newest"], ["longest", "Longest"], ["tools", "Most tool calls"], ["errors", "Most failures"], ["cost", "Highest cost"]];

export async function sessionsPage(extra) {
  const sort = extra.sort || "recent";
  const data = await api("v2/sessions", { limit: 200, sort }, { filtered: true });
  return h("div", null,
    pageHead("Sessions", `${fmt.n(data.total)} sessions match. `, data.total > data.rows.length ? `The first ${data.rows.length} are listed; narrow the filters to reach the rest.` : null),
    h("div", { class: "seg", role: "group", "aria-label": "Sort" }, SORTS.map(([key, label]) =>
      h("a", { href: href("sessions", { sort: key }), "aria-pressed": String(sort === key), role: "button" }, label))),
    table({
      limit: 50,
      cols: sessionCols([
        { key: "first_prompt", label: "Opening prompt", render: (r) => h("span", { class: "clip" }, r.first_prompt) },
        { key: "prompts", label: "Prompts", num: true, render: (r) => fmt.n(r.prompts) },
        { key: "tool_count", label: "Tool calls", num: true, render: (r) => fmt.n(r.tool_count) },
        { key: "errors", label: "Failures", num: true, render: (r) => (r.errors ? fmt.n(r.errors) : null) },
        { key: "duration_min", label: "Active", num: true, render: (r) => fmt.mins(r.duration_min) },
        { key: "cost", label: "Cost", num: true, render: (r) => fmt.money(r.cost) },
      ]),
      rows: data.rows, expand: sessionDetail,
    }));
}

// ── Tools and skills ─────────────────────────────────────────────────────────

async function toolDetail(t) {
  const [sess, why] = await Promise.all([
    api("tool-sessions", { tool: t.tool }),
    t.errors ? api("v2/friction/tool", { tool: t.tool }, { filtered: true }) : null,
  ]);
  return h("div", { class: "detail-body" },
    why && why.reasons.length ? h("div", null, h("h4", null, "Why it fails"), bars(why.reasons.map((r) => ({ label: r.reason, value: r.count, tone: "red" })), { wide: true })) : null,
    h("h4", null, "Sessions that used it most recently"),
    table({
      limit: 10,
      cols: [
        { key: "created_at", label: "Started", render: (r) => fmt.date(r.created_at) },
        { key: "project", label: "Project" },
        { key: "invocations", label: "Calls", num: true, render: (r) => fmt.n(r.invocations) },
      ],
      rows: sess, expand: sessionDetail,
    }));
}

export async function toolsPage() {
  const d = await api("v2/tools", {}, { filtered: true });
  const groups = {};
  for (const t of d.tools) (groups[t.family] ||= []).push(t);
  const names = Object.keys(groups).sort((a, b) => (a === "Built-in" ? -1 : b === "Built-in" ? 1 : groups[b].reduce((s, t) => s + t.calls, 0) - groups[a].reduce((s, t) => s + t.calls, 0)));
  const maxCalls = Math.max(...d.tools.map((t) => t.calls), 1);
  const toolTable = (rows) => table({
    cols: [
      { key: "tool", label: "Tool", render: (t) => t.tool.replace(/^mcp__[^_]+(?:_[^_]+)*?__/, "") },
      { key: "calls", label: "Calls", num: true, render: (t) => meter(t.calls, maxCalls, fmt.n(t.calls)) },
      { key: "sessions", label: "Sessions", num: true, render: (t) => fmt.n(t.sessions) },
      { key: "rate", label: "Failure rate", num: true, title: "Failures divided by calls with a known outcome", render: (t) => (t.known ? fmt.pct(t.rate) : null) },
      { key: "avg_ms", label: "Average time", num: true, render: (t) => fmt.ms(t.avg_ms) },
      { key: "last_used", label: "Last used", render: (t) => fmt.ago(t.last_used) },
    ],
    rows, expand: toolDetail,
  });
  return h("div", null,
    pageHead("Tools and skills", `${fmt.n(d.tools.length)} different tools were called, in ${names.length} groups.`),
    names.map((n) => {
      const calls = groups[n].reduce((s, t) => s + t.calls, 0);
      return disclosure(h("span", null, strong(n), ` ${groups[n].length} tools, ${fmt.n(calls)} calls`), () => toolTable(groups[n]), { open: n === "Built-in" });
    }),
    section("Skills", "Loaded through the Skill tool. A skill that is never loaded is not earning its place.",
      table({
        limit: 25,
        cols: [
          { key: "skill", label: "Skill" },
          { key: "calls", label: "Loads", num: true, render: (s) => fmt.n(s.calls) },
          { key: "sessions", label: "Sessions", num: true, render: (s) => fmt.n(s.sessions) },
          { key: "last_used", label: "Last used", render: (s) => fmt.ago(s.last_used) },
        ],
        rows: d.skills,
      })));
}

// ── Files (project → folder → file) ──────────────────────────────────────────

// Some imports recorded the project as a folder slug ("-home-me-project-foo")
// instead of its name. Resolve a slug to the folder it names, so both spellings
// of one project land in the same branch of the tree.
function splitPath(path, project) {
  const parts = path.split("/").filter(Boolean);
  if (project.startsWith("-")) {
    let slug = "";
    for (let i = 0; i < parts.length; i++) {
      slug += "-" + parts[i];
      if (slug === project) return { name: parts[i], rel: parts.slice(i + 1) };
    }
    return null;
  }
  const at = parts.indexOf(project);
  return { name: project, rel: at >= 0 ? parts.slice(at + 1) : parts };
}

function buildTree(rows) {
  const root = { name: "", kids: new Map(), reads: 0, writes: 0, files: 0 };
  const slugName = {};
  const placed = rows.map((r) => {
    const project = r.project || "(no project)";
    const hit = splitPath(r.path, project);
    if (hit && project.startsWith("-")) slugName[project] = hit.name;
    return { r, project, hit };
  });
  for (const { r, project, hit } of placed) {
    // A file outside its project's folder keeps its full path under that project.
    const name = hit ? hit.name : slugName[project] || project;
    const rel = hit ? hit.rel : r.path.split("/").filter(Boolean);
    let node = root;
    for (const part of [name, ...rel]) {
      if (!node.kids.has(part)) node.kids.set(part, { name: part, kids: new Map(), reads: 0, writes: 0, files: 0 });
      node = node.kids.get(part);
      node.reads += r.reads; node.writes += r.writes; node.files += 1;
    }
    node.leaf = r;
  }
  return root;
}

function treeNode(node, depth, max) {
  // Fold a chain of single-child folders into one line: src/coworker/dashboard
  let name = node.name;
  while (!node.leaf && node.kids.size === 1) {
    const only = [...node.kids.values()][0];
    if (only.leaf || depth === 0) break;
    name += "/" + only.name; node = only;
  }
  const figures = h("span", { class: "tree-figs" },
    meter(node.writes, max, fmt.n(node.writes) + " edits", "accent"),
    h("span", { class: "tree-reads" }, fmt.n(node.reads) + " reads"),
    node.leaf ? h("span", { class: "tree-reads" }, fmt.ago(node.leaf.last_touched)) : h("span", { class: "tree-reads" }, fmt.n(node.files) + " files"));
  if (node.leaf) return h("div", { class: "tree-row leaf", style: { paddingLeft: depth * 1.1 + 1.4 + "rem" } }, h("span", { class: "tree-name", title: node.leaf.path }, name), figures);
  const kids = [...node.kids.values()].sort((a, b) => b.writes + b.reads - (a.writes + a.reads));
  const d = disclosure(h("span", { class: "tree-line" }, h("span", { class: "tree-name" }, name + (depth ? "/" : "")), figures),
    () => h("div", null, kids.map((k) => treeNode(k, depth + 1, max))));
  d.firstChild.style.paddingLeft = depth * 1.1 + "rem";
  d.classList.add("tree-row");
  return d;
}

export async function filesPage() {
  const d = await api("v2/files", {}, { filtered: true });
  if (!d.rows.length) return h("div", null, pageHead("Files"), empty("No file activity was recorded for this filter."));
  const tree = buildTree(d.rows);
  const tops = [...tree.kids.values()].sort((a, b) => b.writes + b.reads - (a.writes + a.reads));
  const max = Math.max(...tops.map((t) => t.writes), 1);
  return h("div", null,
    pageHead("Files", `${fmt.n(d.totals.files)} files touched: ${fmt.n(d.totals.reads)} reads and ${fmt.n(d.totals.writes)} edits.`),
    d.totals.files > d.rows.length ? note(`The tree holds the ${fmt.n(d.rows.length)} most-touched files; totals above count all of them.`) : null,
    h("div", { class: "tree" }, tops.map((t) => treeNode(t, 0, max))));
}

// ── Projects ─────────────────────────────────────────────────────────────────

export async function projectsPage() {
  const rows = await api("v2/projects", {}, { filtered: true });
  const max = Math.max(...rows.map((r) => r.sessions), 1);
  return h("div", null,
    pageHead("Projects", `${fmt.n(rows.length)} projects have recorded sessions.`),
    table({
      cols: [
        { key: "project", label: "Project" },
        { key: "sessions", label: "Sessions", num: true, render: (r) => meter(r.sessions, max, fmt.n(r.sessions)) },
        { key: "ides", label: "Agents", render: (r) => (r.ides || "").split(",").filter(Boolean).map((i) => pill(i, agentTone(i))) },
        { key: "tools", label: "Tool calls", num: true, render: (r) => fmt.n(r.tools) },
        { key: "minutes", label: "Active time", num: true, render: (r) => fmt.mins(r.minutes) },
        { key: "tokens_output", label: "Output tokens", num: true, render: (r) => fmt.compact(r.tokens_output) },
        { key: "cost", label: "Cost", num: true, render: (r) => fmt.money(r.cost) },
        { key: "last_active", label: "Last session", render: (r) => fmt.ago(r.last_active) },
      ],
      rows,
      expand: async (r) => {
        if (r.project === "(none)") return note("These sessions carry no project name.");
        const s = await api("v2/sessions", { project: r.project, limit: 15 }, { filtered: true });
        return h("div", { class: "detail-body" },
          h("p", null, link(`Filter every page to ${r.project}`, "#/" + "?project=" + encodeURIComponent(r.project))),
          table({ cols: sessionCols([{ key: "first_prompt", label: "Opening prompt", render: (x) => h("span", { class: "clip" }, x.first_prompt) }, { key: "tool_count", label: "Tool calls", num: true, render: (x) => fmt.n(x.tool_count) }]), rows: s.rows, expand: sessionDetail }));
      },
    }));
}

// ── Data health ──────────────────────────────────────────────────────────────

export async function healthPage() {
  const d = await api("v2/health");
  const weak = d.checks.filter((c) => c.share != null && c.share < 0.6);
  return h("div", null,
    pageHead("Data health", "How much of each field is actually recorded. A page that depends on a thin field says so instead of filling the gap."),
    weak.length ? finding("warn", `${weak.length} of ${d.checks.length} fields cover less than 60% of their records.`) : finding("good", "Every field covers at least 60% of its records."),
    table({
      cols: [
        { key: "name", label: "Field" },
        { key: "share", label: "Recorded", num: true, render: (c) => meter(c.share, 1, fmt.pct(c.share, 0), c.share < 0.6 ? "red" : "green") },
        { key: "covered", label: "Records", num: true, render: (c) => `${fmt.n(c.covered)} of ${fmt.n(c.total)}` },
        { key: "note", label: "What it affects" },
      ],
      rows: d.checks,
    }));
}
