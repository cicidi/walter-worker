"""Merge worker — enrich, validate, dedup, and merge pending session dumps.

Spec §8.3: single-threaded merge worker triggered by the session-end hook
(coworker memory close). Reads pending/<session>.json, enriches edges,
validates targets, deduplicates nodes, and atomically writes graph.json.
"""

from __future__ import annotations

import difflib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .graph import Graph, Node, Edge
from .confidence import confidence_to_score
from .storage import (
    PENDING_DIR,
    GRAPH_PATH,
    load_graph,
    save_graph,
    write_json_atomic,
)

logger = logging.getLogger(__name__)


def process_pending(pending_path: Path | None = None) -> dict:
    """Process a single pending session dump into graph.json.

    Spec §8.3 pipeline:
        1. Read pending/<session>.json
        2. ENRICH: base_weight, last_traversed_at, provenance
        3. VALIDATE: skip edges with dangling targets
        4. DEDUP: merge similar nodes → reuse existing IDs
        5. MERGE: append to graph.json (atomic os.replace)
        6. DELETE: remove pending file

    Returns stats dict.
    """
    pending_path = pending_path or _find_next_pending()
    if pending_path is None:
        return {"status": "no_pending", "added_nodes": 0, "added_edges": 0}

    # 1. Read pending dump
    try:
        dump = json.loads(pending_path.read_text())
    except Exception as exc:
        logger.error("Failed to read pending file %s: %s", pending_path, exc)
        return {"status": "error", "error": str(exc)}

    session_id = dump.get("session_id", pending_path.stem)
    raw_nodes = dump.get("nodes", dump.get("session_nodes", []))
    raw_edges = dump.get("edges", dump.get("session_edges", []))

    # 2. Load current graph
    graph = load_graph()
    existing_ids = {n.id for n in graph.nodes}

    stats = {"status": "ok", "added_nodes": 0, "added_edges": 0, "graph_misses": 0, "deduped": 0}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Collect IDs that will exist after this merge (existing + new from this session)
    new_node_ids: set[str] = set()

    # 2a. ENRICH + DEDUP nodes
    new_nodes: list[Node] = []
    for raw_node in raw_nodes:
        node = _enrich_node(raw_node, session_id, now)
        deduped_id = _dedup_and_merge(graph, node)
        if deduped_id != node.id:
            stats["deduped"] += 1
            new_node_ids.add(deduped_id)
        else:
            new_nodes.append(node)
            new_node_ids.add(node.id)

    # 2b. ENRICH + VALIDATE edges
    valid_target_ids = existing_ids | new_node_ids
    new_edges: list[Edge] = []
    for raw_edge in raw_edges:
        edge = _enrich_edge(raw_edge, session_id, now)
        # Validate target exists (spec §4.2 review #8)
        if edge.target not in valid_target_ids:
            logger.debug("graph_miss: edge %s → %s (target not in graph)", edge.source, edge.target)
            stats["graph_misses"] += 1
            continue
        new_edges.append(edge)

    # 3. Append to graph
    for node in new_nodes:
        graph.nodes.append(node)
        stats["added_nodes"] += 1
    for edge in new_edges:
        graph.links.append(edge)
        stats["added_edges"] += 1

    # 4. Atomic write
    save_graph(graph)

    # 5. Remove pending file
    try:
        pending_path.unlink()
    except Exception as exc:
        logger.warning("Failed to delete pending file %s: %s", pending_path, exc)

    logger.info("Merge worker: +%d nodes, +%d edges, %d deduped, %d misses for session %s",
                 stats["added_nodes"], stats["added_edges"], stats["deduped"], stats["graph_misses"], session_id)
    return stats


