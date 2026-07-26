from __future__ import annotations
from ..analytics.db import get_db


def _get_db_conn():
    """Return a fresh database connection (caller must close)."""
    return get_db()


# ---------------------------------------------------------------------------


def query_cost_analytics():
    """Token consumption, cost, and cache efficiency per model, per day."""
    conn = _get_db_conn()
    try:
        model_stats = conn.execute(
            """SELECT s.model,
                      COUNT(DISTINCT s.id) as sessions,
                      COALESCE(SUM(ss.tokens_input),0) as total_input,
                      COALESCE(SUM(ss.tokens_output),0) as total_output,
                      COALESCE(SUM(ss.tokens_reasoning),0) as total_reasoning,
                      COALESCE(SUM(ss.tokens_cache_read),0) as total_cache_read,
                      COALESCE(SUM(ss.tokens_cache_write),0) as total_cache_write,
                      COALESCE(ROUND(SUM(ss.cost),4),0) as total_cost,
                      COALESCE(ROUND(AVG(ss.cost),4),0) as avg_cost_per_session,
                      CASE WHEN COALESCE(SUM(ss.tokens_input),0) > 0
                           THEN ROUND(COALESCE(SUM(ss.tokens_cache_read),0) * 100.0 /
                                (COALESCE(SUM(ss.tokens_input),0) + COALESCE(SUM(ss.tokens_cache_read),0) + 1), 1)
                           ELSE 0 END as cache_hit_rate_pct
               FROM sessions s
               LEFT JOIN session_stats ss ON s.id = ss.session_id
               WHERE ss.tokens_input > 0
               GROUP BY s.model
               ORDER BY total_cost DESC"""
        ).fetchall()
        daily = conn.execute(
            """SELECT substr(s.created_at,1,10) as day,
                      COALESCE(SUM(ss.tokens_input),0) as input_tokens,
                      COALESCE(SUM(ss.tokens_output),0) as output_tokens,
                      COUNT(DISTINCT s.id) as sessions
               FROM sessions s
               LEFT JOIN session_stats ss ON s.id = ss.session_id
               WHERE s.created_at IS NOT NULL
               GROUP BY day ORDER BY day DESC LIMIT 30"""
        ).fetchall()
        return {"model_stats": [dict(r) for r in model_stats], "daily_tokens": [dict(r) for r in daily]}
    finally:
        conn.close()


def query_model_usage():
    """Model and IDE distribution across sessions."""
    conn = _get_db_conn()
    try:
        ide_stats = conn.execute(
            """SELECT CASE WHEN ide LIKE '%claude%' THEN 'Claude Code' ELSE COALESCE(ide,'unknown') END as ide_name,
                      COUNT(*) as sessions, COUNT(DISTINCT project) as projects
               FROM sessions WHERE ide IS NOT NULL AND ide != ''
               GROUP BY ide_name ORDER BY sessions DESC"""
        ).fetchall()
        model_trend = conn.execute(
            """SELECT substr(created_at,1,10) as day, model, COUNT(*) as count
               FROM sessions WHERE model IS NOT NULL AND created_at IS NOT NULL
               GROUP BY day, model ORDER BY day DESC LIMIT 50"""
        ).fetchall()
        return {"ide_stats": [dict(r) for r in ide_stats], "model_trend": [dict(r) for r in model_trend]}
    finally:
        conn.close()


def query_efficiency_insights():
    """Efficiency metrics from session_summaries."""
    conn = _get_db_conn()
    try:
        summaries = conn.execute(
            """SELECT session_id, efficiency_score, think_action_ratio,
                      edit_redundancy, loop_count, user_wait_minutes,
                      bottlenecks, efficiency_tip, generated_at
               FROM session_summaries WHERE efficiency_score IS NOT NULL
               ORDER BY generated_at DESC"""
        ).fetchall()
        all_scores = [s[1] for s in summaries if s[1] is not None]
        avg_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
        bottlenecks = conn.execute(
            """SELECT bottlenecks, COUNT(*) as count
               FROM session_summaries WHERE bottlenecks IS NOT NULL AND bottlenecks != ''
               GROUP BY bottlenecks ORDER BY count DESC LIMIT 10"""
        ).fetchall()
        return {
            "total_summaries": len(summaries),
            "avg_efficiency": avg_score,
            "avg_think_action": round(sum(s[2] for s in summaries if s[2] is not None) / max(len(summaries), 1), 2),
            "avg_edit_redundancy": round(sum(s[3] for s in summaries if s[3] is not None) / max(len(summaries), 1), 1),
            "bottlenecks": [dict(r) for r in bottlenecks],
            "recent": [dict(r) for r in summaries[:10]],
        }
    finally:
        conn.close()


