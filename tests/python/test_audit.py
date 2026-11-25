"""Tests for coworker.memory.audit — audit trail and gap detection."""

from __future__ import annotations

import pytest
from coworker.memory.audit import check_gaps, write_audit_record


class TestWriteAuditRecord:
    def test_write_creates_file(self, tmp_path):
        path = tmp_path / "audit.log"
        write_audit_record(str(path), "posttooluse", "sess_test_001", "Edit", lessons=2, ms=423, status="ok")
        assert path.exists()
        content = path.read_text()
        assert "sess_test_001" in content
        assert "tool=Edit" in content
        assert "lessons=2" in content
        assert "ms=423" in content
        assert "ok" in content

    def test_write_multiple_records(self, tmp_path):
        path = tmp_path / "audit.log"
        write_audit_record(str(path), "posttooluse", "sess_a", "Read", 0, 200, "ok")
        write_audit_record(str(path), "posttooluse", "sess_a", "Edit", 1, 350, "ok")
        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_write_with_subagent_trigger(self, tmp_path):
        path = tmp_path / "audit.log"
        write_audit_record(str(path), "subagentstop", "sess_x", "Agent", 3, 150, "ok")
        content = path.read_text()
        assert "subagentstop" in content

    def test_write_error_status(self, tmp_path):
        path = tmp_path / "audit.log"
        write_audit_record(str(path), "posttooluse", "sess_err", "Edit", 0, 500, "error")
        content = path.read_text()
        assert "error" in content

    def test_a_tilde_path_is_expanded(self, tmp_path, monkeypatch):
        """capture passes "~/.coworker/memory/", and Path() keeps the tilde.

        Every record then went to a literal `~` directory under the session's
        cwd instead of the user's home, which is how that path ended up
        committed in the repo.
        """
        monkeypatch.setenv("HOME", str(tmp_path))
        write_audit_record(
            "~/.coworker/memory/audit.log", "stop", "sess_tilde", "session-end", 0, 1, "ok"
        )
        written = tmp_path / ".coworker" / "memory" / "audit.log"
        assert written.exists()
        assert "sess_tilde" in written.read_text()


class TestCheckGaps:
    def test_no_file_returns_empty(self, tmp_path):
        gaps = check_gaps(str(tmp_path / "nonexistent.log"))
        assert gaps == []

    def test_single_record_no_gaps(self, tmp_path):
        path = tmp_path / "audit.log"
        write_audit_record(str(path), "posttooluse", "sess_test", "Read", 0, 200, "ok", ts="2026-07-25T10:00:00Z")
        gaps = check_gaps(str(path))
        assert gaps == []

    def test_small_gap_not_detected(self, tmp_path):
        path = tmp_path / "audit.log"
        write_audit_record(str(path), "posttooluse", "sess_test", "Read", 0, 200, "ok", ts="2026-07-25T10:00:00Z")
        write_audit_record(str(path), "posttooluse", "sess_test", "Edit", 1, 300, "ok", ts="2026-07-25T10:01:00Z")
        gaps = check_gaps(str(path), gap_threshold_minutes=5)
        assert gaps == []

    def test_large_gap_detected(self, tmp_path):
        path = tmp_path / "audit.log"
        write_audit_record(str(path), "posttooluse", "sess_test", "Read", 0, 200, "ok", ts="2026-07-25T10:00:00Z")
        write_audit_record(str(path), "posttooluse", "sess_test", "Edit", 1, 350, "ok", ts="2026-07-25T10:25:00Z")
        gaps = check_gaps(str(path), gap_threshold_minutes=5)
        assert len(gaps) == 1
        assert gaps[0]["session_id"] == "sess_test"
        assert gaps[0]["gap_minutes"] == 25.0

    def test_different_sessions_no_gap(self, tmp_path):
        """Inference: gap check only within same session."""
        path = tmp_path / "audit.log"
        write_audit_record(str(path), "posttooluse", "sess_a", "Read", 0, 200, "ok", ts="2026-07-25T10:00:00Z")
        write_audit_record(str(path), "posttooluse", "sess_b", "Edit", 1, 300, "ok", ts="2026-07-25T11:00:00Z")
        gaps = check_gaps(str(path))
        assert gaps == []

    def test_malformed_lines_skipped(self, tmp_path):
        path = tmp_path / "audit.log"
        path.write_text("garbage line\n")
        write_audit_record(str(path), "posttooluse", "sess_test", "Read", 0, 200, "ok", ts="2026-07-25T10:00:00Z")
        gaps = check_gaps(str(path))
        assert gaps == []


class TestRebuildIndex:
    """rebuild_index deletes every mem0 entry before rebuilding.

    It called get_transcript as a method on the connection, but that is a
    module-level function taking (conn, session_id) - so the first iteration
    raised AttributeError, after delete_all() had already wiped the index.
    """

    @pytest.fixture
    def db(self):
        import sqlite3

        from coworker.analytics.db import SCHEMA

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        conn.execute(
            "INSERT INTO sessions (id, ide, created_at) "
            "VALUES ('s1', 'claude', '2026-01-01')"
        )
        conn.execute(
            "INSERT INTO messages (session_id, seq, type, content, ts) "
            "VALUES ('s1', 1, 'user', 'hi', 't')"
        )
        conn.commit()
        return conn

    def test_does_not_raise(self, db):
        from coworker.memory.audit import rebuild_index

        class FakeMem0:
            def delete_all(self): pass

            def add(self, **kwargs): pass

        rebuild_index(db, FakeMem0())  # would raise AttributeError before

    def test_rebuilds_from_transcripts(self, db):
        from coworker.memory.audit import rebuild_index

        class FakeMem0:
            def __init__(self):
                self.deleted = False
                self.added = []

            def delete_all(self):
                self.deleted = True

            def add(self, **kwargs):
                self.added.append(kwargs)

        mem0 = FakeMem0()
        rebuild_index(db, mem0)

        assert mem0.deleted is True
        assert len(mem0.added) == 1, "the session was not re-indexed"
        assert mem0.added[0]["run_id"] == "s1"


class TestErrorReason:
    """An error record said only "error": the exception went to stderr, which
    the session-end hook discards, so ~40% of captures failed with no trace of
    why. The reason now rides on the same line."""

    def test_error_reason_on_one_line(self, tmp_path):
        path = tmp_path / "audit.log"
        write_audit_record(str(path), "stop", "s1", "session-end", 0, 9, "error",
                           reason='Unterminated string\nat "x"')
        line = path.read_text()
        assert line.count("\n") == 1
        assert line.rstrip().endswith('error reason="Unterminated string\\nat \\"x\\""')

    def test_reason_does_not_break_gap_detection(self, tmp_path):
        path = tmp_path / "audit.log"
        write_audit_record(str(path), "stop", "s1", "t", 0, 1, "error", ts="2026-01-01T00:00:00Z", reason="a b c")
        write_audit_record(str(path), "stop", "s1", "t", 0, 1, "ok", ts="2026-01-01T01:00:00Z")
        assert check_gaps(str(path))[0]["session_id"] == "s1"

    def test_ok_record_unchanged(self, tmp_path):
        path = tmp_path / "audit.log"
        write_audit_record(str(path), "stop", "s1", "t", 2, 5, "ok", ts="T")
        assert path.read_text() == "T sync stop s1 tool=t lessons=2 ms=5 ok\n"
