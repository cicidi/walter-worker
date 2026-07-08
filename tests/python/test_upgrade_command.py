"""Tests for the worker upgrade command (G1)."""
import json
from pathlib import Path

from click.testing import CliRunner

from coworker.cli import main
from coworker.templates.global_claude_md import generate_global_claude_md


def _setup_home(tmp_path, monkeypatch, content=None):
    home = tmp_path / "home"
    home.mkdir()
    claude = home / ".claude"
    claude.mkdir(parents=True)
    md = claude / "CLAUDE.md"
    if content is not None:
        md.write_text(content, encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    return md


def test_upgrade_pristine_is_up_to_date(tmp_path, monkeypatch):
    """Upgrade over a freshly generated file reports 'already up to date'."""
    prist = generate_global_claude_md()
    _setup_home(tmp_path, monkeypatch, content=prist)

    runner = CliRunner()
    result = runner.invoke(main, ["upgrade", "--yes"])
    assert result.exit_code == 0, f"failed: {result.output}"
    assert "Already up to date" in result.output


def test_upgrade_user_edited_keeps_user_sections(tmp_path, monkeypatch):
    """User-added sections survive; modified sections overwrite; merge completes."""
    orig = generate_global_claude_md()
    # Modify a template section to trigger OVERWRITE, and add a user section
    edited = orig.replace("Behavioral guidelines to reduce common LLM coding mistakes.",
                          "MY CUSTOM BODY TEXT")
    edited += "\n## My Custom Rules\nmy content\n"
    md = _setup_home(tmp_path, monkeypatch, content=edited)

    runner = CliRunner()
    result = runner.invoke(main, ["upgrade", "--yes"])
    assert result.exit_code == 0, f"failed: {result.output}"

    out = md.read_text()
    assert "My Custom Rules" in out
    assert "my content" in out
    assert "CLAUDE.md upgraded" in result.output


def test_upgrade_dry_run_writes_nothing(tmp_path, monkeypatch):
    """--dry-run prints a plan but does not write."""
    orig = generate_global_claude_md()
    edited = orig + "\n## Extra\nx\n"
    md = _setup_home(tmp_path, monkeypatch, content=edited)

    before = md.read_text()
    runner = CliRunner()
    result = runner.invoke(main, ["upgrade", "--dry-run"])
    assert result.exit_code == 0
    assert "--dry-run" in result.output
    assert md.read_text() == before  # unchanged


def test_upgrade_no_tty_without_yes_refuses(tmp_path, monkeypatch):
    """When stdout is not a TTY and --yes is absent, refuse."""
    orig = generate_global_claude_md()
    edited = orig + "\n## X\nx\n"
    _setup_home(tmp_path, monkeypatch, content=edited)

    runner = CliRunner()
    # CliRunner's stdout is not a TTY by default
    result = runner.invoke(main, ["upgrade"])
    assert "stdout is not a TTY" in result.output
