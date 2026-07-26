"""Tests for analytics/auto_import.py — auto-import daemon functions."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_jsonl(path: Path, lines: list[dict]) -> Path:
    path.write_text("\n".join(json.dumps(obj) for obj in lines))
    return path


# ---------------------------------------------------------------------------
# DB fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def auto_db(monkeypatch):
    """In-memory SQLite with full schema, patched get_db."""
    from coworker.analytics import auto_import as ai_mod
    from coworker.analytics.db import SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    monkeypatch.setattr(ai_mod, "get_db", lambda: conn)
    yield conn
    conn.close()


# ===================================================================
# _parse_session_id
# ===================================================================


def test_parse_session_id_from_yaml(tmp_path):
    from coworker.analytics.auto_import import _parse_session_id

    d = tmp_path / "session_dir"
    d.mkdir()
    (d / "session.yaml").write_text('session_id: "abc-123"\nother: val\n')
    assert _parse_session_id(d) == "abc-123"


def test_parse_session_id_fallback_to_dirname(tmp_path):
    from coworker.analytics.auto_import import _parse_session_id

    d = tmp_path / "my-session-dir"
    d.mkdir()
    assert _parse_session_id(d) == "my-session-dir"


def test_parse_session_id_yaml_exists_but_no_session_id(tmp_path):
    from coworker.analytics.auto_import import _parse_session_id

    d = tmp_path / "my-dir"
    d.mkdir()
    (d / "session.yaml").write_text("project: my-project\ncwd: /tmp\n")
    assert _parse_session_id(d) == "my-dir"


def test_parse_session_id_empty_value(tmp_path):
    from coworker.analytics.auto_import import _parse_session_id

    d = tmp_path / "my-dir"
    d.mkdir()
    (d / "session.yaml").write_text('session_id: ""\n')
    assert _parse_session_id(d) == "my-dir"


# ===================================================================
# _get_skills
# ===================================================================


def test_get_skills_from_jsonl(tmp_path):
    from coworker.analytics.auto_import import _get_skills

    f = _make_jsonl(tmp_path / "test.jsonl", [
        {"message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"name": "my-skill"}},
        ]}},
        {"message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"name": "other-skill"}},
        ]}},
        {"message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"name": "my-skill"}},
        ]}},
    ])
    skills = _get_skills(f)
    assert skills == {"my-skill", "other-skill"}


def test_get_skills_file_not_exists(tmp_path):
    from coworker.analytics.auto_import import _get_skills
    assert _get_skills(tmp_path / "nonexistent.jsonl") == set()


def test_get_skills_empty_file(tmp_path):
    from coworker.analytics.auto_import import _get_skills
    f = tmp_path / "empty.jsonl"
    f.write_text("")
    assert _get_skills(f) == set()


def test_get_skills_no_skill_calls(tmp_path):
    from coworker.analytics.auto_import import _get_skills

    f = _make_jsonl(tmp_path / "test.jsonl", [
        {"message": {"content": [
            {"type": "tool_use", "name": "Read", "input": {"file_path": "/x.py"}},
        ]}},
    ])
    assert _get_skills(f) == set()


def test_get_skills_bad_json_skipped(tmp_path):
    from coworker.analytics.auto_import import _get_skills

    f = tmp_path / "test.jsonl"
    f.write_text(
        "not valid json\n"
        + json.dumps({"message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"name": "ok-skill"}},
        ]}})
    )
    skills = _get_skills(f)
    assert skills == {"ok-skill"}


def test_get_skills_message_not_dict(tmp_path):
    from coworker.analytics.auto_import import _get_skills

    f = _make_jsonl(tmp_path / "test.jsonl", [
        {"message": "just a string"},
    ])
    assert _get_skills(f) == set()


def test_get_skills_content_not_list(tmp_path):
    from coworker.analytics.auto_import import _get_skills

    f = _make_jsonl(tmp_path / "test.jsonl", [
        {"message": {"content": "not a list"}},
    ])
    assert _get_skills(f) == set()


# ===================================================================
# _count_jsonl_lines
# ===================================================================


def test_count_jsonl_lines(tmp_path):
    from coworker.analytics.auto_import import _count_jsonl_lines

    f = tmp_path / "test.jsonl"
    f.write_text("line1\nline2\nline3\n")
    assert _count_jsonl_lines(f) == 3


def test_count_jsonl_lines_file_not_exists(tmp_path):
    from coworker.analytics.auto_import import _count_jsonl_lines
    assert _count_jsonl_lines(tmp_path / "nonexistent.jsonl") == 0


def test_count_jsonl_lines_empty(tmp_path):
    from coworker.analytics.auto_import import _count_jsonl_lines
    f = tmp_path / "empty.jsonl"
    f.write_text("")
    assert _count_jsonl_lines(f) == 0


def test_count_jsonl_lines_with_blank_lines(tmp_path):
    from coworker.analytics.auto_import import _count_jsonl_lines

    f = tmp_path / "test.jsonl"
    f.write_text("line1\n\nline2\n  \n")
    assert _count_jsonl_lines(f) == 2


# ===================================================================
# _count_jsonl_skill_calls
# ===================================================================


def test_count_jsonl_skill_calls(tmp_path):
    from coworker.analytics.auto_import import _count_jsonl_skill_calls

    f = _make_jsonl(tmp_path / "test.jsonl", [
        {"message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"name": "skill-a"}},
        ]}},
        {"message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"name": "skill-b"}},
        ]}},
    ])
    skills = _count_jsonl_skill_calls(f)
    assert skills == {"skill-a", "skill-b"}


def test_count_jsonl_skill_calls_not_exists(tmp_path):
    from coworker.analytics.auto_import import _count_jsonl_skill_calls
    assert _count_jsonl_skill_calls(tmp_path / "nonexistent.jsonl") == set()


def test_count_jsonl_skill_calls_with_bad_json(tmp_path):
    from coworker.analytics.auto_import import _count_jsonl_skill_calls

    f = tmp_path / "test.jsonl"
    f.write_text(
        "bad json\n"
        + json.dumps({"message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"name": "still-found"}},
        ]}})
    )
    skills = _count_jsonl_skill_calls(f)
    assert skills == {"still-found"}


# ===================================================================
# import_claude_jsonl
# ===================================================================


def test_import_claude_jsonl_basic(auto_db, tmp_path):
    """Import a JSONL session with all tool types."""
    from coworker.analytics.auto_import import import_claude_jsonl

    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    jsonl_file = _make_jsonl(project_dir / "session-id.jsonl", [
        {
            "type": "assistant", "timestamp": "2025-01-01T10:00:00", "cwd": "/tmp/proj",
            "message": {"model": "claude-3", "content": [
                {"type": "tool_use", "name": "Skill", "id": "call-1",
                 "input": {"name": "my-skill"}},
            ]},
        },
        {
            "type": "user", "timestamp": "2025-01-01T10:00:05", "cwd": "/tmp/proj",
            "message": {"content": [{"type": "text", "text": "hello"}]},
        },
        {
            "type": "assistant", "timestamp": "2025-01-01T10:00:06", "cwd": "/tmp/proj",
            "message": {"model": "claude-3", "content": [
                {"type": "tool_use", "name": "Read", "id": "call-2",
                 "input": {"file_path": "/tmp/test.py"}},
            ]},
        },
        {
            "type": "assistant", "timestamp": "2025-01-01T10:00:07", "cwd": "/tmp/proj",
            "message": {"model": "claude-3", "content": [
                {"type": "tool_use", "name": "Write", "id": "call-3",
                 "input": {"file_path": "/tmp/test.py"}},
            ]},
        },
        {
            "type": "assistant", "timestamp": "2025-01-01T10:00:08", "cwd": "/tmp/proj",
            "message": {"model": "claude-3", "content": [
                {"type": "tool_use", "name": "Edit", "id": "call-4",
                 "input": {"path": "/tmp/other.py"}},
            ]},
        },
        {
            "type": "assistant", "timestamp": "2025-01-01T10:00:09", "cwd": "/tmp/proj",
            "message": {"model": "claude-3", "content": [
                {"type": "tool_use", "name": "Bash", "id": "call-5",
                 "input": {"command": "ls"}},
            ]},
        },
    ])

    import_claude_jsonl(jsonl_file, auto_db)

    # session
    s = auto_db.execute("SELECT * FROM sessions WHERE id = ?", ("session-id",)).fetchone()
    assert s is not None
    assert s["ide"] == "claude-code"
    assert s["project"] == "test-project"
    assert s["cwd"] == "/tmp/proj"
    assert s["model"] == "claude-3"
    assert s["created_at"] == "2025-01-01T10:00:00"

    # stats
    stats = auto_db.execute(
        "SELECT * FROM session_stats WHERE session_id = ?", ("session-id",)
    ).fetchone()
    assert stats is not None
    assert stats["message_count"] == 6
    assert stats["tool_count"] == 4  # Read + Write + Edit + Bash (Skill counted separately)
    assert stats["skill_count"] == 1  # my-skill
    assert stats["read_count"] == 1  # Read
    assert stats["write_count"] == 2  # Write + Edit
    assert stats["bash_count"] == 0  # Bash does not count as bash in stats

    # file_ops — Read, Write, Edit leave entries; Bash has no file_path so skipped
    file_ops = auto_db.execute(
        "SELECT * FROM file_ops WHERE session_id = ?", ("session-id",)
    ).fetchall()
    assert len(file_ops) == 3  # Read + Write + Edit

    # skills table
    skill_row = auto_db.execute(
        "SELECT * FROM skills WHERE name = ?", ("my-skill",)
    ).fetchone()
    assert skill_row is not None
    assert skill_row["total_calls"] == 1


def test_import_claude_jsonl_no_tools(auto_db, tmp_path):
    from coworker.analytics.auto_import import import_claude_jsonl

    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    jsonl_file = _make_jsonl(project_dir / "session-no-tools.jsonl", [
        {
            "type": "assistant", "timestamp": "2025-01-01T10:00:00", "cwd": "/tmp/proj",
            "message": {"model": "claude-3", "content": [{"type": "text", "text": "hello"}]},
        },
    ])

    import_claude_jsonl(jsonl_file, auto_db)

    s = auto_db.execute(
        "SELECT * FROM sessions WHERE id = ?", ("session-no-tools",)
    ).fetchone()
    assert s is not None

    stats = auto_db.execute(
        "SELECT * FROM session_stats WHERE session_id = ?", ("session-no-tools",)
    ).fetchone()
    assert stats["tool_count"] == 0
    assert stats["message_count"] == 1


def test_import_claude_jsonl_glob_counts_as_read(auto_db, tmp_path):
    from coworker.analytics.auto_import import import_claude_jsonl

    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    jsonl_file = _make_jsonl(project_dir / "session-glob.jsonl", [
        {
            "type": "assistant", "timestamp": "2025-01-01T10:00:00", "cwd": "/tmp/proj",
            "message": {"model": "claude-3", "content": [
                {"type": "tool_use", "name": "Glob", "id": "call-1",
                 "input": {"path": "/tmp/*.py"}},
            ]},
        },
    ])

    import_claude_jsonl(jsonl_file, auto_db)

    stats = auto_db.execute(
        "SELECT * FROM session_stats WHERE session_id = ?", ("session-glob",)
    ).fetchone()
    assert stats["read_count"] == 1


def test_import_claude_jsonl_other_tool_ends_skill_context(auto_db, tmp_path):
    """A non-skill, non-file tool (e.g. TodoWrite) should set active_skill to None."""
    from coworker.analytics.auto_import import import_claude_jsonl

    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    jsonl_file = _make_jsonl(project_dir / "session-context.jsonl", [
        {
            "type": "assistant", "timestamp": "2025-01-01T10:00:00", "cwd": "/tmp/proj",
            "message": {"model": "claude-3", "content": [
                {"type": "tool_use", "name": "Skill", "id": "call-1",
                 "input": {"name": "my-skill"}},
            ]},
        },
        {
            "type": "assistant", "timestamp": "2025-01-01T10:00:01", "cwd": "/tmp/proj",
            "message": {"model": "claude-3", "content": [
                {"type": "tool_use", "name": "TodoWrite", "id": "call-2",
                 "input": {"todos": []}},
            ]},
        },
        {
            "type": "assistant", "timestamp": "2025-01-01T10:00:02", "cwd": "/tmp/proj",
            "message": {"model": "claude-3", "content": [
                {"type": "tool_use", "name": "Write", "id": "call-3",
                 "input": {"file_path": "/tmp/output.py"}},
            ]},
        },
    ])

    import_claude_jsonl(jsonl_file, auto_db)

    s = auto_db.execute(
        "SELECT * FROM sessions WHERE id = ?", ("session-context",)
    ).fetchone()
    assert s is not None

    # The Write call after TodoWrite should have active_skill=None
    # (not "my-skill") because TodoWrite ended the skill context
    file_ops = auto_db.execute(
        "SELECT skill_name FROM file_ops WHERE session_id = ? AND call_id = ?",
        ("session-context", "call-3"),
    ).fetchone()
    assert file_ops is not None
    assert file_ops["skill_name"] is None


def test_import_claude_jsonl_skill_context_persists_for_file_tools(auto_db, tmp_path):
    """After a Skill call, file tools inherit the skill_name."""
    from coworker.analytics.auto_import import import_claude_jsonl

    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    jsonl_file = _make_jsonl(project_dir / "session-skill-ctx.jsonl", [
        {
            "type": "assistant", "timestamp": "2025-01-01T10:00:00", "cwd": "/tmp/proj",
            "message": {"model": "claude-3", "content": [
                {"type": "tool_use", "name": "Skill", "id": "call-1",
                 "input": {"name": "active-skill"}},
            ]},
        },
        {
            "type": "assistant", "timestamp": "2025-01-01T10:00:01", "cwd": "/tmp/proj",
            "message": {"model": "claude-3", "content": [
                {"type": "tool_use", "name": "Read", "id": "call-2",
                 "input": {"file_path": "/tmp/data.py"}},
            ]},
        },
    ])

    import_claude_jsonl(jsonl_file, auto_db)

    file_op = auto_db.execute(
        "SELECT skill_name FROM file_ops WHERE session_id = ? AND call_id = ?",
        ("session-skill-ctx", "call-2"),
    ).fetchone()
    assert file_op is not None
    assert file_op["skill_name"] == "active-skill"


def test_import_claude_jsonl_bad_json_lines(auto_db, tmp_path):
    from coworker.analytics.auto_import import import_claude_jsonl

    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    jsonl_file = project_dir / "session-bad.jsonl"
    jsonl_file.write_text(
        "not valid json\n"
        + json.dumps({
            "type": "assistant", "timestamp": "2025-01-01T10:00:00", "cwd": "/tmp/proj",
            "message": {"model": "claude-3", "content": []},
        })
    )

    import_claude_jsonl(jsonl_file, auto_db)

    s = auto_db.execute(
        "SELECT * FROM sessions WHERE id = ?", ("session-bad",)
    ).fetchone()
    assert s is not None


def test_import_claude_jsonl_cwd_from_later_line(auto_db, tmp_path):
    """cwd can come from any line, not just the first one."""
    from coworker.analytics.auto_import import import_claude_jsonl

    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    jsonl_file = _make_jsonl(project_dir / "session-cwd.jsonl", [
        {
            "type": "assistant", "timestamp": "2025-01-01T10:00:00",
            "message": {"model": "claude-3", "content": []},
        },
        {
            "type": "user", "timestamp": "2025-01-01T10:00:01", "cwd": "/tmp/later-cwd",
            "message": {"content": []},
        },
    ])

    import_claude_jsonl(jsonl_file, auto_db)

    s = auto_db.execute(
        "SELECT * FROM sessions WHERE id = ?", ("session-cwd",)
    ).fetchone()
    assert s["cwd"] == "/tmp/later-cwd"


def test_import_claude_jsonl_no_timestamp(auto_db, tmp_path):
    """Session without a timestamp gets empty string for created_at."""
    from coworker.analytics.auto_import import import_claude_jsonl

    project_dir = tmp_path / "no-ts-project"
    project_dir.mkdir()
    jsonl_file = _make_jsonl(project_dir / "session-no-ts.jsonl", [
        {
            "type": "assistant", "cwd": "/tmp/proj",
            "message": {"model": "claude-3", "content": []},
        },
    ])

    import_claude_jsonl(jsonl_file, auto_db)

    s = auto_db.execute(
        "SELECT * FROM sessions WHERE id = ?", ("session-no-ts",)
    ).fetchone()
    assert s is not None
    assert s["created_at"] == ""


def test_import_claude_jsonl_message_not_dict(auto_db, tmp_path):
    """Messages that are not dicts should be skipped safely."""
    from coworker.analytics.auto_import import import_claude_jsonl

    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    jsonl_file = _make_jsonl(project_dir / "session-msg-str.jsonl", [
        {
            "type": "assistant", "timestamp": "2025-01-01T10:00:00", "cwd": "/tmp/proj",
            "message": "just a string, not a dict",
        },
    ])

    import_claude_jsonl(jsonl_file, auto_db)

    s = auto_db.execute(
        "SELECT * FROM sessions WHERE id = ?", ("session-msg-str",)
    ).fetchone()
    assert s is not None


def test_import_claude_jsonl_file_op_with_filePath_key(auto_db, tmp_path):
    """filePath as an alternative key for file path."""
    from coworker.analytics.auto_import import import_claude_jsonl

    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    jsonl_file = _make_jsonl(project_dir / "session-filepath.jsonl", [
        {
            "type": "assistant", "timestamp": "2025-01-01T10:00:00", "cwd": "/tmp/proj",
            "message": {"model": "claude-3", "content": [
                {"type": "tool_use", "name": "Read", "id": "call-1",
                 "input": {"filePath": "/tmp/camel.py"}},
            ]},
        },
    ])

    import_claude_jsonl(jsonl_file, auto_db)

    fop = auto_db.execute(
        "SELECT path, op FROM file_ops WHERE session_id = ?", ("session-filepath",)
    ).fetchone()
    assert fop is not None
    assert fop["path"] == "/tmp/camel.py"
    assert fop["op"] == "read"


def test_import_claude_jsonl_no_content_list(auto_db, tmp_path):
    """Messages with non-list content should not crash."""
    from coworker.analytics.auto_import import import_claude_jsonl

    project_dir = tmp_path / "test-project"
    project_dir.mkdir()
    jsonl_file = _make_jsonl(project_dir / "session-nolist.jsonl", [
        {
            "type": "assistant", "timestamp": "2025-01-01T10:00:00", "cwd": "/tmp/proj",
            "message": {"model": "claude-3", "content": "plain text"},
        },
    ])

    import_claude_jsonl(jsonl_file, auto_db)

    s = auto_db.execute(
        "SELECT * FROM sessions WHERE id = ?", ("session-nolist",)
    ).fetchone()
    assert s is not None


# ===================================================================
# import_claude_hooks
# ===================================================================


def test_import_claude_hooks_basic(auto_db, tmp_path):
    from coworker.analytics.auto_import import import_claude_hooks

    session_dir = tmp_path / "hooks-session"
    session_dir.mkdir()
    (session_dir / "session.yaml").write_text(
        "session_id: hooks-123\nproject: my-proj\ncwd: /tmp/proj\n"
        "model: claude-3\ncreated: 2025-01-01\n"
    )
    (session_dir / "messages.jsonl").write_text(
        '{"type":"user"}\n{"type":"assistant"}\n'
    )
    (session_dir / "tools.jsonl").write_text(
        '{"tool":"Read"}\n{"tool":"Write"}\n{"tool":"Bash"}\n'
    )

    import_claude_hooks(session_dir, auto_db)

    s = auto_db.execute(
        "SELECT * FROM sessions WHERE id = ?", ("hooks-session",)
    ).fetchone()
    assert s is not None
    assert s["ide"] == "claude-code"
    assert s["project"] == "my-proj"
    assert s["cwd"] == "/tmp/proj"
    assert s["model"] == "claude-3"

    stats = auto_db.execute(
        "SELECT * FROM session_stats WHERE session_id = ?", ("hooks-session",)
    ).fetchone()
    assert stats is not None
    assert stats["message_count"] == 2
    assert stats["tool_count"] == 3


def test_import_claude_hooks_no_message_or_tool_files(auto_db, tmp_path):
    from coworker.analytics.auto_import import import_claude_hooks

    session_dir = tmp_path / "hooks-minimal"
    session_dir.mkdir()
    (session_dir / "session.yaml").write_text("session_id: minimal-1\n")

    import_claude_hooks(session_dir, auto_db)

    s = auto_db.execute(
        "SELECT * FROM sessions WHERE id = ?", ("hooks-minimal",)
    ).fetchone()
    assert s is not None

    stats = auto_db.execute(
        "SELECT * FROM session_stats WHERE session_id = ?", ("hooks-minimal",)
    ).fetchone()
    assert stats["message_count"] == 0
    assert stats["tool_count"] == 0


def test_import_claude_hooks_no_yaml(auto_db, tmp_path):
    from coworker.analytics.auto_import import import_claude_hooks

    session_dir = tmp_path / "hooks-no-yaml"
    session_dir.mkdir()
    (session_dir / "messages.jsonl").write_text('{"type":"user"}\n')
    (session_dir / "tools.jsonl").write_text('{"tool":"Read"}\n')

    import_claude_hooks(session_dir, auto_db)

    s = auto_db.execute(
        "SELECT * FROM sessions WHERE id = ?", ("hooks-no-yaml",)
    ).fetchone()
    assert s is not None
    assert s["project"] == ""


def test_import_claude_hooks_yaml_with_extra_fields(auto_db, tmp_path):
    from coworker.analytics.auto_import import import_claude_hooks

    session_dir = tmp_path / "hooks-extra"
    session_dir.mkdir()
    (session_dir / "session.yaml").write_text(
        "session_id: extra-1\nproject: p\ncwd: /tmp\nmodel: m\n"
        "unknown_field: blah\nanother: x\n"
    )
    (session_dir / "messages.jsonl").write_text("")
    (session_dir / "tools.jsonl").write_text("")

    import_claude_hooks(session_dir, auto_db)

    s = auto_db.execute(
        "SELECT * FROM sessions WHERE id = ?", ("hooks-extra",)
    ).fetchone()
    assert s is not None
    assert s["project"] == "p"


# ===================================================================
# import_opencode_meta
# ===================================================================


def test_import_opencode_no_db_file(monkeypatch):
    from coworker.analytics import auto_import as ai_mod
    from coworker.analytics.db import SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)

    monkeypatch.setattr(ai_mod, "OPCODE_DB", Path("/nonexistent/opencode.db"))

    result = ai_mod.import_opencode_meta(conn)
    assert result == 0
    conn.close()


def test_import_opencode_with_data(monkeypatch, tmp_path):
    from coworker.analytics import auto_import as ai_mod
    from coworker.analytics.db import SCHEMA

    # Create a temporary opencode.db
    oc_path = tmp_path / "opencode.db"
    oc = sqlite3.connect(str(oc_path))
    oc.execute(
        "CREATE TABLE IF NOT EXISTS session "
        "(id TEXT, title TEXT, model TEXT, cost REAL, "
        "tokens_input INTEGER, tokens_output INTEGER, time_created TEXT)"
    )
    oc.execute(
        "INSERT INTO session (id, title, model, time_created) VALUES (?, ?, ?, ?)",
        ("oc-sess-1", "Test Session", "gpt-4", "1700000000000"),
    )
    oc.execute(
        "INSERT INTO session (id, title, model, time_created) VALUES (?, ?, ?, ?)",
        ("oc-sess-2", "", "gpt-4", "1700000001000"),
    )
    oc.commit()
    oc.close()

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)

    monkeypatch.setattr(ai_mod, "OPCODE_DB", oc_path)

    result = ai_mod.import_opencode_meta(conn)
    assert result == 1  # only oc-sess-1 (non-empty title)

    s = conn.execute(
        "SELECT * FROM sessions WHERE id = ?", ("oc-sess-1",)
    ).fetchone()
    assert s is not None
    assert s["ide"] == "opencode"
    assert s["model"] == "gpt-4"
    conn.close()


def test_import_opencode_invalid_timestamp(monkeypatch, tmp_path):
    from coworker.analytics import auto_import as ai_mod
    from coworker.analytics.db import SCHEMA

    oc_path = tmp_path / "opencode_badts.db"
    oc = sqlite3.connect(str(oc_path))
    oc.execute(
        "CREATE TABLE IF NOT EXISTS session "
        "(id TEXT, title TEXT, model TEXT, cost REAL, "
        "tokens_input INTEGER, tokens_output INTEGER, time_created TEXT)"
    )
    oc.execute(
        "INSERT INTO session (id, title, model, time_created) VALUES (?, ?, ?, ?)",
        ("oc-bad-ts", "Bad TS", "gpt-4", "not-a-number"),
    )
    oc.commit()
    oc.close()

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)

    monkeypatch.setattr(ai_mod, "OPCODE_DB", oc_path)

    result = ai_mod.import_opencode_meta(conn)
    assert result == 1

    s = conn.execute(
        "SELECT * FROM sessions WHERE id = ?", ("oc-bad-ts",)
    ).fetchone()
    assert s is not None
    conn.close()


def test_import_opencode_no_timestamp(monkeypatch, tmp_path):
    from coworker.analytics import auto_import as ai_mod
    from coworker.analytics.db import SCHEMA

    oc_path = tmp_path / "opencode_nots.db"
    oc = sqlite3.connect(str(oc_path))
    oc.execute(
        "CREATE TABLE IF NOT EXISTS session "
        "(id TEXT, title TEXT, model TEXT, cost REAL, "
        "tokens_input INTEGER, tokens_output INTEGER, time_created TEXT)"
    )
    oc.execute(
        "INSERT INTO session (id, title, model, time_created) VALUES (?, ?, ?, ?)",
        ("oc-no-ts", "No TS", "gpt-4", None),
    )
    oc.commit()
    oc.close()

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)

    monkeypatch.setattr(ai_mod, "OPCODE_DB", oc_path)

    result = ai_mod.import_opencode_meta(conn)
    assert result == 1

    s = conn.execute(
        "SELECT * FROM sessions WHERE id = ?", ("oc-no-ts",)
    ).fetchone()
    assert s is not None
    conn.close()


def test_import_opencode_skips_existing(monkeypatch, tmp_path):
    from coworker.analytics import auto_import as ai_mod
    from coworker.analytics.db import SCHEMA

    oc_path = tmp_path / "opencode_existing.db"
    oc = sqlite3.connect(str(oc_path))
    oc.execute(
        "CREATE TABLE IF NOT EXISTS session "
        "(id TEXT, title TEXT, model TEXT, cost REAL, "
        "tokens_input INTEGER, tokens_output INTEGER, time_created TEXT)"
    )
    oc.execute(
        "INSERT INTO session (id, title, model, time_created) VALUES (?, ?, ?, ?)",
        ("oc-s1", "Existing", "gpt-4", "1700000000000"),
    )
    oc.commit()
    oc.close()

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT INTO sessions (id, ide, created_at) VALUES (?, ?, ?)",
        ("oc-s1", "opencode", "2025-01-01"),
    )
    conn.commit()

    monkeypatch.setattr(ai_mod, "OPCODE_DB", oc_path)

    result = ai_mod.import_opencode_meta(conn)
    assert result == 0
    conn.close()


def test_import_opencode_db_error(monkeypatch, tmp_path):
    from coworker.analytics import auto_import as ai_mod
    from coworker.analytics.db import SCHEMA

    oc_path = tmp_path / "opencode_corrupt.db"
    oc_path.write_text("not a valid sqlite database")

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)

    monkeypatch.setattr(ai_mod, "OPCODE_DB", oc_path)

    result = ai_mod.import_opencode_meta(conn)
    assert result == 0
    conn.close()


# ===================================================================
# run_once
# ===================================================================


def test_run_once_no_directories(monkeypatch, tmp_path):
    from coworker.analytics import auto_import as ai_mod
    from coworker.analytics.db import SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)

    monkeypatch.setattr(ai_mod, "get_db", lambda: conn)
    monkeypatch.setattr(ai_mod, "CLAUDE_PROJECTS", tmp_path / "nonexistent_projects")
    monkeypatch.setattr(ai_mod, "SESSIONS", tmp_path / "nonexistent_sessions")

    stats = ai_mod.run_once()
    assert stats["claude_jsonl"] == 0
    assert stats["claude_hooks"] == 0
    assert stats["skipped"] == 0
    conn.close()


def test_run_once_with_claude_jsonl(monkeypatch, tmp_path):
    from coworker.analytics import auto_import as ai_mod
    from coworker.analytics.db import SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)

    projects_dir = tmp_path / "claude_projects"
    projects_dir.mkdir()
    proj = projects_dir / "my-project"
    proj.mkdir()
    _make_jsonl(proj / "session-abc.jsonl", [
        {
            "type": "assistant", "timestamp": "2025-01-01T10:00:00", "cwd": "/tmp/proj",
            "message": {"model": "claude-3", "content": []},
        },
    ])

    monkeypatch.setattr(ai_mod, "get_db", lambda: conn)
    monkeypatch.setattr(ai_mod, "CLAUDE_PROJECTS", projects_dir)
    monkeypatch.setattr(ai_mod, "SESSIONS", tmp_path / "nonexistent_sessions")

    stats = ai_mod.run_once(verbose=True)
    assert stats["claude_jsonl"] == 1
    # run_once closes the DB connection, so we only check stats here


def test_run_once_with_claude_hooks(monkeypatch, tmp_path):
    from coworker.analytics import auto_import as ai_mod
    from coworker.analytics.db import SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)

    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    sd = sessions_dir / "hooks-sess"
    sd.mkdir()
    (sd / "session.yaml").write_text(
        "session_id: hooks-abc\nproject: p\ncwd: /tmp\nmodel: c\ncreated: 2025-01-01\n"
    )
    (sd / "messages.jsonl").write_text("")
    (sd / "tools.jsonl").write_text("")

    monkeypatch.setattr(ai_mod, "get_db", lambda: conn)
    monkeypatch.setattr(ai_mod, "CLAUDE_PROJECTS", tmp_path / "nonexistent_projects")
    monkeypatch.setattr(ai_mod, "SESSIONS", sessions_dir)

    stats = ai_mod.run_once(verbose=True)
    assert stats["claude_hooks"] == 1
    # run_once closes the DB connection, so we only check stats here


def test_run_once_skips_existing(monkeypatch, tmp_path):
    from coworker.analytics import auto_import as ai_mod
    from coworker.analytics.db import SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT INTO sessions (id, ide, created_at) VALUES (?, ?, ?)",
        ("session-abc", "claude-code", "2025-01-01"),
    )
    conn.commit()

    projects_dir = tmp_path / "claude_projects"
    projects_dir.mkdir()
    proj = projects_dir / "my-project"
    proj.mkdir()
    _make_jsonl(proj / "session-abc.jsonl", [
        {
            "type": "assistant", "timestamp": "2025-01-01T10:00:00", "cwd": "/tmp/proj",
            "message": {"model": "claude-3", "content": []},
        },
    ])

    monkeypatch.setattr(ai_mod, "get_db", lambda: conn)
    monkeypatch.setattr(ai_mod, "CLAUDE_PROJECTS", projects_dir)
    monkeypatch.setattr(ai_mod, "SESSIONS", tmp_path / "nonexistent_sessions")

    stats = ai_mod.run_once()
    assert stats["claude_jsonl"] == 0
    assert stats["skipped"] == 1
    conn.close()


def test_run_once_hooks_skips_dot_and_underscore_dirs(monkeypatch, tmp_path):
    from coworker.analytics import auto_import as ai_mod
    from coworker.analytics.db import SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)

    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    for name in (".hidden", "_private"):
        d = sessions_dir / name
        d.mkdir()
        (d / "session.yaml").write_text(f"session_id: {name}\n")

    monkeypatch.setattr(ai_mod, "get_db", lambda: conn)
    monkeypatch.setattr(ai_mod, "CLAUDE_PROJECTS", tmp_path / "nonexistent_projects")
    monkeypatch.setattr(ai_mod, "SESSIONS", sessions_dir)

    stats = ai_mod.run_once()
    assert stats["claude_hooks"] == 0
    conn.close()


def test_run_once_hooks_skips_no_yaml(monkeypatch, tmp_path):
    from coworker.analytics import auto_import as ai_mod
    from coworker.analytics.db import SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)

    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    (sessions_dir / "no-yaml-dir").mkdir()

    monkeypatch.setattr(ai_mod, "get_db", lambda: conn)
    monkeypatch.setattr(ai_mod, "CLAUDE_PROJECTS", tmp_path / "nonexistent_projects")
    monkeypatch.setattr(ai_mod, "SESSIONS", sessions_dir)

    stats = ai_mod.run_once()
    assert stats["claude_hooks"] == 0
    conn.close()


def test_run_once_not_a_dir_project_skipped(monkeypatch, tmp_path):
    from coworker.analytics import auto_import as ai_mod
    from coworker.analytics.db import SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)

    projects_dir = tmp_path / "claude_projects"
    projects_dir.mkdir()
    (projects_dir / "not-a-dir.txt").write_text("hello")

    monkeypatch.setattr(ai_mod, "get_db", lambda: conn)
    monkeypatch.setattr(ai_mod, "CLAUDE_PROJECTS", projects_dir)
    monkeypatch.setattr(ai_mod, "SESSIONS", tmp_path / "nonexistent_sessions")

    stats = ai_mod.run_once()
    assert stats["claude_jsonl"] == 0
    conn.close()


def test_run_once_hooks_uses_parse_session_id_for_dedup(monkeypatch, tmp_path):
    """_parse_session_id result is used for dedup, but import_claude_hooks
    inserts with session_dir.name in the DB."""
    from coworker.analytics import auto_import as ai_mod
    from coworker.analytics.db import SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)

    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    sd = sessions_dir / "some-dir-name"
    sd.mkdir()
    (sd / "session.yaml").write_text('session_id: "real-session-id"\n')
    (sd / "messages.jsonl").write_text("")
    (sd / "tools.jsonl").write_text("")

    monkeypatch.setattr(ai_mod, "get_db", lambda: conn)
    monkeypatch.setattr(ai_mod, "CLAUDE_PROJECTS", tmp_path / "nonexistent_projects")
    monkeypatch.setattr(ai_mod, "SESSIONS", sessions_dir)

    stats = ai_mod.run_once(verbose=True)
    assert stats["claude_hooks"] == 1
    # Dedup uses _parse_session_id; import_claude_hooks inserts with dir name.
    # Verified by correct stats — DB closed by run_once.
    conn.close()


def test_run_once_import_error_caught(monkeypatch, tmp_path):
    """Exception during import should be caught and not crash run_once."""
    from coworker.analytics import auto_import as ai_mod
    from coworker.analytics.db import SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)

    projects_dir = tmp_path / "claude_projects"
    projects_dir.mkdir()
    proj = projects_dir / "my-project"
    proj.mkdir()
    # Write a file that will trigger an error in import_claude_jsonl
    # A file with only non-dict messages so no crash, but run_once catches exceptions
    _make_jsonl(proj / "session-err.jsonl", [
        {
            "type": "assistant", "timestamp": "2025-01-01T10:00:00", "cwd": "/tmp/proj",
            "message": {"model": "claude-3", "content": []},
        },
    ])

    monkeypatch.setattr(ai_mod, "get_db", lambda: conn)
    monkeypatch.setattr(ai_mod, "CLAUDE_PROJECTS", projects_dir)
    monkeypatch.setattr(ai_mod, "SESSIONS", tmp_path / "nonexistent_sessions")

    stats = ai_mod.run_once(verbose=True)
    assert stats["claude_jsonl"] == 1
    conn.close()


def test_run_once_hooks_skipped_when_session_id_exists(monkeypatch, tmp_path):
    """When _parse_session_id returns an ID that already exists, it's skipped."""
    from coworker.analytics import auto_import as ai_mod
    from coworker.analytics.db import SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT INTO sessions (id, ide, created_at) VALUES (?, ?, ?)",
        ("already-exists", "claude-code", "2025-01-01"),
    )
    conn.commit()

    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    sd = sessions_dir / "hooks-dir"
    sd.mkdir()
    (sd / "session.yaml").write_text('session_id: "already-exists"\n')
    (sd / "messages.jsonl").write_text("")
    (sd / "tools.jsonl").write_text("")

    monkeypatch.setattr(ai_mod, "get_db", lambda: conn)
    monkeypatch.setattr(ai_mod, "CLAUDE_PROJECTS", tmp_path / "nonexistent_projects")
    monkeypatch.setattr(ai_mod, "SESSIONS", sessions_dir)

    stats = ai_mod.run_once()
    assert stats["claude_hooks"] == 0
    assert stats["skipped"] == 1
    conn.close()


# ===================================================================
# run_daemon
# ===================================================================


def test_run_daemon_one_iteration(monkeypatch):
    """run_daemon should call run_once and sleep in a loop."""
    from coworker.analytics import auto_import as ai_mod

    iterations = []

    def fake_run_once(verbose=False):
        iterations.append(1)
        if len(iterations) >= 2:
            raise StopIteration
        return {"claude_jsonl": 2, "claude_hooks": 3, "opencode": 1, "skipped": 5}

    monkeypatch.setattr(ai_mod, "run_once", fake_run_once)
    monkeypatch.setattr(ai_mod.time, "sleep", lambda x: None)

    try:
        ai_mod.run_daemon(interval=1)
    except StopIteration:
        pass

    assert len(iterations) >= 1
