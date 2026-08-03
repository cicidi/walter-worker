"""Tests for analytics/knowledge.py — knowledge extraction, dedup, and storage."""
from __future__ import annotations

import json
import sqlite3
import hashlib
from datetime import datetime, timedelta

import pytest


# ── Pure function tests ────────────────────────────────────────────────────────


def test_semantic_key_basic():
    from coworker.analytics.knowledge import _semantic_key

    card = {"title": "Test Function", "summary": "A test summary", "type": "pattern"}
    key = _semantic_key(card)
    assert isinstance(key, str)
    assert len(key) == 12  # md5 hex[:12]


def test_semantic_key_missing_fields():
    from coworker.analytics.knowledge import _semantic_key

    card = {}
    key = _semantic_key(card)
    assert isinstance(key, str)
    assert len(key) == 12


def test_semantic_key_deterministic():
    from coworker.analytics.knowledge import _semantic_key

    card = {"title": "X", "summary": "Y", "type": "Z"}
    assert _semantic_key(card) == _semantic_key(card)


def test_semantic_key_different_cards():
    from coworker.analytics.knowledge import _semantic_key

    # Use words longer than 3 characters so the >3 filter keeps them
    a = {"title": "First Unique Concept", "summary": "alpha beta", "type": "pattern"}
    b = {"title": "Different Second Idea", "summary": "gamma delta", "type": "pattern"}
    assert _semantic_key(a) != _semantic_key(b)


def test_levenshtein_identical():
    from coworker.analytics.knowledge import _levenshtein
    assert _levenshtein("hello", "hello") == 0


def test_levenshtein_empty():
    from coworker.analytics.knowledge import _levenshtein
    assert _levenshtein("", "") == 0
    assert _levenshtein("abc", "") == 3
    assert _levenshtein("", "abc") == 3


def test_levenshtein_one_edit():
    from coworker.analytics.knowledge import _levenshtein
    assert _levenshtein("cat", "bat") == 1  # substitution
    assert _levenshtein("cat", "cats") == 1  # insertion
    assert _levenshtein("cats", "cat") == 1  # deletion


def test_levenshtein_multiple_edits():
    from coworker.analytics.knowledge import _levenshtein
    assert _levenshtein("kitten", "sitting") == 3


# ── Dedup tests ────────────────────────────────────────────────────────────────


def test_is_duplicate_empty_existing():
    from coworker.analytics.knowledge import _is_duplicate

    card = {"title": "Test", "type": "pattern", "summary": "test"}
    assert not _is_duplicate(card, [])


def test_is_duplicate_semantic_key_no_match():
    from coworker.analytics.knowledge import _is_duplicate

    card = {"title": "Unique Function", "type": "pattern", "summary": "unique"}
    existing = [{"title": "Other", "type": "pattern", "summary": "different"}]
    assert not _is_duplicate(card, existing)


def test_is_duplicate_exact_title_match():
    from coworker.analytics.knowledge import _is_duplicate

    card = {"title": "Same Pattern", "type": "pattern", "summary": "A"}
    existing = [
        {
            "title": "Same Pattern",
            "type": "pattern",
            "summary": "A",
        }
    ]
    assert _is_duplicate(card, existing)


def test_is_duplicate_close_title_same_type(monkeypatch):
    from coworker.analytics import knowledge

    # Titles share the same set of words > 3 chars (Code, Review),
    # same type, and LD ≤ 3 → should match before reaching LLM
    card = {"title": "Code Review abc", "type": "pattern", "summary": "shared"}
    existing = [{"title": "Code Review xyz", "type": "pattern", "summary": "shared"}]

    assert knowledge._is_duplicate(card, existing)


