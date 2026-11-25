"""Normalization shared by the importers, and the one-off database repair."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from coworker.analytics.normalize import canonical_tool, minutes_between, project_from_cwd, utc_iso


def test_utc_iso_accepts_every_stored_format():
    assert utc_iso("2026-11-24T19:43:02.450Z") == "2026-11-24T19:43:02.450Z"
    assert utc_iso("2026-11-24T00:01:46-0800") == "2026-11-24T08:01:46.000Z"
    assert utc_iso("2026-06-10T17:34:00+08:00") == "2026-06-10T09:34:00.000Z"
    assert utc_iso(1795563034896) == "2026-11-24T23:30:34.896Z"
    assert utc_iso("") == "" and utc_iso(None) == "" and utc_iso("garbage") == ""


def test_project_from_cwd():
    home = Path("/home/u")
    assert project_from_cwd("/home/u/project/repo/src", home) == "repo"
    assert project_from_cwd("/home/u", home) == "home"
    assert project_from_cwd("/tmp/x/scratchpad/", home) == "scratchpad"
    assert project_from_cwd("", home) == ""


def test_canonical_tool_and_minutes():
    assert canonical_tool("bash") == "Bash" and canonical_tool("github_search") == "github_search"
    assert minutes_between("2026-01-01T00:00:00.000Z", "2026-01-01T01:30:00.000Z") == 90
    assert minutes_between("", "x") is None


def test_repair_removes_seed_and_duplicates_and_keeps_orphans(monkeypatch, tmp_path):
    from coworker.analytics import auto_import, repair as rep
    from coworker.analytics.db import init_db

    db = tmp_path / "analytics.db"
    conn = init_db(db)
    conn.executescript("""
      INSERT INTO sessions (id, ide, project, cwd, created_at) VALUES
        ('claude-20260610T173400-631', 'claude', 'dotfiles', '/x', '2026-06-10T17:34:00+08:00'),
        ('orphan', 'claude', '-home-u-project-repo', '', '2026-07-01T10:00:00-0700'),
        ('2026-07-02-T143004-ii176n', 'opencode', '', '/tmp', '2026-07-02T21:30:04.208Z');
      INSERT INTO messages (session_id, seq, type, content, ts) VALUES ('orphan', 1, 'user', 'hi', '');
      INSERT INTO tool_calls (session_id, call_id, tool, args, ts) VALUES
        ('orphan', 'c1', 'Skill', '{"skill":"commit"}', ''), ('orphan', 'c2', 'bash', '{}', '');
      INSERT INTO skills (name, total_calls) VALUES ('seeded', 25);
      INSERT INTO knowledge (title, type, session_id, generated_at) VALUES ('fake', 'best', 'claude-20260610T173400-631', 'x');
    """)
    conn.commit()
    conn.close()
    oc = sqlite3.connect(tmp_path / "opencode.db")
    oc.executescript("""CREATE TABLE session (id TEXT, parent_id TEXT, directory TEXT, model TEXT,
        cost REAL, tokens_input INT, tokens_output INT, tokens_reasoning INT, tokens_cache_read INT,
        tokens_cache_write INT, time_created INT, time_updated INT);
        CREATE TABLE message (id TEXT, session_id TEXT, time_created INT, data TEXT);
        CREATE TABLE part (id TEXT, message_id TEXT, session_id TEXT, time_created INT, data TEXT);
        INSERT INTO session VALUES ('ses_a', NULL, '/tmp', NULL, 0, 0, 0, 0, 0, 0, 1783027804208, 1783027864208);""")
    oc.commit()
    oc.close()
    monkeypatch.setattr(auto_import, "OPCODE_DB", tmp_path / "opencode.db")
    monkeypatch.setattr(auto_import, "CLAUDE_PROJECTS", tmp_path / "none")
    monkeypatch.setattr(auto_import, "SESSIONS", tmp_path / "none")

    report = rep.repair(db, verbose=False)

    c = sqlite3.connect(db)
    assert sorted(r[0] for r in c.execute("SELECT id FROM sessions")) == ["orphan", "ses_a"]
    assert (report["seed_sessions"], report["opencode_duplicates"], report["fake_knowledge"]) == (1, 1, 1)
    assert c.execute("SELECT ide, project, created_at FROM sessions WHERE id='orphan'").fetchone() == (
        "claude-code", "repo", "2026-07-01T17:00:00.000Z")
    assert c.execute("SELECT message_count, tool_count, skill_count FROM session_stats "
                     "WHERE session_id='orphan'").fetchone() == (1, 2, 1)
    assert c.execute("SELECT name, total_calls FROM skills").fetchall() == [("commit", 1)]
    assert sorted(r[0] for r in c.execute("SELECT tool FROM tool_calls")) == ["Bash", "Skill"]
    assert Path(report["backup"]).exists()
