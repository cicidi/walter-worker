"""G9 tests: state-update opt-in gate + per-day file."""
import datetime
from pathlib import Path

from click.testing import CliRunner

from coworker.cli import main


def test_state_update_noop_outside_coworker(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(main, ["state-update"])
    assert result.exit_code == 0
    assert not (tmp_path / "docs").exists()


def test_state_update_activates_with_coworker_dir(tmp_path, monkeypatch):
    (tmp_path / ".coworker").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(main, ["state-update"])
    assert result.exit_code == 0
    state_dir = tmp_path / "docs" / "state"
    assert state_dir.is_dir()
    files = list(state_dir.glob("state-*.md"))
    assert len(files) == 1
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    assert today in files[0].name


def test_two_stops_one_file(tmp_path, monkeypatch):
    (tmp_path / ".coworker").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("HOME", str(tmp_path))
    runner = CliRunner()
    runner.invoke(main, ["state-update"])
    runner.invoke(main, ["state-update"])
    state_dir = tmp_path / "docs" / "state"
    files = list(state_dir.glob("state-*.md"))
    assert len(files) == 1
    content = files[0].read_text()
    assert content.count("## Update —") == 1