def process_all_pending() -> dict:
    """Process ALL pending session dumps.

    Called on startup or when catching up after a crash.
    Returns aggregate stats.
    """
    total = {"status": "ok", "sessions_processed": 0, "added_nodes": 0, "added_edges": 0, "graph_misses": 0, "deduped": 0}
    for pending_path in sorted(PENDING_DIR.glob("*.json")):
        stats = process_pending(pending_path)
        if stats["status"] == "ok":
            total["sessions_processed"] += 1
            total["added_nodes"] += stats["added_nodes"]
            total["added_edges"] += stats["added_edges"]
            total["graph_misses"] += stats.get("graph_misses", 0)
            total["deduped"] += stats.get("deduped", 0)
    return total


# ── Enrichment ──────────────────────────────────────────────────────────────


def _enrich_node(raw_node: dict, session_id: str, now: str) -> Node:
    """Add provenance, timestamps, and defaults to a raw session node."""
    return Node(
        id=raw_node.get("id", f"{session_id}::unknown"),
        type=raw_node.get("type", "session"),
        provenance="capture",
        label=raw_node.get("label", raw_node.get("id", "")),
        source_file=raw_node.get("source_file"),
        related_file=raw_node.get("related_file"),
        last_seen=now,
        session_count=1,
        metadata=raw_node.get("metadata", {}),
    )


def _enrich_edge(raw_edge: dict, session_id: str, now: str) -> Edge:
    """Add base_weight, last_traversed_at, and provenance to a raw edge.

    Spec §4.2: base_weight = confidence_to_score(confidence).
    Spec §3.3 v1-gap: last_traversed_at is refreshed here so decay fires in v1.
    """
    confidence = raw_edge.get("confidence", "AMBIGUOUS")
    score = confidence_to_score(confidence)
    return Edge(
        source=raw_edge["source"],
        target=raw_edge["target"],
        relation=raw_edge.get("relation", "references"),
        confidence=confidence,
        confidence_score=score,
        base_weight=score,
        last_traversed_at=now,  # refreshed on every session reference (v1 decay trigger)
        source_file=raw_edge.get("source_file"),
        provenance="capture",
    )


# ── Dedup ───────────────────────────────────────────────────────────────────


def _dedup_and_merge(graph: Graph, new_node: Node) -> str:
    """Deduplicate a session node against existing graph nodes.

    Spec §4.3: same type + related_file + similar label (>0.7) → merge.
    Returns the effective node ID (existing if merged, new_node.id if unique).

    _similarity is pinned to difflib.SequenceMatcher (spec §4.3 review #7).
    """
    for existing in graph.nodes:
        if existing.type != new_node.type:
            continue
        if existing.related_file and new_node.related_file:
            if existing.related_file != new_node.related_file:
                continue
        if _similarity(existing.label, new_node.label) > 0.7:
            # Merge: increment count, update timestamp
            existing.session_count = existing.session_count + 1
            existing.last_seen = new_node.last_seen
            return existing.id
    return new_node.id


def _similarity(a: str, b: str) -> float:
    """Label similarity in [0, 1]. 1.0 = identical.

    Pinned to difflib.SequenceMatcher so the 0.7 threshold has a single,
    reproducible meaning (spec §4.3 review #7).
    """
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


# ── Helpers ─────────────────────────────────────────────────────────────────


def _find_next_pending() -> Path | None:
    """Find the next pending session dump to process."""
    if not PENDING_DIR.exists():
        return None
    files = sorted(PENDING_DIR.glob("*.json"))
    return files[0] if files else None


def write_session_pending(session_id: str, session_nodes: list[dict], session_edges: list[dict]) -> Path:
    """Write a raw session dump to the pending directory.

    Spec §4.2: capture.py calls this — writes raw data only. No enrichment.
    The merge worker enriches + dedups + merges later.

    Returns the path to the pending file.
    """
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    dump = {
        "session_id": session_id,
        "nodes": session_nodes,
        "edges": session_edges,
    }
    path = PENDING_DIR / f"{session_id}.json"
    write_json_atomic(path, dump)
    logger.info("Wrote session pending: %s (%d nodes, %d edges)",
                session_id, len(session_nodes), len(session_edges))
    return path
