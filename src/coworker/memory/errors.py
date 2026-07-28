"""Error code registry — spec §9.

Namespaced error codes for the memory platform and auto-worker.
Reuses the QA E0xx style from the deferred qa-autonomous-agent-spec.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Memory / Extraction errors
# ---------------------------------------------------------------------------


class ErrorCode:
    """Namespaced error code with message template."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message

    def format(self, **kwargs) -> str:
        return f"[{self.code}] {self.message.format(**kwargs)}"


# mem0 + extraction
MEM_E001 = ErrorCode("MEM_E001", "mem0 extraction LLM call failed: {detail}")
MEM_E002 = ErrorCode("MEM_E002", "mem0 search returned no results for query: {query}")
MEM_E003 = ErrorCode("MEM_E003", "mem0 add failed after {retries} retries: {detail}")
MEM_E004 = ErrorCode("MEM_E004", "mem0 store corrupt — rebuild required from analytics.db")
MEM_E005 = ErrorCode("MEM_E005", "mem0 vector index corrupt — re-index required")

# Sync / capture
SYNC_E001 = ErrorCode("SYNC_E001", "PostToolUse hook failed to fire: {detail}")
SYNC_E002 = ErrorCode("SYNC_E002", "SubagentStop hook not configured: {detail}")
SYNC_E003 = ErrorCode("SYNC_E003", "Session-end reconciliation failed: {detail}")
SYNC_E004 = ErrorCode("SYNC_E004", "Audit gap detected: session {session_id} has a {gap_minutes:.0f}min gap")
SYNC_E005 = ErrorCode("SYNC_E005", "CLAUDE.local.md lock conflict — concurrent sessions")

# Skill lifecycle
SKILL_E001 = ErrorCode("SKILL_E001", "Skill creation circuit breaker tripped: {count}/{limit} in 24h")
SKILL_E002 = ErrorCode("SKILL_E002", "Skill usage.json corrupt for '{skill_name}': {detail}")
SKILL_E003 = ErrorCode("SKILL_E003", "Skill approval failed: pending item '{skill_id}' not found")
SKILL_E004 = ErrorCode("SKILL_E004", "Skill patch rejected by safety gate: {reason}")
SKILL_E005 = ErrorCode("SKILL_E005", "Curator run failed mid-way at phase '{phase}': {detail}")

# Auto-worker
AUTO_E001 = ErrorCode("AUTO_E001", "Agent session failed: {detail}")
AUTO_E002 = ErrorCode("AUTO_E002", "Validation harness comparison failed: {detail}")
AUTO_E003 = ErrorCode("AUTO_E003", "Context loading failed for path: {path}")


# Registry for lookup
ALL_ERROR_CODES: dict[str, ErrorCode] = {
    c.code: c
    for c in [
        MEM_E001, MEM_E002, MEM_E003, MEM_E004, MEM_E005,
        SYNC_E001, SYNC_E002, SYNC_E003, SYNC_E004, SYNC_E005,
        SKILL_E001, SKILL_E002, SKILL_E003, SKILL_E004, SKILL_E005,
        AUTO_E001, AUTO_E002, AUTO_E003,
    ]
}
