"""Pending queue — staged skill review before promotion.

Auto-created/patched skills land in ~/.coworker/pending/skills/ as
JSON files.  The user reviews and approves/rejects them.
Unreviewed items expire after 30 days.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_PENDING_DIR = "~/.coworker/pending/skills"
AUTO_EXPIRE_DAYS = 30


def _pending_dir() -> Path:
    return Path(DEFAULT_PENDING_DIR).expanduser()


def stage_skill(name: str, description: str, tool_call_count: int, session_id: str) -> str:
    """Stage a new skill candidate to the pending queue.

    Returns the skill ID (filename without .json).
    """
    skill_id = name.replace(" ", "-").lower()
    payload = {
        "name": name,
        "description": description,
        "tool_call_count": tool_call_count,
        "source_session": session_id,
        "staged_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "pending",
    }
    path = _pending_dir() / f"{skill_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
    logger.info("Staged skill: %s", name)
    return skill_id


def list_pending() -> list[dict]:
    """List all pending skill items, sorted by staged_at descending."""
    d = _pending_dir()
    if not d.exists():
        return []
    items = []
    for f in sorted(d.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text())
            data["id"] = f.stem
            items.append(data)
        except Exception:
            continue
    return items


def approve(skill_id: str) -> bool:
    """Approve a pending skill — promote to active skills directory."""
    path = _pending_dir() / f"{skill_id}.json"
    if not path.exists():
        return False
    data = json.loads(path.read_text())
    data["status"] = "approved"
    data["approved_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path.write_text(json.dumps(data, indent=2))
    logger.info("Approved skill: %s", skill_id)
    # TODO: Trigger actual skill promotion (skill-create integration)
    return True


def reject(skill_id: str) -> bool:
    """Reject a pending skill."""
    path = _pending_dir() / f"{skill_id}.json"
    if not path.exists():
        return False
    data = json.loads(path.read_text())
    data["status"] = "rejected"
    data["rejected_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    path.write_text(json.dumps(data, indent=2))
    logger.info("Rejected skill: %s", skill_id)
    return True


def batch_approve(item_type: str | None = None) -> int:
    """Approve all pending items, optionally filtered by type.

    Returns count of approved items.
    """
    count = 0
    for item in list_pending():
        if item_type and item.get("type") != item_type:
            continue
        if item.get("status") == "pending":
            approve(item["id"])
            count += 1
    return count


def expire_old_items(days: int = AUTO_EXPIRE_DAYS) -> int:
    """Auto-reject items that have been pending for more than `days`.

    Returns count of expired items.
    """
    d = _pending_dir()
    if not d.exists():
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    count = 0
    for f in d.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            if data.get("status") != "pending":
                continue
            staged = datetime.strptime(data["staged_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            if staged < cutoff:
                data["status"] = "expired"
                data["expired_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                f.write_text(json.dumps(data, indent=2))
                count += 1
        except Exception:
            continue
    if count:
        logger.info("Expired %d pending items", count)
    return count
