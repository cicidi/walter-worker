import json
import tempfile
from pathlib import Path
from src.coworker.analytics.db import init_db
from src.coworker.analytics.import_data import import_session
from tests.analytics.test_data import generate_test_dataset


def test_full_pipeline():
    tmp = Path(tempfile.mkdtemp())
    db_path = tmp / "analytics.db"

    from src.coworker.analytics.db import init_db
    conn = init_db(db_path)

    generate_test_dataset(str(db_path), num_sessions=5)

    tables = ["sessions", "messages", "tool_calls", "file_ops", "skills", "session_stats"]
    for table in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        assert count > 0, f"Table {table} is empty"

    session_count = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    assert session_count == 5

    msg_counts = conn.execute(
        "SELECT session_id, COUNT(*) FROM messages GROUP BY session_id"
    ).fetchall()
    for row in msg_counts:
        assert row[1] >= 1

    tcs = conn.execute("SELECT tool, args, result FROM tool_calls LIMIT 5").fetchall()
    assert len(tcs) > 0
    assert tcs[0]["tool"]

    fos = conn.execute("SELECT op, path FROM file_ops").fetchall()
    for fo in fos:
        assert fo["op"] in ("read", "write", "edit", "glob")

    conn.close()


def test_dashboard_api():
    tmp = Path(tempfile.mkdtemp())
    db_path = tmp / "analytics.db"

    from src.coworker.analytics.db import init_db
    init_db(db_path)

    generate_test_dataset(str(db_path), num_sessions=5)

    import os
    os.environ["COWORKER_ANALYTICS_DB"] = str(db_path)

    try:
        import importlib
        import src.coworker.analytics.db as db_mod
        import src.coworker.dashboard.queries as q_mod
        import src.coworker.dashboard.app as app_mod
        importlib.reload(db_mod)
        importlib.reload(q_mod)
        importlib.reload(app_mod)

        from src.coworker.dashboard.app import app
        from fastapi.testclient import TestClient
        client = TestClient(app)

        endpoints = [
            "/api/overview", "/api/sessions", "/api/skills",
            "/api/tools", "/api/files", "/api/knowledge", "/api/features",
        ]
        for ep in endpoints:
            r = client.get(ep)
            assert r.status_code == 200, f"{ep} returned {r.status_code}"
            data = r.json()
            assert isinstance(data, (list, dict)), f"{ep} should return list or dict"

        r = client.get("/api/sessions?limit=1")
        sessions = r.json()
        if sessions:
            sid = sessions[0]["id"]
            r = client.get(f"/api/sessions/{sid}")
            assert r.status_code == 200
            detail = r.json()
            assert "session" in detail
            assert "messages" in detail
            assert "tool_calls" in detail
    finally:
        os.environ.pop("COWORKER_ANALYTICS_DB", None)


def test_db_idempotent():
    tmp = Path(tempfile.mkdtemp())
    db_path = tmp / "analytics.db"

    from src.coworker.analytics.db import init_db
    conn1 = init_db(db_path)
    conn1.close()

    conn2 = init_db(db_path)
    count = conn2.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    assert count >= 8
    conn2.close()
