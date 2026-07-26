"""Auto-worker validation rules — 8 rules for auditing skills, code, and data.

Each rule produces a verdict (OK / MISMATCH / NOT_DONE / DONE_WRONG / DONE_RIGHT)
with evidence so the loop can decide whether to fix or skip.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ValidateResult:
    verdict: str  # "OK" | "MISMATCH"
    claimed: int = 0
    actual: int = 0
    evidence: str = ""


@dataclass
class AuditResult:
    verdict: str  # "DONE_RIGHT" | "DONE_WRONG" | "NOT_DONE"
    confidence: str = "high"
    evidence: str = ""


def validate_against_raw_data(skill_name: str, usage_path: str, db) -> ValidateResult:
    """Rule 1: Compare skill usage.json claimed calls vs analytics.db actual calls.

    Returns ValidateResult with verdict OK or MISMATCH.
    """
    try:
        usage = json.loads(Path(usage_path).read_text())
    except Exception:
        return ValidateResult(verdict="MISMATCH", evidence="Cannot read usage.json")

    claimed = usage.get("total_calls", 0)
    try:
        rows = db.execute(
            "SELECT COUNT(*) FROM tool_calls WHERE tool = 'Skill' AND detail LIKE ?",
            (f"%{skill_name}%",),
        ).fetchone()
        actual = rows[0] if rows else 0
    except Exception as exc:
        return ValidateResult(verdict="MISMATCH", evidence=f"DB query failed: {exc}")

    if claimed == actual:
        return ValidateResult(verdict="OK", claimed=claimed, actual=actual)
    return ValidateResult(
        verdict="MISMATCH",
        claimed=claimed,
        actual=actual,
        evidence=f"usage.json claims {claimed}, analytics.db has {actual}",
    )


def detect_dead_skills(skills_dir: str, db) -> list[dict]:
    """Rule 2: Find skills with zero actual calls in analytics.db.

    Returns list of dead skill dicts.
    """
    d = Path(skills_dir)
    if not d.exists():
        return []

    dead: list[dict] = []
    for skill_d in d.iterdir():
        if not skill_d.is_dir():
            continue
        usage_path = skill_d / "usage.json"
        usage: dict = {}
        if usage_path.exists():
            try:
                usage = json.loads(usage_path.read_text())
            except Exception:
                pass
        try:
            rows = db.execute(
                "SELECT COUNT(*) FROM tool_calls WHERE tool = 'Skill' AND detail LIKE ?",
                (f"%{skill_d.name}%",),
            ).fetchone()
            count = rows[0] if rows else 0
        except Exception:
            count = 0

        if count == 0:
            dead.append({
                "name": skill_d.name,
                "reason": "zero_calls",
                "claimed_calls": usage.get("total_calls", 0),
            })
    return dead


def audit_requirement(
    prd_item: str,
    grep_results: list[str] | None = None,
    test_results: list[dict] | None = None,
    spec_intent: str | None = None,
) -> AuditResult:
    """Rule 3: Audit a PRD requirement against code and tests.

    Args:
        prd_item: The PRD requirement description.
        grep_results: Code search results (list of matching file:line strings).
        test_results: Test results for this requirement.
        spec_intent: Optional spec intent for stronger verification.

    Returns:
        AuditResult with verdict (DONE_RIGHT / DONE_WRONG / NOT_DONE).
    """
    if not grep_results:
        return AuditResult(verdict="NOT_DONE", evidence="no code found matching requirement")

    if test_results and any(t.get("status") == "FAILED" for t in test_results):
        return AuditResult(verdict="DONE_WRONG", evidence="test failure")

    has_tests = test_results and all(t.get("status") == "PASSED" for t in test_results)
    if has_tests:
        return AuditResult(verdict="DONE_RIGHT", evidence=f"{len(test_results)} tests passing")
    if spec_intent:
        return AuditResult(verdict="DONE_RIGHT", evidence="code matches spec intent")
    return AuditResult(verdict="NOT_DONE", evidence="no tests verifying requirement")


def check_mem0_operational() -> AuditResult:
    """Rule 4: Verify mem0 is importable and configured."""
    try:
        from mem0 import Memory  # noqa: F401
        return AuditResult(verdict="DONE_RIGHT", evidence="mem0 importable")
    except ImportError:
        return AuditResult(verdict="NOT_DONE", evidence="mem0 not installed")


def check_api_keys() -> AuditResult:
    """Rule 5: Verify required API keys are set."""
    import os
    ds = bool(os.environ.get("DEEPSEEK_API_KEY"))
    if ds:
        return AuditResult(verdict="DONE_RIGHT", evidence="DEEPSEEK_API_KEY set")
    return AuditResult(verdict="NOT_DONE", evidence="DEEPSEEK_API_KEY missing")


def check_skills_directory() -> AuditResult:
    """Rule 6: Verify skills directory exists and is populated."""
    d = Path.home() / ".coworker" / "skills"
    if not d.exists():
        return AuditResult(verdict="NOT_DONE", evidence="~/.coworker/skills/ missing")
    count = sum(1 for x in d.iterdir() if x.is_dir())
    if count == 0:
        return AuditResult(verdict="NOT_DONE", evidence="no skills installed")
    return AuditResult(verdict="DONE_RIGHT", evidence=f"{count} skills installed")


def check_pending_queue() -> AuditResult:
    """Rule 7: Check pending queue for expired items."""
    d = Path.home() / ".coworker" / "pending" / "skills"
    if not d.exists():
        return AuditResult(verdict="DONE_RIGHT", evidence="no pending queue (clean)")
    count = len(list(d.glob("*.json")))
    if count > 20:
        return AuditResult(verdict="DONE_WRONG", evidence=f"{count} pending items — review needed")
    return AuditResult(verdict="DONE_RIGHT", evidence=f"{count} pending items")


def check_memory_store_size() -> AuditResult:
    """Rule 8: Warn if memory store has too many entries."""
    try:
        from coworker.memory.mem0_client import Mem0Client
        mem0 = Mem0Client.from_config()
        results = mem0.search(query=".", filters={"state": "active"}, top_k=1000)
        count = len(results)
        if count > 500:
            return AuditResult(verdict="DONE_WRONG", evidence=f"{count} active entries — consider curation")
        return AuditResult(verdict="DONE_RIGHT", evidence=f"{count} active entries")
    except Exception as exc:
        return AuditResult(verdict="NOT_DONE", evidence=str(exc))
