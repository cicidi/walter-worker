"""Graphify integration — import code/document skeleton into memory graph.

Spec §5: imports Graphify's output (nodes + links) into the memory graph.
Graphify provides the static skeleton; capture sessions add dynamic experience.
We never modify Graphify's file — we copy relevant nodes + edges.

Sync schedule (spec §5.3):
    - On install: graphify . once, import skeleton
    - Weekly cron: 0 3 * * 0 (Sunday 3am) re-sync
    - On-demand: after major PRD/Spec rewrite
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .graph import Graph, Node, Edge
from .confidence import confidence_to_score

logger = logging.getLogger(__name__)

DEFAULT_GRAPHIFY_DIR = Path("graphify-out")
DEFAULT_GRAPHIFY_FILE = DEFAULT_GRAPHIFY_DIR / "graph.json"


def load_graphify_output(path: Path | None = None) -> dict | None:
    """Load Graphify's output JSON.

    Returns None if Graphify hasn't been run yet (no graphify-out/ directory).
    """
    path = path or DEFAULT_GRAPHIFY_FILE
    if not path.exists():
        logger.info("Graphify output not found at %s — skipping sync", path)
        return None
    try:
        return json.loads(path.read_text())
    except Exception as exc:
        logger.warning("Failed to read Graphify output: %s", exc)
        return None


def sync_graphify_skeleton(graph: Graph, graphify_data: dict) -> int:
    """Merge Graphify's static skeleton into the memory graph.

    Spec §5.2 — idempotent merge:
        - New nodes → added to graph
        - Existing nodes → metadata updated, weights preserved
        - New edges → added with confidence_score as base_weight
        - Existing edges → skipped (preserve our weights)

    Args:
        graph: The current memory graph (mutated in place).
        graphify_data: Dict with "nodes" and "links" keys from Graphify.

    Returns:
        Number of new items added (nodes + edges).
    """
    new_nodes = graphify_data.get("nodes", [])
    new_links = graphify_data.get("links", [])
    existing_ids = {n.id for n in graph.nodes}
    existing_edge_keys = {(e.source, e.target, e.relation) for e in graph.links}

    added = 0

    # Merge nodes
    for raw_node in new_nodes:
        node_id = raw_node["id"]
        if node_id in existing_ids:
            # Update metadata, preserve session-derived fields
            for existing in graph.nodes:
                if existing.id == node_id:
                    existing.label = raw_node.get("label", node_id)
                    existing.community = raw_node.get("community")
                    # Keep existing source_file if the new one is empty
                    if raw_node.get("source_file"):
                        existing.source_file = raw_node.get("source_file")
                    break
        else:
            node_type = _infer_node_type(raw_node)
            graph.nodes.append(Node(
                id=node_id,
                type=node_type,
                provenance="graphify",
                label=raw_node.get("label", node_id),
                source_file=raw_node.get("source_file", raw_node.get("file_path")),
                community=raw_node.get("community"),
                metadata=raw_node.get("metadata", {}),
            ))
            added += 1

    # Merge edges
    for link in new_links:
        source = link["source"]
        target = link["target"]
        relation = link.get("relation", "references")
        key = (source, target, relation)

        if key in existing_edge_keys:
            # Existing edge — preserve our weights
            continue

        confidence = link.get("confidence", "INFERRED")
        score = confidence_to_score(confidence)
        graph.links.append(Edge(
            source=source,
            target=target,
            relation=relation,
            confidence=confidence,
            confidence_score=score,
            base_weight=score,
            last_traversed_at=None,
            source_file=link.get("source_file"),
            provenance="graphify",
        ))
        added += 1

    logger.info("Graphify sync: added %d items (%d nodes, %d edges)",
                 added, added - len([l for l in new_links if (l["source"], l["target"], l.get("relation", "references")) not in existing_edge_keys]),
                 len([l for l in new_links if (l["source"], l["target"], l.get("relation", "references")) not in existing_edge_keys]))

    return added


def init_graph_from_graphify(graphify_path: Path | None = None) -> Graph:
    """Create a new graph seeded from Graphify's output.

    Used on first install when no graph.json exists.
    """
    data = load_graphify_output(graphify_path)
    graph = Graph(schema_version="1.0")
    if data:
        sync_graphify_skeleton(graph, data)
        logger.info("Initialized graph from Graphify: %d nodes, %d edges",
                     len(graph.nodes), len(graph.links))
    else:
        logger.info("No Graphify output found — starting with empty graph")
    return graph


def _infer_node_type(raw_node: dict) -> str:
    """Infer node type from Graphify's output fields."""
    file_type = raw_node.get("file_type", raw_node.get("type", ""))
    if file_type in ("code", "py", "ts", "js", "go", "rs", "java", "rb"):
        return "code"
    if file_type in ("document", "doc", "md", "mdx", "rst"):
        return "document"
    # Heuristic: if the id contains a file extension, it's code
    node_id = raw_node.get("id", "")
    if any(node_id.endswith(ext) for ext in (".py", ".ts", ".js", ".go", ".rs")):
        return "code"
    if any(node_id.endswith(ext) for ext in (".md", ".mdx", ".rst")):
        return "document"
    return "code"  # default
