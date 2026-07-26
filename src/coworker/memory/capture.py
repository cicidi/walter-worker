"""Per-turn and session-end capture — the bridge between IDE hooks and mem0.

process_turn:   Extracts lessons from a single tool event (called every PostToolUse).
process_session_end: Full-transcript reconciliation pass (called on Stop).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

EXTRACTION_PROMPT = """You are extracting reusable knowledge from an AI coding session.

Given the current tool event and recent conversation context, extract:
1. Lessons learned (patterns, pitfalls, conventions, workarounds)
2. An optional one-line progress note if meaningful work was done

Rules:
- Most tool calls produce ZERO lessons. Only extract if there's a real pattern.
- "git status", simple reads, echoing values → never extract.
- MCP errors with workarounds, project-specific conventions, repeated patterns → extract.
- If existing lessons on the same topic already cover this, skip it.

Existing lessons on related topics:
{existing_lessons}

Current tool event:
Tool: {tool}
Input: {tool_input}
Result: {tool_result}

Recent context:
{recent_context}

Respond with JSON:
{{"lessons": [{{"memory": "...", "type": "lesson|convention|preference", "topic": "...", "problem": "..."}}], "state_delta": "one-line progress or null"}}
"""

SESSION_END_PROMPT = """You are summarizing an AI coding session to extract reusable knowledge.

Read the full session transcript and produce:

1. Lessons learned — patterns, pitfalls, conventions, workarounds discovered in this session.
   - Do NOT repeat lessons that were already captured during individual turns.
   - Focus on cross-turn patterns that only emerge from the full session view.

2. Skill candidates — if any task pattern in this session is reusable, describe it as a skill.
   - A skill-worthy task must involve >= 10 tool calls.
   - Include: skill name, one-line description, tool call count.

