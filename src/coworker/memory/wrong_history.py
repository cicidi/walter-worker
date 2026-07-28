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


def record_entry(
    summary: str,
    prevention_rule: str,
    *,
    severity: str = "high",
    category: str = "code-quality",
    what_happened: str = "",
    root_cause: str = "",
    fix: str = "",
    impact: str = "",
    tags: list[str] | None = None,
    session_id: str = "",
) -> Path | None:
    """Create a new wrong-history entry programmatically.

    Called by the auto-worker after fixing a bug to document the lesson.
    Returns the path to the created entry, or None on failure.
    """
    d = Path(WH_DIR) / "entries"
    d.mkdir(parents=True, exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    slug = summary.lower().replace(" ", "-").replace("/", "-")[:60]
    path = d / f"{today}-{slug}.md"

    if path.exists():
        logger.info("Wrong-history entry already exists: %s", path.name)
        return path

    tag_list = ", ".join(tags) if tags else ""
    content = f"""---
date: {today}
session_id: {session_id}
severity: {severity}
category: {category}
tags: [{tag_list}]
---

# {summary}

**What happened:** {what_happened or summary}

**Root cause:** {root_cause or "Discovered during auto-worker inspection"}

**How it was discovered:** auto-worker health check

**Impact:** {impact or "Unknown — auto-detected"}

**Fix:** {fix or "Auto-fixed by auto-worker"}

**Prevention rule:** {prevention_rule}

**Anti-pattern:** Not following the prevention rule above

**Related entries:**
"""
    try:
        path.write_text(content)
        logger.info("Created wrong-history entry: %s", path.name)
        _rebuild_index()
        return path
    except Exception as e:
        logger.error("Failed to create wrong-history entry: %s", e)
        return None


def _rebuild_index() -> None:
    """Rebuild the wrong-history INDEX.md from all entries."""
    d = Path(WH_DIR) / "entries"
    entries = sorted(d.glob("*.md"), reverse=True) if d.exists() else []

    by_severity: dict[str, list[dict]] = {"critical": [], "high": [], "medium": [], "low": []}
    for ep in entries:
        try:
            text = ep.read_text()
            sev = _extract_field(text, "severity", "low")
            cat = _extract_field(text, "category", "unknown")
            summary = _extract_field(text, "# ", ep.stem)
            rule = ""
            for line in text.split("\n"):
                if "**Prevention rule:**" in line:
                    rule = line.split("**Prevention rule:**")[-1].strip()[:120]
                    break
            by_severity.setdefault(sev, []).append({
                "date": _extract_field(text, "date", ep.stem[:10]),
                "slug": ep.stem,
                "category": cat,
                "summary": summary.strip() if summary else ep.stem,
                "rule": rule,
            })
        except Exception:
            continue

    total = sum(len(v) for v in by_severity.values())
    lines = [
        "# Wrong History — Index",
        "",
        "> **Purpose:** Prevent repeating past mistakes.",
        "> **Check before coding:** `grep -rl \"<keyword>\" docs/self-evolving-agent/wrong-history/entries/`",
        "",
    ]

    for sev in ["critical", "high", "medium", "low"]:
        items = by_severity.get(sev, [])
        if not items:
            continue
        icon = {"critical": "🔴", "high": "🟡", "medium": "🟠", "low": "⚪"}.get(sev, "")
        lines.append(f"## {icon} {sev.capitalize()}")
        lines.append("| Date | Entry | Category | Prevention Rule |")
        lines.append("|------|-------|----------|-----------------|")
        for item in items:
            rule_short = (item["rule"][:80] + "...") if len(item["rule"]) > 80 else item["rule"]
            lines.append(
                f"| {item['date']} | [{item['summary']}](entries/{item['slug']}.md) "
                f"| {item['category']} | {rule_short} |"
            )
        lines.append("")

    lines.append("## Stats")
    lines.append(f"- **Total entries:** {total}")
    for sev in ["critical", "high", "medium", "low"]:
        count = len(by_severity.get(sev, []))
        if count:
            icon = {"critical": "🔴", "high": "🟡", "medium": "🟠", "low": "⚪"}.get(sev, "")
            lines.append(f"- **{icon} {sev.capitalize()}:** {count}")

    idx_path = Path(WH_DIR) / "INDEX.md"
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    idx_path.write_text("\n".join(lines) + "\n")
    logger.info("Rebuilt wrong-history INDEX with %d entries", total)


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
