"""Batch training pipeline — process all past sessions into skills and experiences.

Runs offline (not in the hot per-turn path).  Reads raw session data
from analytics.db, extracts lessons via LLM, stores in mem0.
"""

from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def run_training_pipeline(
    mem0_client,
    llm_client,
    db,
    limit: int | None = None,
    skip_existing: bool = True,
) -> dict:
    """Process past sessions and populate mem0 with extracted lessons.

    Args:
        mem0_client: Mem0Client instance.
        llm_client: LLMClient instance.
        db: AnalyticsDB connection.
        limit: Max sessions to process (None = all).
        skip_existing: Skip sessions that already have mem0 entries.

    Returns:
        Stats dict with sessions_processed, lessons_extracted, errors.
    """
    from coworker.memory.engine import extract_and_store

    stats = {"sessions_processed": 0, "lessons_extracted": 0, "errors": []}

    try:
        sessions = db.list_all_sessions()
    except Exception as exc:
        logger.error("Failed to list sessions: %s", exc)
        stats["errors"].append(str(exc))
        return stats

    for session in sessions:
        if limit and stats["sessions_processed"] >= limit:
            break

        session_id = session.get("id", "")
        if not session_id:
            continue

        # Check for existing entries
        if skip_existing:
            try:
                existing = mem0_client.search(
                    query="",
                    filters={"source_session": session_id},
                    top_k=1,
                )
                if existing:
                    logger.debug("Skipping session %s (already has entries)", session_id)
                    continue
            except Exception:
                pass

        # Get transcript
        try:
            transcript = db.get_transcript(session_id)
        except AttributeError:
            transcript = None

        if not transcript:
            logger.debug("Skipping session %s (no transcript)", session_id)
            continue

        # Convert transcript to text
        transcript_text = "\n".join(
            f"[{m.get('role', '?')}] {m.get('content', '')}"
            for m in transcript
        )

        # Extract lessons
        try:
            result = extract_and_store(
                mem0_client, llm_client, session_id, transcript_text,
                project=session.get("project", "ai-coworker"),
            )
            stats["lessons_extracted"] += result.stats.get("stored", 0)
        except Exception as exc:
            logger.error("Failed to process session %s: %s", session_id, exc)
            stats["errors"].append(f"{session_id}: {exc}")

        stats["sessions_processed"] += 1
        if stats["sessions_processed"] % 10 == 0:
            logger.info(
                "Training progress: %d sessions, %d lessons",
                stats["sessions_processed"], stats["lessons_extracted"],
            )

    logger.info(
        "Training complete: %d sessions → %d lessons",
        stats["sessions_processed"], stats["lessons_extracted"],
    )
    return stats
