// Memory: is the capture-and-recall work paying off? Plus Evolution (skills and review queue).
import { api, post } from "./main.js";
import { h, fmt, section, finding, strong, note, empty, pill, meter, disclosure, table, bars, columns, funnel, ledger, pre } from "./ui.js";
import { pageHead, sessionDetail } from "./pages-core.js";

const top = (list, tone) => bars((list || []).map((x) => ({ label: x.value, value: x.count, tone })));

// ── Memory ───────────────────────────────────────────────────────────────────

function captureSection(c) {
  if (!c.available) return section("Capture", null, note("No capture log was found at ~/.coworker/memory/audit.log."));
  const allBlank = c.error_reasons.length === 1 && c.error_reasons[0].reason.startsWith("(no reason");
  return section("Capture", "Each time a session stops, a hook reads the conversation and writes down lessons.",
    ledger([
      { label: "Attempts", value: fmt.n(c.attempts) },
      { label: "Failed", value: fmt.n(c.errors), sub: fmt.pct(c.error_rate, 0) + " of attempts" },
      { label: "Lessons written", value: fmt.n(c.lessons) },
      { label: "Sessions captured", value: fmt.n(c.sessions) },
      { label: "Average time", value: c.avg_seconds == null ? "–" : c.avg_seconds + " s" },
    ]),
    h("h3", null, "Attempts on each day that had any"),
    columns(c.daily.map((d) => ({ x: d.day, parts: [{ value: d.ok, tone: "green", name: "worked" }, { value: d.error, tone: "red", name: "failed" }] })), { height: 100 }),
    h("p", { class: "legend" }, h("span", null, h("i", { class: "swatch fill-green" }), "worked"), h("span", null, h("i", { class: "swatch fill-red" }), "failed")),
    c.errors ? [h("h3", null, "Why attempts failed"), allBlank
      ? note(`None of the ${fmt.n(c.errors)} failed attempts recorded a reason. Captures made after the audit fix write one.`)
      : bars(c.error_reasons.map((r) => ({ label: r.reason, value: r.count, tone: "red" })), { wide: true })] : null);
}

function storeSection(s, error) {
  if (!s) return section("What is stored", null, empty("The lesson store could not be read.", error));
  const u = s.use_count;
  return section("What is stored", `${fmt.n(s.total)} lessons from ${fmt.n(s.source_sessions)} sessions.`,
    h("div", { class: "split" },
      h("div", null, h("h3", null, "By kind"), top(s.by_type), h("h3", null, "By state"), top(s.by_state, "green")),
      h("div", null, h("h3", null, "By project"), top(s.by_project.slice(0, 8), "blue"))),
    h("h3", null, "Lessons written on each day that had any"),
    columns(s.created_daily.map((d) => ({ x: d.day, parts: [{ value: d.count }] })), { height: 90 }),
    disclosure("Most common topics", () => top(s.top_topics)),
    h("h3", null, "Recorded reuse"),
    ledger([
      { label: "Never marked as used", value: fmt.n(u.never_used), sub: fmt.pct(u.never_used / Math.max(s.total, 1), 0) + " of lessons" },
      { label: "Median use count", value: fmt.n(u.median) },
      { label: "Highest use count", value: fmt.n(u.max) },
      { label: "Scored by the curator", value: fmt.n(s.scored) },
    ]),
    note(u.caveat));
}

function recallSection(r, sessions) {
  return section("Recall", "A lookup is the agent asking memory a question during a session, through the memory tools or `coworker memory query`.",
    finding(r.sessions > sessions / 20 ? "good" : "bad", `${fmt.n(r.calls)} lookups in ${fmt.n(r.sessions)} sessions. The most recent was ${fmt.ago(r.last)}.`),
    r.monthly.length ? [h("h3", null, "Lookups per month"), columns(r.monthly.map((m) => ({ x: m.month, parts: [{ value: m.calls, tone: "blue" }] })), { every: 1, height: 80 })] : null,
    r.recent.length ? [h("h3", null, "Most recent lookups"), table({
      limit: 6,
      cols: [
        { key: "ts", label: "When", render: (x) => fmt.date(x.ts), width: "9.5rem" },
        { key: "project", label: "Project" },
        { key: "tool", label: "Through", render: (x) => pill(x.tool === "Bash" ? "command line" : "memory tool") },
        { key: "args", label: "Asked", render: (x) => h("span", { class: "clip" }, x.args) },
      ],
      rows: r.recent, expand: (x) => sessionDetail({ id: x.session_id }),
    })] : null);
}

