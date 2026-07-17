"""Knowledge extraction and storage with LLM-powered semantic deduplication."""
from __future__ import annotations

import json
import hashlib
from datetime import datetime, timedelta

from .db import get_db


def _semantic_key(card: dict) -> str:
    text = (
        (card.get("title", "") or "")
        + " "
        + (card.get("summary", "") or "")
        + " "
        + (card.get("type", "") or "")
    ).lower()
    words = sorted(set(w for w in text.split() if len(w) > 3))[:20]
    return hashlib.md5(" ".join(words).encode()).hexdigest()[:12]


def _levenshtein(a: str, b: str) -> int:
    n, m = len(a), len(b)
    if n > m:
        a, b = b, a
        n, m = m, n
    prev = list(range(m + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + (0 if ca == cb else 1)))
        prev = curr
    return prev[-1]


def _ask_llm_is_duplicate(new_card: dict, candidates: list[dict]) -> bool:
    try:
        import os
        import openai
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            return False
        client = openai.OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com/v1",
        )

        old_text = "\n---\n".join(
            f"Title: {e.get('title', '')}\nType: {e.get('type', '')}\nSummary: {e.get('summary', '')}"
            for e in candidates[:5]
        )
        new_text = (
            f"Title: {new_card.get('title', '')}\n"
            f"Type: {new_card.get('type', '')}\n"
            f"Summary: {new_card.get('summary', '')}"
        )

        resp = client.chat.completions.create(
            model="deepseek-chat",
            max_tokens=10,
            messages=[{
                "role": "user",
                "content": (
                    f"Are these two knowledge entries about the SAME insight or concept? "
                    f"Answer YES or NO only.\n\n"
                    f"Existing:\n{old_text}\n\n"
                    f"New:\n{new_text}"
                ),
            }],
        )
        answer = (resp.choices[0].message.content or "").strip().upper()
        return answer.startswith("YES")
    except Exception:
        return False


def _is_duplicate(new_card: dict, existing_for_session: list[dict]) -> bool:
    if not existing_for_session:
        return False

    new_key = _semantic_key(new_card)
    candidates = [e for e in existing_for_session if _semantic_key(e) == new_key]
    if not candidates:
        return False

    # Exact title match
    for e in candidates:
        if e.get("title") == new_card.get("title"):
            return True

    # Very similar titles (within edit distance 3)
    for e in candidates:
        if (
            e.get("type") == new_card.get("type")
            and _levenshtein(str(e.get("title") or ""), str(new_card.get("title") or "")) <= 3
        ):
            return True

    # LLM semantic check
    return _ask_llm_is_duplicate(new_card, candidates)


# ── existing functions ────────────────────────────────────────────────────────


def get_session_data(session_id: str):
    conn = get_db()
    session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not session:
        conn.close()
        return None
    data = {key: session[key] for key in session.keys()}
    data["messages"] = [
        dict(m) for m in conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY seq", (session_id,)
        ).fetchall()
    ]
    data["tool_calls"] = [
        dict(t) for t in conn.execute(
            "SELECT * FROM tool_calls WHERE session_id = ? ORDER BY COALESCE(seq_before, seq_after)",
            (session_id,),
        ).fetchall()
    ]
    conn.close()
    return data


def build_summary_prompt(data: dict) -> str:
    project = data.get("project") or data.get("cwd", "")
    initiative = data.get("initiative", "")
    messages = data.get("messages", [])
    tools = data.get("tool_calls", [])

    return (
        f"Project: {project}\n"
        f"Initiative: {initiative}\n"
        f"Messages: {len(messages)}\n"
        f"Tool calls: {len(tools)}\n"
    ).strip()


def write_summary(session_id: str, result: dict):
    conn = get_db()
    conn.execute(
        """INSERT OR REPLACE INTO session_summaries
           (session_id, context_to_remember, efficiency_tip, memory_keywords,
            efficiency_score, last_guide_attempt)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (
            session_id,
            result.get("context_to_remember", ""),
            result.get("efficiency_tip", ""),
            result.get("memory_keywords", ""),
            result.get("efficiency_score", 0.0),
            result.get("last_guide_attempt", ""),
        ),
    )
    conn.commit()
    conn.close()


def _fetch_existing_for_dedup(conn, card: dict) -> list[dict]:
    """Fetch candidate knowledge entries for dedup — same type + similar title, across ALL sessions."""
    title = card.get("title", "")[:40]  # first 40 chars for fuzzy matching
    card_type = card.get("type", "")
    rows = conn.execute(
        """SELECT title, type, summary FROM knowledge
           WHERE type = ? AND (title LIKE ? OR ? LIKE '%' || substr(title,1,20) || '%')
           LIMIT 20""",
        (card_type, f"%{title[:30]}%", title[:30]),
    ).fetchall()
    return [dict(r) for r in rows]


def write_knowledge(cards: list[dict]):
    conn = get_db()
    # Ensure knowledge_sessions table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_sessions (
            knowledge_id INTEGER NOT NULL REFERENCES knowledge(id),
            session_id TEXT NOT NULL REFERENCES sessions(id),
            generated_at TEXT NOT NULL,
            PRIMARY KEY (knowledge_id, session_id)
        )
    """)
    for card in cards:
        sid = card.get("session_id", "")
        title = card.get("title", "")

        # Check across ALL sessions for semantic dedup (not just this session)
        candidates = _fetch_existing_for_dedup(conn, card)

        dup = _is_duplicate(card, candidates)
        if dup:
            # Found duplicate — link the session to existing knowledge
            existing = conn.execute(
                "SELECT id FROM knowledge WHERE title=? AND type=? LIMIT 1",
                (title, card["type"]),
            ).fetchone()
            if existing:
                conn.execute(
                    "INSERT OR IGNORE INTO knowledge_sessions (knowledge_id, session_id, generated_at) VALUES (?, ?, ?)",
                    (existing["id"], sid, datetime.now().isoformat()),
                )
            continue

        conn.execute(
            """INSERT INTO knowledge (title, type, session_id, project, skills, summary, evidence, generated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                title,
                card["type"],
                sid,
                card.get("project", ""),
                json.dumps(card.get("skills", [])),
                card.get("summary", ""),
                json.dumps(card.get("evidence", [])),
                datetime.now().isoformat(),
            ),
        )
        # Also link the creating session
        kid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute(
            "INSERT OR IGNORE INTO knowledge_sessions (knowledge_id, session_id, generated_at) VALUES (?, ?, ?)",
            (kid, sid, datetime.now().isoformat()),
        )
    conn.commit()
    conn.close()


def get_all_sessions_since(since: str = "yesterday"):
    conn = get_db()
    if since == "all":
        rows = conn.execute("SELECT id FROM sessions ORDER BY created_at").fetchall()
    else:
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT id FROM sessions WHERE created_at >= ? ORDER BY created_at", (date,)
        ).fetchall()
    conn.close()
    return [r["id"] for r in rows]
