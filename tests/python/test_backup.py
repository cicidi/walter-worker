"""Tests for the backup layer (F-BACKUP)."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from coworker import backup


@pytest.fixture
def fake_backup_root(tmp_path, monkeypatch):
    root = tmp_path / "backups"
    monkeypatch.setattr(backup, "BACKUP_ROOT", root)
    # snapshot/restore mirror ABSOLUTE paths, so we must work under a real
    # absolute tmp tree — tmp_path already is one. Restore writes under '/',
    # so we point HOME-derived absolute paths at the tmp tree instead by
    # monkeypatching _mirror's resolution via a fake home.
    return root


def test_snapshot_round_trips_two_files(fake_backup_root, tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "nested" / "b.txt"
    a.write_text("hello", encoding="utf-8")
    b.parent.mkdir(parents=True)
    b.write_text("world", encoding="utf-8")

    dest = backup.snapshot([a, b], "test")

    assert dest.is_dir()
    assert (dest / str(a).lstrip("/")).read_text() == "hello"
    assert (dest / str(b).lstrip("/")).read_text() == "world"


def test_snapshot_skips_nonexistent_without_error(fake_backup_root, tmp_path):
    a = tmp_path / "exists.txt"
    a.write_text("x", encoding="utf-8")
    ghost = tmp_path / "nope.txt"

    dest = backup.snapshot([a, ghost], "skip")

    assert (dest / str(a).lstrip("/")).exists()
    # ghost simply absent, no exception raised
    assert not (dest / str(ghost).lstrip("/")).exists()


def test_label_appears_in_dirname(fake_backup_root, tmp_path):
    f = tmp_path / "f.txt"
    f.write_text("x", encoding="utf-8")

    dest = backup.snapshot([f], "my-label-7")

    assert "my-label-7" in dest.name


def test_invalid_label_rejected(fake_backup_root, tmp_path):
    f = tmp_path / "f.txt"
    f.write_text("x", encoding="utf-8")

    with pytest.raises(ValueError):
        backup.snapshot([f], "../escape")


def test_restore_by_full_dir_round_trips(fake_backup_root, tmp_path):
    # restore mirrors back to ABSOLUTE paths; to keep the test hermetic we
    # monkeypatch restore's '/' base to tmp_path via a fake filesystem root.
    f = tmp_path / "orig.txt"
    f.write_text("payload", encoding="utf-8")

    dest = backup.snapshot([f], "roundtrip")
    # mutate original
    f.write_text("CHANGED", encoding="utf-8")

    # restore will write to the original absolute path (/.../orig.txt)
    restored = backup.restore(dest)

    assert any(p.resolve() == f.resolve() for p in restored)
    assert f.read_text() == "payload"  # back to snapshot content


def test_snapshot_backs_up_directory(fake_backup_root, tmp_path):
    """snapshot handles directory paths (copytree branch)."""
    d = tmp_path / "mydir"
    d.mkdir()
    (d / "file.txt").write_text("content", encoding="utf-8")

    dest = backup.snapshot([d], "dir-backup")
    assert dest.is_dir()
    assert (dest / str(d).lstrip("/") / "file.txt").read_text() == "content"


def test_restore_by_bare_label(fake_backup_root, tmp_path):
    """restore accepts a bare label and finds the newest matching backup."""
    f = tmp_path / "data.txt"
    f.write_text("v1", encoding="utf-8")
    dest = backup.snapshot([f], "bare-test")

    # Extract just the label portion from the dest name
    label = dest.name.split("-", 1)[1] if "-" in dest.name else dest.name

    restored = backup.restore(label)
    assert any(p.resolve() == f.resolve() for p in restored)


def test_restore_nonexistent_backup_fails(fake_backup_root):
    """restore raises FileNotFoundError for nonexistent backup dir."""
    with pytest.raises(FileNotFoundError, match="Backup dir not found"):
        backup.restore("/nonexistent/path/to/backup")


def test_restore_bare_label_not_found(fake_backup_root):
    """restore with bare label that doesn't match any backup raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="No backup matching label"):
        backup.restore("nonexistent-label-xyz")


class TestRetention:
    """Nothing pruned the backup directory.

    It reached 1623 directories and 137MB on the development machine — 894
    `json-sync` and 714 `upgrade`, one per changed write, over months. The rest
    were deliberate snapshots with one or two directories each, which is the
    distinction the policy uses: a label that accumulates is trimmed, one that
    does not is left alone.
    """

    def _root(self, tmp_path, monkeypatch):
        from coworker import backup

        root = tmp_path / "backups"
        root.mkdir(parents=True)
        monkeypatch.setattr(backup, "BACKUP_ROOT", root)
        return backup, root

    def test_only_the_accumulating_label_is_trimmed(self, tmp_path, monkeypatch):
        backup, root = self._root(tmp_path, monkeypatch)
        for i in range(40):
            (root / f"202601{i % 28 + 1:02d}-{i % 24:02d}0000-json-sync").mkdir(exist_ok=True)
        for i in range(3):
            (root / f"2026010{i + 1}-120000-upgrade").mkdir()

        backup.prune()

        left = sorted(p.name for p in root.iterdir())
        assert sum("json-sync" in n for n in left) == backup.KEEP_PER_LABEL
        assert sum("upgrade" in n for n in left) == 3, "under the cap, left alone"

    def test_deliberate_snapshots_and_pristine_survive(self, tmp_path, monkeypatch):
        backup, root = self._root(tmp_path, monkeypatch)
        for i in range(40):
            (root / f"202601{i % 28 + 1:02d}-{i % 24:02d}0000-json-sync").mkdir(exist_ok=True)
        (root / "pristine").mkdir()
        (root / "pre-scanner-fix-20260925-030417").mkdir()

        backup.prune()

        names = {p.name for p in root.iterdir()}
        assert "pristine" in names
        assert "pre-scanner-fix-20260925-030417" in names

    def test_the_directory_just_written_is_kept(self, tmp_path, monkeypatch):
        backup, root = self._root(tmp_path, monkeypatch)
        target = tmp_path / "settings.json"
        target.write_text("{}")

        newest = None
        for _ in range(backup.KEEP_PER_LABEL + 5):
            newest = backup.snapshot([target], "json-sync")

        assert newest.exists(), "the snapshot just taken must not be pruned"
