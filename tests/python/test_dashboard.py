"""Tests for the coworker.dashboard module: queries and FastAPI endpoints."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from coworker.analytics.db import SCHEMA
from coworker.dashboard import queries
from coworker.dashboard.app import app
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# DB fixtures
# ---------------------------------------------------------------------------

def _make_shared_conn():
    """Create a new connection to the shared in-memory database."""
    conn = sqlite3.connect("file:test_dashboard?mode=memory&cache=shared", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@pytest.fixture
def test_db(monkeypatch):
    """Create a shared in-memory DB, seed it, and patch get_db.

    Returns the anchor connection that keeps shared memory alive.
    """
    conn = _make_shared_conn()
    conn.executescript(SCHEMA)
    _seed_all(conn)
    conn.commit()

    monkeypatch.setattr(queries, "get_db", _make_shared_conn)

    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

def _seed_all(conn: sqlite3.Connection) -> None:
    """Populate every table with representative test data."""
    _seed_sessions(conn)
    _seed_messages(conn)
    _seed_tool_calls(conn)
    _seed_file_ops(conn)
    _seed_session_stats(conn)
    _seed_skills(conn)
    _seed_knowledge(conn)
    _seed_session_summaries(conn)


def _seed_sessions(conn: sqlite3.Connection) -> None:
    rows = [
        ("s1", "claude", "test-project", "/tmp/proj", "claude-3", "my-initiative",
         "feat/test", "2025-01-01T10:00:00", "2025-01-01T10:30:00"),
        ("s2", "opencode", "other-project", "/tmp/other", "gpt-4", None,
         "fix/bug", "2025-01-02T12:00:00", None),
        ("s3", "claude", "test-project", "/tmp/proj", "claude-3", "my-initiative",
         "feat/test2", "2025-01-03T08:00:00", "2025-01-03T09:00:00"),
    ]
    conn.executemany(
        """INSERT INTO sessions (id, ide, project, cwd, model, initiative, branch, created_at, closed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )


def _seed_messages(conn: sqlite3.Connection) -> None:
    rows = [
        ("s1", 1, "user", "Hello, write some code", "2025-01-01T10:00:01"),
        ("s1", 2, "assistant", "Sure, here is the code", "2025-01-01T10:00:05"),
        ("s1", 3, "user", "Now fix the bug", "2025-01-01T10:10:00"),
        ("s2", 1, "user", "Review this PR", "2025-01-02T12:00:01"),
        ("s2", 2, "assistant", "LGTM", "2025-01-02T12:05:00"),
    ]
    conn.executemany(
        "INSERT INTO messages (session_id, seq, type, content, ts) VALUES (?, ?, ?, ?, ?)",
        rows,
    )


def _seed_tool_calls(conn: sqlite3.Connection) -> None:
    rows = [
        ("s1", "call-1", "Read", "builtin", None, None, None,
         '{"file_path":"/tmp/test.py"}', '"content..."', 150, 1, 2,
         "2025-01-01T10:00:02"),
        ("s1", "call-2", "Skill", "api", None, None, "my-skill",
         '{"args":"value"}', '"result"', 500, 2, 3,
         "2025-01-01T10:00:06"),
        ("s1", "call-3", "Write", "builtin", None, "call-2", None,
         '{"file_path":"/tmp/test.py"}', '"ok"', 200, None, None,
         "2025-01-01T10:00:07"),
        ("s2", "call-4", "Bash", "builtin", None, None, None,
         '{"command":"ls"}', '"file list"', 300, 1, 2,
         "2025-01-02T12:00:02"),
        ("s2", "call-5", "Skill", "api", None, None, "other-skill",
         '{"args":"x"}', '"done"', 100, None, None,
         "2025-01-02T12:03:00"),
    ]
    conn.executemany(
        """INSERT INTO tool_calls
           (session_id, call_id, tool, tool_type, server_name, parent_call_id,
            parent_skill, args, result, duration_ms, seq_before, seq_after, ts)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )


def _seed_file_ops(conn: sqlite3.Connection) -> None:
    rows = [
        ("s1", "call-1", "read",  "/tmp/test.py",     "py", "test-project", None,       1, "2025-01-01T10:00:02"),
        ("s1", "call-3", "write", "/tmp/test.py",     "py", "test-project", "my-skill", 2, "2025-01-01T10:00:07"),
        ("s1", "call-3", "read",  "/tmp/config.json",  "json", "test-project", "my-skill", 3, "2025-01-01T10:00:08"),
        ("s2", "call-4", "read",  "/tmp/other.py",    "py", "other-project", None,       1, "2025-01-02T12:00:03"),
        ("s2", "call-5", "write", "/tmp/other.py",    "py", "other-project", "other-skill", 2, "2025-01-02T12:04:00"),
    ]
    conn.executemany(
        """INSERT INTO file_ops (session_id, call_id, op, path, file_type, project, skill_name, seq, ts)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )


