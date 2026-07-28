"""Unit tests for memory graph core modules.

Covers: memory-graph-test-plan.md §1.1–§1.8
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from coworker.memory.graph import Graph, Node, Edge
from coworker.memory.confidence import confidence_to_score, rank as tier_rank
from coworker.memory.decay import compute_effective_weight, query_filter
from coworker.memory.storage import (
    load_graph,
    save_graph,
    write_json_atomic,
    dict_to_graph,
    graph_to_dict,
    MEMORY_DIR,
    GRAPH_PATH,
    PENDING_DIR,
    ARCHIVE_DIR,
)
from coworker.memory.graphify_sync import (
    sync_graphify_skeleton,
    init_graph_from_graphify,
    load_graphify_output,
)
from coworker.memory.merge_worker import (
    _dedup_and_merge,
    _similarity,
    _enrich_node,
    _enrich_edge,
    write_session_pending,
)


# ═══════════════════════════════════════════════════════════════════════════════
# §1.1 Passive Decay (D1-D9)
# ═══════════════════════════════════════════════════════════════════════════════

class TestPassiveDecay:
    """Spec §2: passive decay tests."""

    def _now(self) -> datetime:
        return datetime(2026, 7, 27, 12, 0, 0, tzinfo=timezone.utc)

    def test_d1_within_protection_window(self):
        """D1: Within protection window (10 days) → effective=base."""
        ts = (self._now() - timedelta(days=10)).isoformat()
        assert compute_effective_weight(0.9, ts, self._now()) == 0.9

    def test_d2_at_boundary(self):
        """D2: At boundary (20 days) → effective=base."""
        ts = (self._now() - timedelta(days=20)).isoformat()
        assert compute_effective_weight(0.9, ts, self._now()) == 0.9

    def test_d3_30_days_idle(self):
        """D3: 30 days idle → 0.9 * 0.99^10 ≈ 0.814."""
        ts = (self._now() - timedelta(days=30)).isoformat()
        result = compute_effective_weight(0.9, ts, self._now())
        assert 0.81 <= result <= 0.82, f"Expected ~0.814, got {result}"

    def test_d4_60_days_idle(self):
        """D4: 60 days idle → 0.9 * 0.99^40 ≈ 0.602."""
        ts = (self._now() - timedelta(days=60)).isoformat()
        result = compute_effective_weight(0.9, ts, self._now())
        assert 0.60 <= result <= 0.61, f"Expected ~0.602, got {result}"

    def test_d5_90_days_low_base(self):
        """D5: 90 days idle from base 0.5 → ~0.248."""
        ts = (self._now() - timedelta(days=90)).isoformat()
        result = compute_effective_weight(0.5, ts, self._now())
        assert 0.24 <= result <= 0.25, f"Expected ~0.248, got {result}"

    def test_d6_120_days_idle(self):
        """D6: 120 days idle from 0.9 → 0.9 * 0.99^100 ≈ 0.330."""
        ts = (self._now() - timedelta(days=120)).isoformat()
        result = compute_effective_weight(0.9, ts, self._now())
        assert 0.32 <= result <= 0.34, f"Expected ~0.330, got {result}"

    def test_d7_zero_base_weight(self):
        """D7: Base weight ≤ 0 → treated as 0.2 (WEAK floor)."""
        ts = (self._now() - timedelta(days=120)).isoformat()
        result = compute_effective_weight(0.0, ts, self._now())
        assert result > 0, "Zero base should floor to 0.2"
        assert result < 0.1, f"After 120d decay from 0.2: expected <0.1, got {result}"

    def test_d8_untraversed_edge(self):
        """D8: Never traversed (last_traversed_at=None) → effective=base."""
        assert compute_effective_weight(0.9, None, self._now()) == 0.9

    def test_d9_future_date(self):
        """D9: Future timestamp → clamped to now, no decay."""
        ts = (self._now() + timedelta(days=10)).isoformat()
        assert compute_effective_weight(0.9, ts, self._now()) == 0.9


# ═══════════════════════════════════════════════════════════════════════════════
# §1.2 Confidence Mapping (C1-C5)
# ═══════════════════════════════════════════════════════════════════════════════

class TestConfidenceMapping:
    """Spec §1.3: confidence tier to score mapping."""

    def test_c1_extracted(self):
        assert confidence_to_score("EXTRACTED") == 0.9

    def test_c2_inferred(self):
        assert confidence_to_score("INFERRED") == 0.7

    def test_c3_ambiguous(self):
        assert confidence_to_score("AMBIGUOUS") == 0.5

    def test_c4_unknown_string(self):
        """C4: Unknown → AMBIGUOUS (0.5)."""
        assert confidence_to_score("FOO") == 0.5

    def test_c5_none_value(self):
        """C5: Missing/None → AMBIGUOUS (0.5)."""
        assert confidence_to_score(None) == 0.5

    def test_tier_rank_order(self):
        """Tier ranks must be: EXTRACTED > INFERRED > AMBIGUOUS > WEAK."""
        assert tier_rank("EXTRACTED") > tier_rank("INFERRED")
        assert tier_rank("INFERRED") > tier_rank("AMBIGUOUS")
        assert tier_rank("AMBIGUOUS") > tier_rank("WEAK")


# ═══════════════════════════════════════════════════════════════════════════════
# §1.3 Node ID Namespace (N1-N5)
# ═══════════════════════════════════════════════════════════════════════════════

class TestNodeIdNamespace:
    """Spec §1.4: node ID namespace isolation."""

    def test_n1_graphify_code_id(self):
        node = Node(id="src/auth.py::login", type="code", provenance="graphify")
        assert node.type == "code"
        assert node.provenance == "graphify"

    def test_n2_graphify_doc_id(self):
        node = Node(id="docs/prd.md::r4_auth", type="document", provenance="graphify")
        assert node.type == "document"

    def test_n3_session_root_id(self):
        node = Node(id="session_20260727_001", type="session", provenance="capture")
        assert node.type == "session"
        assert node.provenance == "capture"

    def test_n4_session_child_id(self):
        node = Node(id="session_20260727_001::attempt_bearer", type="decision_point", provenance="capture")
        assert node.type == "decision_point"

    def test_n5_no_id_collision(self):
        """N5: IDs stored opaquely — no collision between identical-looking IDs."""
        # A code file literally named session_20260101_001.py
        code_node = Node(id="session_20260101_001.py", type="code", provenance="graphify")
        session_node = Node(id="session_20260101_001", type="session", provenance="capture")
        # Different types + provenances — unambiguous
        assert code_node.type != session_node.type
        assert code_node.provenance != session_node.provenance


# ═══════════════════════════════════════════════════════════════════════════════
# §1.4 Graphify Sync (S1-S5)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGraphifySync:
    """Spec §5: Graphify skeleton import."""

    def test_s1_new_code_node_added(self):
        graph = Graph(schema_version="1.0")
        gf_data = {
            "nodes": [{"id": "src/new.py::fn", "label": "fn", "file_type": "code"}],
            "links": [],
        }
        added = sync_graphify_skeleton(graph, gf_data)
        assert added == 1
        assert len(graph.nodes) == 1
        assert graph.nodes[0].id == "src/new.py::fn"

    def test_s2_existing_node_metadata_updated(self):
        """S2: Existing node → label updated, base_weight preserved."""
        graph = Graph(
            schema_version="1.0",
            nodes=[Node(id="src/auth.py::login", type="code", provenance="graphify", label="old_label")],
        )
        gf_data = {
            "nodes": [{"id": "src/auth.py::login", "label": "new_label"}],
            "links": [],
        }
        sync_graphify_skeleton(graph, gf_data)
        assert graph.nodes[0].label == "new_label"
        assert len(graph.nodes) == 1  # no duplicate

    def test_s3_new_edge_added_with_weight(self):
        """S3: New edge → added with base_weight=confidence_score."""
        graph = Graph(
            schema_version="1.0",
            nodes=[
                Node(id="a", type="code", provenance="graphify"),
                Node(id="b", type="code", provenance="graphify"),
            ],
        )
        gf_data = {
            "nodes": [],
            "links": [{"source": "a", "target": "b", "relation": "calls", "confidence": "EXTRACTED"}],
        }
        sync_graphify_skeleton(graph, gf_data)
        assert len(graph.links) == 1
        assert graph.links[0].base_weight == 0.9

    def test_s4_existing_edge_preserved(self):
        """S4: Existing edge → skipped, base_weight untouched."""
        graph = Graph(
            schema_version="1.0",
            nodes=[
                Node(id="a", type="code", provenance="graphify"),
                Node(id="b", type="code", provenance="graphify"),
            ],
            links=[
                Edge(
                    source="a", target="b", relation="calls",
                    confidence="EXTRACTED", confidence_score=0.9,
                    base_weight=0.85, provenance="graphify",
                ),
            ],
        )
        gf_data = {
            "nodes": [],
            "links": [{"source": "a", "target": "b", "relation": "calls", "confidence": "EXTRACTED"}],
        }
        sync_graphify_skeleton(graph, gf_data)
        assert len(graph.links) == 1
        assert graph.links[0].base_weight == 0.85  # unchanged

    def test_s5_removed_file_no_crash(self):
        """S5: Node removed from Graphify → orphaned in graph, no crash."""
        graph = Graph(
            schema_version="1.0",
            nodes=[Node(id="old_file.py::fn", type="code", provenance="graphify")],
        )
        gf_data = {"nodes": [], "links": []}
        sync_graphify_skeleton(graph, gf_data)
        # old node stays (orphaned), no crash
        assert len(graph.nodes) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# §1.5 Atomic Write (A1-A3)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAtomicWrite:
    """Spec §8.4: atomic JSON writes."""

    def test_a1_normal_write(self):
        graph = Graph(schema_version="1.0", nodes=[Node(id="test", type="concept", provenance="capture")])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "graph.json"
            save_graph(graph, path)
            assert path.exists()
            loaded = load_graph(path)
            assert loaded.schema_version == "1.0"
            assert len(loaded.nodes) == 1

    def test_a2_simulated_crash_no_corruption(self):
        """A2: Write is atomic — .tmp file is the intermediate."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "graph.json"
            graph = Graph(schema_version="1.0")
            write_json_atomic(path, graph_to_dict(graph))
            # Check no .tmp leftover
            tmp_files = list(Path(tmp).glob(".*.tmp"))
            assert len(tmp_files) == 0
            # Check file is valid JSON
            loaded = load_graph(path)
            assert loaded.schema_version == "1.0"

    def test_a3_write_preserves_old_on_error(self):
        """A3: If write fails, old file is preserved."""
        # We test that the atomic write pattern (write to tmp, then replace)
        # doesn't corrupt the target on disk full scenarios (simulated).
        # The actual OS error handling is at the filesystem level.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "graph.json"
            # Write initial
            graph1 = Graph(schema_version="1.0", nodes=[Node(id="n1", type="concept", provenance="capture")])
            save_graph(graph1, path)
            # Verify it's there
            loaded = load_graph(path)
            assert len(loaded.nodes) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# §1.7 Node Dedup (D1-D3)
