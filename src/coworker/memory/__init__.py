"""Memory platform module — mem0 substrate, capture hooks, and self-evolution engine.

Public API:
    LLMClient — DeepSeek Flash wrapper with provider fallback chain.
    Mem0Client — mem0 wrapper: add, search, update, delete, get.
"""

from coworker.memory.llm import LLMClient, LLMResponse
from coworker.memory.mem0_client import Mem0Client, ConfigError, Mem0Error

__all__ = [
    "LLMClient",
    "LLMResponse",
    "Mem0Client",
    "ConfigError",
    "Mem0Error",
]
