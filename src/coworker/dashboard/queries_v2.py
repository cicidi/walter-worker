"""Queries behind the redesigned dashboard (/api/v2/*).

Every query here takes a Filters value (tool, model, project, time range), so
one filter bar drives every page. Rules these queries keep:

- A "prompt" is a user message a person typed: not empty and not a
  harness-injected block (those start with "<").
- Error rates divide by calls whose outcome is known (is_error IS NOT NULL).
  About half of the older imported calls carry no flag; counting them as
  successes would halve every rate.
- Missing data is returned as None or reported as coverage, never as 0.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..analytics.db import get_db

MODEL_SQL = """COALESCE(NULLIF(CASE WHEN s.model LIKE '{%}' THEN json_extract(s.model, '$.id')
                                    ELSE s.model END, ''), 'unknown')"""
PROMPT_SQL = "m.type = 'user' AND TRIM(m.content, ' \n\t\r') != '' AND m.content NOT LIKE '<%'"


@dataclass(frozen=True)
class Filters:
    ide: str = ""
    model: str = ""
    project: str = ""
    days: int = 0  # 0 = all time

    def where(self) -> tuple[str, list]:
        """SQL predicate over `sessions s`, and its parameters."""
        sql, params = ["1=1"], []
        if self.ide:
            sql.append("s.ide = ?")
            params.append(self.ide)
        if self.model:
            sql.append(f"{MODEL_SQL} = ?")
            params.append(self.model)
        if self.project:
            sql.append("s.project = ?")
            params.append(self.project)
        if self.days and self.days > 0:
            sql.append("s.created_at >= strftime('%Y-%m-%dT%H:%M:%fZ', 'now', ?)")
            params.append(f"-{int(self.days)} days")
        return " AND ".join(sql), params


def _rows(conn, sql: str, params=()) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _rate(errors, known):
    return round(errors / known, 4) if known else None


# ── Filter options ───────────────────────────────────────────────────────────

def filter_options() -> dict:
    conn = get_db()
    try:
        return {
            "ides": _rows(conn, "SELECT s.ide AS value, COUNT(*) AS count FROM sessions s "
                                "WHERE s.ide != '' GROUP BY 1 ORDER BY 2 DESC"),
            "models": _rows(conn, f"SELECT {MODEL_SQL} AS value, COUNT(*) AS count FROM sessions s "
                                  "GROUP BY 1 ORDER BY 2 DESC"),
            "projects": _rows(conn, "SELECT s.project AS value, COUNT(*) AS count FROM sessions s "
                                    "WHERE COALESCE(s.project, '') != '' GROUP BY 1 ORDER BY 2 DESC"),
        }
    finally:
        conn.close()


# ── Pulse (home) ─────────────────────────────────────────────────────────────

def pulse(f: Filters) -> dict:
    w, p = f.where()
    conn = get_db()
    try:
        k = dict(conn.execute(
            f"""SELECT COUNT(*) AS sessions,
                       COUNT(DISTINCT NULLIF(s.project, '')) AS projects,
                       SUM(s.closed_at >= strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '-30 minutes')) AS active,
                       SUM(ss.tokens_input) AS tokens_input, SUM(ss.tokens_output) AS tokens_output,
                       SUM(ss.tokens_cache_read) AS tokens_cache_read, SUM(ss.cost) AS cost,
                       SUM(ss.duration_min) AS active_minutes
                FROM sessions s LEFT JOIN session_stats ss ON ss.session_id = s.id WHERE {w}""", p).fetchone())
        k["prompts"] = conn.execute(
            f"SELECT COUNT(*) FROM messages m JOIN sessions s ON s.id = m.session_id "
            f"WHERE {PROMPT_SQL} AND {w}", p).fetchone()[0]
        t = conn.execute(
            f"""SELECT COUNT(*), SUM(tc.is_error IS NOT NULL), COALESCE(SUM(tc.is_error), 0)
                FROM tool_calls tc JOIN sessions s ON s.id = tc.session_id WHERE {w}""", p).fetchone()
        k.update(tool_calls=t[0], calls_known=t[1] or 0, errors=t[2], error_rate=_rate(t[2], t[1] or 0))

        span = min(f.days, 365) if f.days else 90
        since = f"-{span - 1} days"

        def per_day(sql: str) -> dict:
            return {r["day"]: r["c"] for r in _rows(conn, sql, [*p, since])}

        d_sessions = per_day(f"""SELECT date(s.created_at, 'localtime') AS day, COUNT(*) AS c FROM sessions s
            WHERE {w} AND s.created_at != '' AND date(s.created_at, 'localtime') >= date('now', 'localtime', ?)
            GROUP BY 1""")
        d_prompts = per_day(f"""SELECT date(m.ts, 'localtime') AS day, COUNT(*) AS c
            FROM messages m JOIN sessions s ON s.id = m.session_id
            WHERE {PROMPT_SQL} AND {w} AND date(m.ts, 'localtime') >= date('now', 'localtime', ?) GROUP BY 1""")
        d_tools = per_day(f"""SELECT date(tc.ts, 'localtime') AS day, COUNT(*) AS c
            FROM tool_calls tc JOIN sessions s ON s.id = tc.session_id
            WHERE {w} AND date(tc.ts, 'localtime') >= date('now', 'localtime', ?) GROUP BY 1""")
        days = [r[0] for r in conn.execute(
            """WITH RECURSIVE d(day, n) AS (SELECT date('now', 'localtime'), 1
                   UNION ALL SELECT date(day, '-1 day'), n + 1 FROM d WHERE n < ?)
               SELECT day FROM d ORDER BY day""", (span,))]
        daily = [{"day": d, "sessions": d_sessions.get(d, 0), "prompts": d_prompts.get(d, 0),
                  "tools": d_tools.get(d, 0)} for d in days]
        by_ide = _rows(conn, f"""
            SELECT date(s.created_at, 'localtime') AS day, s.ide, COUNT(*) AS c FROM sessions s
            WHERE {w} AND s.created_at != '' AND date(s.created_at, 'localtime') >= date('now', 'localtime', ?)
            GROUP BY 1, 2""", [*p, since])
        heat = _rows(conn, f"""
            SELECT CAST(strftime('%w', m.ts, 'localtime') AS INTEGER) AS dow,
                   CAST(strftime('%H', m.ts, 'localtime') AS INTEGER) AS hour, COUNT(*) AS c
            FROM messages m JOIN sessions s ON s.id = m.session_id
            WHERE {PROMPT_SQL} AND {w} AND m.ts != '' GROUP BY 1, 2""", p)
        return {"kpis": k, "daily": daily, "by_ide": by_ide, "heatmap": heat,
                "recent": sessions(f, limit=8)["rows"]}
    finally:
        conn.close()


# ── Friction: where tools fail ───────────────────────────────────────────────

def friction(f: Filters) -> dict:
    w, p = f.where()
    conn = get_db()
    try:
        tools = _rows(conn, f"""
            SELECT tc.tool, COUNT(*) AS calls, SUM(tc.is_error IS NOT NULL) AS known,
                   COALESCE(SUM(tc.is_error), 0) AS errors, COUNT(DISTINCT tc.session_id) AS sessions,
                   ROUND(AVG(tc.duration_ms)) AS avg_ms
            FROM tool_calls tc JOIN sessions s ON s.id = tc.session_id WHERE {w}
            GROUP BY tc.tool HAVING errors > 0 ORDER BY errors DESC LIMIT 40""", p)
        for t in tools:
            t["rate"] = _rate(t["errors"], t["known"])
        # A retry: a failed call whose next call in the same session is the same tool.
        retries = _rows(conn, f"""
            WITH seq AS (
                SELECT tc.tool, tc.is_error,
                       LEAD(tc.tool) OVER (PARTITION BY tc.session_id
                                           ORDER BY COALESCE(tc.seq_before, tc.seq_after), tc.id) AS next_tool
                FROM tool_calls tc JOIN sessions s ON s.id = tc.session_id WHERE {w})
            SELECT tool, COUNT(*) AS retries FROM seq WHERE is_error = 1 AND next_tool = tool
            GROUP BY tool""", p)
        rmap = {r["tool"]: r["retries"] for r in retries}
        for t in tools:
            t["retries"] = rmap.get(t["tool"], 0)
        monthly = _rows(conn, f"""
            SELECT strftime('%Y-%m', tc.ts, 'localtime') AS month, SUM(tc.is_error IS NOT NULL) AS known,
                   COALESCE(SUM(tc.is_error), 0) AS errors
            FROM tool_calls tc JOIN sessions s ON s.id = tc.session_id
            WHERE {w} AND tc.ts != '' GROUP BY 1 ORDER BY 1""", p)
        for m in monthly:
            m["rate"] = _rate(m["errors"], m["known"])
        worst = _rows(conn, f"""
            SELECT s.id, s.project, s.ide, s.created_at, COALESCE(SUM(tc.is_error), 0) AS errors,
                   COUNT(*) AS calls
            FROM tool_calls tc JOIN sessions s ON s.id = tc.session_id WHERE {w}
            GROUP BY s.id HAVING errors > 0 ORDER BY errors DESC LIMIT 10""", p)
        unknown = conn.execute(
            f"SELECT COUNT(*) FROM tool_calls tc JOIN sessions s ON s.id = tc.session_id "
            f"WHERE tc.is_error IS NULL AND {w}", p).fetchone()[0]
        return {"tools": tools, "monthly": monthly, "worst_sessions": worst, "unknown_outcome": unknown}
    finally:
        conn.close()


_PATH_RE = re.compile(r"(/[\w.\-]+){2,}")
_NUM_RE = re.compile(r"\d+")


def _reason(text: str | None) -> str:
    """First line of an error, with paths and numbers blanked so repeats group."""
    line = (text or "").strip().split("\n", 1)[0][:160]
    line = _PATH_RE.sub("<path>", line)
    return _NUM_RE.sub("N", line)[:90] or "(no error text recorded)"


def friction_tool(tool: str, f: Filters, limit: int = 30) -> dict:
    """Why one tool fails: grouped reasons and the most recent failed calls."""
    w, p = f.where()
    conn = get_db()
    try:
        rows = _rows(conn, f"""
            SELECT tc.session_id, s.project, tc.ts, SUBSTR(tc.args, 1, 400) AS args,
                   SUBSTR(tc.result, 1, 400) AS result
            FROM tool_calls tc JOIN sessions s ON s.id = tc.session_id
            WHERE tc.tool = ? AND tc.is_error = 1 AND {w} ORDER BY tc.ts DESC LIMIT 2000""", [tool, *p])
    finally:
        conn.close()
    reasons: dict[str, int] = {}
    for r in rows:
        key = _reason(r["result"])
        reasons[key] = reasons.get(key, 0) + 1
    top = sorted(reasons.items(), key=lambda kv: -kv[1])[:12]
    return {"tool": tool, "failed": len(rows),
            "reasons": [{"reason": k, "count": v} for k, v in top], "examples": rows[:limit]}


# ── Feature adoption ─────────────────────────────────────────────────────────

# (key, label, what it is for, SQL predicate over tool_calls tc)
FEATURES = [
    ("plan", "Plan mode", "Agree on an approach before any edit",
     "tc.tool IN ('EnterPlanMode', 'ExitPlanMode')"),
    ("subagents", "Subagents", "Hand side work to a separate agent, keep the main context small",
     "tc.tool IN ('Agent', 'Task')"),
    ("skills", "Skills", "Reusable instructions loaded on demand", "tc.tool = 'Skill'"),
    ("workflows", "Workflows", "Scripted multi-agent runs", "tc.tool = 'Workflow'"),
    ("questions", "Clarifying questions", "The agent asks before guessing",
     "tc.tool IN ('AskUserQuestion', 'Question')"),
    ("tasks", "Task lists", "A visible plan with progress",
     "tc.tool IN ('TodoWrite', 'TaskCreate', 'TaskUpdate', 'TaskList')"),
    ("web", "Web research", "Search and read the web", "tc.tool IN ('WebSearch', 'WebFetch')"),
    ("browser", "Browser automation", "Drive a real browser to verify UI work",
     "tc.tool LIKE 'mcp__plugin_playwright%'"),
    ("mcp", "MCP tools", "Any tool from a connected MCP server",
     "(tc.tool LIKE 'mcp__%' OR tc.tool LIKE 'github_%' OR tc.tool LIKE 'memory-graph_%')"),
    ("scheduling", "Background and scheduled work", "Loops, wake-ups, cron jobs, monitors",
     "tc.tool IN ('ScheduleWakeup', 'CronCreate', 'Monitor', 'Yield')"),
    ("memory", "Memory recall", "Look up lessons from past sessions",
     "(tc.tool LIKE 'mcp__memory%' OR tc.tool LIKE 'memory-graph_%' OR (tc.tool = 'Bash' AND "
     "(tc.args LIKE '%coworker memory query%' OR tc.args LIKE '%coworker memory search%')))"),
    ("worktrees", "Git worktrees", "Isolated checkouts for parallel work",
     "(tc.tool IN ('EnterWorktree', 'ExitWorktree') OR (tc.tool = 'Bash' AND tc.args LIKE '%git worktree add%'))"),
]
_FEATURE_SQL = {key: pred for key, _, _, pred in FEATURES}


def adoption(f: Filters) -> dict:
    w, p = f.where()
    conn = get_db()
    try:
        total = conn.execute(f"SELECT COUNT(*) FROM sessions s WHERE {w}", p).fetchone()[0]
        out = []
        for key, label, purpose, pred in FEATURES:
            r = dict(conn.execute(f"""
                SELECT COUNT(*) AS calls, COUNT(DISTINCT tc.session_id) AS sessions,
                       MIN(NULLIF(tc.ts, '')) AS first_used, MAX(tc.ts) AS last_used
                FROM tool_calls tc JOIN sessions s ON s.id = tc.session_id WHERE {pred} AND {w}""", p).fetchone())
            r["monthly"] = _rows(conn, f"""
                SELECT strftime('%Y-%m', tc.ts, 'localtime') AS month, COUNT(DISTINCT tc.session_id) AS sessions
                FROM tool_calls tc JOIN sessions s ON s.id = tc.session_id
                WHERE {pred} AND {w} AND tc.ts != '' GROUP BY 1 ORDER BY 1""", p)
            r.update(key=key, label=label, purpose=purpose,
                     share=round(r["sessions"] / total, 4) if total else None)
            out.append(r)
        out.sort(key=lambda r: -r["sessions"])
        return {"total_sessions": total, "features": out}
    finally:
        conn.close()


def adoption_sessions(key: str, f: Filters, limit: int = 40) -> list[dict]:
    pred = _FEATURE_SQL.get(key)
    if pred is None:
        return []
    w, p = f.where()
    conn = get_db()
    try:
        return _rows(conn, f"""
            SELECT s.id, s.project, s.ide, {MODEL_SQL} AS model, s.created_at, COUNT(*) AS calls
            FROM tool_calls tc JOIN sessions s ON s.id = tc.session_id WHERE {pred} AND {w}
            GROUP BY s.id ORDER BY s.created_at DESC LIMIT ?""", [*p, limit])
    finally:
        conn.close()


# ── Prompt habits ────────────────────────────────────────────────────────────

LENGTH_BUCKETS = [(0, "under 20"), (20, "20–79"), (80, "80–199"), (200, "200–499"),
                  (500, "500–1,499"), (1500, "1,500+")]
_BUCKET_SQL = "CASE " + " ".join(
    f"WHEN L >= {lo} THEN {i}" for i, (lo, _) in reversed(list(enumerate(LENGTH_BUCKETS)))) + " END"
# Heuristic: the prompt opens by saying the last answer was wrong.
_CORRECTION_SQL = " OR ".join(
    "LOWER(LTRIM(m.content)) LIKE '{}%'".format(s.replace("'", "''")) for s in
    ("不对", "不是", "错了", "不行", "还是不", "为什么没", "no,", "no.", "nope", "wrong", "that's not",
     "thats not", "not what", "you didn", "still not", "still broken", "doesn't work", "does not work"))


def prompts(f: Filters) -> dict:
    w, p = f.where()
    conn = get_db()
    try:
        base = f"FROM messages m JOIN sessions s ON s.id = m.session_id WHERE {PROMPT_SQL} AND {w}"
        hist = {r["b"]: r["c"] for r in _rows(conn, f"""
            SELECT {_BUCKET_SQL} AS b, COUNT(*) AS c FROM (SELECT LENGTH(m.content) AS L {base}) GROUP BY 1""", p)}
        total = sum(hist.values())
        # Sessions grouped by the length of their opening prompt.
        opening = _rows(conn, f"""
            WITH firsts AS (
                SELECT m.session_id AS sid, LENGTH(m.content) AS L,
                       ROW_NUMBER() OVER (PARTITION BY m.session_id ORDER BY m.seq, m.id) AS rn {base}),
            per AS (
                SELECT fi.sid, {_BUCKET_SQL} AS b,
                       (SELECT COUNT(*) FROM messages m WHERE m.session_id = fi.sid AND {PROMPT_SQL}) AS turns,
                       (SELECT COUNT(*) FROM tool_calls tc WHERE tc.session_id = fi.sid) AS tools,
                       (SELECT COALESCE(SUM(tc.is_error), 0) FROM tool_calls tc WHERE tc.session_id = fi.sid) AS errors
                FROM firsts fi WHERE fi.rn = 1)
            SELECT b, COUNT(*) AS sessions, ROUND(AVG(turns), 1) AS avg_turns, ROUND(AVG(tools), 1) AS avg_tools,
                   ROUND(1.0 * SUM(tools) / MAX(SUM(turns), 1), 1) AS tools_per_prompt, SUM(errors) AS errors
            FROM per GROUP BY b ORDER BY b""", p)
        for r in opening:
            r["bucket"] = LENGTH_BUCKETS[r["b"]][1]
        short = _rows(conn, f"""
            SELECT LOWER(TRIM(m.content)) AS text, COUNT(*) AS count, COUNT(DISTINCT m.session_id) AS sessions
            {base} AND LENGTH(m.content) <= 24 GROUP BY 1 HAVING count >= 3 ORDER BY 2 DESC LIMIT 20""", p)
        corr = _rows(conn, f"""
            SELECT strftime('%Y-%m', m.ts, 'localtime') AS month, COUNT(*) AS prompts,
                   SUM(CASE WHEN {_CORRECTION_SQL} THEN 1 ELSE 0 END) AS corrections
            {base} AND m.ts != '' GROUP BY 1 ORDER BY 1""", p)
        for r in corr:
            r["rate"] = _rate(r["corrections"], r["prompts"])
        corr_examples = _rows(conn, f"""
            SELECT m.session_id, s.project, m.ts, SUBSTR(m.content, 1, 200) AS text
            {base} AND ({_CORRECTION_SQL}) ORDER BY m.ts DESC LIMIT 25""", p)
        commands = _rows(conn, f"""
            SELECT SUBSTR(m.content, INSTR(m.content, '<command-name>') + 14,
                          INSTR(m.content, '</command-name>') - INSTR(m.content, '<command-name>') - 14) AS command,
                   COUNT(*) AS count, COUNT(DISTINCT m.session_id) AS sessions
            FROM messages m JOIN sessions s ON s.id = m.session_id
            WHERE m.type = 'user' AND m.content LIKE '%<command-name>%' AND {w}
            GROUP BY 1 ORDER BY 2 DESC LIMIT 20""", p)
        avg_len = conn.execute(f"SELECT ROUND(AVG(LENGTH(m.content))) {base}", p).fetchone()[0]
        return {
            "total": total, "avg_length": avg_len,
            "histogram": [{"bucket": lbl, "count": hist.get(i, 0)} for i, (_, lbl) in enumerate(LENGTH_BUCKETS)],
            "by_opening": opening, "short_repeats": short, "corrections_monthly": corr,
            "corrections_total": sum(r["corrections"] for r in corr), "correction_examples": corr_examples,
            "commands": commands,
        }
    finally:
        conn.close()


# ── Session shape ────────────────────────────────────────────────────────────

DURATION_BUCKETS = [(0, "under 5 min"), (5, "5–14"), (15, "15–29"), (30, "30–59"), (60, "1–2 h"), (120, "over 2 h")]


def shape(f: Filters) -> dict:
    w, p = f.where()
    conn = get_db()
    try:
        case = "CASE " + " ".join(
            f"WHEN ss.duration_min >= {lo} THEN {i}"
            for i, (lo, _) in reversed(list(enumerate(DURATION_BUCKETS)))) + " END"
        dur = {r["b"]: r for r in _rows(conn, f"""
            SELECT {case} AS b, COUNT(*) AS sessions, ROUND(AVG(ss.tool_count), 1) AS avg_tools
            FROM sessions s JOIN session_stats ss ON ss.session_id = s.id
            WHERE ss.duration_min > 0 AND {w} GROUP BY 1""", p)}
        per_model = _rows(conn, f"""
            SELECT {MODEL_SQL} AS model, s.ide, COUNT(*) AS sessions,
                   ROUND(AVG(NULLIF(ss.duration_min, 0)), 1) AS avg_minutes,
                   ROUND(AVG(NULLIF(ss.tool_count, 0)), 1) AS avg_tools,
                   ROUND(AVG(NULLIF(ss.turn_count, 0)), 1) AS avg_turns
            FROM sessions s LEFT JOIN session_stats ss ON ss.session_id = s.id WHERE {w}
            GROUP BY 1, 2 HAVING sessions >= 2 ORDER BY sessions DESC LIMIT 20""", p)
        longest = _rows(conn, f"""
            SELECT s.id, s.project, s.ide, {MODEL_SQL} AS model, s.created_at, ss.duration_min,
                   ss.tool_count, ss.message_count
            FROM sessions s JOIN session_stats ss ON ss.session_id = s.id WHERE {w}
            ORDER BY ss.duration_min DESC LIMIT 12""", p)
        return {
            "durations": [{"bucket": lbl, "sessions": dur.get(i, {}).get("sessions", 0),
                           "avg_tools": dur.get(i, {}).get("avg_tools")}
                          for i, (_, lbl) in enumerate(DURATION_BUCKETS)],
            "by_model": per_model, "longest": longest,
        }
    finally:
        conn.close()


# ── Cost and cache ───────────────────────────────────────────────────────────

def cost(f: Filters) -> dict:
    w, p = f.where()
    conn = get_db()
    try:
        models = _rows(conn, f"""
            SELECT {MODEL_SQL} AS model, COUNT(*) AS sessions,
                   SUM(ss.tokens_input > 0 OR ss.tokens_output > 0) AS sessions_with_tokens,
                   SUM(ss.tokens_input) AS input, SUM(ss.tokens_output) AS output,
                   SUM(ss.tokens_reasoning) AS reasoning, SUM(ss.tokens_cache_read) AS cache_read,
                   SUM(ss.tokens_cache_write) AS cache_write, SUM(ss.cost) AS cost,
                   SUM(ss.cost > 0) AS sessions_with_cost
            FROM sessions s LEFT JOIN session_stats ss ON ss.session_id = s.id WHERE {w}
            GROUP BY 1 ORDER BY COALESCE(SUM(ss.tokens_input), 0) + COALESCE(SUM(ss.tokens_output), 0) DESC""", p)
        for m in models:
            read, inp = m["cache_read"] or 0, m["input"] or 0
            m["cache_share"] = round(read / (read + inp), 4) if read + inp else None
        daily = _rows(conn, f"""
            SELECT date(s.created_at, 'localtime') AS day, SUM(ss.tokens_input) AS input,
                   SUM(ss.tokens_output) AS output, SUM(ss.cost) AS cost
            FROM sessions s JOIN session_stats ss ON ss.session_id = s.id
            WHERE {w} AND s.created_at != '' GROUP BY 1 ORDER BY 1 DESC LIMIT 60""", p)
        return {"models": models, "daily": daily[::-1]}
    finally:
        conn.close()


# ── Sessions explorer ────────────────────────────────────────────────────────

_SORTS = {"recent": "s.created_at DESC", "longest": "ss.duration_min DESC", "tools": "ss.tool_count DESC",
          "errors": "errors DESC", "cost": "ss.cost DESC"}


def sessions(f: Filters, limit: int = 50, offset: int = 0, sort: str = "recent") -> dict:
    w, p = f.where()
    conn = get_db()
    try:
        total = conn.execute(f"SELECT COUNT(*) FROM sessions s WHERE {w}", p).fetchone()[0]
        rows = _rows(conn, f"""
            SELECT s.id, s.ide, s.project, {MODEL_SQL} AS model, s.feature, s.branch, s.created_at, s.closed_at,
                   ss.duration_min, ss.tool_count, ss.cost, ss.tokens_input, ss.tokens_output,
                   (SELECT COUNT(*) FROM messages m WHERE m.session_id = s.id AND {PROMPT_SQL}) AS prompts,
                   (SELECT COALESCE(SUM(tc.is_error), 0) FROM tool_calls tc WHERE tc.session_id = s.id) AS errors,
                   (SELECT SUBSTR(m.content, 1, 160) FROM messages m WHERE m.session_id = s.id AND {PROMPT_SQL}
                     ORDER BY m.seq, m.id LIMIT 1) AS first_prompt
            FROM sessions s LEFT JOIN session_stats ss ON ss.session_id = s.id WHERE {w}
            ORDER BY {_SORTS.get(sort, _SORTS['recent'])} LIMIT ? OFFSET ?""",
                     [*p, max(1, min(limit, 200)), max(0, offset)])
        return {"total": total, "rows": rows}
    finally:
        conn.close()


# ── Tools ────────────────────────────────────────────────────────────────────

def _family(tool: str) -> str:
    if tool.startswith("mcp__"):
        server = tool[5:].split("__", 1)[0].removeprefix("plugin_")
        half = len(server) // 2
        if server[:half] + "_" + server[:half] == server:  # plugin_playwright_playwright
            server = server[:half]
        return "MCP: " + server
    if tool.startswith(("github_", "memory-graph_")):
        return "MCP: " + tool.split("_", 1)[0]
    return "Built-in"


def tools(f: Filters) -> dict:
    w, p = f.where()
    conn = get_db()
    try:
        rows = _rows(conn, f"""
            SELECT tc.tool, COUNT(*) AS calls, COUNT(DISTINCT tc.session_id) AS sessions,
                   ROUND(AVG(tc.duration_ms)) AS avg_ms, MAX(tc.duration_ms) AS max_ms,
                   SUM(tc.is_error IS NOT NULL) AS known, COALESCE(SUM(tc.is_error), 0) AS errors,
                   MAX(tc.ts) AS last_used
            FROM tool_calls tc JOIN sessions s ON s.id = tc.session_id WHERE {w}
            GROUP BY tc.tool ORDER BY calls DESC""", p)
        for r in rows:
            r["family"] = _family(r["tool"])
            r["rate"] = _rate(r["errors"], r["known"])
        skills = _rows(conn, f"""
            SELECT COALESCE(json_extract(tc.args, '$.skill'), json_extract(tc.args, '$.name')) AS skill,
                   COUNT(*) AS calls, COUNT(DISTINCT tc.session_id) AS sessions, MAX(tc.ts) AS last_used
            FROM tool_calls tc JOIN sessions s ON s.id = tc.session_id
            WHERE tc.tool = 'Skill' AND json_valid(tc.args) AND {w}
            GROUP BY 1 HAVING skill IS NOT NULL ORDER BY calls DESC LIMIT 80""", p)
        return {"tools": rows, "skills": skills}
    finally:
        conn.close()


# ── Files ────────────────────────────────────────────────────────────────────

def files(f: Filters, limit: int = 1500) -> dict:
    """Most-touched files; the page folds them into a project → folder → file tree."""
    w, p = f.where()
    conn = get_db()
    try:
        rows = _rows(conn, f"""
            SELECT fo.path, COALESCE(NULLIF(fo.project, ''), s.project) AS project,
                   SUM(fo.op = 'read') AS reads, SUM(fo.op IN ('write', 'edit')) AS writes,
                   COUNT(DISTINCT fo.session_id) AS sessions, MAX(fo.ts) AS last_touched
            FROM file_ops fo JOIN sessions s ON s.id = fo.session_id WHERE {w}
            GROUP BY fo.path ORDER BY COUNT(*) DESC LIMIT ?""", [*p, limit])
        tot = dict(conn.execute(f"""
            SELECT COUNT(DISTINCT fo.path) AS files, SUM(fo.op = 'read') AS reads,
                   SUM(fo.op IN ('write', 'edit')) AS writes
            FROM file_ops fo JOIN sessions s ON s.id = fo.session_id WHERE {w}""", p).fetchone())
        return {"totals": tot, "rows": rows}
    finally:
        conn.close()


# ── Projects ─────────────────────────────────────────────────────────────────

def projects(f: Filters) -> list[dict]:
    w, p = f.where()
    conn = get_db()
    try:
        return _rows(conn, f"""
            SELECT COALESCE(NULLIF(s.project, ''), '(none)') AS project, COUNT(*) AS sessions,
                   GROUP_CONCAT(DISTINCT s.ide) AS ides, MAX(s.created_at) AS last_active,
                   SUM(ss.tool_count) AS tools, SUM(ss.duration_min) AS minutes, SUM(ss.cost) AS cost,
                   SUM(ss.tokens_input) AS tokens_input, SUM(ss.tokens_output) AS tokens_output
            FROM sessions s LEFT JOIN session_stats ss ON ss.session_id = s.id WHERE {w}
            GROUP BY 1 ORDER BY sessions DESC""", p)
    finally:
        conn.close()


# ── Data health ──────────────────────────────────────────────────────────────

def health() -> dict:
    """How much of each field is actually recorded. Pages cite this instead of guessing."""
    conn = get_db()
    try:
        n = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        calls = conn.execute("SELECT COUNT(*) FROM tool_calls").fetchone()[0]

        def one(sql):
            return conn.execute(sql).fetchone()[0] or 0

        checks = [
            ("Model recorded", one("SELECT COUNT(*) FROM sessions WHERE COALESCE(model, '') != ''"), n,
             "Per-model comparisons skip sessions without it"),
            ("Start time recorded", one("SELECT COUNT(*) FROM sessions WHERE COALESCE(created_at, '') != ''"), n,
             "Sessions without it fall out of any time-range filter"),
            ("Token counts", one("SELECT COUNT(*) FROM session_stats WHERE tokens_input > 0 OR tokens_output > 0"), n,
             "Token totals cover only these sessions"),
            ("Cost", one("SELECT COUNT(*) FROM session_stats WHERE cost > 0"), n,
             "OpenCode reports cost; Claude Code transcripts carry no price"),
            ("Project name normalized", one("SELECT COUNT(*) FROM sessions WHERE COALESCE(project, '') != '' "
                                            "AND project NOT LIKE '-%'"), n,
             "Names starting with '-' are raw folder slugs, so one project can appear twice"),
            ("Session summary", one("SELECT COUNT(*) FROM session_summaries"), n,
             "Written by `coworker memory train`"),
            ("Tool call outcome known", one("SELECT COUNT(*) FROM tool_calls WHERE is_error IS NOT NULL"), calls,
             "Error rates are computed over these calls only"),
            ("Tool call duration", one("SELECT COUNT(*) FROM tool_calls WHERE duration_ms > 0"), calls,
             "Latency averages use these calls only"),
        ]
        return {"sessions": n, "tool_calls": calls,
                "checks": [{"name": a, "covered": b, "total": c, "share": round(b / c, 4) if c else None, "note": d}
                           for a, b, c, d in checks]}
    finally:
        conn.close()
