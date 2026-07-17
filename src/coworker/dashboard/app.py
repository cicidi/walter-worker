import json
import logging
from importlib.resources import files as resource_files

from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles

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

@app.get("/api/knowledge/{knowledge_id}/sessions")
def api_knowledge_sessions(knowledge_id: int):
    return queries.query_knowledge_sessions(knowledge_id)


@app.get("/api/initiatives")
def api_initiatives():
    return queries.query_initiatives()


@app.get("/api/projects")
def api_projects():
    return queries.query_projects()


@app.get("/api/models")
def api_models():
    return queries.query_model_usage()


@app.get("/api/sessions/{session_id}/timeline")
def api_session_timeline(session_id: str):
    return queries.query_session_timeline(session_id)


@app.get("/api/sessions/{session_id}/messages")
def api_session_messages(session_id: str):
    return queries.query_session_messages(session_id)


@app.get("/api/skill-detail")
def api_skill_detail(name: str = None, days: int = 1):
    return queries.query_skill_detail(name, days)


@app.get("/api/skill-timeline")
def api_skill_timeline(name: str, days: int = 1):
    return queries.query_skill_timeline(name, days)


@app.get("/api/tool-detail")
def api_tool_detail(tool: str = None):
    return queries.query_tool_detail(tool)


@app.get("/api/file-detail")
def api_file_detail(file_path: str = None, project: str = None,
                     file_type: str = None, initiative: str = None,
                     limit: int = 200):
    return queries.query_file_detail(file_path, project, file_type, initiative, limit)


@app.get("/api/skill-sessions")
def api_skill_sessions():
    return queries.query_skill_sessions()

@app.get("/api/skill-session-ids")
def api_skill_session_ids(name: str):
    return queries.find_skill_session_ids(name)

@app.get("/api/skill-mentions")
def api_skill_mentions(name: str):
    return queries.find_skill_mentions(name)


@app.get("/api/daily-sessions")
def api_daily_sessions(days: int = 14):
    return queries.query_daily_sessions(days)


@app.get("/api/tool-sessions")
def api_tool_sessions(tool: str, limit: int = 50):
    return queries.query_tool_sessions(tool, limit)


@app.get("/api/top-files")
def api_top_files(limit: int = 50):
    return queries.query_top_files(limit)


@app.get("/api/file-stats")
def api_file_stats():
    return queries.query_file_stats()


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
