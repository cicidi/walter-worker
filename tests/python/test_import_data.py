"""Tests for analytics/import_data.py — session import from hooks directories."""
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
def import_db(monkeypatch):
    """In-memory SQLite with full schema, patched get_db."""
    from coworker.analytics import import_data as id_mod
    from coworker.analytics.db import SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    monkeypatch.setattr(id_mod, "get_db", lambda _path=None: conn)
    yield conn
    conn.close()


# ===================================================================
# parse_session_yaml
# ===================================================================


def test_parse_session_yaml_basic(tmp_path):
    from coworker.analytics.import_data import parse_session_yaml

    d = tmp_path / "sess"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "abc-123"\nproject: my-proj\ncwd: /tmp/proj\n'
        "model: claude-3\ninitiative: my-init\nbranch: feat/x\n"
        "created: 2025-01-01T10:00:00\nclosed: 2025-01-01T10:30:00\n"
    )
    data = parse_session_yaml(d)
    assert data["session_id"] == "abc-123"
    assert data["project"] == "my-proj"
    assert data["cwd"] == "/tmp/proj"
    assert data["model"] == "claude-3"
    assert data["initiative"] == "my-init"
    assert data["branch"] == "feat/x"
    assert data["created"] == "2025-01-01T10:00:00"
    assert data["closed"] == "2025-01-01T10:30:00"


def test_parse_session_yaml_file_not_exists(tmp_path):
    from coworker.analytics.import_data import parse_session_yaml

    d = tmp_path / "no-yaml"
    d.mkdir()
    assert parse_session_yaml(d) == {}


def test_parse_session_yaml_empty_file(tmp_path):
    from coworker.analytics.import_data import parse_session_yaml

    d = tmp_path / "empty-yaml"
    d.mkdir()
    (d / "session.yaml").write_text("")
    assert parse_session_yaml(d) == {}


def test_parse_session_yaml_no_colon_lines(tmp_path):
    from coworker.analytics.import_data import parse_session_yaml

    d = tmp_path / "bad-yaml"
    d.mkdir()
    (d / "session.yaml").write_text("this line has no colon\nneither does this\n")
    assert parse_session_yaml(d) == {}


# ===================================================================
# import_session
# ===================================================================


def test_import_session_basic(import_db, tmp_path):
    """Import a complete session with messages, tools, and skills."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess1"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-001"\nproject: my-proj\ncwd: /tmp/proj\n'
        "model: claude-3\ninitiative: my-init\nbranch: feat/x\n"
        "created: 2025-01-01T10:00:00\nclosed: 2025-01-01T10:30:00\n"
    )
    _make_jsonl(d / "messages.jsonl", [
        {"seq": 1, "type": "user", "content": "hello", "ts": "2025-01-01T10:00:00"},
        {"seq": 2, "type": "assistant", "content": "hi there", "ts": "2025-01-01T10:00:05"},
    ])
    _make_jsonl(d / "tools.jsonl", [
        {
            "call_id": "call-1", "tool": "Read", "tool_type": "builtin",
            "phase": "before", "seq": 1,
            "args": {"file_path": "/tmp/test.py"},
            "ts": "2025-01-01T10:00:01",
        },
        {
            "call_id": "call-1", "tool": "Read", "tool_type": "builtin",
            "phase": "after", "seq": 2,
            "result": "content here", "duration_ms": 150,
            "ts": "2025-01-01T10:00:02",
        },
    ])

    import_session(d, import_db)

    # session
    s = import_db.execute(
        "SELECT * FROM sessions WHERE id = ?", ("sess-001",)
    ).fetchone()
    assert s is not None
    assert s["project"] == "my-proj"
    assert s["cwd"] == "/tmp/proj"
    assert s["model"] == "claude-3"
    assert s["initiative"] == "my-init"
    assert s["branch"] == "feat/x"
    assert s["created_at"] == "2025-01-01T10:00:00"
    assert s["closed_at"] == "2025-01-01T10:30:00"

    # messages
    msgs = import_db.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY seq", ("sess-001",)
    ).fetchall()
    assert len(msgs) == 2
    assert msgs[0]["type"] == "user"
    assert msgs[0]["content"] == "hello"
    assert msgs[1]["type"] == "assistant"

    # tool_calls
    tc = import_db.execute(
        "SELECT * FROM tool_calls WHERE session_id = ?", ("sess-001",)
    ).fetchall()
    assert len(tc) == 1
    assert tc[0]["tool"] == "Read"
    assert tc[0]["tool_type"] == "builtin"
    assert tc[0]["result"] == "content here"
    assert tc[0]["duration_ms"] == 150

    # file_ops
    fo = import_db.execute(
        "SELECT * FROM file_ops WHERE session_id = ?", ("sess-001",)
    ).fetchall()
    assert len(fo) == 1
    assert fo[0]["op"] == "read"
    assert fo[0]["path"] == "/tmp/test.py"
    assert fo[0]["file_type"] == "py"

    # stats
    stats = import_db.execute(
        "SELECT * FROM session_stats WHERE session_id = ?", ("sess-001",)
    ).fetchone()
    assert stats is not None
    assert stats["message_count"] == 2
    assert stats["tool_count"] == 1
    assert stats["skill_count"] == 0
    assert stats["read_count"] == 1
    assert stats["write_count"] == 0
    assert stats["bash_count"] == 0
    assert stats["duration_min"] == 30


def test_import_session_no_yaml(import_db, tmp_path):
    """Session without session.yaml — uses directory name as session_id."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "dir-name-sess"
    d.mkdir()

    import_session(d, import_db)

    s = import_db.execute(
        "SELECT * FROM sessions WHERE id = ?", ("dir-name-sess",)
    ).fetchone()
    assert s is not None