def test_is_duplicate_llm_yes(monkeypatch):
    from coworker.analytics import knowledge

    # Same semantic key, same type, LD ≤ 3 → levenshtein path matches
    card2 = {"title": "Code Review abc", "type": "pattern", "summary": "shared"}
    existing2 = [
        {"title": "Code Review xyz", "type": "pattern", "summary": "shared"}
    ]
    # Levenshtein = 3, same type → should return True
    assert knowledge._is_duplicate(card2, existing2)


def test_is_duplicate_llm_fallback_yes(monkeypatch):
    from coworker.analytics import knowledge

    def mock_ask_llm(new, candidates):
        return True

    monkeypatch.setattr(knowledge, "_ask_llm_is_duplicate", mock_ask_llm)

    # Same semantic key (both share Code, Review, Pattern, Note, shared),
    # different types → levenshtein skipped → falls through to LLM mock
    card3 = {"title": "Code Review Pattern", "type": "note", "summary": "shared"}
    existing3 = [{"title": "Code Review Note", "type": "pattern", "summary": "shared"}]
    assert knowledge._is_duplicate(card3, existing3)


def test_is_duplicate_llm_fallback_no(monkeypatch):
    from coworker.analytics import knowledge

    def mock_ask_llm(new, candidates):
        return False

    monkeypatch.setattr(knowledge, "_ask_llm_is_duplicate", mock_ask_llm)

    # Same semantic key, different types → skips levenshtein → LLM mock returns False
    card = {"title": "Code Review Pattern", "type": "note", "summary": "shared"}
    existing = [{"title": "Code Review Note", "type": "pattern", "summary": "shared"}]
    assert not knowledge._is_duplicate(card, existing)


# ── LLM dedup tests ────────────────────────────────────────────────────────────


def test_ask_llm_no_api_key(monkeypatch):
    """When DEEPSEEK_API_KEY is empty, returns False without calling API."""
    import sys
    from coworker.analytics.knowledge import _ask_llm_is_duplicate

    # Inject a fake openai module so the import inside the function succeeds
    fake_mod = type(sys)("openai")
    monkeypatch.setitem(sys.modules, "openai", fake_mod)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")
    result = _ask_llm_is_duplicate({"title": "X"}, [{"title": "Y"}])
    assert not result


def test_ask_llm_yes_response(monkeypatch):
    """When LLM returns YES, function returns True."""
    import sys
    from coworker.analytics.knowledge import _ask_llm_is_duplicate

    class FakeChoice:
        def __init__(self, content):
            self.message = type("msg", (), {"content": content})()

    class FakeCompletions:
        @staticmethod
        def create(**kw):
            return type("resp", (), {"choices": [FakeChoice("YES")]})()

    class FakeChat:
        completions = FakeCompletions()

    class FakeOpenAI:
        def __init__(self, **kwargs):
            pass
        chat = FakeChat()

    fake_mod = type(sys)("openai")
    fake_mod.OpenAI = FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_mod)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key")
    assert _ask_llm_is_duplicate({"title": "X"}, [{"title": "Y"}])


def test_ask_llm_no_response(monkeypatch):
    """When LLM returns NO, function returns False."""
    import sys
    from coworker.analytics.knowledge import _ask_llm_is_duplicate

    class FakeChoice:
        def __init__(self, content):
            self.message = type("msg", (), {"content": content})()

    class FakeCompletions:
        @staticmethod
        def create(**kw):
            return type("resp", (), {"choices": [FakeChoice("NO")]})()

    class FakeChat:
        completions = FakeCompletions()

    class FakeOpenAI:
        def __init__(self, **kwargs):
            pass
        chat = FakeChat()

    fake_mod = type(sys)("openai")
    fake_mod.OpenAI = FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_mod)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key")
    assert not _ask_llm_is_duplicate({"title": "X"}, [{"title": "Y"}])


