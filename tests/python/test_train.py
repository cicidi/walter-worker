"""Tests for coworker.memory.train — batch training pipeline."""

from __future__ import annotations

import json
import pytest
from unittest.mock import MagicMock

from coworker.memory.train import run_training_pipeline


class TestTrainingPipeline:
    def test_empty_db_returns_zero(self):
        mock_mem0 = MagicMock()
        mock_mem0.search.return_value = []
        mock_llm = MagicMock()
        mock_db = MagicMock()
        mock_db.list_all_sessions.return_value = []

        stats = run_training_pipeline(mock_mem0, mock_llm, mock_db, limit=1)
        assert stats["sessions_processed"] == 0
        assert stats["lessons_extracted"] == 0

    def test_skip_existing_entries(self):
        mock_mem0 = MagicMock()
        mock_mem0.search.return_value = [{"id": "existing"}]
        mock_llm = MagicMock()
        mock_db = MagicMock()
        mock_db.list_all_sessions.return_value = [{"id": "s1", "project": "test"}]

        stats = run_training_pipeline(mock_mem0, mock_llm, mock_db, limit=1, skip_existing=True)
        assert stats["sessions_processed"] == 0  # Skipped because existing entry found

    def test_limit_respected(self):
        mock_mem0 = MagicMock()
        mock_mem0.search.return_value = []
        mock_llm = MagicMock()
        mock_db = MagicMock()
        mock_db.list_all_sessions.return_value = [
            {"id": "s1", "project": "test"}, {"id": "s2", "project": "test"}
        ]

        stats = run_training_pipeline(mock_mem0, mock_llm, mock_db, limit=1, skip_existing=False)
        assert stats["sessions_processed"] <= 1

    def test_db_error_handled(self):
        mock_mem0 = MagicMock()
        mock_llm = MagicMock()
        mock_db = MagicMock()
        mock_db.list_all_sessions.side_effect = RuntimeError("db down")

        stats = run_training_pipeline(mock_mem0, mock_llm, mock_db)
        assert "errors" in stats
        # The error message gets stringified into the errors list
        # It's either a single entry or the list is populated in some way
        assert stats["sessions_processed"] == 0  # Nothing processed due to error


class TestTrainingStagesApprovableSkills:
    """Skills staged by training must survive the sandbox at approval.

    train.py wrote the pending JSON itself with a "source" field, but
    _sandbox_check requires "source_session" - so every skill the pipeline
    staged was rejected by approve() as "Missing source_session in skill
    metadata", while stats["skills_staged"] counted it as a success. Writing
    directly also skipped the circuit breaker.
    """

    @pytest.fixture(autouse=True)
    def _isolate(self, tmp_path, monkeypatch):
        from coworker.memory import pending, safety

        monkeypatch.setattr(pending, "DEFAULT_PENDING_DIR", str(tmp_path / "pending"))
        monkeypatch.setattr(pending, "DEFAULT_ACTIVE_DIR", str(tmp_path / "skills"))
        monkeypatch.setattr(
            pending,
            "DEFAULT_IDE_COMMAND_DIRS",
            (str(tmp_path / "commands"), str(tmp_path / "instructions")),
        )
        monkeypatch.setattr(
            safety, "_circuit_state_path", lambda: tmp_path / "circuit.json"
        )

    def _mem0_returning(self, topic, times):
        from unittest.mock import MagicMock

        m = MagicMock()
        m.search.return_value = [{"metadata": {"topic": topic}} for _ in range(times)]
        return m

    def test_staged_skill_carries_source_session(self):
        from coworker.memory import pending
        from coworker.memory.train import auto_generate_skills

        auto_generate_skills(self._mem0_returning("deploy-thing", 5), None, None,
                             min_occurrences=3)

        items = pending.list_pending()
        assert items, "nothing was staged"
        assert items[0].get("source_session"), "sandbox will reject this at approval"

    def test_staged_skill_can_be_approved(self):
        from coworker.memory import pending
        from coworker.memory.train import auto_generate_skills

        auto_generate_skills(self._mem0_returning("deploy-thing", 5), None, None,
                             min_occurrences=3)

        skill_id = pending.list_pending()[0]["name"].replace(" ", "-").lower()[:40]
        assert pending.approve(skill_id) is True, (
            "approve rejected a training-staged skill"
        )

    def test_training_respects_the_circuit_breaker(self):
        from coworker.memory import pending, safety
        from coworker.memory.train import auto_generate_skills

        for i in range(safety.CIRCUIT_BREAKER_LIMIT):
            pending.stage_skill(f"filler-{i}", "d", 10, "s")

        generated = auto_generate_skills(
            self._mem0_returning("deploy-thing", 5), None, None, min_occurrences=3
        )
        assert generated == [], "staged past a tripped breaker"
