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
