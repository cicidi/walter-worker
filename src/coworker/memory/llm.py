"""LLM client with DeepSeek Flash primary + automatic provider fallback chain.

Fallback order: DeepSeek Flash → Gemini Flash → Claude Haiku → raise.
All providers are accessed via OpenAI-compatible API for uniformity.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field

from openai import OpenAI

logger = logging.getLogger(__name__)

FALLBACK_CHAIN: list[dict[str, str]] = [
    {
        "provider": "gemini",
        "model": "gemini-2.5-flash",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "api_key_env": "GEMINI_API_KEY",
    },
]


@dataclass
class LLMResponse:
    """Result from an LLM chat completion call."""

    content: str
    model: str
    provider: str
    usage: dict = field(default_factory=dict)


class LLMClient:
    """Thin wrapper around OpenAI-compatible chat completions with fallback.

    Primary provider is DeepSeek Flash. On failure, falls back through
    Gemini Flash → Claude Haiku. Raises RuntimeError if all are exhausted.
    """

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self._primary = {
            "provider": provider or "deepseek",
            "model": model or "deepseek-v4-flash",
            "base_url": base_url or "https://api.deepseek.com",
            "api_key": api_key or os.environ.get("DEEPSEEK_API_KEY", ""),
        }
        self._timeout = timeout
        self._max_retries = max_retries

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.3,
        max_tokens: int = 1000,
        response_format: dict | None = None,
    ) -> LLMResponse:
        """Send a chat completion request with automatic provider fallback.

        Args:
            messages: List of {"role": ..., "content": ...} dicts.
            temperature: Sampling temperature (0.0–2.0).
            max_tokens: Maximum tokens in the response.
            response_format: Optional OpenAI-style format spec
                (e.g. ``{"type": "json_object"}``).

        Returns:
            LLMResponse with content, model, provider, and token usage.

        Raises:
            RuntimeError: All providers exhausted.
        """
        providers = self._build_provider_list()
        last_error: Exception | None = None

        for cfg in providers:
            try:
                return self._call_provider(cfg, messages, temperature, max_tokens, response_format)
            except Exception as exc:
                logger.warning("LLM provider %s failed: %s", cfg["provider"], exc)
                last_error = exc
                continue

        raise RuntimeError(f"All LLM providers exhausted. Last error: {last_error}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_provider_list(self) -> list[dict[str, str]]:
        """Return the ordered list of provider configs to try.

        Supports COWORKER_LLM_MODELS env var override:
        e.g. COWORKER_LLM_MODELS="deepseek-v4-flash,gemini-2.5-flash"
        """
        providers: list[dict[str, str]] = []

        # Allow env var override of model names
        override = os.environ.get("COWORKER_LLM_MODELS", "")
        model_overrides = [m.strip() for m in override.split(",") if m.strip()] if override else []

        if self._primary.get("api_key"):
            primary = dict(self._primary)
            if model_overrides:
                primary["model"] = model_overrides[0]
            providers.append(primary)

        for i, cfg in enumerate(FALLBACK_CHAIN):
            api_key = cfg.get("api_key") or os.environ.get(str(cfg["api_key_env"]), "")
            if api_key:
                providers.append({**cfg, "api_key": api_key})
        if not providers:
            raise RuntimeError(
                "No LLM provider configured. Set DEEPSEEK_API_KEY, GEMINI_API_KEY, "
                "or ANTHROPIC_API_KEY in the environment."
            )
        return providers

    def _call_provider(
        self,
        cfg: dict[str, str],
        messages: list[dict],
        temperature: float,
        max_tokens: int,
        response_format: dict | None,
    ) -> LLMResponse:
        """Call a single provider with retry logic."""
        api_key = str(cfg["api_key"])
        client = OpenAI(base_url=str(cfg["base_url"]), api_key=api_key, timeout=self._timeout)

        last_error: Exception | None = None
        for attempt in range(self._max_retries):
            try:
                kwargs: dict = dict(
                    model=str(cfg["model"]),
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                if response_format:
                    kwargs["response_format"] = response_format

                resp = client.chat.completions.create(**kwargs)
                msg = resp.choices[0].message
                content = msg.content or ""

                # DeepSeek v4: if reasoning consumed all tokens, content may be empty.
                # Fall back to reasoning_content so callers always get usable text.
                if not content and msg.model_extra:
                    reasoning = msg.model_extra.get("reasoning_content", "")
                    if reasoning:
                        content = f"[reasoning] {reasoning}"

                return LLMResponse(
                    content=content,
                    model=str(cfg["model"]),
                    provider=str(cfg["provider"]),
                    usage={
                        "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
                        "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
                        "total_tokens": resp.usage.total_tokens if resp.usage else 0,
                    },
                )
            except Exception as exc:
                last_error = exc
                if attempt < self._max_retries - 1:
                    time.sleep(2**attempt)
                continue

        raise last_error  # type: ignore[misc]