def test_import_session_with_empty_messages_empty_tools(import_db, tmp_path):
    """Empty messages and tools files should not crash."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess-empty-files"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-empty"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )
    (d / "messages.jsonl").write_text("")
    (d / "tools.jsonl").write_text("")

    import_session(d, import_db)

    stats = import_db.execute(
        "SELECT * FROM session_stats WHERE session_id = ?", ("sess-empty",)
    ).fetchone()
    assert stats is not None
    assert stats["message_count"] == 0
    assert stats["tool_count"] == 0


def test_import_session_no_message_or_tool_files(import_db, tmp_path):
    """Session without messages.jsonl or tools.jsonl should not crash."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess-no-files"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-no-files"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )

    import_session(d, import_db)

    s = import_db.execute(
        "SELECT * FROM sessions WHERE id = ?", ("sess-no-files",)
    ).fetchone()
    assert s is not None

    stats = import_db.execute(
        "SELECT * FROM session_stats WHERE session_id = ?", ("sess-no-files",)
    ).fetchone()
    assert stats["message_count"] == 0
    assert stats["tool_count"] == 0


def test_import_session_with_bad_json_messages(import_db, tmp_path):
    """Messages with bad JSON lines should be skipped."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess-bad-msg"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-bad-msg"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )
    (d / "messages.jsonl").write_text(
        "not valid json\n"
        + json.dumps({"seq": 1, "type": "user", "content": "hello", "ts": "2025-01-01T10:00:00"})
        + "\n"
    )
    # Also provide tools.jsonl to avoid the UnboundLocalError path
    (d / "tools.jsonl").write_text("")

    import_session(d, import_db)

    msgs = import_db.execute(
        "SELECT * FROM messages WHERE session_id = ?", ("sess-bad-msg",)
    ).fetchall()
    assert len(msgs) == 1  # only the valid line


def test_import_session_with_bad_json_tools(import_db, tmp_path):
    """Tools with bad JSON lines should be skipped."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess-bad-tool"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-bad-tool"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )
    (d / "tools.jsonl").write_text(
        "bad json\n"
        + json.dumps({
            "call_id": "c1", "tool": "Read", "tool_type": "builtin",
            "phase": "before", "seq": 1,
            "args": {"file_path": "/tmp/x.py"},
            "ts": "2025-01-01T10:00:01",
        })
        + "\n"
    )

    import_session(d, import_db)

    tc = import_db.execute(
        "SELECT * FROM tool_calls WHERE session_id = ?", ("sess-bad-tool",)
    ).fetchall()
    assert len(tc) == 1


