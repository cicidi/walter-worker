# Decision Record — unknown
> Project: walter-worker
> Decisions: 30

## Change Log
| Date | Change |
|------|--------|
| 2026-07-26 | Auto-generated from session analysis |

## Decisions

### 1. Remove budget-related features from PRD (budget flags, budget guards, cost model, 'Budget exhausted'
- **Source**: claude-code
- **Context**: During PRD refinement, user likely indicated budget constraints were not needed or too complex
- **Rationale**: Simplify the PRD and reduce implementation complexity; focus on time-based termination (12h default) instead
- **Alternatives rejected**: Keeping budget as a secondary mechanism, Implementing both budget and time limits
- **Confidence**: high

### 2. Replace complex Cost Model section with a simplified version
- **Source**: claude-code
- **Context**: During budget removal, the detailed cost model became irrelevant
- **Rationale**: Avoid unnecessary detail and maintenance burden; keep documentation lean
- **Alternatives rejected**: Keeping detailed cost tables, Moving cost model to separate appendix
- **Confidence**: medium

### 3. Perform comprehensive infrastructure reuse analysis before writing new code
- **Source**: claude-code
- **Context**: Need to determine which existing walter-worker components can be reused for self-evolving agent
- **Rationale**: Avoid reinventing the wheel; hooks, analytics DB, knowledge dedup, CLI framework, config adapter, semantic merge, backup mechanisms are all production-ready and can be directly reused
- **Alternatives rejected**: Building all components from scratch, Ignoring existing infrastructure
- **Confidence**: high

### 4. Update all PRD secondary documents (zh.md, en.html, zh.html, design doc) in parallel using workflows
- **Source**: claude-code
- **Context**: After v3 PRD .md was complete, need to synchronize all derived docs
- **Rationale**: Efficiency through parallel updates; ensure consistency across all formats and languages
- **Alternatives rejected**: Updating one by one sequentially, Only updating the main .md and ignoring others
- **Confidence**: high

### 5. Update memory file to mark previously blocked issues as resolved after v3 PRD updates
- **Source**: claude-code
- **Context**: Three blocking issues were identified earlier and have been addressed in v3
- **Rationale**: Maintain accurate project state for future sessions and coordination
- **Alternatives rejected**: Leaving memory file unchanged, Creating new memory file instead of updating
- **Confidence**: high

### 6. Add cal-NqnUgwDcAfKNXHN to EXTRA_CALENDARS seed list in luma-event-scout skill
- **Source**: claude-code
- **Context**: User asked to include Robotics Reading Club event calendar which was not in existing seed list because it is isolated from Bond AI ecosystem
- **Rationale**: To improve event discovery coverage by adding independent calendars that are not cross-linked with existing seed calendars
- **Confidence**: high

### 7. Install zsh-syntax-highlighting and zsh-completions plugins
- **Source**: claude-code
- **Context**: User requested completion of terminal plugins; oh-my-zsh, zsh-autosuggestions already present, but syntax highlighting and enhanced completions missing.
- **Rationale**: Improve terminal usability with command highlighting and better tab completion.
- **Confidence**: high

### 8. Use --dangerously-skip-permissions flag in all Claude proxy commands
- **Source**: claude-code
- **Context**: User rejected the settings.json bypassPermissions approach, explicitly requesting the command-line flag instead.
- **Rationale**: User preference for fully automatic mode; ensures all Claude sessions skip permission prompts without relying on config file.
- **Alternatives rejected**: Setting permissions.defaultMode to bypassPermissions in .claude/settings.json
- **Confidence**: high

### 9. Replace Guild with sqlite-vec + fastembed for vector storage and embedding
- **Source**: claude-code
- **Context**: Advocate review revealed 3 blocking issues in PRD v3 (zero safety guardrails, undefined loop termination, fragile PostToolUse hook layer) which were linked to Guild dependency. A spike (6/6 queries) validated sqlite-vec as a drop-in replacement.
- **Rationale**: Guild introduced fragility and unresolved issues; sqlite-vec is simpler, already integrated via sqlite-vec Python package, and works with existing analytics.db. Reduces complexity and risk.
- **Alternatives rejected**: Guild v2 (rejected due to unresolved blocking issues and fragility), FTS5 (replaced, not suitable for semantic search)
- **Confidence**: high

### 10. Update spec to include sqlite-vec schema and semantic search section
- **Source**: claude-code
- **Context**: Spec previously referenced FTS5 and Guild; needed alignment with new backend.
- **Rationale**: Maintain coherence across docs; new §2.5 describes vec0 DDL, embedding pipeline, and dual retrieval path.
- **Confidence**: high

