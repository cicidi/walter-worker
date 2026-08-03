"""CLAUDE.local.md context injection — frozen snapshot at session start.

Reads relevant mem0 entries at session start and injects them into
CLAUDE.local.md between marker comments.  The snapshot is frozen —
mid-session mem0 writes do not refresh it.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MARKER_START = "<!-- MEMORY:{project} START -->"
MARKER_END = "<!-- MEMORY:{project} END -->"


def build_snapshot(mem0_client, project: str = "walter-worker", top_k: int = 10) -> str:
    """Build a memory snapshot block for injection into CLAUDE.local.md.

    Args:
        mem0_client: Mem0Client instance.
        project: Project name to filter memories.
        top_k: Max entries to include.

    Returns:
        Markdown-formatted snapshot string with markers.
    """
    try:
        results = mem0_client.search(
            query="project context knowledge convention preference",
            filters={"project": project, "state": "active"},
            top_k=top_k,
        )
    except Exception as exc:
        logger.warning("mem0 search failed during snapshot build: %s", exc)
        results = []

    if not results:
        return f"{MARKER_START.format(project=project)}\n<!-- No stored memories yet -->\n{MARKER_END.format(project=project)}"

    lines = [MARKER_START.format(project=project), "## Memory Snapshot (frozen at session start)"]

    for entry in results:
        memory_text = entry.get("memory", "")
        meta = entry.get("metadata", {})
        entry_type = meta.get("type", "lesson")
        prefix = {"lesson": "🔧", "convention": "📋", "preference": "⚙️", "state": "📌"}.get(entry_type, "📝")
        lines.append(f"- {prefix} {memory_text}")

    lines.append(MARKER_END.format(project=project))
    return "\n".join(lines)


def inject_into_local_md(local_md_path: str, snapshot: str, project: str = "walter-worker") -> bool:
    """Inject (or replace) a memory snapshot block in CLAUDE.local.md.

    Args:
        local_md_path: Path to CLAUDE.local.md.
        snapshot: The snapshot string (including markers) to inject.
        project: Project name (used in markers).

    Returns:
        True if the file was modified, False otherwise.
    """
    path = Path(local_md_path)
    if not path.exists():
        logger.info("CLAUDE.local.md not found at %s; creating with snapshot.", local_md_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(snapshot + "\n")
        return True

    content = path.read_text()
    start_marker = MARKER_START.format(project=project)
    end_marker = MARKER_END.format(project=project)

    # Replace existing block if present
    if start_marker in content and end_marker in content:
        start_idx = content.index(start_marker)
        end_idx = content.index(end_marker) + len(end_marker)
        new_content = content[:start_idx] + snapshot + content[end_idx:]
        if new_content != content:
            path.write_text(new_content)
            logger.info("Updated memory snapshot in %s", local_md_path)
            return True
        return False

    # Append if no existing block
    path.write_text(content.rstrip() + "\n\n" + snapshot + "\n")

    # Verify the injection actually worked (R-1, C-10)
    try:
        verify = path.read_text()
        if start_marker in verify and end_marker in verify:
            logger.info("Appended memory snapshot to %s (verified)", local_md_path)
        else:
            logger.error("Snapshot injection verification FAILED for %s", local_md_path)
            return False
    except Exception:
        logger.warning("Could not verify snapshot injection in %s", local_md_path)

    return True


def remove_snapshot(local_md_path: str, project: str = "walter-worker") -> bool:
    """Remove the memory snapshot block from CLAUDE.local.md.

    Returns True if the block was found and removed.
    """
    path = Path(local_md_path)
    if not path.exists():
        return False

    content = path.read_text()
    start_marker = MARKER_START.format(project=project)
    end_marker = MARKER_END.format(project=project)

    if start_marker in content and end_marker in content:
        start_idx = content.index(start_marker)
        end_idx = content.index(end_marker) + len(end_marker)
        # Remove leading newlines before the block
        while start_idx > 0 and content[start_idx - 1] == "\n":
            start_idx -= 1
        new_content = content[:start_idx] + content[end_idx:]
        path.write_text(new_content)
        return True
    return False
