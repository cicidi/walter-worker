# computer-config — Complete Technical Specification

## Change Log

| Date | Version | Change |
|------|---------|--------|
| 2026-08-01 | 0.1.0 | Initial draft — expanded from migration design doc to full configuration spec |

---

## 1. Overview

This specification describes the user's complete development environment
customizations: the **Claude Code statusline**, the **tmux terminal theme**, and
the **ai-coworker role boundary**. Goals:

1. Consolidate the Claude + tmux presentation assets (currently scattered in the
   home directory, under no version control) into an independent project
   `claude-tmux-config`, with its own install confirmation script, zero impact
   on other users.
2. Strip the presentation layer out of ai-coworker so it remains a pure
   framework (context/skills/analytics/memory).

> This document is the **spec** (defines "what it is"). Companion docs:
> - `docs/computer-config/prd/computer-config-prd.md` — requirements (what we want)
> - `docs/computer-config/impl-plan/computer-config-impl-plan.md` — implementation plan (how to build)
> - `docs/computer-config/test-plan/computer-config-test-plan.md` — test strategy (how to verify)

---

## 2. Claude Code Complete Configuration

### 2.1 Architecture Overview: CCR Proxy Routing

Claude Code natively talks only to the Anthropic API. **claude-code-router (CCR)**
is a local proxy (`127.0.0.1:3456`) that presents an Anthropic-compatible API
surface while routing requests to non-Anthropic models (DeepSeek V4 Pro).

