"""Evolution engine — extract, assess, reconcile.

Bridges capture layer (raw tool events) with mem0 storage and
session-end reconciliation.  Also handles the session-end
skill-creation assessment trigger.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result of extracting lessons from a session transcript."""

    lessons: list[dict] = field(default_factory=list)
    skill_candidates: list[dict] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def extract_and_store(
    mem0_client,
    llm_client,
    session_id: str,
    transcript: str,
    project: str = "ai-coworker",
) -> ExtractionResult:
    """Extract lessons and skill candidates from a session transcript.

    Args:
        mem0_client: Mem0Client instance.
        llm_client: LLMClient instance.
        session_id: Session identifier.
        transcript: Full session transcript text.
        project: Project name for metadata tagging.

    Returns:
        ExtractionResult with lessons, skill_candidates, and stats.
    """
    from coworker.memory.capture import SESSION_END_PROMPT

    if len(transcript) > 50000:
        transcript = transcript[-50000:]

    try:
        response = llm_client.chat(
            messages=[
                {"role": "system", "content": SESSION_END_PROMPT},
                {"role": "user", "content": f"Session transcript:\n{transcript}"},
            ],
            temperature=0.2,
            max_tokens=1000,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.content)
    except Exception as exc:
        logger.error("LLM extraction failed: %s", exc)
        return ExtractionResult()

    lessons = data.get("lessons", [])
    skill_candidates = data.get("skill_candidates", [])

    # Store lessons in mem0
    stored = 0
    for lesson in lessons:
        try:
            mem0_client.add(
                memory=lesson["memory"],
                user_id="default",
                run_id=session_id,
                metadata={
                    "type": lesson.get("type", "lesson"),
                    "project": project,
                    "topic": lesson.get("topic", ""),
                    "problem": lesson.get("problem", ""),
                    "provenance": "agent",
                    "state": "active",
                    "source_session": session_id,
                    "use_count": 0,
                    "last_used": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
            )
            stored += 1
        except Exception as exc:
            logger.error("Failed to store lesson: %s", exc)

    # Assess skill creation threshold
    eligible_skills: list[dict] = []
    for candidate in skill_candidates:
        tc = candidate.get("tool_call_count", 0)
        if tc >= _get_skill_threshold():
            eligible_skills.append(candidate)

    return ExtractionResult(
        lessons=lessons,
        skill_candidates=eligible_skills,
        stats={"total_extracted": len(lessons), "stored": stored, "eligible_skills": len(eligible_skills)},
    )


def assess_skill(
    mem0_client,
    session_id: str,
    tool_count: int,
    transcript: str,
) -> list[dict]:
    """Check if a session's work pattern is skill-worthy.

    Called at session-end. Returns list of skill candidate dicts.
    """
    if tool_count < _get_skill_threshold():
        return []

    # Collect task descriptions from transcript (simple heuristic)
    candidates: list[dict] = []
    # The full extraction is handled by extract_and_store above
    return candidates


def reconcile(
    mem0_client,
    session_id: str,
    transcript_path: str,
) -> int:
    """Back-fill any missed captures by re-extracting from transcript.

    Returns count of newly extracted entries.
    """
    try:
        text = Path(transcript_path).read_text()
    except Exception as exc:
        logger.error("Failed to read transcript for reconciliation: %s", exc)
        return 0

    if len(text) < 100:
        return 0

    # Search for existing entries from this session
    try:
        existing = mem0_client.search(query="", filters={"source_session": session_id}, top_k=100)
    except Exception:
        existing = []

    existing_count = len(existing)

    # If no entries exist, re-run extraction (simplified)
    if existing_count == 0 and len(text) > 500:
        # Use a small model call to extract a few key facts
        logger.info("No existing entries for session %s; back-filling...", session_id)
        # For now, just note the gap — full re-extraction needs LLM
        return 0

    return 0


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def _get_skill_threshold() -> int:
    """Return the minimum tool calls for a session to trigger skill creation."""
    # Could be read from coworker config, env, etc.
    import os
    return int(os.environ.get("COWORKER_SKILL_THRESHOLD", "10"))
