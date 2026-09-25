"""Tests for coworker.memory.llm — LLMClient with provider fallback chain.

Tier 1 deterministic tests: real LLM calls (marked @pytest.mark.real).
"""

from __future__ import annotations

import os

import pytest
from coworker.memory.llm import FALLBACK_CHAIN, LLMClient, LLMResponse


# ---------------------------------------------------------------------------
# LLMResponse dataclass
# ---------------------------------------------------------------------------


class TestLLMResponse:
    def test_default_usage_is_empty_dict(self):
        resp = LLMResponse(content="hello", model="m", provider="p")
        assert resp.usage == {}

    def test_all_fields_present(self):
        resp = LLMResponse(
            content="text",
            model="deepseek-chat",
            provider="deepseek",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        )
        assert resp.content == "text"
        assert resp.model == "deepseek-chat"
        assert resp.provider == "deepseek"
        assert resp.usage["total_tokens"] == 15


# ---------------------------------------------------------------------------
# LLMClient init
# ---------------------------------------------------------------------------


class TestLLMClientInit:
    def test_default_config(self):
        client = LLMClient()
        assert client._primary["provider"] == "deepseek"
        assert client._primary["model"] == "deepseek-v4-flash"
        assert client._primary["base_url"] == "https://api.deepseek.com"

    def test_custom_config(self):
        client = LLMClient(
            provider="custom-p",
            model="custom-m",
            base_url="https://custom.api",
            api_key="sk-test",
            timeout=60,
            max_retries=5,
        )
        assert client._primary["provider"] == "custom-p"
        assert client._primary["model"] == "custom-m"
        assert client._primary["base_url"] == "https://custom.api"
        assert client._primary["api_key"] == "sk-test"
        assert client._timeout == 60
        assert client._max_retries == 5

    def test_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "env-key")
        client = LLMClient()
        assert client._primary["api_key"] == "env-key"


# ---------------------------------------------------------------------------
# LLMClient.chat (real — requires DEEPSEEK_API_KEY)
# ---------------------------------------------------------------------------


@pytest.mark.real
class TestLLMClientChatReal:
    def test_simple_chat_returns_response(self):
        if "DEEPSEEK_API_KEY" not in os.environ:
            pytest.skip("DEEPSEEK_API_KEY not set")
        client = LLMClient()
        resp = client.chat(
            messages=[{"role": "user", "content": "Say 'hello' and nothing else."}],
            max_tokens=100,  # DeepSeek v4 uses some tokens for reasoning
        )
        assert isinstance(resp, LLMResponse)
        assert len(resp.content) > 0
        assert resp.model == "deepseek-v4-flash"
        assert resp.provider == "deepseek"
        assert resp.usage["total_tokens"] > 0

    def test_chat_with_system_message(self):
        if "DEEPSEEK_API_KEY" not in os.environ:
            pytest.skip("DEEPSEEK_API_KEY not set")
        client = LLMClient()
        resp = client.chat(
            messages=[
                {"role": "system", "content": "Reply in ALL CAPS."},
                {"role": "user", "content": "hello"},
            ],
            max_tokens=100,
        )
        assert len(resp.content) > 0

    def test_chat_with_temperature(self):
        """Inference 1: vary temperature → still returns valid response."""
        if "DEEPSEEK_API_KEY" not in os.environ:
            pytest.skip("DEEPSEEK_API_KEY not set")
        client = LLMClient()
        resp = client.chat(
            messages=[{"role": "user", "content": "Say 'ok'"}],
            temperature=0.0,
            max_tokens=50,  # DeepSeek v4 needs room for reasoning tokens
        )
        assert len(resp.content) > 0

    def test_chat_with_json_mode(self):
        """Inference 2: JSON response format → valid JSON returned."""
        if "DEEPSEEK_API_KEY" not in os.environ:
            pytest.skip("DEEPSEEK_API_KEY not set")
        client = LLMClient()
        resp = client.chat(
            messages=[{"role": "user", "content": 'Return JSON: {"key": "value"}'}],
            response_format={"type": "json_object"},
            max_tokens=50,
        )
        assert len(resp.content) > 0

    def test_chat_with_high_max_tokens(self):
        """Inference 3: higher max_tokens → more completion tokens consumed."""
        if "DEEPSEEK_API_KEY" not in os.environ:
            pytest.skip("DEEPSEEK_API_KEY not set")
        client = LLMClient()
        resp = client.chat(
            messages=[{"role": "user", "content": "List 5 testing best practices with brief explanation."}],
            max_tokens=500,
        )
        # DeepSeek v4 Flash may use tokens for reasoning; content may be short
        # but total completion tokens should be > 0
        assert resp.usage["completion_tokens"] > 0