function injectSection(i) {
  const e = i.export;
  return section("Handed to new sessions", "What a session receives without asking for it.",
    i.snapshot_lines == null
      ? finding("plain", "~/CLAUDE.local.md has no memory block.")
      : finding(i.snapshot_lines ? "good" : "bad", `The memory block in ~/CLAUDE.local.md holds ${i.snapshot_lines} lesson${i.snapshot_lines === 1 ? "" : "s"}.`),
    e ? finding("plain", `The MEMORY.md export lists ${fmt.n(e.entries)} lessons (${fmt.compact(e.bytes)} bytes), written ${e.generated}. Nothing loads it into a session automatically.`)
      : finding("plain", "No MEMORY.md export exists."));
}

function summariesSection(s) {
  const max = Math.max(s.count, 1);
  return section("Session summaries", "Written by `coworker memory train`: what to remember, what went wrong, and an efficiency score.",
    finding((s.coverage || 0) < 0.2 ? "bad" : "good", `${fmt.n(s.count)} of ${fmt.n(s.sessions)} sessions have a summary (${fmt.pct(s.coverage, 0)}). `,
      s.count ? `They were written between ${fmt.day(s.first)} and ${fmt.day(s.last)}.` : null),
    s.count ? table({
      cols: [
        { key: "field", label: "Field", render: (f) => h("code", null, f.field) },
        { key: "filled", label: "Filled in", num: true, render: (f) => meter(f.filled, max, `${fmt.n(f.filled)} of ${fmt.n(s.count)}`, f.filled ? "green" : "red") },
      ],
      rows: s.fields,
    }) : null);
}

function browser(store) {
  const state = { q: "", project: "", type: "", state: "" };
  const out = h("div");
  let timer = 0, token = 0;
  const load = async () => {
    const mine = ++token;
    out.replaceChildren(note("Loading…"));
    try {
      const d = await api("v2/memories", { ...state, limit: 300 });
      if (mine !== token) return;
      out.replaceChildren(
        note(d.error ? "The lesson store could not be read: " + d.error : `${fmt.n(d.total)} lessons match${d.total > d.rows.length ? `; the newest ${d.rows.length} are listed` : ""}.`),
        table({
          limit: 25,
          cols: [
            { key: "created_at", label: "Written", render: (m) => fmt.day(m.created_at), width: "6.5rem" },
            { key: "type", label: "Kind", render: (m) => pill(m.type || "unknown") },
            { key: "project", label: "Project" },
            { key: "topic", label: "Topic" },
            { key: "memory", label: "Lesson", render: (m) => h("span", { class: "clip" }, m.memory) },
            { key: "use_count", label: "Uses", num: true, render: (m) => fmt.n(m.use_count) },
          ],
          rows: d.rows, emptyText: "No lesson matches.",
          expand: (m) => h("div", { class: "detail-body" },
            h("p", { class: "lesson" }, m.memory),
            m.problem ? h("p", null, strong("Problem it answers: "), m.problem) : null,
            h("p", { class: "note" }, `State ${m.state}. Last marked as used ${fmt.ago(m.last_used)}. `, m.score != null ? `Curator score ${m.score}. ` : null),
            m.source_session ? disclosure("The session it came from", () => sessionDetail({ id: m.source_session })) : null),
        }));
    } catch (e) {
      if (mine === token) out.replaceChildren(empty("Could not load lessons.", e.message));
    }
  };
  const pick = (label, key, items) => h("label", { class: "filter" }, h("span", null, label),
    h("select", { onchange: (e) => { state[key] = e.target.value; load(); } },
      h("option", { value: "" }, "All"), (items || []).filter((i) => i.value !== "(none)").map((i) => h("option", { value: i.value }, `${i.value} (${i.count})`))));
  const controls = h("div", { class: "filters inline" },
    h("label", { class: "filter grow" }, h("span", null, "Search"),
      h("input", { type: "search", placeholder: "Words in the lesson, topic or problem", oninput: (e) => { state.q = e.target.value; clearTimeout(timer); timer = setTimeout(load, 250); } })),
    pick("Kind", "type", store?.by_type), pick("State", "state", store?.by_state), pick("Project", "project", store?.by_project));
  load();
  return section("Browse the lessons", "Reading here does not count as a use.", controls, out);
}

