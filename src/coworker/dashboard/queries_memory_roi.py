"""Is the memory work paying off? The evidence for the Memory page.

Memory is a pipeline: sessions are captured into lessons, lessons are stored
and curated, and stored lessons are meant to come back into later sessions.
Each stage leaves a different trace, so each is read from where it is recorded:

- capture   ~/.coworker/memory/audit.log (one line per capture attempt)
- store     mem0 (read with list_entries, which records no retrieval)
- recall    tool_calls in analytics.db (memory MCP tools, `coworker memory query`)
- inject    the MEMORY block in ~/CLAUDE.local.md and the MEMORY.md export
- summaries session_summaries in analytics.db

`use_count` is reported but flagged: until 2026-11-25 every dashboard view
bumped it, so it overstates real recalls.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from ..analytics.db import get_db

_AUDIT_RE = re.compile(
    r"^(?P<ts>\S+) sync (?P<trigger>\S+) (?P<session>\S+) tool=(?P<tool>\S+) "
    r"lessons=(?P<lessons>\d+) ms=(?P<ms>\d+) (?P<status>ok|error)(?: reason=(?P<reason>.*))?$")
_RECALL_SQL = """(tc.tool LIKE 'mcp__memory%' OR tc.tool LIKE 'memory-graph_%' OR (tc.tool = 'Bash' AND
    (tc.args LIKE '%coworker memory query%' OR tc.args LIKE '%coworker memory search%')))"""
_SUMMARY_FIELDS = ("context_to_remember", "memory_keywords", "sop_workflows", "effective_operations",
                   "pitfalls_and_fixes", "wasted_actions", "bottlenecks", "efficiency_tip", "efficiency_score")


def _capture(memory_dir: Path) -> dict:
    """Capture attempts from the audit log: volume, failures, and why they failed."""
    path = memory_dir / "audit.log"
    if not path.is_file():
        return {"available": False}
    days: dict[str, dict] = {}
    reasons: Counter = Counter()
    sessions, ok, errors, lessons, ms_total, unparsed = set(), 0, 0, 0, 0, 0
    for line in path.read_text(errors="replace").splitlines():
        m = _AUDIT_RE.match(line.strip())
        if not m:
            unparsed += bool(line.strip())
            continue
        d = days.setdefault(m["ts"][:10], {"day": m["ts"][:10], "ok": 0, "error": 0, "lessons": 0})
        d[m["status"]] += 1
        d["lessons"] += int(m["lessons"])
        sessions.add(m["session"])
        lessons += int(m["lessons"])
        ms_total += int(m["ms"])
        if m["status"] == "ok":
            ok += 1
        else:
            errors += 1
            reason = m["reason"] or ""
            try:
                reason = json.loads(reason) if reason else ""
            except ValueError:
                pass
            reasons[(str(reason).split("\n", 1)[0][:110]) or "(no reason recorded)"] += 1
    attempts = ok + errors
    return {
        "available": True, "attempts": attempts, "ok": ok, "errors": errors,
        "error_rate": round(errors / attempts, 4) if attempts else None,
        "lessons": lessons, "sessions": len(sessions), "unparsed_lines": unparsed,
        "avg_seconds": round(ms_total / attempts / 1000, 1) if attempts else None,
        "daily": sorted(days.values(), key=lambda d: d["day"]),
        "error_reasons": [{"reason": r, "count": c} for r, c in reasons.most_common(8)],
    }


def _store(entries: list[dict]) -> dict:
    meta = [e.get("metadata") or {} for e in entries]
    uses = sorted(int(m.get("use_count") or 0) for m in meta)
    per_day = Counter((e.get("created_at") or "")[:10] for e in entries)
    per_day.pop("", None)

    def top(key: str, n: int = 12) -> list[dict]:
        return [{"value": v or "(none)", "count": c} for v, c in Counter(m.get(key) for m in meta).most_common(n)]

    return {
        "total": len(entries), "by_type": top("type"), "by_state": top("state"),
        "by_project": top("project"), "top_topics": top("topic", 20),
        "source_sessions": len({m.get("source_session") for m in meta if m.get("source_session")}),
        "scored": sum(1 for m in meta if m.get("scored_at")),
        "created_daily": [{"day": d, "count": c} for d, c in sorted(per_day.items())],
        "use_count": {
            "never_used": sum(1 for u in uses if u == 0),
            "median": uses[len(uses) // 2] if uses else None,
            "max": uses[-1] if uses else None,
            "caveat": "Dashboard views bumped use_count until 2026-11-25, so it overstates real recalls.",
        },
    }


def _recall(conn) -> dict:
    """Explicit lookups: the agent asked memory a question during a session."""
    row = conn.execute(f"""SELECT COUNT(*), COUNT(DISTINCT tc.session_id), MAX(tc.ts)
                           FROM tool_calls tc WHERE {_RECALL_SQL}""").fetchone()
    monthly = [dict(r) for r in conn.execute(f"""
        SELECT strftime('%Y-%m', tc.ts, 'localtime') AS month, COUNT(*) AS calls,
               COUNT(DISTINCT tc.session_id) AS sessions
        FROM tool_calls tc WHERE {_RECALL_SQL} AND tc.ts != '' GROUP BY 1 ORDER BY 1""")]
    recent = [dict(r) for r in conn.execute(f"""
        SELECT tc.session_id, s.project, tc.tool, tc.ts,
               SUBSTR(COALESCE(CASE WHEN json_valid(tc.args) THEN COALESCE(
                   json_extract(tc.args, '$.query'), json_extract(tc.args, '$.command')) END, tc.args), 1, 240) AS args
        FROM tool_calls tc LEFT JOIN sessions s ON s.id = tc.session_id
        WHERE {_RECALL_SQL} ORDER BY tc.ts DESC LIMIT 15""")]
    return {"calls": row[0], "sessions": row[1], "last": row[2], "monthly": monthly, "recent": recent}


def _inject(memory_dir: Path, home: Path) -> dict:
    """What is handed to a new session without it asking."""
    out: dict = {"snapshot_lines": None, "export": None}
    local = home / "CLAUDE.local.md"
    if local.is_file():
        inside, n = False, 0
        for line in local.read_text(errors="replace").splitlines():
            if line.startswith("<!-- MEMORY:") and line.rstrip().endswith("START -->"):
                inside, n = True, 0
            elif line.startswith("<!-- MEMORY:") and line.rstrip().endswith("END -->"):
                inside = False
                out["snapshot_lines"] = n
            elif inside and line.strip() and not line.lstrip().startswith("<!--"):
                n += 1  # a placeholder comment is not a lesson
    export = memory_dir / "MEMORY.md"
    if export.is_file():
        head = export.read_text(errors="replace")[:400]
        gen = re.search(r"Generated: ([^\n]+)", head)
        total = re.search(r"Total entries: (\d+)", head)
        out["export"] = {"generated": gen[1].strip() if gen else None,
                         "entries": int(total[1]) if total else None, "bytes": export.stat().st_size}
    return out


def _summaries(conn) -> dict:
    total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    n, first, last = conn.execute(
        "SELECT COUNT(*), MIN(generated_at), MAX(generated_at) FROM session_summaries").fetchone()
    fields = []
    for col in _SUMMARY_FIELDS:
        filled = conn.execute(
            f"SELECT COUNT(*) FROM session_summaries WHERE COALESCE({col}, '') NOT IN ('', '0', '[]')"
        ).fetchone()[0]
        fields.append({"field": col, "filled": filled})
    return {"count": n, "sessions": total_sessions,
            "coverage": round(n / total_sessions, 4) if total_sessions else None,
            "first": first, "last": last, "fields": fields}


def _verdicts(cap: dict, store: dict | None, recall: dict, inject: dict, summ: dict, sessions: int) -> list[dict]:
    """Plain statements of what the evidence shows. tone: good | warn | bad."""
    v = []
    if store:
        v.append({"tone": "good", "text": f"{store['total']:,} lessons are stored, taken from "
                                          f"{store['source_sessions']} of {sessions} sessions."})
    if cap.get("available") and cap["attempts"]:
        tone = "bad" if cap["error_rate"] >= 0.2 else "good"
        v.append({"tone": tone, "text": f"{cap['errors']} of {cap['attempts']} capture attempts failed "
                                        f"({cap['error_rate']:.0%})."})
    tone = "bad" if recall["sessions"] <= max(2, sessions // 20) else "good"
    last = (recall["last"] or "")[:10] or "never"
    v.append({"tone": tone, "text": f"Agents looked memory up in {recall['sessions']} of {sessions} sessions "
                                    f"({recall['calls']} lookups; most recent {last})."})
    if inject.get("snapshot_lines") is not None:
        n = inject["snapshot_lines"]
        v.append({"tone": "bad" if n == 0 else "good",
                  "text": f"The memory block injected into ~/CLAUDE.local.md holds {n} lesson{'s' * (n != 1)}."})
    if summ["sessions"]:
        tone = "bad" if (summ["coverage"] or 0) < 0.2 else "good"
        v.append({"tone": tone, "text": f"{summ['count']} of {summ['sessions']} sessions have a summary "
                                        f"({(summ['coverage'] or 0):.0%}); the newest is from "
                                        f"{(summ['last'] or 'never')[:10]}."})
    return v


def memory_roi(mem0_client=None, memory_dir: str | Path | None = None, home: str | Path | None = None) -> dict:
    memory_dir = Path(memory_dir) if memory_dir else Path.home() / ".coworker" / "memory"
    home = Path(home) if home else Path.home()
    cap = _capture(memory_dir)
    inject = _inject(memory_dir, home)
    conn = get_db()
    try:
        recall = _recall(conn)
        summ = _summaries(conn)
        sessions = summ["sessions"]
    finally:
        conn.close()

    store, store_error = None, None
    try:
        if mem0_client is None:
            from coworker.memory.mem0_client import Mem0Client
            mem0_client = Mem0Client.from_config()
        store = _store(mem0_client.list_entries(top_k=100_000))
    except Exception as exc:  # mem0 missing, no API key, or the store is locked
        store_error = str(exc)[:200]

    funnel = [
        {"stage": "Sessions recorded", "value": sessions},
        {"stage": "Sessions that produced lessons", "value": store["source_sessions"] if store else None},
        {"stage": "Lessons stored", "value": store["total"] if store else None},
        {"stage": "Sessions that looked memory up", "value": recall["sessions"]},
    ]
    return {"funnel": funnel, "verdicts": _verdicts(cap, store, recall, inject, summ, sessions),
            "capture": cap, "store": store, "store_error": store_error, "recall": recall,
            "inject": inject, "summaries": summ}


def memories(q: str = "", project: str = "", type_: str = "", state: str = "", limit: int = 200,
             mem0_client=None) -> dict:
    """Browse stored lessons, newest first. Reads with list_entries: no use_count bump."""
    try:
        if mem0_client is None:
            from coworker.memory.mem0_client import Mem0Client
            mem0_client = Mem0Client.from_config()
        entries = mem0_client.list_entries(top_k=100_000)
    except Exception as exc:
        return {"total": 0, "rows": [], "error": str(exc)[:200]}
    needle = q.strip().lower()
    rows = []
    for e in entries:
        m = e.get("metadata") or {}
        if project and m.get("project") != project:
            continue
        if type_ and m.get("type") != type_:
            continue
        if state and m.get("state", "active") != state:
            continue
        text = e.get("memory") or ""
        if needle and needle not in (text + " " + str(m.get("topic", "")) + " " + str(m.get("problem", ""))).lower():
            continue
        rows.append({"id": e.get("id", ""), "memory": text, "created_at": e.get("created_at") or "",
                     "type": m.get("type", ""), "project": m.get("project", ""), "topic": m.get("topic", ""),
                     "problem": m.get("problem", ""), "state": m.get("state", "active"),
                     "use_count": m.get("use_count", 0), "last_used": m.get("last_used", ""),
                     "source_session": m.get("source_session", ""), "score": m.get("score")})
    rows.sort(key=lambda r: r["created_at"], reverse=True)
    return {"total": len(rows), "rows": rows[:max(1, min(limit, 1000))]}