def _seed_session_stats(conn: sqlite3.Connection) -> None:
    rows = [
        ("s1", 3, 3, 1, 2, 1, 0, 30, "2025-01-01T10:30:00"),
        ("s2", 2, 2, 1, 1, 1, 1, 5, "2025-01-02T12:05:00"),
    ]
    conn.executemany(
        """INSERT INTO session_stats
           (session_id, message_count, tool_count, skill_count,
            read_count, write_count, bash_count, duration_min, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )


def _seed_skills(conn: sqlite3.Connection) -> None:
    rows = [
        ("my-skill",   2, "2025-01-03T08:00:00", "2025-01-01T10:00:06"),
        ("other-skill", 1, "2025-01-02T12:03:00", "2025-01-02T12:03:00"),
    ]
    conn.executemany(
        "INSERT INTO skills (name, total_calls, last_invoked, first_invoked) VALUES (?, ?, ?, ?)",
        rows,
    )


def _seed_knowledge(conn: sqlite3.Connection) -> None:
    rows = [
        ("How to write tests", "pattern", "s1", "test-project", "my-skill",
         "Use pytest with fixtures", "evidence...", "2025-01-01T10:30:00", None),
        ("Deploy checklist", "checklist", "s2", "other-project", "other-skill",
         "Run CI before merge", "evidence2", "2025-01-02T12:05:00", "merged-to-x"),
    ]
    conn.executemany(
        """INSERT INTO knowledge
           (title, type, session_id, project, skills, summary, evidence, generated_at, merged_to_skill)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )


