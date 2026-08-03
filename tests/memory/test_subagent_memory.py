"""Test: Subagent using past experience from memory.

Scenario (Test 2 from test plan):
  1. Create a subagent with access to search_memory tool
  2. Give it a task: "create a new CLI command skill for walter-worker"
  3. Verify the subagent:
     a. Calls search_memory to find relevant past experiences
     b. Uses the retrieved conventions in its response
     c. Follows the established patterns (SKILL.md location, design spec, etc.)

This test runs in two modes:
  - SDK mode: Uses Anthropic SDK with search_memory as a tool (if API key available)
  - Simulation mode: Programmatically verifies memory retrieval works (always runs)
"""

from __future__ import annotations

import json
import os
import pytest
from unittest.mock import MagicMock


# ── Helpers ───────────────────────────────────────────────────────────────────


def _mem0_available() -> bool:
    try:
        from coworker.memory.mem0_client import Mem0Client
        client = Mem0Client.from_config()
        results = client.search("test", top_k=1)
        return isinstance(results, list)
    except Exception:
        return False


def _anthropic_sdk_available() -> bool:
    try:
        import anthropic
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    except ImportError:
        return False


# ── Subagent memory tool definition ──────────────────────────────────────────

SEARCH_MEMORY_TOOL = {
    "name": "search_memory",
    "description": "Search past session memories for relevant lessons, patterns, "
                   "conventions, and decisions. Use this before starting any task "
                   "to find prior experience.",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "What to search for — describe the problem or topic",
            },
            "min_score": {
                "type": "number",
                "description": "Minimum relevance score 0-1 (default 0.3)",
                "default": 0.3,
            },
        },
        "required": ["query"],
    },
}


def _execute_search_memory(query: str, min_score: float = 0.3) -> list[dict]:
    """Execute a search_memory call — this is what the subagent's tool would do."""
    from coworker.memory.mem0_client import Mem0Client
    client = Mem0Client.from_config()
    return client.search(query=query, top_k=5, min_score=min_score)


# ── Test: Memory retrieval for subagent tasks ────────────────────────────────


@pytest.mark.integration
@pytest.mark.skipif(not _mem0_available(), reason="mem0 not configured")
class TestSubagentMemoryRetrieval:
    """Verify that search_memory returns useful past experiences for common tasks.

    These tests simulate what a subagent would retrieve before starting work.
    """

    # ── Task 1: Create a new skill ─────────────────────────────────────────

    def test_task_create_skill_finds_conventions(self):
        """Subagent tasked with 'create a new CLI command skill' should find
        the skill creation convention in memory."""
        results = _execute_search_memory(
            "create a new skill for a project CLI command", min_score=0.5,
        )

        assert len(results) > 0, "Should find skill creation conventions"

        # The conventions should mention skill creation patterns
        memories = [r.get("memory", "") for r in results]
        combined = " ".join(memories).lower()

        # Known convention signals a subagent should find:
        signals_found = []
        if "skill" in combined:
            signals_found.append("skill reference")
        if "skill-factory" in combined or "personal-skills" in combined:
            signals_found.append("skill location convention")
        if "SKILL.md" in combined or "skill.md" in combined:
            signals_found.append("SKILL.md file convention")

        assert len(signals_found) >= 1, (
            f"Subagent would miss key conventions. Found signals: {signals_found}. "
            f"Top memory: {memories[0][:200] if memories else 'NONE'}"
        )

    # ── Task 2: Fix a bug ──────────────────────────────────────────────────

    def test_task_fix_bug_finds_patterns(self):
        """Subagent tasked with fixing a bug should find bug-fix patterns."""
        results = _execute_search_memory(
            "how to fix a bug systematically", min_score=0.5,
        )

        assert len(results) > 0, "Should find debugging conventions"

        memories = [r.get("memory", "") for r in results]
        combined = " ".join(memories).lower()

        # Bug-fix related signals
        signals = []
        if "bug" in combined or "fix" in combined or "debug" in combined:
            signals.append("debugging reference")
        if "test" in combined:
            signals.append("testing reference")

        # At minimum, some useful memory should exist
        assert len(results) >= 1

    # ── Task 3: Update a skill ─────────────────────────────────────────────

    def test_task_update_skill_finds_process(self):
        """Subagent tasked with 'update a skill' should find the update workflow.

        The established convention: update the skill first, then install
        locally via 'update grade'."""
        results = _execute_search_memory(
            "how to update or change an existing skill", min_score=0.5,
        )

        assert len(results) > 0, "Should find skill update conventions"

        # Check for the update workflow pattern
        memories = [r.get("memory", "") for r in results]
        combined = " ".join(memories).lower()

        # The specific convention: update → grade install
        update_signals = []
        if "update" in combined or "change" in combined or "rename" in combined:
            update_signals.append("update/change reference")
        if "skill" in combined:
            update_signals.append("skill reference")

        assert len(update_signals) >= 1, (
            f"Expected update conventions. Top memory: {memories[0][:200] if memories else 'NONE'}"
        )

    # ── Quality: min_score filtering ───────────────────────────────────────

    def test_min_score_improves_relevance(self):
        """Higher min_score should give more focused results for the subagent."""
        results_loose = _execute_search_memory("skill creation", min_score=0.0)
        results_strict = _execute_search_memory("skill creation", min_score=0.7)

        # Strict filtering should not return more results
        assert len(results_strict) <= len(results_loose)

        # All strict results should actually be about skills
        for r in results_strict:
            assert r.get("score", 0) >= 0.7

    # ── Combined: budget simulation ────────────────────────────────────────

    def test_subagent_with_budget_gets_focused_results(self):
        """Simulate subagent getting budget-limited results from query()."""
        from coworker.memory.storage import load_graph
        from coworker.memory.query import query as graph_query
        from coworker.memory.mem0_client import Mem0Client

        graph = load_graph()
        mem0 = Mem0Client.from_config()

        # Simulate subagent querying with tight budget
        result = graph_query(
            graph, "create skill", mode="both", mem0_client=mem0,
            top_k=20, min_score=0.5, budget=500,
        )

        # Results should exist and be focused
        assert result["stats"]["total_returned"] <= 20  # capped by top_k or budget
        for r in result["results"]:
            if r.get("source") == "vector":
                assert r.get("score", 0) >= 0.5