def test_import_session_blank_lines_skipped(import_db, tmp_path):
    """Blank lines in messages and tools files should be skipped."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess-blank"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-blank"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )
    (d / "messages.jsonl").write_text(
        "\n"
        + json.dumps({"seq": 1, "type": "user", "content": "hello", "ts": "2025-01-01T10:00:00"})
        + "\n\n"
    )
    (d / "tools.jsonl").write_text(
        "\n"
        + json.dumps({
            "call_id": "c1", "tool": "Read", "tool_type": "builtin",
            "phase": "before", "seq": 1,
            "args": {"file_path": "/tmp/x.py"},
            "ts": "2025-01-01T10:00:01",
        })
        + "\n  \n"
    )

    import_session(d, import_db)

    msgs = import_db.execute(
        "SELECT * FROM messages WHERE session_id = ?", ("sess-blank",)
    ).fetchall()
    assert len(msgs) == 1

    tc = import_db.execute(
        "SELECT * FROM tool_calls WHERE session_id = ?", ("sess-blank",)
    ).fetchall()
    assert len(tc) == 1


def test_import_session_file_ops_with_different_keys(import_db, tmp_path):
    """File ops with filePath and path keys."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess-file-keys"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-file-keys"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )
    _make_jsonl(d / "tools.jsonl", [
        {
            "call_id": "c1", "tool": "Read", "tool_type": "builtin",
            "phase": "before", "seq": 1,
            "args": {"filePath": "/tmp/camel.py"},
            "ts": "2025-01-01T10:00:01",
        },
        {
            "call_id": "c1", "tool": "Read", "tool_type": "builtin",
            "phase": "after", "seq": 2,
            "result": "ok", "ts": "2025-01-01T10:00:02",
        },
        {
            "call_id": "c2", "tool": "Write", "tool_type": "builtin",
            "phase": "before", "seq": 3,
            "args": {"path": "/tmp/snake.py"},
            "ts": "2025-01-01T10:00:03",
        },
        {
            "call_id": "c2", "tool": "Write", "tool_type": "builtin",
            "phase": "after", "seq": 4,
            "result": "ok", "ts": "2025-01-01T10:00:04",
        },
    ])

    import_session(d, import_db)

    file_ops = import_db.execute(
        "SELECT * FROM file_ops WHERE session_id = ? ORDER BY seq",
        ("sess-file-keys",),
    ).fetchall()
    assert len(file_ops) == 2
    assert file_ops[0]["path"] == "/tmp/camel.py"
    assert file_ops[0]["op"] == "read"
    assert file_ops[1]["path"] == "/tmp/snake.py"
    assert file_ops[1]["op"] == "write"


def test_import_session_with_edit_and_glob_ops(import_db, tmp_path):
    """Edit and Glob operations should create file_ops entries."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess-edit-glob"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-eg"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )
    _make_jsonl(d / "tools.jsonl", [
        {
            "call_id": "c-edit", "tool": "Edit", "tool_type": "builtin",
            "phase": "before", "seq": 1,
            "args": {"file_path": "/tmp/edit.py"},
            "ts": "2025-01-01T10:00:01",
        },
        {
            "call_id": "c-edit", "tool": "Edit", "tool_type": "builtin",
            "phase": "after", "seq": 2,
            "result": "ok", "ts": "2025-01-01T10:00:02",
        },
        {
            "call_id": "c-glob", "tool": "Glob", "tool_type": "builtin",
            "phase": "before", "seq": 3,
            "args": {"file_path": "/tmp/*.py"},
            "ts": "2025-01-01T10:00:03",
        },
        {
            "call_id": "c-glob", "tool": "Glob", "tool_type": "builtin",
            "phase": "after", "seq": 4,
            "result": "ok", "ts": "2025-01-01T10:00:04",
        },
    ])

    import_session(d, import_db)

    file_ops = import_db.execute(
        "SELECT op FROM file_ops WHERE session_id = ? ORDER BY seq",
        ("sess-eg",),
    ).fetchall()
    ops = [r["op"] for r in file_ops]
    assert "edit" in ops
    assert "glob" in ops

    stats = import_db.execute(
        "SELECT * FROM session_stats WHERE session_id = ?", ("sess-eg",)
    ).fetchone()
    # Glob has op='glob', not 'read' — only Read counts as read
    assert stats["read_count"] == 0
    assert stats["write_count"] == 1  # Edit counts as write
    # tool_count counts total tool calls in tool_calls table
    assert stats["tool_count"] == 2  # 2 unique call_ids (c-edit, c-glob)


def test_import_session_with_skill_calls(import_db, tmp_path):
    """Skill invocations should increment skills table."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess-skills"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-skills"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )
    _make_jsonl(d / "tools.jsonl", [
        {
            "call_id": "c1", "tool": "Skill", "tool_type": "api",
            "phase": "before", "seq": 1,
            "args": {"name": "my-skill"},
            "ts": "2025-01-01T10:00:01",
        },
        {
            "call_id": "c1", "tool": "Skill", "tool_type": "api",
            "phase": "after", "seq": 2,
            "result": "done", "ts": "2025-01-01T10:00:02",
        },
        {
            "call_id": "c2", "tool": "Skill", "tool_type": "api",
            "phase": "before", "seq": 3,
            "args": {"name": "other-skill"},
            "ts": "2025-01-01T10:00:03",
        },
        {
            "call_id": "c2", "tool": "Skill", "tool_type": "api",
            "phase": "after", "seq": 4,
            "result": "done", "ts": "2025-01-01T10:00:04",
        },
    ])

    import_session(d, import_db)

    # skills table
    skills = import_db.execute("SELECT * FROM skills ORDER BY name").fetchall()
    assert len(skills) == 2
    names = {r["name"] for r in skills}
    assert names == {"my-skill", "other-skill"}
    for s_row in skills:
        assert s_row["total_calls"] == 1

    # stats skill_count
    stats = import_db.execute(
        "SELECT * FROM session_stats WHERE session_id = ?", ("sess-skills",)
    ).fetchone()
    assert stats["skill_count"] == 2


