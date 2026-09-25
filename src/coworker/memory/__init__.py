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
    safety — Circuit breaker. (Sandbox lives in pending; rollback is not
             implemented — see the module docstring.)
    metrics — Evolution metrics collection and scoring.

    graph — Memory Graph data model (Node, Edge, Graph).
    confidence — Confidence tier → numeric score mapping.
    decay — Passive decay computation for graph edges.
    storage — Graph persistence (atomic read/write).
    graphify_sync — Import Graphify skeleton into memory graph.
    merge_worker — Merge pending session dumps into graph.json.
    query — Graph traversal + mem0 hybrid search.
"""

# Re-exported lazily rather than imported eagerly.
#
# This package is imported as a side effect of `import coworker.memory.cli_memory`,
# which coworker.cli does in order to register the `memory` command group. Eager
# imports here therefore made the *entire* CLI depend on openai, mem0, networkx
# and graphify - none of which are installable dependencies of this project
# (graphify is a local tool with no distribution at all). A fresh
# `pip install` produced a CLI that raised ModuleNotFoundError on every
# invocation, including `coworker status`.
#
# Nothing is imported until an attribute is actually requested, so the CLI
# loads with only the declared dependencies; the memory features resolve their
# own requirements when used.
_LAZY_EXPORTS = {
    "LLMClient": "coworker.memory.llm",
    "LLMResponse": "coworker.memory.llm",
    "Mem0Client": "coworker.memory.mem0_client",
    "ConfigError": "coworker.memory.mem0_client",
    "Mem0Error": "coworker.memory.mem0_client",
    "Graph": "coworker.memory.graph",
    "Node": "coworker.memory.graph",
    "Edge": "coworker.memory.graph",
    "confidence_to_score": "coworker.memory.confidence",
    "compute_effective_weight": "coworker.memory.decay",
    "query_filter": "coworker.memory.decay",
    "load_graph": "coworker.memory.storage",
    "save_graph": "coworker.memory.storage",
    "write_json_atomic": "coworker.memory.storage",
}

__all__ = sorted(_LAZY_EXPORTS)


def __getattr__(name: str):
    """PEP 562 lazy attribute access for the re-exports above."""
    module = _LAZY_EXPORTS.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(module), name)
