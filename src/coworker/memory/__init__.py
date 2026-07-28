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

    graph — Memory Graph data model (Node, Edge, Graph).
    confidence — Confidence tier → numeric score mapping.
    decay — Passive decay computation for graph edges.
    storage — Graph persistence (atomic read/write).
    graphify_sync — Import Graphify skeleton into memory graph.
    merge_worker — Merge pending session dumps into graph.json.
    query — Graph traversal + mem0 hybrid search.
"""

from coworker.memory.llm import LLMClient, LLMResponse
from coworker.memory.mem0_client import Mem0Client, ConfigError, Mem0Error
from coworker.memory.graph import Graph, Node, Edge
from coworker.memory.confidence import confidence_to_score
from coworker.memory.decay import compute_effective_weight, query_filter
from coworker.memory.storage import load_graph, save_graph, write_json_atomic

__all__ = [
    "LLMClient",
    "LLMResponse",
    "Mem0Client",
    "ConfigError",
    "Mem0Error",
    "Graph",
    "Node",
    "Edge",
    "confidence_to_score",
    "compute_effective_weight",
    "query_filter",
    "load_graph",
    "save_graph",
    "write_json_atomic",
]
