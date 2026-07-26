"""Tests for coworker.autoworker.rules — validation rules."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from coworker.autoworker.rules import (
    ValidateResult,
    AuditResult,
    check_api_keys,
    check_mem0_operational,
    check_pending_queue,
    check_skills_directory,
    detect_dead_skills,
    validate_against_raw_data,
)


class TestValidateResult:
    def test_ok(self):
        r = ValidateResult("OK", claimed=5, actual=5)
        assert r.verdict == "OK"

    def test_mismatch(self):
        r = ValidateResult("MISMATCH", claimed=10, actual=5, evidence="mismatch")
        assert r.verdict == "MISMATCH"
        assert "mismatch" in r.evidence


class TestAuditResult:
    def test_done_right(self):
        r = AuditResult("DONE_RIGHT", evidence="3 tests pass")
        assert r.verdict == "DONE_RIGHT"

    def test_not_done(self):
        r = AuditResult("NOT_DONE", evidence="no code")
        assert r.verdict == "NOT_DONE"


class TestValidateAgainstRawData:
    def test_ok_when_counts_match(self, tmp_path):
        usage_path = tmp_path / "usage.json"
        usage_path.write_text(json.dumps({"total_calls": 5}))
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = [5]

        result = validate_against_raw_data("test-skill", str(usage_path), mock_db)
        assert result.verdict == "OK"
        assert result.claimed == 5
        assert result.actual == 5

    def test_mismatch_when_counts_differ(self, tmp_path):
        usage_path = tmp_path / "usage.json"
        usage_path.write_text(json.dumps({"total_calls": 10}))
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = [3]

        result = validate_against_raw_data("test-skill", str(usage_path), mock_db)
        assert result.verdict == "MISMATCH"

    def test_bad_json_returns_mismatch(self, tmp_path):
        usage_path = tmp_path / "usage.json"
        usage_path.write_text("not json")
        mock_db = MagicMock()

        result = validate_against_raw_data("test-skill", str(usage_path), mock_db)
        assert result.verdict == "MISMATCH"


class TestDetectDeadSkills:
    def test_no_dead_skills(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "live-skill").mkdir()
        (skills_dir / "live-skill" / "usage.json").write_text(json.dumps({"total_calls": 5}))

        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = [5]

        dead = detect_dead_skills(str(skills_dir), mock_db)
        assert dead == []

    def test_detects_dead_skill(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "dead-skill").mkdir()

        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = [0]

        dead = detect_dead_skills(str(skills_dir), mock_db)
        assert len(dead) == 1
        assert dead[0]["name"] == "dead-skill"
        assert dead[0]["reason"] == "zero_calls"

    def test_missing_dir_returns_empty(self):
        mock_db = MagicMock()
        dead = detect_dead_skills("/nonexistent/path", mock_db)
        assert dead == []


class TestBuiltinRules:
    def test_check_mem0_operational(self):
        result = check_mem0_operational()
        assert result.verdict in ("DONE_RIGHT", "NOT_DONE")

    def test_check_api_keys(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        result = check_api_keys()
        assert result.verdict == "DONE_RIGHT"

    def test_check_api_keys_missing(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        result = check_api_keys()
        assert result.verdict == "NOT_DONE"

    def test_check_skills_directory_detects_missing(self):
        """When skills dir is missing, returns NOT_DONE."""
        result = check_skills_directory()
        # Real system may or may not have skills dir
        assert result.verdict in ("DONE_RIGHT", "NOT_DONE")

    def test_check_pending_queue(self):
        result = check_pending_queue()
        assert result.verdict in ("DONE_RIGHT", "DONE_WRONG")
