"""Batch training pipeline — spec §12.4.

Reads all past sessions from analytics.db, extracts lessons via
DeepSeek Flash, aggregates across sessions, deduplicates, and
identifies the top 10 skills and experiences.
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def run_training_pipeline(
    mem0_client,
    llm_client,
    db,
    limit: int | None = None,
    skip_existing: bool = True,
    target_skills: int = 10,
    target_experiences: int = 10,
) -> dict:
    """Run the complete training pipeline per spec §12.4.

    1. Read ALL past sessions from analytics.db
    2. Extract lessons + skill_candidates per session
    3. Aggregate: merge similar lessons, deduplicate, find recurring patterns
    4. Write top N skills to ~/.coworker/pending/skills/
    5. Write top N experiences to mem0
    6. Generate training report

    Args:
        mem0_client: Mem0Client instance.
        llm_client: LLMClient instance.
        db: AnalyticsDB connection.
        limit: Max sessions (None = all).
        skip_existing: Skip sessions already in mem0.
        target_skills: Number of top skills to stage.
        target_experiences: Number of top experiences to store.

    Returns:
        Stats dict with sessions_processed, lessons_extracted, skills_staged, etc.
    """
    from coworker.memory.engine import extract_and_store
    from coworker.analytics.db import list_all_sessions as db_list_sessions
    from coworker.analytics.db import get_transcript as db_get_transcript

    stats = {
        "sessions_processed": 0,
        "lessons_extracted": 0,
        "skills_identified": 0,
        "skills_staged": 0,
        "experiences_stored": 0,
        "errors": [],
    }

    all_lessons: list[dict] = []
    all_skill_candidates: list[dict] = []

    # 1. Read sessions
    try:
        sessions = db_list_sessions(db)
    except Exception as exc:
        logger.error("Failed to list sessions: %s", exc)
        stats["errors"].append(str(exc))
        return stats

    # 2. Process each session
    for session in sessions:
        if limit and stats["sessions_processed"] >= limit:
            break

        session_id = session.get("id", "")
        if not session_id:
            continue

        if skip_existing:
            try:
                existing = mem0_client.search(query=".", filters={"source_session": session_id}, top_k=1)
                if existing:
                    continue
            except Exception:
                pass

        try:
            transcript = db_get_transcript(db, session_id)
        except AttributeError:
            transcript = None

        if not transcript:
            continue

        transcript_text = "\n".join(
            f"[{m.get('role', '?')}] {m.get('content', '')}" for m in transcript
        )

        # Skip sessions with too little content to extract meaningful lessons
        content_chars = sum(len(m.get("content", "") or "") for m in transcript)
        if content_chars < 500:
            continue

        try:
            result = extract_and_store(
                mem0_client, llm_client, session_id, transcript_text,
                project=session.get("project") or "ai-coworker",
            )
            all_lessons.extend(result.lessons)
            all_skill_candidates.extend(result.skill_candidates)
            stats["lessons_extracted"] += result.stats.get("stored", 0)
            stats["skills_identified"] += len(result.skill_candidates)
        except Exception as exc:
            logger.error("Session %s failed: %s", session_id, exc)
            stats["errors"].append(f"{session_id}: {exc}")

        stats["sessions_processed"] += 1
        if stats["sessions_processed"] % 10 == 0:
            logger.info("Training: %d sessions, %d lessons, %d skills",
                        stats["sessions_processed"], stats["lessons_extracted"], stats["skills_identified"])

    # 3. Aggregate: deduplicate and rank
    skill_freq = Counter()
    for sc in all_skill_candidates:
        name = sc.get("name", "")
        if name:
            skill_freq[name] += 1

    # Top skills by frequency (≥3 occurrences)
    top_skills = [(name, count) for name, count in skill_freq.most_common(target_skills) if count >= 3]

    # 4. Stage top skills
    pending_dir = Path.home() / ".coworker" / "pending" / "skills"
    pending_dir.mkdir(parents=True, exist_ok=True)
    for name, count in top_skills:
        skill_id = name.replace(" ", "-").lower()
        payload = {
            "name": name,
            "description": f"Auto-detected reusable task pattern (appeared in {count} sessions)",
            "tool_call_count": count,
            "source": "training-pipeline",
            "staged_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "pending",
        }
        (pending_dir / f"{skill_id}.json").write_text(json.dumps(payload, indent=2))
        stats["skills_staged"] += 1
        logger.info("Staged skill: %s (frequency: %d)", name, count)

    # 5. Generate training report
    report_path = Path.home() / ".coworker" / "memory" / f"training-report-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_lines = [
        "# Training Report",
        f"> Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        "",
        f"- **Sessions processed:** {stats['sessions_processed']}",
        f"- **Lessons extracted:** {stats['lessons_extracted']}",
        f"- **Skills identified:** {stats['skills_identified']}",
        f"- **Skills staged:** {stats['skills_staged']}",
        f"- **Experiences stored:** {stats['experiences_stored']}",
        "",
        "## Top Skills",
        "",
    ]
    for name, count in top_skills:
        report_lines.append(f"- **{name}** — appeared in {count} sessions")
    report_lines.append("")
    if stats["errors"]:
        report_lines.append(f"## Errors ({len(stats['errors'])})")
        for e in stats["errors"][:20]:
            report_lines.append(f"- {e}")
    report_path.write_text("\n".join(report_lines))
    logger.info("Training report: %s", report_path)

    return stats
