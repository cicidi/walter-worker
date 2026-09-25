"""H3: coverage sweep — smoke tests for previously untested paths."""
from pathlib import Path

from coworker.analytics.auto_import import run_once
from coworker.analytics.db import get_db
from coworker.dashboard import queries
from coworker.templates.local_claude_md import inject_feature_into_local_md


def test_run_once_returns_expected_keys():
    result = run_once(verbose=False)
    for k in ("claude_jsonl", "claude_hooks", "opencode", "skipped"):
        assert k in result


def test_query_overview_works_on_empty_db(tmp_path, monkeypatch):
    db = tmp_path / "db.sqlite"
    monkeypatch.setenv("COWORKER_ANALYTICS_DB", str(db))
    monkeypatch.setattr(queries, "get_db", lambda: get_db(str(db)))
    r = queries.query_overview()
    assert "total_sessions" in r


def test_idempotent_injection():
    content = "# Claude\n\n<!-- FEATURE_PLACEHOLDER -->\n\n## More\n"
    block = "<!-- FEATURE:foo START -->\n## foo\nstuff\n<!-- FEATURE:foo END -->"
    first = inject_feature_into_local_md(content, block)
    for _ in range(5):
        result = inject_feature_into_local_md(first, block)
        assert "foo" in result
        assert "FEATURE:foo" in result


def test_injection_adds_block():
    content = "# No placeholder\n\n## Done\n"
    block = "<!-- FEATURE:x START -->\nx\n<!-- FEATURE:x END -->"
    result = inject_feature_into_local_md(content, block)
    assert "FEATURE:x" in result