Respond with JSON:
{{
  "lessons": [{{"memory": "...", "type": "lesson|convention|preference", "topic": "...", "problem": "..."}}],
  "skill_candidates": [{{"name": "...", "description": "...", "tool_call_count": N}}]
}}
"""

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class TurnResult:
    """Result of processing a single tool event."""

    lessons_extracted: int = 0
    lessons: list[dict] = field(default_factory=list)
    state_delta: str | None = None
    error: str | None = None


@dataclass
class SessionEndResult:
    """Result of session-end reconciliation pass."""

    reconciled: int = 0
    lessons: list[dict] = field(default_factory=list)
    skills_staged: list[str] = field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# Per-turn capture
# ---------------------------------------------------------------------------


def process_turn(
    mem0_client,
    llm_client,
    tool_event: dict,
    recent_window: list[dict],
    session_id: str,
    state_dir: str | None = None,
    audit_dir: str | None = None,
) -> TurnResult:
    """Extract lessons from a single tool event and persist to mem0 + state file.

    This is called by PostToolUse and SubagentStop hooks (async).
    """
    from coworker.memory.audit import write_audit_record

    tool_name = tool_event.get("tool", "unknown")
    audit_path = str(Path(audit_dir) / "audit.log") if audit_dir else None

    # Cap recent window at 5 turns
    window = recent_window[-5:] if len(recent_window) > 5 else recent_window
    recent_text = "\n".join(
        f"[{m.get('role', 'tool')}] {str(m.get('content', ''))[:200]}"
        for m in window
    )

    # Fetch existing lessons on related topics
    try:
        existing = mem0_client.search(query=str(tool_event.get("input", ""))[:200], top_k=3)
        existing_text = "\n".join(f"- {e.get('memory', '')}" for e in existing) if existing else "(none)"
    except Exception:
        existing_text = "(search unavailable)"

    # Build prompt
    prompt = EXTRACTION_PROMPT.format(
        existing_lessons=existing_text,
        tool=tool_name,
        tool_input=str(tool_event.get("input", {}))[:500],
        tool_result=str(tool_event.get("result", ""))[:500],
        recent_context=recent_text,
    )

    start = time.time()

    try:
        response = llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=500,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.content)
        lessons = data.get("lessons", [])
        state_delta = data.get("state_delta")
        ms = int((time.time() - start) * 1000)

        # Store lessons in mem0
        for lesson in lessons:
            try:
                mem0_client.add(
                    memory=lesson["memory"],
                    user_id="default",
                    agent_id="ai-coworker",
                    run_id=session_id,
                    metadata={
                        "type": lesson.get("type", "lesson"),
                        "project": "ai-coworker",
                        "topic": lesson.get("topic", ""),
                        "problem": lesson.get("problem", ""),
                        "provenance": "agent",
                        "state": "active",
                        "source_session": session_id,
                        "use_count": 0,
                        "last_used": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    },
                )
            except Exception as exc:
                logger.error("Failed to store lesson in mem0: %s", exc)

        # Write state delta to Tier 2 state file
        if state_delta and state_dir:
            _append_state_delta(state_dir, state_delta)

        # Write audit record
        if audit_path:
            write_audit_record(audit_path, "posttooluse", session_id, tool_name, len(lessons), ms, "ok")

        return TurnResult(lessons_extracted=len(lessons), lessons=lessons, state_delta=state_delta)

    except Exception as exc:
        ms = int((time.time() - start) * 1000)
        logger.error("process_turn failed: %s", exc)
        if audit_path:
            write_audit_record(audit_path, "posttooluse", session_id, tool_name, 0, ms, "error")
        return TurnResult(lessons_extracted=0, error=str(exc))


# ---------------------------------------------------------------------------
# Session-end capture
# ---------------------------------------------------------------------------


def process_session_end(
    mem0_client,
    llm_client,
    session_id: str,
    transcript_path: str,
    db=None,
    audit_dir: str | None = None,
) -> SessionEndResult:
    """Full-transcript reconciliation pass called on session Stop.

    Back-fills missed captures, deduplicates, and assesses
    whether any task pattern is skill-worthy.
    """
    from coworker.memory.audit import write_audit_record

    start = time.time()
    audit_path = str(Path(audit_dir) / "audit.log") if audit_dir else None

    # Read transcript
    try:
        transcript_text = Path(transcript_path).read_text()
    except Exception as exc:
        logger.error("Failed to read transcript: %s", exc)
        return SessionEndResult(error=str(exc))

    # Truncate if too long (model context limit)
    if len(transcript_text) > 50000:
        transcript_text = transcript_text[-50000:]

    prompt = SESSION_END_PROMPT

    try:
        response = llm_client.chat(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Session transcript:\n{transcript_text}"},
            ],
            temperature=0.2,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.content)
        lessons = data.get("lessons", [])
        skill_candidates = data.get("skill_candidates", [])
        ms = int((time.time() - start) * 1000)

        # Store lessons
        stored = 0
        for lesson in lessons:
            try:
                mem0_client.add(
                    memory=lesson["memory"],
                    user_id="default",
                    agent_id="ai-coworker",
                    run_id=session_id,
                    metadata={
                        "type": lesson.get("type", "lesson"),
                        "project": "ai-coworker",
                        "topic": lesson.get("topic", ""),
                        "problem": lesson.get("problem", ""),
                        "provenance": "agent",
                        "state": "active",
                        "source_session": session_id,
                        "use_count": 0,
                        "last_used": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    },
                )
                stored += 1
            except Exception as exc:
                logger.error("Failed to store session-end lesson: %s", exc)

        # Stage skill candidates to pending
        skills_staged: list[str] = []
        for candidate in skill_candidates:
            if candidate.get("tool_call_count", 0) < 10:
                continue
            try:
                _stage_skill(candidate, session_id)
                skills_staged.append(candidate["name"])
            except Exception as exc:
                logger.error("Failed to stage skill %s: %s", candidate.get("name"), exc)

        if audit_path:
            write_audit_record(audit_path, "stop", session_id, "session-end", stored, ms, "ok")

        return SessionEndResult(reconciled=stored, lessons=lessons, skills_staged=skills_staged)

    except Exception as exc:
        ms = int((time.time() - start) * 1000)
        logger.error("process_session_end failed: %s", exc)
        if audit_path:
            write_audit_record(audit_path, "stop", session_id, "session-end", 0, ms, "error")
        return SessionEndResult(error=str(exc))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _append_state_delta(state_dir: str, delta: str) -> None:
    """Append a timestamped line to the daily state file."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    state_path = Path(state_dir) / f"{today}-state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%H:%M")
    with open(state_path, "a") as f:
        f.write(f"- {timestamp} | {delta}\n")


def _stage_skill(candidate: dict, session_id: str) -> None:
    """Write a skill candidate to the pending queue."""
    pending_dir = Path.home() / ".coworker" / "pending" / "skills"
    pending_dir.mkdir(parents=True, exist_ok=True)
    skill_id = candidate["name"].replace(" ", "-").lower()
    payload = {
        "name": candidate["name"],
        "description": candidate.get("description", ""),
        "tool_call_count": candidate.get("tool_call_count", 0),
        "source_session": session_id,
        "staged_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "pending",
    }
    path = pending_dir / f"{skill_id}.json"
    path.write_text(json.dumps(payload, indent=2))
    logger.info("Staged skill candidate: %s", candidate["name"])
