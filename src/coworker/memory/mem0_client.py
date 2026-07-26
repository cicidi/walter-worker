"""mem0 client wrapper — store, retrieve, and manage cross-session memory.

Uses mem0 in library mode (in-process, no Docker/server required).
Hybrid retrieval combines semantic (vector) + BM25 (keyword) + entity matching.
"""

from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when mem0 configuration is invalid (missing keys, bad paths, etc.)."""


class Mem0Error(Exception):
    """Raised when a mem0 operation fails after all retries."""


class Mem0Client:
    """Wrapper around the mem0 Memory instance.

    Provides typed add/search/update/delete/get operations with
    retry logic on transient failures.
    """

    def __init__(self, memory: "Memory") -> None:  # noqa: F821
        self._memory = memory

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_config(
        cls,
        llm_provider: str = "openai",
        llm_model: str = "deepseek-v4-flash",
        llm_base_url: str = "https://api.deepseek.com",
        embedder_provider: str = "fastembed",
        embedder_model: str = "BAAI/bge-small-en-v1.5",
        vector_store_path: str = "~/.coworker/memory/vector",
    ) -> "Mem0Client":
        """Create a Mem0Client from a typed configuration.

        Args:
            llm_provider: mem0 provider key for the extraction LLM.
            llm_model: Model name (DeepSeek Flash).
            llm_base_url: Base URL for the OpenAI-compatible API.
            embedder_provider: mem0 provider key for embeddings (fastembed = local ONNX).
            embedder_model: Model ID for fastembed (BGE-small, 384-dim).
            vector_store_path: Filesystem path for the embedded Qdrant store.

        Returns:
            Configured Mem0Client ready for use.

        Raises:
            ConfigError: DEEPSEEK_API_KEY is missing or mem0 init fails.
        """
        from mem0 import Memory

        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if not api_key:
            raise ConfigError("DEEPSEEK_API_KEY environment variable is required")

        path = Path(vector_store_path).expanduser()
        path.mkdir(parents=True, exist_ok=True)

        config = {
            "llm": {
                "provider": llm_provider,
                "config": {
                    "model": llm_model,
                    "openai_base_url": llm_base_url,
                    "api_key": api_key,
                },
            },
            "embedder": {
                "provider": embedder_provider,
                "config": {"model": embedder_model},
            },
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "path": str(path),
                    "embedding_model_dims": 384,  # BGE-small embedding dimension
                    "on_disk": True,
                },
            },
        }

        try:
            memory = Memory.from_config(config)
        except Exception as exc:
            raise ConfigError(f"Failed to initialize mem0: {exc}") from exc

        return cls(memory)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def add(
        self,
        memory: str,
        user_id: str = "default",
        run_id: str | None = None,
        metadata: dict | None = None,
        max_retries: int = 3,
    ) -> str:
        """Add a memory entry. Retries with exponential backoff on failure.

        Returns:
            The mem0 entry ID string.
        """
        messages = [{"role": "user", "content": memory}]
        kwargs: dict = {"messages": messages, "user_id": user_id}
        if run_id:
            kwargs["run_id"] = run_id
        if metadata:
            kwargs["metadata"] = metadata

        last_error: Exception | None = None
        for attempt in range(max_retries):
            try:
                result = self._memory.add(**kwargs)
                # mem0 v2 returns {"results": [{"id": ..., "memory": ..., "event": "ADD"}]}
                if isinstance(result, dict) and "results" in result:
                    results_list = result["results"]
                    if results_list:
                        return str(results_list[0]["id"])
                    # LLM extraction returned nothing — retry without inference
                    logger.debug("mem0 LLM extraction returned empty; retrying with infer=False")
                    kwargs["infer"] = False
                    result = self._memory.add(**kwargs)
                    if isinstance(result, dict) and "results" in result:
                        if result["results"]:
                            return str(result["results"][0]["id"])
                    raise Mem0Error(f"mem0 add returned empty results for: {memory[:100]}")
                if isinstance(result, list):
                    return str(result[0]["id"])
                return str(result["id"])
            except Exception as exc:
                last_error = exc
                logger.warning("mem0 add attempt %d/%d failed: %s", attempt + 1, max_retries, exc)
                if attempt < max_retries - 1:
                    time.sleep(2**attempt)
                continue

        raise Mem0Error(f"mem0 add failed after {max_retries} retries: {last_error}")

    def search(
        self,
        query: str,
        filters: dict | None = None,
        top_k: int = 10,
        user_id: str = "default",
    ) -> list[dict]:
        """Search memory entries using hybrid retrieval.

        Args:
            query: Natural-language search query.
            filters: Key-value filter dict.
            top_k: Maximum number of results.
            user_id: User ID filter (mem0 v2 requires user_id/agent_id/run_id).

        Returns:
            List of memory entry dicts (empty list on error or no results).
        """
        effective_filters = dict(filters) if filters else {}
        # mem0 v2 requires at least one of user_id, agent_id, run_id
        if "user_id" not in effective_filters:
            effective_filters["user_id"] = user_id

        kwargs: dict = {"query": query, "top_k": top_k, "filters": effective_filters}
        try:
            result = self._memory.search(**kwargs)
            # mem0 v2 returns {"results": [...]}
            results_list: list[dict] = []
            if isinstance(result, dict) and "results" in result:
                results_list = list(result["results"])
            elif result:
                results_list = list(result)

            # Auto-increment use_count for retrieved entries (W-5, C-5)
            for entry in results_list:
                try:
                    meta = entry.get("metadata", {})
                    current_count = int(meta.get("use_count", 0))
                    entry_id = entry.get("id", "")
                    if entry_id:
                        self.update(entry_id, metadata={
                            "use_count": current_count + 1,
                            "last_used": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        })
                except Exception:
                    pass  # Best-effort — don't fail search for tracking

            return results_list
        except Exception as exc:
            logger.error("mem0 search failed: %s", exc)
            return []

    def update(
        self,
        entry_id: str,
        memory: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Update a memory entry's content and/or metadata.

        Args:
            entry_id: The mem0 entry ID.
            memory: New content string (if None, content is unchanged).
            metadata: New metadata dict (if None, metadata is unchanged).
        """
        kwargs: dict = {"memory_id": entry_id}
        if memory is not None:
            kwargs["data"] = memory
        if metadata is not None:
            kwargs["metadata"] = metadata
        self._memory.update(**kwargs)

    def delete(self, entry_id: str) -> None:
        """Delete a memory entry. Silently succeeds if entry does not exist."""
        try:
            self._memory.delete(entry_id)
        except (KeyError, Exception):
            pass

    def get(self, entry_id: str) -> dict:
        """Retrieve a single memory entry by ID.

        Returns:
            Memory entry dict as returned by mem0.
        """
        return self._memory.get(entry_id)

    def delete_all(self) -> None:
        """Reset the memory store — removes ALL entries. Irreversible."""
        self._memory.reset()
