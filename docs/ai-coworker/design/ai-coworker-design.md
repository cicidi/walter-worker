# ai-coworker Design

**Document Version:** 1.0  
**Last Updated:** 2026-07-25  

## Change Log

| Date | Version | Changes |
|------|---------|---------|
| 2026-06-11 | 0.1 | Initial commit; unified dev environment structure |
| 2026-06-12 | 0.2 | Analytics listener & dashboard design finalized |
| 2026-06-23 | 0.5 | Big refactor: `global/` removed, skills consolidated, naming scheme change |
| 2026-07-02 | 0.6 | Three-layer CLAUDE.md architecture introduced |
| 2026-07-10 | 0.7 | CLAUDE.md harness optimization (95→60 lines) |
| 2026-07-17 | 0.9 | Skills moved to `~/.claude/skills/`; doc types consolidated to 9 |
| 2026-07-25 | 1.0 | Memory substrate (mem0 + DeepSeek), auto-worker, dashboard extensions, 96% test coverage |

---

## 1. High-Level Architecture

The project – **ai-coworker** – is a **context management system** for AI coding assistants (Claude Code, OpenCode). It is **not a development tool** but a framework that orchestrates skills, contextual configuration, analytics, and memory to guide AI behaviour.

```
┌─────────────────────────────────────────────────────────┐
│                    ai-coworker                          │
│                                                         │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │ CLAUDE.md   │  │   Skills     │  │   Analytics     │ │
│  │ (3 layers)  │  │ (in skills/) │  │   Listener + DB │ │
│  │             │  │  (CLI/agent) │  │                 │ │
│  │ Global      │  │              │  │ SQLite schema   │ │
│  │ Project     │  │ Manifest-    │  │ Dashboards      │ │
│  │ Local       │  │ driven       │  │ (Flask webapp)  │ │
│  │ (override)  │  │ install      │  │                 │ │
│  └─────────────┘  └──────────────┘  └────────────────┘ │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │          Memory Substrate (mem0 + DeepSeek)       │   │
│  │   Capture → Engine → Injection → Curator → Train  │   │
│  └──────────────────────────────────────────────────┘   │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │          Auto-Worker (Claude SDK Agent)           │   │
│  │   Safety gates, metrics, skill CLI integration   │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Key Architectural Components

- **Skills Directory** – All skills live under `skills/` at repository root. Each skill has an `SKILL.md` (frontmatter with dual-format for Claude Code + OpenCode). Skills are installed into `~/.claude/skills/` via a manifest-driven install/uninstall process.
- **Three-Layer CLAUDE.md** – A layered configuration system: `Global` (system-wide), `Project` (per-repo), `Local` (user-specific overrides). This provides deterministic context inheritance.
- **Analytics Listener & Dashboard** – A background daemon that imports sessions from OpenCode/Claude Code (JSONL), deduplicates, and stores metadata in SQLite. A Flask web dashboard visualizes file operations, skill usage, costs, efficiency, etc.
- **Memory Substrate** – Uses `mem0` as the foundation for long-term memory, with a DeepSeek LLM client for semantic operations. The pipeline is: capture → engine → injection → curator → training.
- **Auto-Worker** – A Claude SDK agent that can execute skills autonomously with safety gates, metric tracking, and CLI integration.

---

## 2. Design Patterns

### 2.1 Layered Configuration (Context Inheritance)
- **Pattern:** Chain of Responsibility / Override Chain
- **Rationale:** Global configuration provides defaults (e.g., user conventions), Project overrides for team-specific rules, Local for personal tweaks. This avoids duplication and allows per-project customization.
- **Evidence:** Commit `81e946e8` introduced "three-layer CLAUDE.md architecture (Global → Project → Local)". Later simplified to 95→60 lines while preserving structure.

### 2.2 Skill-Based Modularity
- **Pattern:** Plugin / Module system
- **Rationale:** Skills are self-contained units with a defined interface (`SKILL.md`). They can be added, removed, or updated independently. The skill directory is public and version-controlled.
- **Evidence:** Skills moved to public `skills/` directory (`c4577dbf`). Skills renamed to a consistent naming scheme (`b22a2b8c`). Skills installed to `~/.claude/skills/` (`b177e61f`).

### 2.3 Manifest-Driven Install
- **Pattern:** Declarative Installation
- **Rationale:** A manifest defines ownership, hooks, and dependencies. Uninstall is safe because the system tracks what it installed.
- **Evidence:** Commit `4867eb69` "manifest-driven install/uninstall with hook-ownership safety".

### 2.4 Event-Driven Analytics Import
- **Pattern:** Observer / Listener
- **Rationale:** The analytics daemon watches for new session files (e.g., OpenCode JSONL) and imports them incrementally. Checkpoints are stored in SQLite.
- **Evidence:** Commits `cdf88052` (analytics auto-import daemon with checkpoint), `6a642a28` (use DB as checkpoint).

### 2.5 Content Hash-Based Change Detection
- **Pattern:** Immutable / Hash comparison
- **Rationale:** To detect skill renames without relying on `--delete` operations, content hashes are compared.
- **Evidence:** Commit `7d90e61c` "skill sync without --delete, detect renames via content hash".

### 2.6 State Files with Auto-Timestamp
- **Pattern:** Snapshot / Timestamped state
- **Rationale:** Each task gets a state file under `docs/state/` with an automatic timestamp to prevent session collisions.
- **Evidence:** Commits `432536cc` (move state files to `docs/state/`), `c1dfa568` (auto-timestamp state files).

### 2.7 Topic-Based Documentation Convention
- **Pattern:** Classification by type (9 types)
- **Rationale:** Documents are organized by initiative (topic) and use suffix-based types (`.hld.md`, `.lld.md`, `.evidence.md`, etc.) to reduce fragmentation.
- **Evidence:** Multiple merges and refactors consolidating from 12+ types down to 9 (`0906289b`, `b8e4bbe0`, `bc9f81ac`, `9729e37d`).

---

## 3. Technology Choices and Rationale

| Technology | Decision | Rationale |
|------------|----------|-----------|
| **SQLite** | Analytics database | Zero-config, file-based, sufficient for single-user metrics and session metadata. Schema was designed to support dashboard views (skills, knowledge, session summaries). |
| **DeepSeek API** | LLM for memory dedup and semantic operations | Chosen for low cost and good performance for embedding/knowledge tasks. API key requested during `init` and stored in `.local_config.yaml`. |
| **mem0** | Long-term memory substrate | Provides out-of-the-box memory retrieval and storage; used as foundation for the memory pipeline (capture → engine → injection → curator → training). |
| **Flask** | Dashboard backend | Lightweight, easily embeddable; dashboard was added as part of the analytics listener component. |
| **tmux** | Status bar integration (with worktree support) | Many developers use tmux; worktree support was added to handle multiple active repositories. |
| **Bash 3.2** | Installation scripts | Widely available on macOS; avoided `declare -A` to maintain compatibility (`7476a7b3`). |
| **pytest** (inferred) | Testing framework | 300+ tests across 10 modules achieved 96% coverage. |

---

## 4. Data Flow and Service Topology

### 4.1 Session Import Pipeline
```
OpenCode/Claude Code session JSONL
     │
     ▼
