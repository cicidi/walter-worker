"""Graph query API — traversal + mem0 hybrid search.

Spec §6: BFS with max depth 3, rank by effective_weight,
prefer EXTRACTED over INFERRED, suppress decayed edges.
Hybrid mode combines graph traversal with mem0 semantic search.
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Any

from .graph import Graph, Node, Edge
from .decay import compute_effective_weight, query_filter

logger = logging.getLogger(__name__)

MAX_DEPTH = 3


# ── Public API ──────────────────────────────────────────────────────────────


def query(
    graph: Graph,
    question: str,
    mode: str = "both",
    mem0_client: Any = None,
    top_k: int = 10,
) -> dict:
    """Search the memory graph for nodes/edges relevant to a question.

    Spec §6.1 — three modes:
        "graph"   — BFS traversal with decay-adjusted weights
        "vector"  — mem0 semantic search (requires mem0_client)
        "both"    — merge and rank results from both

    Returns:
        {"results": [...], "mode": str, "stats": {...}}
    """
    results_graph: list[dict] = []
    results_vector: list[dict] = []

    if mode in ("graph", "both"):
        results_graph = graph_traverse(graph, question, top_k=top_k)

    if mode in ("vector", "both") and mem0_client is not None:
        try:
            results_vector = mem0_client.search(query=question, top_k=top_k)
        except Exception as exc:
            logger.warning("mem0 search failed (non-fatal): %s", exc)
            results_vector = []

    if mode == "both":
        results = _merge_and_rank(results_graph, results_vector)
    elif mode == "graph":
        results = results_graph
    else:
        results = [{"memory": r.get("memory", ""), "score": 1.0, "source": "vector"}
                   for r in results_vector]

    return {
        "results": results[:top_k],
        "mode": mode,
        "stats": {
            "graph_hits": len(results_graph),
            "vector_hits": len(results_vector),
            "total_returned": min(len(results), top_k),
        },
    }


def graph_traverse(
    graph: Graph,
    question: str,
    top_k: int = 10,
    now: Any = None,
) -> list[dict]:
    """BFS traversal with decay-weighted ranking.

    Spec §6.2:
        - Start from nodes matching query terms
        - BFS with max depth 3
        - Rank by edge effective_weight
        - Prefer EXTRACTED edges over INFERRED
        - Suppress edges with effective_weight < 0.3
    """
    # Tokenize question for matching
    query_terms = set(question.lower().split())

    # Find seed nodes — match question terms against node labels + IDs
    seed_ids: list[str] = []
    for node in graph.nodes:
        label_lower = node.label.lower()
        id_lower = node.id.lower()
        if any(term in label_lower or term in id_lower for term in query_terms):
            seed_ids.append(node.id)

    if not seed_ids:
        # Broad match: any node with a label word overlap
        for node in graph.nodes:
            label_words = set(node.label.lower().split())
            if label_words & query_terms:
                seed_ids.append(node.id)
        # Limit seeds to avoid explosion
        seed_ids = seed_ids[:20]

    if not seed_ids:
        return []

    # Build adjacency index
    adjacency: dict[str, list[Edge]] = {}
    for edge in graph.links:
        adjacency.setdefault(edge.source, []).append(edge)

    # BFS with depth tracking
    visited: set[str] = set()
    queue: deque = deque()
    for sid in seed_ids:
        queue.append((sid, 0, []))  # (node_id, depth, path_edges)

    found: list[dict] = []

    while queue:
        node_id, depth, path = queue.popleft()
        if node_id in visited:
            continue
        visited.add(node_id)

        # Find the node object
        node = _find_node(graph, node_id)

        if depth >= 0 and node:
            # Compute cumulative path weight
            path_weight = 1.0
            path_flags: list[str] = []
            for edge in path:
                ew = compute_effective_weight(edge.base_weight, edge.last_traversed_at, now)
                path_weight *= max(ew, 0.01)  # avoid zeroing out
                qf = query_filter(ew)
                if qf != "normal":
                    path_flags.append(qf)

            found.append({
                "node_id": node_id,
                "label": node.label,
                "type": node.type,
                "provenance": node.provenance,
                "depth": depth,
                "path_weight": round(path_weight, 4),
                "flags": path_flags,
                "source_file": node.source_file,
            })

        if depth < MAX_DEPTH:
            for edge in adjacency.get(node_id, []):
                if edge.target not in visited:
                    ew = compute_effective_weight(edge.base_weight, edge.last_traversed_at, now)
                    if ew < 0.3:
                        continue  # suppress decayed edges
                    queue.append((edge.target, depth + 1, path + [edge]))

    # Rank: prefer lower depth, higher path_weight, EXTRACTED edges
    found.sort(key=lambda f: (f["depth"], -f["path_weight"]))
    return found[:top_k]


# ── Helpers ─────────────────────────────────────────────────────────────────


def _find_node(graph: Graph, node_id: str) -> Node | None:
    """Find a node by ID."""
    for n in graph.nodes:
        if n.id == node_id:
            return n
    return None


def _merge_and_rank(graph_results: list[dict], vector_results: list[dict]) -> list[dict]:
    """Merge graph and vector results, deduplicate, rank by relevance.

    Graph results take priority when they have high path_weight.
    Vector results fill gaps.
    """
    seen_ids: set[str] = set()
    merged: list[dict] = []

    # Graph results first
    for r in graph_results:
        r["source"] = "graph"
        merged.append(r)
        seen_ids.add(r["node_id"])

    # Vector results — skip duplicates
    for r in vector_results:
        memory = r.get("memory", "")
        # Simple dedup: if a graph result's label matches vector memory text
        if not any(_text_overlap(memory, gr.get("label", "")) for gr in graph_results):
            merged.append({
                "memory": memory,
                "score": r.get("score", 0.5),
                "source": "vector",
                "metadata": r.get("metadata", {}),
            })

    # Sort: graph results by path_weight (desc), then vector by score (desc)
    graph_part = [m for m in merged if m.get("source") == "graph"]
    vector_part = [m for m in merged if m.get("source") == "vector"]
    graph_part.sort(key=lambda x: -x.get("path_weight", 0))
    vector_part.sort(key=lambda x: -x.get("score", 0))

    return graph_part + vector_part


def _text_overlap(a: str, b: str) -> bool:
    """Check if two strings share significant word overlap."""
    if not a or not b:
        return False
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return False
    overlap = len(words_a & words_b)
    return overlap >= min(len(words_a), len(words_b)) * 0.3
