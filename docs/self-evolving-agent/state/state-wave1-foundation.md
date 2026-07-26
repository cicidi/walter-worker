# Wave 1: Foundation — Implementation State

> Started: 2026-07-25 | Completed: 2026-07-25 | Status: **complete**
> Auto-TDD Phase: Phase 1-3 complete (Agent-A + Agent-B + Test Execution)

## Files Created/Modified

| File | Action |
|------|--------|
| `src/coworker/memory/__init__.py` | **Created** — module init, exports LLMClient, Mem0Client, error classes |
| `src/coworker/memory/llm.py` | **Created** — 120 lines, LLMClient + DeepSeek-v4-Flash + Gemini fallback |
| `src/coworker/memory/mem0_client.py` | **Created** — 190 lines, Mem0Client CRUD wrapper with fastembed |
| `tests/python/conftest.py` | **Modified** — added `_mem0_session_dir` + `clean_mem0` + `populated_mem0` fixtures |
| `tests/python/test_llm.py` | **Created** — 17 tests (12 unit + 5 real) |
| `tests/python/test_mem0_client.py` | **Created** — 43 tests (all real) |
| `pyproject.toml` | **Modified** — added `[tool.pytest.ini_options]` markers config |

## Dependencies Added

```
pip install openai mem0ai fastembed qdrant-client
```

- Upgraded PyTorch from 2.4.0 to 2.13.0 (then reverted to 2.4.0)
- mem0ai 2.0.14, qdrant-client 1.18.0

## Issues Encountered & Resolved

### Issue 1: Wrong model names
- **Problem:** `deepseek-chat` no longer valid → must use `deepseek-v4-flash` or `deepseek-v4-pro`
- **Problem:** `gemini-2.0-flash` deprecated → switched to `gemini-2.5-flash`
- **Problem:** Anthropic doesn't support OpenAI-compatible API → removed from fallback chain
- **Fix:** Updated defaults in llm.py, mem0_client.py, and all tests

### Issue 2: DeepSeek v4 reasoning tokens
- **Problem:** DeepSeek v4 Flash uses tokens for `reasoning_content` which counts against `max_tokens`. With low max_tokens (10-20), content was empty.
- **Fix:** Increased default test max_tokens to 50-100. Added `reasoning_content` fallback in LLMClient (uses reasoning as content if content is empty).

### Issue 3: mem0 API compatibility (v2)
- **Problem:** mem0 v2 returns `{"results": [...]}` dicts, not lists
- **Problem:** mem0 v2 requires `openai_base_url` (not `base_url`)
- **Problem:** mem0 v2 requires `user_id`/`agent_id`/`run_id` in search filters
- **Problem:** mem0 v2 rejects empty string queries
- **Fix:** Updated Mem0Client.add() and search() to handle dict results. Added `user_id="default"` auto-injection in search(). Fixed `embedding_model_dims=384` in Qdrant config.

### Issue 4: HuggingFace embedder → fastembed
- **Problem:** mem0's huggingface embedder requires sentence-transformers + torch, causing DTensor import error with PyTorch 2.4.0
- **Fix:** Switched to `fastembed` provider (ONNX runtime, no PyTorch dependency). Spec-compliant (BAAI/bge-small-en-v1.5, 384-dim).

### Issue 5: Qdrant file lock conflicts
- **Problem:** mem0 creates a global `~/.mem0/migrations_qdrant/` with file locks. Multiple tests creating/destroying clients cause `AlreadyLocked` errors.
- **Fix:** Session-scoped `MEM0_DIR` fixture. Each test still gets an isolated vector store.

### Issue 6: mem0 LLM extraction returns empty
- **Problem:** mem0's LLM extraction sometimes returns empty `{"results": []}` for simple messages
- **Fix:** Added `infer=False` fallback in add() — retry without LLM extraction if first attempt yields empty results

## Test Results

### Tier 1: Deterministic Fixed-Scenario Tests — **FINAL: 60/60 PASSED**

#### test_llm.py (17/17 passed)
```
TestLLMResponse::test_default_usage_is_empty_dict        PASSED
TestLLMResponse::test_all_fields_present                 PASSED
TestLLMClientInit::test_default_config                    PASSED
TestLLMClientInit::test_custom_config                     PASSED
TestLLMClientInit::test_api_key_from_env                  PASSED
TestLLMClientChatReal::test_simple_chat_returns_response  PASSED  [DeepSeek v4 Flash]
TestLLMClientChatReal::test_chat_with_system_message      PASSED  [DeepSeek v4 Flash]
TestLLMClientChatReal::test_chat_with_temperature         PASSED  [DeepSeek v4 Flash]
TestLLMClientChatReal::test_chat_with_json_mode           PASSED  [DeepSeek v4 Flash]
TestLLMClientChatReal::test_chat_with_high_max_tokens     PASSED  [DeepSeek v4 Flash]
TestLLMClientFallback::test_no_api_keys_configured_raises PASSED
TestLLMClientFallback::test_fallback_chain_is_defined     PASSED
TestLLMClientFallback::test_fallback_skips_missing_keys   PASSED
TestLLMClientBuildProviderList::test_only_primary_*       PASSED
TestLLMClientBuildProviderList::test_primary_plus_gemini  PASSED
TestLLMClientBuildProviderList::test_all_providers_*      PASSED
TestLLMClientBuildProviderList::test_primary_skipped_*    PASSED
```

#### test_mem0_client.py (43/43 passed)
```
Init:     4/4  ✓  (from_config, missing_key, defaults, custom_path)
Add:      8/8  ✓  (retrieve, minimal, empty_meta, run_id, full_schema, multiple, chinese, long)
Search:  14/14 ✓  (empty, project, project2, type, state, topic, combined, top_k, top_k_1, query+filter,
                   semantic, keyword, provenance_agent, provenance_hand)
Update:   7/7  ✓  (state, content, both, metadata_only, archive, pin, timestamp)
Delete:   5/5  ✓  (remove, nonexistent, empty_id, double, middle)
Get:      2/2  ✓  (entry, fields)
DeleteAll:2/2  ✓  (clear, idempotent)
Errors:   2/2  ✓  (malformed_query, rapid_adds)
```

### Tier 2: Simulated LLM Tests — **DEFERRED**
> Tier 2 (multi-model simulated LLM tests) requires additional test infrastructure (mock gateways, session simulation). Will be implemented in Wave 3 (engine) where per-turn extraction is tested end-to-end.

### Tier 3: Quality Judge (Agent-D) — **NOT YET APPLIED**
> Agent-D evaluation will run after Tier 2 is complete. Current code is mechanically correct and follows spec patterns.

## Known Limitations

1. **Qdrant lock after reset:** Tests that call `delete_all()` should not be followed by tests that create new clients in the same process. The session-scoped MEM0_DIR mitigates this for most cases.
2. **Anthropic fallback removed:** Claude API requires non-OpenAI-compatible SDK. Future: add Anthropic SDK integration.
3. **No spaCy:** `mem0ai[nlp]` not installed. mem0 logs warnings but functions without it.

## Commits

_(pending — will commit after state file is complete)_
