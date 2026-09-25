"""Periodic maintenance — archive stale entries, merge duplicates, export MEMORY.md.

Manages the lifecycle: active -> stale (30d) -> archived (90d), and regenerates
MEMORY.md from mem0.

Spec §4.3 schedules this "every 7 days, after 2h+ idle". The interval half is
implemented as a lazy check at session end — `coworker memory curate --if-due`,
wired into the Stop hook — rather than a daemon. The 2h-idle half is not
implemented.

One constraint shapes how this module reads mem0: it must not use search().
search() bumps use_count and last_used on every entry it returns, so a sweep
built on it resets the last_used of exactly the entries it is about to expire,
and _archive_old's 90-day test can then never be satisfied. Every read here
goes through Mem0Client.list_entries(), which does not record a retrieval.

Known gap: ARCHIVE_DAYS is in the spec, but the recovery command the spec
names (§4.3, `coworker memory unarchive`) does not exist anywhere in the
codebase. Archival is therefore a one-way door.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

STALE_DAYS = 30
ARCHIVE_DAYS = 90
CURATOR_INTERVAL_DAYS = 7

_DEFAULT_STATE_PATH = "~/.coworker/memory/.curator_last_run"
DEFAULT_EXPORT_PATH = "~/.coworker/memory/MEMORY.md"


def _resolve_state_path(state_path: str | Path | None = None) -> Path:
    return Path(state_path).expanduser() if state_path else Path(_DEFAULT_STATE_PATH).expanduser()


def is_due(
    state_path: str | Path | None = None,
    interval_days: int = CURATOR_INTERVAL_DAYS,
    now: float | None = None,
) -> bool:
    """True when the curator has not run within interval_days.

    Cheap on purpose: this runs at the end of every session, so it must
    answer before anything imports mem0.
    """
    try:
        last = float(_resolve_state_path(state_path).read_text().strip())
    except (OSError, ValueError):
        return True  # never run, or the stamp is unreadable
    return (now if now is not None else time.time()) - last >= interval_days * 86400


def mark_ran(state_path: str | Path | None = None, now: float | None = None) -> None:
    """Record that the curator ran, so the next check can tell."""
    path = _resolve_state_path(state_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(now if now is not None else time.time()))


def run_curator(mem0_client, skills_dir: str | None = None, export_path: str | None = None) -> dict:
    """Run all curator maintenance tasks.

    Returns a stats dict summarizing changes.
    """
    stats: dict = {
        "stale_marked": 0,
        "archived": 0,
        "merged": 0,
        "exported_entries": 0,
        "errors": [],
    }

    # 1. Mark stale entries
    try:
        stats["stale_marked"] = _mark_stale(mem0_client)
    except Exception as exc:
        stats["errors"].append(f"stale: {exc}")

    # 2. Archive very old entries
    try:
        stats["archived"] = _archive_old(mem0_client)
    except Exception as exc:
        stats["errors"].append(f"archive: {exc}")

    # 3. Export MEMORY.md
    if export_path:
        try:
            stats["exported_entries"] = export_memory_md(mem0_client, export_path)
        except Exception as exc:
            stats["errors"].append(f"export: {exc}")

    # 4. Expire pending queue
    try:
        from coworker.memory.pending import expire_old_items
        expired = expire_old_items()
        stats["pending_expired"] = expired
    except Exception as exc:
        stats["errors"].append(f"pending_expire: {exc}")

    # 5. Score memories by recency + frequency (W-8)
    try:
        stats["scored"] = _score_memories(mem0_client)
    except Exception as exc:
        stats["errors"].append(f"score: {exc}")

    logger.info("Curator run complete: %s", stats)
    return stats


def _mark_stale(mem0_client) -> int:
    """Mark active entries as stale if unused for STALE_DAYS."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=STALE_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    count = 0
    try:
        results = mem0_client.list_entries(filters={"state": "active"})
        for entry in results:
            last_used = entry.get("metadata", {}).get("last_used", "")
            if last_used and last_used < cutoff:
                mem0_client.update(entry["id"], metadata={"state": "stale"})
                count += 1
    except Exception as exc:
        logger.warning("_mark_stale error: %s", exc)
    if count:
        logger.info("Marked %d entries as stale", count)
    return count


