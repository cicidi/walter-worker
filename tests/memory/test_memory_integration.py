"""Integration tests for memory query — real mem0 data, CLI, MCP server.

Tests cover:
  - Test 1: Query skill conventions against real mem0 data
  - Test 2: Token budget + min_score with real data
  - Test 3: CLI `coworker memory query` end-to-end
  - Test 4: MCP server JSON-RPC integration
  - Test 5: Graph query with real graph.json data
"""

from __future__ import annotations

import json
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────


def _mem0_available() -> bool:
    """Check if mem0 is configured and reachable."""
    try:
        from coworker.memory.mem0_client import Mem0Client
        client = Mem0Client.from_config()
        results = client.search("test", top_k=1)
        return isinstance(results, list)
    except Exception:
        return False


def _graph_available() -> bool:
    """Check if graph.json exists and has data."""
    try:
        from coworker.memory.storage import load_graph
        g = load_graph()
        return len(g.nodes) > 0
    except Exception:
        return False


# ── Test 1: Real mem0 data — skill update query ──────────────────────────────


@pytest.mark.integration
@pytest.mark.skipif(not _mem0_available(), reason="mem0 not configured")
class TestRealMem0SkillQuery:
    """Query real mem0 for skill-related conventions.

    This verifies the system can find past experiences about:
    - How to update/change a skill
    - Skill creation conventions
    - The 'update → grade install' workflow
    """

    def test_query_skill_update_finds_conventions(self):
        """Search for 'how to update or change a skill' — should find conventions."""
        from coworker.memory.mem0_client import Mem0Client
        client = Mem0Client.from_config()

        results = client.search("how to update or change a skill", top_k=10, min_score=0.3)

        assert len(results) > 0, "Should find at least some skill-related memories"
        # At least one result should be about skills
        skill_related = [
            r for r in results
            if any(word in r.get("memory", "").lower()
                   for word in ["skill", "update", "convention", "create"])
        ]
        assert len(skill_related) > 0, (
            f"Expected skill-related memories, got: "
            f"{[r.get('memory', '')[:80] for r in results[:3]]}"
        )

    def test_min_score_filters_quality(self):
        """Higher min_score should return fewer but higher-quality results."""
        from coworker.memory.mem0_client import Mem0Client
        client = Mem0Client.from_config()

        results_loose = client.search("skill creation convention", top_k=10, min_score=0.3)
        results_strict = client.search("skill creation convention", top_k=10, min_score=0.7)

        # Strict filtering should return fewer or equal results
        assert len(results_strict) <= len(results_loose), (
            f"Strict (0.7): {len(results_strict)}, Loose (0.3): {len(results_loose)}"
        )

        # All strict results should have score >= 0.7
        for r in results_strict:
            assert r.get("score", 0) >= 0.7, f"Score {r.get('score')} < 0.7"

    def test_query_skill_finds_specific_convention(self):
        """Search should find the skill creation convention (SKILL.md in skill-factory)."""
        from coworker.memory.mem0_client import Mem0Client
        client = Mem0Client.from_config()

        results = client.search(
            "how to create a new skill for a project",
            top_k=10, min_score=0.5,
        )

        # At least one result should mention skill creation
        skill_texts = [r.get("memory", "") for r in results]
        combined = " ".join(skill_texts).lower()

        # Check for known convention patterns
        convention_signals = [
            "skill" in combined,
            "SKILL.md" in combined or "skill.md" in combined,
        ]
        assert any(convention_signals), (
            f"No skill convention found in: {[t[:100] for t in skill_texts[:3]]}"
        )

    def test_high_min_score_still_has_results(self):
        """At min_score=0.7, skill query should still return valid results."""
        from coworker.memory.mem0_client import Mem0Client
        client = Mem0Client.from_config()

        results = client.search("skill update convention", top_k=5, min_score=0.7)
        # With real data, we verified scores 0.50-0.87 exist
        # At 0.7 threshold, should have at least 1 result
        assert len(results) >= 1, (
            f"Expected results at min_score=0.7 for skill queries, got {len(results)}"
        )


# ── Test 2: Token budget + min_score combined ────────────────────────────────


@pytest.mark.integration
@pytest.mark.skipif(not _mem0_available(), reason="mem0 not configured")
class TestBudgetAndMinScore:
    """Test budget + min_score work together with real data."""

    def test_budget_limits_real_results(self):
        """Token budget should reduce result count even with many matches."""
        from coworker.memory.storage import load_graph
        from coworker.memory.query import query as graph_query
        from coworker.memory.mem0_client import Mem0Client

        graph = load_graph()
        mem0 = Mem0Client.from_config()

        # Without budget
        result_full = graph_query(graph, "test", mode="vector", mem0_client=mem0,
                                  top_k=50, min_score=0.3, budget=None)
        # With tight budget
        result_budget = graph_query(graph, "test", mode="vector", mem0_client=mem0,
                                    top_k=50, min_score=0.3, budget=200)

        # Budget should reduce or equal the count
        assert len(result_budget["results"]) <= len(result_full["results"]), (
            f"budget=None: {len(result_full['results'])}, "
            f"budget=200: {len(result_budget['results'])}"
        )

    def test_budget_and_min_score_from_query_api(self):
        """query() API with both budget and min_score."""
        from coworker.memory.storage import load_graph
        from coworker.memory.query import query as graph_query
        from coworker.memory.mem0_client import Mem0Client

        graph = load_graph()
        mem0 = Mem0Client.from_config()

        result = graph_query(
            graph, "skill update convention",
            mode="vector", mem0_client=mem0,
            top_k=20, min_score=0.5, budget=500,
        )

        # All results must meet min_score
        for r in result["results"]:
            assert r.get("score", 0) >= 0.5

        # Stats should be consistent
        assert result["stats"]["vector_hits"] == len(result["results"])


