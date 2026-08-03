# Graph Report - .  (2026-07-27)

## Corpus Check
- Large corpus: 547 files · ~522,949 words. Semantic extraction will be expensive (many Claude tokens). Consider running on a subfolder.

## Summary
- 2595 nodes · 5126 edges · 202 communities (140 shown, 62 thin omitted)
- Extraction: 84% EXTRACTED · 16% INFERRED · 0% AMBIGUOUS · INFERRED: 836 edges (avg confidence: 0.6)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20
- Community 21
- Community 22
- Community 23
- Community 24
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 129
- Community 130
- Community 131
- Community 132
- Community 153
- Community 154
- Community 155
- Community 156
- Community 157
- Community 158
- Community 159
- Community 160
- Community 161
- Community 162
- Community 163
- Community 164
- Community 165
- Community 166
- Community 167
- Community 168
- Community 169
- Community 170
- Community 171
- Community 172
- Community 173
- Community 174
- Community 175
- Community 176
- Community 177
- Community 178
- Community 179
- Community 180
- Community 181
- Community 182
- Community 183
- Community 184
- Community 185
- Community 186
- Community 187
- Community 188
- Community 189
- Community 190
- Community 191
- Community 192
- Community 193
- Community 194
- Community 195
- Community 196
- Community 197
- Community 198

## God Nodes (most connected - your core abstractions)
1. `main()` - 119 edges
2. `InitiativeConfig` - 119 edges
3. `CoworkerConfig` - 100 edges
4. `InitiativeManager` - 94 edges
5. `ProjectCatalog` - 94 edges
6. `ProjectEntry` - 77 edges
7. `InitiativeProjectRef` - 57 edges
8. `Graph` - 51 edges
9. `Node` - 47 edges
10. `get_db()` - 43 edges

## Surprising Connections (you probably didn't know these)
- `test_state_update_activates_with_coworker_dir()` --indirect_call--> `main()`  [INFERRED]
  tests/python/test_state_update.py → src/coworker/cli.py
- `test_state_update_noop_outside_coworker()` --indirect_call--> `main()`  [INFERRED]
  tests/python/test_state_update.py → src/coworker/cli.py
- `test_two_stops_one_file()` --indirect_call--> `main()`  [INFERRED]
  tests/python/test_state_update.py → src/coworker/cli.py
- `test_parse_session_id_empty_value()` --calls--> `_parse_session_id()`  [INFERRED]
  tests/python/test_auto_import.py → src/coworker/analytics/auto_import.py
- `test_parse_session_id_fallback_to_dirname()` --calls--> `_parse_session_id()`  [INFERRED]
  tests/python/test_auto_import.py → src/coworker/analytics/auto_import.py

## Import Cycles
- None detected.

## Communities (202 total, 62 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (44): Auto-worker module — autonomous QA agent that audits and self-improves.  Uses Cl, ContextLoader, DeadCodeDetector, Finding, GapCheck, Auto-worker validation rules — spec §12.3.  8 rules that audit project state aga, Check for config keys that have no code references., R3: Per PRD/spec item, three-layer verification.      Layer 1: grep for code exi (+36 more)

