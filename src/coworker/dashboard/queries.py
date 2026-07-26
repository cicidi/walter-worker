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


# ---------------------------------------------------------------------------
# Evolution page queries (Spec §11)
# ---------------------------------------------------------------------------


def _get_db_conn():
    """Return a fresh database connection (caller must close)."""
    return get_db()


def _list_skills(provenance=None):
    """List skills from ~/.coworker/skills/ directory."""
    import json
    from pathlib import Path
    skills_dir = Path.home() / ".coworker" / "skills"
    if not skills_dir.exists():
        return []
    result = []
    for d in skills_dir.iterdir():
        if not d.is_dir():
            continue
        usage_path = d / "usage.json"
        meta = {}
        if usage_path.exists():
            try:
                meta = json.loads(usage_path.read_text())
            except Exception:
                pass
        if provenance and meta.get("provenance") != provenance:
            continue
        meta["name"] = d.name
        result.append(meta)
    return result


def _count_agent_experiences(mem0_client=None):
    """Count mem0 entries with agent provenance."""
    try:
        from coworker.memory.mem0_client import Mem0Client
        if mem0_client is None:
            mem0_client = Mem0Client.from_config()
        results = mem0_client.search(query=".", filters={"provenance": "agent"}, top_k=1000)
        return len(results)
    except Exception:
        return 0


def _count_pending():
    """Count pending skill review items."""
    from pathlib import Path
    p = Path.home() / ".coworker" / "pending" / "skills"
    if not p.exists():
        return 0
    return len(list(p.glob("*.json")))


def _compute_evolution_score(skills, sessions_with_auto, total_sessions):
    """Compute an evolution score 0-100."""
    reuse = sessions_with_auto / max(total_sessions, 1)
    active_skills = sum(1 for s in skills if s.get("state") == "active")
    return min(100, int(reuse * 40 + active_skills * 5 + 30))


def query_evolution_overview():
    """Stat cards for the Evolution page."""
    conn = _get_db_conn()
    try:
        skills = _list_skills(provenance="agent")
        total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
        sessions_with_auto = conn.execute(
            "SELECT COUNT(DISTINCT session_id) FROM tool_calls WHERE LOWER(tool) = 'skill'"
        ).fetchone()[0]
    finally:
        conn.close()

    return {
        "auto_trained_skills": len(skills),
        "auto_trained_experiences": _count_agent_experiences(),
        "pending_review": _count_pending(),
        "skill_reuse_rate": round(sessions_with_auto / max(total_sessions, 1), 2),
        "evolution_score": _compute_evolution_score(skills, sessions_with_auto, total_sessions),
    }


def query_evolution_skills(auto_train: bool = True, project: str = "", status: str = "active"):
    """Skill list for the Evolution page."""
    conn = _get_db_conn()
    try:
        all_skills = _list_skills()
        total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]

        results = []
        for skill in all_skills:
            if auto_train and skill.get("provenance") != "agent":
                continue
            if status != "all" and skill.get("state", "active") != status:
                continue

            rows = conn.execute(
                "SELECT DISTINCT session_id, ts FROM tool_calls WHERE LOWER(tool) = 'skill' AND args LIKE ? ORDER BY ts",
                (f"%{skill['name']}%",),
            ).fetchall()

            results.append({
                "name": skill["name"],
                "provenance": skill.get("provenance", "manual"),
                "state": skill.get("state", "active"),
                "created_at": skill.get("created_at", ""),
                "total_calls": skill.get("total_calls", 0),
                "sessions_invoked": len(rows),
                "last_used": skill.get("last_used", ""),
                "reuse_rate": round(len(rows) / max(total_sessions, 1), 2),
                "session_ids": [r[0] for r in rows],
            })
        return results
    finally:
        conn.close()


def query_evolution_experiences(auto_train: bool = True, project: str = "", status: str = "active"):
    """Experience list for the Evolution page (reads from mem0)."""
    try:
        from coworker.memory.mem0_client import Mem0Client
        mem0 = Mem0Client.from_config()
    except Exception:
        return []

    filters: dict = {}
    if project:
        filters["project"] = project
    if auto_train:
        filters["provenance"] = "agent"
    if status != "all":
        filters["state"] = status

    try:
        raw = mem0.search(query=".", filters=filters, top_k=200)
    except Exception:
        return []

    return [
        {
            "id": r.get("id", ""),
            "memory": r.get("memory", ""),
            "provenance": r.get("metadata", {}).get("provenance", "manual"),
            "topic": r.get("metadata", {}).get("topic", ""),
            "project": r.get("metadata", {}).get("project", ""),
            "source_session": r.get("metadata", {}).get("source_session", ""),
            "use_count": r.get("metadata", {}).get("use_count", 0),
            "last_used": r.get("metadata", {}).get("last_used", ""),
            "state": r.get("metadata", {}).get("state", "active"),
        }
        for r in raw
    ]


def query_evolution_pending():
    """Pending review queue items."""
    try:
        from coworker.memory.pending import list_pending
        return list_pending()
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Enhanced dashboard queries — project comparison, error tracking, activity
# ---------------------------------------------------------------------------