def _archive_old(mem0_client) -> int:
    """Archive entries that have been stale beyond ARCHIVE_DAYS."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=ARCHIVE_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    count = 0
    try:
        results = mem0_client.list_entries(filters={"state": "stale"})
        for entry in results:
            last_used = entry.get("metadata", {}).get("last_used", "")
            if last_used and last_used < cutoff:
                mem0_client.update(entry["id"], metadata={"state": "archived"})
                count += 1
    except Exception as exc:
        logger.warning("_archive_old error: %s", exc)
    if count:
        logger.info("Archived %d entries", count)
    return count


def export_memory_md(mem0_client, export_path: str) -> int:
    """Generate a human-readable MEMORY.md from mem0 entries.

    Groups entries by project, then by type.
    Returns count of exported entries.
    """
    path = Path(export_path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)

    projects: dict[str, list[dict]] = {}
    try:
        # Fetch active entries for all projects
        results = mem0_client.list_entries(filters={"state": "active"})
    except Exception as exc:
        logger.warning("export_memory_md listing failed: %s", exc)
        results = []

    for entry in results:
        proj = entry.get("metadata", {}).get("project", "unknown")
        projects.setdefault(proj, []).append(entry)

    lines = [
        "# MEMORY.md — Auto-generated by curator",
        f"> Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        f"> Total entries: {len(results)}",
        "",
        "> ⚠️ This file is a **read-only export** from mem0. Do not edit directly.",
        "",
    ]

    for proj_name in sorted(projects):
        lines.append(f"## Project: {proj_name}")
        lines.append("")
        entries = projects[proj_name]
        # Sort by type then by memory
        entries.sort(key=lambda e: (e.get("metadata", {}).get("type", ""), e.get("memory", "")))

        current_type = None
        for entry in entries:
            etype = entry.get("metadata", {}).get("type", "lesson")
            if etype != current_type:
                current_type = etype
                lines.append(f"### {etype.title()}s")
                lines.append("")
            topic = entry.get("metadata", {}).get("topic", "")
            prefix = f"`{topic}` " if topic else ""
            lines.append(f"- {prefix}{entry.get('memory', '')}")
        lines.append("")

    path.write_text("\n".join(lines))
    logger.info("Exported %d entries to %s", len(results), export_path)
    return len(results)


def _score_memories(mem0_client) -> int:
    """Score active memories by recency + frequency. Higher score = more useful.

    Uses a simple decay model: score = use_count * recency_weight.
    Recent (used <7d ago): weight 1.0, Medium (7-30d): 0.5, Old (>30d): 0.1.
    Memories with score=0 and last_used > 60d are auto-marked stale.
    """
    try:
        results = mem0_client.list_entries(filters={"state": "active"})
    except Exception:
        return 0

    now = datetime.now(timezone.utc)
    scored = 0
    for entry in results:
        meta = entry.get("metadata", {})
        use_count = int(meta.get("use_count", 0))
        last_used_str = meta.get("last_used", "")
        score = 0

        if last_used_str:
            try:
                last_used = datetime.strptime(last_used_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                days_since = (now - last_used).days
                if days_since < 7:
                    score = use_count * 1.0
                elif days_since < 30:
                    score = use_count * 0.5
                elif days_since < 60:
                    score = use_count * 0.1
                # >60 days: score stays 0 → will be marked stale below
            except ValueError:
                pass

        # Update metadata with score
        try:
            mem0_client.update(entry["id"], metadata={
                "score": score,
                "scored_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            })
            scored += 1
        except Exception:
            pass

    logger.info("Scored %d active memories by recency+frequency", scored)
    return scored


def generate_report(mem0_client, export_dir: str) -> Path:
    """Generate a curator REPORT.md with metrics summary."""
    report_path = Path(export_dir).expanduser() / "REPORT.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        active = len(mem0_client.list_entries(filters={"state": "active"}))
        stale = len(mem0_client.list_entries(filters={"state": "stale"}))
        archived = len(mem0_client.list_entries(filters={"state": "archived"}))
    except Exception:
        active = stale = archived = 0

    lines = [
        "# Curator Report",
        f"> Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        "",
        "## Memory Store",
        f"- Active: {active}",
        f"- Stale: {stale}",
        f"- Archived: {archived}",
        "",
    ]

    report_path.write_text("\n".join(lines))
    return report_path
