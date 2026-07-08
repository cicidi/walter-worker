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
    initiative    TEXT,
    branch        TEXT,
    created_at    TEXT NOT NULL,
    closed_at     TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id    TEXT NOT NULL REFERENCES sessions(id),
    seq           INTEGER NOT NULL,
    type          TEXT NOT NULL,
    content       TEXT,
    ts            TEXT NOT NULL
);
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
    updated_at    TEXT NOT NULL
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
    efficiency_score       REAL,
    think_action_ratio     REAL,
    edit_redundancy        REAL,
    loop_count             INTEGER,
    user_wait_minutes      REAL,
    memory_keywords        TEXT,
    generated_at           TEXT NOT NULL
);
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
    conn.commit()
    return conn


def init_db(db_path: str | Path | None = None) -> sqlite3.Connection:
    conn = get_db(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn
