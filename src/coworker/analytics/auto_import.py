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
    return len([_l for _l in path.read_text().strip().split("\n") if _l.strip()])


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
    """Store session metadata + stats + file ops + messages from Claude Code JSONL."""
    sid = jsonl_file.stem
    lines = jsonl_file.read_text().strip().split("\n")
    msg_count = 0

    # Clear stale message/tool_call data so we can re-import with full content
    conn.execute("DELETE FROM messages WHERE session_id = ?", (sid,))
    conn.execute("DELETE FROM tool_calls WHERE session_id = ?", (sid,))

    created = ""
    model = ""
    cwd = ""
    branch = ""
    active_skill = None
    file_count = 0
    tool_count = 0
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
        if obj.get("gitBranch") and not branch:
            branch = obj["gitBranch"]

        msg = obj.get("message", {})
        ts = obj.get("timestamp", "")

        if not isinstance(msg, dict):
            continue

        # Import individual messages with content
        obj_type = obj.get("type", "")
        if obj_type in ("user", "assistant"):
            content_text = ""
            content_val = msg.get("content", "")
            if isinstance(content_val, list):
                parts = []
                for b in content_val:
                    if not isinstance(b, dict):
                        continue
                    bt = b.get("type", "")
                    if bt == "thinking":
                        parts.append(f"[thinking] {b.get('thinking', '')}")
                    elif bt == "text":
                        parts.append(b.get("text", ""))
                    elif bt == "tool_use":
                        parts.append(f"[tool: {b.get('name', '?')}] {json.dumps(b.get('input', {}))}")
                content_text = "\n".join(parts)
            elif content_val:
                content_text = str(content_val)
            if content_text:
                conn.execute(
                    "INSERT OR IGNORE INTO messages (session_id, seq, type, content, ts) VALUES (?, ?, ?, ?, ?)",
                    (sid, seq, obj_type, content_text[:10000], ts),
                )
                msg_count += 1
        elif obj_type == "system":
            content_text = obj.get("subtype", "") or ""
            if content_text:
                conn.execute(
                    "INSERT OR IGNORE INTO messages (session_id, seq, type, content, ts) VALUES (?, ?, ?, ?, ?)",
                    (sid, seq, "system", content_text, ts),
                )

        content = msg.get("content", []) if isinstance(msg.get("content"), list) else []
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            tname = block.get("name", "")
            input_str = json.dumps(block.get("input", {})) if block.get("input") else None

            if btype == "tool_use":
                tool_count += 1
                call_id = block.get("id", "") or f"{sid}-{seq}"
                conn.execute(
                    "INSERT OR IGNORE INTO tool_calls (session_id, call_id, tool, tool_type, args, parent_skill, seq_before, seq_after, ts) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (sid, call_id, tname, "builtin", input_str, active_skill, seq, seq, ts),
                )

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
        """INSERT OR IGNORE INTO sessions (id, ide, project, cwd, model, branch, created_at)
           VALUES (?, 'claude-code', ?, ?, ?, ?, ?)""",
        (sid, jsonl_file.parent.name, cwd, model, branch, created or ""),
    )

    # Estimate tokens from message content
    tokens_in = 0
    tokens_out = 0
    for seq, line in enumerate(lines):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = obj.get("message", {})
        if not isinstance(msg, dict):
            continue
        content = msg.get("content", []) if isinstance(msg.get("content"), list) else []
        msg_type = obj.get("type", "")
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                text = block.get("text", "")
                # Rough estimate: ~4 chars per token
                if msg_type == "user":
                    tokens_in += len(text) // 4
                else:
                    tokens_out += len(text) // 4
            elif block.get("type") == "tool_result":
                text = str(block.get("content", ""))
                tokens_in += len(text) // 4

    conn.execute(
        """INSERT INTO session_stats
           (session_id, message_count, tool_count, skill_count, read_count, write_count, bash_count, tokens_input, tokens_output, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(session_id) DO UPDATE SET
             message_count=excluded.message_count,
             tool_count=excluded.tool_count,
             skill_count=excluded.skill_count,
             read_count=excluded.read_count,
             write_count=excluded.write_count,
             bash_count=excluded.bash_count,
             tokens_input=excluded.tokens_input,
             tokens_output=excluded.tokens_output,
             updated_at=excluded.updated_at""",
        (sid, msg_count, tool_count, len(_get_skills(jsonl_file)), read_count, write_count, 0, tokens_in, tokens_out, datetime.now().isoformat()),
    )
    conn.commit()