def test_import_session_skill_args_as_json_string(import_db, tmp_path):
    """Skill args may be a JSON string instead of a dict."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess-skill-str"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-skill-str"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )
    _make_jsonl(d / "tools.jsonl", [
        {
            "call_id": "c1", "tool": "Skill", "tool_type": "api",
            "phase": "before", "seq": 1,
            "args": json.dumps({"name": "json-string-skill"}),
            "ts": "2025-01-01T10:00:01",
        },
        {
            "call_id": "c1", "tool": "Skill", "tool_type": "api",
            "phase": "after", "seq": 2,
            "result": "ok", "ts": "2025-01-01T10:00:02",
        },
    ])

    import_session(d, import_db)

    skill = import_db.execute(
        "SELECT * FROM skills WHERE name = ?", ("json-string-skill",)
    ).fetchone()
    assert skill is not None
    assert skill["total_calls"] == 1


def test_import_session_skill_args_bad_json_string(import_db, tmp_path):
    """Bad JSON string in skill args should be handled gracefully."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess-skill-bad"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-skill-bad"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )
    _make_jsonl(d / "tools.jsonl", [
        {
            "call_id": "c1", "tool": "Skill", "tool_type": "api",
            "phase": "before", "seq": 1,
            "args": "not valid json for skill",
            "ts": "2025-01-01T10:00:01",
        },
        {
            "call_id": "c1", "tool": "Skill", "tool_type": "api",
            "phase": "after", "seq": 2,
            "result": "ok", "ts": "2025-01-01T10:00:02",
        },
    ])

    import_session(d, import_db)

    # Should not crash — no skill should be added
    skills = import_db.execute("SELECT * FROM skills").fetchall()
    assert len(skills) == 0


def test_import_session_file_op_args_as_json_string(import_db, tmp_path):
    """File op args as a JSON string should be parsed."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess-fo-str"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-fo-str"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )
    _make_jsonl(d / "tools.jsonl", [
        {
            "call_id": "c1", "tool": "Read", "tool_type": "builtin",
            "phase": "before", "seq": 1,
            "args": json.dumps({"file_path": "/tmp/from-string.py"}),
            "ts": "2025-01-01T10:00:01",
        },
        {
            "call_id": "c1", "tool": "Read", "tool_type": "builtin",
            "phase": "after", "seq": 2,
            "result": "ok", "ts": "2025-01-01T10:00:02",
        },
    ])

    import_session(d, import_db)

    fo = import_db.execute(
        "SELECT * FROM file_ops WHERE session_id = ?", ("sess-fo-str",)
    ).fetchone()
    assert fo is not None
    assert fo["path"] == "/tmp/from-string.py"


def test_import_session_file_op_bad_json_string(import_db, tmp_path):
    """Bad JSON string for file op args should be handled gracefully."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess-fo-bad"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-fo-bad"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )
    _make_jsonl(d / "tools.jsonl", [
        {
            "call_id": "c1", "tool": "Read", "tool_type": "builtin",
            "phase": "before", "seq": 1,
            "args": "this is not json",
            "ts": "2025-01-01T10:00:01",
        },
        {
            "call_id": "c1", "tool": "Read", "tool_type": "builtin",
            "phase": "after", "seq": 2,
            "result": "ok", "ts": "2025-01-01T10:00:02",
        },
    ])

    import_session(d, import_db)

    # Should not crash — no file_op with empty path is inserted
    file_ops = import_db.execute(
        "SELECT * FROM file_ops WHERE session_id = ?", ("sess-fo-bad",)
    ).fetchall()
    assert len(file_ops) == 0


