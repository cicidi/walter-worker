"""Tests for coworker.autoworker.rules — spec §12.3 validation rules."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from coworker.autoworker.rules import (
    ContextLoader,
    DeadCodeDetector,
    Finding,
    GapCheck,
    RequirementAuditor,
    ResearchAdvisor,
    StateFile,
    VisionCheck,
)


class TestFinding:
    def test_create(self):
        f = Finding("R1", "test", "DONE_RIGHT", "source", "evidence", "skip")
        assert f.rule_id == "R1"
        assert f.verdict == "DONE_RIGHT"


class TestGapCheck:
    def test_ok_when_counts_match(self, tmp_path):
        usage_path = tmp_path / "usage.json"
        usage_path.write_text(json.dumps({"total_calls": 5}))
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = [5]
        f = GapCheck.verify(mock_db, "test-skill", str(usage_path))
        assert f.verdict == "DONE_RIGHT"

    def test_mismatch(self, tmp_path):
        usage_path = tmp_path / "usage.json"
        usage_path.write_text(json.dumps({"total_calls": 10}))
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = [3]
        f = GapCheck.verify(mock_db, "test-skill", str(usage_path))
        assert f.verdict == "MISMATCH"
        assert f.action == "fix"


class TestDeadCodeDetector:
    def test_finds_dead_skill(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "dead-skill").mkdir()
        mock_db = MagicMock()
        mock_db.execute.return_value.fetchone.return_value = [0]
        findings = DeadCodeDetector.scan_skills(str(skills_dir), mock_db)
        assert len(findings) == 1
        assert findings[0].rule_id == "R2"


class TestRequirementAuditor:
    def test_no_code_found(self):
        f = RequirementAuditor.audit("nonexistent_function_xyz", "", grep_dir="/tmp/nonexistent")
        assert f.verdict == "NOT_DONE"


class TestVisionCheck:
    def test_evaluate_skip(self):
        mock_llm = MagicMock()
        mock_llm.chat.return_value.content = json.dumps({"verdict": "skip", "reason": "Not aligned"})
        f = VisionCheck.evaluate(mock_llm, "Remove all tests")
        assert f.action == "skip"


class TestResearchAdvisor:
    def test_advise(self):
        mock_llm = MagicMock()
        mock_llm.chat.return_value.content = json.dumps({"action": "fix", "rationale": "Worth doing"})
        f = ResearchAdvisor.advise(mock_llm, "Add logging")
        assert f.rule_id == "R6"


class TestContextLoader:
    def test_empty_project(self, tmp_path):
        ctx = ContextLoader.load(str(tmp_path))
        assert ctx["prd_items"] == []

    def test_loads_spec_sections(self, tmp_path):
        base = tmp_path / "docs" / "self-evolving-agent" / "spec"
        base.mkdir(parents=True)
        (base / "self-evolving-agent-spec.md").write_text("## §1 Test\n## §2 Memory\ncontent")
        ctx = ContextLoader.load(str(tmp_path))
        assert len(ctx["spec_sections"]) == 2


class TestStateFile:
    def test_mark_and_check(self, tmp_path):
        sf = StateFile(str(tmp_path / "state.md"))
        assert sf.has_been_checked("C-1") is False
        sf.mark_checked("C-1", "test item", "grep", "DONE_RIGHT")
        assert sf.has_been_checked("C-1") is True

    def test_add_question(self, tmp_path):
        sf = StateFile(str(tmp_path / "state.md"))
        qid = sf.add_open_question("Is this a bug?")
        assert qid == "Q-1"
        assert sf.path.exists()

    def test_record_fixed_and_skipped(self, tmp_path):
        sf = StateFile(str(tmp_path / "state.md"))
        sf.record_fixed("F-1", "fixed bug", "auto-fixed usage.json")
        sf.record_skipped("S-1", "E501 rule", "deliberate choice")
        content = sf.path.read_text()
        assert "F-1" in content
        assert "S-1" in content
