"""Test memory query quality — min_score filtering, token budget, decay suppression.

Tests cover:
  - min_score filtering for vector results
  - Token budget cutting
  - Graph BFS with decay suppression
  - Source tagging
  - Both mode result formatting
  - MCP server query functions
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from coworker.memory.query import (
    query,
    graph_traverse,
    _cut_by_budget,
    _simple_seeds,
    _bfs_from_seeds,
    MAX_DEPTH,
    MAX_SEEDS,
    _EDGE_SUPPRESS_THRESHOLD,
)
from coworker.memory.graph import Graph, Node, Edge
from coworker.memory.decay import compute_effective_weight, query_filter


# ── Fixtures ─────────────────────────────────────────────────────────────────


def _make_test_graph(n_nodes: int = 10) -> Graph:
    """Create a simple test graph with a chain of nodes."""
    nodes = []
    edges = []
    for i in range(n_nodes):
        nodes.append(Node(
            id=f"node_{i}",
            type="code",
            provenance="graphify",
            label=f"Test Node {i}",
            source_file=f"src/test_{i}.py",
        ))
        if i > 0:
            edges.append(Edge(
                source=f"node_{i-1}",
                target=f"node_{i}",
                relation="calls",
                confidence="EXTRACTED",
                confidence_score=0.9,
                base_weight=0.9,
                provenance="graphify",
            ))
    return Graph(nodes=nodes, links=edges)


def _make_mock_mem0(results: list[dict]) -> MagicMock:
    """Create a mock Mem0Client that returns given results."""
    mock = MagicMock()
    mock.search.return_value = results
    return mock


# ── Test: _cut_by_budget ─────────────────────────────────────────────────────


class TestCutByBudget:
    def test_empty_list(self):
        assert _cut_by_budget([], 100) == []

    def test_single_item_fits(self):
        items = [{"label": "short label"}]
        result = _cut_by_budget(items, 50)
        assert len(result) == 1

    def test_budget_zero_returns_nothing(self):
        items = [{"label": "any text"}]
        result = _cut_by_budget(items, 0)
        assert len(result) == 0

    def test_cuts_at_budget_boundary(self):
        # Each item costs len(label) + 50 chars
        # budget=50 → char_budget=150
        # item1: len("hello") + 50 = 55 → fits (55 < 150)
        # item2: 55 + 55 = 110 → fits (110 < 150)
        # item3: 110 + 55 = 165 → DOES NOT fit (165 > 150)
        items = [{"label": "hello"}, {"label": "world"}, {"label": "extra"}]
        result = _cut_by_budget(items, 50)
        assert len(result) == 2
        assert result[0]["label"] == "hello"
        assert result[1]["label"] == "world"

    def test_uses_memory_field_for_vector_results(self):
        items = [{"memory": "a" * 100}]
        result = _cut_by_budget(items, 50)
        # len("a"*100) + 50 = 150 → char_budget = 50*3 = 150 → fits
        assert len(result) == 1

    def test_large_budget_returns_all(self):
        items = [{"label": f"item_{i}"} for i in range(20)]
        result = _cut_by_budget(items, 10000)
        assert len(result) == 20


# ── Test: min_score filtering in query() ─────────────────────────────────────


class TestMinScoreFiltering:
    """Test that min_score filters vector results in query()."""

    def test_min_score_default_keeps_high_scores(self):
        graph = _make_test_graph(3)
        mem0 = _make_mock_mem0([
            {"memory": "Relevant skill update convention", "score": 0.85, "metadata": {"type": "convention"}},
            {"memory": "Somewhat related pattern", "score": 0.45, "metadata": {"type": "pattern"}},
            {"memory": "Low relevance noise", "score": 0.15, "metadata": {"type": "misc"}},
        ])

        result = query(graph, "skill update", mode="vector", mem0_client=mem0, min_score=0.3)
        # default min_score=0.3: keeps 0.85 and 0.45, drops 0.15
        assert result["stats"]["vector_hits"] == 2
        scores = [r["score"] for r in result["results"]]
        assert all(s >= 0.3 for s in scores)
        assert 0.15 not in scores

    def test_min_score_strict_filters_more(self):
        graph = _make_test_graph(3)
        mem0 = _make_mock_mem0([
            {"memory": "High quality skill convention", "score": 0.87},
            {"memory": "Medium relevance", "score": 0.55},
            {"memory": "Medium-low", "score": 0.40},
        ])

        result = query(graph, "skill update", mode="vector", mem0_client=mem0, min_score=0.6)
        assert result["stats"]["vector_hits"] == 1
        assert result["results"][0]["score"] == 0.87

    def test_min_score_zero_keeps_all(self):
        graph = _make_test_graph(3)
        mem0 = _make_mock_mem0([
            {"memory": "A", "score": 0.9},
            {"memory": "B", "score": 0.1},
        ])
        result = query(graph, "test", mode="vector", mem0_client=mem0, min_score=0.0)
        assert result["stats"]["vector_hits"] == 2

    def test_min_score_one_keeps_none(self):
        graph = _make_test_graph(3)
        mem0 = _make_mock_mem0([
            {"memory": "A", "score": 0.9},
            {"memory": "B", "score": 0.8},
        ])
        result = query(graph, "test", mode="vector", mem0_client=mem0, min_score=1.0)
        assert result["stats"]["vector_hits"] == 0


# ── Test: Token budget in query() ─────────────────────────────────────────────


class TestTokenBudget:
    """Test that token budget controls result count in query()."""

    def test_budget_cuts_graph_results(self):
        """Budget should cut graph results after graph_traverse returns them."""
        graph = _make_test_graph(20)
        # Mock graph_traverse to return 10 results, budget should cut to fewer
        many_results = [
            {
                "node_id": f"n{i}", "label": f"Node_{i}_with_a_long_label_for_budget",
                "type": "code", "provenance": "graphify",
                "depth": 0, "path_weight": 1.0, "flags": [], "source_file": f"src/test_{i}.py",
            }
            for i in range(10)
        ]
        with patch("coworker.memory.query.graph_traverse", return_value=many_results):
            result = query(graph, "test", mode="graph", budget=200)
            # With budget=200 → char_budget=600, each result costs len(label)+50 ≈ 90
            # So ~6 results expected
            assert len(result["results"]) < len(many_results)
            assert len(result["results"]) >= 1

    def test_budget_none_uses_top_k_exactly(self):
        graph = _make_test_graph(20)
        mem0 = _make_mock_mem0([
            {"memory": f"Memory {i}", "score": 0.8} for i in range(15)
        ])

        result = query(graph, "test", mode="vector", mem0_client=mem0, top_k=5, budget=None)
        # budget=None → use top_k=5 → exactly 5 results
        assert len(result["results"]) == 5

    def test_budget_and_min_score_together(self):
        """Budget + min_score combined: min_score filters first, then budget cuts."""
        graph = _make_test_graph(3)
        mem0 = _make_mock_mem0([
            {"memory": "High quality A", "score": 0.9},
            {"memory": "High quality B", "score": 0.85},
            {"memory": "Low quality", "score": 0.2},
        ])
        result = query(graph, "test", mode="vector", mem0_client=mem0,
                       min_score=0.5, budget=50)
        # min_score=0.5 → drops 0.2, keeps 0.9 + 0.85
        # budget=50 → char_budget=150 → each item costs len("High quality X")+50 ≈ 64
        # 64 < 150, 128 < 150, 192 > 150 → 2 items
        assert result["stats"]["vector_hits"] == 2
        scores = [r["score"] for r in result["results"]]
        assert 0.2 not in scores
        assert all(s >= 0.5 for s in scores)

    def test_min_score_passed_to_mem0_client(self):
        """Verify query() passes min_score to mem0_client.search()."""
        graph = _make_test_graph(3)
        mem0 = MagicMock()
        mem0.search.return_value = []

        query(graph, "test", mode="vector", mem0_client=mem0, min_score=0.7)
        mem0.search.assert_called_once()
        call_kwargs = mem0.search.call_args.kwargs
        assert call_kwargs["min_score"] == 0.7

    def test_mem0_failure_graceful_degradation(self):
        """When mem0 throws, query() should return empty vector results, not crash."""
        graph = _make_test_graph(3)
        mem0 = MagicMock()
        mem0.search.side_effect = RuntimeError("mem0 connection refused")

        result = query(graph, "test", mode="vector", mem0_client=mem0)
        assert result["stats"]["vector_hits"] == 0
        assert result["results"] == []


# ── Test: Source tagging ─────────────────────────────────────────────────────


class TestSourceTagging:
    """Test that results are tagged with correct source."""

    def test_graph_results_tagged(self):
        nodes = [Node(id="n0", type="code", provenance="graphify", label="test")]
        graph = Graph(nodes=nodes, links=[])

        # Mock graph_traverse to return a known result
        with patch("coworker.memory.query.graph_traverse") as mock_gt:
            mock_gt.return_value = [{
                "node_id": "n0", "label": "test", "type": "code",
                "provenance": "graphify", "depth": 0, "path_weight": 1.0,
                "flags": [], "source_file": "test.py",
            }]
            result = query(graph, "test", mode="graph")
            for r in result["results"]:
                assert r["source"] == "graph"

    def test_vector_results_tagged(self):
        graph = _make_test_graph(3)
        mem0 = _make_mock_mem0([
            {"memory": "test memory", "score": 0.75, "metadata": {"type": "pattern"}},
        ])

        result = query(graph, "test", mode="vector", mem0_client=mem0)
        for r in result["results"]:
            assert r["source"] == "vector"

    def test_both_mode_has_both_sources(self):
        nodes = [Node(id="n0", type="code", provenance="graphify", label="test code")]
        graph = Graph(nodes=nodes, links=[])
        mem0 = _make_mock_mem0([
            {"memory": "test memory", "score": 0.8, "metadata": {"type": "pattern"}},
        ])

        with patch("coworker.memory.query.graph_traverse") as mock_gt:
            mock_gt.return_value = [{
                "node_id": "n0", "label": "test code", "type": "code",
                "provenance": "graphify", "depth": 0, "path_weight": 1.0,
                "flags": [], "source_file": "test.py",
            }]
            result = query(graph, "test", mode="both", mem0_client=mem0)
            sources = {r["source"] for r in result["results"]}
            assert sources == {"graph", "vector"}


# ── Test: _simple_seeds (bug fix verification) ────────────────────────────────


class TestSimpleSeeds:
    """Verify the _MAX_SEEDS → MAX_SEEDS bug fix."""

    def test_does_not_crash(self):
        import networkx as nx
        G = nx.Graph()
        G.add_node("test_node", label="test dashboard bug fix")
        seeds = _simple_seeds(G, "how to fix dashboard")
        assert isinstance(seeds, list)

    def test_matches_keywords(self):
        import networkx as nx
        G = nx.Graph()
        G.add_node("n1", label="skill update convention")
        G.add_node("n2", label="project setup guide")
        G.add_node("n3", label="unrelated")
        seeds = _simple_seeds(G, "update skill")
        assert "n1" in seeds

    def test_respects_max_seeds(self):
        import networkx as nx
        G = nx.Graph()
        for i in range(20):
            G.add_node(f"n{i}", label=f"skill update pattern {i}")
        seeds = _simple_seeds(G, "skill update")
        assert len(seeds) <= MAX_SEEDS


# ── Test: BFS decay suppression ───────────────────────────────────────────────


class TestBFSDecaySuppression:
    """Test that BFS skips edges with effective_weight < SUPPRESS_THRESHOLD."""

    def test_normal_edges_traversed(self):
        nodes = [
            Node(id="n0", type="code", provenance="graphify", label="Start"),
            Node(id="n1", type="code", provenance="graphify", label="Reachable"),
        ]
        edges = [
            Edge(source="n0", target="n1", relation="calls", confidence="EXTRACTED",
                 confidence_score=0.9, base_weight=0.9, provenance="graphify"),
        ]
        graph = Graph(nodes=nodes, links=edges)
        results = _bfs_from_seeds(graph, ["n0"], top_k=10)
        node_ids = {r["node_id"] for r in results}
        assert "n1" in node_ids  # edge weight 0.9 > 0.3 → traversed

    def test_suppressed_edges_skipped(self):
        """Edge with base_weight < 0.3 should be skipped (never traversed = no decay)."""
        nodes = [
            Node(id="n0", type="code", provenance="graphify", label="Start"),
            Node(id="n1", type="code", provenance="graphify", label="Unreachable"),
        ]
        edges = [
            Edge(source="n0", target="n1", relation="calls", confidence="WEAK",
                 confidence_score=0.2, base_weight=0.2, provenance="graphify"),
        ]
        graph = Graph(nodes=nodes, links=edges)
        results = _bfs_from_seeds(graph, ["n0"], top_k=10)
        node_ids = {r["node_id"] for r in results}
        assert "n1" not in node_ids  # base_weight 0.2 < 0.3 → skipped


# ── Test: query() preserves actual mem0 scores ────────────────────────────────


class TestVectorScorePreservation:
    """Verify vector mode preserves actual mem0 scores (not hardcoded 1.0)."""

    def test_vector_mode_preserves_scores(self):
        graph = _make_test_graph(3)
        mem0 = _make_mock_mem0([
            {"memory": "A", "score": 0.72, "metadata": {}},
            {"memory": "B", "score": 0.55, "metadata": {}},
        ])
        result = query(graph, "test", mode="vector", mem0_client=mem0)
        scores = [r["score"] for r in result["results"]]
        assert scores == [0.72, 0.55]

    def test_both_mode_preserves_scores(self):
        graph = _make_test_graph(3)
        mem0 = _make_mock_mem0([
            {"memory": "A", "score": 0.68, "metadata": {}},
        ])
        with patch("coworker.memory.query.graph_traverse") as mock_gt:
            mock_gt.return_value = [{
                "node_id": "n0", "label": "graph item", "type": "code",
                "provenance": "graphify", "depth": 0, "path_weight": 1.0,
                "flags": [], "source_file": "test.py",
            }]
            result = query(graph, "test", mode="both", mem0_client=mem0)
            vector_scores = [r["score"] for r in result["results"] if r["source"] == "vector"]
            assert vector_scores == [0.68]


# ── Test: graph_traverse empty/edge cases ─────────────────────────────────────


class TestGraphTraverseEdgeCases:
    def test_empty_question_returns_empty(self):
        graph = _make_test_graph(5)
        assert graph_traverse(graph, "") == []
        assert graph_traverse(graph, "   ") == []

    def test_no_seeds_returns_empty(self):
        with patch("coworker.memory.query._graphify_seeds", return_value=[]):
            result = graph_traverse(_make_test_graph(5), "xyzabc123_nonexistent")
            assert result == []


# ── Test: query() stats accuracy ──────────────────────────────────────────────


class TestQueryStats:
    def test_stats_reflect_filtered_results(self):
        graph = _make_test_graph(3)
        mem0 = _make_mock_mem0([
            {"memory": "Good", "score": 0.8},
            {"memory": "Bad", "score": 0.1},
        ])
        result = query(graph, "test", mode="vector", mem0_client=mem0, min_score=0.3)
        # mem0 returns 2, but min_score=0.3 filters out score=0.1
        # Actually: mem0_client.search returns 2, then query() filters to 1
        # But the stats count "vector_hits" from the raw mem0 result (2)
        # Wait - in the new query(), vector_hits is len(results_vector) AFTER filtering
        assert result["stats"]["vector_hits"] == 1
        assert result["stats"]["total_returned"] == 1
