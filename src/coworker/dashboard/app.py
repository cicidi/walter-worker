import json
import logging
from importlib.resources import files as resource_files

from fastapi import FastAPI, WebSocket
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
