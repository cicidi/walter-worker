import json
import logging
from importlib.resources import files as resource_files

from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from . import queries

logger = logging.getLogger(__name__)

app = FastAPI(title="Coworker Analytics Dashboard")


@app.get("/api/overview")
def api_overview():
    return queries.query_overview()


@app.get("/api/sessions")
def api_sessions(limit: int = 50):
    return queries.query_sessions(limit)


@app.get("/api/sessions/{session_id}")
def api_session_detail(session_id: str):
    return queries.query_session_detail(session_id)


@app.get("/api/skills")
def api_skills():
    return queries.query_skills()


@app.get("/api/tools")
def api_tools():
    return queries.query_tools()


@app.get("/api/files")
def api_files(project: str = None, file_type: str = None):
    return queries.query_files(project, file_type)


@app.get("/api/knowledge")
def api_knowledge():
    return queries.query_knowledge()


@app.get("/api/initiatives")
def api_initiatives():
    return queries.query_initiatives()


@app.get("/api/sessions/{session_id}/timeline")
def api_session_timeline(session_id: str):
    return queries.query_session_timeline(session_id)


@app.get("/api/skill-sessions")
def api_skill_sessions():
    return queries.query_skill_sessions()


@app.get("/api/top-files")
def api_top_files(limit: int = 50):
    return queries.query_top_files(limit)


@app.get("/api/file-stats")
def api_file_stats():
    return queries.query_file_stats()


# ---------------------------------------------------------------------------
# Evolution page endpoints (Spec §11.1)
# ---------------------------------------------------------------------------


@app.get("/api/evolution/overview")
def api_evolution_overview():
    return queries.query_evolution_overview()


@app.get("/api/evolution/skills")
def api_evolution_skills(auto_train: bool = True, project: str = "", status: str = "active"):
    return queries.query_evolution_skills(auto_train=auto_train, project=project, status=status)


@app.get("/api/evolution/skills/{name}")
def api_evolution_skill_detail(name: str):
    skills = queries.query_evolution_skills(auto_train=False, status="all")
    for s in skills:
        if s["name"] == name:
            return s
    raise HTTPException(status_code=404, detail=f"Skill '{name}' not found")


@app.get("/api/evolution/experiences")
def api_evolution_experiences(auto_train: bool = True, project: str = "", status: str = "active"):
    return queries.query_evolution_experiences(auto_train=auto_train, project=project, status=status)


@app.get("/api/evolution/experiences/{exp_id}")
def api_evolution_experience_detail(exp_id: str):
    try:
        from coworker.memory.mem0_client import Mem0Client
        mem0 = Mem0Client.from_config()
        entry = mem0.get(exp_id)
        return {"id": exp_id, "memory": entry.get("memory", ""), "metadata": entry.get("metadata", {})}
    except Exception:
        raise HTTPException(status_code=404, detail=f"Experience '{exp_id}' not found")


@app.get("/api/evolution/pending")
def api_evolution_pending():
    return queries.query_evolution_pending()


@app.post("/api/evolution/approve/{item_id}")
def api_evolution_approve(item_id: str):
    from coworker.memory.pending import approve
    ok = approve(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Pending item '{item_id}' not found")
    return {"status": "approved", "id": item_id}


@app.post("/api/evolution/reject/{item_id}")
def api_evolution_reject(item_id: str):
    from coworker.memory.pending import reject
    ok = reject(item_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Pending item '{item_id}' not found")
    return {"status": "rejected", "id": item_id}


# ---------------------------------------------------------------------------
# Enhanced monitoring endpoints
# ---------------------------------------------------------------------------


@app.get("/api/projects")
def api_projects():
    """Project comparison — side-by-side metrics."""
    return queries.query_project_comparison()


@app.get("/api/hotspots")
def api_hotspots(limit: int = 30):
    """Most frequently modified files with churn metrics."""
    return queries.query_file_hotspots(limit)


@app.get("/api/activity")
def api_activity(hours: int = 24):
    """Hourly activity breakdown."""
    return queries.query_activity_timeline(hours)


@app.get("/api/errors")
def api_errors():
    """Error patterns across tools and sessions."""
    return queries.query_error_patterns()


@app.get("/api/memory-stats")
def api_memory_stats():
    """Memory platform health."""
    return queries.query_memory_stats()


@app.post("/api/memory/refresh-snapshot")
def api_memory_refresh():
    """Trigger CLAUDE.local.md snapshot refresh."""
    from coworker.memory.inject import build_snapshot, inject_into_local_md
    from coworker.memory.mem0_client import Mem0Client
    try:
        mem0 = Mem0Client.from_config()
        import os
        local_md = os.path.expanduser("~/CLAUDE.local.md")
        snapshot = build_snapshot(mem0)
        inject_into_local_md(str(local_md), snapshot)
        return {"status": "refreshed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/reset-circuit")
def api_memory_reset_circuit():
    """Reset the circuit breaker."""
    from coworker.memory.safety import reset_circuit_breaker
    reset_circuit_breaker()
    return {"status": "reset"}


@app.get("/api/session-errors")
def api_session_errors(limit: int = 20):
    """Sessions with the most errors."""
    return queries.query_session_errors(limit)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.receive_text()
            overview = queries.query_overview()
            await websocket.send_text(json.dumps(overview, default=str))
    except Exception:
        logger.exception("WebSocket error")


static_dir = resource_files("coworker.dashboard") / "static"
if static_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
