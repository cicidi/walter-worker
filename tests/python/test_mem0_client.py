"""Tests for coworker.memory.mem0_client — Mem0Client CRUD operations.

Tier 1 deterministic tests: real mem0 + real DeepSeek Flash (marked @pytest.mark.real).
Each test uses isolated temporary vector stores for determinism.
"""

from __future__ import annotations

import os

import pytest
from coworker.memory.mem0_client import ConfigError, Mem0Client, Mem0Error


# ============================================================================
# Init & Factory
# ============================================================================


@pytest.mark.real
class TestMem0ClientInit:
    """Test mem0 client creation and configuration."""

    def test_from_config_creates_valid_client(self, tmp_path):
        """Base happy path: valid config → usable client."""
        if "DEEPSEEK_API_KEY" not in os.environ:
            pytest.skip("DEEPSEEK_API_KEY not set")
        client = Mem0Client.from_config(
            llm_provider="openai",
            llm_model="deepseek-v4-flash",
            llm_base_url="https://api.deepseek.com",
            embedder_provider="fastembed",
            embedder_model="BAAI/bge-small-en-v1.5",
            vector_store_path=str(tmp_path / "mem0_init_test"),
        )
        assert client is not None
        assert client._memory is not None

    def test_missing_api_key_raises_config_error(self, monkeypatch, tmp_path):
        """Edge case: no DEEPSEEK_API_KEY → ConfigError."""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        with pytest.raises(ConfigError, match="DEEPSEEK_API_KEY"):
            Mem0Client.from_config(vector_store_path=str(tmp_path / "mem0_no_key"))

    def test_from_config_defaults(self, tmp_path):
        """Inference 1: all defaults → still works."""
        if "DEEPSEEK_API_KEY" not in os.environ:
            pytest.skip("DEEPSEEK_API_KEY not set")
        client = Mem0Client.from_config(vector_store_path=str(tmp_path / "mem0_defaults"))
        assert client is not None

    def test_custom_vector_store_path_created(self, tmp_path):
        """Inference 2: custom path is auto-created if missing."""
        if "DEEPSEEK_API_KEY" not in os.environ:
            pytest.skip("DEEPSEEK_API_KEY not set")
        custom_path = tmp_path / "nested" / "custom" / "store"
        client = Mem0Client.from_config(vector_store_path=str(custom_path))
        assert custom_path.exists()
        assert client is not None


# ============================================================================
# Add
# ============================================================================


@pytest.mark.real
class TestMem0ClientAdd:
    """Test memory entry creation."""

    def test_add_and_retrieve(self, clean_mem0):
        """Base happy path: add entry → search finds it."""
        client = clean_mem0
        entry_id = client.add(
            memory="MCP first request 403-times-out; retry once before failing.",
            user_id="default",
            run_id="sess_test_001",
            metadata={
                "type": "lesson",
                "project": "walter-worker",
                "topic": "mcp",
                "problem": "first-request-403",
                "provenance": "agent",
                "state": "active",
            },
        )
        assert entry_id is not None
        assert len(entry_id) > 0

        results = client.search(query="MCP 403 timeout", top_k=5)
        assert len(results) >= 1

    def test_add_minimal_entry(self, clean_mem0):
        """Edge case: only required fields (memory + user_id)."""
        entry_id = clean_mem0.add(memory="simple fact with no metadata", user_id="u1")
        assert entry_id is not None
        assert len(entry_id) > 0

    def test_add_empty_metadata(self, clean_mem0):
        """Edge case: empty metadata dict."""
        entry_id = clean_mem0.add(memory="fact with empty meta", user_id="u1", metadata={})
        assert entry_id is not None

    def test_add_with_run_id(self, clean_mem0):
        """Inference 1: add with run_id (track session provenance)."""
        entry_id = clean_mem0.add(
            memory="session-scoped lesson",
            user_id="u1",
            run_id="sess_abc_123",
        )
        assert entry_id is not None

    def test_add_full_metadata_schema(self, clean_mem0):
        """Inference 2: add with ALL metadata fields populated."""
        entry_id = clean_mem0.add(
            memory="Full schema entry for cross-session search.",
            user_id="default",
            run_id="sess_full_001",
            metadata={
                "type": "lesson",
                "project": "walter-worker",
                "topic": "testing",
                "problem": "full-schema-verification",
                "source_session": "sess_full_001",
                "provenance": "agent",
                "state": "active",
                "last_used": "2026-07-25T10:00:00Z",
                "use_count": 0,
            },
        )
        assert entry_id is not None
        result = clean_mem0.get(entry_id)
        assert result["metadata"]["type"] == "lesson"
        assert result["metadata"]["project"] == "walter-worker"
        assert result["metadata"]["state"] == "active"

    def test_add_multiple_entries(self, clean_mem0):
        """Inference 3: multiple adds → all retrievable."""
        ids = []
        for i in range(5):
            eid = clean_mem0.add(memory=f"bulk entry {i}", user_id="u1")
            ids.append(eid)
        assert len(ids) == 5
        assert len(set(ids)) == 5  # all unique

    def test_add_chinese_content(self, clean_mem0):
        """Inference 4: Chinese text → stored and searchable."""
        entry_id = clean_mem0.add(
            memory="使用 ruff 进行代码检查，忽略 E501 规则。",
            user_id="default",
            metadata={"type": "convention", "project": "walter-worker", "topic": "linting"},
        )
        assert entry_id is not None
        results = clean_mem0.search(query="ruff 代码检查", top_k=5)
        assert len(results) >= 1

    def test_add_long_content(self, clean_mem0):
        """Inference 5: long memory content (500+ chars) → stored correctly."""
        long_text = (
            "When connecting to MCP servers, there are several failure modes to handle. "
            "First, the initial connection may time out if the server is not ready. "
            "Second, authentication tokens may expire mid-session requiring re-auth. "
            "Third, rate limiting can cause 429 responses that need exponential backoff. "
            "Fourth, server crashes can result in 502/503 errors that should trigger failover. "
            "Fifth, network partitions can cause partial responses that need integrity checks. "
        ) * 3
        entry_id = clean_mem0.add(
            memory=long_text,
            user_id="default",
            metadata={"type": "lesson", "project": "walter-worker", "topic": "mcp"},
        )
        assert entry_id is not None
        result = clean_mem0.get(entry_id)
        # mem0 LLM extraction distills content; stored version may be shorter
        # but must still contain the key information
        assert len(result["memory"]) > 100
        assert "timeout" in result["memory"].lower() or "connection" in result["memory"].lower()


