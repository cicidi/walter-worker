"""Auto-import daemon: scan sessions, store metadata + stats only. Raw data lives at source."""
import json
import time
from pathlib import Path
from datetime import datetime
from .db import get_db
from .normalize import canonical_tool, minutes_between, project_from_cwd, utc_iso

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


def _skill_name(block: dict) -> str:
    """The skill a Skill tool_use names. Claude Code sends it as "skill"; this
    read only "name", so no Claude Code session ever recorded a skill. "name"
    is still accepted for data written that way."""
    args = block.get("input") or {}
    return args.get("skill") or args.get("name") or ""


def _typed_prompt(obj: dict, msg: dict) -> str:
    """What the user typed, or "". Claude Code stores a typed prompt as a plain
    string, not a block list, and the importer read only lists — so not one
    typed prompt reached the database. Strings that Claude Code itself
    injected (promptSource "system", or isMeta) are not the user's words.
    Every other source is: "queued" (written while a turn ran),
    "suggestion_accepted", "sdk" (claude -p). Keeping only "typed" dropped
    those. Transcripts older than promptSource only have isMeta to go on."""
    if obj.get("type") != "user" or obj.get("isMeta"):
        return ""
    if obj.get("promptSource") == "system":
        return ""
    content = msg.get("content")
    return content.strip() if isinstance(content, str) else ""


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
                        sname = _skill_name(block)
                        if sname:
                            skills.add(sname)
        except json.JSONDecodeError:
            continue
    return skills


def _count_jsonl_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return len([line for line in path.read_text().strip().split("\n") if line.strip()])


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
                        sname = _skill_name(block)
                        if sname:
                            skills.add(sname)
        except json.JSONDecodeError:
            continue
    return skills