Analytics Listener Daemon
     │  (checkpoint stored in SQLite)
     │
     ▼
SQLite Database
  - sessions (metadata only, not raw messages)
  - file_ops (file reads per session, op type)
  - skills (skill usage)
  - knowledge (semantic dedup via DeepSeek)
  - session_summaries (aggregated)
     │
     ▼
Dashboard (Flask webapp)
  Views: session monitor, file ops, skill usage, unified timeline,
         projects, hotspots, errors, memory control,
         cost/token, model/IDE, efficiency, data quality
```

### 4.2 CLAUDE.md Loading Order
```
Global CLAUDE.md (user home, system-wide defaults)
     │
     ▼
Project CLAUDE.md (repo root, project-level rules)
     │
     ▼
Local CLAUDE.md (user-local overrides)
     │
     ▼
Final context passed to AI assistant
```

### 4.3 Skill Discovery and Installation
```
Skills in skills/ directory (version-controlled in repo)
     │  (install via manifest-driven script)
     ▼
~/.claude/skills/ (installed location, used by Claude Code and OpenCode)
     │
     ▼
AI assistant reads SKILL.md frontmatter to activate skill
```

### 4.4 Memory Pipeline
```
Capture Layer (collects interactions, file changes)
     │
     ▼
Engine Layer (processes, deduplicates via DeepSeek API)
     │
     ▼