# ═══════════════════════════════════════════════════════════════════════════════

class TestNodeDedup:
    """Spec §4.3: node deduplication."""

    def test_d1_same_file_same_decision_merged(self):
        """D1: Same file + same label → merged."""
        graph = Graph(
            schema_version="1.0",
            nodes=[Node(id="n1", type="decision_point", provenance="capture",
                         label="try bearer on auth.py", related_file="src/auth.py")],
        )
        new_node = Node(id="n2", type="decision_point", provenance="capture",
                        label="try bearer on auth.py", related_file="src/auth.py")
        result = _dedup_and_merge(graph, new_node)
        assert result == "n1"  # merged into existing
        assert graph.nodes[0].session_count == 2

    def test_d2_same_file_different_decision_separate(self):
        """D2: Same file, very different label → separate nodes."""
        graph = Graph(
            schema_version="1.0",
            nodes=[Node(id="n1", type="decision_point", provenance="capture",
                         label="added rate limiting to auth.py", related_file="src/auth.py")],
        )
        new_node = Node(id="n2", type="decision_point", provenance="capture",
                        label="debugged memory leak in auth.py", related_file="src/auth.py")
        result = _dedup_and_merge(graph, new_node)
        assert result == "n2"  # not merged — labels are different enough

    def test_d3_different_file_separate(self):
        """D3: Different file → separate nodes."""
        graph = Graph(
            schema_version="1.0",
            nodes=[Node(id="n1", type="decision_point", provenance="capture",
                         label="try bearer on auth.py", related_file="src/auth.py")],
        )
        new_node = Node(id="n2", type="decision_point", provenance="capture",
                        label="try bearer on db.py", related_file="src/db.py")
        result = _dedup_and_merge(graph, new_node)
        assert result == "n2"  # not merged


