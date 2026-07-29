"""Graph query API — thin wrapper around graphify's scoring engine.

We don't maintain our own search algorithm. graphify's _score_nodes,
_pick_seeds, and BFS traversal are used directly.
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Any

import networkx as nx

from .graph import Graph as CoworkerGraph, Node, Edge
from .decay import compute_effective_weight, query_filter

logger = logging.getLogger(__name__)

MAX_DEPTH = 6
MAX_SEEDS = 5  # more seeds than graphify to compensate for simpler BFS
_EDGE_SUPPRESS_THRESHOLD = 0.3  # edges below this weight are NOT traversed


# ── Public API ──────────────────────────────────────────────────────────────


def query(
    graph: CoworkerGraph,
    question: str,
    mode: str = "graph",
    mem0_client: Any = None,
    top_k: int = 10,
    min_score: float = 0.3,
    budget: int | None = None,
) -> dict:
    """Search the memory graph + vector memory (mem0).

    Args:
        graph: The memory graph to search.
        question: Natural-language query.
        mode: "graph", "vector", or "both".
        mem0_client: Mem0Client instance (required for vector modes).
        top_k: Max results per source.
        min_score: Minimum score for vector results (default 0.3).
        budget: Token budget per source (None = use top_k only).

    Returns:
        Dict with results, mode, stats.
    """
    results_graph: list[dict] = []
    results_vector: list[dict] = []

    if mode in ("graph", "both"):
        results_graph = graph_traverse(graph, question, top_k=top_k)

    if mode in ("vector", "both") and mem0_client is not None:
        try:
            results_vector = mem0_client.search(
                query=question, top_k=top_k, min_score=min_score,
            )
        except Exception as exc:
            logger.warning("mem0 search failed (non-fatal): %s", exc)

    # Apply quality filter to vector results (belt-and-suspenders with mem0_client.search filter)
    results_vector = [r for r in results_vector if r.get("score", 0) >= min_score]

    # Apply budget cut if specified, otherwise use top_k
    if budget is not None:
        results_graph = _cut_by_budget(results_graph, budget)
        results_vector = _cut_by_budget(results_vector, budget)
    else:
        results_graph = results_graph[:top_k]
        results_vector = results_vector[:top_k]

    # Tag graph results with source
    for r in results_graph:
        r["source"] = "graph"

    if mode == "both":
        graph_out = list(results_graph)
        vector_out = [{"memory": r.get("memory", ""), "score": r.get("score", 0), "source": "vector",
                       "metadata": r.get("metadata", {})}
                      for r in results_vector]
        results = graph_out + vector_out
    elif mode == "graph":
        results = list(results_graph)
        vector_out = []
    else:
        results = [{"memory": r.get("memory", ""), "score": r.get("score", 0), "source": "vector"}
                   for r in results_vector]
        vector_out = []

    return {
        "results": results,
        "mode": mode,
        "graph_results": results_graph,
        "vector_results": results_vector,
        "stats": {
            "graph_hits": len(results_graph),
            "vector_hits": len(results_vector),
            "total_returned": len(results),
        },
    }


def graph_traverse(
    graph: CoworkerGraph,
    question: str,
    top_k: int = 10,
    now: Any = None,
) -> list[dict]:
    """graphify-powered search: score nodes → pick seeds → BFS.

    Seed selection delegated to graphify's _score_nodes + _pick_seeds.
    BFS is our own lightweight implementation (graphify's BFS is tightly
    coupled to its serve layer).
    """
    if not question.strip():
        return []

    # 1. Build networkx graph for graphify scoring
    G = _to_networkx(graph)

    # 2. Score nodes + pick seeds (graphify)
    seed_ids = _graphify_seeds(G, question)

    if not seed_ids:
        return []

    # 3. BFS from seeds (lightweight, our implementation)
    return _bfs_from_seeds(graph, seed_ids, top_k, now)


def _cut_by_budget(items: list[dict], budget_tokens: int) -> list[dict]:
    """Cut items to fit within budget_tokens (~3 chars per token).

    Each item costs len(label_or_memory) + 50 chars for metadata overhead.
    Items beyond the budget are dropped.
    """
    char_budget = budget_tokens * 3
    used = 0
    out: list[dict] = []
    for item in items:
        text = str(item.get("label") or item.get("memory", ""))
        used += len(text) + 50
        if used > char_budget:
            break
        out.append(item)
    return out


def _graphify_seeds(G: nx.Graph, question: str, max_k: int = MAX_SEEDS) -> list[str]:
    """Use graphify's _score_nodes + _pick_seeds to find entry points."""
    try:
        from graphify.serve import _score_nodes, _pick_seeds
    except ImportError:
        logger.warning("graphify not installed — falling back to simple text match")
        return _simple_seeds(G, question)

    terms = [t for t in question.lower().split() if len(t) > 1]
    if not terms:
        return []

    scored = _score_nodes(G, terms)
    seeds = _pick_seeds(scored, max_k=max_k, G=G)
    return seeds


def _simple_seeds(G: nx.Graph, question: str) -> list[str]:
    """Fallback seed selection when graphify is unavailable."""
    terms = set(question.lower().split())
    seeds = []
    for nid in G.nodes:
        label = (G.nodes[nid].get("label") or nid).lower()
        if any(t in label for t in terms):
            seeds.append(nid)
    return seeds[:MAX_SEEDS]


def _to_networkx(graph: CoworkerGraph) -> nx.Graph:
    """Convert coworker Graph to networkx for graphify compatibility."""
    G = nx.Graph()
    for node in graph.nodes:
        G.add_node(
            node.id,
            label=node.label or node.id,
            norm_label=(node.label or node.id).lower(),
            type=node.type or "unknown",
            source_file=node.source_file or "",
            community=node.community or "",
        )
    for edge in graph.links:
        G.add_edge(
            edge.source,
            edge.target,
            relation=edge.relation,
            confidence=edge.confidence,
            base_weight=edge.base_weight,
        )
    return G


def _bfs_from_seeds(
    graph: CoworkerGraph,
    seed_ids: list[str],
    top_k: int,
    now: Any = None,
) -> list[dict]:
    """BFS from seeds with decay-weighted ranking.

    Edges with effective_weight < 0.3 (suppressed) are NOT traversed.
    Edges 0.3-0.5 (stale) are traversed but flagged.
    """
    adjacency: dict[str, list[Edge]] = {}
    for edge in graph.links:
        adjacency.setdefault(edge.source, []).append(edge)

    visited: set[str] = set()
    queue: deque = deque()
    for sid in seed_ids:
        queue.append((sid, 0, []))

    found: list[dict] = []

    while queue:
        node_id, depth, path = queue.popleft()
        if node_id in visited:
            continue
        visited.add(node_id)

        node = _find_node(graph, node_id)
        if node:
            path_weight = 1.0
            path_flags: list[str] = []
            for edge in path:
                ew = compute_effective_weight(edge.base_weight, edge.last_traversed_at, now)
                path_weight *= max(ew, 0.01)
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
                    if ew < _EDGE_SUPPRESS_THRESHOLD:
                        continue  # skip suppressed edges
                    queue.append((edge.target, depth + 1, path + [edge]))

    found.sort(key=lambda f: (f["depth"], -f["path_weight"]))
    return found[:top_k]


# ── Helpers ─────────────────────────────────────────────────────────────────


def _find_node(graph: CoworkerGraph, node_id: str) -> Node | None:
    for n in graph.nodes:
        if n.id == node_id:
            return n
    return None
