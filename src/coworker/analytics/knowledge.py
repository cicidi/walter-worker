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


#: Ceiling on the rendered prompt. A long session can hold thousands of
#: messages; without a bound the request is rejected by the provider and the
#: session can never be summarised at all.
MAX_PROMPT_CHARS = 12000

#: Per-message share of the transcript budget, so one enormous paste cannot
#: crowd out the rest of the session.
_MAX_MESSAGE_CHARS = 1500

#: What the summariser must return. write_summary reads these keys by name.
_SUMMARY_FIELDS = (
    '{"context_to_remember": "", "efficiency_tip": "", '
    '"memory_keywords": "", "efficiency_score": 0.0}'
)


def _clip(text: str, limit: int) -> str:
    """Shorten text to at most `limit` characters, marker included.

    The marker has to come out of the budget rather than be appended past it,
    or a "bounded" prompt overshoots by its own marker.
    """
    if len(text) <= limit:
        return text
    marker = "…[truncated]"
    if limit <= len(marker):
        return text[:limit]
    return text[: limit - len(marker)] + marker


def build_summary_prompt(data: dict) -> str:
    """Render one session as a prompt the summariser can actually work from.

    This returned the counts line and nothing else, so the model was asked to
    summarise a session it had not been shown. The header it produced is kept
    as-is; the transcript below it is what made the call meaningful.
    """
    project = data.get("project") or data.get("cwd", "")
    feature = data.get("feature", "")
    messages = data.get("messages", [])
    tools = data.get("tool_calls", [])

    header = (
        f"Project: {project}\n"
        f"Feature: {feature}\n"
        f"Messages: {len(messages)}\n"
        f"Tool calls: {len(tools)}\n"
    )

    body: list[str] = []
    for m in messages:
        content = (m.get("content") or "").strip()
        if not content:
            continue
        kind = m.get("type") or m.get("role") or "?"
        body.append(f"[{kind}] {_clip(content, _MAX_MESSAGE_CHARS)}")

    for t in tools:
        name = t.get("tool") or "?"
        args = (t.get("args") or "").strip()
        ms = t.get("duration_ms")
        suffix = f" ({ms}ms)" if ms else ""
        body.append(f"[tool] {name}{suffix} {_clip(args, 400)}".rstrip())

    prompt = header
    if body:
        prompt += "\n## Transcript\n" + "\n".join(body)
    prompt += f"\n\n## Task\nSummarise the session above. Reply with JSON only:\n{_SUMMARY_FIELDS}\n"

    return _clip(prompt, MAX_PROMPT_CHARS)


def write_summary(session_id: str, result: dict):
    conn = get_db()
    conn.execute(
        """INSERT OR REPLACE INTO session_summaries
           (session_id, context_to_remember, efficiency_tip, memory_keywords,
            efficiency_score, last_guide_attempt, generated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            session_id,
            result.get("context_to_remember", ""),
            result.get("efficiency_tip", ""),
            result.get("memory_keywords", ""),
            result.get("efficiency_score", 0.0),
            result.get("last_guide_attempt", ""),
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    conn.close()


def write_knowledge(cards: list[dict]):
    conn = get_db()
    for card in cards:
        sid = card.get("session_id", "")
        title = card.get("title", "")

        # Fetch existing knowledge for this session for semantic dedup
        existing = conn.execute(
            "SELECT title, type, summary FROM knowledge WHERE session_id = ?",
            (sid,),
        ).fetchall()
        existing_dicts = [dict(r) for r in existing]

        if _is_duplicate(card, existing_dicts):
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
    conn.commit()
    conn.close()


def _since_to_date(since: str) -> str | None:
    """Lower bound as an ISO date, or None meaning "no lower bound".

    Raises ValueError rather than guessing: this used to accept any string and
    answer with yesterday's date for all of them, so `--since 2026-07-01`
    quietly returned one day's sessions and looked like it had worked.
    """
    text = (since or "").strip()
    lowered = text.lower()
    if lowered == "all":
        return None

    now = datetime.now()
    if lowered in ("", "today"):
        return now.strftime("%Y-%m-%d")
    if lowered == "yesterday":
        return (now - timedelta(days=1)).strftime("%Y-%m-%d")
    if lowered.endswith(" days ago"):
        try:
            days = int(lowered[: -len(" days ago")].strip())
        except ValueError:
            raise ValueError(f"Unrecognised --since value: {since!r}") from None
        return (now - timedelta(days=days)).strftime("%Y-%m-%d")

    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    raise ValueError(
        f"Unrecognised --since value: {since!r}. Use 'all', 'today', "
        f"'yesterday', 'N days ago', or an ISO date such as 2026-07-01."
    )


def get_all_sessions_since(since: str = "yesterday"):
    conn = get_db()
    lower = _since_to_date(since)
    if lower is None:
        rows = conn.execute("SELECT id FROM sessions ORDER BY created_at").fetchall()
    else:
        rows = conn.execute(
            "SELECT id FROM sessions WHERE created_at >= ? ORDER BY created_at",
            (lower,),
        ).fetchall()
    conn.close()
    return [r["id"] for r in rows]


def _parse_summary(content: str) -> dict:
    """Read the model's JSON reply, tolerating prose wrapped around it.

    A model answering conversationally must not take the run down: the session
    still gets its summary row, and the caller sees the same shape either way.
    """
    text = (content or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return {}
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {}
    return parsed if isinstance(parsed, dict) else {}


def _valid_cards(cards, session_id: str, project: str) -> list[dict]:
    """Keep the cards write_knowledge can actually store.

    It indexes card["type"] and card["title"] directly, so a model that omits
    either would raise KeyError mid-run and abandon the remaining sessions.
    """
    kept = []
    for card in cards or []:
        if not isinstance(card, dict):
            continue
        if not card.get("title") or not card.get("type"):
            continue
        card.setdefault("session_id", session_id)
        card.setdefault("project", project)
        kept.append(card)
    return kept


def summarize_session(session_id: str, llm=None) -> dict | None:
    """Summarise one session, plus any knowledge cards it produced.

    Returns None for an unknown session, so a caller can tell "no such
    session" apart from "summarised, with nothing to say".
    """
    data = get_session_data(session_id)
    if data is None:
        return None

    if llm is None:
        from ..memory.llm import LLMClient

        llm = LLMClient()

    response = llm.chat(
        [{"role": "user", "content": build_summary_prompt(data)}],
        response_format={"type": "json_object"},
    )
    result = _parse_summary(getattr(response, "content", ""))

    write_summary(session_id, result)

    cards = _valid_cards(result.get("cards"), session_id, data.get("project", ""))
    if cards:
        write_knowledge(cards)

    return {"session_id": session_id, "cards": len(cards)}
