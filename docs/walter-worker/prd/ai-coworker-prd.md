```markdown
# walter-worker PRD

**Product Requirements Document**

*Version: 1.0 (Reconstructed from development history up to 2026-07-25)*

---

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-07-25 | 1.0 | Initial PRD reconstruction from development decisions. Includes self-evolving-agent phase (memory, auto-worker, dashboard v2). |

---

## 1. Project Overview and Goals

### 1.1 Overview
Ai-coworker is a **context manager** for AI coding assistants (Claude Code, OpenCode). It provides a structured development environment that enhances the capabilities of these assistants through:

- A skill-based plugin system for reusable commands and workflows.
- Automated analytics and session import pipeline to collect telemetry from AI coding sessions.
- A dashboard for visualizing productivity, costs, and memory usage.
- A memory subsystem (mem0 + DeepSeek) for persistent learning across sessions.
- An autonomous agent (auto-worker) that can execute long-running tasks with safety guarantees.
- A three-layer CLAUDE.md architecture (Global → Project → Local) for adaptive configuration.

The project is **not** a standalone development tool; it is designed to be used *inside* an AI assistant environment (such as Claude Code or OpenCode). Skills are written in Markdown frontmatter format and are consumed by the AI.

### 1.2 Goals
1. **Improve AI assistant productivity** by providing a reusable skill library and automatic context injection.
2. **Provide actionable analytics** – track session data, file operations, skill usage, costs, and efficiency.
3. **Enable persistent memory** – allow the AI to recall past sessions and learn from experience.
4. **Support autonomous task execution** – run multi-step workflows with self-healing and safety checks.
5. **Maintain high code quality** – ≥96% test coverage, hermetic installs, manifest-driven lifecycle.

---

## 2. Target Users / Use Cases

### 2.1 Primary Users
- **AI power users** who run Claude Code or OpenCode daily and want to optimise their workflow.
- **Developers** using AI coding assistants in complex, multi-project environments (including git worktrees).
- **Teams** that want to standardise AI behaviour across projects (via global / project CLAUDE.md layers).

### 2.2 Use Cases

| Use Case | Description | Decisions Trace |
|----------|-------------|-----------------|
| **Project onboarding** | Run `coworker init` to auto-detect language, dependencies, IDE, and generate a tailored CLAUDE.local.md. | `feat: auto-scan in coworker init` |
| **Session analytics** | Automatically import Claude Code JSONL sessions and OpenCode logs, deduplicate, and store in SQLite. View via dashboard. | `feat: analytics auto-import daemon`, `feat: import Claude Code native JSONL sessions` |
| **Skill management** | Install external skills with license check (`meta-import-skill`), uninstall with safety, sync across repos via content hash. | `feat: add meta-import-skill`, `fix: skill sync without --delete, detect renames via content hash` |
| **Bug tracking** | Use `bug-report` to create issues in any repo via project catalog; use `bug-hunt` to collect evidence and reason. | `refactor: merge bug-create into bug-report`, `refactor: bug-hunt — collect first, then reason` |
| **Self-healing** | Automatic hooks and traces that detect and fix configuration drift in CLAUDE.md files. | `feat: rewrite self-heal + self-analyze` |
| **Memory recall** | AI can query past session summaries, decisions, and knowledge chunks via `session-memory` skill. | `feat: add session-memory skill` |
| **Autonomous agent** | Deploy the auto-worker skill to run long tasks (e.g., “implement feature X”) with safety gates, timeouts, and progress metrics. | `feat: add auto-worker skill`, `feat: spec-compliant auto-worker — Claude SDK agent, safety gates` |
| **Documentation organization** | Use `doc-organize` skill to classify documents into 9 types (decision, design, research, etc.) and generate INDEX.md. | `refactor: reorganize docs/ using doc-organize conventions (9 types)` |

---

## 3. Core Features and Requirements

### 3.1 Initialization and Configuration (`coworker init`)

| # | Feature | Description | Source Decisions |
|---|---------|-------------|------------------|
| F1 | **Auto-scan project** | Detect language, dependencies, IDE, and generate CLAUDE.local.md with initiative and config. | `feat: auto-scan in coworker init — detect language, deps, IDE, generate config` |
| F2 | **DeepSeek API key** | Prompt user for DeepSeek API key during init; store in `.local_config.yaml`. | `feat: ask for DeepSeek API key during init, save to .local_config.yaml` |
| F3 | **Force upgrade** | `--force` flag to overwrite existing project CLAUDE.md. | `feat: add --force flag to init for upgrading project CLAUDE.md` |
| F4 | **Three-layer CLAUDE.md** | Global (shared), Project, Local (per-working-copy) architecture. Hooks and patterns injected. | `feat: three-layer CLAUDE.md architecture (Global → Project → Local)` |

### 3.2 Skills System

Skills are Markdown files with frontmatter (coworker-{category}-{name}) that define reusable commands for the AI assistant. They live in `skills/` directory and are deployed to `~/.claude/skills/`.

| # | Feature | Description | Source Decisions |
|---|---------|-------------|------------------|
| F5 | **Skill naming scheme** | `coworker-{category}-{name}` format. | `refactor: rename all skills to new naming scheme` |
| F6 | **Dual frontmatter** | Support both Claude Code and OpenCode format (v1). | `feat: upgrade skill frontmatter to Claude Code + OpenCode dual format` |
| F7 | **Manifest-driven install/uninstall** | Use manifest to track hook ownership and safe uninstall. | `fix: manifest-driven install/uninstall with hook-ownership safety` |
| F8 | **External skill import** | `meta-import-skill` – import from URL with license check and auto-install. | `feat: add skill meta-import-skill — import external skills with license check and auto-install` |
| F9 | **Skill sync** | Sync skills across repos without `--delete`, detect renames via content hash. | `fix: skill sync without --delete, detect renames via content hash