export async function memoryPage() {
  const m = await api("v2/memory-roi");
  const sessions = m.summaries.sessions;
  const ratio = m.store && m.recall.calls ? Math.round(m.store.total / m.recall.calls) : null;
  return h("div", null,
    pageHead("Is the memory work paying off?", "Memory is a pipeline: sessions are captured into lessons, lessons are stored, and stored lessons should come back in later sessions. Each stage is measured where it leaves a trace."),
    h("div", { class: "findings" },
      m.verdicts.map((v) => finding(v.tone, v.text)),
      ratio ? finding("plain", `About ${fmt.n(ratio)} lessons have been stored for every lookup.`) : null),
    h("section", { class: "sec hero" }, h("h2", null, "From session to reuse"), funnel(m.funnel),
      note("Bar lengths use a square-root scale so the small stages stay visible.")),
    captureSection(m.capture), storeSection(m.store, m.store_error), recallSection(m.recall, sessions),
    injectSection(m.inject), summariesSection(m.summaries), browser(m.store));
}

// ── Evolution ────────────────────────────────────────────────────────────────

function actions(buttons, done) {
  const msg = h("span", { class: "note" });
  return h("p", { class: "actions" }, buttons.map(([label, run, cls]) =>
    h("button", { type: "button", class: cls || null, onclick: async (e) => {
      e.target.disabled = true;
      try { msg.textContent = " " + (await run()); done?.(); }
      catch (err) { msg.textContent = " Did not work: " + err.message; e.target.disabled = false; }
    } }, label)), msg);
}

export async function evolutionPage() {
  const [ov, skills, pending] = await Promise.all([api("evolution/overview"), api("evolution/skills", { status: "all" }), api("evolution/pending")]);
  return h("div", null,
    pageHead("Evolution", "Skills the system wrote for itself, and drafts waiting for your review."),
    ledger([
      { label: "Evolution score", value: ov.evolution_score + " / 100" },
      { label: "Skills written by agents", value: fmt.n(ov.auto_trained_skills) },
      { label: "Sessions that reused one", value: fmt.pct(ov.skill_reuse_rate, 0) },
      { label: "Lessons stored", value: fmt.n(ov.auto_trained_experiences) },
      { label: "Drafts awaiting review", value: fmt.n(ov.pending_review) },
    ]),
    section("Skills", null, table({
      cols: [
        { key: "name", label: "Skill" },
        { key: "provenance", label: "Written by", render: (s) => pill(s.provenance || "unknown") },
        { key: "state", label: "State", render: (s) => pill(s.state || "unknown", s.state === "active" ? "green" : null) },
        { key: "total_calls", label: "Loads", num: true, render: (s) => fmt.n(s.total_calls) },
        { key: "sessions_invoked", label: "Sessions", num: true, render: (s) => fmt.n(s.sessions_invoked) },
        { key: "last_used", label: "Last used", render: (s) => fmt.ago(s.last_used) },
      ],
      rows: skills, emptyText: "No agent-written skills yet.",
      expand: async (s) => {
        const d = await api("evolution/skills/" + encodeURIComponent(s.name));
        const set = (status) => async () => (await post(`evolution/skills/${encodeURIComponent(s.name)}/status`, { status })).status ? `Set to ${status}.` : "";
        return h("div", { class: "detail-body" },
          d.description ? h("p", null, d.description) : null,
          actions([["Set active", set("active")], ["Set pending", set("pending")], ["Set inactive", set("inactive")]]),
          d.content ? disclosure("Skill text", () => pre(d.content)) : note("No SKILL.md was found for this skill."));
      },
    })),
    section("Drafts awaiting review", `${fmt.n(pending.length)} drafts. Approving one installs it as a skill.`, table({
      limit: 20,
      cols: [
        { key: "name", label: "Draft" },
        { key: "description", label: "What it does", render: (p) => h("span", { class: "clip" }, p.description) },
        { key: "tool_call_count", label: "Steps", num: true, render: (p) => fmt.n(p.tool_call_count) },
        { key: "staged_at", label: "Drafted", render: (p) => fmt.ago(p.staged_at) },
      ],
      rows: pending, emptyText: "Nothing is waiting for review.",
      expand: (p) => h("div", { class: "detail-body" },
        h("p", null, p.description),
        actions([
          ["Approve", async () => "Approved: " + (await post("evolution/approve/" + encodeURIComponent(p.id))).status + "."],
          ["Reject", async () => "Rejected: " + (await post("evolution/reject/" + encodeURIComponent(p.id))).status + ".", "danger"],
        ]),
        p.source_session ? disclosure("The session it came from", () => sessionDetail({ id: p.source_session })) : null),
    })),
    section("Knowledge graph", "Code, documents, sessions and decisions, linked.",
      disclosure("Open the graph", () => h("iframe", { class: "graph", src: "/graph.html", title: "Knowledge graph" }))));
}