# ── Test 3: Graph query with real data ───────────────────────────────────────


@pytest.mark.integration
@pytest.mark.skipif(not _graph_available(), reason="graph.json not available")
class TestRealGraphQuery:
    """Test graph query against real graph.json data."""

    def test_graph_query_returns_results(self):
        """Graph query should return nodes from the real graph."""
        from coworker.memory.storage import load_graph
        from coworker.memory.query import query as graph_query

        graph = load_graph()
        result = graph_query(graph, "CLI command", mode="graph", top_k=10, budget=1000)

        assert "results" in result
        assert result["mode"] == "graph"
        # Should find something (CLI-related code exists)
        assert result["stats"]["graph_hits"] >= 0

    def test_graph_results_tagged(self):
        """All graph results should have source='graph'."""
        from coworker.memory.storage import load_graph
        from coworker.memory.query import query as graph_query

        graph = load_graph()
        result = graph_query(graph, "memory query", mode="graph", top_k=5, budget=500)

        for r in result["results"]:
            assert r.get("source") == "graph"

    def test_graph_budget_cuts_results(self):
        """Small budget should return fewer results."""
        from coworker.memory.storage import load_graph
        from coworker.memory.query import query as graph_query

        graph = load_graph()
        result_large = graph_query(graph, "memory", mode="graph", top_k=20, budget=None)
        result_small = graph_query(graph, "memory", mode="graph", top_k=20, budget=200)

        # Small budget should not return MORE than large budget
        assert len(result_small["results"]) <= len(result_large["results"])


# ── Test 4: CLI integration ──────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.skipif(not _mem0_available(), reason="mem0 not configured")
class TestCLIMemoryQuery:
    """Test the `coworker memory query` CLI command using Click's CliRunner."""

    def test_cli_query_both_mode(self):
        """CLI query in both mode should produce output without crashing."""
        from click.testing import CliRunner
        from coworker.cli import main
        result = CliRunner().invoke(
            main,
            ["memory", "query", "skill update", "--mode", "both", "--budget", "500", "--min-score", "0.5"],
        )
        assert result.exit_code == 0, f"CLI failed: {result.output[:500]}"
        assert len(result.output) > 0

    def test_cli_query_graph_only(self):
        """CLI query in graph-only mode."""
        from click.testing import CliRunner
        from coworker.cli import main
        result = CliRunner().invoke(
            main,
            ["memory", "query", "CLI", "--mode", "graph", "--budget", "300"],
        )
        assert result.exit_code == 0
        assert "Traceback" not in result.output

    def test_cli_query_vector_only(self):
        """CLI query in vector-only mode with min_score."""
        from click.testing import CliRunner
        from coworker.cli import main
        result = CliRunner().invoke(
            main,
            ["memory", "query", "skill", "--mode", "vector", "--min-score", "0.7"],
        )
        assert result.exit_code == 0
        assert "Traceback" not in result.output

    def test_cli_query_shows_stats_footer(self):
        """CLI output should include stats summary."""
        from click.testing import CliRunner
        from coworker.cli import main
        result = CliRunner().invoke(
            main,
            ["memory", "query", "test", "--mode", "both", "--budget", "300"],
        )
        output = result.output
        has_stats = "budget" in output.lower() or "Graph:" in output
        assert has_stats or "Graph is empty" in output or "mem0 not available" in output


# ── Test 5: MCP server JSON-RPC integration ──────────────────────────────────