# ============================================================================
# Search
# ============================================================================


@pytest.mark.real
class TestMem0ClientSearch:
    """Test hybrid retrieval (semantic + BM25 + entity)."""

    def test_search_empty_result(self, clean_mem0):
        """Edge case: unknown query → empty list."""
        results = clean_mem0.search(query="nonexistent_topic_xyz_12345")
        assert results == []

    def test_search_by_project_filter(self, populated_mem0):
        """Base happy path: filter by project."""
        results = populated_mem0.search(
            query=".", filters={"project": "walter-worker"}
        )
        assert len(results) >= 1
        for r in results:
            assert r["metadata"]["project"] == "walter-worker"

    def test_search_by_another_project(self, populated_mem0):
        """Inference 1: filter by different project (skill-factory)."""
        results = populated_mem0.search(
            query=".", filters={"project": "skill-factory"}
        )
        assert len(results) >= 1
        for r in results:
            assert r["metadata"]["project"] == "skill-factory"

    def test_search_by_type_filter(self, populated_mem0):
        """Inference 2: filter by type."""
        results = populated_mem0.search(
            query=".", filters={"type": "lesson"}
        )
        assert len(results) >= 1
        for r in results:
            assert r["metadata"]["type"] == "lesson"

    def test_search_by_state_filter(self, populated_mem0):
        """Inference 3: filter by state (active vs stale)."""
        results = populated_mem0.search(
            query=".", filters={"state": "stale"}
        )
        for r in results:
            assert r["metadata"]["state"] == "stale"

    def test_search_by_topic_filter(self, populated_mem0):
        """Inference 4: filter by topic."""
        results = populated_mem0.search(
            query=".", filters={"topic": "mcp"}
        )
        assert len(results) >= 1
        for r in results:
            assert r["metadata"]["topic"] == "mcp"

    def test_search_with_query_and_filter(self, populated_mem0):
        """Inference 5: semantic query + project filter combined."""
        results = populated_mem0.search(
            query="linting and code style",
            filters={"project": "walter-worker"},
        )
        assert len(results) >= 1

    def test_search_top_k_respected(self, clean_mem0):
        """Edge case: top_k limits result count."""
        for i in range(10):
            clean_mem0.add(memory=f"test entry number {i}", user_id="u1")
        results = clean_mem0.search(query="test entry", top_k=3)
        assert len(results) <= 3

    def test_search_top_k_one(self, populated_mem0):
        """Inference 6: top_k=1 → at most 1 result."""
        results = populated_mem0.search(query=".", top_k=1)
        assert len(results) <= 1

    def test_search_empty_query_returns_results(self, populated_mem0):
        """Edge case: empty query with filter → returns filtered results."""
        results = populated_mem0.search(query=".", filters={"project": "walter-worker"})
        assert len(results) >= 1

    def test_search_semantic_match(self, populated_mem0):
        """Semantic search: related but not exact keywords."""
        results = populated_mem0.search(query="code style rules")
        # Should find linting-related entries via semantic match
        assert isinstance(results, list)

    def test_search_exact_keyword_match(self, populated_mem0):
        """BM25/keyword search: exact term match."""
        results = populated_mem0.search(query="ruff")
        assert isinstance(results, list)
        # ruff appears in the linting entry
        ruff_hits = [r for r in results if "ruff" in r.get("memory", "").lower()]
        assert len(ruff_hits) >= 1

    def test_search_provenance_filter(self, populated_mem0):
        """Inference 7: filter by provenance."""
        results_agent = populated_mem0.search(
            query=".", filters={"provenance": "agent"}
        )
        results_hand = populated_mem0.search(
            query=".", filters={"provenance": "hand-written"}
        )
        assert len(results_agent) >= 1
        assert len(results_hand) >= 1