def _seed_session_summaries(conn: sqlite3.Connection) -> None:
    rows = [
        ("s1", "workflow1", "remember this", "ops1", "pitfall1",
         "waste1", "bottleneck1", "tip1", 8.5, 0.7, 0.1, 2, 5.0,
         "keyword1,keyword2", "2025-01-01T10:30:00"),
    ]
    conn.executemany(
        """INSERT INTO session_summaries
           (session_id, sop_workflows, context_to_remember, effective_operations,
            pitfalls_and_fixes, wasted_actions, bottlenecks, efficiency_tip,
            efficiency_score, think_action_ratio, edit_redundancy, loop_count,
            user_wait_minutes, memory_keywords, generated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )


# ===================================================================
# Part 1: Query function tests
# ===================================================================

class TestQuerySessions:
    def test_returns_all_sessions_ordered_by_created_at_desc(self, test_db):
        result = queries.query_sessions()
        assert len(result) == 3
        assert result[0]["id"] == "s3"  # most recent first
        assert result[1]["id"] == "s2"
        assert result[2]["id"] == "s1"
        # s1 has stats
        assert result[2]["message_count"] == 3
        assert result[2]["tool_count"] == 3
        assert result[2]["skill_count"] == 1
        assert result[2]["duration_min"] == 30

    def test_respects_limit(self, test_db):
        result = queries.query_sessions(limit=1)
        assert len(result) == 1
        assert result[0]["id"] == "s3"


class TestQuerySessionDetail:
    def test_returns_full_detail_for_existing_session(self, test_db):
        result = queries.query_session_detail("s1")
        assert result["session"]["id"] == "s1"
        assert result["session"]["project"] == "test-project"
        assert len(result["messages"]) == 3
        assert len(result["tool_calls"]) == 3
        assert len(result["file_ops"]) == 3
        assert result["summary"]["session_id"] == "s1"
        assert result["stats"]["session_id"] == "s1"
        # messages ordered by seq
        assert result["messages"][0]["seq"] == 1
        assert result["messages"][0]["type"] == "user"

    def test_returns_none_session_for_missing_id(self, test_db):
        result = queries.query_session_detail("nonexistent")
        assert result["session"] is None
        assert result["messages"] == []
        assert result["tool_calls"] == []
        assert result["file_ops"] == []
        assert result["summary"] is None
        assert result["stats"] is None


class TestQuerySkills:
    def test_returns_all_skills_ordered_by_total_calls(self, test_db):
        result = queries.query_skills()
        assert len(result) == 2
        assert result[0]["name"] == "my-skill"
        assert result[0]["total_calls"] == 2
        assert result[1]["name"] == "other-skill"
        assert result[1]["total_calls"] == 1


class TestQueryTools:
    def test_returns_aggregated_tool_stats(self, test_db):
        result = queries.query_tools()
        # 4 distinct tools: Read, Skill, Write, Bash
        # Wait - actually Skill appears twice (call-2 and call-5), Read once, Write once, Bash once
        # So 4 tools with Skill having 2 calls
        tools_by_name = {r["tool"]: r for r in result}
        assert len(result) >= 3
        assert tools_by_name["Skill"]["calls"] == 2
        assert tools_by_name["Read"]["calls"] == 1
        assert tools_by_name["Write"]["calls"] == 1
        assert tools_by_name["Bash"]["calls"] == 1

    def test_includes_avg_and_max_duration(self, test_db):
        result = queries.query_tools()
        skill = next(r for r in result if r["tool"] == "Skill")
        assert skill["avg_ms"] == 300.0  # (500 + 100) / 2
        assert skill["max_ms"] == 500


class TestQueryFiles:
    def test_returns_all_file_ops_by_default(self, test_db):
        result = queries.query_files()
        assert len(result) == 5

    def test_filters_by_project(self, test_db):
        result = queries.query_files(project="test-project")
        assert len(result) == 3
        for r in result:
            assert r["project"] == "test-project"

    def test_filters_by_file_type(self, test_db):
        result = queries.query_files(file_type="json")
        assert len(result) == 1
        assert result[0]["path"] == "/tmp/config.json"

    def test_filters_by_both_project_and_file_type(self, test_db):
        result = queries.query_files(project="test-project", file_type="py")
        assert len(result) == 2
        for r in result:
            assert r["project"] == "test-project"
            assert r["file_type"] == "py"

    def test_respects_limit(self, test_db):
        result = queries.query_files(limit=2)
        assert len(result) == 2


class TestQueryKnowledge:
    def test_returns_all_knowledge_entries(self, test_db):
        result = queries.query_knowledge()
        assert len(result) == 2
        assert result[0]["title"] == "Deploy checklist"  # most recent first
        assert result[1]["title"] == "How to write tests"

    def test_includes_merged_to_skill_when_set(self, test_db):
        result = queries.query_knowledge()
        entry = next(r for r in result if r["title"] == "Deploy checklist")
        assert entry["merged_to_skill"] == "merged-to-x"


class TestQueryInitiatives:
    def test_returns_initiatives_with_counts(self, test_db):
        result = queries.query_initiatives()
        assert len(result) == 1  # only "my-initiative"
        assert result[0]["initiative"] == "my-initiative"
        assert result[0]["session_count"] == 2
        # s1 has 3 tool calls, s3 has 0 → 3 distinct call_ids
        assert result[0]["tool_count"] == 3


class TestQueryOverview:
    def test_returns_comprehensive_aggregates(self, test_db):
        result = queries.query_overview()
        assert result["total_sessions"] == 3
        assert result["total_messages"] == 5
        assert result["total_tools"] == 5
        assert result["total_skills"] == 2
        assert result["total_knowledge"] == 2
        # s2 has closed_at=NULL → active
        assert result["active_sessions"] == 1
        assert len(result["recent_sessions"]) == 3
        assert len(result["tool_distribution"]) > 0
        assert len(result["daily_sessions"]) > 0

    def test_tool_distribution_correct(self, test_db):
        result = queries.query_overview()
        td = {r["tool"]: r["c"] for r in result["tool_distribution"]}
        assert td["Skill"] == 2
        assert td["Read"] == 1


class TestQuerySessionTimeline:
    def test_returns_interleaved_timeline(self, test_db):
        result = queries.query_session_timeline("s1")
        assert len(result) > 0
        kinds = {r["kind"] for r in result}
        assert kinds == {"message", "tool_call", "file_op"}

    def test_messages_have_subtype_and_detail(self, test_db):
        result = queries.query_session_timeline("s1")
        msgs = [r for r in result if r["kind"] == "message"]
        assert len(msgs) == 3
        assert msgs[0]["subtype"] == "user"
        assert msgs[0]["detail"] == "Hello, write some code"

    def test_tool_calls_have_subtype_and_detail(self, test_db):
        result = queries.query_session_timeline("s1")
        calls = [r for r in result if r["kind"] == "tool_call"]
        assert len(calls) == 3
        # Tool calls have tool name as subtype, args as detail
        read_call = next(r for r in calls if r["subtype"] == "Read")
        assert read_call["tool"] == "Read"
        assert "test.py" in read_call["detail"]

    def test_file_ops_have_subtype_and_detail(self, test_db):
        result = queries.query_session_timeline("s1")
        ops = [r for r in result if r["kind"] == "file_op"]
        assert len(ops) == 3
        assert ops[0]["subtype"] == "read"
        assert ops[0]["detail"] == "/tmp/test.py"

    def test_ordered_by_ts_and_seq(self, test_db):
        result = queries.query_session_timeline("s1")
        for i in range(len(result) - 1):
            assert result[i]["ts"] <= result[i + 1]["ts"]

    def test_empty_for_unknown_session(self, test_db):
        result = queries.query_session_timeline("nonexistent")
        assert result == []


class TestQuerySkillSessions:
    def test_returns_skill_sessions_with_join(self, test_db):
        result = queries.query_skill_sessions()
        # Only call-2 (s1) and call-5 (s2) have tool='Skill'
        # GROUP BY session_id, tool → one row per session, both with tool='Skill'
        assert len(result) == 2
        sessions_in_result = {r["session_id"] for r in result}
        assert sessions_in_result == {"s1", "s2"}

    def test_includes_project_and_created_at(self, test_db):
        result = queries.query_skill_sessions()
        s1_row = next(r for r in result if r["session_id"] == "s1")
        assert s1_row["project"] == "test-project"
        assert s1_row["created_at"] == "2025-01-01T10:00:00"
        assert s1_row["invocations"] == 1


class TestQueryFileStats:
    def test_returns_file_stats_grouped_by_path_and_op(self, test_db):
        result = queries.query_file_stats()
        # /tmp/test.py: read + write = 2 rows
        # /tmp/config.json: read = 1 row
        # /tmp/other.py: read + write = 2 rows
        assert len(result) == 5

    def test_includes_op_type_and_ops_count(self, test_db):
        result = queries.query_file_stats()
        by_path_op = {(r["file_path"], r["op_type"]): r for r in result}
        assert by_path_op[("/tmp/test.py", "write")]["ops"] == 1
        assert by_path_op[("/tmp/test.py", "read")]["ops"] == 1


class TestQueryTopFiles:
    def test_returns_files_ranked_by_total_ops(self, test_db):
        result = queries.query_top_files()
        assert len(result) == 3
        # test.py: 2 ops, other.py: 2 ops, config.json: 1 op
        assert result[0]["file_path"] in ("/tmp/other.py", "/tmp/test.py")
        assert result[0]["total_ops"] == 2

    def test_includes_read_write_breakdown(self, test_db):
        result = queries.query_top_files()
        test_py = next(r for r in result if r["file_path"] == "/tmp/test.py")
        assert test_py["reads"] == 1
        assert test_py["writes"] == 1

    def test_respects_limit(self, test_db):
        result = queries.query_top_files(limit=1)
        assert len(result) == 1

    def test_includes_projects_concatenated(self, test_db):
        result = queries.query_top_files()
        test_py = next(r for r in result if r["file_path"] == "/tmp/test.py")
        assert "test-project" in test_py["projects"]


# ===================================================================
# Part 2: FastAPI endpoint tests
# ===================================================================

@pytest.fixture
def client(monkeypatch):
    """TestClient with get_db patched to use the shared in-memory database."""
    # Ensure the shared DB is seeded before any FastAPI request
    conn = _make_shared_conn()
    conn.executescript(SCHEMA)
    _seed_all(conn)
    conn.commit()

    monkeypatch.setattr(queries, "get_db", _make_shared_conn)

    with TestClient(app) as tc:
        yield tc

    # Drop tables so the next test fixture gets a clean slate
    conn.executescript("""
        DROP TABLE IF EXISTS session_summaries;
        DROP TABLE IF EXISTS knowledge;
        DROP TABLE IF EXISTS skills;
        DROP TABLE IF EXISTS session_stats;
        DROP TABLE IF EXISTS file_ops;
        DROP TABLE IF EXISTS tool_calls;
        DROP TABLE IF EXISTS messages;
        DROP TABLE IF EXISTS sessions;
    """)
    conn.commit()
    conn.close()


class TestApiOverview:
    def test_returns_200_with_aggregates(self, client):
        resp = client.get("/api/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_sessions"] == 3
        assert data["total_messages"] == 5
        assert "recent_sessions" in data
        assert "tool_distribution" in data
        assert "daily_sessions" in data


class TestApiSessions:
    def test_returns_200_with_session_list(self, client):
        resp = client.get("/api/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

    def test_respects_limit_query_param(self, client):
        resp = client.get("/api/sessions?limit=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1


class TestApiSessionDetail:
    def test_returns_200_with_full_detail(self, client):
        resp = client.get("/api/sessions/s1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session"]["id"] == "s1"
        assert len(data["messages"]) == 3
        assert len(data["tool_calls"]) == 3
        assert len(data["file_ops"]) == 3

    def test_returns_200_with_null_session_for_missing_id(self, client):
        resp = client.get("/api/sessions/nonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session"] is None


class TestApiSessionTimeline:
    def test_returns_200_with_interleaved_timeline(self, client):
        resp = client.get("/api/sessions/s1/timeline")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) > 0
        kinds = {item["kind"] for item in data}
        assert kinds == {"message", "tool_call", "file_op"}

    def test_empty_array_for_unknown_session(self, client):
        resp = client.get("/api/sessions/nonexistent/timeline")
        assert resp.status_code == 200
        data = resp.json()
        assert data == []


class TestApiSkills:
    def test_returns_200_with_skills(self, client):
        resp = client.get("/api/skills")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "my-skill"


class TestApiTools:
    def test_returns_200_with_tool_stats(self, client):
        resp = client.get("/api/tools")
        assert resp.status_code == 200
        data = resp.json()
        tools = {r["tool"]: r for r in data}
        assert "Skill" in tools
        assert tools["Skill"]["calls"] == 2


class TestApiFiles:
    def test_returns_200_with_all_files(self, client):
        resp = client.get("/api/files")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5

    def test_filters_by_project(self, client):
        resp = client.get("/api/files?project=test-project")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3
        for item in data:
            assert item["project"] == "test-project"

    def test_filters_by_file_type(self, client):
        resp = client.get("/api/files?file_type=json")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["file_type"] == "json"


class TestApiKnowledge:
    def test_returns_200_with_knowledge_entries(self, client):
        resp = client.get("/api/knowledge")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2


class TestApiInitiatives:
    def test_returns_200_with_initiatives(self, client):
        resp = client.get("/api/initiatives")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["initiative"] == "my-initiative"


class TestApiSkillSessions:
    def test_returns_200_with_skill_sessions(self, client):
        resp = client.get("/api/skill-sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        sessions_in_result = {r["session_id"] for r in data}
        assert sessions_in_result == {"s1", "s2"}


class TestApiTopFiles:
    def test_returns_200_with_ranked_files(self, client):
        resp = client.get("/api/top-files")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

    def test_respects_limit_query_param(self, client):
        resp = client.get("/api/top-files?limit=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1


class TestApiFileStats:
    def test_returns_200_with_file_stats(self, client):
        resp = client.get("/api/file-stats")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5
        # Each row should have file_path, op_type, ops
        for item in data:
            assert "file_path" in item
            assert "op_type" in item
            assert "ops" in item


# ===================================================================
# Part 3: WebSocket endpoint test
# ===================================================================


class TestWebSocket:
    def test_websocket_returns_overview_on_refresh(self, client):
        with client.websocket_connect("/ws") as ws:
            ws.send_text("refresh")
            data = ws.receive_json()
            assert "total_sessions" in data
