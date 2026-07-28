"""Auto-import daemon: scan sessions, store metadata + stats only. Raw data lives at source."""
import json
import time
from pathlib import Path
from datetime import datetime
from .db import get_db

HOME = Path.home()
BASE = HOME / ".coworker" / "analytics"
SESSIONS = BASE / "sessions"
OPCODE_DB = HOME / ".local" / "share" / "opencode" / "opencode.db"
CLAUDE_PROJECTS = HOME / ".claude" / "projects"
POLL_INTERVAL = 1800


def _parse_session_id(session_dir: Path) -> str:
    """Read session_id from session.yaml, falling back to directory name."""
    yaml_file = session_dir / "session.yaml"
    if yaml_file.exists():
        for line in yaml_file.read_text(encoding="utf-8").strip().split("\n"):
            if line.startswith("session_id:"):
                val = line.split(":", 1)[1].strip().strip('"')
                if val:
                    return val
    return session_dir.name


def _get_skills(jsonl_file: Path) -> set:
    """Extract unique skill names from a Claude Code JSONL session."""
    skills = set()
    if not jsonl_file.exists():
        return skills
    for line in jsonl_file.read_text().strip().split("\n"):
        try:
            obj = json.loads(line)
            msg = obj.get("message", {})
            if isinstance(msg, dict):
                content = msg.get("content", []) if isinstance(msg.get("content"), list) else []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Skill":
                        sname = block.get("input", {}).get("name", "")
                        if sname:
                            skills.add(sname)
        except json.JSONDecodeError:
            continue
    return skills


def _count_jsonl_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return len([l for l in path.read_text().strip().split("\n") if l.strip()])


def _count_jsonl_skill_calls(path: Path) -> set:
    """Count Skill invocations in a Claude Code JSONL session."""
    skills = set()
    if not path.exists():
        return skills
    for line in path.read_text().strip().split("\n"):
        try:
            obj = json.loads(line)
            msg = obj.get("message", {})
            if isinstance(msg, dict):
                for block in msg.get("content", []) if isinstance(msg.get("content"), list) else []:
                    if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "Skill":
                        sname = block.get("input", {}).get("name", "")
                        if sname:
                            skills.add(sname)
        except json.JSONDecodeError:
            continue
    return skills