Injection Layer (injects relevant memories into context)
     │
     ▼
Curator Layer (validates and organizes)
     │
     ▼
Training Layer (updates mem0 embeddings)
```

---

## 5. Key Trade-Offs and Why Specific Approaches Were Chosen

### 5.1 Removed 8-Stage Pipeline in Favor of Simpler Workflow
- **Decision:** Replaced an 8-stage pipeline with a 5-stage workflow, then later removed the pipeline entirely (`455d9e99`, `5d56b85c`).
- **Rationale:** The multi-stage development pipeline was overly bureaucratic for AI assistants. A simpler "Development Loop" (suggest next actions, compact state) proved more effective.
- **Impact:** Reduced CLAUDE.md from 95 to 60 lines; smoother context load.

### 5.2 Global vs. Project-Level Storage for Initiatives
- **Decision:** Initiatives migrated from global (user-wide) to project-level storage (`2a9e69ea`).
- **Rationale:** Project-specific initiatives avoid cluttering the global context and allow each repo to define its own priorities.
- **Impact:** Initiatives are now scoped per repository; global initiatives still exist for system-level concerns.

### 5.3 Session Metadata Only – Not Raw Messages
- **Decision:** Analytics stores only session metadata, not full raw messages (`8015aad1`).
- **Rationale:** Raw messages are bulky and privacy-sensitive; metadata (file ops, skill usage, duration) is sufficient for dashboard analytics. Full messages can be referenced from the original session files.
- **Impact:** Database remains small; incremental imports are fast.

### 5.4 DB as Checkpoint vs. File-Based Position
- **Decision:** Use SQLite as the checkpoint for analytics import instead of a file-based offset (`6a642a28`).
- **Rationale:** DB checkpoint allows incremental updates and easy query of what has been imported. Also supports session dedup via manifest checks.
- **Impact:** Simpler consistency; import daemon is restart-safe.

### 5.5 Removed Budget Concept from Autonomous Agent PRD
- **Decision:** Budget flags and "Budget exhausted" conditions were removed; replaced by a hard 12-hour time limit (`claude-code` entry 2026-07-24).
- **Rationale:** Budgets added complexity without clear benefit; a simple timeout is more robust and understandable. Cost tracking moved to analytics (non-enforcing).
- **Impact:** Simplified safety model; termination is now based on completion, goal achievement, or max-time.

### 5.6 Consolidation of Document Types from 10+ to 9
- **Decision:** Merged `compare` into `research`, `evidence` as suffix, `hld/lld` into `design`, `why-this` into `decision-history` (`0906289b`, `b8e4bbe0`, `bc9f81ac`, `9729e37d`).
- **Rationale:** Too many document types caused fragmentation; a simpler type system with suffix conventions makes the docs easier to navigate and maintain.
- **Impact:** Docs are now organized by 9 types with consistent naming (initiative-doc-type.md).

### 5.7 Skills Migration from Global/Personal to Public `skills/`
- **Decision:** All skills moved to `skills/` directory, personal skills removed (`c7b2ea3f`, `1989bb09`).
- **Rationale:** Skills should be shared and version-controlled as part of the project. The skill-factory (separate repository) holds general-purpose skills; ai-coworker retains 5 core skills.
- **Impact:** Reduced code duplication; clear boundary between core and external skills.

### 5.8 Dual-Format for Claude Code + OpenCode
- **Decision:** Skill frontmatter supports both Claude Code and OpenCode formats (`6055e4b9`).
- **Rationale:** Both AI assistants are used; maintaining dual-format ensures compatibility without forking.
- **Impact:** Single skill definition works across platforms; minor complexity in frontmatter parsing.

---

*This design document is based solely on decisions recorded in the project history up to 2026-07-25.*