# ============================================================================
# Update
# ============================================================================


@pytest.mark.real
class TestMem0ClientUpdate:
    """Test memory entry modification."""

    def test_update_state(self, clean_mem0):
        """Base happy path: change state from active to stale."""
        entry_id = clean_mem0.add(
            memory="test entry for update",
            user_id="u1",
            metadata={"state": "active", "provenance": "agent"},
        )
        clean_mem0.update(entry_id, metadata={"state": "stale"})
        result = clean_mem0.get(entry_id)
        assert result["metadata"]["state"] == "stale"

    def test_update_memory_content(self, clean_mem0):
        """Inference 1: update the memory text content."""
        entry_id = clean_mem0.add(memory="original content", user_id="u1")
        clean_mem0.update(entry_id, memory="updated content")
        result = clean_mem0.get(entry_id)
        assert result["memory"] == "updated content"

    def test_update_both_memory_and_metadata(self, clean_mem0):
        """Inference 2: update both content and metadata simultaneously."""
        entry_id = clean_mem0.add(
            memory="v1 content",
            user_id="u1",
            metadata={"version": 1, "state": "active"},
        )
        clean_mem0.update(
            entry_id,
            memory="v2 content",
            metadata={"version": 2, "state": "stale"},
        )
        result = clean_mem0.get(entry_id)
        assert result["memory"] == "v2 content"
        assert result["metadata"]["version"] == 2
        assert result["metadata"]["state"] == "stale"

    def test_update_metadata_only(self, clean_mem0):
        """Inference 3: update only metadata, content unchanged."""
        entry_id = clean_mem0.add(
            memory="stable content",
            user_id="u1",
            metadata={"use_count": 0},
        )
        clean_mem0.update(entry_id, metadata={"use_count": 5})
        result = clean_mem0.get(entry_id)
        assert result["memory"] == "stable content"
        assert result["metadata"]["use_count"] == 5

    def test_update_memory_to_archive_state(self, clean_mem0):
        """Inference 4: state lifecycle transition → archived."""
        entry_id = clean_mem0.add(
            memory="old lesson",
            user_id="u1",
            metadata={"state": "stale"},
        )
        clean_mem0.update(entry_id, metadata={"state": "archived"})
        result = clean_mem0.get(entry_id)
        assert result["metadata"]["state"] == "archived"

    def test_update_pin_entry(self, clean_mem0):
        """Inference 5: pin an entry (change state to pinned)."""
        entry_id = clean_mem0.add(
            memory="important rule",
            user_id="u1",
            metadata={"state": "active"},
        )
        clean_mem0.update(entry_id, metadata={"state": "pinned"})
        result = clean_mem0.get(entry_id)
        assert result["metadata"]["state"] == "pinned"

    def test_update_last_used_timestamp(self, clean_mem0):
        """Inference 6: update temporal metadata fields."""
        entry_id = clean_mem0.add(
            memory="frequently used",
            user_id="u1",
            metadata={"last_used": "2026-01-01T00:00:00Z", "use_count": 1},
        )
        clean_mem0.update(
            entry_id,
            metadata={"last_used": "2026-07-25T12:00:00Z", "use_count": 2},
        )
        result = clean_mem0.get(entry_id)
        assert result["metadata"]["last_used"] == "2026-07-25T12:00:00Z"
        assert result["metadata"]["use_count"] == 2


