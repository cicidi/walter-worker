from __future__ import annotations
from ..analytics.db import get_db


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
            "SELECT COUNT(DISTINCT session_id) FROM tool_calls WHERE tool = 'Skill'"
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
                "SELECT DISTINCT session_id, ts FROM tool_calls WHERE tool = 'Skill' AND args LIKE ? ORDER BY ts",
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