def import_claude_hooks(session_dir: Path, conn):
    """Import messages, tool calls, and file ops from Claude Code hooks JSONL."""
    sid = _parse_session_id(session_dir)
    yaml_file = session_dir / "session.yaml"
    msgs_file = session_dir / "messages.jsonl"
    tools_file = session_dir / "tools.jsonl"

    info = {}
    if yaml_file.exists():
        for line in yaml_file.read_text().strip().split("\n"):
            if ":" in line:
                k, _, v = line.partition(":")
                info[k.strip()] = v.strip().strip('"')

    conn.execute(
        """INSERT OR REPLACE INTO sessions (id, ide, project, cwd, model, initiative, branch, created_at)
           VALUES (?, 'claude-code', ?, ?, ?, ?, ?, ?)""",
        (sid, info.get("project", ""), info.get("cwd", ""), info.get("model", ""),
         info.get("initiative", ""), info.get("branch", ""), info.get("created", "")),
    )

    # Import messages from messages.jsonl
    msg_count = 0
    if msgs_file.exists():
        for line in msgs_file.read_text().strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                m = json.loads(line)
                content = m.get("content", "")
                if content:
                    conn.execute(
                        "INSERT OR IGNORE INTO messages (session_id, seq, type, content, ts) VALUES (?, ?, ?, ?, ?)",
                        (sid, m.get("seq", 0), m.get("type", ""), content, m.get("ts", "")),
                    )
                    msg_count += 1
            except json.JSONDecodeError:
                continue

    # Import tool calls and file ops from tools.jsonl
    pre_calls = {}
    post_calls = {}
    tool_count = 0
    skill_names = set()

    if tools_file.exists():
        for line in tools_file.read_text().strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                t = json.loads(line)
            except json.JSONDecodeError:
                continue
            cid = t.get("call_id", "")
            if t.get("phase") == "before":
                pre_calls[cid] = t
            elif t.get("phase") == "after":
                post_calls[cid] = t

        for cid in sorted(set(pre_calls.keys()) | set(post_calls.keys())):
            pre = pre_calls.get(cid, {})
            post = post_calls.get(cid, {})
            tool = pre.get("tool") or post.get("tool", "")
            tool_type = pre.get("tool_type") or post.get("tool_type", "builtin")
            server_name = pre.get("server_name") or post.get("server_name", "")
            args_json = json.dumps(pre.get("args", {})) if pre.get("args") else None
            result = post.get("result", "") or ""
            duration = post.get("duration_ms") or 0
            seq_before = pre.get("seq")
            seq_after = post.get("seq")
            ts = pre.get("ts") or post.get("ts", "")

            if tool == "Skill" and args_json:
                try:
                    args = json.loads(args_json) if isinstance(args_json, str) else {}
                    if isinstance(args, dict) and args.get("name"):
                        skill_names.add(args["name"])
                except json.JSONDecodeError:
                    pass

            conn.execute(
                """INSERT OR IGNORE INTO tool_calls
                   (session_id, call_id, tool, tool_type, server_name, args, result, duration_ms, seq_before, seq_after, ts)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (sid, cid, tool, tool_type, server_name or None, args_json, result, duration,
                 seq_before, seq_after, ts),
            )
            tool_count += 1

            # File ops from read/write/edit/glob tools (case-insensitive)
            if tool.lower() in ("read", "write", "edit", "glob") and pre.get("args"):
                args = pre["args"]
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                file_path = args.get("filePath") or args.get("path") or args.get("file_path") or ""
                if file_path:
                    op = tool.lower()
                    file_type = Path(file_path).suffix.lstrip(".") or None
                    project = info.get("project", "")
                    conn.execute(
                        """INSERT OR IGNORE INTO file_ops
                           (session_id, call_id, op, path, file_type, project, seq, ts)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (sid, cid, op, file_path, file_type, project, seq_before or 0, ts),
                    )

    # Register skills
    for name in skill_names:
        conn.execute("INSERT OR IGNORE INTO skills (name) VALUES (?)", (name,))
        conn.execute(
            """UPDATE skills SET total_calls = total_calls + 1,
               last_invoked = MAX(COALESCE(last_invoked, ''), ?),
               first_invoked = CASE WHEN first_invoked IS NULL THEN ? ELSE first_invoked END
               WHERE name = ?""",
            (info.get("created", ""), info.get("created", ""), name),
        )

    # Update session_stats with real counts
    msg_count = conn.execute("SELECT COUNT(*) FROM messages WHERE session_id = ?", (sid,)).fetchone()[0]
    tool_count = conn.execute("SELECT COUNT(*) FROM tool_calls WHERE session_id = ?", (sid,)).fetchone()[0]
    skill_count = conn.execute(
        "SELECT COUNT(*) FROM tool_calls WHERE session_id = ? AND LOWER(tool) = 'skill'", (sid,)
    ).fetchone()[0]
    bash_count = conn.execute(
        "SELECT COUNT(*) FROM tool_calls WHERE session_id = ? AND LOWER(tool) = 'bash'", (sid,)
    ).fetchone()[0]
    read_count = conn.execute(
        "SELECT COUNT(*) FROM file_ops WHERE session_id = ? AND op = 'read'", (sid,)
    ).fetchone()[0]
    write_count = conn.execute(
        "SELECT COUNT(*) FROM file_ops WHERE session_id = ? AND op IN ('write', 'edit')", (sid,)
    ).fetchone()[0]
    turn_count = conn.execute(
        "SELECT COUNT(DISTINCT seq) FROM messages WHERE session_id = ? AND LOWER(type) = 'user'", (sid,)
    ).fetchone()[0]

    # Estimate tokens from message content (simple char/4 heuristic)
    tokens_in = 0
    tokens_out = 0
    msgs = conn.execute("SELECT content, type FROM messages WHERE session_id = ?", (sid,)).fetchall()
    for m in msgs:
        content_len = len(m["content"] or "")
        if m["type"] == "user":
            tokens_in += content_len // 4
        else:
            tokens_out += content_len // 4

    # Calculate duration from created/closed or last tool call
    duration_min = None
    created = info.get("created", "")
    closed = info.get("closed", "")
    if created:
        if not closed:
            # Try to get last timestamp from tools.jsonl
            last_ts = conn.execute(
                "SELECT MAX(ts) FROM tool_calls WHERE session_id = ?", (sid,)
            ).fetchone()[0]
            closed = last_ts if last_ts else datetime.now().isoformat()
        try:
            c1 = datetime.fromisoformat(created.replace('Z','+00:00'))
            c2 = datetime.fromisoformat(closed.replace('Z','+00:00'))
            duration_min = max(1, int((c2 - c1).total_seconds() / 60))
        except (ValueError, TypeError):
            pass

    conn.execute(
        """INSERT OR REPLACE INTO session_stats
           (session_id, message_count, tool_count, skill_count, read_count, write_count,
            bash_count, duration_min, tokens_input, tokens_output, turn_count, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (sid, msg_count, tool_count, skill_count, read_count, write_count,
         bash_count, duration_min, tokens_in, tokens_out, turn_count, datetime.now().isoformat()),
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
            "SELECT id, title, model, cost, tokens_input, tokens_output, "
            "tokens_reasoning, tokens_cache_read, tokens_cache_write, time_created "
            "FROM session WHERE title IS NOT NULL AND title != ''"
        ).fetchall()
        oc.close()
    except sqlite3.Error:
        return 0

    count = 0
    for row in rows:
        sid = row["id"]
        is_new = sid not in existing
        created = row["time_created"]
        if created:
            try:
                created = datetime.fromtimestamp(int(created) / 1000).isoformat()
            except (ValueError, TypeError, OSError):
                pass
        if is_new:
            conn.execute(
                """INSERT OR REPLACE INTO sessions (id, ide, model, created_at)
                   VALUES (?, 'opencode', ?, ?)""",
                (sid, row["model"] or "", created or ""),
            )
            existing.add(sid)
        else:
            if row["model"]:
                conn.execute("UPDATE sessions SET model=? WHERE id=?", (row["model"], sid))
        tokens_in = row["tokens_input"] or 0
        tokens_out = row["tokens_output"] or 0
        tokens_reason = row["tokens_reasoning"] or 0
        tokens_cr = row["tokens_cache_read"] or 0
        tokens_cw = row["tokens_cache_write"] or 0
        cost_val = row["cost"] or 0.0
        conn.execute(
            """INSERT INTO session_stats
               (session_id, message_count, tool_count,
                tokens_input, tokens_output, tokens_reasoning, tokens_cache_read, tokens_cache_write,
                cost, updated_at)
               VALUES (?, 0, 0, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET
                 tokens_input=excluded.tokens_input,
                 tokens_output=excluded.tokens_output,
                 tokens_reasoning=excluded.tokens_reasoning,
                 tokens_cache_read=excluded.tokens_cache_read,
                 tokens_cache_write=excluded.tokens_cache_write,
                 cost=excluded.cost,
                 updated_at=excluded.updated_at""",
            (sid, tokens_in, tokens_out, tokens_reason, tokens_cr, tokens_cw, cost_val,
             datetime.now().isoformat()),
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
        total = stats["claude_jsonl"] + stats["claude_hooks"] + stats["opencode"]  # noqa: F841
        print(f"[daemon] {datetime.now().strftime('%H:%M:%S')} "
              f"claude_jsonl={stats['claude_jsonl']} claude_hooks={stats['claude_hooks']} "
              f"opencode={stats['opencode']} skipped={stats['skipped']}")
        time.sleep(interval)
