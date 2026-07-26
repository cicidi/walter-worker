"""Tests for coworker.memory.curator — periodic maintenance."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from coworker.memory.curator import export_memory_md, generate_report, run_curator, STALE_DAYS, ARCHIVE_DAYS


class TestConstants:
    def test_stale_days(self):
        assert STALE_DAYS == 30

    def test_archive_days(self):
        assert ARCHIVE_DAYS == 90


class TestExportMemoryMd:
    def test_empty_store(self, tmp_path):
        mock_client = MagicMock()
        mock_client.search.return_value = []
        path = tmp_path / "MEMORY.md"
        count = export_memory_md(mock_client, str(path))
        assert count == 0
        assert path.exists()

    def test_with_entries_grouped_by_project(self, tmp_path):
        mock_client = MagicMock()
        mock_client.search.return_value = [
            {"memory": "Lesson A", "metadata": {"project": "ai-coworker", "type": "lesson", "topic": "mcp"}},
            {"memory": "Convention B", "metadata": {"project": "ai-coworker", "type": "convention", "topic": "lint"}},
            {"memory": "Lesson C", "metadata": {"project": "skill-factory", "type": "lesson", "topic": "docker"}},
        ]
        path = tmp_path / "MEMORY.md"
        count = export_memory_md(mock_client, str(path))
        assert count == 3
        content = path.read_text()
        assert "Project: ai-coworker" in content
        assert "Project: skill-factory" in content
        assert "Lesson A" in content
        assert "Convention B" in content
        assert "Lesson C" in content

    def test_search_error_handled(self, tmp_path):
        mock_client = MagicMock()
        mock_client.search.side_effect = RuntimeError("down")
        path = tmp_path / "MEMORY.md"
        count = export_memory_md(mock_client, str(path))
        assert count == 0


class TestGenerateReport:
    def test_generates_report(self, tmp_path):
        mock_client = MagicMock()
        mock_client.search.return_value = []
        path = generate_report(mock_client, str(tmp_path))
        assert path.exists()
        content = path.read_text()
        assert "Curator Report" in content


class TestRunCurator:
    def test_run_curator_basic(self, tmp_path):
        mock_mem0 = MagicMock()
        mock_mem0.search.return_value = []
        with patch("coworker.memory.pending.expire_old_items", return_value=0):
            stats = run_curator(mock_mem0, export_path=str(tmp_path / "MEMORY.md"))
        assert "stale_marked" in stats
        assert "archived" in stats
        assert "exported_entries" in stats
