"""Tests for coworker.memory.train — batch training pipeline."""

from __future__ import annotations

import json
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
