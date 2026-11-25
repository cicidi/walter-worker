"""Mem0Client.from_config picks the Qdrant server from COWORKER_QDRANT_URL.

Embedded Qdrant locks its folder to one process, so the dashboard, the Stop
hook and every memory MCP server fought over ~/.coworker/memory/vector and
the losers silently got nothing. A Qdrant server takes many clients at once.
"""

from __future__ import annotations

import sys
import types

import pytest
from coworker.memory.mem0_client import Mem0Client


@pytest.fixture
def captured(monkeypatch, tmp_path):
    """Stand-in `mem0` module that records the config it is built with."""
    configs: list[dict] = []

    class Memory:
        @classmethod
        def from_config(cls, config):
            configs.append(config)
            return cls()

    monkeypatch.setitem(sys.modules, "mem0", types.SimpleNamespace(Memory=Memory))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.delenv("COWORKER_QDRANT_URL", raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))  # never touch the real ~
    return configs


def _vs(configs):
    return configs[-1]["vector_store"]["config"]


def test_url_env_selects_the_server(captured, monkeypatch):
    monkeypatch.setenv("COWORKER_QDRANT_URL", "http://localhost:6333")
    Mem0Client.from_config()
    vs = _vs(captured)
    assert vs["url"] == "http://localhost:6333"
    assert "path" not in vs
    assert vs["embedding_model_dims"] == 384


def test_no_env_keeps_the_embedded_store(captured, tmp_path):
    Mem0Client.from_config()
    vs = _vs(captured)
    assert vs["path"] == str(tmp_path / ".coworker" / "memory" / "vector")
    assert "url" not in vs


def test_explicit_path_wins_over_env(captured, monkeypatch, tmp_path):
    monkeypatch.setenv("COWORKER_QDRANT_URL", "http://localhost:6333")
    Mem0Client.from_config(vector_store_path=str(tmp_path / "vec"))
    vs = _vs(captured)
    assert vs["path"] == str(tmp_path / "vec")
    assert "url" not in vs
