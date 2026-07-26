"""Auto-worker loop engine — continuous validation and auto-fix.

Runs in a loop (configurable duration).  Each round:
1. Runs all 8 rules
2. Records new findings
3. Exits when no new findings or max duration reached
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


def run_autoworker_loop(
    mem0_client=None,
    llm_client=None,
    db=None,
    max_hours: int = 12,
    project: str = "ai-coworker",
    state_dir: str | None = None,
) -> dict:
    """Run the auto-worker validation loop.

    Args:
        mem0_client: Mem0Client instance (optional, created if None).
        llm_client: LLMClient instance (optional).
        db: AnalyticsDB connection (optional).
        max_hours: Maximum loop duration in hours.
        project: Target project name.
        state_dir: Directory for state files.

    Returns:
        Stats dict with rounds, findings, errors.
    """
    from coworker.autoworker.state import has_been_checked, mark_checked, add_open_question
    from coworker.autoworker.rules import (
        check_mem0_operational,
        check_api_keys,
        check_skills_directory,
        check_pending_queue,
        check_memory_store_size,
    )

    state_dir_path = Path(state_dir) if state_dir else Path("docs/self-evolving-agent/state")
    state_dir_path.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    state_path = state_dir_path / f"auto-worker-{today}-state.md"

    # Initialize state file
    if not state_path.exists():
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        state_path.write_text(
            f"# Auto-Worker Run State\n\n"
            f"**Started:** {now}\n"
            f"**Status:** in_progress\n"
            f"**Max Duration:** {max_hours}h\n"
            f"**Project:** {project}\n\n"
            f"## Open Questions\n\n"
            f"## Checked\n"
            f"| ID | What | Verdict | Date |\n"
            f"|----|------|---------|------|\n"
        )

    start = time.time()
    deadline = start + (max_hours * 3600)
    round_num = 0
    total_findings = 0
    errors: list[str] = []

    while time.time() < deadline:
        round_num += 1
        logger.info("Auto-worker round %d", round_num)
        new_findings = 0

        # Run all 8 rules
        checks = [
            ("C-001", "mem0 operational", lambda: check_mem0_operational()),
            ("C-002", "API keys configured", lambda: check_api_keys()),
            ("C-003", "Skills directory", lambda: check_skills_directory()),
            ("C-004", "Pending queue", lambda: check_pending_queue()),
            ("C-005", "Memory store size", lambda: check_memory_store_size()),
        ]

        for cid, what, check_fn in checks:
            try:
                result = check_fn()
                if not has_been_checked(str(state_path), what):
                    mark_checked(str(state_path), cid, what, result.verdict)
                    new_findings += 1
                    if result.verdict == "NOT_DONE":
                        add_open_question(str(state_path), f"Fix: {what} — {result.evidence}")
                    elif result.verdict == "DONE_WRONG":
                        add_open_question(str(state_path), f"Investigate: {what} — {result.evidence}")
            except Exception as exc:
                errors.append(f"{cid}: {exc}")
                logger.error("Check %s failed: %s", cid, exc)

        total_findings += new_findings

        # Exit conditions
        if new_findings == 0 and round_num > 1:
            logger.info("No new findings after %d rounds — loop complete", round_num)
            break

        if round_num >= 100:
            logger.info("Max rounds (100) reached")
            break

        # Sleep between rounds (minimum 30s)
        if time.time() < deadline:
            time.sleep(30)

    # Mark complete
    content = state_path.read_text()
    content = content.replace("in_progress", "completed")
    state_path.write_text(content)

    elapsed = (time.time() - start) / 60
    logger.info("Auto-worker finished: %d rounds, %d findings, %.1f min", round_num, total_findings, elapsed)
    return {
        "rounds": round_num,
        "findings": total_findings,
        "errors": errors,
        "elapsed_minutes": round(elapsed, 1),
    }
