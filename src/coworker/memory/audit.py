"""Audit trail for memory sync operations.

Every sync (per-turn and session-end) writes a timestamped record.
Gap detection identifies missing captures between records.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

AUDIT_LOG_FORMAT = "{ts} sync {trigger} {session_id} tool={tool} lessons={lessons} ms={ms} {status}\n"


def write_audit_record(
    path: str,
    trigger: str,
    session_id: str,
    tool: str,
    lessons: int,
    ms: int,
    status: str,
    ts: str | None = None,
) -> None:
    """Append a timestamped audit record to the log file.

    Args:
        path: Full path to audit.log.
        trigger: Hook trigger name (posttooluse, subagentstop, stop).
        session_id: Session identifier.
        tool: Tool name that triggered this record.
        lessons: Number of lessons extracted.
        ms: Latency in milliseconds.
        status: ``"ok"`` or ``"error"``.
        ts: ISO-8601 timestamp (auto-generated if None).
    """
    ts = ts or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    record = AUDIT_LOG_FORMAT.format(
        ts=ts,
        trigger=trigger,
        session_id=session_id,
        tool=tool,
        lessons=lessons,
        ms=ms,
        status=status,
    )
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as f:
        f.write(record)


def check_gaps(path: str, gap_threshold_minutes: int = 5) -> list[dict]:
    """Scan the audit log for gaps between consecutive records in the same session.

    Args:
        path: Full path to audit.log.
        gap_threshold_minutes: Gap longer than this is reported.

    Returns:
        List of gap dicts with keys: session_id, gap_minutes, from, to.
    """
    p = Path(path)
    if not p.exists():
        return []

    records: list[dict] = []
    for line in p.read_text().strip().split("\n"):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 8:
            continue
        records.append({"ts": parts[0], "session_id": parts[3]})

    gaps: list[dict] = []
    for i in range(1, len(records)):
        if records[i]["session_id"] != records[i - 1]["session_id"]:
            continue
        try:
            t1 = datetime.strptime(records[i - 1]["ts"], "%Y-%m-%dT%H:%M:%SZ")
            t2 = datetime.strptime(records[i]["ts"], "%Y-%m-%dT%H:%M:%SZ")
            gap = (t2 - t1).total_seconds() / 60
            if gap > gap_threshold_minutes:
                gaps.append({
                    "session_id": records[i]["session_id"],
                    "gap_minutes": gap,
                    "from": records[i - 1]["ts"],
                    "to": records[i]["ts"],
                })
        except ValueError:
            continue
    return gaps


def rebuild_index(db, mem0_client) -> None:
    """Rebuild the mem0 index from raw session transcripts.

    WARNING: Deletes all existing mem0 entries before rebuilding.
    """
    logger.info("Rebuilding mem0 index from raw transcripts...")
    sessions = db.execute("SELECT id FROM sessions").fetchall()
    mem0_client.delete_all()
    for (session_id,) in sessions:
        transcript = db.get_transcript(session_id)
        if transcript:
            mem0_client.add(messages=transcript, user_id="rebuild", run_id=session_id)
    logger.info("Rebuilt index from %d sessions", len(sessions))
