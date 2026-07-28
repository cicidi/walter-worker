"""Graph persistence — atomic read/write for graph.json.

Spec §8: file layout, schema version, atomic writes.
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any

from .graph import Graph, Node, Edge
from .confidence import confidence_to_score

# Default storage paths
MEMORY_DIR = Path.home() / ".coworker" / "memory"
GRAPH_PATH = MEMORY_DIR / "graph.json"
PENDING_DIR = MEMORY_DIR / "pending"
ARCHIVE_DIR = MEMORY_DIR / "archive"
ARCHIVE_PATH = ARCHIVE_DIR / "graph_archive.json"


def ensure_dirs() -> None:
    """Create memory directories if they don't exist."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def write_json_atomic(path: Path, data: dict[str, Any], indent: int = 2) -> None:
    """Write JSON to path atomically via temp-file + rename.

    Spec §8.4: atomic writes prevent corruption on crash.
    """
    tmp = path.parent / f".{path.name}.tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False, default=str)
    os.replace(tmp, path)


def graph_to_dict(g: Graph) -> dict[str, Any]:
    """Serialize a Graph to a plain dict for JSON writing."""
    return {
        "schema_version": g.schema_version,
        "nodes": [n.model_dump() for n in g.nodes],
        "links": [e.model_dump() for e in g.links],
        "hyperedges": g.hyperedges,
    }


def dict_to_graph(data: dict[str, Any]) -> Graph:
    """Deserialize a dict (from graph.json) into a Graph.

    Handles schema migration stubs for forward compatibility.
    Missing schema_version → treated as 1.0.
    """
    version = data.get("schema_version", "1.0")

    if version == "1.0":
        return Graph(
            schema_version="1.0",
            nodes=[Node(**n) for n in data.get("nodes", [])],
            links=[Edge(**e) for e in data.get("links", [])],
            hyperedges=data.get("hyperedges", []),
        )

    # Future versions: attempt migration
    migrated = _migrate(data, version, "1.0")
    return Graph(
        schema_version="1.0",
        nodes=[Node(**n) for n in migrated.get("nodes", [])],
        links=[Edge(**e) for e in migrated.get("links", [])],
        hyperedges=migrated.get("hyperedges", []),
    )


def _migrate(data: dict, from_version: str, to_version: str) -> dict:
    """Stub migration function for forward compatibility (spec §8.2).

    Currently only handles 1.0 → 1.0 (no-op). When v2 fields are added,
    add a migration path here.
    """
    if from_version == "1.0" and to_version == "1.0":
        return data
    raise ValueError(
        f"No migration path from schema_version={from_version} to {to_version}"
    )


def load_graph(path: Path | None = None) -> Graph:
    """Load the memory graph from disk.

    If graph.json doesn't exist, returns an empty Graph (schema_version 1.0).
    """
    path = path or GRAPH_PATH
    if not path.exists():
        return Graph(schema_version="1.0")
    with open(path, "r") as f:
        data = json.load(f)
    return dict_to_graph(data)


def save_graph(graph: Graph, path: Path | None = None) -> None:
    """Save the memory graph to disk atomically."""
    path = path or GRAPH_PATH
    ensure_dirs()
    write_json_atomic(path, graph_to_dict(graph))