def test_ask_llm_exception_returns_false(monkeypatch):
    """When OpenAI client crashes, function returns False."""
    import sys
    from coworker.analytics.knowledge import _ask_llm_is_duplicate

    class CrashOpenAI:
        def __init__(self, **kwargs):
            pass

        @property
        def chat(self):
            raise RuntimeError("API crash")

    fake_mod = type(sys)("openai")
    fake_mod.OpenAI = CrashOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_mod)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key")
    assert not _ask_llm_is_duplicate({"title": "X"}, [{"title": "Y"}])


# ── DB-backed function tests ───────────────────────────────────────────────────


@pytest.fixture
def knowledge_db(monkeypatch):
    """In-memory SQLite with full schema, patched get_db.

    Uses a shared-cache in-memory database so that functions which
    call get_db() and then close their connection don't invalidate
    the test's own anchor connection.
    """
    import coworker.analytics.knowledge as k_mod
    from coworker.analytics.db import SCHEMA

    conn = sqlite3.connect("file:test_knowledge?mode=memory&cache=shared", uri=True)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)

    def _get_shared_db():
        c = sqlite3.connect("file:test_knowledge?mode=memory&cache=shared", uri=True)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA foreign_keys=ON")
        return c

    monkeypatch.setattr(k_mod, "get_db", _get_shared_db)
    yield conn
    conn.close()


def test_get_session_data_not_found(knowledge_db):
    from coworker.analytics.knowledge import get_session_data
    assert get_session_data("nonexistent") is None


def test_get_session_data_found(knowledge_db):
    from coworker.analytics.knowledge import get_session_data

    knowledge_db.execute(
        "INSERT INTO sessions (id, ide, created_at) VALUES (?, ?, ?)",
        ("s1", "claude", "2025-01-01"),
    )
    knowledge_db.execute(
        "INSERT INTO messages (session_id, seq, type, content, ts) VALUES (?, ?, ?, ?, ?)",
        ("s1", 1, "user", "hello", "2025-01-01T00:00:00"),
    )
    knowledge_db.execute(
        "INSERT INTO tool_calls (session_id, call_id, tool, ts) VALUES (?, ?, ?, ?)",
        ("s1", "c1", "Bash", "2025-01-01T00:00:01"),
    )
    knowledge_db.commit()

    data = get_session_data("s1")
    assert data is not None
    assert data["id"] == "s1"
    assert len(data["messages"]) == 1
    assert data["messages"][0]["content"] == "hello"
    assert len(data["tool_calls"]) == 1
    assert data["tool_calls"][0]["tool"] == "Bash"


def test_build_summary_prompt():
    from coworker.analytics.knowledge import build_summary_prompt

    data = {
        "project": "walter-worker",
        "initiative": "test-coverage",
        "messages": [{"role": "user"}],
        "tool_calls": [{"tool": "Bash"}],
    }
    prompt = build_summary_prompt(data)
    assert "walter-worker" in prompt
    assert "test-coverage" in prompt
    assert "Messages: 1" in prompt
    assert "Tool calls: 1" in prompt


def test_build_summary_prompt_minimal():
    from coworker.analytics.knowledge import build_summary_prompt

    data = {}
    prompt = build_summary_prompt(data)
    assert "Project: " in prompt
    assert "Messages: 0" in prompt


def test_write_summary(knowledge_db):
    from coworker.analytics.knowledge import write_summary

    knowledge_db.execute(
        "INSERT INTO sessions (id, ide, created_at) VALUES (?, ?, ?)",
        ("s1", "claude", "2025-01-01"),
    )
    knowledge_db.commit()

    write_summary("s1", {
        "context_to_remember": "ctx",
        "efficiency_tip": "tip",
        "memory_keywords": "kw",
        "efficiency_score": 0.8,
        "last_guide_attempt": "guide",
    })

    row = knowledge_db.execute(
        "SELECT * FROM session_summaries WHERE session_id = ?", ("s1",)
    ).fetchone()
    assert row is not None
    assert row["context_to_remember"] == "ctx"
    assert row["efficiency_tip"] == "tip"
    assert row["memory_keywords"] == "kw"


