from __future__ import annotations
from ..analytics.db import get_db


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


def query_initiatives():
    conn = get_db()
    rows = conn.execute(
        """SELECT s.initiative, s.project, COUNT(DISTINCT s.id) as session_count,
                  COUNT(DISTINCT t.call_id) as tool_count
           FROM sessions s LEFT JOIN tool_calls t ON s.id = t.session_id
           WHERE s.initiative IS NOT NULL AND s.initiative != ''
           GROUP BY s.initiative ORDER BY session_count DESC"""
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
