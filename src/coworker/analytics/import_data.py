import json
from pathlib import Path
from datetime import datetime
from .db import get_db

HOME = Path.home()
BASE = HOME / ".coworker" / "analytics"
SESSIONS = BASE / "sessions"


def parse_session_yaml(session_dir: Path) -> dict:
    yaml_file = session_dir / "session.yaml"
    if not yaml_file.exists():
        return {}
    data = {}
    for line in yaml_file.read_text().strip().split("\n"):
        if ":" in line:
            key, _, val = line.partition(":")
            data[key.strip()] = val.strip().strip('"')
    return data


def import_session(session_dir: Path, conn_or_path=None):
    conn = conn_or_path if hasattr(conn_or_path, 'execute') else get_db(conn_or_path)
    info = parse_session_yaml(session_dir)
    session_id = info.get("session_id", session_dir.name)

    conn.execute(
        """INSERT OR REPLACE INTO sessions (id, ide, project, cwd, model, initiative, branch, created_at, closed_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, info.get("ide", ""), info.get("project", ""), info.get("cwd", ""),
         info.get("model", ""), info.get("initiative", ""), info.get("branch", ""),
         info.get("created", ""), info.get("closed", "")),
    )

    msgs_file = session_dir / "messages.jsonl"
    if msgs_file.exists():
        for line in msgs_file.read_text().strip().split("\n"):
            if not line.strip():
                continue
            try:
                m = json.loads(line)
                conn.execute(
                    "INSERT OR IGNORE INTO messages (session_id, seq, type, content, ts) VALUES (?, ?, ?, ?, ?)",
                    (session_id, m.get("seq", 0), m.get("type", ""), m.get("content", ""), m.get("ts", "")),
                )
            except json.JSONDecodeError:
                continue

    pre_calls = {}
    post_calls = {}
    tools_file = session_dir / "tools.jsonl"
    if tools_file.exists():
        for line in tools_file.read_text().strip().split("\n"):
            if not line.strip():
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

        all_call_ids = set(pre_calls.keys()) | set(post_calls.keys())
        skill_call_ids = set()
        for cid in sorted(all_call_ids):
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

            if tool == "Skill":
                skill_call_ids.add(cid)

            conn.execute(
                """INSERT OR IGNORE INTO tool_calls
                   (session_id, call_id, tool, tool_type, server_name, args, result, duration_ms, seq_before, seq_after, ts)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (session_id, cid, tool, tool_type, server_name or None, args_json, result, duration,
                 seq_before, seq_after, ts),
            )

            if tool in ("Read", "Write", "Edit", "Glob") and pre.get("args"):
                args = pre["args"]
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                file_path = args.get("filePath") or args.get("path") or args.get("file_path") or ""
                if file_path:
                    op_map = {"Read": "read", "Write": "write", "Edit": "edit", "Glob": "glob"}
                    op = op_map.get(tool, tool.lower())
                    file_type = Path(file_path).suffix.lstrip(".") or None
                    project = info.get("project", "")
                    conn.execute(
                        """INSERT OR IGNORE INTO file_ops (session_id, call_id, op, path, file_type, project, seq, ts)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (session_id, cid, op, file_path, file_type, project, seq_before or 0, ts),
                    )

    skill_names = set()
    for cid in skill_call_ids:
        pre = pre_calls.get(cid, {})
        args = pre.get("args", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except json.JSONDecodeError:
                continue
        name = args.get("name", "") if isinstance(args, dict) else ""
        if name:
            skill_names.add(name)

    for name in skill_names:
        conn.execute("INSERT OR IGNORE INTO skills (name) VALUES (?)", (name,))
        conn.execute(
            """UPDATE skills SET total_calls = total_calls + 1,
               last_invoked = MAX(COALESCE(last_invoked, ''), ?),
               first_invoked = CASE WHEN first_invoked IS NULL THEN ? ELSE first_invoked END
               WHERE name = ?""",
            (info.get("created", ""), info.get("created", ""), name),
        )

    msg_count = conn.execute("SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,)).fetchone()[0]
    tool_count = conn.execute("SELECT COUNT(*) FROM tool_calls WHERE session_id = ?", (session_id,)).fetchone()[0]
    skill_count = conn.execute(
        "SELECT COUNT(*) FROM tool_calls WHERE session_id = ? AND tool = 'Skill'", (session_id,)
    ).fetchone()[0]
    read_count = conn.execute("SELECT COUNT(*) FROM file_ops WHERE session_id = ? AND op = 'read'", (session_id,)).fetchone()[0]
    write_count = conn.execute(
        "SELECT COUNT(*) FROM file_ops WHERE session_id = ? AND op IN ('write', 'edit')", (session_id,)
    ).fetchone()[0]
    bash_count = conn.execute(
        "SELECT COUNT(*) FROM tool_calls WHERE session_id = ? AND tool = 'Bash'", (session_id,)
    ).fetchone()[0]

    created = info.get("created", "")
    closed = info.get("closed", "")
    duration_min = None
    if created and closed:
        try:
            c1 = datetime.fromisoformat(created)
            c2 = datetime.fromisoformat(closed)
            duration_min = int((c2 - c1).total_seconds() / 60)
        except (ValueError, TypeError):
            pass

    conn.execute(
        """INSERT OR REPLACE INTO session_stats
           (session_id, message_count, tool_count, skill_count, read_count, write_count, bash_count, duration_min, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (session_id, msg_count, tool_count, skill_count, read_count, write_count, bash_count, duration_min,
         datetime.now().isoformat()),
    )
    conn.commit()


def import_all():
    conn = get_db()
    if not SESSIONS.exists():
        print("No sessions directory found")
        return
    for session_dir in sorted(SESSIONS.iterdir()):
        if session_dir.is_dir() and not session_dir.name.startswith('.'):
            yaml_file = session_dir / "session.yaml"
            if yaml_file.exists():
                print(f"Importing {session_dir.name}...")
                import_session(session_dir, conn)
    conn.close()
    print("Done.")


if __name__ == "__main__":
    import_all()