def query_project_comparison():
    """Side-by-side project metrics for comparison view."""
    conn = _get_db_conn()
    try:
        rows = conn.execute(
            """SELECT s.project,
                      COUNT(DISTINCT s.id) as sessions,
                      COALESCE(SUM(ss.message_count),0) as messages,
                      COALESCE(SUM(ss.tool_count),0) as tool_calls,
                      COALESCE(SUM(ss.skill_count),0) as skills_used,
                      COALESCE(ROUND(AVG(ss.duration_min),1),0) as avg_duration_min,
                      MAX(s.created_at) as last_active
               FROM sessions s
               LEFT JOIN session_stats ss ON s.id = ss.session_id
               WHERE s.project IS NOT NULL AND s.project != ''
               GROUP BY s.project
               ORDER BY sessions DESC"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_file_hotspots(limit: int = 30):
    """Most frequently modified files with churn metrics."""
    conn = _get_db_conn()
    try:
        rows = conn.execute(
            """SELECT path as file_path,
                      COUNT(*) as total_ops,
                      SUM(CASE WHEN op = 'read' THEN 1 ELSE 0 END) as reads,
                      SUM(CASE WHEN op IN ('write','edit') THEN 1 ELSE 0 END) as writes,
                      SUM(CASE WHEN op = 'delete' THEN 1 ELSE 0 END) as deletes,
                      COUNT(DISTINCT session_id) as sessions_touched,
                      COUNT(DISTINCT s.project) as projects,
                      MAX(f.ts) as last_touched
               FROM file_ops f
               LEFT JOIN sessions s ON f.session_id = s.id
               GROUP BY path
               ORDER BY writes DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_activity_timeline(hours: int = 24):
    """Hourly activity breakdown for recent period."""
    conn = _get_db_conn()
    try:
        rows = conn.execute(
            """SELECT substr(COALESCE(m.ts, t.ts), 1, 13) as hour,
                      COUNT(DISTINCT m.id) as msgs,
                      COUNT(DISTINCT t.call_id) as tools
               FROM sessions s
               LEFT JOIN messages m ON s.id = m.session_id
               LEFT JOIN tool_calls t ON s.id = t.session_id
               WHERE s.created_at >= datetime('now', '-' || ? || ' hours')
               GROUP BY hour
               ORDER BY hour DESC
               LIMIT ?""",
            (hours, hours),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_error_patterns():
    """Extract error patterns from tool calls and messages."""
    conn = _get_db_conn()
    try:
        # Tool call errors — check args and result for error patterns
        tool_errors = conn.execute(
            """SELECT tool, COUNT(*) as error_count
               FROM tool_calls
               WHERE (args LIKE '%error%' OR args LIKE '%fail%'
                  OR args LIKE '%exception%' OR args LIKE '%traceback%'
                  OR result LIKE '%error%' OR result LIKE '%fail%'
                  OR result LIKE '%exception%' OR result LIKE '%traceback%')
               GROUP BY tool
               ORDER BY error_count DESC
               LIMIT 20"""
        ).fetchall()

        # File operation errors
        file_errors = conn.execute(
            """SELECT op, COUNT(*) as count
               FROM file_ops
               WHERE path LIKE '%error%' OR path LIKE '%fail%'
               GROUP BY op"""
        ).fetchall()

        return {
            "tool_errors": [dict(r) for r in tool_errors],
            "file_errors": [dict(r) for r in file_errors],
        }
    finally:
        conn.close()


def query_memory_stats():
    """Memory platform health statistics."""
    stats = {"mem0_entries": 0, "pending_review": 0, "circuit_breaker": {}}
    try:
        from coworker.memory.mem0_client import Mem0Client
        mem0 = Mem0Client.from_config()
        active = mem0.search(query=".", filters={"state": "active"}, top_k=1000)
        stats["mem0_entries"] = len(active)
        stale = mem0.search(query=".", filters={"state": "stale"}, top_k=1000)
        archived = mem0.search(query=".", filters={"state": "archived"}, top_k=1000)
        stats["mem0_stale"] = len(stale)
        stats["mem0_archived"] = len(archived)
        stats["mem0_by_type"] = {}
        for entry in active[:500]:
            t = entry.get("metadata", {}).get("type", "unknown")
            stats["mem0_by_type"][t] = stats["mem0_by_type"].get(t, 0) + 1
    except Exception:
        stats["mem0_error"] = "mem0 unavailable"

    try:
        from coworker.memory.safety import check_circuit_breaker
        stats["circuit_breaker"] = check_circuit_breaker()
    except Exception:
        pass

    try:
        from coworker.memory.pending import list_pending
        stats["pending_review"] = len(list_pending())
    except Exception:
        pass

    return stats


def query_session_errors(limit: int = 20):
    """Sessions with the most tool errors."""
    conn = _get_db_conn()
    try:
        rows = conn.execute(
            """SELECT s.id as session_id, s.project, s.created_at,
                      COUNT(t.call_id) as error_tools
               FROM sessions s
               JOIN tool_calls t ON s.id = t.session_id
               WHERE (t.args LIKE '%error%' OR t.args LIKE '%fail%'
                  OR t.args LIKE '%exception%'
                  OR t.result LIKE '%error%' OR t.result LIKE '%fail%'
                  OR t.result LIKE '%exception%')
               GROUP BY s.id
               ORDER BY error_tools DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Cost, Model, Efficiency, Data Quality
# ---------------------------------------------------------------------------


def query_cost_analytics():
    """Token consumption and cost per model, per day."""
    conn = _get_db_conn()
    try:
        model_stats = conn.execute(
            """SELECT s.model,
                      COUNT(DISTINCT s.id) as sessions,
                      COALESCE(SUM(ss.tokens_input),0) as total_input,
                      COALESCE(SUM(ss.tokens_output),0) as total_output,
                      COALESCE(SUM(ss.tokens_reasoning),0) as total_reasoning,
                      COALESCE(ROUND(SUM(ss.cost),4),0) as total_cost,
                      COALESCE(ROUND(AVG(ss.cost),4),0) as avg_cost_per_session
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
