"""The Evolution page reads mem0 without recording a retrieval.

Mem0Client.search() bumps use_count and last_used on every hit. The overview
counted experiences with search(top_k=1000), so each page load rewrote 1000
entries (about 16 s, past the page's 8 s timeout), capped the count at 1000,
and refreshed last_used on entries the curator was about to expire. The
experiences list did the same to 200 entries.
"""

from __future__ import annotations

import pytest
from coworker.dashboard import queries_evolution as qe
from coworker.memory.mem0_client import Mem0Client


class FakeMem0:
    def __init__(self, entries):
        self.entries = entries
        self.list_calls = []

    def search(self, *a, **kw):
        raise AssertionError("search() bumps use_count; the dashboard must not call it")

    def list_entries(self, filters=None, top_k=1000, user_id="default"):
        self.list_calls.append((dict(filters or {}), top_k))
        out = [e for e in self.entries
               if all(e["metadata"].get(k) == v for k, v in (filters or {}).items())]
        return out[:top_k]


def _entry(i, provenance="agent", state="active", created="2026-11-01T00:00:00Z"):
    return {"id": f"id{i}", "memory": f"lesson {i}", "created_at": created,
            "metadata": {"provenance": provenance, "state": state, "topic": "t",
                         "project": "p", "use_count": i, "last_used": ""}}


def test_overview_counts_every_agent_entry_past_1000():
    fake = FakeMem0([_entry(i) for i in range(2500)] + [_entry(9999, provenance="manual")])
    assert qe._count_agent_experiences(fake) == 2500


@pytest.fixture
def fake_store(monkeypatch):
    entries = [
        _entry(1, created="2026-11-01T00:00:00Z"),
        _entry(2, created="2026-11-03T00:00:00Z"),
        _entry(3, state="stale", created="2026-11-02T00:00:00Z"),
        _entry(4, provenance="manual", created="2026-11-04T00:00:00Z"),
    ]
    fake = FakeMem0(entries)
    monkeypatch.setattr(Mem0Client, "from_config", classmethod(lambda cls, **kw: fake))
    return fake


def test_experiences_list_does_not_search_and_is_newest_first(fake_store):
    rows = qe.query_evolution_experiences(status="all")
    assert [r["id"] for r in rows] == ["id2", "id3", "id1"]


def test_experiences_list_filters_by_state(fake_store):
    rows = qe.query_evolution_experiences(status="active")
    assert {r["id"] for r in rows} == {"id1", "id2"}
