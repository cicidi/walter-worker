"""Smoke tests for the analytics CLI subcommands — guards the P1 class:
packaging (relative imports) and the once/stats-key crash. Uses CliRunner
against a temp DB via COWORKER_ANALYTICS_DB, never the developer's real DB.
"""
from click.testing import CliRunner

from coworker.cli import main


def test_analytics_create_db_and_once(tmp_path, monkeypatch):
    """create-db then once both exit 0 against a temp DB.

    Regression guard for:
      - P1: 'coworker analytics once' crashed with KeyError on wrong stat keys
      - P1: modules unimportable when installed (from src.coworker... -> relative)
      - get_db() now bootstraps the schema, so 'once' works on a fresh DB
    """
    db = tmp_path / "analytics.db"
    monkeypatch.setenv("COWORKER_ANALYTICS_DB", str(db))
    monkeypatch.setenv("HOME", str(tmp_path))

    runner = CliRunner()
    r1 = runner.invoke(main, ["analytics", "create-db"])
    assert r1.exit_code == 0, f"create-db failed: {r1.output}\n{r1.exception}"
    assert db.exists()

    r2 = runner.invoke(main, ["analytics", "once"])
    assert r2.exit_code == 0, f"once failed: {r2.output}\n{r2.exception}"
    # the fixed summary line uses the real stat keys
    assert "claude_jsonl=" in r2.output
    assert "opencode=" in r2.output