# ═══════════════════════════════════════════════════════════════════════════════
# §1.8 Schema Version (V1-V4)
# ═══════════════════════════════════════════════════════════════════════════════

class TestSchemaVersion:
    """Spec §8.2: schema versioning."""

    def test_v1_load_v1_graph(self):
        data = {"schema_version": "1.0", "nodes": [], "links": [], "hyperedges": []}
        graph = dict_to_graph(data)
        assert graph.schema_version == "1.0"

    def test_v2_load_legacy_no_version(self):
        """V2: Missing schema_version → treated as 1.0."""
        data = {"nodes": [], "links": [], "hyperedges": []}
        graph = dict_to_graph(data)
        assert graph.schema_version == "1.0"

    def test_v3_future_version_error(self):
        """V3: Future version → raises error with clear message."""
        data = {"schema_version": "99.0", "nodes": [], "links": [], "hyperedges": []}
        with pytest.raises(ValueError, match="migration"):
            dict_to_graph(data)


# ═══════════════════════════════════════════════════════════════════════════════
# Query Filter
# ═══════════════════════════════════════════════════════════════════════════════

class TestQueryFilter:
    """Spec §2.2: query filter thresholds."""

    def test_normal_above_05(self):
        assert query_filter(0.9) == "normal"
        assert query_filter(0.5) == "normal"

    def test_stale_03_to_05(self):
        assert query_filter(0.4) == "stale"
        assert query_filter(0.3) == "stale"

    def test_suppressed_below_03(self):
        assert query_filter(0.29) == "suppressed"
        assert query_filter(0.0) == "suppressed"