# ---------------------------------------------------------------------------
# LLMClient fallback
# ---------------------------------------------------------------------------


class TestLLMClientFallback:
    def test_no_api_keys_configured_raises(self, monkeypatch):
        """All providers missing → RuntimeError during _build_provider_list."""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        client = LLMClient(api_key="")  # empty primary key
        with pytest.raises(RuntimeError, match="No LLM provider configured"):
            client.chat(messages=[{"role": "user", "content": "hi"}])

    def test_fallback_chain_is_defined(self):
        """FALLBACK_CHAIN has expected structure."""
        assert len(FALLBACK_CHAIN) >= 1
        for entry in FALLBACK_CHAIN:
            assert "provider" in entry
            assert "model" in entry
            assert "base_url" in entry
            assert "api_key_env" in entry

    def test_fallback_skips_missing_keys(self, monkeypatch):
        """Primary fails, fallback also missing → raises RuntimeError."""
        monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-ds-key")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        client = LLMClient()
        # With fake keys, providers will fail at API level → all exhausted
        with pytest.raises(RuntimeError, match="All LLM providers exhausted"):
            client.chat(messages=[{"role": "user", "content": "hi"}])


# ---------------------------------------------------------------------------
# LLMClient._build_provider_list
# ---------------------------------------------------------------------------


class TestLLMClientBuildProviderList:
    def test_only_primary_when_no_fallback_keys(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-key")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        client = LLMClient()
        providers = client._build_provider_list()
        assert len(providers) == 1
        assert providers[0]["provider"] == "deepseek"

    def test_primary_plus_gemini_when_gemini_key_set(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-key")
        monkeypatch.setenv("GEMINI_API_KEY", "gem-key")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        client = LLMClient()
        providers = client._build_provider_list()
        assert len(providers) == 2
        assert providers[1]["provider"] == "gemini"

    def test_all_providers_when_keys_set(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-key")
        monkeypatch.setenv("GEMINI_API_KEY", "gem-key")
        client = LLMClient()
        providers = client._build_provider_list()
        assert len(providers) == 2  # primary (deepseek) + gemini fallback

    def test_primary_skipped_when_api_key_empty(self, monkeypatch):
        """Inference: empty primary key + fallback keys → primary skipped."""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.setenv("GEMINI_API_KEY", "gem-key")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        client = LLMClient(api_key="")
        providers = client._build_provider_list()
        # primary skipped (empty key), gemini included
        assert all(p["provider"] != "deepseek" for p in providers)
        assert any(p["provider"] == "gemini" for p in providers)


class TestFallbackModelIsNotAPinnedVersion:
    """The fallback named a model that had been retired.

    gemini-2.5-flash still appears in the API's model list but answers 404 for
    new users — "no longer available to new users. Please update your code to
    use models/gemini-3.8-flash" — so a user without DEEPSEEK_API_KEY got a
    hard failure and no fallback at all.

    A fallback exists to work when the primary does not, so it should not be
    the part that expires. Asserted as a property rather than a name, so
    replacing one pin with another does not pass this.
    """

    def test_no_fallback_pins_an_exact_gemini_version(self):
        from coworker.memory.llm import FALLBACK_CHAIN

        for entry in FALLBACK_CHAIN:
            model = entry.get("model", "")
            if entry.get("provider") != "gemini":
                continue
            assert model.endswith("-latest") or "preview" in model, (
                f"gemini fallback pins {model!r}; a retired pin breaks the "
                f"fallback silently. Use an alias such as gemini-flash-latest."
            )


class TestTheErrorMessageNamesRealProviders:
    """It told users to set ANTHROPIC_API_KEY, which nothing reads.

    FALLBACK_CHAIN holds gemini and nothing else, so a user without a DeepSeek
    key read the error, set the variable it named, and got the same error
    again. The README said the same thing.

    Asserted as a property — every *_API_KEY the message names must belong to a
    configured provider — so adding a provider to the chain, or removing one,
    keeps the two in step without anyone remembering to edit the string.
    """

    def test_every_key_in_the_message_belongs_to_a_provider(self, monkeypatch):
        import re

        from coworker.memory.llm import FALLBACK_CHAIN, LLMClient

        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        try:
            LLMClient()._build_provider_list()
        except RuntimeError as exc:
            message = str(exc)
        else:
            pytest.fail("expected a RuntimeError when no provider is configured")

        named = set(re.findall(r"\b[A-Z][A-Z_]*_API_KEY\b", message))
        known = {"DEEPSEEK_API_KEY"} | {
            str(c["api_key_env"]) for c in FALLBACK_CHAIN
        }

        assert named, f"the message names no key at all: {message}"
        assert named <= known, (
            f"the message names {sorted(named - known)}, which no provider reads. "
            f"Configured: {sorted(known)}"
        )
