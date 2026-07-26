"""Tests for coworker.memory.capture — per-turn and session-end capture."""

from __future__ import annotations

import os

import pytest
from coworker.memory.capture import EXTRACTION_PROMPT, SESSION_END_PROMPT, TurnResult, SessionEndResult, process_turn


class TestTurnResult:
    def test_default_values(self):
        r = TurnResult()
        assert r.lessons_extracted == 0
        assert r.lessons == []
        assert r.state_delta is None
        assert r.error is None

    def test_with_lessons(self):
        r = TurnResult(lessons_extracted=2, lessons=[{"memory": "test"}], state_delta="fixed bug")
        assert r.lessons_extracted == 2


class TestSessionEndResult:
    def test_default_values(self):
        r = SessionEndResult()
        assert r.reconciled == 0
        assert r.skills_staged == []

    def test_with_skills(self):
        r = SessionEndResult(reconciled=3, skills_staged=["test-skill"])
        assert r.reconciled == 3
        assert "test-skill" in r.skills_staged


class TestPrompts:
    def test_extraction_prompt_has_placeholders(self):
        assert "{existing_lessons}" in EXTRACTION_PROMPT
        assert "{tool}" in EXTRACTION_PROMPT
        assert "{tool_input}" in EXTRACTION_PROMPT
        assert "{tool_result}" in EXTRACTION_PROMPT
        assert "{recent_context}" in EXTRACTION_PROMPT

    def test_session_end_prompt_is_non_empty(self):
        assert len(SESSION_END_PROMPT) > 100
        assert "lessons" in SESSION_END_PROMPT.lower()
        assert "skill_candidates" in SESSION_END_PROMPT.lower()


@pytest.mark.real
class TestProcessTurnReal:
    def test_extracts_from_meaningful_event(self, clean_mem0, real_llm, tmp_path):
        if "DEEPSEEK_API_KEY" not in os.environ:
            pytest.skip("DEEPSEEK_API_KEY not set")

        tool_event = {
            "tool": "Edit",
            "input": {"file_path": "src/auth.py"},
            "result": "Added retry logic with exponential backoff for token refresh",
            "session_id": "sess_test",
        }
        recent = [
            {"role": "user", "content": "fix the token refresh bug in auth.py"},
            {"role": "tool", "tool": "Read", "content": "def refresh_token(): ..."},
        ]

        result = process_turn(
            clean_mem0, real_llm, tool_event, recent, "sess_test",
            audit_dir=str(tmp_path),
        )

        assert result is not None
        assert isinstance(result, TurnResult)
        assert (tmp_path / "audit.log").exists()
        content = (tmp_path / "audit.log").read_text()
        assert "sess_test" in content

    def test_trivial_event_no_crash(self, clean_mem0, real_llm, tmp_path):
        if "DEEPSEEK_API_KEY" not in os.environ:
            pytest.skip("DEEPSEEK_API_KEY not set")

        tool_event = {
            "tool": "Bash",
            "input": {"command": "git status"},
            "result": "nothing to commit, working tree clean",
            "session_id": "sess_test",
        }

        result = process_turn(
            clean_mem0, real_llm, tool_event, [], "sess_test",
            audit_dir=str(tmp_path),
        )

        assert result is not None
        # Most trivial events should produce 0 lessons
        assert result.lessons_extracted >= 0

    def test_with_state_dir(self, clean_mem0, real_llm, tmp_path):
        if "DEEPSEEK_API_KEY" not in os.environ:
            pytest.skip("DEEPSEEK_API_KEY not set")

        state_dir = tmp_path / "state"
        tool_event = {
            "tool": "Write",
            "input": {"file_path": "src/new_module.py"},
            "result": "Created new module with 200 lines",
            "session_id": "sess_test",
        }

        result = process_turn(
            clean_mem0, real_llm, tool_event, [], "sess_test",
            state_dir=str(state_dir), audit_dir=str(tmp_path),
        )

        assert result is not None
