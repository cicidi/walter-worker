from __future__ import annotations
from ..analytics.db import get_db


def query_sessions(limit: int = 50):
    conn = get_db()
    rows = conn.execute(
        """SELECT s.*, ss.message_count, ss.tool_count, ss.skill_count, ss.bash_count,
                  ss.read_count, ss.write_count, ss.duration_min
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
    rows = conn.execute("""
        SELECT k.*, COUNT(ks.session_id) as session_count
        FROM knowledge k
        LEFT JOIN knowledge_sessions ks ON k.id = ks.knowledge_id
        GROUP BY k.id
        ORDER BY session_count DESC, k.generated_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_knowledge_sessions(knowledge_id: int):
    """Sessions that validated a knowledge entry."""
    conn = get_db()
    rows = conn.execute("""
        SELECT ks.session_id, ks.generated_at as validated_at,
               s.ide, s.project, s.initiative, s.created_at
        FROM knowledge_sessions ks
        JOIN sessions s ON ks.session_id = s.id
        WHERE ks.knowledge_id = ?
        ORDER BY ks.generated_at DESC
    """, (knowledge_id,)).fetchall()
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
        """SELECT s.*, ss.message_count, ss.tool_count, ss.skill_count, ss.bash_count,
                  ss.read_count, ss.write_count, ss.duration_min,
                  ss.tokens_input, ss.tokens_output, ss.cost, ss.turn_count
           FROM sessions s
           LEFT JOIN session_stats ss ON s.id = ss.session_id
           ORDER BY s.created_at DESC LIMIT 10"""
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


def query_daily_sessions(days: int = 14):
    """Daily session counts for the last N days."""
    conn = get_db()
    rows = conn.execute(
        """SELECT substr(created_at, 1, 10) as day, COUNT(*) as c
           FROM sessions
           WHERE created_at >= date('now', ? || ' days')
           GROUP BY day ORDER BY day ASC""",
        (f"-{days}",),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_tool_sessions(tool: str, limit: int = 50):
    """Sessions that used a specific tool."""
    conn = get_db()
    rows = conn.execute(
        """SELECT DISTINCT s.id, s.ide, s.project, s.initiative, s.created_at,
                  COUNT(tc.id) as call_count
           FROM sessions s
           JOIN tool_calls tc ON s.id = tc.session_id
           WHERE tc.tool = ?
           GROUP BY s.id
           ORDER BY s.created_at DESC
           LIMIT ?""",
        (tool, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_projects():
    """Aggregated project data with worktree merging."""
    conn = get_db()
    rows = conn.execute("""
        SELECT
            CASE
                WHEN s.project IS NULL OR s.project = '' THEN 'root'
                WHEN s.project LIKE '-home-%%' THEN s.project
                ELSE s.project
            END as project_name,
            COALESCE(s.ide, 'unknown') as ide,
            COUNT(DISTINCT s.id) as session_count,
            COUNT(DISTINCT s.initiative) FILTER (WHERE s.initiative IS NOT NULL AND s.initiative != '') as initiative_count,
            SUM(ss.tool_count) as total_tools,
            SUM(ss.message_count) as total_messages,
            SUM(ss.tokens_input) as total_tokens_in,
            SUM(ss.tokens_output) as total_tokens_out,
            MAX(s.created_at) as last_session
        FROM sessions s
        LEFT JOIN session_stats ss ON s.id = ss.session_id
        GROUP BY project_name, ide
        ORDER BY session_count DESC
    """).fetchall()

    # Deduplicate: merge worktree projects into their origin (Python-side)
    proj_map = {}
    for r in rows:
        d = dict(r)
        ide = d.pop("ide") or "unknown"
        name = d["project_name"]
        # Simplify path-like names
        if name and "/" in name:
            parts = name.strip("/").split("/")
            name = parts[-1] if parts else name
        # Normalize -home-cicidi-project-X patterns to just X
        if name and name.startswith("-home-"):
            # Split by dash and find meaningful tail
            parts = name.split("-")
            idx = -1
            for pi, p in enumerate(parts):
                if p == "project" and pi + 1 < len(parts):
                    idx = pi
                    break
            if idx >= 0:
                name = "-".join(parts[idx+1:])
            else:
                name = parts[-1] if len(parts) > 2 else name
        d["project_name"] = name
        if name in proj_map:
            existing = proj_map[name]
            existing["session_count"] += d["session_count"]
            existing["initiative_count"] += d["initiative_count"]
            existing["total_tools"] = (existing["total_tools"] or 0) + (d["total_tools"] or 0)
            existing["total_messages"] = (existing["total_messages"] or 0) + (d["total_messages"] or 0)
            existing["total_tokens_in"] = (existing["total_tokens_in"] or 0) + (d["total_tokens_in"] or 0)
            existing["total_tokens_out"] = (existing["total_tokens_out"] or 0) + (d["total_tokens_out"] or 0)
            existing["ides"][ide] = existing["ides"].get(ide, 0) + d["session_count"]
            if d["last_session"] and (not existing["last_session"] or d["last_session"] > existing["last_session"]):
                existing["last_session"] = d["last_session"]
        else:
            d["ides"] = {ide: d["session_count"]}
            proj_map[name] = d

    result = sorted(proj_map.values(), key=lambda x: x["session_count"], reverse=True)
    conn.close()
    return result


def query_model_usage():
    """Model usage stats with token/cost aggregation."""
    conn = get_db()
    rows = conn.execute("""
        SELECT
            CASE
                WHEN s.model LIKE '%deepseek%' THEN 'deepseek'
                WHEN s.model LIKE '%claude%' THEN 'claude'
                WHEN s.model LIKE '%glm%' THEN 'glm'
                WHEN s.model LIKE '%minimax%' THEN 'minimax'
                WHEN s.model = '' OR s.model IS NULL THEN 'unknown'
                ELSE 'other'
            END as model_group,
            COUNT(DISTINCT s.id) as session_count,
            COUNT(DISTINCT tc.id) as request_count,
            AVG(tc.duration_ms) as avg_duration_ms,
            MAX(tc.duration_ms) as max_duration_ms,
            SUM(ss.tokens_input) as total_tokens_in,
            SUM(ss.tokens_output) as total_tokens_out,
            SUM(ss.tokens_reasoning) as total_tokens_reasoning,
            SUM(ss.tokens_cache_read) as total_tokens_cache_read,
            SUM(ss.tokens_cache_write) as total_tokens_cache_write,
            SUM(ss.cost) as total_cost,
            AVG(ss.tokens_input + ss.tokens_output) as avg_tokens_per_session
        FROM sessions s
        LEFT JOIN tool_calls tc ON s.id = tc.session_id
        LEFT JOIN session_stats ss ON s.id = ss.session_id
        GROUP BY model_group
        ORDER BY session_count DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_session_messages(session_id: str):
    """All messages for a session, ordered by seq."""
    conn = get_db()
    rows = conn.execute(
        """SELECT seq, type, content, ts FROM messages
           WHERE session_id = ? ORDER BY seq DESC""",
        (session_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def find_skill_session_ids(name: str):
    """Find session IDs where a skill was used, from both tool_calls and file_ops."""
    conn = get_db()
    rows = conn.execute("""
        SELECT DISTINCT tc.session_id FROM tool_calls tc
        WHERE json_extract(tc.args, '$.name') = ? AND LOWER(tc.tool) = 'skill'
        UNION
        SELECT DISTINCT fo.session_id FROM file_ops fo
        WHERE fo.skill_name = ?
    """, (name, name)).fetchall()
    conn.close()
    return [r["session_id"] for r in rows]


def find_skill_mentions(name: str):
    """Find sessions that mention a skill name ANYWHERE in tool_calls (args or result).
    Best-effort recovery for legacy skills whose original JSONL data is lost."""
    conn = get_db()
    rows = conn.execute("""
        SELECT DISTINCT tc.session_id
        FROM tool_calls tc
        WHERE (tc.args LIKE '%' || ? || '%' OR tc.result LIKE '%' || ? || '%')
        UNION
        SELECT DISTINCT fo.session_id
        FROM file_ops fo
        WHERE fo.skill_name = ?
    """, (name, name, name)).fetchall()
    conn.close()
    # Return session_ids with a "mentioned" flag
    return [r["session_id"] for r in rows]


def query_skill_detail(name: str = None, days: int = 1):
    """Skill usage timeline with session/project context.
    Skill name is stored in tc.args as JSON {"name": "skill-name"} when tc.tool = 'Skill'.
    """
    conn = get_db()
    where = ""
    params = []
    if name:
        where = "WHERE json_extract(tc.args, '$.name') = ? AND LOWER(tc.tool) = 'skill'"
        params.append(name)
    else:
        where = "WHERE LOWER(tc.tool) = 'skill' AND tc.args IS NOT NULL"
    rows = conn.execute(f"""
        SELECT json_extract(tc.args, '$.name') as skill_name,
               tc.ts, tc.session_id, tc.duration_ms, tc.parent_skill,
               tc.args, tc.tool_type,
               s.project, s.initiative, s.ide, s.created_at as session_created
        FROM tool_calls tc
        JOIN sessions s ON tc.session_id = s.id
        {where}
        ORDER BY tc.ts DESC
        LIMIT 200
    """, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_skill_timeline(name: str, days: int = 1):
    """Skill calls grouped by time. Skill name from args JSON."""
    conn = get_db()
    rows = conn.execute("""
        SELECT json_extract(tc.args, '$.name') as name,
               tc.ts, tc.session_id, tc.duration_ms, tc.parent_skill,
               s.project, s.initiative, s.ide
        FROM tool_calls tc
        JOIN sessions s ON tc.session_id = s.id
        WHERE json_extract(tc.args, '$.name') = ? AND LOWER(tc.tool) = 'skill'
        ORDER BY tc.ts DESC
        LIMIT 100
    """, (name,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_tool_detail(tool: str = None):
    """Detailed tool usage with session context."""
    conn = get_db()
    where = ""
    params = []
    if tool:
        where = "WHERE tc.tool = ?"
        params.append(tool)
    rows = conn.execute(f"""
        SELECT tc.*, s.project, s.initiative, s.ide, s.created_at as session_created
        FROM tool_calls tc
        JOIN sessions s ON tc.session_id = s.id
        {where}
        ORDER BY tc.ts DESC
        LIMIT 200
    """, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_file_detail(file_path: str = None, project: str = None,
                       file_type: str = None, initiative: str = None,
                       limit: int = 200):
    """File operations with filtering and detail."""
    conn = get_db()
    conditions = []
    params = []
    if file_path:
        conditions.append("fo.path LIKE ?")
        params.append(f"%{file_path}%")
    if project:
        conditions.append("s.project LIKE ?")
        params.append(f"%{project}%")
    if file_type:
        conditions.append("fo.file_type = ?")
        params.append(file_type)
    if initiative:
        conditions.append("s.initiative LIKE ?")
        params.append(f"%{initiative}%")

    where = " AND ".join(conditions) if conditions else "1=1"
    rows = conn.execute(f"""
        SELECT fo.id, fo.session_id, fo.call_id, fo.op, fo.path, fo.file_type, fo.skill_name, fo.seq, fo.ts,
               COALESCE(NULLIF(s.project, ''), NULLIF(fo.project, ''),
                 CASE
                   WHEN fo.path LIKE '%%/project/%%' THEN
                     SUBSTR(fo.path, INSTR(fo.path, '/project/') + 9,
                       INSTR(SUBSTR(fo.path, INSTR(fo.path, '/project/') + 9), '/') - 1)
                   WHEN fo.path LIKE '%%/ai-coworker%%' THEN 'ai-coworker'
                   WHEN fo.path LIKE '%%/opencode%%' THEN 'opencode'
                   WHEN fo.path LIKE '%%/skill-factory%%' THEN 'skill-factory'
                   WHEN fo.path LIKE '%%/dotfiles%%' THEN 'dotfiles'
                   ELSE ''
                 END) as project,
               s.initiative, s.ide, s.branch, s.created_at as session_created
        FROM file_ops fo
        JOIN sessions s ON fo.session_id = s.id
        WHERE {where}
        ORDER BY fo.ts DESC
        LIMIT ?
    """, params + [limit]).fetchall()
    conn.close()
    return [dict(r) for r in rows]


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
           WHERE LOWER(tc.tool) = 'skill'
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
