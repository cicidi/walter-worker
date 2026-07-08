"""H3: coverage sweep — smoke tests for previously untested paths."""
from pathlib import Path

from coworker.analytics.auto_import import run_once
from coworker.analytics.db import get_db
from coworker.dashboard import queries
from coworker.templates.local_claude_md import inject_initiative_into_local_md


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
    content = "# Claude\n\n<!-- INITIATIVE_PLACEHOLDER -->\n\n## More\n"
    block = "<!-- INITIATIVE:foo START -->\n## foo\nstuff\n<!-- INITIATIVE:foo END -->"
    first = inject_initiative_into_local_md(content, block)
    for _ in range(5):
        result = inject_initiative_into_local_md(first, block)
        assert "foo" in result
        assert "INITIATIVE:foo" in result


def test_injection_adds_block():
    content = "# No placeholder\n\n## Done\n"
    block = "<!-- INITIATIVE:x START -->\nx\n<!-- INITIATIVE:x END -->"
    result = inject_initiative_into_local_md(content, block)
    assert "INITIATIVE:x" in result
