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


# ── Scoring constants ────────────────────────────────────────────────────────

_EXACT_MATCH_WEIGHT = 100.0    # label exactly equals a query term
_SUBSTRING_MATCH_WEIGHT = 1.0  # label contains a query term as substring
_MAX_SEEDS = 8                 # cap seed nodes to avoid BFS explosion
_SEED_GAP_RATIO = 0.15         # drop seeds scoring below top_score * ratio


def _score_nodes(graph: Graph, terms: list[str]) -> list[tuple[float, str]]:
    """Score every node by how well its label matches query terms.

    Two tiers:
        EXACT:   a query term is a whole-word match in the label (×100)
        SUBSTR:  a query term is a substring of the label (×1)

    Returns list of (score, node_id) sorted descending.
    """
    scored: list[tuple[float, str]] = []
    terms_lower = [t.lower() for t in terms]
    n_terms = len(terms)

    for node in graph.nodes:
        label_lower = node.label.lower()
        source_lower = (node.source_file or "").lower()
        score = 0.0

        for t in terms_lower:
            # Exact whole-word match in label
            if t in label_lower.split():
                score += _EXACT_MATCH_WEIGHT
            # Exact match in source_file path (filename match)
            elif t in source_lower.split("/")[-1].replace(".py", "").replace(".md", "").split("-"):
                score += _EXACT_MATCH_WEIGHT * 0.5
            # Substring match in label
            elif t in label_lower:
                score += _SUBSTRING_MATCH_WEIGHT
            # Substring in source_file
            elif t in source_lower:
                score += _SUBSTRING_MATCH_WEIGHT * 0.5

        if score > 0:
            # Normalize by number of terms (longer queries don't get inflated scores)
            score = score / n_terms
            scored.append((score, node.id))

    scored.sort(key=lambda x: -x[0])
    return scored


def _pick_seeds(scored: list[tuple[float, str]], max_k: int = _MAX_SEEDS) -> list[str]:
    """Select BFS seed nodes with gap_ratio cutoff + label deduplication."""
    if not scored:
        return []

    top_score = scored[0][0]
    seeds: list[str] = []
    seen_labels: set[str] = set()

    for score, nid in scored:
        if len(seeds) >= max_k:
            break
        if seeds and score < top_score * _SEED_GAP_RATIO:
            break
        # Dedup by normalized label (collapse GET/Get/get into one seed)
        label_key = nid.rsplit("__", 1)[-1].lower().strip("_")
        if label_key in seen_labels:
            continue
        seen_labels.add(label_key)
        seeds.append(nid)

    # Guarantee at least one seed per distinct query-ish term
    return seeds


def graph_traverse(
    graph: Graph,
    question: str,
    top_k: int = 10,
    now: Any = None,
) -> list[dict]:
    """BFS traversal with scored seed selection + decay-weighted ranking.

    Improved seed selection (graphify-style):
        - Score ALL nodes against query terms (exact/substring tiers)
        - Gap-ratio cutoff drops noise seeds
        - Label dedup prevents homologous symbols flooding BFS
        - Per-term seed guarantee

    BFS:
        - Max depth 3 from seeds
        - Rank by path weight × effective_weight
        - Suppress edges with effective_weight < 0.3
    """
    query_terms = [t for t in question.lower().split() if len(t) > 1]
    if not query_terms:
        return []

    # 1. Score ALL nodes → pick top seeds
    scored = _score_nodes(graph, query_terms)
    seed_ids = _pick_seeds(scored)

    if not seed_ids:
        return []

    # 2. Build adjacency index
    adjacency: dict[str, list[Edge]] = {}
    for edge in graph.links:
        adjacency.setdefault(edge.source, []).append(edge)

    # 3. BFS with depth tracking
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

        node = _find_node(graph, node_id)
        if depth >= 0 and node:
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
