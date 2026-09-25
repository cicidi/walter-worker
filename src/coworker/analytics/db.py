import sqlite3
import os
from pathlib import Path

def _default_db_path() -> Path:
    return Path(os.environ.get("COWORKER_ANALYTICS_DB",
               str(Path.home() / ".coworker" / "analytics" / "analytics.db")))

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id            TEXT PRIMARY KEY,
    ide           TEXT NOT NULL,
    project       TEXT,
    cwd           TEXT,
    model         TEXT,
    feature       TEXT,
    branch        TEXT,
    created_at    TEXT NOT NULL,
    closed_at     TEXT,
    graph_enabled INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS messages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL REFERENCES sessions(id),
    seq           INTEGER NOT NULL,
    type          TEXT NOT NULL,
    content       TEXT,
    ts            TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_msg_unique ON messages(session_id, seq);
CREATE INDEX IF NOT EXISTS idx_msg_session_seq ON messages(session_id, seq);

CREATE TABLE IF NOT EXISTS tool_calls (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES sessions(id),
    call_id         TEXT NOT NULL,
    tool            TEXT NOT NULL,
    tool_type       TEXT DEFAULT 'builtin',
    server_name     TEXT,
    parent_call_id  TEXT,
    parent_skill    TEXT,
    args            TEXT,
    result          TEXT,
    duration_ms     INTEGER,
    seq_before      INTEGER,
    seq_after       INTEGER,
    ts              TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_tc_unique ON tool_calls(session_id, call_id);
CREATE INDEX IF NOT EXISTS idx_tc_session ON tool_calls(session_id);
CREATE INDEX IF NOT EXISTS idx_tc_parent ON tool_calls(parent_call_id);
CREATE INDEX IF NOT EXISTS idx_tc_tool ON tool_calls(tool);

CREATE TABLE IF NOT EXISTS file_ops (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    call_id     TEXT NOT NULL,
    op          TEXT NOT NULL,
    path        TEXT NOT NULL,
    file_type   TEXT,
    project     TEXT,
    skill_name  TEXT,
    seq         INTEGER NOT NULL,
    ts          TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_fo_unique ON file_ops(session_id, call_id, op, path);
CREATE INDEX IF NOT EXISTS idx_fo_session ON file_ops(session_id);
CREATE INDEX IF NOT EXISTS idx_fo_type ON file_ops(file_type);
CREATE INDEX IF NOT EXISTS idx_fo_project ON file_ops(project);

CREATE TABLE IF NOT EXISTS session_stats (
    session_id    TEXT PRIMARY KEY REFERENCES sessions(id),
    message_count INTEGER DEFAULT 0,
    tool_count    INTEGER DEFAULT 0,
    skill_count   INTEGER DEFAULT 0,
    read_count    INTEGER DEFAULT 0,
    write_count   INTEGER DEFAULT 0,
    bash_count    INTEGER DEFAULT 0,
    duration_min  INTEGER,
    updated_at    TEXT NOT NULL,
    -- Token/cost accounting. These were present in long-lived databases but
    -- missing from this schema, so a fresh install got 9 columns while the
    -- queries referenced 16 and any query touching these crashed with
    -- "no such column" (query_projects served the dashboard's Projects view).
    tokens_input       INTEGER DEFAULT 0,
    tokens_output      INTEGER DEFAULT 0,
    cost               INTEGER DEFAULT 0,
    turn_count         INTEGER DEFAULT 0,
    tokens_reasoning   INTEGER DEFAULT 0,
    tokens_cache_read  INTEGER DEFAULT 0,
    tokens_cache_write INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS skills (
    name           TEXT PRIMARY KEY,
    total_calls    INTEGER DEFAULT 0,
    last_invoked   TEXT,
    first_invoked  TEXT
);

CREATE TABLE IF NOT EXISTS knowledge (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT NOT NULL,
    type            TEXT NOT NULL,
    session_id      TEXT REFERENCES sessions(id),
    project         TEXT,
    skills          TEXT,
    summary         TEXT,
    evidence        TEXT,
    generated_at    TEXT NOT NULL,
    merged_to_skill TEXT
);
CREATE INDEX IF NOT EXISTS idx_knowledge_project ON knowledge(project);
CREATE INDEX IF NOT EXISTS idx_knowledge_session ON knowledge(session_id);

CREATE TABLE IF NOT EXISTS session_summaries (
    session_id             TEXT PRIMARY KEY REFERENCES sessions(id),
    sop_workflows          TEXT,
    context_to_remember    TEXT,
    effective_operations   TEXT,
    pitfalls_and_fixes     TEXT,
    wasted_actions         TEXT,
    bottlenecks            TEXT,
    efficiency_tip         TEXT,
    last_guide_attempt     TEXT,
    efficiency_score       REAL,
    think_action_ratio     REAL,
    edit_redundancy        REAL,
    loop_count             INTEGER,
    user_wait_minutes      REAL,
    memory_keywords        TEXT,
    generated_at           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS graph_queries (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT REFERENCES sessions(id),
    query           TEXT NOT NULL,
    graph_hits      INTEGER DEFAULT 0,
    graph_useful    INTEGER DEFAULT 0,
    avoided_tools   TEXT,
    graph_misses    TEXT,
    ts              TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_gq_session ON graph_queries(session_id);
"""


def get_db(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = Path(db_path) if db_path else _default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    # Idempotently ensure the schema exists so every entrypoint (once/daemon/
    # import/dashboard) works on a fresh DB without an explicit create-db first.
    # Every statement in SCHEMA is CREATE ... IF NOT EXISTS, so this is safe to repeat.
    conn.executescript(SCHEMA)
    # Migration: add graph_enabled column to existing databases (spec §9.5)
    _migrate_add_graph_enabled(conn)
    _migrate_add_session_stat_columns(conn)
    _migrate_rename_initiative_to_feature(conn)
    conn.commit()
    return conn


# Token/cost accounting on session_stats, in the order they were introduced.
_SESSION_STAT_COLUMNS = (
    ("tokens_input", "INTEGER DEFAULT 0"),
    ("tokens_output", "INTEGER DEFAULT 0"),
    ("cost", "INTEGER DEFAULT 0"),
    ("turn_count", "INTEGER DEFAULT 0"),
    ("tokens_reasoning", "INTEGER DEFAULT 0"),
    ("tokens_cache_read", "INTEGER DEFAULT 0"),
    ("tokens_cache_write", "INTEGER DEFAULT 0"),
)


def _migrate_add_session_stat_columns(conn: sqlite3.Connection) -> None:
    """Add token/cost columns to databases created before SCHEMA declared them.

    These columns existed only in long-lived databases, so a fresh install was
    missing them while the dashboard queries referenced them - query_projects
    (which serves /api/projects) failed outright with "no such column". Now that
    SCHEMA declares them, a fresh database has them already and this is a no-op.
    """
    existing = {row[1] for row in conn.execute("PRAGMA table_info(session_stats)")}
    for name, decl in _SESSION_STAT_COLUMNS:
        if name not in existing:
            conn.execute(f"ALTER TABLE session_stats ADD COLUMN {name} {decl}")
    conn.commit()


def _migrate_add_graph_enabled(conn: sqlite3.Connection) -> None:
    """Add graph_enabled column if it doesn't exist (pre-v1 databases)."""
    try:
        conn.execute("SELECT graph_enabled FROM sessions LIMIT 0")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE sessions ADD COLUMN graph_enabled INTEGER DEFAULT 0")
        conn.commit()


def _migrate_rename_initiative_to_feature(conn: sqlite3.Connection) -> None:
    """Rename sessions.initiative -> feature on pre-rename databases.

    Data is preserved in place; only the column name changes. Idempotent — a
    fresh database already has `feature`, and an already-migrated one has no
    `initiative`, so both paths are no-ops.
    """
    columns = {row[1] for row in conn.execute("PRAGMA table_info(sessions)")}
    if "initiative" in columns and "feature" not in columns:
        conn.execute("ALTER TABLE sessions RENAME COLUMN initiative TO feature")
        conn.commit()


def init_db(db_path: str | Path | None = None) -> sqlite3.Connection:
    conn = get_db(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def list_all_sessions(conn: sqlite3.Connection) -> list[dict]:
    """List all sessions from the analytics database."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM sessions ORDER BY created_at").fetchall()
    return [dict(r) for r in rows]


def get_transcript(conn: sqlite3.Connection, session_id: str) -> list[dict]:
    """Get messages for a session formatted as transcript."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT type as role, content FROM messages WHERE session_id = ? ORDER BY seq",
        (session_id,),
    ).fetchall()
    return [dict(r) for r in rows]