def test_import_session_duration_invalid_timestamps(import_db, tmp_path):
    """Invalid created/closed timestamps should not crash duration calc."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess-bad-ts"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-bad-ts"\nproject: p\n'
        "created: not-a-date\nclosed: also-not-a-date\n"
    )

    import_session(d, import_db)

    stats = import_db.execute(
        "SELECT * FROM session_stats WHERE session_id = ?", ("sess-bad-ts",)
    ).fetchone()
    assert stats is not None
    assert stats["duration_min"] is None


def test_import_session_duration_missing_closed(import_db, tmp_path):
    """Missing closed_at should give None duration."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess-no-closed"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-no-closed"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )

    import_session(d, import_db)

    stats = import_db.execute(
        "SELECT * FROM session_stats WHERE session_id = ?", ("sess-no-closed",)
    ).fetchone()
    assert stats["duration_min"] is None


def test_import_session_with_bash_tool(import_db, tmp_path):
    """Bash tool calls should be counted in bash_count."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess-bash"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-bash"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )
    _make_jsonl(d / "tools.jsonl", [
        {
            "call_id": "c1", "tool": "Bash", "tool_type": "builtin",
            "phase": "before", "seq": 1,
            "args": {"command": "ls"},
            "ts": "2025-01-01T10:00:01",
        },
        {
            "call_id": "c1", "tool": "Bash", "tool_type": "builtin",
            "phase": "after", "seq": 2,
            "result": "file list", "ts": "2025-01-01T10:00:02",
        },
    ])

    import_session(d, import_db)

    stats = import_db.execute(
        "SELECT * FROM session_stats WHERE session_id = ?", ("sess-bash",)
    ).fetchone()
    assert stats["bash_count"] == 1
    assert stats["tool_count"] == 1


def test_import_session_missing_args_handled(import_db, tmp_path):
    """Tool calls with no args should be handled gracefully."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess-no-args"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-no-args"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )
    _make_jsonl(d / "tools.jsonl", [
        {
            "call_id": "c1", "tool": "Read", "tool_type": "builtin",
            "phase": "before", "seq": 1,
            # No 'args' key at all
            "ts": "2025-01-01T10:00:01",
        },
        {
            "call_id": "c1", "tool": "Read", "tool_type": "builtin",
            "phase": "after", "seq": 2,
            "result": "ok", "ts": "2025-01-01T10:00:02",
        },
    ])

    import_session(d, import_db)

    # No file_op because Read has no args at all
    file_ops = import_db.execute(
        "SELECT * FROM file_ops WHERE session_id = ?", ("sess-no-args",)
    ).fetchall()
    assert len(file_ops) == 0


def test_import_session_post_has_no_args(import_db, tmp_path):
    """Post-phase only tool call; no args, so no file_op."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess-post-only"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-post-only"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )
    _make_jsonl(d / "tools.jsonl", [
        {
            "call_id": "call-only-post", "tool": "Read", "tool_type": "builtin",
            "phase": "after", "seq": 2,
            "result": "ok", "ts": "2025-01-01T10:00:02",
        },
    ])

    import_session(d, import_db)

    # Tool call from post phase uses post.get("tool") etc.
    tc = import_db.execute(
        "SELECT * FROM tool_calls WHERE session_id = ?", ("sess-post-only",)
    ).fetchone()
    assert tc is not None
    assert tc["tool"] == "Read"

    # No file_op because post phase has no args, and pre is empty
    file_ops = import_db.execute(
        "SELECT * FROM file_ops WHERE session_id = ?", ("sess-post-only",)
    ).fetchall()
    assert len(file_ops) == 0


def test_import_session_tool_no_phase(import_db, tmp_path):
    """Tool call without a phase field is not added to pre_calls or post_calls,
    so it won't appear in all_call_ids. It's effectively skipped."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess-no-phase"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-no-phase"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )
    _make_jsonl(d / "tools.jsonl", [
        {
            "call_id": "c1", "tool": "Read", "tool_type": "builtin",
            "seq": 1,
            "args": {"filePath": "/tmp/nop.py"},
            "ts": "2025-01-01T10:00:01",
        },
    ])

    import_session(d, import_db)

    # No phase → not added to pre_calls or post_calls → not in all_call_ids
    tc_count = import_db.execute(
        "SELECT COUNT(*) FROM tool_calls WHERE session_id = ?", ("sess-no-phase",)
    ).fetchone()[0]
    assert tc_count == 0


