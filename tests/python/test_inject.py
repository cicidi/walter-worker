"""Tests for coworker.memory.inject — CLAUDE.local.md snapshot injection."""

from __future__ import annotations

from unittest.mock import MagicMock

from coworker.memory.inject import (
    MARKER_START,
    MARKER_END,
    build_snapshot,
    inject_into_local_md,
    remove_snapshot,
)


class TestBuildSnapshot:
    def test_empty_results(self):
        mock_client = MagicMock()
        mock_client.search.return_value = []
        snapshot = build_snapshot(mock_client, project="test-project")
        assert "<!-- MEMORY:test-project START -->" in snapshot
        assert "No stored memories yet" in snapshot
        assert "<!-- MEMORY:test-project END -->" in snapshot

    def test_with_entries(self):
        mock_client = MagicMock()
        mock_client.search.return_value = [
            {"memory": "Use ruff for linting", "metadata": {"type": "convention"}},
            {"memory": "Prefer Chinese", "metadata": {"type": "preference"}},
            {"memory": "MCP 403 retry pattern", "metadata": {"type": "lesson"}},
        ]
        snapshot = build_snapshot(mock_client, project="test")
        assert "Use ruff" in snapshot
        assert "Prefer Chinese" in snapshot
        assert "MCP 403" in snapshot
        assert snapshot.count("- 📋") >= 1
        assert snapshot.count("- ⚙️") >= 1
        assert snapshot.count("- 🔧") >= 1

    def test_search_error_handled_gracefully(self):
        mock_client = MagicMock()
        mock_client.search.side_effect = RuntimeError("search down")
        snapshot = build_snapshot(mock_client)
        assert "No stored memories yet" in snapshot


class TestInjectIntoLocalMd:
    def test_creates_file_if_missing(self, tmp_path):
        path = tmp_path / "CLAUDE.local.md"
        snapshot = "<!-- MEMORY:test START -->\ncontent\n<!-- MEMORY:test END -->"
        result = inject_into_local_md(str(path), snapshot, project="test")
        assert result is True
        assert path.exists()
        assert "content" in path.read_text()

    def test_replaces_existing_block(self, tmp_path):
        path = tmp_path / "CLAUDE.local.md"
        path.write_text("some content\n<!-- MEMORY:test START -->\nold\n<!-- MEMORY:test END -->\nmore")
        snapshot = "<!-- MEMORY:test START -->\nnew\n<!-- MEMORY:test END -->"
        result = inject_into_local_md(str(path), snapshot, project="test")
        assert result is True
        content = path.read_text()
        assert "new" in content
        assert "old" not in content
        assert "some content" in content
        assert "more" in content

    def test_appends_if_no_existing_block(self, tmp_path):
        path = tmp_path / "CLAUDE.local.md"
        path.write_text("existing content")
        snapshot = "<!-- MEMORY:test START -->\nnew snapshot\n<!-- MEMORY:test END -->"
        result = inject_into_local_md(str(path), snapshot, project="test")
        assert result is True
        content = path.read_text()
        assert "existing content" in content
        assert "new snapshot" in content

    def test_no_change_if_block_identical(self, tmp_path):
        path = tmp_path / "CLAUDE.local.md"
        snapshot = "<!-- MEMORY:test START -->\nsame\n<!-- MEMORY:test END -->"
        path.write_text("before\n" + snapshot + "\nafter")
        result = inject_into_local_md(str(path), snapshot, project="test")
        assert result is False

    def test_different_project_markers(self, tmp_path):
        path = tmp_path / "CLAUDE.local.md"
        path.write_text("<!-- MEMORY:proj-a START -->\na\n<!-- MEMORY:proj-a END -->")
        snapshot_b = "<!-- MEMORY:proj-b START -->\nb\n<!-- MEMORY:proj-b END -->"
        result = inject_into_local_md(str(path), snapshot_b, project="proj-b")
        assert result is True
        content = path.read_text()
        assert "proj-a" in content
        assert "proj-b" in content


class TestRemoveSnapshot:
    def test_removes_existing_block(self, tmp_path):
        path = tmp_path / "CLAUDE.local.md"
        path.write_text("before\n<!-- MEMORY:test START -->\nblock\n<!-- MEMORY:test END -->\nafter")
        result = remove_snapshot(str(path), project="test")
        assert result is True
        content = path.read_text()
        assert "before" in content
        assert "after" in content
        assert "block" not in content

    def test_noop_if_no_block(self, tmp_path):
        path = tmp_path / "CLAUDE.local.md"
        path.write_text("no markers here")
        result = remove_snapshot(str(path), project="test")
        assert result is False

    def test_noop_if_file_missing(self, tmp_path):
        result = remove_snapshot(str(tmp_path / "nonexistent.md"), project="test")
        assert result is False