### Community 1 - "Community 1"
Cohesion: 0.07
Nodes (71): allFileCache, applySF(), approveSkill(), cMov(), cRes(), cUp(), enrichContent(), escHtml() (+63 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (55): _had_block(), inject_initiative(), inject_static_context(), Path, Sync coworker config to Claude Code. Returns list of actions taken., Replace content between start..end markers with new_block.     Handles truncated, Write JSON to path atomically (tmp + rename) and keep a .bak., Write MCP servers to mcp_path (union by server name). (+47 more)

### Community 3 - "Community 3"
Cohesion: 0.10
Nodes (59): InitiativeManager, CoworkerConfig, InitiativeProjectRef, ProjectCatalog, ProjectEntry, Cover archive() method., Cover sync error-handling path when an adapter raises., Cover analytics import, daemon, once, and dashboard command bodies. (+51 more)

### Community 4 - "Community 4"
Cohesion: 0.05
Nodes (60): import_session(), parse_session_yaml(), Path, _make_jsonl(), Path, Tests for analytics/import_data.py — session import from hooks directories., Multiple calls to the same skill: total_calls incremented once per     unique sk, Session without session.yaml — uses directory name as session_id. (+52 more)

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (39): McpServer, OpenCodeOverrides, _make_config(), When all servers are disabled, mcp_servers dict is empty but mcp key is written., When project_dir is provided, config is written to <project_dir>/.opencode/confi, The bash permission 'coworker *' is set to 'allow'., Existing permissions are preserved when injecting coworker bash permission., config.opencode.extra entries are merged into the config. (+31 more)

### Community 6 - "Community 6"
Cohesion: 0.03
Nodes (44): When json.dump fails, the temp file should be cleaned up., sync() removes stale mcpServers from settings.json., sync() adds the state-update Stop hook if not present., sync() should not add a second state-update hook if one exists., sync() calls _sync_mcp and picks up its actions., inject_static_context updates an existing CLAUDE.md that already has a static bl, inject_static_context creates CLAUDE.md if it doesn't exist., inject_initiative injects into an existing CLAUDE.local.md. (+36 more)

### Community 7 - "Community 7"
Cohesion: 0.06
Nodes (24): _build_initiative_block(), save_initiative(), Create docs/<initiative>/{prd,plan,spec}/ directories., InitiativeConfig, test_build_initiative_block_with_testing(), Cover initiative start: existing initiative, invalid name, activate     error, a, Lines 697-698: initiative already exists, falls through to activate., Lines 687-688: _project_name finds catalog entry by local_path.          NOTE: _ (+16 more)

### Community 8 - "Community 8"
Cohesion: 0.06
Nodes (30): check_gaps(), Audit trail for memory sync operations.  Every sync (per-turn and session-end) w, Rebuild the mem0 index from raw session transcripts.      WARNING: Deletes all e, Append a timestamped audit record to the log file.      Args:         path: Full, Scan the audit log for gaps between consecutive records in the same session., rebuild_index(), write_audit_record(), _append_state_delta() (+22 more)

### Community 9 - "Community 9"
Cohesion: 0.06
Nodes (43): _ask_llm_is_duplicate(), build_summary_prompt(), get_all_sessions_since(), get_session_data(), _is_duplicate(), _levenshtein(), Knowledge extraction and storage with LLM-powered semantic deduplication., _semantic_key() (+35 more)

### Community 10 - "Community 10"
Cohesion: 0.12
Nodes (23): _build_static_block(), _remove_all_initiative_blocks(), ClaudeOverrides, Decision, GeminiOverrides, GitHubRef, KnowledgePoolEntry, LinkRef (+15 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (35): rank(), Confidence tier → numeric score mapping.  Single source of truth. Used by BOTH c, Return numeric rank for tier comparison. Higher = more confident., Graph data model — Node, Edge, and Graph types.  Schema version 1.0. See docs/se, Memory platform module — mem0 substrate, capture hooks, and self-evolution engin, _enrich_node(), _find_next_pending(), process_pending() (+27 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (22): LLMClient, LLMResponse, LLM client with DeepSeek Flash primary + automatic provider fallback chain.  Fal, Return the ordered list of provider configs to try.          Supports COWORKER_L, Call a single provider with retry logic., Result from an LLM chat completion call., Thin wrapper around OpenAI-compatible chat completions with fallback.      Prima, Send a chat completion request with automatic provider fallback.          Args: (+14 more)

### Community 13 - "Community 13"
Cohesion: 0.08
Nodes (4): main(), Coworker — unified AI dev environment for Claude Code, Gemini & OpenCode., Ensure --help works for every group and subcommand., TestHelpCov

### Community 14 - "Community 14"
Cohesion: 0.06
Nodes (31): Permissions, Skill, sync() without project_dir writes to global paths. Mock the global constants., sync() with project_dir writes to project/.claude/settings.json etc., Existing permissions should be preserved, new ones merged., sync() copies skill directory to skills dir., sync() copies a single skill file to skills dir., sync() warns when a configured skill path doesn't exist. (+23 more)

### Community 15 - "Community 15"
Cohesion: 0.09
Nodes (36): get, api_cost_analytics(), api_data_quality(), api_efficiency(), api_evolution_experiences(), api_evolution_overview(), api_evolution_pending(), api_evolution_skill_detail() (+28 more)

### Community 16 - "Community 16"
Cohesion: 0.06
Nodes (9): When removing the active initiative, deactivate is called first., TestActivate, TestActiveName, TestCreate, TestDeactivate, TestEdit, TestListAll, TestRemove (+1 more)

### Community 17 - "Community 17"
Cohesion: 0.11
Nodes (31): initiative_activate(), initiative_create(), initiative_deactivate(), initiative_edit(), initiative_list(), initiative_remove(), initiative_show(), initiative_start() (+23 more)

### Community 18 - "Community 18"
Cohesion: 0.10
Nodes (22): Group, Memory CLI — graph and memory management subcommands.  Wired into the main cowor, Register the 'memory' subcommand group on the main CLI., register_memory_commands(), _infer_node_type(), init_graph_from_graphify(), load_graphify_output(), Path (+14 more)

### Community 19 - "Community 19"
Cohesion: 0.08
Nodes (12): skip, _scan_project(), xfail, _scan_project detects Python from pyproject.toml., _scan_project detects FastAPI/Django/Flask/Click from pyproject.toml., _scan_project detects Go from go.mod., _scan_project detects Rust from Cargo.toml., _scan_project returns defaults when no markers found. (+4 more)

### Community 20 - "Community 20"
Cohesion: 0.11
Nodes (20): Inject wrong-history prevention rules into CLAUDE.local.md., memory_wrong_history(), Manage wrong-history entries — record mistakes or rebuild index., build_snapshot(), _extract_field(), extract_rules(), inject_into_local_md(), Path (+12 more)

### Community 21 - "Community 21"
Cohesion: 0.11
Nodes (27): List or approve pending skill review items., skill_pending(), approve(), batch_approve(), expire_old_items(), _install_to_commands(), list_pending(), _pending_dir() (+19 more)

### Community 22 - "Community 22"
Cohesion: 0.10
Nodes (19): _archive_old(), export_memory_md(), generate_report(), _mark_stale(), Path, Periodic maintenance — archive stale entries, merge duplicates, export MEMORY.md, Generate a human-readable MEMORY.md from mem0 entries.      Groups entries by pr, Score active memories by recency + frequency. Higher score = more useful.      U (+11 more)

### Community 23 - "Community 23"
Cohesion: 0.07
Nodes (15): Test hybrid retrieval (semantic + BM25 + entity)., Edge case: unknown query → empty list., Base happy path: filter by project., Inference 1: filter by different project (skill-factory)., Inference 2: filter by type., Inference 3: filter by state (active vs stale)., Inference 4: filter by topic., Inference 5: semantic query + project filter combined. (+7 more)

### Community 24 - "Community 24"
Cohesion: 0.10
Nodes (19): _fresh_config(), P5 tests: adapter sync respects user-owned entries (permissions union, MCP union, _temp_home(), test_foreign_hook_survives_sync(), test_gemini_mcp_union(), test_mcp_written_to_claude_json_not_settings(), test_permissions_user_entries_survive(), test_state_update_hook_deduped() (+11 more)

### Community 25 - "Community 25"
Cohesion: 0.13
Nodes (16): compute_effective_weight(), datetime, Passive decay computation for graph edges.  Spec §2: exponential decay on edge e, Compute the decay-adjusted effective_weight of an edge.      Spec §2.1 formula:, datetime, D9: Future timestamp → clamped to now, no decay., Spec §2: passive decay tests., D1: Within protection window (10 days) → effective=base. (+8 more)

### Community 26 - "Community 26"
Cohesion: 0.10
Nodes (18): AutoWorkerAgent, Auto-worker loop engine — spec §12.  Spawns Claude Code SDK sessions as autonomo, Run the auto-worker as a series of Claude agent sessions.          Each round sp, Build the initial agent prompt with full context., Read prior state files to give the agent context., Extract findings from agent output and update state file., Spawn a Claude Code agent session to perform a task.      Uses `claude` CLI in S, Write final summary to state file. (+10 more)

### Community 27 - "Community 27"
Cohesion: 0.13
Nodes (24): bridge_export(), export_initiatives(), export_knowledge_cards(), export_projects(), export_sessions(), export_skills(), export_tools(), Path (+16 more)

### Community 28 - "Community 28"
Cohesion: 0.12
Nodes (15): assess_skill(), extract_and_store(), ExtractionResult, _get_skill_threshold(), Evolution engine — extract, assess, reconcile.  Bridges capture layer (raw tool, Check if a session's work pattern is skill-worthy.      Called at session-end. R, Back-fill any missed captures by re-extracting from transcript.      Returns cou, Return the minimum tool calls for a session to trigger skill creation. (+7 more)

### Community 29 - "Community 29"
Cohesion: 0.12
Nodes (11): build_snapshot(), inject_into_local_md(), CLAUDE.local.md context injection — frozen snapshot at session start.  Reads rel, Remove the memory snapshot block from CLAUDE.local.md.      Returns True if the, Build a memory snapshot block for injection into CLAUDE.local.md.      Args:, Inject (or replace) a memory snapshot block in CLAUDE.local.md.      Args:, remove_snapshot(), Tests for coworker.memory.inject — CLAUDE.local.md snapshot injection. (+3 more)

### Community 30 - "Community 30"
Cohesion: 0.16
Nodes (18): get_transcript(), init_db(), list_all_sessions(), _migrate_add_graph_enabled(), Connection, Add graph_enabled column if it doesn't exist (pre-v1 databases)., List all sessions from the analytics database., Get messages for a session formatted as transcript. (+10 more)

### Community 31 - "Community 31"
Cohesion: 0.17
Nodes (20): Show current config status., status(), discover_project_skills(), find_project_config(), initiative_exists(), initiative_path(), _initiatives_dir(), list_initiatives() (+12 more)

### Community 32 - "Community 32"
Cohesion: 0.14
Nodes (22): _get_db_conn(), query_cost_analytics(), query_daily_sessions(), query_data_quality(), query_efficiency_insights(), query_file_detail(), query_knowledge_sessions(), query_model_usage() (+14 more)

### Community 33 - "Community 33"
Cohesion: 0.14
Nodes (21): memory(), memory_close(), memory_refresh(), memory_search(), memory_sync(), memory_train(), memory_validate(), argument (+13 more)

### Community 34 - "Community 34"
Cohesion: 0.14
Nodes (20): parse_sections(), Semantic merge for CLAUDE.md/doc documents.  Parses markdown into an ordered lis, Serialize back to markdown.  Normalizes to a single trailing newline., Split text into (line, in_fence) pairs.  Lines inside a ``` or ~~~ fence     blo, Parse markdown text into (header, ordered list of Sections).      * Duplicate he, _scan_lines(), Section, sections_to_text() (+12 more)

### Community 35 - "Community 35"
Cohesion: 0.18
Nodes (15): Graph, The full memory graph.      Schema version for forward compatibility (spec §8.2), _find_node(), graph_traverse(), _merge_and_rank(), Any, query(), Graph query API — traversal + mem0 hybrid search.  Spec §6: BFS with max depth 3 (+7 more)

### Community 36 - "Community 36"
Cohesion: 0.14
Nodes (15): _count_incorrect_assumptions(), _estimate_tool_calls(), _extract_memory_searches(), _extract_skill_calls(), Claude SDK Validation Harness — spec §12.5.  Spawns two Claude agents (baseline, Run a single Claude agent session. Returns result dict., Estimate tool call count from agent output., Count incorrect assumptions in transcript. (+7 more)

### Community 37 - "Community 37"
Cohesion: 0.17
Nodes (19): categorize_opencode_sessions(), extract_decisions_from_text(), generate_doc_organize_output(), get_git_log(), get_llm_client(), main(), process_project(), Connection (+11 more)

### Community 38 - "Community 38"
Cohesion: 0.16
Nodes (12): Node, A node in the memory graph.      Node types (spec §1.1):         code — static c, _dedup_and_merge(), Deduplicate a session node against existing graph nodes.      Spec §4.3: same ty, Spec §1.4: node ID namespace isolation., N5: IDs stored opaquely — no collision between identical-looking IDs., Spec §4.3: node deduplication., D1: Same file + same label → merged. (+4 more)

### Community 39 - "Community 39"
Cohesion: 0.17
Nodes (5): generate_project_claude_md(), Project info moved to CLAUDE.local.md — must not be in project CLAUDE.md., Relationships moved to CLAUDE.local.md — no relationships heading in CLAUDE.md., Doc map and knowledge repo headings removed from project CLAUDE.md., TestProjectTemplate

### Community 40 - "Community 40"
Cohesion: 0.20
Nodes (18): assign_test_scenarios(), check_blueprint(), check_duplicates(), check_protected_intact(), Duplicate, extract_instructions(), HarnessReport, Instruction (+10 more)

### Community 41 - "Community 41"
Cohesion: 0.20
Nodes (18): generate_full_session(), generate_knowledge_cards(), generate_messages(), generate_session_summary(), generate_session_yaml(), generate_tool_calls(), datetime, Path (+10 more)

### Community 42 - "Community 42"
Cohesion: 0.15
Nodes (15): import_opencode_meta(), Auto-import daemon: scan sessions, store metadata + stats only. Raw data lives a, Import OpenCode session metadata from opencode.db., run_daemon(), run_once(), import_all(), Group, Analytics commands for the Coworker CLI. (+7 more)

### Community 43 - "Community 43"
Cohesion: 0.11
Nodes (19): import_claude_jsonl(), Store session metadata + stats + file ops from Claude Code JSONL., Import a JSONL session with all tool types., A non-skill, non-file tool (e.g. TodoWrite) should set active_skill to None., After a Skill call, file tools inherit the skill_name., cwd can come from any line, not just the first one., Session without a timestamp gets empty string for created_at., filePath as an alternative key for file path. (+11 more)

### Community 44 - "Community 44"
Cohesion: 0.18
Nodes (12): check_circuit_breaker(), _circuit_state_path(), Path, Safety gates — spec §6 + §9.  Circuit breaker, sandbox dry-run, and rollback for, Manually reset the circuit breaker., Check if auto-evolution should be halted.      Returns {"allowed": bool, "reason, Record an auto-evolution action (create/patch).      Returns True if the action, record_auto_evolution() (+4 more)

### Community 45 - "Community 45"
Cohesion: 0.18
Nodes (11): apply_merge(), Apply classified changes to produce the merged document.      Raises ValueError, SectionClassification, apply_merge raises ValueError for unknown classification categories., test_raise_on_unknown_classification(), Cover apply_merge edges: OUTDATED (line 292) and unknown class (line 303)., Line 292: OUTDATED classification keeps the original section., Line 303: a classification with an unknown category raises ValueError. (+3 more)

### Community 46 - "Community 46"
Cohesion: 0.16
Nodes (13): generate_global_claude_md(), Return the canonical Global CLAUDE.md content., TestGlobalTemplate, Tests for the worker upgrade command (G1)., Upgrade over a freshly generated file reports 'already up to date'., User-added sections survive; modified sections overwrite; merge completes., --dry-run prints a plan but does not write., When stdout is not a TTY and --yes is absent, refuse. (+5 more)

### Community 47 - "Community 47"
Cohesion: 0.11
Nodes (18): gemini_home(), fixture, Tests for gemini adapter., sync preserves existing user MCP servers., sync applies gemini.extra overrides., sync writes settings.json with MCP servers., sync writes to project_dir when provided., Disabled MCP servers are skipped. (+10 more)

### Community 48 - "Community 48"
Cohesion: 0.21
Nodes (14): esc(), navigate(), renderAllSessions(), renderFiles(), renderFilesView(), renderInitiatives(), renderKnowledge(), renderKnowledgeCard() (+6 more)

### Community 49 - "Community 49"
Cohesion: 0.16
Nodes (16): _build_project_claude_md(), init(), initiative(), project(), group, Generate project CLAUDE.md (pure meta-controller, no project info)., Initialize global or project config with auto-scan., Sync config to Claude Code, Gemini, and/or OpenCode. (+8 more)

### Community 50 - "Community 50"
Cohesion: 0.11
Nodes (18): api_daily_sessions(), api_file_detail(), api_knowledge_sessions(), api_session_messages(), api_skill_detail(), api_skill_timeline(), api_tool_detail(), api_tool_sessions() (+10 more)

### Community 51 - "Community 51"
Cohesion: 0.20
Nodes (16): _compute_evolution_score(), _count_agent_experiences(), _count_pending(), _list_skills(), query_evolution_experiences(), query_evolution_overview(), query_evolution_pending(), query_evolution_skills() (+8 more)

### Community 52 - "Community 52"
Cohesion: 0.18
Nodes (12): compute_evolution_score(), get_metrics_report(), _load_metrics(), Evolution metrics collection — spec §7.  Collects effectiveness and safety metri, Record per-session evolution metrics.      Args:         session_id: Session ide, Compute a 0-100 evolution score from collected metrics.      Higher = agent is g, Generate a human-readable metrics report., record_session_metrics() (+4 more)

### Community 53 - "Community 53"
Cohesion: 0.14
Nodes (11): classify_sections(), Compare current and future CLAUDE.md, classify each section.      Sections wholl, Sections inside a PROTECTED span are forced KEEP even when changed in future., Non-protected sections still overwrite normally., test_normal_section_still_overwrites(), test_protected_sections_forced_keep(), Cover classification edges: placeholder KEEP (lines 214-215)., Lines 213-215: when future body is a placeholder,         the section is classif (+3 more)

### Community 54 - "Community 54"
Cohesion: 0.11
Nodes (7): Tests for analytics/auto_import.py — auto-import daemon functions., _parse_session_id result is used for dedup, but import_claude_hooks     inserts, When _parse_session_id returns an ID that already exists, it's skipped., run_daemon should call run_once and sleep in a loop., test_run_daemon_one_iteration(), test_run_once_hooks_skipped_when_session_id_exists(), test_run_once_hooks_uses_parse_session_id_for_dedup()

### Community 55 - "Community 55"
Cohesion: 0.11
Nodes (10): Edge case: empty metadata dict., Inference 1: add with run_id (track session provenance)., Inference 2: add with ALL metadata fields populated., Inference 3: multiple adds → all retrievable., Inference 4: Chinese text → stored and searchable., Inference 5: long memory content (500+ chars) → stored correctly., Test memory entry creation., Base happy path: add entry → search finds it. (+2 more)

### Community 56 - "Community 56"
Cohesion: 0.21
Nodes (16): check_blueprint_3layer(), check_budget(), check_duplicates(), count_lines(), extract_instructions(), _is_useful(), main(), print_result() (+8 more)

### Community 57 - "Community 57"
Cohesion: 0.14
Nodes (12): Edge, BaseModel, A directed edge in the memory graph.      Spec §1.2 — full edge schema.      con, _enrich_edge(), Add base_weight, last_traversed_at, and provenance to a raw edge.      Spec §4.2, Spec §4.2: merge worker enrichment., Spec integration test plan G1-G4., G1: Empty graph + Graphify output → all imported. (+4 more)

### Community 58 - "Community 58"
Cohesion: 0.16
Nodes (9): Cover upgrade command: no file, dry-run, already up-to-date, declines,     prote, Lines 411-412: ~/.claude/CLAUDE.md does not exist., Lines 427, 429, 433-435: --dry-run prints merge plan and exits., Lines 442-444: content matches template; no merge needed., Lines 447-448: user answers 'n' to confirmation prompt., Lines 427: MERGE_ADD detail string in the merge plan table when         the curr, Lines 455-458: verify_protected returns violations, sys.exit(1)., Lines 450-451, 460-461: successful merge writes updated content. (+1 more)

### Community 59 - "Community 59"
Cohesion: 0.15
Nodes (16): _get_skills(), Extract unique skill names from a Claude Code JSONL session., _make_jsonl(), Path, Exception during import should be caught and not crash run_once., test_get_skills_bad_json_skipped(), test_get_skills_content_not_list(), test_get_skills_empty_file() (+8 more)

### Community 60 - "Community 60"
Cohesion: 0.18
Nodes (7): append_jsonl(), ensure_session(), common.sh script, on-post-tool.sh script, on-pre-tool.sh script, on-stop.sh script, on-user-prompt.sh script

### Community 61 - "Community 61"
Cohesion: 0.12
Nodes (9): Test memory entry modification., Base happy path: change state from active to stale., Inference 1: update the memory text content., Inference 2: update both content and metadata simultaneously., Inference 3: update only metadata, content unchanged., Inference 4: state lifecycle transition → archived., Inference 5: pin an entry (change state to pinned)., Inference 6: update temporal metadata fields. (+1 more)

### Community 62 - "Community 62"
Cohesion: 0.16
Nodes (6): applyTheme(), buildPresenterHTML(), cycleTheme(), fromHash(), go(), openPresenterWindow()

### Community 63 - "Community 63"
Cohesion: 0.15
Nodes (11): Exception, ConfigError, Mem0Error, mem0 client wrapper — store, retrieve, and manage cross-session memory.  Uses me, Add a memory entry. Retries with exponential backoff on failure.          Return, Raised when mem0 configuration is invalid (missing keys, bad paths, etc.)., Raised when a mem0 operation fails after all retries., Test single entry retrieval. (+3 more)

### Community 64 - "Community 64"
Cohesion: 0.13
Nodes (5): ErrorCode, Error code registry — spec §9.  Namespaced error codes for the memory platform a, Namespaced error code with message template., Tests for coworker.memory.errors — error code registry., TestErrorCodes

### Community 65 - "Community 65"
Cohesion: 0.15
Nodes (12): Return violation descriptions.  Each span in 'original' that is marked     <!--, verify_protected(), Any change inside a protected span is blocked — merged output keeps original., A user-added rule inside a PROTECTED span survives the merge., test_protection_overrides_tampering(), test_user_rule_inside_protected_span_is_kept(), test_verify_protected_passes_on_clean_merge(), Cover verify_protected: truncation (lines 320-321) and modification     (line 32 (+4 more)

### Community 66 - "Community 66"
Cohesion: 0.20
Nodes (14): clean_mem0(), _mem0_session_dir(), populated_mem0(), fixture, mem0 client pre-loaded with 5 test entries across 2 projects., Real DeepSeek Flash LLMClient. Requires DEEPSEEK_API_KEY., Redirect INITIATIVES_DIR to a temp directory for isolated tests., Session-scoped temp directory for mem0 global state.      MEM0_DIR must be set b (+6 more)

### Community 67 - "Community 67"
Cohesion: 0.14
Nodes (10): real, Tests for coworker.memory.mem0_client — Mem0Client CRUD operations.  Tier 1 dete, Test full store reset., Base: add entries → delete_all → search returns empty., Inference 1: after reset, store is functional.          NOTE: mem0 reset() may c, Test resilience patterns.      NOTE: These tests are kept simple to avoid Qdrant, Edge case: unusual query characters → no crash., Edge case: 10 rapid adds → all succeed. (+2 more)

### Community 68 - "Community 68"
Cohesion: 0.13
Nodes (3): TestClaudeMdReferences, TestDeployConsistency, TestSkillFactorySource

### Community 69 - "Community 69"
Cohesion: 0.14
Nodes (3): Tests for coworker.memory.pending — staged skill review queue., TestExpire, TestStageListApproveReject

### Community 70 - "Community 70"
Cohesion: 0.23
Nodes (4): BASE_DIR, Recorder, createSession(), generateSessionId()

### Community 71 - "Community 71"
Cohesion: 0.18
Nodes (12): project_add(), project_edit(), project_list(), project_remove(), project_show(), List all tracked projects., Show details of a single project., Add a project to the catalog. (+4 more)

### Community 72 - "Community 72"
Cohesion: 0.21
Nodes (5): _extract_active_name(), _local_md_path(), Path, Derive the active initiative from the project's CLAUDE.local.md         INITIATI, TestExtractActiveName

### Community 73 - "Community 73"
Cohesion: 0.21
Nodes (7): confidence_to_score(), Map a confidence tier string to its numeric score.      Unknown/missing → AMBIGU, Spec §1.3: confidence tier to score mapping., C4: Unknown → AMBIGUOUS (0.5)., C5: Missing/None → AMBIGUOUS (0.5)., Tier ranks must be: EXTRACTED > INFERRED > AMBIGUOUS > WEAK., TestConfidenceMapping

### Community 74 - "Community 74"
Cohesion: 0.18
Nodes (7): Mem0Client, Search memory entries using hybrid retrieval.          Args:             query:, Update a memory entry's content and/or metadata.          Args:             entr, Delete a memory entry. Silently succeeds if entry does not exist., Retrieve a single memory entry by ID.          Returns:             Memory entry, Reset the memory store — removes ALL entries. Irreversible., Wrapper around the mem0 Memory instance.      Provides typed add/search/update/d

### Community 75 - "Community 75"
Cohesion: 0.36
Nodes (12): Connection, Tests for the coworker.dashboard module: queries and FastAPI endpoints., Populate every table with representative test data., _seed_all(), _seed_file_ops(), _seed_knowledge(), _seed_messages(), _seed_session_stats() (+4 more)

### Community 76 - "Community 76"
Cohesion: 0.29
Nodes (10): AVAILABLE_SKILLS, error(), index_skills(), install_skill(), log(), ok(), install.sh script, SKILL_LABELS (+2 more)

### Community 77 - "Community 77"
Cohesion: 0.17
Nodes (12): _count_jsonl_skill_calls(), _parse_session_id(), Path, Read session_id from session.yaml, falling back to directory name., Count Skill invocations in a Claude Code JSONL session., test_count_jsonl_skill_calls(), test_count_jsonl_skill_calls_not_exists(), test_count_jsonl_skill_calls_with_bad_json() (+4 more)

### Community 78 - "Community 78"
Cohesion: 0.26
Nodes (5): _is_placeholder(), Cover _is_placeholder including all patterns and the line-37 fallthrough., Placeholder detection is substring-based, not exact match., Line 37: stripped body that doesn't match any pattern -> False., TestIsPlaceholder

### Community 79 - "Community 79"
Cohesion: 0.17
Nodes (11): Install artifact tests — run against a hermetic temp HOME (installed_home).  Nev, install.sh creates hooks, DB, config under the temp HOME., Claude Code hooks use the canonical {matcher, hooks:[{type,command}]} shape., OpenCode: ai-coworker skills are deployed under .config/opencode/skills/.      N, The on-user-prompt hook script exists and is executable., sessions directory created., test_claude_hooks_configured(), test_install_creates_all_artifacts() (+3 more)

### Community 80 - "Community 80"
Cohesion: 0.17
Nodes (7): Test memory entry removal., Base happy path: delete → search no longer finds it., Edge case: deleting non-existent ID → no exception., Edge case: delete with empty string ID → no crash., Inference 1: double-delete → idempotent, no error., Inference 2: delete one of many → others remain., TestMem0ClientDelete

### Community 81 - "Community 81"
Cohesion: 0.18
Nodes (11): _count_jsonl_lines(), import_claude_hooks(), Store metadata from Claude Code hooks session directory., test_count_jsonl_lines(), test_count_jsonl_lines_empty(), test_count_jsonl_lines_file_not_exists(), test_count_jsonl_lines_with_blank_lines(), test_import_claude_hooks_basic() (+3 more)

### Community 82 - "Community 82"
Cohesion: 0.22
Nodes (8): dict_to_graph(), _migrate(), Deserialize a dict (from graph.json) into a Graph.      Handles schema migration, Stub migration function for forward compatibility (spec §8.2).      Currently on, Spec §8.2: schema versioning., V2: Missing schema_version → treated as 1.0., V3: Future version → raises error with clear message., TestSchemaVersion

### Community 83 - "Community 83"
Cohesion: 0.22
Nodes (8): protected_ranges(), Return inclusive (start_line, end_line) ranges protected by     ``<!-- PROTECTED, test_protected_ranges_are_found(), Cover protected_ranges edge cases: unclosed markers (line 164-165)     and end-w, Lines 164-165: start marker with no end — protects through end of file., End marker without prior start is silently skipped., Nested protected markers produce overlapping ranges., TestProtectedRanges

### Community 84 - "Community 84"
Cohesion: 0.20
Nodes (9): post, api_evolution_approve(), api_evolution_experience_detail(), api_evolution_reject(), api_memory_refresh(), api_memory_reset_circuit(), Trigger CLAUDE.local.md snapshot refresh., Reset the circuit breaker. (+1 more)

### Community 85 - "Community 85"
Cohesion: 0.20
Nodes (6): Test mem0 client creation and configuration., Base happy path: valid config → usable client., Edge case: no DEEPSEEK_API_KEY → ConfigError., Inference 1: all defaults → still works., Inference 2: custom path is auto-created if missing., TestMem0ClientInit

### Community 86 - "Community 86"
Cohesion: 0.31
Nodes (4): Run the complete training pipeline per spec §12.4.      1. Read ALL past session, run_training_pipeline(), Tests for coworker.memory.train — batch training pipeline., TestTrainingPipeline

### Community 87 - "Community 87"
Cohesion: 0.22
Nodes (6): Cover the line-137 early-return when header and sections are empty., Line 137: sections_to_text with empty header and no sections., Cover parse_sections edge cases including heading-inside-fence     (exercising l, A heading (#, ##, ###) inside a fenced code block before the         first real, TestParseSectionsEdgeCases, TestSectionsToText

### Community 88 - "Community 88"
Cohesion: 0.32
Nodes (6): parametrize, _parse_fm(), G11: All skills/*/SKILL.md must conform to the canonical frontmatter schema. Req, Running 'coworker skill new test-skill' produces schema-compliant output., test_frontmatter_has_required_fields(), test_scaffold_conforms()

### Community 89 - "Community 89"
Cohesion: 0.36
Nodes (7): fill_project_gaps(), generate_doc(), get_llm(), main(), Path, Generate a document from decisions using LLM., Fill missing document types for a project.

### Community 90 - "Community 90"
Cohesion: 0.46
Nodes (7): api_call(), extract_json(), extract_parts(), main(), process_one(), update_index(), write_card()

### Community 91 - "Community 91"
Cohesion: 0.25
Nodes (8): api_errors(), api_session_errors(), Error patterns across tools and sessions., Sessions with the most errors., query_error_patterns(), query_session_errors(), Error patterns across tools and sessions., Recent sessions with tool errors.

### Community 92 - "Community 92"
Cohesion: 0.36
Nodes (4): Label similarity in [0, 1]. 1.0 = identical.      Pinned to difflib.SequenceMatc, _similarity(), Spec §4.3: difflib-based label similarity., TestSimilarity

### Community 93 - "Community 93"
Cohesion: 0.14
Nodes (4): Lines 953-959: dashboard with --db sets env var., Lines 722-723: mgr.activate raises FileNotFoundError., init --project detects pyproject.toml., init --project detects go.mod.

### Community 94 - "Community 94"
Cohesion: 0.39
Nodes (7): xfail, G12: correction-detector precision tests., _run(), test_correction_detected(), test_normal_prompt_no_trace(), test_plain_no_does_not_fire(), test_slash_command_skipped()

### Community 95 - "Community 95"
Cohesion: 0.25
Nodes (7): Tests for cohort init --project (P2 fixes: mkdir, sentinel, backup)., Second init skips CLAUDE.md regeneration (sentinel match fix)., Init over a hand-written CLAUDE.md takes a backup before overwriting., Fresh init on empty dir creates .coworker/coworker.yaml (mkdir fix)., test_init_over_handwritten_claude_md_backs_up(), test_init_project_creates_coworker_dir(), test_init_project_idempotent()

### Community 96 - "Community 96"
Cohesion: 0.38
Nodes (4): query_filter(), Classify an edge's effective_weight for query filtering.      Spec §2.2:, Spec §2.2: query filter thresholds., TestQueryFilter

### Community 97 - "Community 97"
Cohesion: 0.33
Nodes (6): _git_env(), installed_home(), fixture, Path, Top-level test config: import paths + the hermetic install fixture.  Every test, Run setup/install.sh --global into a throwaway HOME.      Pre-seeds a local fake

### Community 98 - "Community 98"
Cohesion: 0.33
Nodes (7): client(), _make_shared_conn(), fixture, Create a new connection to the shared in-memory database., Create a shared in-memory DB, seed it, and patch get_db.      Returns the anchor, TestClient with get_db patched to use the shared in-memory database., test_db()

### Community 100 - "Community 100"
Cohesion: 0.60
Nodes (5): error(), log(), ok(), uninstall.sh script, warn()

### Community 101 - "Community 101"
Cohesion: 0.53
Nodes (4): log(), ok(), update.sh script, warn()

### Community 103 - "Community 103"
Cohesion: 0.53
Nodes (5): _cli_commands(), _collect_refs(), Path, Reference-integrity test: every 'coworker <cmd>' in setup scripts must resolve t, test_all_script_skill_refs_resolve_in_cli()

### Community 104 - "Community 104"
Cohesion: 0.80
Nodes (4): boot(), initFxIn(), reinitFxIn(), stopFxIn()

### Community 106 - "Community 106"
Cohesion: 0.60
Nodes (4): main(), _parse_hook(), G12: Correction detector hook script (runs on UserPromptSubmit).  Reads a Claude, _score()

### Community 108 - "Community 108"
Cohesion: 0.40
Nodes (4): G9 tests: state-update opt-in gate + per-day file., test_state_update_activates_with_coworker_dir(), test_state_update_noop_outside_coworker(), test_two_stops_one_file()

### Community 109 - "Community 109"
Cohesion: 0.67
Nodes (3): main(), migrate_frontmatter(), Parse old frontmatter, return new YAML or None if already compliant.

### Community 110 - "Community 110"
Cohesion: 0.50
Nodes (4): api_activity(), Hourly activity breakdown., query_activity_timeline(), Hourly activity breakdown.

### Community 111 - "Community 111"
Cohesion: 0.50
Nodes (4): api_hotspots(), Most frequently modified files with churn metrics., query_file_hotspots(), Most frequently modified files with churn metrics.

### Community 112 - "Community 112"
Cohesion: 0.50
Nodes (4): api_memory_stats(), Memory platform health., query_memory_stats(), Memory platform health.

### Community 113 - "Community 113"
Cohesion: 0.50
Nodes (4): api_overview(), websocket_endpoint(), query_overview(), websocket

### Community 114 - "Community 114"
Cohesion: 0.50
Nodes (4): api_projects(), Project comparison — side-by-side metrics., query_projects(), Original project query format — used by original dashboard.js loadProjects().

### Community 115 - "Community 115"
Cohesion: 0.50
Nodes (3): Smoke tests for the analytics CLI subcommands — guards the P1 class: packaging (, create-db then once both exit 0 against a temp DB.      Regression guard for:, test_analytics_create_db_and_once()

### Community 118 - "Community 118"
Cohesion: 0.67
Nodes (3): api_session_timeline(), query_session_timeline(), Unified chronological timeline: messages + tool_calls + file_ops interleaved.

### Community 119 - "Community 119"
Cohesion: 0.67
Nodes (3): api_top_files(), query_top_files(), Files ranked by total touches.

### Community 120 - "Community 120"
Cohesion: 0.67
Nodes (3): auto_db(), fixture, In-memory SQLite with full schema, patched get_db.

### Community 132 - "Community 132"
Cohesion: 0.67
Nodes (3): import_db(), fixture, In-memory SQLite with full schema, patched get_db.

## Knowledge Gaps
- **18 isolated node(s):** `BASE_DIR`, `ai-coworker`, `polish-loop-driver.sh script`, `polish-loop-qa.sh script`, `AVAILABLE_SKILLS` (+13 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **62 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Mem0Client` connect `Community 74` to `Community 33`, `Community 67`, `Community 11`, `Community 15`, `Community 80`, `Community 51`, `Community 84`, `Community 85`, `Community 23`, `Community 55`, `Community 26`, `Community 61`, `Community 63`?**
  _High betweenness centrality (0.104) - this node is a cross-community bridge._
- **Why does `get_db()` connect `Community 41` to `Community 32`, `Community 33`, `Community 4`, `Community 9`, `Community 42`, `Community 15`, `Community 79`, `Community 113`, `Community 50`, `Community 51`, `Community 118`, `Community 119`, `Community 26`, `Community 27`, `Community 30`?**
  _High betweenness centrality (0.091) - this node is a cross-community bridge._
- **Why does `LLMClient` connect `Community 12` to `Community 33`, `Community 26`, `Community 11`, `Community 66`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **Are the 116 inferred relationships involving `main()` (e.g. with `test_analytics_create_db_and_once()` and `.test_analytics_daemon_body()`) actually correct?**
  _`main()` has 116 INFERRED edges - model-reasoned connections that need verification._
- **Are the 77 inferred relationships involving `InitiativeConfig` (e.g. with `TestAnalyticsCommandBodies` and `TestAnalyticsCommands`) actually correct?**
  _`InitiativeConfig` has 77 INFERRED edges - model-reasoned connections that need verification._
- **Are the 55 inferred relationships involving `CoworkerConfig` (e.g. with `TestAnalyticsCommandBodies` and `TestAnalyticsCommands`) actually correct?**
  _`CoworkerConfig` has 55 INFERRED edges - model-reasoned connections that need verification._
- **Are the 49 inferred relationships involving `InitiativeManager` (e.g. with `TestAnalyticsCommandBodies` and `TestAnalyticsCommands`) actually correct?**
  _`InitiativeManager` has 49 INFERRED edges - model-reasoned connections that need verification._