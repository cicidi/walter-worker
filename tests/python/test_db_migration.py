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


# ---------------------------------------------------------------------------
# Schema drift: objects that existed only in long-lived databases
# ---------------------------------------------------------------------------

REQUIRED_SESSION_STAT_COLUMNS = (
    "tokens_input", "tokens_output", "cost", "turn_count",
    "tokens_reasoning", "tokens_cache_read", "tokens_cache_write",
)


def _table_names(path) -> set:
    conn = sqlite3.connect(str(path))
    try:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()


def _columns_of(path, table) -> list:
    conn = sqlite3.connect(str(path))
    try:
        return [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
    finally:
        conn.close()


def test_fresh_database_has_token_columns(tmp_path):
    """A fresh install must have every column the dashboard queries reference.

    These existed only in long-lived databases, so query_projects (which serves
    /api/projects) failed on a fresh install with "no such column: ss.tokens_input".
    """
    db = tmp_path / "fresh.db"
    get_db(db).close()

    columns = _columns_of(db, "session_stats")
    for name in REQUIRED_SESSION_STAT_COLUMNS:
        assert name in columns, f"fresh session_stats is missing {name}"


def test_fresh_database_has_knowledge_sessions(tmp_path):
    """knowledge_sessions is read by cli.py and the dashboard, but was declared
    nowhere, so a fresh install got "no such table" on those paths."""
    db = tmp_path / "fresh.db"
    get_db(db).close()

    assert "knowledge_sessions" in _table_names(db)


def test_migration_backfills_old_session_summaries(tmp_path):
    """CREATE TABLE IF NOT EXISTS never alters an existing table, so databases
    predating last_guide_attempt never got it and write_summary() failed."""
    db = tmp_path / "old.db"
    conn = sqlite3.connect(str(db))
    conn.execute(
        """CREATE TABLE session_summaries (
               session_id TEXT PRIMARY KEY, generated_at TEXT NOT NULL)"""
    )
    conn.execute(
        "INSERT INTO session_summaries (session_id, generated_at) VALUES ('s1', 'now')"
    )
    conn.commit()
    conn.close()
    assert "last_guide_attempt" not in _columns_of(db, "session_summaries")

    get_db(db).close()

    assert "last_guide_attempt" in _columns_of(db, "session_summaries")
    conn = sqlite3.connect(str(db))
    try:
        assert conn.execute(
            "SELECT generated_at FROM session_summaries WHERE session_id = 's1'"
        ).fetchone()[0] == "now", "existing rows must survive the migration"
    finally:
        conn.close()
