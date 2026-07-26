"""Tests for coworker.memory.engine — evolution engine."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest
from coworker.memory.engine import ExtractionResult, extract_and_store, reconcile


class TestExtractionResult:
    def test_default_values(self):
        r = ExtractionResult()
        assert r.lessons == []
        assert r.skill_candidates == []
        assert r.stats == {}

    def test_with_data(self):
        r = ExtractionResult(
            lessons=[{"memory": "test"}],
            skill_candidates=[{"name": "s1", "tool_call_count": 15}],
            stats={"total_extracted": 1, "stored": 1, "eligible_skills": 1},
        )
        assert r.stats["eligible_skills"] == 1


class TestExtractAndStore:
    def test_empty_transcript(self, clean_mem0, real_llm):
        if "DEEPSEEK_API_KEY" not in os.environ:
            pytest.skip("DEEPSEEK_API_KEY not set")
        result = extract_and_store(clean_mem0, real_llm, "sess_empty", "no useful content here")
        assert isinstance(result, ExtractionResult)

    def test_with_content(self, clean_mem0, real_llm):
        if "DEEPSEEK_API_KEY" not in os.environ:
            pytest.skip("DEEPSEEK_API_KEY not set")
        transcript = """
[user] Fix the authentication bug in auth.py
[tool] Read: def refresh_token(): ...
[tool] Edit: Added retry logic with exponential backoff
[tool] Bash: pytest tests/ -v — 45 passed
[user] The MCP server 403'd on first request, had to retry
[tool] Edit: Added MCP retry wrapper
"""
        result = extract_and_store(clean_mem0, real_llm, "sess_test_engine", transcript)
        assert isinstance(result, ExtractionResult)
        assert result.stats.get("total_extracted", 0) >= 0


class TestReconcile:
    def test_empty_transcript(self, clean_mem0, tmp_path):
        path = tmp_path / "empty.txt"
        path.write_text("")
        count = reconcile(clean_mem0, "sess_x", str(path))
        assert count == 0

    def test_short_transcript(self, clean_mem0, tmp_path):
        path = tmp_path / "short.txt"
        path.write_text("hi")
        count = reconcile(clean_mem0, "sess_x", str(path))
        assert count == 0

    def test_missing_file(self, clean_mem0):
        count = reconcile(clean_mem0, "sess_x", "/nonexistent/path.txt")
        assert count == 0