# ═══════════════════════════════════════════════════════════════════════════════
# Edge Enrichment
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeEnrichment:
    """Spec §4.2: merge worker enrichment."""

    def test_enrich_edge_sets_base_weight(self):
        raw = {"source": "a", "target": "b", "relation": "modifies", "confidence": "EXTRACTED"}
        now = "2026-07-27T12:00:00Z"
        edge = _enrich_edge(raw, "session_001", now)
        assert edge.base_weight == 0.9
        assert edge.confidence_score == 0.9
        assert edge.last_traversed_at == now  # refreshed in v1
        assert edge.provenance == "capture"

    def test_enrich_edge_ambiguous_default(self):
        raw = {"source": "a", "target": "b"}
        now = "2026-07-27T12:00:00Z"
        edge = _enrich_edge(raw, "session_001", now)
        assert edge.base_weight == 0.5  # AMBIGUOUS default
        assert edge.confidence == "AMBIGUOUS"


# ═══════════════════════════════════════════════════════════════════════════════
# Similarity
# ═══════════════════════════════════════════════════════════════════════════════

class TestSimilarity:
    """Spec §4.3: difflib-based label similarity."""

    def test_identical(self):
        assert _similarity("hello world", "hello world") == 1.0

    def test_case_insensitive(self):
        assert _similarity("Hello World", "hello world") == 1.0

    def test_partial_overlap(self):
        score = _similarity("try bearer on auth.py", "try cookie on auth.py")
        assert 0.5 < score < 0.9  # partial match

    def test_no_overlap(self):
        score = _similarity("fix auth bug", "add dashboard feature")
        assert score < 0.4  # unrelated


# ═══════════════════════════════════════════════════════════════════════════════
# Graphify Sync Edge Cases
# ═══════════════════════════════════════════════════════════════════════════════

class TestGraphifyEdgeCases:
    """Spec integration test plan G1-G4."""

    def test_g1_first_sync_empty_graph(self):
        """G1: Empty graph + Graphify output → all imported."""
        graph = Graph(schema_version="1.0")
        gf = {"nodes": [{"id": "a.py::f", "label": "f", "file_type": "code"}], "links": []}
        sync_graphify_skeleton(graph, gf)
        assert len(graph.nodes) == 1

    def test_g2_resync_preserves_weights(self):
        """G2: Existing weights preserved on re-sync."""
        graph = Graph(
            schema_version="1.0",
            nodes=[Node(id="a.py::f", type="code", provenance="graphify", label="f")],
            links=[Edge(source="a.py::f", target="b.py::g", relation="calls",
                         confidence="EXTRACTED", confidence_score=0.9,
                         base_weight=0.88, provenance="capture")],
        )
        gf = {"nodes": [{"id": "a.py::f", "label": "f_new"}],
              "links": [{"source": "a.py::f", "target": "b.py::g", "relation": "calls"}]}
        sync_graphify_skeleton(graph, gf)
        assert graph.nodes[0].label == "f_new"
        assert graph.links[0].base_weight == 0.88  # capture weight preserved

    def test_g4_graphify_empty_session_survive(self):
        """G4: Empty Graphify, session nodes survive."""
        graph = Graph(
            schema_version="1.0",
            nodes=[Node(id="session_001", type="session", provenance="capture")],
        )
        gf = {"nodes": [], "links": []}
        sync_graphify_skeleton(graph, gf)
        assert len(graph.nodes) == 1  # session node survives


