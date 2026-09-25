from __future__ import annotations
from ..analytics.db import get_db
from .queries_evolution import _get_db_conn


def query_sessions(limit: int = 50):
    conn = get_db()
    rows = conn.execute(
        """SELECT s.*, ss.message_count, ss.tool_count, ss.skill_count, ss.duration_min
           FROM sessions s LEFT JOIN session_stats ss ON s.id = ss.session_id
           ORDER BY s.created_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_session_detail(session_id: str):
    conn = get_db()
    session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    msgs = conn.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY seq", (session_id,)).fetchall()
    tools = conn.execute(
        "SELECT * FROM tool_calls WHERE session_id = ? ORDER BY COALESCE(seq_before, seq_after)",
        (session_id,),
    ).fetchall()
    files = conn.execute("SELECT * FROM file_ops WHERE session_id = ? ORDER BY seq", (session_id,)).fetchall()
    summary = conn.execute("SELECT * FROM session_summaries WHERE session_id = ?", (session_id,)).fetchone()
    stats = conn.execute("SELECT * FROM session_stats WHERE session_id = ?", (session_id,)).fetchone()
    conn.close()
    return {
        "session": dict(session) if session else None,
        "messages": [dict(m) for m in msgs],
        "tool_calls": [dict(t) for t in tools],
        "file_ops": [dict(f) for f in files],
        "summary": dict(summary) if summary else None,
        "stats": dict(stats) if stats else None,
    }


def query_skills():
    conn = get_db()
    rows = conn.execute("SELECT * FROM skills ORDER BY total_calls DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_tools():
    conn = get_db()
    rows = conn.execute(
        """SELECT tool, tool_type, server_name, COUNT(*) as calls,
                  ROUND(AVG(duration_ms), 1) as avg_ms, MAX(duration_ms) as max_ms
           FROM tool_calls GROUP BY tool, tool_type ORDER BY calls DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_files(project: str | None = None, file_type: str | None = None, limit: int = 500):
    conn = get_db()
    params = []
    sql = "SELECT f.* FROM file_ops f WHERE 1=1"
    if project:
        sql += " AND f.project = ?"
        params.append(project)
    if file_type:
        sql += " AND f.file_type = ?"
        params.append(file_type)
    sql += " ORDER BY f.ts DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_knowledge():
    conn = get_db()
    rows = conn.execute("SELECT * FROM knowledge ORDER BY generated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_features():
    conn = get_db()
    rows = conn.execute(
        """SELECT s.feature, s.project, COUNT(DISTINCT s.id) as session_count,
                  COUNT(DISTINCT t.call_id) as tool_count
           FROM sessions s LEFT JOIN tool_calls t ON s.id = t.session_id
           WHERE s.feature IS NOT NULL AND s.feature != ''
           GROUP BY s.feature ORDER BY session_count DESC"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_overview():
    conn = get_db()
    total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    total_messages = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
    total_tools = conn.execute("SELECT COUNT(*) FROM tool_calls").fetchone()[0]
    total_skills = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
    total_knowledge = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
    active = conn.execute("SELECT COUNT(*) FROM sessions WHERE closed_at IS NULL OR closed_at = ''").fetchone()[0]

    recent = conn.execute(
        "SELECT * FROM sessions ORDER BY created_at DESC LIMIT 10"
    ).fetchall()

    tool_dist = conn.execute(
        "SELECT tool, COUNT(*) as c FROM tool_calls GROUP BY tool ORDER BY c DESC LIMIT 10"
    ).fetchall()

    daily = conn.execute(
        """SELECT substr(created_at, 1, 10) as day, COUNT(*) as c
           FROM sessions GROUP BY day ORDER BY day DESC LIMIT 14"""
    ).fetchall()

    conn.close()
    return {
        "total_sessions": total_sessions,
        "total_messages": total_messages,
        "total_tools": total_tools,
        "total_skills": total_skills,
        "total_knowledge": total_knowledge,
        "active_sessions": active,
        "recent_sessions": [dict(r) for r in recent],
        "tool_distribution": [dict(r) for r in tool_dist],
        "daily_sessions": [dict(r) for r in daily],
    }


def query_session_timeline(session_id: str):
    """Unified chronological timeline: messages + tool_calls + file_ops interleaved."""
    conn = get_db()
    rows = conn.execute(
        """SELECT ts, 'message' as kind, seq, type as subtype, content as detail, NULL as tool
           FROM messages WHERE session_id = ?
           UNION ALL
           SELECT ts, 'tool_call' as kind,
                  COALESCE(seq_before, seq_after) as seq, tool as subtype,
                  COALESCE(args, '') as detail, tool
           FROM tool_calls WHERE session_id = ?
           UNION ALL
           SELECT ts, 'file_op' as kind,
                  seq, op as subtype,
                  path as detail, NULL as tool
           FROM file_ops WHERE session_id = ?
           ORDER BY ts, seq""",
        (session_id, session_id, session_id),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_skill_sessions():
    """Which skills were used in which sessions."""
    conn = get_db()
    rows = conn.execute(
        """SELECT tc.session_id, tc.tool as skill_name, COUNT(*) as invocations,
                  s.project, s.created_at
           FROM tool_calls tc
           JOIN sessions s ON tc.session_id = s.id
           WHERE tc.tool = 'Skill'
           GROUP BY tc.session_id, tc.tool
           ORDER BY s.created_at DESC
           LIMIT 200"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_file_stats():
    """Top files touched across all sessions, with read/write breakdown."""
    conn = get_db()
    rows = conn.execute(
        """SELECT path as file_path, op as op_type, COUNT(*) as ops, s.project
           FROM file_ops f
           LEFT JOIN sessions s ON f.session_id = s.id
           GROUP BY path, op
           ORDER BY ops DESC
           LIMIT 200"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_top_files(limit: int = 50):
    """Files ranked by total touches."""
    conn = get_db()
    rows = conn.execute(
        """SELECT path as file_path, COUNT(*) as total_ops,
                  SUM(CASE WHEN op = 'read' THEN 1 ELSE 0 END) as reads,
                  SUM(CASE WHEN op IN ('write','edit') THEN 1 ELSE 0 END) as writes,
                  GROUP_CONCAT(DISTINCT s.project) as projects
           FROM file_ops f
           LEFT JOIN sessions s ON f.session_id = s.id
           GROUP BY path
           ORDER BY total_ops DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Enhanced monitoring queries
# ---------------------------------------------------------------------------


def query_file_hotspots(limit: int = 30):
    """Most frequently modified files with churn metrics."""
    conn = _get_db_conn()
    try:
        rows = conn.execute(
            """SELECT path, file_type, COUNT(*) as total_ops,
                      SUM(CASE WHEN op='write' THEN 1 ELSE 0 END) as writes,
                      SUM(CASE WHEN op='edit' THEN 1 ELSE 0 END) as edits,
                      SUM(CASE WHEN op='read' THEN 1 ELSE 0 END) as reads,
                      SUM(CASE WHEN op NOT IN ('read','write','edit','glob') THEN 1 ELSE 0 END) as deletes,
                      COUNT(DISTINCT session_id) as sessions_touched,
                      COUNT(DISTINCT project) as projects,
                      MAX(ts) as last_touched
               FROM file_ops
               GROUP BY path
               ORDER BY total_ops DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_activity_timeline(hours: int = 24):
    """Hourly activity breakdown."""
    conn = _get_db_conn()
    try:
        rows = conn.execute(
            """SELECT substr(ts, 1, 13) as hour,
                      COUNT(*) as tool_calls,
                      COUNT(DISTINCT session_id) as active_sessions
               FROM tool_calls
               WHERE ts >= datetime('now', ? || ' hours')
               GROUP BY hour
               ORDER BY hour DESC""",
            (f"-{hours}",),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_error_patterns():
    """Error patterns across tools and sessions."""
    conn = _get_db_conn()
    try:
        rows = conn.execute(
            """SELECT tc.tool, tc.server_name,
                      COUNT(*) as error_count,
                      COUNT(DISTINCT tc.session_id) as sessions_affected,
                      GROUP_CONCAT(DISTINCT substr(tc.result, 1, 120)) as sample_errors
               FROM tool_calls tc
               WHERE tc.result LIKE '%error%' OR tc.result LIKE '%fail%'
                  OR tc.result LIKE '%exception%' OR tc.result LIKE '%traceback%'
               GROUP BY tc.tool, tc.server_name
               ORDER BY error_count DESC
               LIMIT 50"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_memory_stats():
    """Memory platform health."""
    conn = _get_db_conn()
    try:
        skills_count = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
        knowledge_count = conn.execute("SELECT COUNT(*) FROM knowledge").fetchone()[0]
        summaries_count = conn.execute(
            "SELECT COUNT(*) FROM session_summaries"
        ).fetchone()[0]
        summary_coverage = conn.execute(
            """SELECT ROUND(100.0 * (SELECT COUNT(*) FROM session_summaries) /
                      MAX((SELECT COUNT(*) FROM sessions), 1), 1)"""
        ).fetchone()[0]
        return {
            "skills_count": skills_count,
            "knowledge_count": knowledge_count,
            "summaries_count": summaries_count,
            "summary_coverage_pct": summary_coverage,
        }
    finally:
        conn.close()


def query_session_errors(limit: int = 20):
    """Recent sessions with tool errors."""
    conn = _get_db_conn()
    try:
        rows = conn.execute(
            """SELECT s.id, s.ide, s.project, s.feature, s.created_at,
                      COUNT(tc.id) as error_count,
                      GROUP_CONCAT(DISTINCT tc.tool) as failing_tools
               FROM sessions s
               JOIN tool_calls tc ON s.id = tc.session_id
               WHERE tc.result LIKE '%error%' OR tc.result LIKE '%fail%'
                  OR tc.result LIKE '%exception%'
               GROUP BY s.id
               ORDER BY s.created_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Evolution page queries (Spec §11)
# ---------------------------------------------------------------------------




# ═══════════════════════════════════════════════════════
# Restored original queries (required by dashboard.js)
# ═══════════════════════════════════════════════════════

def query_daily_sessions(days: int = 14):
    conn = _get_db_conn()
    try:
        rows = conn.execute(
            """SELECT substr(created_at, 1, 10) as day, COUNT(*) as c, s.ide
               FROM sessions s WHERE created_at IS NOT NULL
               GROUP BY day ORDER BY day DESC LIMIT ?""",
            (days,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_session_messages(session_id: str):
    conn = _get_db_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY seq", (session_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_skill_detail(name: str = None, days: int = 1):
    conn = _get_db_conn()
    try:
        params = []
        sql = """SELECT tc.tool as skill_name, tc.session_id, s.project, s.created_at,
                        tc.duration_ms, tc.args, tc.result
                 FROM tool_calls tc JOIN sessions s ON tc.session_id = s.id
                 WHERE tc.tool = 'Skill'"""
        if name:
            sql += " AND tc.tool = ?"
            params.append(name)
        sql += " ORDER BY s.created_at DESC LIMIT 500"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_skill_timeline(name: str, days: int = 1):
    conn = _get_db_conn()
    try:
        rows = conn.execute(
            """SELECT tc.session_id, s.created_at, tc.duration_ms
               FROM tool_calls tc JOIN sessions s ON tc.session_id = s.id
               WHERE tc.tool = ? ORDER BY s.created_at DESC LIMIT 200""",
            (name,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_tool_detail(tool: str = None):
    conn = _get_db_conn()
    try:
        params = []
        sql = """SELECT tool, tool_type, server_name, COUNT(*) as calls,
                        ROUND(AVG(duration_ms), 1) as avg_ms, MAX(duration_ms) as max_ms,
                        COUNT(DISTINCT session_id) as sessions
                 FROM tool_calls"""
        if tool:
            sql += " WHERE tool = ?"
            params.append(tool)
        sql += " GROUP BY tool, tool_type ORDER BY calls DESC LIMIT 50"
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_tool_sessions(tool: str, limit: int = 50):
    conn = _get_db_conn()
    try:
        rows = conn.execute(
            """SELECT tc.session_id, s.project, s.created_at, COUNT(*) as invocations
               FROM tool_calls tc JOIN sessions s ON tc.session_id = s.id
               WHERE tc.tool = ? GROUP BY tc.session_id
               ORDER BY s.created_at DESC LIMIT ?""",
            (tool, limit),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_file_detail(file_path: str = None, project: str = None, limit: int = 200):
    conn = _get_db_conn()
    try:
        params = []
        sql = "SELECT * FROM file_ops WHERE 1=1"
        if file_path:
            sql += " AND path = ?"
            params.append(file_path)
        if project:
            sql += " AND project = ?"
            params.append(project)
        sql += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_knowledge_sessions(knowledge_id: int):
    conn = _get_db_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM knowledge_sessions WHERE knowledge_id = ?", (knowledge_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# Normalize cwd to a project name (GitHub repo level):
#   ~/project/<repo>/... → <repo>
#   ~/                   → home
#   otherwise the last path component
# Shared by the project aggregate and its per-IDE breakdown so the two cannot
# drift apart; the join below aliases this subquery as ss2.
_CWD_PROJECT_SQL = """
        SELECT id,
          CASE
            WHEN cwd GLOB '*/project/*' THEN
              REPLACE(SUBSTR(cwd, INSTR(cwd, '/project/') + 9), '/', '')
            WHEN cwd LIKE '/home/%' AND LENGTH(cwd) - LENGTH(REPLACE(cwd,'/','')) <= 2 THEN
              'home'
            ELSE REPLACE(TRIM(cwd,'/'), '/', '-')
          END as cwd_proj
        FROM sessions
"""


def query_projects():
    """Original project query format — used by original dashboard.js loadProjects()."""
    conn = _get_db_conn()
    try:
        rows = conn.execute(
            f"""SELECT COALESCE(NULLIF(s.project,''), COALESCE(ss2.cwd_proj,'root')) as project_name,
                      COUNT(*) as session_count,
                      SUM(ss.message_count) as total_messages,
                      SUM(ss.tool_count) as total_tools,
                      SUM(COALESCE(ss.tokens_input,0)) as total_tokens_in,
                      SUM(COALESCE(ss.tokens_output,0)) as total_tokens_out,
                      MAX(s.created_at) as last_session,
                      GROUP_CONCAT(DISTINCT s.ide) as ide_list
               FROM sessions s
               LEFT JOIN session_stats ss ON s.id = ss.session_id
               LEFT JOIN ({_CWD_PROJECT_SQL}) ss2 ON s.id = ss2.id
               GROUP BY project_name
               ORDER BY session_count DESC"""
        ).fetchall()

        # Per-IDE counts, keyed by (project, ide). ide_list above records only
        # *which* IDEs appear for a project, never how many sessions each has, so
        # the breakdown cannot be derived from it.
        ide_counts: dict[tuple[str, str], int] = {}
        for r in conn.execute(
            f"""SELECT COALESCE(NULLIF(s.project,''), COALESCE(ss2.cwd_proj,'root')) as project_name,
                       s.ide as ide,
                       COUNT(*) as n
                FROM sessions s
                LEFT JOIN ({_CWD_PROJECT_SQL}) ss2 ON s.id = ss2.id
                GROUP BY project_name, ide"""
        ).fetchall():
            ide_counts[(r["project_name"], r["ide"])] = r["n"]

        result = []
        for r in rows:
            d = dict(r)
            d["ides"] = {
                ide: n
                for (proj, ide), n in ide_counts.items()
                if proj == d["project_name"] and ide
            }
            result.append(d)
        return result
    finally:
        conn.close()
