"""Migration: sessions.initiative -> feature on databases created pre-rename.

`get_db()` runs the migration lazily on every connection, so these tests drive
it the same way a real analytics command would.
"""
import sqlite3

from coworker.analytics.db import get_db

# A database as it existed before the rename: `initiative`, and no `feature`.
PRE_RENAME_SCHEMA = """
CREATE TABLE sessions (
    id            TEXT PRIMARY KEY,
    ide           TEXT NOT NULL,
    project       TEXT,
    cwd           TEXT,
    model         TEXT,
    initiative    TEXT,
    branch        TEXT,
    created_at    TEXT NOT NULL,
    closed_at     TEXT,
    graph_enabled INTEGER DEFAULT 0
);
"""

ROWS = [
    ("s1", "claude", "proj", "/tmp", "opus", "alpha", "main", "2026-01-01", None, 0),
    ("s2", "claude", "proj", "/tmp", "opus", "beta", "main", "2026-01-02", None, 0),
    ("s3", "claude", "proj", "/tmp", "opus", None, "main", "2026-01-03", None, 0),
]


def _make_pre_rename_db(path) -> None:
    conn = sqlite3.connect(str(path))
    conn.executescript(PRE_RENAME_SCHEMA)
    conn.executemany("INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?)", ROWS)
    conn.commit()
    conn.close()


def _columns(path) -> list[str]:
    conn = sqlite3.connect(str(path))
    try:
        return [r[1] for r in conn.execute("PRAGMA table_info(sessions)")]
    finally:
        conn.close()


def _feature_values(path) -> list:
    conn = sqlite3.connect(str(path))
    try:
        return [r[0] for r in conn.execute("SELECT feature FROM sessions ORDER BY id")]
    finally:
        conn.close()


def test_rename_migrates_column_and_preserves_rows(tmp_path):
    db = tmp_path / "analytics.db"
    _make_pre_rename_db(db)
    assert "initiative" in _columns(db)

    get_db(db).close()

    columns = _columns(db)
    assert "feature" in columns
    assert "initiative" not in columns
    assert _feature_values(db) == ["alpha", "beta", None], "row data must be preserved"


def test_rename_migration_is_idempotent(tmp_path):
    db = tmp_path / "analytics.db"
    _make_pre_rename_db(db)

    get_db(db).close()
    after_first = _feature_values(db)
    get_db(db).close()  # second connection must not re-run or double-apply

    assert _feature_values(db) == after_first
    assert _columns(db).count("feature") == 1


def test_fresh_database_gets_feature_column(tmp_path):
    """A brand new database never has the old column at all."""
    db = tmp_path / "fresh.db"
    get_db(db).close()

    columns = _columns(db)
    assert "feature" in columns
    assert "initiative" not in columns