def test_write_summary_upsert(knowledge_db):
    from coworker.analytics.knowledge import write_summary

    knowledge_db.execute(
        "INSERT INTO sessions (id, ide, created_at) VALUES (?, ?, ?)",
        ("s1", "claude", "2025-01-01"),
    )
    knowledge_db.commit()

    write_summary("s1", {"context_to_remember": "first"})
    write_summary("s1", {"context_to_remember": "second"})

    row = knowledge_db.execute(
        "SELECT * FROM session_summaries WHERE session_id = ?", ("s1",)
    ).fetchone()
    assert row["context_to_remember"] == "second"


def test_write_knowledge_basic(knowledge_db, monkeypatch):
    from coworker.analytics.knowledge import write_knowledge

    knowledge_db.execute(
        "INSERT INTO sessions (id, ide, created_at) VALUES (?, ?, ?)",
        ("s1", "claude", "2025-01-01"),
    )
    knowledge_db.commit()

    cards = [
        {
            "session_id": "s1",
            "title": "Test Pattern",
            "type": "pattern",
            "project": "test",
            "skills": ["python"],
            "summary": "A test pattern",
            "evidence": ["file.py"],
        }
    ]
    write_knowledge(cards)

    rows = knowledge_db.execute("SELECT * FROM knowledge").fetchall()
    assert len(rows) == 1
    assert rows[0]["title"] == "Test Pattern"
    assert json.loads(rows[0]["skills"]) == ["python"]
    assert json.loads(rows[0]["evidence"]) == ["file.py"]


def test_write_knowledge_skips_duplicate(knowledge_db, monkeypatch):
    from coworker.analytics import knowledge as k_mod

    knowledge_db.execute(
        "INSERT INTO sessions (id, ide, created_at) VALUES (?, ?, ?)",
        ("s1", "claude", "2025-01-01"),
    )
    knowledge_db.commit()

    cards = [
        {
            "session_id": "s1",
            "title": "Same Pattern",
            "type": "pattern",
            "project": "test",
            "skills": [],
            "summary": "A",
            "evidence": [],
        }
    ]
    k_mod.write_knowledge(cards)
    # Write again — should skip duplicate
    k_mod.write_knowledge(cards)

    rows = knowledge_db.execute("SELECT * FROM knowledge").fetchall()
    assert len(rows) == 1


def test_write_knowledge_empty_list(knowledge_db):
    from coworker.analytics.knowledge import write_knowledge
    write_knowledge([])  # should not error
    rows = knowledge_db.execute("SELECT * FROM knowledge").fetchall()
    assert len(rows) == 0


def test_get_all_sessions_since_yesterday(knowledge_db):
    from coworker.analytics.knowledge import get_all_sessions_since

    today = datetime.now().strftime("%Y-%m-%d")
    knowledge_db.execute(
        "INSERT INTO sessions (id, ide, created_at) VALUES (?, ?, ?)",
        ("s_recent", "claude", today),
    )
    knowledge_db.execute(
        "INSERT INTO sessions (id, ide, created_at) VALUES (?, ?, ?)",
        ("s_old", "claude", "2020-01-01"),
    )
    knowledge_db.commit()

    ids = get_all_sessions_since("yesterday")
    assert "s_recent" in ids
    assert "s_old" not in ids


def test_get_all_sessions_since_all(knowledge_db):
    from coworker.analytics.knowledge import get_all_sessions_since

    knowledge_db.execute(
        "INSERT INTO sessions (id, ide, created_at) VALUES (?, ?, ?)",
        ("s1", "claude", "2025-01-01"),
    )
    knowledge_db.execute(
        "INSERT INTO sessions (id, ide, created_at) VALUES (?, ?, ?)",
        ("s2", "claude", "2025-01-02"),
    )
    knowledge_db.commit()

    ids = get_all_sessions_since("all")
    assert ids == ["s1", "s2"]