**Why**: DeepSeek V4 Pro output costs ~`$0.87/1M` tokens vs Claude Sonnet's
`$15/1M` (~17x cheaper); DeepSeek also offers a 1M-token context window (5x
Claude's 200k). The user has a DeepSeek subscription and wants to keep Claude
Code's full feature set (thinking/tool-use/streaming) while using DeepSeek as
the primary model.

**How**: Three env vars (`ANTHROPIC_BASE_URL` / `ANTHROPIC_API_BASE_URL` /
`CLAUDE_AGENT_API_BASE_URL`) all point at CCR; `apiKeyHelper` points at CCR's key
helper. Claude Code sees a standard Anthropic endpoint; CCR does the internal
request translation (Anthropic Messages → OpenAI-compatible → DeepSeek, and back).

### 2.2 settings.json Complete Fields

Main config at `~/.claude/settings.json`, 11 top-level keys:

| Key | Value | Purpose |
|-----|-------|---------|
| `apiKeyHelper` | `/home/cicidi/.claude-code-router/bin/ccr-claude-code-api-key-default-claude-code` | Routes API key requests through CCR, returns Anthropic-format keys regardless of backend model |
| `env.ANTHROPIC_BASE_URL` | `http://127.0.0.1:3456` | Points at local CCR proxy |
| `env.ANTHROPIC_API_BASE_URL` | `http://127.0.0.1:3456` | Same (different Claude Code internals read different vars) |
| `env.CLAUDE_AGENT_API_BASE_URL` | `http://127.0.0.1:3456` | Same |
| `env.ANTHROPIC_MODEL` | `DeepSeek/deepseek-v4-pro` | Actual model name CCR passes to DeepSeek API |
| `env.CCR_CLAUDE_CODE_MODEL` | `DeepSeek/deepseek-v4-pro` | Same |
| `env.CODEXL_CLAUDE_CODE_MODEL` | `DeepSeek/deepseek-v4-pro` | Same |
| `env.CLAUDE_CODE_ENABLE_GATEWAY_MODEL_DISCOVERY` | `1` | Tells Claude Code a gateway (CCR) exists; query for available model listings |
| `model` | `anthropic/claude-ccr-h446...f6c617368[1m]` | CCR-wrapped model ID; `[1m]` suffix signals 1M-token context window |
| `permissions.defaultMode` | `bypassPermissions` | Skips permission prompt system; real safety net is hook infra audit logs |
| `permissions.allow` | `Bash(*)`, `Edit(*)`, `Read(*)`, ... | Allow-list (no-op under bypass mode) |
| `hooks` | 4 events + commands | UserPromptSubmit / PreToolUse / PostToolUse / Stop |
| `statusLine` | `{type: command, command: bash .../statusline-command.sh, padding: 0}` | 4-line statusline rendering |
| `enabledPlugins` | 12 plugins | superpowers/frontend-design/code-review/github/playwright/context7/feature-dev/claude-md-management/skill-creator/discord/telegram/claude-hud |
| `extraKnownMarketplaces` | claude-hud | Installs claude-hud plugin from jarrodwatts/claude-hud |
| `alwaysThinkingEnabled` | `true` | Forces extended thinking mode |
| `skipDangerousModePermissionPrompt` | `true` | Suppresses confirmation prompt when bypassPermissions is active |

**Key semantics**: `bypassPermissions` means all file/browser/bash operations are
pre-approved. The real safety model relies on hook infrastructure logging
everything for audit, not the permission prompt system.

---

## 3. Claude Code Statusline

### 3.1 Mechanism

`statusLine.type: command` → on each refresh, invokes
`bash ~/.claude/statusline-command.sh`, piping session JSON to stdin. The script
computes real costs (bypassing CCR's wrong pricing), context percentage (using the
actual model window, not Anthropic's 200k), turn count, git diff stats, initiative
detection, and ccusage integration. Output is piped through `wrap-statusline.py`
for terminal-width-aware wrapping.

### 3.2 Four Output Lines

| Line | Content | Coloring |
|------|---------|----------|
| 1 | project + initiative + tmux session + user@host + start time | forest-green labels / teal values / orange initiative |
| 2 | model + effort + context bar `[████░░░]` + real cost + turns + elapsed + avg_api | yellow labels / values color-coded by semantics |
| 3 | branch + claude_change (+N/-M) + github_change (+N/-M) + last commit | green labels / add-del red-green |
| 4 | current folder path | forest-green 📂 |

### 3.3 Benjamin Blue Palette (256-color approximations)

| Color | Hex | 256-color | Role |
|-------|-----|-----------|------|
| Crayon Yellow | `#F2C94C` | `38;5;220` | cursor / highlights / warnings / emphasis |
| Forest Green | `#5F8D4E` | `38;5;71` | success / pass / additions / confirmations |
| Clay Orange | `#D98A3A` | `38;5;172` | primary accent / headings / links / notices |
| Brick Red | `#B95547` | `38;5;131` | errors / failures / deletions / critical alerts |
| Deep Ocean | `#102D46` | `38;5;17` | background / calm sections |

Supplementary (variable values): lavender `183`, peach `216`, mint `121`, sky `117`,
rose `211`, gold `214`, coral `209`, grape `141`, teal `43`, silver `250`.

### 3.4 Threshold Logic

| Metric | Green | Yellow | Red |
|--------|-------|--------|-----|
| Context usage | <50% | 50-80% | >80% |
| Cost | <$1 | $1-3 | >$3 |
| Effort level | low | medium/high | max |
| Elapsed | <30min | 30-60min | >1h |
| avg_api | <3s | 3-8s | >8s |

### 3.5 Real Cost Calculation (compute_real_cost)

**Why**: CCR wraps non-Claude models under ids it cannot price, so
`.cost.total_cost_usd` is wrong by up to ~35x (CCR bills at Claude rates `$3/$15`,
but actually routes DeepSeek tokens at `$0.87/1M`).

**How**:
1. Read `.cost.total_cost_usd` from transcript JSONL as baseline
2. Parse transcript, group tokens by model family (dspro/dsflash/glm5x/claude)
3. All-Claude session → use Claude Code's exact number
4. Mixed/non-Claude session → multiply raw token counts × real rates

Price table (USD/1M tokens: input / cache-write / cache-read / output):

| Family | input | cache-write | cache-read | output |
|--------|-------|-------------|------------|--------|
| glm5x | 1.40 | 0 | 0.26 | 4.40 |
| dsflash | 0.14 | 0.14 | 0.0028 | 0.28 |
| dspro | 0.435 | 0.435 | 0.003625 | 0.87 |
| claude | 3.0 | 3.75 | 0.30 | 15.0 |

### 3.6 Context Window Detection

**Why**: Claude Code always reports 200k (Anthropic's window), but DeepSeek is 1M.

**How**: Parse `model_id`:
- Contains `[2m]`/`[2M]` → 2,097,152
- Contains `[1m]`/`[1M]` → 1,048,576
- Contains deepseek/glm/qwen → 1,048,576
- Contains claude → 200,000
- Other → 200,000 (fallback)

### 3.7 Turn Counter

Persists in `~/.claude/turn-counter-{session_id}.json` (`{prompt_id, count, start_time}`).
Seeds from transcript on first run (to catch already-happened turns). Increments
only when `prompt_id` changes (new user message).

### 3.8 ccusage Cache

`~/.claude/ccusage-cache.json`, refreshed every 120s via `ccusage blocks --json`,
as a secondary cost source. Avoids spawning ccusage on every statusline tick.

### 3.9 Initiative Detection

Searches `CLAUDE.local.md` for `<!-- INITIATIVE:<name> START -->`, walking up from
workspace to project root to `$HOME`.

### 3.10 wrap-statusline.py

Python 3, no dependencies. Detects terminal width (`$COLUMNS` → `tput cols` →
fallback 120), wraps at word boundaries preserving ANSI SGR escape sequences.
Hard-breaks at width if no space found.

### 3.11 Hardcoded Paths (to parameterize)

```
:150  turn_counter_file="$HOME/.claude/turn-counter-${session_id}.json"
:199  cache_file="$HOME/.claude/ccusage-cache.json"
:370  printf ... | python3 ~/.claude/wrap-statusline.py
```

Dependencies: `jq`, `bc`, `python3`, `git`, `tmux` (`ccusage` optional, degrades
gracefully). Contains Linux-specific commands `stat -c %W`, `hostname -s`
(macOS-incompatible).

---

## 4. tmux Complete Configuration

### 4.1 .tmux.conf (34 lines)

| Section | Config | Why |
|---------|--------|-----|
| Truecolor | `default-terminal tmux-256color` + `terminal-overrides "*256col*:Tc"` etc. | Render ANSI 256-color correctly inside tmux panes |
| Passthrough | `allow-passthrough on` + `update-environment COLORTERM` | Support truecolor passthrough |
| claude-tmux binding | `bind-key C-c display-popup -E -w 80 -h 30 "~/.cargo/bin/claude-tmux"` | Ctrl+C prefix opens 80x30 Claude Code TUI popup |
| Mouse/clipboard | `set -g mouse on` / `set-clipboard on` | Mouse support + system clipboard |
| status-style | `bg=#102D46,fg=#EAE7DD` | Benjamin Blue deep-ocean bg + warm off-white text |
| message-style | `bg=#F2C94C,fg=#102D46` | Yellow bg + deep-ocean text, high contrast |
| pane-active-border | `fg=#F2C94C` | Active pane border yellow, draws the eye |
| status-left | `#{session_name} + green ●` | Session name yellow + forest-green activity dot |
| status-right | `📂 + $(~/.tmux/scripts/status_info.sh)` | Folder icon + dynamic status info |
| window-status-current | `fg=#102D46,bg=#F2C94C,bold` | Current window: deep-ocean text on yellow, bold |
| window-status | `fg=#8EA2AF,bg=#102D46` | Inactive windows: muted steel-blue text |
| continuum | `@continuum-restore on` + `@continuum-save-interval 1` | Auto-save session every minute |
| resurrect/continuum | two `run-shell` lines | Session persistence |

### 4.2 status_info.sh (currently-running version = simple)

13 lines, displays only the current folder path (`$HOME` shortened to `~`).
Reads via `tmux display-message -p -F '#{pane_current_path}'`.

**⚠️ Version divergence**: the user currently runs the 303B simple version
(folder path only). The 3KB rich version in ai-coworker (session/project/worktree/
branch/ahead-behind/staged/initiative) was **never deployed** to this machine.
The spec uses the simple version; the rich version is an optional enhancement.

### 4.3 git_branch.sh

Legacy file, not referenced by the current `.tmux.conf`. The rich status_info.sh
already embeds git info; this file is redundant and not ported.

### 4.4 claude-tmux

Third-party Rust TUI (github.com/nielsgroen/claude-tmux), binary at
`~/.cargo/bin/`. install.sh is bash-only with no Rust build step → **does NOT
auto-install the binary**, only documents the binding.

### 4.5 Benjamin Blue Palette (tmux side)

| Use | Hex |
|-----|-----|
| Status bar bg | `#102D46` |
| Status bar fg | `#EAE7DD` |
| Highlight (current window/active border/message) | `#F2C94C` |
| Success (status dot) | `#5F8D4E` |
| Inactive window text | `#8EA2AF` |
| Pane border | `#30506B` |

---

## 5. ai-coworker Role Boundary

### 5.1 Core Layer (keep)

| Module | Role |
|--------|------|
| Context Injection | CLAUDE.md template generation + semantic merge |
| Skill Deployment | Deploy skills from skill-factory to Claude Code + OpenCode |
| Analytics Hooks | 4 hook events → session audit log |
| MCP Config | coworker.yaml → settings.json/opencode/gemini sync |
| Memory Graph | graph.json + mem0 + curator + MCP server |
| Wrong-History Prevention | Extract anti-patterns from corrections, inject into CLAUDE.md |
| Permission Management | Declarative permission model |

### 5.2 Presentation Layer (strip → claude-tmux-config)

| Location | Content |
|----------|---------|
| `setup/install.sh` Step 16 | tmux status bar deploy + append grey theme |
| `setup/status_info.sh` | tmux rich status bar script |
| `~/.claude/statusline-command.sh` | Claude Code statusline (scattered, no VCS) |
| `~/.claude/wrap-statusline.py` | ANSI wrap helper (scattered) |
| `~/.tmux.conf` + `~/.tmux/scripts/` | Benjamin Blue theme (scattered) |

### 5.3 Migration Matrix

| Asset | From | To |
|-------|------|----|
| `statusline-command.sh` | `~/.claude/` | `claude-tmux-config/statusline/` |
| `wrap-statusline.py` | `~/.claude/` | `claude-tmux-config/statusline/` |
| `status_info.sh` (simple) | `~/.tmux/scripts/` | `claude-tmux-config/tmux/` |
| Benjamin Blue theme | inline in .tmux.conf + statusline | `claude-tmux-config/theme/` |
| `install.sh` Step 16 | `ai-coworker/setup/` | delete |
| `setup/status_info.sh` (rich) | `ai-coworker/setup/` | delete (or fold into claude-tmux-config as optional enhancement) |

### 5.4 Deploy Targets (after claude-tmux-config install)

| Asset | Deploy To |
|-------|-----------|
| `statusline-command.sh` | `~/.claude/statusline/statusline-command.sh` |
| `wrap-statusline.py` | `~/.claude/statusline/wrap-statusline.py` |
| `status_info.sh` | `~/.tmux/scripts/status_info.sh` |
| `benjamin-blue.tmux` | `~/.tmux/conf.d/benjamin-blue.tmux` |
| settings.json `statusLine` | `~/.claude/settings.json` |

---

## 6. claude-tmux-config Independent Project

### 6.1 Repo Structure

```
claude-tmux-config/
├── README.md                     # usage, install, uninstall, screenshots
├── install.sh                    # main install script (with confirm prompts)
├── uninstall.sh                  # uninstall (manifest-driven)
├── assets/
│   ├── statusline-command.sh     # Claude Code statusline (3 paths parameterized)
│   ├── wrap-statusline.py        # ANSI wrap helper
│   ├── status_info.sh            # tmux status bar (simple version)
│   └── benjamin-blue.tmux        # tmux theme file
└── docs/
    └── claude-tmux.md            # claude-tmux binding docs
```

### 6.2 Install Confirmation Mechanism

Reuses ai-coworker install.sh interaction style (0/1/2 menu + y/N confirm,
default N):

```
claude-tmux-config install
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 What to install? (default skip, non-destructive)
  1) Claude Code statusline (statusline + statusLine setting)
  2) tmux theme + status bar (Benjamin Blue + source theme file)
  0) Skip
Choose [0]:
```

**⚠️ Existing-inline-color special case**: the user's `.tmux.conf` already has
Benjamin Blue inlined. If detected, install only deploys `status_info.sh` and does
NOT add a duplicate `source`, avoiding pollution. Fresh users get the full theme file.

### 6.3 Idempotency & Safety

- settings.json: backup `.bak` + atomic write (reuse `_write_json_atomic` pattern)
- .tmux.conf: backup `.tmux.conf.bak` before mutation; marker check prevents duplicates
- uninstall: manifest-driven, removes statusLine, deletes `~/.tmux/conf.d/`, restores source line

### 6.4 Dependency Check

Before component 1 install: `command -v jq && command -v bc && command -v python3`; warn + explain if missing.

---

## 7. Explicitly Not Done

- ❌ No auto-install of the `claude-tmux` Rust binary (third-party, documented only)
- ❌ No porting of `git_branch.sh` (redundant)
- ❌ No macOS adaptation (`stat -c %W` / `hostname -s` Linux-only; Linux-only stated)
- ❌ No stripping of ai-coworker core (hooks/skills/MCP/context/memory) — that is its soul

---

## 8. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| statusline performance overhead | ccusage cache (120s TTL), git lightweight, overall <100ms |
| Missing jq/bc/python3 silent failure | install does `command -v` check + warn |
| .tmux.conf pollution | idempotent marker + backup `.bak` before mutation |
| settings.json corruption on interrupt | `_write_json_atomic` (temp + rename + .bak) |
| macOS cross-platform incompatibility | declare Linux-only |
| Uninstall leaves orphans | manifest tracks new paths + owned_dirs extension |

---

## 9. Acceptance Criteria

1. `claude-tmux-config` repo created, assets complete, paths parameterized
2. `install.sh` runs: 0/1/2 menu + y/N confirm, default N
3. After install: `~/.claude/statusline/` two files in place, settings.json has `statusLine`
4. After install: `~/.tmux/conf.d/benjamin-blue.tmux` in place (or skipped if existing inline color)
5. `uninstall.sh` cleanly removes all traces
6. After ai-coworker strip: install.sh no longer touches tmux, core tests all green