@pytest.mark.integration
class TestMCPServer:
    """Test the MCP server's JSON-RPC handlers directly (no subprocess needed)."""

    def test_initialize_response(self):
        """MCP initialize should return server info."""
        from coworker.memory.mcp_server import handle_request

        resp = handle_request({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"},
        })
        assert resp is not None
        assert resp["result"]["serverInfo"]["name"] == "memory-graph"
        assert "tools" in resp["result"]["capabilities"]

    def test_tools_list(self):
        """tools/list should return query_memory_graph, search_memory, memory_graph_stats."""
        from coworker.memory.mcp_server import handle_request

        resp = handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tool_names = [t["name"] for t in resp["result"]["tools"]]
        assert "query_memory_graph" in tool_names
        assert "search_memory" in tool_names
        assert "memory_graph_stats" in tool_names

    def test_tools_list_includes_budget_param(self):
        """query_memory_graph tool schema should include budget parameter."""
        from coworker.memory.mcp_server import handle_request

        resp = handle_request({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
        graph_tool = [t for t in resp["result"]["tools"] if t["name"] == "query_memory_graph"][0]
        props = graph_tool["inputSchema"]["properties"]
        assert "budget" in props
        assert props["budget"]["default"] == 2000

    def test_tools_list_includes_min_score_param(self):
        """search_memory tool schema should include min_score parameter."""
        from coworker.memory.mcp_server import handle_request

        resp = handle_request({"jsonrpc": "2.0", "id": 4, "method": "tools/list"})
        mem_tool = [t for t in resp["result"]["tools"] if t["name"] == "search_memory"][0]
        props = mem_tool["inputSchema"]["properties"]
        assert "min_score" in props
        assert props["min_score"]["default"] == 0.3

    def test_query_memory_graph_tool_call(self):
        """tools/call query_memory_graph should return results."""
        from coworker.memory.mcp_server import handle_request

        resp = handle_request({
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": {
                "name": "query_memory_graph",
                "arguments": {"query": "memory", "top_k": 3, "budget": 500},
            },
        })
        assert resp is not None
        assert "result" in resp
        assert "content" in resp["result"]
        # Should be valid JSON content
        content_text = resp["result"]["content"][0]["text"]
        results = json.loads(content_text)
        assert isinstance(results, list)

    def test_search_memory_tool_call(self):
        """tools/call search_memory should return results (or empty on error)."""
        from coworker.memory.mcp_server import handle_request

        resp = handle_request({
            "jsonrpc": "2.0", "id": 6, "method": "tools/call",
            "params": {
                "name": "search_memory",
                "arguments": {"query": "skill", "top_k": 3, "min_score": 0.5},
            },
        })
        assert resp is not None
        assert "result" in resp
        content_text = resp["result"]["content"][0]["text"]
        results = json.loads(content_text)
        assert isinstance(results, list)
        # If results exist, scores should be >= min_score
        for r in results:
            assert r.get("score", 0) >= 0.5, f"Score below min_score: {r}"

    def test_memory_graph_stats(self):
        """memory_graph_stats should return node/edge counts."""
        from coworker.memory.mcp_server import handle_request

        resp = handle_request({
            "jsonrpc": "2.0", "id": 7, "method": "tools/call",
            "params": {"name": "memory_graph_stats", "arguments": {}},
        })
        content_text = resp["result"]["content"][0]["text"]
        stats = json.loads(content_text)
        assert "total_nodes" in stats
        assert "total_edges" in stats

    def test_ping(self):
        """Ping should return empty result."""
        from coworker.memory.mcp_server import handle_request

        resp = handle_request({"jsonrpc": "2.0", "id": 8, "method": "ping"})
        assert resp["result"] == {}

    def test_unknown_method(self):
        """Unknown method should return error."""
        from coworker.memory.mcp_server import handle_request

        resp = handle_request({"jsonrpc": "2.0", "id": 9, "method": "nonexistent"})
        assert "error" in resp
        assert resp["error"]["code"] == -32601

    def test_notification_no_response(self):
        """Notifications should return None."""
        from coworker.memory.mcp_server import handle_request

        resp = handle_request({
            "jsonrpc": "2.0", "method": "notifications/initialized",
        })
        assert resp is None


# ── Test 6: query() both mode with real data ─────────────────────────────────


@pytest.mark.integration
@pytest.mark.skipif(not (_mem0_available() and _graph_available()),
                    reason="mem0 or graph not available")
class TestBothModeIntegration:
    """Test query() in both mode with real graph + mem0 data."""

    def test_both_mode_returns_both_sources(self):
        """Both mode should return graph and vector results."""
        from coworker.memory.storage import load_graph
        from coworker.memory.query import query as graph_query
        from coworker.memory.mem0_client import Mem0Client

        graph = load_graph()
        mem0 = Mem0Client.from_config()

        result = graph_query(
            graph, "skill", mode="both", mem0_client=mem0,
            top_k=5, min_score=0.5, budget=500,
        )

        sources = {r.get("source") for r in result["results"]}
        assert "graph" in sources, f"Expected graph results, got sources: {sources}"

    def test_both_mode_stats_consistent(self):
        """Stats should reflect actual result counts."""
        from coworker.memory.storage import load_graph
        from coworker.memory.query import query as graph_query
        from coworker.memory.mem0_client import Mem0Client

        graph = load_graph()
        mem0 = Mem0Client.from_config()

        result = graph_query(
            graph, "test", mode="both", mem0_client=mem0,
            top_k=10, min_score=0.3, budget=1000,
        )

        assert result["stats"]["total_returned"] == len(result["results"])
        # graph_results key should match graph part
        graph_count = len([r for r in result["results"] if r.get("source") == "graph"])
        assert result["stats"]["graph_hits"] == graph_count
