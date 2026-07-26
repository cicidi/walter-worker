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
