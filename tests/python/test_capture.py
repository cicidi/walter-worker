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


class TestSkillThresholdIsConfigurable:
    """COWORKER_SKILL_THRESHOLD was documented and inert.

    capture.process_session_end compared candidate tool counts against a
    literal 10, so setting the variable changed nothing. The prompt states the
    same rule to the model, which is why it went unnoticed: the two agreed
    until you tried to configure either. The threshold now lives in one place
    and both read it.
    """

    def test_capture_uses_the_configured_threshold(self, monkeypatch, tmp_path):
        import json as _json

        from coworker.memory import capture
        from coworker.memory.llm import LLMResponse

        staged = []

        class _Mem0:
            def search(self, **kw):
                return []

            def add(self, **kw):
                return {"results": [{"id": "m", "memory": "x", "event": "ADD"}]}

        monkeypatch.setattr(capture, "_stage_skill", lambda c, s: staged.append(c))

        transcript = tmp_path / "t.txt"
        transcript.write_text("x" * 600)

        def run(threshold):
            staged.clear()
            monkeypatch.setenv("COWORKER_SKILL_THRESHOLD", str(threshold))

            class _LLM:
                def chat(self, messages, **kw):
                    return LLMResponse(content=_json.dumps({
                        "lessons": [],
                        "skill_candidates": [
                            {"name": "mid", "description": "d", "tool_call_count": 5}
                        ],
                    }), model="f", provider="f")

            capture.process_session_end(
                mem0_client=_Mem0(), llm_client=_LLM(),
                session_id="s1", transcript_path=str(transcript),
            )
            return list(staged)

        assert run(3), "a candidate above the configured threshold must be staged"
        assert not run(10), "and one below it must not be"

    def test_the_default_is_ten(self, monkeypatch):
        from coworker.memory.capture import _get_skill_threshold

        monkeypatch.delenv("COWORKER_SKILL_THRESHOLD", raising=False)
        assert _get_skill_threshold() == 10


class TestMemoriesAreTaggedWithTheRealProject:
    """Capture tagged every memory with the literal "walter-worker".

    That is the tool's own name, not the project the session ran in. So
    `memory search --project <their project>` matched nothing the capture stage
    had stored, and the injected snapshot was labelled with someone else's
    project name. inject.build_snapshot filtered on the same literal, which is
    why the two agreed and nothing looked wrong.
    """

    def test_the_transcript_names_the_project(self, tmp_path):
        from coworker.memory.capture import project_cwd, resolve_project

        transcript = '{"cwd": "/home/x/project/my-app"}\n{"cwd": "/other"}'
        assert resolve_project(project_cwd(transcript)) == "my-app"

    def test_a_transcript_without_a_cwd_falls_back(self):
        from coworker.memory.capture import project_cwd, resolve_project

        assert project_cwd("not json\n") == ""
        assert resolve_project("") == "walter-worker"

    def test_the_reader_filters_on_the_same_project(self, monkeypatch, tmp_path):
        """inject must look for what capture wrote, not for the tool's name."""
        from coworker.memory import inject

        seen = {}

        class _Mem0:
            def search(self, **kw):
                seen.update(kw.get("filters") or {})
                return []

        (tmp_path / "my-app").mkdir()
        monkeypatch.chdir(tmp_path / "my-app")
        inject.build_snapshot(_Mem0())

        assert seen.get("project") == "my-app", (
            "the snapshot filters on the cwd's project, which is what capture tags"
        )