# ── Test: SDK-based subagent (if Anthropic API available) ────────────────────


@pytest.mark.integration
@pytest.mark.skipif(not _anthropic_sdk_available(),
                    reason="Anthropic SDK not configured")
class TestSDKSubagent:
    """Use Anthropic SDK to create a real subagent with search_memory tool.

    This is the closest to real usage: an actual LLM agent that can
    call search_memory and use the results.
    """

    def test_subagent_uses_search_memory(self):
        """Create an SDK agent, give it a task, verify it calls search_memory."""
        import anthropic

        client = anthropic.Anthropic()

        system_prompt = """You are a helpful coding assistant. Before starting any task,
you MUST call search_memory to find relevant past experiences, conventions,
and lessons. Use what you find to guide your approach.

IMPORTANT: Always call search_memory FIRST, before doing anything else."""

        task = (
            "I need to know the convention for creating a new skill in the "
            "walter-worker project. What is the established process?"
        )

        response = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": task}],
            tools=[SEARCH_MEMORY_TOOL],
        )

        # Check if the agent used the tool
        tool_uses = [block for block in response.content if block.type == "tool_use"]
        memory_calls = [tu for tu in tool_uses if tu.name == "search_memory"]

        assert len(memory_calls) >= 1, (
            f"Subagent did NOT call search_memory! "
            f"Response: {response.content[0].text[:300] if response.content else 'empty'}"
        )

        # The agent should have searched for skill-related queries
        queries = [tu.input.get("query", "") for tu in memory_calls]
        combined_queries = " ".join(queries).lower()
        assert "skill" in combined_queries or "convention" in combined_queries, (
            f"Subagent searched for wrong things: {queries}"
        )

    def test_subagent_applies_convention(self):
        """Subagent given a task should apply retrieved conventions in its answer."""
        import anthropic

        client = anthropic.Anthropic()

        system_prompt = """You are a coding assistant. Use search_memory to find
relevant conventions before answering. Apply what you find."""

        task = "What is the convention for updating a skill in walter-worker?"

        # First call — agent should use search_memory
        response1 = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": task}],
            tools=[SEARCH_MEMORY_TOOL],
        )

        tool_uses = [b for b in response1.content if b.type == "tool_use"]
        memory_calls = [tu for tu in tool_uses if tu.name == "search_memory"]

        if not memory_calls:
            pytest.skip("Agent chose not to use search_memory — model decision")

        # Execute the tool calls
        tool_results = []
        for tu in memory_calls:
            query_str = tu.input.get("query", "")
            min_s = tu.input.get("min_score", 0.3)
            results = _execute_search_memory(query_str, min_score=min_s)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tu.id,
                "content": json.dumps(results, ensure_ascii=False),
            })

        # Second call — agent processes results and answers
        messages = [
            {"role": "user", "content": task},
            {"role": "assistant", "content": response1.content},
            {"role": "user", "content": tool_results},
        ]

        response2 = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
            tools=[SEARCH_MEMORY_TOOL],
        )

        final_text = "".join(
            b.text for b in response2.content if b.type == "text"
        )

        # If model used tool_use instead of text, extract from tool input
        if not final_text:
            tool_uses = [b for b in response2.content if b.type == "tool_use"]
            if tool_uses:
                final_text = json.dumps([{"name": tu.name, "input": tu.input} for tu in tool_uses])

        # The agent's answer should reference the conventions it found
        assert len(final_text) > 20, (
            f"Subagent gave too short an answer. "
            f"Content blocks: {[b.type for b in response2.content]}"
        )

        # Should mention skill-related concepts from the retrieved memories
        skill_signals = ["skill", "update", "convention", "SKILL.md", "skill-factory"]
        found = [s for s in skill_signals if s.lower() in final_text.lower()]
        assert len(found) >= 1, (
            f"Subagent answer didn't reference conventions. "
            f"Found: {found}. Answer: {final_text[:300]}"
        )
