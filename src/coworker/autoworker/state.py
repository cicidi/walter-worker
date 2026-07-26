"""Auto-worker state file management.

Persists checked items, open questions, and run progress to a
markdown state file so the loop can resume across sessions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def has_been_checked(state_path: str, item_description: str) -> bool:
    """Check if an item has already been recorded in the state file."""
    p = Path(state_path)
    if not p.exists():
        return False
    return item_description in p.read_text()


def mark_checked(state_path: str, item_id: str, what: str, verdict: str) -> None:
    """Record a checked item in the state file."""
    p = Path(state_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not p.exists():
        p.write_text(
            "## Checked\n"
            "| ID | What | Verdict | Date |\n"
            "|----|------|---------|------|\n"
        )

    content = p.read_text()
    if f"| {item_id} |" not in content:
        content += f"| {item_id} | {what} | {verdict} | {today} |\n"
        p.write_text(content)


def add_open_question(state_path: str, question: str) -> str:
    """Add an open question and return its ID."""
    p = Path(state_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    if not p.exists():
        p.write_text(
            "## Open Questions\n"
            "| ID | Question | Asked At | Status |\n"
            "|----|----------|----------|--------|\n"
        )
    content = p.read_text()
    qid = f"Q-{content.count('| Q-') + 1}"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")
    content += f"| {qid} | {question} | {now} | pending |\n"
    p.write_text(content)
    return qid


def get_open_questions(state_path: str) -> list[dict]:
    """Return all pending open questions."""
    p = Path(state_path)
    if not p.exists():
        return []
    questions: list[dict] = []
    for line in p.read_text().split("\n"):
        if "| Q-" in line and "| pending |" in line:
            parts = [c.strip() for c in line.split("|") if c.strip()]
            if len(parts) >= 4:
                questions.append({"id": parts[0], "question": parts[1], "asked_at": parts[2], "status": parts[3] if len(parts) > 3 else "pending"})
    return questions


def load_checked_ids(state_path: str) -> set[str]:
    """Return the set of already-checked item IDs."""
    p = Path(state_path)
    if not p.exists():
        return set()
    ids: set[str] = set()
    for line in p.read_text().split("\n"):
        if line.startswith("| C-"):
            ids.add(line.split("|")[1].strip())
    return ids
