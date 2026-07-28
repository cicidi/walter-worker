"""Graph data model — Node, Edge, and Graph types.

Schema version 1.0. See docs/self-evolving-agent/spec/memory-graph-spec.md §1.
"""

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


# ── Node types ──────────────────────────────────────────────────────────────

NodeType = Literal["code", "document", "session", "decision_point", "concept"]
Provenance = Literal["graphify", "capture"]


class Node(BaseModel):
    """A node in the memory graph.

    Node types (spec §1.1):
        code — static code symbol from Graphify
        document — static doc section from Graphify
        session — AI session root from capture.py
        decision_point — decision made in a session
        concept — abstract concept from either source
    """

    id: str
    type: NodeType
    provenance: Provenance
    label: str = ""

    # Graphify metadata (code/document nodes)
    source_file: str | None = None
    community: str | None = None

    # Session metadata (session/decision_point nodes)
    session_count: int = 1
    last_seen: str | None = None  # ISO timestamp
    related_file: str | None = None

    # Extra fields carried through from source
    metadata: dict = Field(default_factory=dict)


# ── Edge relation types ─────────────────────────────────────────────────────

RelationType = Literal[
    "calls",
    "imports",
    "implements",
    "references",
    "depends_on",
    "tried",
    "pivoted_to",
    "modifies",
    "contradicts",
    "verifies",
    "discusses",
]

ConfidenceTier = Literal["EXTRACTED", "INFERRED", "AMBIGUOUS", "WEAK"]


class Edge(BaseModel):
    """A directed edge in the memory graph.

    Spec §1.2 — full edge schema.

    confidence_score is the NUMERIC equivalent of confidence tier (never compare
    tier strings — see spec §1.3 for why). Use confidence_to_score() to convert.
    """

    source: str
    target: str
    relation: RelationType
    confidence: ConfidenceTier
    confidence_score: float  # EXTRACTED=0.9, INFERRED=0.7, AMBIGUOUS=0.5, WEAK=0.2
    base_weight: float
    last_traversed_at: str | None = None  # ISO timestamp or null
    source_file: str | None = None
    provenance: Provenance

    # Verification trail (v2 — spec §3.3)
    verified_by: list[dict] = Field(default_factory=list)


# ── Graph ────────────────────────────────────────────────────────────────────


class Graph(BaseModel):
    """The full memory graph.

    Schema version for forward compatibility (spec §8.2).
    On load, check schema_version. If missing → treat as 1.0.
    """

    schema_version: str = "1.0"
    nodes: list[Node] = Field(default_factory=list)
    links: list[Edge] = Field(default_factory=list)
    hyperedges: list[dict] = Field(default_factory=list)
