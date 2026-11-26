// Insights: what the record says about how you work with agents, most useful first.
import { api, href } from "./main.js";
import { h, fmt, section, finding, strong, note, pill, meter, table, bars, columns, spark, link, pre, pretty } from "./ui.js";
import { pageHead, sessionDetail, sessionCols } from "./pages-core.js";

// ── 1. Where tools fail ──────────────────────────────────────────────────────

async function failureDetail(t) {
  const d = await api("v2/friction/tool", { tool: t.tool }, { filtered: true });
  return h("div", { class: "detail-body" },
    h("h4", null, "Reasons, grouped"),
    bars(d.reasons.map((r) => ({ label: r.reason, value: r.count, tone: "red" })), { wide: true }),
    h("h4", null, "Most recent failures"),
    table({
      limit: 8,
      cols: [
        { key: "ts", label: "When", render: (e) => fmt.date(e.ts), width: "9.5rem" },
        { key: "project", label: "Project" },
        { key: "result", label: "Error", render: (e) => h("span", { class: "clip" }, (e.result || "").split("\n")[0]) },
      ],
      rows: d.examples,
      expand: (e) => h("div", { class: "detail-body" }, h("h4", null, "What was sent"), pre(pretty(e.args)), h("h4", null, "What came back"), pre(e.result)),
    }));
}

function frictionSection(fr) {
  const known = fr.tools.filter((t) => t.known >= 20);
  const top = known[0];
  const worst = known.filter((t) => t.known >= 100).sort((a, b) => b.rate - a.rate)[0];
  const maxErr = Math.max(...fr.tools.map((t) => t.errors), 1);
  return section("Where tools fail", "A failed call costs a round trip, and often a retry. These are the tools worth changing a habit for.",
    top ? finding("warn", strong(top.tool), ` fails most: ${fmt.n(top.errors)} of ${fmt.n(top.known)} calls (${fmt.pct(top.rate)}). `,
      top.retries ? `${fmt.n(top.retries)} of those failures were followed straight away by another ${top.tool} call.` : null) : finding("good", "No tool failures are recorded for this filter."),
    worst && worst !== top ? finding("warn", strong(worst.tool), ` has the highest rate: ${fmt.pct(worst.rate)} of ${fmt.n(worst.known)} calls fail.`) : null,
    table({
      cols: [
        { key: "tool", label: "Tool" },
        { key: "errors", label: "Failures", num: true, render: (t) => meter(t.errors, maxErr, fmt.n(t.errors), "red") },
        { key: "known", label: "Calls with a known outcome", num: true, render: (t) => fmt.n(t.known) },
        { key: "rate", label: "Failure rate", num: true, render: (t) => fmt.pct(t.rate) },
        { key: "retries", label: "Retried at once", num: true, title: "Failures followed by the same tool in the same session", render: (t) => fmt.n(t.retries) },
        { key: "sessions", label: "Sessions", num: true, render: (t) => fmt.n(t.sessions) },
      ],
      rows: fr.tools, expand: failureDetail, limit: 12,
    }),
    h("h3", null, "Failure rate by month"),
    columns(fr.monthly.map((m) => ({ x: m.month, parts: [{ value: m.rate == null ? 0 : m.rate * 100, tone: "red" }] })), { format: (v) => v.toFixed(1) + "%", every: 1, height: 90 }),
    fr.unknown_outcome ? note(`${fmt.n(fr.unknown_outcome)} older calls were imported without an outcome and are left out of every rate here.`) : null,
    h("h3", null, "Sessions with the most failures"),
    table({
      cols: sessionCols([
        { key: "errors", label: "Failures", num: true, render: (r) => fmt.n(r.errors) },
        { key: "calls", label: "Tool calls", num: true, render: (r) => fmt.n(r.calls) },
      ]).filter((c) => c.key !== "model"),
      rows: fr.worst_sessions, expand: sessionDetail,
    }));
}

// ── 2. Features you use ──────────────────────────────────────────────────────