### 11. Update design to replace all Guild/Lore/Quest references with sqlite-vec equivalents
- **Source**: claude-code
- **Context**: Design had 14+ Guild references including v2 Backend section and architecture diagram.
- **Rationale**: Required for consistency; kept one 'Why not Guild' explanation for historical context.
- **Confidence**: high

### 12. Update impl-plan to use sqlite-vec Python API and fastembed instead of mcp__guild__* commands
- **Source**: claude-code
- **Context**: Implementation plan still referenced Guild CLI and MCP tools.
- **Rationale**: Align with actual implementation; changed header, architecture diagram, Task 0 (pip install), and all task references.
- **Confidence**: high

### 13. Keep 'Why not Guild OSS' rationale in design as historical documentation
- **Source**: claude-code
- **Context**: Design contained a section explaining the rejection of Guild; assistant decided to preserve it.
- **Rationale**: Provides context for future readers on architectural decision rationale.
- **Confidence**: medium

### 14. Restore original dashboard CSS (420 lines) and JS (531 lines), then merge new styles/functions incre
- **Source**: claude-code
- **Context**: Investigation revealed that the CSS and JS were accidentally overwritten in commit 6d3a3dc when using Write tool instead of Edit, causing loss of .lexpand, .tab-bar, .tbtn, expRow(), toggleExp(), goBack(), startAR() and other features
- **Rationale**: Direct restoration from original git history (e86741d) preserves all existing functionality; merging new additions on top avoids silent regressions. Using Edit ensures incremental, safe changes.
- **Alternatives rejected**: Reverting the entire commit and reapplying only new features (would lose other unrelated changes), Continuing with broken files and fixing individually (would leave root cause unaddressed)
- **Confidence**: high

### 15. Create a new 'wrong-history' skill that records past mistakes and injects critical rules into CLAUDE
- **Source**: claude-code
- **Context**: After discovering the root cause (Write instead of Edit), the user requested a mechanism to track and prevent similar errors in the future
- **Rationale**: Formalizing lessons learned as a skill ensures they are not forgotten; injection into CLAUDE.local.md makes rules visible every session without manual recall
- **Alternatives rejected**: Only adding a lesson file (would be passive and easily ignored), Modifying auto-worker rules only (would not cover non-auto-worker sessions)
- **Confidence**: high

### 16. Add two new checks to auto-worker: git diff --stat for >50% line count reduction, and JS function co
- **Source**: claude-code
- **Context**: The existing auto-worker only tested backend and missed front-end CSS/JS regressions; the overwrite went undetected
- **Rationale**: These automated checks will catch accidental overwrites before commit, preventing front-end degradation without requiring visual inspection
- **Alternatives rejected**: Adding full E2E/integration tests for front-end (too heavy, not available), Manual CSS review checklist (would require human attention every commit)
- **Confidence**: medium

### 17. Identify root cause: Claude Code uses 200K token default context window for all models, but DeepSeek
- **Source**: claude-code
- **Context**: User reported context percentage bar hitting 100% quickly when using DeepSeek API in Claude Code
- **Rationale**: Different models have different context window sizes; Claude Code's default assumption of 200K leads to incorrect percentage calculation for models with larger windows
- **Confidence**: high

### 18. Use `[1M]` suffix on model name in ANTHROPIC_MODEL environment variable to override context window s
- **Source**: claude-code
- **Context**: After identifying root cause, assistant suggested adding `[1M]` suffix to model name in user's shell configuration
- **Rationale**: Claude Code documentation indicates that appending `[1M]` (camelCase) to model ID tells the tool to use 1M token context window; the suffix is stripped from API requests
- **Alternatives rejected**: Using settings.json env config (found less flexible)
- **Confidence**: medium

### 19. Correct suffix from `[1M]` to `[1m]` (lowercase) after observing it didn't work
- **Source**: claude-code
- **Context**: After restarting Claude Code with `[1M]` suffix, debug log showed context window was still 200K; further research revealed Claude Code requires lowercase `[1m]`
- **Rationale**: Official Claude Code documentation specifies `[1m]` (lowercase) for context window override; uppercase is not recognized
- **Confidence**: high

### 20. Apply `[1m]` suffix to all third-party models: GLM-5.2, DeepSeek V4 Pro, DeepSeek V4 Flash, Gemini 2
- **Source**: claude-code
- **Context**: User has multiple models and wants consistent context bar behavior
- **Rationale**: All these models have 1M token context windows (confirmed via web search), so applying the same suffix ensures correct percentage calculation across all models
- **Confidence**: high