def import_claude_jsonl(jsonl_file: Path, conn):
    """Store a Claude Code session from its JSONL transcript.

    Only ``assistant`` entries are read for tool calls. ``api-request-blob``
    entries replay the whole context the model was sent, earlier tool calls
    included, so reading them counted one session's 437 tool calls as 838.
    """
    sid = jsonl_file.stem
    lines = jsonl_file.read_text().strip().split("\n")

    created = ""
    last_ts = ""
    model = ""
    cwd = ""
    active_skill = None
    read_count = write_count = bash_count = 0
    # file_ops, messages and tool_calls reference sessions(id), so they are
    # collected here and inserted after the session row exists.
    file_ops_rows: list[tuple] = []
    tool_call_rows: list[tuple] = []
    message_rows: list[tuple] = []
    seen_ids: set[str] = set()
    usage_by_msg: dict[str, dict] = {}
    # tool_use_id -> (is_error, error text) from the tool_result blocks.
    results: dict[str, tuple[int, str | None]] = {}

    # The Stop hook re-imports the same session after every reply; skill calls
    # counted by an earlier import must not be counted again.
    seen_calls = {r[0] for r in conn.execute(
        "SELECT call_id FROM tool_calls WHERE session_id = ?", (sid,))}

    for seq, line in enumerate(lines):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        etype = obj.get("type")
        ts = obj.get("timestamp", "")
        if obj.get("cwd") and not cwd:
            cwd = obj["cwd"]
        if etype not in ("user", "assistant"):
            continue
        if ts:
            created = created or ts
            last_ts = ts

        msg = obj.get("message", {})
        if not isinstance(msg, dict):
            continue
        if etype == "assistant":
            m = msg.get("model", "")
            if m and m != "<synthetic>":
                model = m
            if isinstance(msg.get("usage"), dict):
                usage_by_msg[msg.get("id") or f"{sid}-{seq}"] = msg["usage"]

        content = msg.get("content", []) if isinstance(msg.get("content"), list) else []

        # isMeta entries are skill bodies Claude Code inserts, not conversation.
        text = "" if obj.get("isMeta") else (_typed_prompt(obj, msg) or "\n".join(
            b.get("text", "") for b in content
            if isinstance(b, dict) and b.get("type") == "text"
        ).strip())
        if text:
            message_rows.append((sid, seq, etype, text, ts))

        if etype != "assistant":
            for b in content:
                if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("tool_use_id"):
                    err = 1 if b.get("is_error") else 0
                    out = b.get("content")
                    if isinstance(out, list):
                        out = "\n".join(x.get("text", "") for x in out if isinstance(x, dict))
                    results[b["tool_use_id"]] = (err, str(out or "")[:500] if err else None)
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            call_id = block.get("id", f"{sid}-{seq}")
            if call_id in seen_ids:
                continue
            seen_ids.add(call_id)
            tname = block.get("name", "")
            args = block.get("input") or {}

            if tname == "Skill":
                active_skill = _skill_name(block) or None
                if active_skill and call_id not in seen_calls:
                    conn.execute("INSERT OR IGNORE INTO skills (name) VALUES (?)", (active_skill,))
                    conn.execute(
                        "UPDATE skills SET total_calls = total_calls + 1, "
                        "first_invoked = COALESCE(first_invoked, ?), "
                        "last_invoked = MAX(COALESCE(last_invoked, ''), ?) WHERE name = ?",
                        (utc_iso(ts), utc_iso(ts), active_skill))
            elif tname not in ("Read", "Write", "Edit", "Glob", "Bash"):
                # Non-skill, non-file tool ends the skill context.
                active_skill = None

            tool_call_rows.append((
                sid, call_id, tname, "builtin", None, None,
                None if tname == "Skill" else active_skill,
                json.dumps(args), None, None, seq, seq, ts,
            ))

            if tname in ("Read", "Glob"):
                read_count += 1
            elif tname in ("Write", "Edit"):
                write_count += 1
            elif tname == "Bash":
                bash_count += 1
            fpath = args.get("file_path") or args.get("path") or args.get("filePath") or ""
            if fpath and tname in ("Read", "Write", "Edit", "Glob"):
                file_ops_rows.append(
                    (sid, call_id, tname.lower(), fpath, Path(fpath).suffix.lstrip(".") or None,
                     project_from_cwd(cwd) or jsonl_file.parent.name, active_skill, seq, ts)
                )

    project = project_from_cwd(cwd) or jsonl_file.parent.name
    created_u, closed_u = utc_iso(created), utc_iso(last_ts)
    # An upsert, not INSERT OR REPLACE: REPLACE deletes the old row first, and
    # the foreign keys from messages and tool_calls refuse that.
    conn.execute(
        """INSERT INTO sessions (id, ide, project, cwd, model, created_at, closed_at)
           VALUES (?, 'claude-code', ?, ?, ?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET ide='claude-code', project=excluded.project,
               cwd=excluded.cwd, model=excluded.model, created_at=excluded.created_at,
               closed_at=excluded.closed_at""",
        (sid, project, cwd, model, created_u, closed_u),
    )
    conn.executemany(
        "INSERT OR IGNORE INTO messages (session_id, seq, type, content, ts) VALUES (?, ?, ?, ?, ?)",
        message_rows)
    conn.executemany(
        """INSERT OR IGNORE INTO tool_calls
           (session_id, call_id, tool, tool_type, server_name, parent_call_id,
            parent_skill, args, result, duration_ms, seq_before, seq_after, ts)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        tool_call_rows)
    # A result arrives after its call, often in a later import.
    conn.executemany(
        "UPDATE tool_calls SET is_error = ?, result = COALESCE(?, result) "
        "WHERE session_id = ? AND call_id = ?",
        [(e, txt, sid, cid) for cid, (e, txt) in results.items()])
    conn.executemany(
        """INSERT OR IGNORE INTO file_ops (session_id, call_id, op, path, file_type, project, skill_name, seq, ts)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        file_ops_rows)

    def _u(key, sub=None):
        total = 0
        for u in usage_by_msg.values():
            v = u.get(key) if sub is None else (u.get(key) or {}).get(sub)
            total += v if isinstance(v, int) else 0
        return total

    _write_stats(conn, sid, read_count, write_count, bash_count,
                 minutes_between(created_u, closed_u),
                 tokens=(_u("input_tokens"), _u("output_tokens"),
                         _u("output_tokens_details", "thinking_tokens"),
                         _u("cache_read_input_tokens"), _u("cache_creation_input_tokens")),
                 cost=0)
    conn.commit()