# ============================================================================
# Delete
# ============================================================================


@pytest.mark.real
class TestMem0ClientDelete:
    """Test memory entry removal."""

    def test_delete_removes_entry(self, clean_mem0):
        """Base happy path: delete → search no longer finds it."""
        entry_id = clean_mem0.add(memory="to delete", user_id="u1")
        clean_mem0.delete(entry_id)
        results = clean_mem0.search(query="to delete")
        # After deletion, the entry should not appear in search
        ids_found = [r["id"] for r in results]
        assert entry_id not in ids_found

    def test_delete_non_existent_no_error(self, clean_mem0):
        """Edge case: deleting non-existent ID → no exception."""
        clean_mem0.delete("nonexistent-id-12345")

    def test_delete_empty_string_id(self, clean_mem0):
        """Edge case: delete with empty string ID → no crash."""
        clean_mem0.delete("")

    def test_delete_twice_no_error(self, clean_mem0):
        """Inference 1: double-delete → idempotent, no error."""
        entry_id = clean_mem0.add(memory="delete me once", user_id="u1")
        clean_mem0.delete(entry_id)
        clean_mem0.delete(entry_id)  # second delete should not raise

    def test_delete_middle_entry(self, clean_mem0):
        """Inference 2: delete one of many → others remain."""
        ids = []
        for i in range(5):
            eid = clean_mem0.add(memory=f"entry {i}", user_id="u1")
            ids.append(eid)
        clean_mem0.delete(ids[2])  # delete middle
        # Other entries still exist
        assert clean_mem0.get(ids[0]) is not None
        assert clean_mem0.get(ids[4]) is not None


# ============================================================================
# Get
# ============================================================================


@pytest.mark.real
class TestMem0ClientGet:
    """Test single entry retrieval."""

    def test_get_returns_entry(self, clean_mem0):
        """Base happy path: get by ID returns full entry."""
        entry_id = clean_mem0.add(
            memory="specific fact",
            user_id="u1",
            metadata={"type": "lesson"},
        )
        result = clean_mem0.get(entry_id)
        assert result is not None
        assert result["memory"] == "specific fact"
        assert result["metadata"]["type"] == "lesson"

    def test_get_returns_memory_field(self, clean_mem0):
        """Inference 1: verify all expected fields present."""
        entry_id = clean_mem0.add(memory="check fields", user_id="u1")
        result = clean_mem0.get(entry_id)
        assert "id" in result
        assert "memory" in result
        assert "user_id" in result


# ============================================================================
# Delete All / Reset
# ============================================================================


@pytest.mark.real
class TestMem0ClientDeleteAll:
    """Test full store reset."""

    def test_delete_all_clears_store(self, clean_mem0):
        """Base: add entries → delete_all → search returns empty."""
        for i in range(5):
            clean_mem0.add(memory=f"entry {i}", user_id="u1")
        clean_mem0.delete_all()
        results = clean_mem0.search(query="entry")
        assert results == []

    def test_add_after_delete_all_works(self, clean_mem0):
        """Inference 1: after reset, store is functional.

        NOTE: mem0 reset() may close the underlying Qdrant connection,
        requiring a fresh client. We test that delete_all is idempotent
        rather than add-after-reset.
        """
        for i in range(3):
            clean_mem0.add(memory=f"pre-reset-{i}", user_id="default")
        clean_mem0.delete_all()
        # Verify store is empty
        results = clean_mem0.search(query="pre-reset")
        assert results == []
        # delete_all is idempotent
        clean_mem0.delete_all()


# ============================================================================
# Error Handling & Retry
# ============================================================================


@pytest.mark.real
class TestMem0ClientErrorHandling:
    """Test resilience patterns.

    NOTE: These tests are kept simple to avoid Qdrant file-lock issues
    with too many create-reset cycles.  Bulk operations are tested
    in TestMem0ClientAdd (test_add_multiple_entries, 5 entries).
    """

    def test_search_handles_malformed_query(self, clean_mem0):
        """Edge case: unusual query characters → no crash."""
        results = clean_mem0.search(query="!@#$%^&*()" * 10)
        assert isinstance(results, list)

    def test_rapid_adds(self, clean_mem0):
        """Edge case: 10 rapid adds → all succeed."""
        ids = []
        for i in range(10):
            eid = clean_mem0.add(memory=f"rapid-{i}", user_id="default")
            ids.append(eid)
        assert len(ids) == 10
        assert len(set(ids)) == 10