# ===================================================================
# import_all
# ===================================================================


def test_import_all_no_sessions_dir(monkeypatch, tmp_path, capsys):
    """When SESSIONS directory does not exist, print message and return."""
    from coworker.analytics import import_data as id_mod
    from coworker.analytics.db import SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    monkeypatch.setattr(id_mod, "get_db", lambda _path=None: conn)
    monkeypatch.setattr(id_mod, "SESSIONS", tmp_path / "nonexistent_sessions")

    id_mod.import_all()
    captured = capsys.readouterr()
    assert "No sessions directory found" in captured.out
    conn.close()


def test_import_all_with_sessions(monkeypatch, tmp_path, capsys):
    from coworker.analytics import import_data as id_mod
    from coworker.analytics.db import SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    monkeypatch.setattr(id_mod, "get_db", lambda _path=None: conn)

    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    d = sessions_dir / "sess-a"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-a"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )

    monkeypatch.setattr(id_mod, "SESSIONS", sessions_dir)

    id_mod.import_all()
    captured = capsys.readouterr()
    assert "Importing sess-a" in captured.out
    assert "Done." in captured.out
    # import_all closes the connection internally


def test_import_all_skips_dot_dirs(monkeypatch, tmp_path, capsys):
    from coworker.analytics import import_data as id_mod
    from coworker.analytics.db import SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    monkeypatch.setattr(id_mod, "get_db", lambda _path=None: conn)

    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    dot_dir = sessions_dir / ".hidden-sess"
    dot_dir.mkdir()
    (dot_dir / "session.yaml").write_text(
        'session_id: "hidden"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )

    monkeypatch.setattr(id_mod, "SESSIONS", sessions_dir)

    id_mod.import_all()
    captured = capsys.readouterr()
    assert "Done." in captured.out
    # Hidden directory should be skipped — no "Importing" for it
    assert "Importing .hidden-sess" not in captured.out


def test_import_all_skips_no_yaml(monkeypatch, tmp_path, capsys):
    from coworker.analytics import import_data as id_mod
    from coworker.analytics.db import SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    monkeypatch.setattr(id_mod, "get_db", lambda _path=None: conn)

    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    no_yaml = sessions_dir / "no-yaml-dir"
    no_yaml.mkdir()

    monkeypatch.setattr(id_mod, "SESSIONS", sessions_dir)

    id_mod.import_all()
    captured = capsys.readouterr()
    assert "Done." in captured.out
    # No yaml → not imported → no "Importing" for this dir
    assert "Importing no-yaml-dir" not in captured.out


def test_import_all_skips_files_not_dirs(monkeypatch, tmp_path, capsys):
    from coworker.analytics import import_data as id_mod
    from coworker.analytics.db import SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    monkeypatch.setattr(id_mod, "get_db", lambda _path=None: conn)

    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    (sessions_dir / "not-a-dir.txt").write_text("hello")

    monkeypatch.setattr(id_mod, "SESSIONS", sessions_dir)

    id_mod.import_all()
    captured = capsys.readouterr()
    assert "Done." in captured.out
    # import_all closes the connection internally


def test_import_all_multiple_sessions(monkeypatch, tmp_path, capsys):
    from coworker.analytics import import_data as id_mod
    from coworker.analytics.db import SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    monkeypatch.setattr(id_mod, "get_db", lambda _path=None: conn)

    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    for name in ("sess-1", "sess-2", "sess-3"):
        d = sessions_dir / name
        d.mkdir()
        (d / "session.yaml").write_text(
            f'session_id: "{name}"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
        )

    monkeypatch.setattr(id_mod, "SESSIONS", sessions_dir)

    id_mod.import_all()
    captured = capsys.readouterr()
    assert "Importing sess-1" in captured.out
    assert "Importing sess-2" in captured.out
    assert "Importing sess-3" in captured.out
    assert "Done." in captured.out


def test_import_session_with_ide_field(import_db, tmp_path):
    """Session yaml with an 'ide' field."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess-ide"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-ide"\nide: claude-code\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )

    import_session(d, import_db)

    s = import_db.execute(
        "SELECT * FROM sessions WHERE id = ?", ("sess-ide",)
    ).fetchone()
    assert s is not None
    assert s["ide"] == "claude-code"


def test_import_session_message_without_all_fields(import_db, tmp_path):
    """Messages missing some fields should still be inserted with defaults."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess-partial-msg"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-partial-msg"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )
    _make_jsonl(d / "messages.jsonl", [
        {"seq": 1, "type": "user"},  # no content, no ts
    ])

    import_session(d, import_db)

    msg = import_db.execute(
        "SELECT * FROM messages WHERE session_id = ?", ("sess-partial-msg",)
    ).fetchone()
    assert msg is not None
    assert msg["type"] == "user"
    assert msg["content"] == ""
    assert msg["ts"] == ""


def test_import_session_pre_and_post_merge(import_db, tmp_path):
    """Pre-phase tool call provides args, post-phase provides result/duration."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess-merged"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-merged"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )
    _make_jsonl(d / "tools.jsonl", [
        {
            "call_id": "c-merged", "tool": "Bash", "tool_type": "builtin",
            "server_name": "test-server",
            "phase": "before", "seq": 1,
            "args": {"command": "pytest"},
            "ts": "2025-01-01T10:00:01",
        },
        {
            "call_id": "c-merged", "tool": "Bash", "tool_type": "builtin",
            "server_name": "test-server",
            "phase": "after", "seq": 2,
            "result": "10 passed", "duration_ms": 5000,
            "ts": "2025-01-01T10:00:06",
        },
    ])

    import_session(d, import_db)

    tc = import_db.execute(
        "SELECT * FROM tool_calls WHERE session_id = ?", ("sess-merged",)
    ).fetchone()
    assert tc is not None
    assert tc["tool"] == "Bash"
    assert tc["tool_type"] == "builtin"
    assert tc["server_name"] == "test-server"
    assert tc["result"] == "10 passed"
    assert tc["duration_ms"] == 5000
    assert tc["seq_before"] == 1
    assert tc["seq_after"] == 2
    assert tc["ts"] == "2025-01-01T10:00:01"  # pre-phase ts

    args = json.loads(tc["args"])
    assert args["command"] == "pytest"


def test_import_session_multiple_skill_calls_same_name(import_db, tmp_path):
    """Multiple calls to the same skill: total_calls incremented once per
    unique skill name (skill_names is a set, not a counter of invocations)."""
    from coworker.analytics.import_data import import_session

    d = tmp_path / "sess-multi-skill"
    d.mkdir()
    (d / "session.yaml").write_text(
        'session_id: "sess-multi-skill"\nproject: p\ncreated: 2025-01-01T10:00:00\n'
    )
    _make_jsonl(d / "tools.jsonl", [
        {
            "call_id": "c1", "tool": "Skill", "tool_type": "api",
            "phase": "before", "seq": 1,
            "args": {"name": "repeat-skill"},
            "ts": "2025-01-01T10:00:01",
        },
        {
            "call_id": "c1", "tool": "Skill", "tool_type": "api",
            "phase": "after", "seq": 2,
            "result": "ok", "ts": "2025-01-01T10:00:02",
        },
        {
            "call_id": "c2", "tool": "Skill", "tool_type": "api",
            "phase": "before", "seq": 3,
            "args": {"name": "repeat-skill"},
            "ts": "2025-01-01T10:00:03",
        },
        {
            "call_id": "c2", "tool": "Skill", "tool_type": "api",
            "phase": "after", "seq": 4,
            "result": "ok", "ts": "2025-01-01T10:00:04",
        },
    ])

    import_session(d, import_db)

    skill = import_db.execute(
        "SELECT * FROM skills WHERE name = ?", ("repeat-skill",)
    ).fetchone()
    assert skill is not None
    # skill_names is a set, so total_calls is incremented once for this name
    assert skill["total_calls"] == 1