def _write_stats(conn, sid, read_count, write_count, bash_count, duration_min,
                 tokens=(0, 0, 0, 0, 0), cost=0.0):
    """session_stats counts come from the rows stored for the session, so the
    sessions list, the overview and the detail view all agree."""
    msg_count = conn.execute("SELECT COUNT(*) FROM messages WHERE session_id = ?", (sid,)).fetchone()[0]
    tool_count = conn.execute("SELECT COUNT(*) FROM tool_calls WHERE session_id = ?", (sid,)).fetchone()[0]
    skill_count = conn.execute(
        "SELECT COUNT(*) FROM tool_calls WHERE session_id = ? AND tool = 'Skill'", (sid,)).fetchone()[0]
    turns = conn.execute(
        "SELECT COUNT(*) FROM messages WHERE session_id = ? AND type = 'user'", (sid,)).fetchone()[0]
    # Active minutes: gaps over 30 minutes between events are idle time. The
    # first-to-last span made a session resumed a week later read as 10,000m.
    active = conn.execute(
        """SELECT CAST(SUM(CASE WHEN gap <= 1800 THEN gap ELSE 0 END) / 60 AS INTEGER) FROM (
               SELECT (julianday(ts) - julianday(LAG(ts) OVER (ORDER BY ts))) * 86400 AS gap
               FROM (SELECT ts FROM messages WHERE session_id = ? AND ts != ''
                     UNION ALL SELECT ts FROM tool_calls WHERE session_id = ? AND ts != ''))""",
        (sid, sid)).fetchone()[0]
    if active is not None:
        duration_min = active
    conn.execute(
        """INSERT OR REPLACE INTO session_stats
           (session_id, message_count, tool_count, skill_count, read_count, write_count, bash_count,
            duration_min, updated_at, tokens_input, tokens_output, tokens_reasoning,
            tokens_cache_read, tokens_cache_write, cost, turn_count)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (sid, msg_count, tool_count, skill_count, read_count, write_count, bash_count,
         duration_min, datetime.now().isoformat(), *tokens, cost, turns),
    )


def import_claude_hooks(session_dir: Path, conn):
    """Store metadata from Claude Code hooks session directory."""
    # Must match _parse_session_id, which is what run_once dedups against. Using
    # the directory name here instead would insert under an id the dedup never
    # looks for, so every run would re-import the same session.
    sid = _parse_session_id(session_dir)
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

    # Delegate to full import_session for complete data (feature, branch, tokens, messages, tool_calls)
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


def _oc_model(raw) -> str:
    """OpenCode stores session.model as JSON ({"id": ..., "providerID": ...})."""
    if not raw:
        return ""
    try:
        m = json.loads(raw)
    except (TypeError, ValueError):
        return str(raw)
    return (m.get("id") or m.get("modelID") or "") if isinstance(m, dict) else str(m)


def import_opencode(conn, force: bool = False) -> int:
    """Import OpenCode sessions, with their messages and tool calls, from opencode.db.

    opencode.db is the only source for OpenCode: the old importer stored the
    session row and nothing else (0 messages, 0 tools for every session), and
    the hooks wrote a second copy of each session under a generated id.

    A sub-agent session (parent_id set) is folded into its root session, the
    way a Claude Code sub-agent belongs to the session that started it: its
    tool calls and token spend count there, and it is not a session of its own.
    A session is re-imported when OpenCode has updated it since the last import.
    """
    if not OPCODE_DB.exists():
        return 0
    import sqlite3
    try:
        oc = sqlite3.connect(f"file:{OPCODE_DB}?mode=ro", uri=True)
        oc.row_factory = sqlite3.Row
        sessions = oc.execute(
            "SELECT id, parent_id, directory, model, cost, tokens_input, tokens_output, "
            "tokens_reasoning, tokens_cache_read, tokens_cache_write, time_created, time_updated "
            "FROM session").fetchall()
    except sqlite3.Error:
        return 0

    by_id = {r["id"]: r for r in sessions}

    def root_of(sid):
        seen = set()
        while by_id.get(sid) and by_id[sid]["parent_id"] and sid not in seen:
            seen.add(sid)
            sid = by_id[sid]["parent_id"]
        return sid

    family: dict[str, list] = {}
    for r in sessions:
        family.setdefault(root_of(r["id"]), []).append(r)

    imported = {r[0]: r[1] for r in conn.execute(
        "SELECT session_id, updated_at FROM session_stats ss JOIN sessions s ON s.id = ss.session_id "
        "WHERE s.ide = 'opencode'")}

    count = 0
    for root_id, members in family.items():
        root = by_id.get(root_id)
        if root is None:
            continue
        last_update = utc_iso(max(m["time_updated"] or 0 for m in members))
        prev = imported.get(root_id)
        if prev and not force and prev >= last_update:
            continue
        ids = [m["id"] for m in members]
        marks = ",".join("?" * len(ids))
        try:
            msgs = oc.execute(
                f"SELECT id, session_id, time_created, json_extract(data,'$.role') AS role, "
                f"json_extract(data,'$.modelID') AS model FROM message "
                f"WHERE session_id IN ({marks}) ORDER BY time_created", ids).fetchall()
            parts = oc.execute(
                f"SELECT id, message_id, session_id, time_created, data FROM part "
                f"WHERE session_id IN ({marks}) AND json_extract(data,'$.type') IN ('text','tool') "
                f"ORDER BY time_created, id", ids).fetchall()
        except sqlite3.Error:
            continue

        cwd = root["directory"] or ""
        created = utc_iso(root["time_created"])
        model = next((m["model"] for m in reversed(msgs)
                      if m["session_id"] == root_id and m["role"] == "assistant" and m["model"]),
                     "") or _oc_model(root["model"])
        conn.execute(
            """INSERT INTO sessions (id, ide, project, cwd, model, created_at, closed_at)
               VALUES (?, 'opencode', ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET ide='opencode', project=excluded.project,
                   cwd=excluded.cwd, model=excluded.model, created_at=excluded.created_at,
                   closed_at=excluded.closed_at""",
            (root_id, project_from_cwd(cwd), cwd, model, created, last_update),
        )

        # Text of the root conversation only: a sub-agent's prompts are tool
        # traffic, not the user's conversation.
        role_of = {m["id"]: m["role"] for m in msgs}
        texts: dict[str, list[str]] = {}
        msg_ts: dict[str, int] = {m["id"]: m["time_created"] for m in msgs}
        read_c = write_c = bash_c = 0
        for seq, p in enumerate(parts):
            try:
                d = json.loads(p["data"])
            except (TypeError, ValueError):
                continue
            if d.get("type") == "text":
                if p["session_id"] == root_id and not d.get("synthetic") and (d.get("text") or "").strip():
                    texts.setdefault(p["message_id"], []).append(d["text"].strip())
                continue
            st = d.get("state") or {}
            tool = canonical_tool(d.get("tool", ""))
            args = st.get("input") or {}
            t = st.get("time") or {}
            dur = (t.get("end") - t.get("start")) if t.get("end") and t.get("start") else None
            out = st.get("output") if st.get("status") != "error" else st.get("error")
            ts = utc_iso(p["time_created"])
            call_id = d.get("callID") or p["id"]
            conn.execute(
                """INSERT INTO tool_calls
                   (session_id, call_id, tool, tool_type, server_name, args, result,
                    duration_ms, seq_before, seq_after, ts, is_error)
                   VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(session_id, call_id) DO UPDATE SET result=excluded.result,
                       duration_ms=excluded.duration_ms, is_error=excluded.is_error""",
                (root_id, call_id, tool, "builtin", json.dumps(args),
                 (str(out) if out is not None else "")[:2000], dur, seq, seq, ts,
                 {"error": 1, "completed": 0}.get(st.get("status"))),
            )
            if tool in ("Read", "Glob"):
                read_c += 1
            elif tool in ("Write", "Edit"):
                write_c += 1
            elif tool == "Bash":
                bash_c += 1
            fpath = args.get("filePath") or args.get("file_path") or args.get("path") or ""
            if fpath and tool in ("Read", "Write", "Edit", "Glob"):
                conn.execute(
                    """INSERT OR IGNORE INTO file_ops (session_id, call_id, op, path, file_type, project, seq, ts)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (root_id, call_id, tool.lower(), fpath, Path(fpath).suffix.lstrip(".") or None,
                     project_from_cwd(cwd), seq, ts),
                )
        for seq, (mid, chunks) in enumerate(sorted(texts.items(), key=lambda kv: msg_ts.get(kv[0], 0))):
            conn.execute(
                "INSERT OR REPLACE INTO messages (session_id, seq, type, content, ts) VALUES (?, ?, ?, ?, ?)",
                (root_id, seq, role_of.get(mid) or "assistant", "\n".join(chunks), utc_iso(msg_ts.get(mid))),
            )

        def tot(col):
            return sum(m[col] or 0 for m in members)
        _write_stats(conn, root_id, read_c, write_c, bash_c, minutes_between(created, last_update),
                     tokens=(tot("tokens_input"), tot("tokens_output"), tot("tokens_reasoning"),
                             tot("tokens_cache_read"), tot("tokens_cache_write")),
                     cost=round(tot("cost"), 6))
        # updated_at doubles as the "imported up to" mark compared above.
        conn.execute("UPDATE session_stats SET updated_at = ? WHERE session_id = ?",
                     (last_update, root_id))
        count += 1
    oc.close()
    conn.commit()
    return count


def _hook_ide(session_dir: Path) -> str:
    yaml_file = session_dir / "session.yaml"
    for line in yaml_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("ide:"):
            return line.split(":", 1)[1].strip().strip('"')
    return ""


def run_once(verbose: bool = False, force: bool = False) -> dict:
    """Import every session source. A Claude transcript is re-imported when the
    file changed after its last import, so a live session's counts keep up
    (skipping every known id froze them at the first Stop)."""
    conn = get_db()
    stats = {"claude_jsonl": 0, "claude_hooks": 0, "opencode": 0, "skipped": 0}

    existing = set(r[0] for r in conn.execute("SELECT id FROM sessions").fetchall())
    imported_at = dict(conn.execute("SELECT session_id, updated_at FROM session_stats").fetchall())
    jsonl_ids: set[str] = set()

    # --- Claude Code JSONL ---
    if CLAUDE_PROJECTS.exists():
        for project_dir in sorted(CLAUDE_PROJECTS.iterdir()):
            if not project_dir.is_dir():
                continue
            for jsonl_file in sorted(project_dir.glob("*.jsonl")):
                sid = jsonl_file.stem
                jsonl_ids.add(sid)
                mtime = datetime.fromtimestamp(jsonl_file.stat().st_mtime).isoformat()
                if not force and sid in existing and (imported_at.get(sid) or "") >= mtime:
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

    # --- Claude Code hooks (only when no transcript exists) ---
    if SESSIONS.exists():
        for session_dir in sorted(SESSIONS.iterdir()):
            if not session_dir.is_dir() or session_dir.name.startswith('.') or session_dir.name.startswith('_'):
                continue
            if not (session_dir / "session.yaml").exists():
                continue
            # opencode.db is the source for OpenCode; the hook copy carried a
            # generated id and duplicated every session.
            if _hook_ide(session_dir) == "opencode":
                continue
            sid = _parse_session_id(session_dir)
            if sid in existing or sid in jsonl_ids:
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
    stats["opencode"] = import_opencode(conn, force=force)

    conn.close()
    return stats


def run_daemon(interval: int = POLL_INTERVAL):
    print(f"[daemon] Auto-import started (interval: {interval}s, {interval//60}min)")
    print(f"[daemon] Claude JSONL: {CLAUDE_PROJECTS}")
    print(f"[daemon] Claude hooks: {SESSIONS}")
    print(f"[daemon] OpenCode DB:  {OPCODE_DB}")

    while True:
        stats = run_once(verbose=True)
        print(f"[daemon] {datetime.now().strftime('%H:%M:%S')} "
              f"claude_jsonl={stats['claude_jsonl']} claude_hooks={stats['claude_hooks']} "
              f"opencode={stats['opencode']} skipped={stats['skipped']}")
        time.sleep(interval)
