"""Memory platform module — mem0 substrate, capture hooks, and self-evolution engine.

Public API:
    LLMClient — DeepSeek Flash wrapper with provider fallback chain.
    Mem0Client — mem0 wrapper: add, search, update, delete, get.
    audit — Audit trail (write records, check gaps, rebuild index).
    capture — Per-turn and session-end capture (process_turn, process_session_end).
    engine — Evolution engine (extract_and_store, reconcile).
    inject — CLAUDE.local.md context injection.
    pending — Pending queue for staged skill review.
    curator — Periodic maintenance (archive, merge, export).
    train — Batch training pipeline.
    validate — Claude SDK validation harness (A/B comparison).
    safety — Circuit breaker, sandbox, rollback gates.
    errors — Namespaced error codes (MEM_E0xx, SYNC_E0xx, SKILL_E0xx, AUTO_E0xx).
    metrics — Evolution metrics collection and scoring.
"""

from coworker.memory.llm import LLMClient, LLMResponse
from coworker.memory.mem0_client import Mem0Client, ConfigError, Mem0Error

__all__ = [
    "LLMClient",
    "LLMResponse",
    "Mem0Client",
    "ConfigError",
    "Mem0Error",
]