def query_data_quality():
    """Data quality metrics — NULL rates, coverage gaps."""
    conn = _get_db_conn()
    try:
        total = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        def pct(n): return round(n / max(total, 1) * 100, 1)
        with_project = conn.execute("SELECT COUNT(*) FROM sessions WHERE project IS NOT NULL AND project != ''").fetchone()[0]
        with_initiative = conn.execute("SELECT COUNT(*) FROM sessions WHERE initiative IS NOT NULL AND initiative != ''").fetchone()[0]
        with_closed = conn.execute("SELECT COUNT(*) FROM sessions WHERE closed_at IS NOT NULL AND closed_at != ''").fetchone()[0]
        with_tokens = conn.execute("""SELECT COUNT(DISTINCT s.id) FROM sessions s JOIN session_stats ss ON s.id = ss.session_id WHERE ss.tokens_input > 0""").fetchone()[0]
        with_summaries = conn.execute("SELECT COUNT(*) FROM session_summaries").fetchone()[0]
        return {
            "total_sessions": total,
            "project": {"covered": with_project, "missing": total - with_project, "pct": pct(with_project)},
            "initiative": {"covered": with_initiative, "missing": total - with_initiative, "pct": pct(with_initiative)},
            "closed": {"covered": with_closed, "missing": total - with_closed, "pct": pct(with_closed)},
            "tokens": {"covered": with_tokens, "missing": total - with_tokens, "pct": pct(with_tokens)},
            "summaries": {"covered": with_summaries, "missing": total - with_summaries, "pct": pct(with_summaries)},
        }
    finally:
        conn.close()


def query_models():
    """Model stats in format expected by original dashboard.js loadModels()."""
    conn = _get_db_conn()
    try:
        rows = conn.execute(
            """SELECT COALESCE(s.model,'unknown') as model_group,
                      COUNT(DISTINCT s.id) as session_count,
                      COUNT(DISTINCT tc.call_id) as request_count,
                      COALESCE(SUM(ss.tokens_input),0) as total_tokens_in,
                      COALESCE(SUM(ss.tokens_output),0) as total_tokens_out,
                      COALESCE(SUM(ss.tokens_reasoning),0) as total_tokens_reasoning,
                      COALESCE(SUM(ss.tokens_cache_read),0) as total_tokens_cache_read,
                      COALESCE(SUM(ss.tokens_cache_write),0) as total_tokens_cache_write,
                      COALESCE(ROUND(SUM(ss.cost),6),0) as total_cost,
                      COALESCE(ROUND(AVG(ss.duration_min*60000),0),0) as avg_duration_ms,
                      COALESCE(ROUND(MAX(ss.duration_min*60000),0),0) as max_duration_ms
               FROM sessions s
               LEFT JOIN session_stats ss ON s.id = ss.session_id
               LEFT JOIN tool_calls tc ON s.id = tc.session_id
               WHERE s.model IS NOT NULL
               GROUP BY s.model
               ORDER BY total_cost DESC"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


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


def query_projects():
    """Original project query format — used by original dashboard.js loadProjects()."""
    conn = _get_db_conn()
    try:
        rows = conn.execute(
            """SELECT COALESCE(NULLIF(s.project,''), COALESCE(ss2.cwd_proj,'root')) as project_name,
                      COUNT(*) as session_count,
                      SUM(ss.message_count) as total_messages,
                      SUM(ss.tool_count) as total_tools,
                      SUM(COALESCE(ss.tokens_input,0)) as total_tokens_in,
                      SUM(COALESCE(ss.tokens_output,0)) as total_tokens_out,
                      MAX(s.created_at) as last_session,
                      GROUP_CONCAT(DISTINCT s.ide) as ide_list
               FROM sessions s
               LEFT JOIN session_stats ss ON s.id = ss.session_id
               LEFT JOIN (SELECT id, TRIM(REPLACE(cwd,'/home/cicidi/project/',''),'/')||'/' as cwd_proj FROM sessions) ss2 ON s.id = ss2.id
               GROUP BY project_name
               ORDER BY session_count DESC"""
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            ides = {}
            if d.get('ide_list'):
                for ide in d['ide_list'].split(','):
                    ide = ide.strip()
                    if ide: ides[ide] = ides.get(ide, 0) + d['session_count']
            d['ides'] = ides
            result.append(d)
        return result
    finally:
        conn.close()