function adoptionSection(ad) {
  const rare = ad.features.filter((f) => f.share != null && f.share < 0.05);
  return section("Features you use", "How many sessions each capability shows up in. A low share is not a fault; it marks something you could try more often.",
    rare.length ? finding("plain", `${rare.length} capabilities appear in under 5% of sessions: `, rare.map((f) => f.label).join(", "), ".") : null,
    table({
      cols: [
        { key: "label", label: "Capability", render: (f) => h("span", null, strong(f.label), h("span", { class: "sub" }, f.purpose)) },
        { key: "share", label: "Share of sessions", num: true, render: (f) => meter(f.share, 1, fmt.pct(f.share), f.share < 0.05 ? "yellow" : "accent") },
        { key: "sessions", label: "Sessions", num: true, render: (f) => fmt.n(f.sessions) },
        { key: "calls", label: "Calls", num: true, render: (f) => fmt.n(f.calls) },
        { key: "trend", label: "By month", sort: (f) => f.monthly.length, render: (f) => spark(f.monthly.map((m) => m.sessions)) },
        { key: "last_used", label: "Last used", render: (f) => fmt.ago(f.last_used) },
      ],
      rows: ad.features,
      expand: async (f) => {
        if (!f.sessions) return note("Never used in the sessions that match this filter.");
        const rows = await api("v2/adoption/sessions", { key: f.key }, { filtered: true });
        return table({ limit: 10, cols: sessionCols([{ key: "calls", label: "Calls", num: true, render: (r) => fmt.n(r.calls) }]), rows, expand: sessionDetail });
      },
    }));
}

// ── 3. How you prompt ────────────────────────────────────────────────────────

function promptsSection(pr) {
  if (!pr.total) return section("How you prompt", null, note("No prompts are recorded for this filter."));
  const short = pr.histogram[0].count + pr.histogram[1].count;
  const corrMax = Math.max(...pr.corrections_monthly.map((m) => m.corrections), 0);
  return section("How you prompt", `${fmt.n(pr.total)} prompts, ${fmt.n(pr.avg_length)} characters on average.`,
    finding("plain", `${fmt.pct(short / pr.total, 0)} of your prompts are under 80 characters.`),
    h("div", { class: "split" },
      h("div", null, h("h3", null, "Prompt length"), bars(pr.histogram.map((b) => ({ label: b.bucket + " characters", value: b.count })))),
      h("div", null, h("h3", null, "Short prompts you repeat"),
        table({ limit: 8, cols: [{ key: "text", label: "Prompt", render: (r) => h("q", null, r.text) }, { key: "count", label: "Times", num: true, render: (r) => fmt.n(r.count) }, { key: "sessions", label: "Sessions", num: true, render: (r) => fmt.n(r.sessions) }], rows: pr.short_repeats, emptyText: "No short prompt is repeated three times or more." }))),
    h("h3", null, "Does a longer opening prompt change the session?"),
    table({
      cols: [
        { key: "b", label: "Opening prompt length", render: (r) => r.bucket + " characters" },
        { key: "sessions", label: "Sessions", num: true, render: (r) => fmt.n(r.sessions) },
        { key: "avg_turns", label: "Prompts per session", num: true, render: (r) => r.avg_turns },
        { key: "tools_per_prompt", label: "Tool calls per prompt", num: true, title: "How much work the agent did per prompt you wrote", render: (r) => r.tools_per_prompt },
        { key: "avg_tools", label: "Tool calls per session", num: true, render: (r) => fmt.n(r.avg_tools) },
      ],
      rows: pr.by_opening,
    }),
    note("Sessions are grouped by the length of their first prompt. This shows a pattern, not a cause: longer openings also go with bigger tasks."),
    h("div", { class: "split" },
      h("div", null, h("h3", null, "Slash commands"),
        table({ limit: 10, cols: [{ key: "command", label: "Command", render: (r) => h("code", null, r.command) }, { key: "count", label: "Times", num: true, render: (r) => fmt.n(r.count) }, { key: "sessions", label: "Sessions", num: true, render: (r) => fmt.n(r.sessions) }], rows: pr.commands, emptyText: "No slash commands are recorded." })),
      h("div", null, h("h3", null, "Prompts that open by rejecting the last answer"),
        corrMax ? columns(pr.corrections_monthly.map((m) => ({ x: m.month, parts: [{ value: m.corrections, tone: "yellow" }] })), { every: 1, height: 70 }) : null,
        note(`${fmt.n(pr.corrections_total)} found by matching openings such as "不对", "还是不行", "no," and "wrong". The match is rough and misses rephrased corrections.`),
        pr.correction_examples.length ? table({ limit: 5, cols: [{ key: "ts", label: "When", render: (r) => fmt.day(r.ts) }, { key: "project", label: "Project" }, { key: "text", label: "Prompt", render: (r) => h("span", { class: "clip" }, r.text) }], rows: pr.correction_examples, expand: (r) => sessionDetail({ id: r.session_id }) }) : null)));
}

// ── 4. Shape of a session ────────────────────────────────────────────────────

