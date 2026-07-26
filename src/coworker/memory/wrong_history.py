"""Wrong-history injection — injects past-mistake prevention rules into Claude context.

Reads all wrong-history entries, extracts prevention rules from critical/high
severity entries, and injects them into CLAUDE.local.md alongside the memory
snapshot.  Runs at session start so the agent always sees what NOT to do.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

WH_DIR = "docs/self-evolving-agent/wrong-history"
MARKER_START = "<!-- WRONG-HISTORY START -->"
MARKER_END = "<!-- WRONG-HISTORY END -->"


def extract_rules(entries_dir: str | None = None) -> list[dict]:
    """Extract prevention rules from all wrong-history entries.

    Returns list of {date, severity, category, rule, summary, session_id}.
    """
    d = Path(entries_dir or WH_DIR) / "entries"
    if not d.exists():
        return []

    rules: list[dict] = []
    for entry_path in sorted(d.glob("*.md"), reverse=True):
        try:
            text = entry_path.read_text()
        except Exception:
            continue

        # Parse frontmatter
        severity = _extract_field(text, "severity", "low")
        if severity not in ("critical", "high"):
            continue

        category = _extract_field(text, "category", "unknown")
        summary = _extract_field(text, "# ", "")
        rule = ""
        for line in text.split("\n"):
            if "**Prevention rule:**" in line:
                rule = line.split("**Prevention rule:**")[-1].strip()
                break

        if rule:
            rules.append({
                "date": _extract_field(text, "date", ""),
                "severity": severity,
                "category": category,
                "rule": rule,
                "summary": summary.strip() if summary else entry_path.stem,
                "session_id": _extract_field(text, "session_id", ""),
            })

    return rules


def build_snapshot(entries_dir: str | None = None) -> str:
    """Build a wrong-history snapshot block with bullet-point rules.

    Returns a markdown string with MARKER_START/END wrappers.
    """
    rules = extract_rules(entries_dir)
    if not rules:
        return f"{MARKER_START}\n<!-- No wrong-history entries yet -->\n{MARKER_END}"

    lines = [
        MARKER_START,
        "## 🚫 Wrong-History Prevention Rules (from past mistakes)",
        "",
        "> These rules come from real mistakes. Break them at your own risk.",
        "",
    ]

    for r in rules:
        sev_icon = "🔴" if r["severity"] == "critical" else "🟡"
        lines.append(f"- {sev_icon} **[{r['category']}]** {r['rule']} _(from {r['date']}: {r['summary']})_")

    lines.append("")
    lines.append(MARKER_END)
    return "\n".join(lines)


def inject_into_local_md(local_md_path: str, snapshot: str | None = None) -> bool:
    """Inject wrong-history rules into CLAUDE.local.md.

    Replaces existing block if present, appends if not.
    Returns True if the file was modified.
    """
    path = Path(local_md_path)
    if snapshot is None:
        snapshot = build_snapshot()

    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(snapshot + "\n")
        return True

    content = path.read_text()

    if MARKER_START in content and MARKER_END in content:
        start_idx = content.index(MARKER_START)
        end_idx = content.index(MARKER_END) + len(MARKER_END)
        new_content = content[:start_idx] + snapshot + content[end_idx:]
        if new_content != content:
            path.write_text(new_content)
            logger.info("Updated wrong-history snapshot in %s", local_md_path)
            return True
        return False

    path.write_text(content.rstrip() + "\n\n" + snapshot + "\n")
    logger.info("Appended wrong-history snapshot to %s", local_md_path)
    return True


def _extract_field(text: str, field: str, default: str) -> str:
    """Extract a frontmatter or markdown heading field."""
    # Frontmatter: field: value
    for line in text.split("\n"):
        if line.strip().startswith(f"{field}:"):
            return line.split(":", 1)[-1].strip()
    # Heading: # value
    if field == "# ":
        for line in text.split("\n"):
            if line.startswith("# ") and not line.startswith("# Index"):
                return line[2:].strip()
    return default
