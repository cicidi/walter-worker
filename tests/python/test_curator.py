"""Tests for coworker.memory.curator — periodic maintenance."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from coworker.memory.curator import (
    ARCHIVE_DAYS,
    CURATOR_INTERVAL_DAYS,
    STALE_DAYS,
    export_memory_md,
    generate_report,
    is_due,
    mark_ran,
    run_curator,
)


def _days_ago(n: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=n)).strftime("%Y-%m-%dT%H:%M:%SZ")


class FakeMem0:
    """In-memory stand-in that models the real client's side effect.

    Mem0Client.search() bumps use_count and last_used on every entry it
    returns (mem0_client.py, "Auto-increment use_count for retrieved
    entries"); list_entries() is a read-only listing. Modelling that here
    is what lets a test catch a sweep that expires its own evidence.
    """

    def __init__(self, entries: list[dict]) -> None:
        self.entries = {e["id"]: e for e in entries}
        self.searches = 0

    @staticmethod
    def _match(entry: dict, filters: dict | None) -> bool:
        return all(entry["metadata"].get(k) == v for k, v in (filters or {}).items())

    def _select(self, filters: dict | None, top_k: int) -> list[dict]:
        return [dict(e) for e in self.entries.values() if self._match(e, filters)][:top_k]

    def list_entries(self, filters: dict | None = None, top_k: int = 1000, **kw) -> list[dict]:
        return self._select(filters, top_k)

    def search(self, query: str = "", filters: dict | None = None, top_k: int = 200, **kw) -> list[dict]:
        self.searches += 1
        found = self._select(filters, top_k)
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        for e in found:  # the real client writes back on read
            real = self.entries[e["id"]]
            real["metadata"]["use_count"] += 1
            real["metadata"]["last_used"] = now
        return found

    def update(self, entry_id: str, metadata: dict | None = None, memory: str | None = None) -> None:
        self.entries[entry_id]["metadata"].update(metadata or {})

    def state(self, entry_id: str) -> str:
        return self.entries[entry_id]["metadata"]["state"]

    def last_used(self, entry_id: str) -> str:
        return self.entries[entry_id]["metadata"]["last_used"]


class TestConstants:
    def test_stale_days(self):
        assert STALE_DAYS == 30

    def test_archive_days(self):
        assert ARCHIVE_DAYS == 90


class TestExportMemoryMd:
    def test_empty_store(self, tmp_path):
        mock_client = MagicMock()
        mock_client.list_entries.return_value = []
        path = tmp_path / "MEMORY.md"
        count = export_memory_md(mock_client, str(path))
        assert count == 0
        assert path.exists()

    def test_with_entries_grouped_by_project(self, tmp_path):
        mock_client = MagicMock()
        mock_client.list_entries.return_value = [
            {"memory": "Lesson A", "metadata": {"project": "walter-worker", "type": "lesson", "topic": "mcp"}},
            {"memory": "Convention B", "metadata": {"project": "walter-worker", "type": "convention", "topic": "lint"}},
            {"memory": "Lesson C", "metadata": {"project": "skill-factory", "type": "lesson", "topic": "docker"}},
        ]
        path = tmp_path / "MEMORY.md"
        count = export_memory_md(mock_client, str(path))
        assert count == 3
        content = path.read_text()
        assert "Project: walter-worker" in content
        assert "Project: skill-factory" in content
        assert "Lesson A" in content
        assert "Convention B" in content
        assert "Lesson C" in content

    def test_listing_error_handled(self, tmp_path):
        mock_client = MagicMock()
        mock_client.list_entries.side_effect = RuntimeError("down")
        path = tmp_path / "MEMORY.md"
        count = export_memory_md(mock_client, str(path))
        assert count == 0


class TestGenerateReport:
    def test_generates_report(self, tmp_path):
        mock_client = MagicMock()
        mock_client.list_entries.return_value = []
        path = generate_report(mock_client, str(tmp_path))
        assert path.exists()
        content = path.read_text()
        assert "Curator Report" in content

    def test_counts_are_not_capped_by_a_query_limit(self, tmp_path):
        """Counts used to come from a top_k=1 search, so they read 0 or 1."""
        mock_client = MagicMock()
        mock_client.list_entries.side_effect = lambda filters=None, **kw: {
            "active": [{"memory": f"a{i}", "metadata": {}} for i in range(7)],
            "stale": [{"memory": "s", "metadata": {}}],
            "archived": [],
        }[filters["state"]]
        content = generate_report(mock_client, str(tmp_path)).read_text()
        assert "- Active: 7" in content
        assert "- Stale: 1" in content
        assert "- Archived: 0" in content


class TestRunCurator:
    def test_run_curator_basic(self, tmp_path):
        mock_mem0 = MagicMock()
        mock_mem0.list_entries.return_value = []
        with patch("coworker.memory.pending.expire_old_items", return_value=0):
            stats = run_curator(mock_mem0, export_path=str(tmp_path / "MEMORY.md"))
        assert "stale_marked" in stats
        assert "archived" in stats
        assert "exported_entries" in stats


class TestDecayActuallyRuns:
    """The sweep must not refresh the evidence it is about to expire.

    _mark_stale runs before _archive_old and reads last_used. If that read
    goes through search(), the entry's last_used is reset to now, so
    _archive_old's "older than ARCHIVE_DAYS" test can never be satisfied.
    """

    def test_entry_untouched_for_100_days_is_archived(self):
        fake = FakeMem0([
            {"id": "a", "memory": "stale lesson",
             "metadata": {"state": "active", "last_used": _days_ago(100),
                          "use_count": 1, "project": "p"}},
        ])
        with patch("coworker.memory.pending.expire_old_items", return_value=0):
            run_curator(fake)
        assert fake.state("a") == "archived"

    def test_sweep_does_not_refresh_last_used(self):
        untouched = _days_ago(100)
        fake = FakeMem0([
            {"id": "a", "memory": "stale lesson",
             "metadata": {"state": "active", "last_used": untouched,
                          "use_count": 1, "project": "p"}},
        ])
        with patch("coworker.memory.pending.expire_old_items", return_value=0):
            run_curator(fake)
        assert fake.last_used("a") == untouched
        assert fake.entries["a"]["metadata"]["use_count"] == 1

    def test_recently_used_entry_is_left_active(self):
        fake = FakeMem0([
            {"id": "fresh", "memory": "current lesson",
             "metadata": {"state": "active", "last_used": _days_ago(3),
                          "use_count": 9, "project": "p"}},
        ])
        with patch("coworker.memory.pending.expire_old_items", return_value=0):
            run_curator(fake)
        assert fake.state("fresh") == "active"


class TestDueCheck:
    """Spec §4.3 schedules the curator "every 7 days"; the check is lazy."""

    def test_interval_is_seven_days(self):
        assert CURATOR_INTERVAL_DAYS == 7

    def test_due_when_never_run(self, tmp_path):
        assert is_due(state_path=tmp_path / ".curator_last_run") is True

    def test_not_due_within_interval(self, tmp_path):
        p = tmp_path / ".curator_last_run"
        mark_ran(state_path=p)
        assert is_due(state_path=p) is False

    def test_due_after_interval(self, tmp_path):
        p = tmp_path / ".curator_last_run"
        p.write_text(str(time.time() - 8 * 86400))
        assert is_due(state_path=p) is True

    def test_mark_ran_creates_parent_dir(self, tmp_path):
        p = tmp_path / "nested" / ".curator_last_run"
        mark_ran(state_path=p)
        assert p.exists()
        assert is_due(state_path=p) is False

    def test_corrupt_state_is_treated_as_never_run(self, tmp_path):
        p = tmp_path / ".curator_last_run"
        p.write_text("not-a-number")
        assert is_due(state_path=p) is True