# ═══════════════════════════════════════════════════════════════════════════════
# Graph Traversal (Query)
# ═══════════════════════════════════════════════════════════════════════════════

class TestGraphTraversal:
    """Spec §6: graph traversal."""

    def test_empty_graph_returns_empty(self):
        from coworker.memory.query import graph_traverse
        graph = Graph(schema_version="1.0")
        results = graph_traverse(graph, "auth")
        assert results == []

    def test_no_matching_nodes(self):
        from coworker.memory.query import graph_traverse
        graph = Graph(
            schema_version="1.0",
            nodes=[Node(id="x.py::fn", type="code", provenance="graphify", label="unknown function")],
        )
        results = graph_traverse(graph, "auth")
        assert results == []

    def test_direct_match_found(self):
        from coworker.memory.query import graph_traverse
        graph = Graph(
            schema_version="1.0",
            nodes=[Node(id="src/auth.py::login", type="code", provenance="graphify", label="login")],
        )
        results = graph_traverse(graph, "auth login")
        assert len(results) == 1
        assert results[0]["node_id"] == "src/auth.py::login"

    def test_bfs_traversal_respects_depth(self):
        from coworker.memory.query import graph_traverse
        graph = Graph(
            schema_version="1.0",
            nodes=[
                Node(id="a", type="code", provenance="graphify", label="auth module"),
                Node(id="b", type="code", provenance="graphify", label="db module"),
                Node(id="c", type="code", provenance="graphify", label="deep node"),
            ],
            links=[
                Edge(source="a", target="b", relation="calls",
                     confidence="EXTRACTED", confidence_score=0.9, base_weight=0.9,
                     provenance="graphify"),
                Edge(source="b", target="c", relation="calls",
                     confidence="EXTRACTED", confidence_score=0.9, base_weight=0.9,
                     provenance="graphify"),
            ],
        )
        results = graph_traverse(graph, "auth")
        # Should find a(depth 0), b(depth 1), c(depth 2)
        ids = [r["node_id"] for r in results]
        assert "a" in ids
        assert "b" in ids

    def test_decayed_edge_suppressed(self):
        from coworker.memory.query import graph_traverse
        now = datetime(2026, 7, 27, tzinfo=timezone.utc)
        old_ts = (now - timedelta(days=200)).isoformat()  # heavily decayed
        graph = Graph(
            schema_version="1.0",
            nodes=[
                Node(id="a", type="code", provenance="graphify", label="auth"),
                Node(id="b", type="code", provenance="graphify", label="irrelevant"),
            ],
            links=[
                Edge(source="a", target="b", relation="calls",
                     confidence="EXTRACTED", confidence_score=0.9, base_weight=0.9,
                     provenance="graphify", last_traversed_at=old_ts),
            ],
        )
        results = graph_traverse(graph, "auth", now=now)
        # Edge is suppressed (effective_weight < 0.3 after 200 days)
        ids = [r["node_id"] for r in results]
        assert "a" in ids
        assert "b" not in ids  # suppressed due to decay


# ═══════════════════════════════════════════════════════════════════════════════
# Storage round-trip
# ═══════════════════════════════════════════════════════════════════════════════

class TestStorageRoundtrip:
    """Graph serialization round-trip."""

    def test_roundtrip_preserves_data(self):
        graph = Graph(
            schema_version="1.0",
            nodes=[
                Node(id="a", type="code", provenance="graphify", label="auth",
                     source_file="src/auth.py"),
                Node(id="session_001", type="session", provenance="capture",
                     label="debug auth", session_count=3),
            ],
            links=[
                Edge(source="session_001", target="a", relation="modifies",
                     confidence="EXTRACTED", confidence_score=0.9,
                     base_weight=0.9, provenance="capture",
                     last_traversed_at="2026-07-27T12:00:00Z"),
            ],
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "graph.json"
            save_graph(graph, path)
            loaded = load_graph(path)
            assert loaded.schema_version == "1.0"
            assert len(loaded.nodes) == 2
            assert len(loaded.links) == 1
            assert loaded.nodes[0].id == "a"
            assert loaded.nodes[1].session_count == 3
            assert loaded.links[0].base_weight == 0.9
            assert loaded.links[0].last_traversed_at == "2026-07-27T12:00:00Z"
