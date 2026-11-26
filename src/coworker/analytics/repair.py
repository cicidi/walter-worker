"""One-off repair of an analytics.db written by the old importers.

What it fixes, each found by comparing the database with its sources:

* Rows written by ``scripts/seed_dashboard.py`` (ids ``opencode-20…`` /
  ``claude-20…`` stamped ``+08:00``) and the knowledge cards derived from them,
  plus one test fixture card (``sess-auth-1``), sat among real sessions.
* Every OpenCode session existed twice: once from opencode.db (with no
  messages or tools) and once from the hooks under a generated id.
* Times were stored in three formats; projects and IDEs under two names each.
* session_stats disagreed with the rows it summarises.

Sessions whose transcript Claude Code has since deleted are kept: the database
is the only record left of them. The original file is copied aside first.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import auto_import
from .db import _default_db_path, get_db
from .normalize import canonical_tool, project_from_cwd, project_from_slug, utc_iso

_CHILD_TABLES = ("messages", "tool_calls", "file_ops", "session_stats",
                 "session_summaries", "knowledge_sessions", "graph_queries")


def _delete_sessions(conn, ids: list[str]) -> None:
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        marks = ",".join("?" * len(chunk))
        for t in _CHILD_TABLES:
            conn.execute(f"DELETE FROM {t} WHERE session_id IN ({marks})", chunk)
        conn.execute(f"UPDATE knowledge SET session_id = NULL WHERE session_id IN ({marks})", chunk)
        conn.execute(f"DELETE FROM sessions WHERE id IN ({marks})", chunk)


def _opencode_hook_duplicates(conn) -> list[str]:
    """OpenCode sessions not from opencode.db whose start matches an
    opencode.db session within two minutes."""
    if not auto_import.OPCODE_DB.exists():
        return []
    oc = sqlite3.connect(f"file:{auto_import.OPCODE_DB}?mode=ro", uri=True)
    starts = sorted(r[0] / 1000 for r in oc.execute("SELECT time_created FROM session"))
    oc_ids = {r[0] for r in oc.execute("SELECT id FROM session")}
    oc.close()
    dups = []
    for sid, created in conn.execute("SELECT id, created_at FROM sessions WHERE ide = 'opencode'"):
        if sid in oc_ids:
            continue
        iso = utc_iso(created)
        if not iso:
            continue
        t = datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp()
        if any(abs(s - t) < 120 for s in starts):
            dups.append(sid)
    return dups


def repair(db_path: str | Path | None = None, verbose: bool = True) -> dict:
    path = Path(db_path) if db_path else _default_db_path()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_name(f"{path.name}.bak-{stamp}")
    conn = get_db(path)
    # The backup API, not a file copy: the database runs in WAL mode and a copy
    # of the main file alone misses whatever is still in the -wal file.
    with sqlite3.connect(backup) as dst:
        conn.backup(dst)
    report: dict = {"backup": str(backup)}

    seed = [r[0] for r in conn.execute(
        "SELECT id FROM sessions WHERE (id GLOB 'opencode-20*' OR id GLOB 'claude-20*') "
        "AND created_at LIKE '%+08:00'")]
    fake_cards = [r[0] for r in conn.execute(
        "SELECT id FROM knowledge WHERE session_id IN ({}) OR session_id = 'sess-auth-1'".format(
            ",".join("?" * len(seed)) or "''"), seed)]
    for kid in fake_cards:
        conn.execute("DELETE FROM knowledge_sessions WHERE knowledge_id = ?", (kid,))
        conn.execute("DELETE FROM knowledge WHERE id = ?", (kid,))
    dups = _opencode_hook_duplicates(conn)
    # Sub-agent sessions are folded into their root by import_opencode now;
    # left as rows of their own they count twice.
    subagents = []
    if auto_import.OPCODE_DB.exists():
        oc = sqlite3.connect(f"file:{auto_import.OPCODE_DB}?mode=ro", uri=True)
        child_ids = {r[0] for r in oc.execute("SELECT id FROM session WHERE parent_id IS NOT NULL")}
        oc.close()
        subagents = [r[0] for r in conn.execute("SELECT id FROM sessions WHERE ide = 'opencode'")
                     if r[0] in child_ids]
    _delete_sessions(conn, seed + dups + subagents)
    report.update(seed_sessions=len(seed), fake_knowledge=len(fake_cards),
                  opencode_duplicates=len(dups), opencode_subagents=len(subagents))

    # Normalize what no source can re-import any more.
    for sid, ide, project, cwd, created, closed in conn.execute(
            "SELECT id, ide, project, cwd, created_at, closed_at FROM sessions").fetchall():
        proj = project_from_cwd(cwd) if cwd else project_from_slug(project or "")
        conn.execute(
            "UPDATE sessions SET ide = ?, project = ?, created_at = ?, closed_at = ? WHERE id = ?",
            ("claude-code" if ide == "claude" else ide, proj or None,
             utc_iso(created), utc_iso(closed), sid))
    # File ops written before their session's cwd was known carry the
    # transcript-folder slug. Give them their session's project, or the name
    # the slug stands for when the session has none.
    conn.execute("""UPDATE file_ops SET project = (SELECT s.project FROM sessions s WHERE s.id = file_ops.session_id)
                    WHERE project LIKE '-%' AND EXISTS (SELECT 1 FROM sessions s
                        WHERE s.id = file_ops.session_id AND COALESCE(s.project, '') != '')""")
    for (slug,) in conn.execute("SELECT DISTINCT project FROM file_ops WHERE project LIKE '-%'").fetchall():
        conn.execute("UPDATE file_ops SET project = ? WHERE project = ?", (project_from_slug(slug), slug))
    for table in ("messages", "tool_calls", "file_ops"):
        rows = conn.execute(f"SELECT id, ts FROM {table} WHERE ts IS NOT NULL AND ts != '' "
                            f"AND ts NOT GLOB '????-??-??T??:??:??.???Z'").fetchall()
        conn.executemany(f"UPDATE {table} SET ts = ? WHERE id = ?", [(utc_iso(t), i) for i, t in rows])
    for tool in [r[0] for r in conn.execute("SELECT DISTINCT tool FROM tool_calls")]:
        if canonical_tool(tool) != tool:
            conn.execute("UPDATE tool_calls SET tool = ? WHERE tool = ?", (canonical_tool(tool), tool))
    conn.commit()
    conn.close()

    # run_once opens the default database; point it at the one being repaired.
    previous = os.environ.get("COWORKER_ANALYTICS_DB")
    os.environ["COWORKER_ANALYTICS_DB"] = str(path)
    try:
        report["reimport"] = auto_import.run_once(force=True)
    finally:
        if previous is None:
            os.environ.pop("COWORKER_ANALYTICS_DB", None)
        else:
            os.environ["COWORKER_ANALYTICS_DB"] = previous

    conn = get_db(path)
    # Stats from the rows themselves, for sessions no importer touched.
    for (sid,) in conn.execute("SELECT id FROM sessions").fetchall():
        row = conn.execute("SELECT read_count, write_count, bash_count, duration_min, tokens_input, "
                           "tokens_output, tokens_reasoning, tokens_cache_read, tokens_cache_write, cost "
                           "FROM session_stats WHERE session_id = ?", (sid,)).fetchone()
        r = tuple(row) if row else (0,) * 10
        created, closed = conn.execute(
            "SELECT created_at, closed_at FROM sessions WHERE id = ?", (sid,)).fetchone()
        dur = r[3] if r[3] is not None else auto_import.minutes_between(created or "", closed or "")
        updated = conn.execute("SELECT updated_at FROM session_stats WHERE session_id = ?", (sid,)).fetchone()
        auto_import._write_stats(conn, sid, r[0] or 0, r[1] or 0, r[2] or 0, dur,
                                 tokens=tuple(x or 0 for x in r[4:9]), cost=r[9] or 0)
        if updated:
            conn.execute("UPDATE session_stats SET updated_at = ? WHERE session_id = ?", (updated[0], sid))

    # Skills from the calls actually stored: the old totals mixed in seed data.
    conn.execute("DELETE FROM skills")
    conn.execute(
        """INSERT INTO skills (name, total_calls, first_invoked, last_invoked)
           SELECT COALESCE(json_extract(args,'$.skill'), json_extract(args,'$.name')) AS n,
                  COUNT(*), MIN(ts), MAX(ts)
           FROM tool_calls WHERE tool = 'Skill' AND json_valid(args) AND n IS NOT NULL AND n != ''
           GROUP BY n""")
    conn.commit()
    report["sessions"] = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    conn.close()
    if verbose:
        for k, v in report.items():
            print(f"  {k}: {v}")
    return report
