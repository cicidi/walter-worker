import json
from datetime import datetime, timedelta
from .db import get_db


def get_session_data(session_id: str):
    conn = get_db()
    session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not session:
        conn.close()
        return None

    msgs = conn.execute(
        "SELECT seq, type, content FROM messages WHERE session_id = ? ORDER BY seq",
        (session_id,),
    ).fetchall()

    tools = conn.execute(
        "SELECT call_id, tool, args, result, duration_ms, seq_before, seq_after "
        "FROM tool_calls WHERE session_id = ? ORDER BY COALESCE(seq_before, seq_after)",
        (session_id,),
    ).fetchall()

    conn.close()

    return {
        "session_id": session_id,
        "ide": session["ide"],
        "project": session["project"],
        "initiative": session["initiative"],
        "branch": session["branch"],
        "started": session["created_at"],
        "ended": session["closed_at"],
        "messages": [dict(m) for m in msgs],
        "tool_calls": [dict(t) for t in tools],
    }


def build_summary_prompt(data: dict) -> str:
    return f"""Analyze this AI coding session data and produce a structured summary.

Session: {data['session_id']}
IDE: {data['ide']}
Project: {data['project']}
Initiative: {data['initiative']}
Branch: {data['branch']}
Duration: {data['started']} to {data['ended']}

Messages:
{json.dumps(data['messages'], indent=2)}

Tool calls:
{json.dumps(data['tool_calls'], indent=2)}

Output a JSON object with these fields:
{{
  "sop_workflows": ["reusable step sequences discovered"],
  "context_to_remember": "project state, branch status, unfinished work",
  "effective_operations": ["specific tool invocations that worked well"],
  "pitfalls_and_fixes": [{{"problem": "...", "attempts": ["..."], "solution": "..."}}],
  "wasted_actions": ["loops, unnecessary reads, dead-end explorations"],
  "bottlenecks": ["longest think times, most repetitive tool calls"],
  "efficiency_tip": "one actionable suggestion",
  "efficiency_score": 0.0-1.0,
  "memory_keywords": ["keyword1", "keyword2"]
}}

Return ONLY the JSON, no markdown code blocks."""


def write_summary(session_id: str, result: dict):
    conn = get_db()
    conn.execute(
        """INSERT OR REPLACE INTO session_summaries
           (session_id, sop_workflows, context_to_remember, effective_operations,
            pitfalls_and_fixes, wasted_actions, bottlenecks, efficiency_tip,
            efficiency_score, memory_keywords, generated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            session_id,
            json.dumps(result.get("sop_workflows", [])),
            result.get("context_to_remember", ""),
            json.dumps(result.get("effective_operations", [])),
            json.dumps(result.get("pitfalls_and_fixes", [])),
            json.dumps(result.get("wasted_actions", [])),
            json.dumps(result.get("bottlenecks", [])),
            result.get("efficiency_tip", ""),
            result.get("efficiency_score"),
            json.dumps(result.get("memory_keywords", [])),
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def write_knowledge(cards: list[dict]):
    conn = get_db()
    for card in cards:
        conn.execute(
            """INSERT INTO knowledge (title, type, session_id, project, skills, summary, evidence, generated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                card["title"],
                card["type"],
                card.get("session_id", ""),
                card.get("project", ""),
                json.dumps(card.get("skills", [])),
                card.get("summary", ""),
                json.dumps(card.get("evidence", [])),
                datetime.now().isoformat(),
            ),
        )
    conn.commit()
    conn.close()


def get_all_sessions_since(since: str = "yesterday"):
    conn = get_db()
    if since == "all":
        rows = conn.execute("SELECT id FROM sessions ORDER BY created_at").fetchall()
    else:
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        rows = conn.execute("SELECT id FROM sessions WHERE created_at >= ? ORDER BY created_at", (date,)).fetchall()
    conn.close()
    return [r["id"] for r in rows]
