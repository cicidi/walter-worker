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

MAX_DEPTH = 3
MAX_SEEDS = 3  # match graphify default — fewer seeds, higher quality


# ── Public API ──────────────────────────────────────────────────────────────


def query(
    graph: CoworkerGraph,
    question: str,
    mode: str = "graph",
    mem0_client: Any = None,
    top_k: int = 10,
) -> dict:
    """Search the memory graph. Delegates seed selection to graphify."""
    results_graph: list[dict] = []
    results_vector: list[dict] = []

    if mode in ("graph", "both"):
        results_graph = graph_traverse(graph, question, top_k=top_k)

    if mode in ("vector", "both") and mem0_client is not None:
        try:
            results_vector = mem0_client.search(query=question, top_k=top_k)
        except Exception as exc:
            logger.warning("mem0 search failed (non-fatal): %s", exc)

    if mode == "both":
        graph_out = results_graph[:top_k]
        vector_out = [{"memory": r.get("memory", ""), "score": r.get("score", 0.5), "source": "vector",
                       "metadata": r.get("metadata", {})}
                      for r in results_vector[:top_k]]
        results = graph_out + vector_out
    elif mode == "graph":
        results = results_graph[:top_k]
        vector_out = []
    else:
        results = [{"memory": r.get("memory", ""), "score": 1.0, "source": "vector"}
                   for r in results_vector[:top_k]]
        vector_out = []
        graph_out = []

    return {
        "results": results,
        "mode": mode,
        "graph_results": graph_out if mode == "both" else results_graph[:top_k],
        "vector_results": vector_out if mode == "both" else results_vector[:top_k],
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
    return seeds[:_MAX_SEEDS]


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
    """BFS from seeds with decay-weighted ranking."""
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
                    if ew < 0.3:
                        continue
                    queue.append((edge.target, depth + 1, path + [edge]))

    found.sort(key=lambda f: (f["depth"], -f["path_weight"]))
    return found[:top_k]


# ── Helpers ─────────────────────────────────────────────────────────────────


def _find_node(graph: CoworkerGraph, node_id: str) -> Node | None:
    for n in graph.nodes:
        if n.id == node_id:
            return n
    return None


def _merge_and_rank(graph_results: list[dict], vector_results: list[dict]) -> list[dict]:
    seen_ids: set[str] = set()
    merged: list[dict] = []

    for r in graph_results:
        r["source"] = "graph"
        merged.append(r)
        seen_ids.add(r["node_id"])

    for r in vector_results:
        memory = r.get("memory", "")
        if not any(_text_overlap(memory, gr.get("label", "")) for gr in graph_results):
            merged.append({
                "memory": memory,
                "score": r.get("score", 0.5),
                "source": "vector",
                "metadata": r.get("metadata", {}),
            })

    graph_part = [m for m in merged if m.get("source") == "graph"]
    vector_part = [m for m in merged if m.get("source") == "vector"]
    graph_part.sort(key=lambda x: -x.get("path_weight", 0))
    vector_part.sort(key=lambda x: -x.get("score", 0))
    return graph_part + vector_part


def _text_overlap(a: str, b: str) -> bool:
    if not a or not b:
        return False
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    if not words_a or not words_b:
        return False
    overlap = len(words_a & words_b)
    return overlap >= min(len(words_a), len(words_b)) * 0.3
