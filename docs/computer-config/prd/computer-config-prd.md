# computer-config — Product Requirements Document (PRD)

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-08-01 | 0.1.0 | Initial draft |
| 2026-08-01 | 0.2.0 | Post devil-advocate review: US-4 "one-click install" satisfied via menu option "3) Both" in spec; target model confirmed DeepSeek V4 Pro |

---

## 1. Background & Goals

The user has a highly customized development environment: a Claude Code statusline
(4-line colored dashboard) + a tmux Benjamin Blue theme + the ai-coworker
framework. These assets are **scattered in the home directory, under no version
control**, and ai-coworker's install script deploys a simple tmux theme to ALL
users who install it (pollution).

**Goals**:
1. Create an independent `claude-tmux-config` project that consolidates all
   personal Claude + tmux presentation assets, with its own install-confirmation
   script, zero impact on other users.
2. Strip the presentation layer out of ai-coworker so it becomes a pure
   framework, never touching any user's terminal skin.

**Non-goals**:
- ❌ Do NOT strip ai-coworker core (hooks/skills/MCP/context/memory)
- ❌ Do NOT auto-install the claude-tmux Rust binary
- ❌ Do NOT do macOS adaptation (Linux-only)

---

## 2. User Stories

| ID | As a... | I want... | So that... |
|----|---------|----------|------------|
| US-1 | environment maintainer | all Claude/tmux assets versioned & consolidated | trackable, reversible, shareable |
| US-2 | environment maintainer | explicit confirmation on install | no accidental installs, no damage to existing config |
| US-3 | ai-coworker user | installing ai-coworker doesn't force my personal theme | my terminal skin is my choice |
| US-4 | new user | one-click install of the full statusline+theme | quickly get the same experience |
| US-5 | environment maintainer | one-click clean uninstall | no orphaned files |

---

## 3. Requirements

### 3.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Create claude-tmux-config repo with install.sh / uninstall.sh / assets/ | P0 |
| FR-2 | Adopt statusline-command.sh, parameterize 3 hardcoded paths | P0 |
| FR-3 | Adopt wrap-statusline.py | P0 |
| FR-4 | Adopt status_info.sh (simple version) | P0 |
| FR-5 | Extract Benjamin Blue theme into a standalone file | P0 |
| FR-6 | install.sh 0/1/2 menu + y/N confirm, default N | P0 |
| FR-7 | Deploy statusline to `~/.claude/statusline/` + write statusLine to settings.json | P0 |
| FR-8 | Deploy tmux theme + status_info.sh (idempotent, with backup) | P0 |
| FR-9 | uninstall.sh manifest-driven clean removal | P0 |
| FR-10 | Remove Step 16 + setup/status_info.sh from ai-coworker | P0 |
| FR-11 | ai-coworker core tests stay green | P0 |

### 3.2 Non-functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Idempotent: repeated installs produce no side effects |
| NFR-2 | Safe: backup before mutation, atomic writes |
| NFR-3 | Performance: statusline refresh <100ms |
| NFR-4 | Portable: parameterized paths, no machine-specific values |
| NFR-5 | Fully isolated from ai-coworker, no interference |

---

## 4. Scope

**In scope**: claude-tmux-config project creation, adoption of 4 assets, install
confirmation, ai-coworker strip of Step 16 + status_info.sh.

**Out of scope**: claude-tmux binary install, macOS support, rich status_info.sh
deployment (optional enhancement), ai-coworker dashboard extraction (future,
separate effort).

---

## 5. Acceptance Criteria

1. `claude-tmux-config` repo created, assets complete, paths parameterized
2. `install.sh` runs: 0/1/2 menu + y/N confirm, default N
3. After install: `~/.claude/statusline/` two files in place, settings.json has `statusLine`
4. After install: `~/.tmux/conf.d/benjamin-blue.tmux` in place (or skipped if existing inline color)
5. `uninstall.sh` cleanly removes all traces
6. After ai-coworker strip: install.sh no longer touches tmux, core tests all green

---

## 6. Milestones

| Milestone | Content | Depends on |
|-----------|---------|------------|
| M1 | claude-tmux-config repo + asset adoption | — |
| M2 | install.sh + uninstall.sh + confirmation mechanism | M1 |
| M3 | ai-coworker strip + test updates | M1 |
| M4 | Doc suite complete + index update | M1-M3 |