### 21. Set default export ANTHROPIC_MODEL in .zshrc to ensure consistent value when no alias is used
- **Source**: claude-code
- **Context**: User has default export ANTHROPIC_MODEL at top of .zshrc that was not updated; this could cause issues if command doesn't go through proxy function
- **Rationale**: Ensure any invocation of claude command uses the correct model with suffix, avoiding inconsistent context window behavior
- **Alternatives rejected**: Leaving default export unchanged (would cause inconsistency)
- **Confidence**: high

### 22. Temporarily add debug logging to statusline-command.sh to verify context window size, then remove af
- **Source**: claude-code
- **Context**: To diagnose why `[1M]` didn't work, assistant added debug log to capture actual context_window_size sent by Claude Code
- **Rationale**: Debug logging provided concrete evidence that context window was still 200K, leading to discovery of case sensitivity issue
- **Confidence**: high

### 23. Use systematic debugging skill to find root cause instead of guessing
- **Source**: claude-code
- **Context**: User reported evolution dashboard empty; prior attempts may have been incomplete
- **Rationale**: Systematic debugging ensures root cause identification before any fix, preventing symptom fixes
- **Alternatives rejected**: Attempting to refill data directly, Guessing at missing configuration
- **Confidence**: high

### 24. Investigate analytics database and knowledge extraction pipeline
- **Source**: claude-code
- **Context**: Need to understand why evolution data is missing
- **Rationale**: Evolution dashboard queries multiple data sources (mem0, knowledge table, pending skills); checking each reveals the pipeline state
- **Alternatives rejected**: Only checking one source (e.g., mem0), Assuming permission issues
- **Confidence**: high

### 25. Identify that phase 2 (knowledge extraction) was never executed at scale
- **Source**: claude-code
- **Context**: Found 568 sessions imported but only 25 session summaries and 0 mem0 entries
- **Rationale**: The `coworker memory train` command implements the full extraction but was never invoked manually, leaving all data sources empty
- **Alternatives rejected**: Assuming bug in dashboard queries, Assuming data import failed
- **Confidence**: high

### 26. Offer to run `coworker memory train` to fill evolution data
- **Source**: claude-code
- **Context**: After root cause identified, next logical step given user needs
- **Rationale**: Running the command will populate mem0, knowledge table, and pending skills, making evolution dashboard functional
- **Alternatives rejected**: Manual data entry, Rewriting dashboard queries to ignore missing data
- **Confidence**: high

### 27. Change auto_approve default from true to false
- **Source**: claude-code
- **Context**: Devil's advocate review revealed high unsafe rate (65.5%) for auto-created skills and security risks in self-evolving agents.
- **Rationale**: Defaults should protect non-technical users; auto_approve: true would automatically activate potentially dangerous skills. Changing to false adds a pending queue and review step while still allowing automation.
- **Alternatives rejected**: Keep auto_approve: true (exposes users to risk), Remove auto-approval entirely (rejected because it would break workflow for advanced users)
- **Confidence**: high

### 28. Replace CLAUDE.md with CLAUDE.local.md in core loop and state machine descriptions
- **Source**: claude-code
- **Context**: PRD was inconsistent: Section 3.6 correctly referenced CLAUDE.local.md for memory snapshots, but diagrams and Section 2.1 incorrectly referenced CLAUDE.md as auto-update target.
- **Rationale**: CLAUDE.md is a team-shared file that should not be automatically modified by the agent. Only the personal CLAUDE.local.md should be auto-updated. This is a safety and clarity fix.
- **Alternatives rejected**: Keep CLAUDE.md and add a note to commit changes (rejected because team files should not be auto-modified), Use a separate memory file entirely (rejected because CLAUDE.local.md is already established)
- **Confidence**: high

### 29. Add post-session skill creation trigger at SessionStop hook
- **Source**: claude-code
- **Context**: User insight that the session summary already runs a full-context LLM call, which can also identify reusable workflows to create as skills.
- **Rationale**: Zero additional cost (piggybacks on existing summary), accesses full session context for better pattern recognition, complements existing in-session trigger which only sees individual tasks.
- **Alternatives rejected**: Only use in-session trigger (misses cross-task patterns), Add a separate dedicated skill discovery step (costly and redundant)
- **Confidence**: medium

### 30. Add new shell function claude-deepseek-flash using deepseek-v4-flash model
- **Source**: claude-code
- **Context**: User requested adding a deepseek flash v4 model option to claude code in zshrc
- **Rationale**: Follows existing naming and configuration pattern for model aliases (e.g., claude-deepseek for deepseek-v4-pro), minimal change to satisfy user request
- **Confidence**: high
