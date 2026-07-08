"""Tests for cohort init --project (P2 fixes: mkdir, sentinel, backup)."""
from click.testing import CliRunner

from coworker.cli import main


def test_init_project_creates_coworker_dir(tmp_path, monkeypatch):
    """Fresh init on empty dir creates .coworker/coworker.yaml (mkdir fix)."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    # confirm "Create project config?" -> y (default)
    result = runner.invoke(main, ["init", "--project"], input="y\n")
    assert result.exit_code == 0, f"init failed: {result.output}"
    assert (tmp_path / ".coworker" / "coworker.yaml").exists()


def test_init_project_idempotent(tmp_path, monkeypatch):
    """Second init skips CLAUDE.md regeneration (sentinel match fix)."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(main, ["init", "--project"], input="y\n")
    claude_md = tmp_path / "CLAUDE.md"
    first_content = claude_md.read_text()
    assert first_content

    # run again — should skip (detects Project Identity sentinel)
    result = runner.invoke(main, ["init", "--project"], input="y\n")
    assert result.exit_code == 0
    assert claude_md.read_text() == first_content, "CLAUDE.md was overwritten on re-init"
    assert "already has project context" in result.output


def test_init_over_handwritten_claude_md_backs_up(tmp_path, monkeypatch):
    """Init over a hand-written CLAUDE.md takes a backup before overwriting."""
    monkeypatch.chdir(tmp_path)
    # backup writes to Path.home()/.coworker/backups; redirect to tmp_path
    from coworker import backup as bu
    monkeypatch.setattr(bu, "BACKUP_ROOT", tmp_path / ".coworker" / "backups")

    original = "# My Hand-Written Notes\n\nimportant content\n"
    (tmp_path / "CLAUDE.md").write_text(original, encoding="utf-8")

    # The sentinel won't match -> overwrite path -> backup
    runner = CliRunner()
    result = runner.invoke(main, ["init", "--project"], input="y\n")
    assert result.exit_code == 0, f"init failed: {result.output}"

    new_content = (tmp_path / "CLAUDE.md").read_text()
    assert "## Project Identity" in new_content  # template was written
    assert original != new_content

    # backup dir should exist with a snapshot of the original
    backup_root = tmp_path / ".coworker" / "backups"
    assert backup_root.is_dir()
    backups = list(backup_root.glob("*-init"))
    assert backups, "no backup taken"
    # the backup should contain the hand-written content
    backup_content = None
    for bd in backups:
        mirrored = bd / str(tmp_path / "CLAUDE.md").lstrip("/")
        if mirrored.exists():
            backup_content = mirrored.read_text()
    assert backup_content and original in backup_content, \
        f"hand-written content not found in backup; got: {backup_content!r}"