function shapeSection(sh) {
  const total = sh.durations.reduce((a, d) => a + d.sessions, 0);
  const long = sh.durations.slice(4).reduce((a, d) => a + d.sessions, 0);
  return section("Shape of a session", "Active time leaves out idle gaps longer than 30 minutes.",
    total ? finding("plain", `${fmt.pct(long / total, 0)} of timed sessions run longer than an hour of active work.`) : null,
    h("div", { class: "split" },
      h("div", null, h("h3", null, "Active time"), bars(sh.durations.map((d) => ({ label: d.bucket, value: d.sessions, sub: d.avg_tools ? `about ${fmt.n(d.avg_tools)} tool calls each` : "" })))),
      h("div", null, h("h3", null, "By agent and model"),
        table({
          limit: 8,
          cols: [
            { key: "model", label: "Model", render: (r) => (r.model === "unknown" ? "not recorded" : r.model) },
            { key: "ide", label: "Agent", render: (r) => pill(r.ide) },
            { key: "sessions", label: "Sessions", num: true, render: (r) => fmt.n(r.sessions) },
            { key: "avg_minutes", label: "Average active", num: true, render: (r) => fmt.mins(r.avg_minutes) },
            { key: "avg_tools", label: "Tool calls", num: true, render: (r) => fmt.n(r.avg_tools) },
          ],
          rows: sh.by_model,
        }))),
    h("h3", null, "Longest sessions"),
    table({
      limit: 6,
      cols: sessionCols([
        { key: "duration_min", label: "Active", num: true, render: (r) => fmt.mins(r.duration_min) },
        { key: "tool_count", label: "Tool calls", num: true, render: (r) => fmt.n(r.tool_count) },
      ]),
      rows: sh.longest, expand: sessionDetail,
    }));
}

// ── 5. Tokens, cache and cost ────────────────────────────────────────────────

function costSection(co) {
  const withTokens = co.models.filter((m) => m.sessions_with_tokens);
  const noTokens = co.models.reduce((a, m) => a + (m.sessions - (m.sessions_with_tokens || 0)), 0);
  const maxOut = Math.max(...withTokens.map((m) => m.output || 0), 1);
  return section("Tokens, cache and cost", "Cache share is the part of input tokens served from the prompt cache. Higher is cheaper and faster.",
    table({
      cols: [
        { key: "model", label: "Model", render: (m) => (m.model === "unknown" ? "not recorded" : m.model) },
        { key: "sessions_with_tokens", label: "Sessions", num: true, render: (m) => fmt.n(m.sessions_with_tokens) },
        { key: "output", label: "Output tokens", num: true, render: (m) => meter(m.output, maxOut, fmt.compact(m.output)) },
        { key: "input", label: "Input tokens", num: true, render: (m) => fmt.compact(m.input) },
        { key: "cache_read", label: "Read from cache", num: true, render: (m) => fmt.compact(m.cache_read) },
        { key: "cache_share", label: "Cache share", num: true, render: (m) => fmt.pct(m.cache_share, 1) },
        { key: "cost", label: "Cost", num: true, render: (m) => fmt.money(m.cost) },
      ],
      rows: withTokens, emptyText: "No token counts are recorded for this filter.",
    }),
    note(`${fmt.n(noTokens)} sessions carry no token counts and are left out. Cost is recorded only where the agent reports a price; Claude Code transcripts do not.`),
    co.daily.length ? [h("h3", null, "Output tokens per day"), columns(co.daily.map((d) => ({ x: d.day, parts: [{ value: d.output || 0 }] })), { format: fmt.compact, height: 90 })] : null);
}

export async function insightsPage() {
  const f = { filtered: true };
  const [fr, ad, pr, sh, co] = await Promise.all([api("v2/friction", {}, f), api("v2/adoption", {}, f), api("v2/prompts", {}, f), api("v2/shape", {}, f), api("v2/cost", {}, f)]);
  const toc = [["Where tools fail", "sec-where-tools-fail"], ["Features you use", "sec-features-you-use"], ["How you prompt", "sec-how-you-prompt"], ["Shape of a session", "sec-shape-of-a-session"], ["Tokens, cache and cost", "sec-tokens-cache-and-cost"]];
  return h("div", null,
    pageHead("Insights", "What the record says about how you work with agents, ordered by how directly you can act on it."),
    h("nav", { class: "toc", "aria-label": "On this page" }, toc.map(([label, id]) => link(label, href("insights", { at: id })))),
    frictionSection(fr), adoptionSection(ad), promptsSection(pr), shapeSection(sh), costSection(co));
}