def import_claude_jsonl(jsonl_file: Path, conn):
    """Store session metadata + stats + file ops from Claude Code JSONL."""
    sid = jsonl_file.stem
    lines = jsonl_file.read_text().strip().split("\n")
    msg_count = len(lines)

    created = ""
    model = ""
    cwd = ""
    active_skill = None
    file_count = 0
    read_count = 0
    write_count = 0

    for seq, line in enumerate(lines):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        if obj.get("type") == "assistant" and not created:
            created = obj.get("timestamp", "")
            mi = obj.get("message", {})
            if isinstance(mi, dict):
                model = mi.get("model", "")
        if obj.get("cwd") and not cwd:
            cwd = obj["cwd"]

        msg = obj.get("message", {})
        ts = obj.get("timestamp", "")

        if not isinstance(msg, dict):
            continue

        content = msg.get("content", []) if isinstance(msg.get("content"), list) else []
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            tname = block.get("name", "")

            if btype == "tool_use" and tname == "Skill":
                active_skill = block.get("input", {}).get("name", "") or None
                sname = active_skill
                if sname:
                    conn.execute("INSERT OR IGNORE INTO skills (name) VALUES (?)", (sname,))
                    conn.execute("UPDATE skills SET total_calls = total_calls + 1 WHERE name = ?", (sname,))

            elif btype == "tool_use" and tname in ("Read", "Write", "Edit", "Glob", "Bash"):
                file_count += 1
                args = block.get("input", {})
                fpath = args.get("file_path") or args.get("path") or args.get("filePath") or ""
                op = tname.lower()

                if tname in ("Read", "Glob"):
                    read_count += 1
                elif tname in ("Write", "Edit"):
                    write_count += 1

                if fpath:
                    file_type = Path(fpath).suffix.lstrip(".") or None
                    conn.execute(
                        """INSERT OR IGNORE INTO file_ops (session_id, call_id, op, path, file_type, project, skill_name, seq, ts)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (sid, block.get("id", f"{sid}-{seq}"), op, fpath, file_type,
                         jsonl_file.parent.name, active_skill, seq, ts),
                    )

            elif btype == "tool_use" and tname not in ("Skill", "Read", "Write", "Edit", "Glob", "Bash"):
                # Non-skill, non-file tool — end skill context if one was active
                active_skill = None

    conn.execute(
        """INSERT OR REPLACE INTO sessions (id, ide, project, cwd, model, created_at)
           VALUES (?, 'claude-code', ?, ?, ?, ?)""",
        (sid, jsonl_file.parent.name, cwd, model, created or ""),
    )

    conn.execute(
        """INSERT OR REPLACE INTO session_stats
           (session_id, message_count, tool_count, skill_count, read_count, write_count, bash_count, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (sid, msg_count, file_count, len(_get_skills(jsonl_file)), read_count, write_count, 0, datetime.now().isoformat()),
    )
    conn.commit()


def import_claude_hooks(session_dir: Path, conn):
    """Store metadata from Claude Code hooks session directory."""
    sid = session_dir.name
    yaml_file = session_dir / "session.yaml"
    msgs_file = session_dir / "messages.jsonl"
    tools_file = session_dir / "tools.jsonl"

    msg_count = _count_jsonl_lines(msgs_file)
    tool_count = _count_jsonl_lines(tools_file)

    info = {}
    if yaml_file.exists():
        for line in yaml_file.read_text().strip().split("\n"):
            if ":" in line:
                k, _, v = line.partition(":")
                info[k.strip()] = v.strip().strip('"')

    # Delegate to full import_session for complete data (initiative, branch, tokens, messages, tool_calls)
    from .import_data import import_session as full_import
    try:
        full_import(session_dir, conn)
    except Exception:
        # Fallback: minimal metadata import if full import fails
        conn.execute(
            """INSERT OR REPLACE INTO sessions (id, ide, project, cwd, model, created_at)
               VALUES (?, 'claude-code', ?, ?, ?, ?)""",
            (sid, info.get("project", ""), info.get("cwd", ""), info.get("model", ""), info.get("created", "")),
        )
        conn.execute(
            """INSERT OR REPLACE INTO session_stats
               (session_id, message_count, tool_count, updated_at)
               VALUES (?, ?, ?, ?)""",
            (sid, msg_count, tool_count, datetime.now().isoformat()),
        )
        conn.commit()


def import_opencode_meta(conn):
    """Import OpenCode session metadata from opencode.db."""
    if not OPCODE_DB.exists():
        return 0
    import sqlite3
    existing = set(
        r[0] for r in conn.execute("SELECT id FROM sessions WHERE ide='opencode'").fetchall()
    )
    try:
        oc = sqlite3.connect(str(OPCODE_DB))
        oc.row_factory = sqlite3.Row
        rows = oc.execute(
            "SELECT id, title, model, cost, tokens_input, tokens_output, time_created "
            "FROM session WHERE title IS NOT NULL AND title != ''"
        ).fetchall()
        oc.close()
    except sqlite3.Error:
        return 0

    count = 0
    for row in rows:
        sid = row["id"]
        if sid in existing:
            continue
        created = row["time_created"]
        if created:
            try:
                created = datetime.fromtimestamp(int(created) / 1000).isoformat()
            except (ValueError, TypeError, OSError):
                pass
        conn.execute(
            """INSERT OR REPLACE INTO sessions (id, ide, model, created_at)
               VALUES (?, 'opencode', ?, ?)""",
            (sid, row["model"] or "", created or ""),
        )
        conn.execute(
            """INSERT OR REPLACE INTO session_stats
               (session_id, message_count, tool_count, updated_at)
               VALUES (?, ?, ?, ?)""",
            (sid, 0, 0, datetime.now().isoformat()),
        )
        count += 1
    conn.commit()
    return count


def run_once(verbose: bool = False) -> dict:
    conn = get_db()
    stats = {"claude_jsonl": 0, "claude_hooks": 0, "opencode": 0, "skipped": 0}

    existing = set(r[0] for r in conn.execute("SELECT id FROM sessions").fetchall())

    # --- Claude Code JSONL ---
    if CLAUDE_PROJECTS.exists():
        for project_dir in sorted(CLAUDE_PROJECTS.iterdir()):
            if not project_dir.is_dir():
                continue
            for jsonl_file in sorted(project_dir.glob("*.jsonl")):
                sid = jsonl_file.stem
                if sid in existing:
                    stats["skipped"] += 1
                    continue
                try:
                    import_claude_jsonl(jsonl_file, conn)
                    existing.add(sid)
                    stats["claude_jsonl"] += 1
                    if verbose:
                        print(f"  [claude-jsonl] {sid}")
                except Exception as e:
                    if verbose:
                        print(f"  [claude-jsonl] fail {sid}: {e}")

    # --- Claude Code hooks ---
    if SESSIONS.exists():
        for session_dir in sorted(SESSIONS.iterdir()):
            if not session_dir.is_dir() or session_dir.name.startswith('.') or session_dir.name.startswith('_'):
                continue
            if not (session_dir / "session.yaml").exists():
                continue
            # Use session_id from session.yaml (matches Claude Code's real session
            # id from hook JSON), not the directory name, so multiple Stop events
            # for the same conversation map to one DB session.
            sid = _parse_session_id(session_dir)
            if sid in existing:
                stats["skipped"] += 1
                continue
            try:
                import_claude_hooks(session_dir, conn)
                existing.add(sid)
                stats["claude_hooks"] += 1
                if verbose:
                    print(f"  [claude-hooks] {sid}")
            except Exception as e:
                if verbose:
                    print(f"  [claude-hooks] fail {sid}: {e}")

    # --- OpenCode ---
    oc_count = import_opencode_meta(conn)
    stats["opencode"] = oc_count

    conn.close()
    return stats


def run_daemon(interval: int = POLL_INTERVAL):
    print(f"[daemon] Auto-import started (interval: {interval}s, {interval//60}min)")
    print(f"[daemon] Claude JSONL: {CLAUDE_PROJECTS}")
    print(f"[daemon] Claude hooks: {SESSIONS}")
    print(f"[daemon] OpenCode DB:  {OPCODE_DB}")

    while True:
        stats = run_once(verbose=True)
        total = stats["claude_jsonl"] + stats["claude_hooks"] + stats["opencode"]
        print(f"[daemon] {datetime.now().strftime('%H:%M:%S')} "
              f"claude_jsonl={stats['claude_jsonl']} claude_hooks={stats['claude_hooks']} "
              f"opencode={stats['opencode']} skipped={stats['skipped']}")
        time.sleep(interval)
