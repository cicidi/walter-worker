#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# ai-coworker install.sh
# Installs coworker skills from skill-factory to Claude Code (primary) and
# OpenCode (symlink/copy).
#
# Usage:
#   ./setup/install.sh              # interactive mode
#   ./setup/install.sh --global     # install to ~/.claude/commands/ (default)
#   ./setup/install.sh --project /path/to/project
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILL_FACTORY_URL="https://github.com/cicidi/skill-factory"
SKILL_FACTORY_DIR="$HOME/.config/opencode/skills/skill-factory"
GLOBAL_CLAUDE_MD="$HOME/.claude/CLAUDE.md"

default_branch() {
    local ref
    ref=$(git ls-remote --symref origin HEAD 2>/dev/null | \
          awk '/^ref:/ {sub("refs/heads/","",$2); print $2}')
    echo "${ref:-main}"
}

INSTALL_MODE=""
PROJECT_PATH=""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

log()    { echo -e "${BLUE}→${NC} $*"; }
ok()     { echo -e "${GREEN}✓${NC} $*"; }
warn()   { echo -e "${YELLOW}⚠${NC}  $*"; }
error()  { echo -e "${RED}✗${NC} $*"; }

# =============================================================================
# Parse arguments
# =============================================================================
while [[ $# -gt 0 ]]; do
  case "$1" in
    --global)   INSTALL_MODE="global"; shift ;;
    --project)  INSTALL_MODE="project"; PROJECT_PATH="$2"; shift 2 ;;
    --help|-h)
      echo "Usage: install.sh [--global | --project /path]"
      exit 0 ;;
    *) error "Unknown argument: $1"; exit 1 ;;
  esac
done

# =============================================================================
# Step 1 — Banner
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  AI Coworker — Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# =============================================================================
# Step 2 — Ensure global CLAUDE.md exists
# =============================================================================
log "Checking global CLAUDE.md..."

CLAUDE_MD_CONTENT=$(python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT/src')
from coworker.templates.global_claude_md import generate_global_claude_md
print(generate_global_claude_md())
")

if [[ -f "$GLOBAL_CLAUDE_MD" ]]; then
  ok "Global CLAUDE.md already exists at $GLOBAL_CLAUDE_MD"
else
  log "Creating global CLAUDE.md at $GLOBAL_CLAUDE_MD..."
  mkdir -p "$(dirname "$GLOBAL_CLAUDE_MD")"
  echo "$CLAUDE_MD_CONTENT" > "$GLOBAL_CLAUDE_MD"
  ok "Created $GLOBAL_CLAUDE_MD"
fi

# =============================================================================
# Step 3 — Clone/update skill-factory
# =============================================================================
log "Setting up skill-factory..."

if [[ -d "$SKILL_FACTORY_DIR" ]]; then
  log "Updating skill-factory from GitHub..."
  git -C "$SKILL_FACTORY_DIR" pull --ff-only origin "$(default_branch)" 2>/dev/null || \
    warn "Could not update skill-factory (dirty or offline). Continuing with current version."
else
  log "Cloning skill-factory from $SKILL_FACTORY_URL..."
  mkdir -p "$(dirname "$SKILL_FACTORY_DIR")"
  git clone "$SKILL_FACTORY_URL" "$SKILL_FACTORY_DIR" 2>/dev/null || {
    error "Failed to clone skill-factory. Check your internet connection and git config."
    exit 1
  }
fi

ok "Skill-factory ready at $SKILL_FACTORY_DIR"

# =============================================================================
# Step 4 — Install mode
# =============================================================================
if [[ -z "$INSTALL_MODE" ]]; then
  echo ""
  echo "Install location:"
  echo "  1) Global (~/.claude/commands/) — available in all projects [default]"
  echo "  2) Project (current directory) — only this project"
  read -rp "  Choose [1]: " CHOICE
  CHOICE="${CHOICE:-1}"
  case "$CHOICE" in
    1) INSTALL_MODE="global" ;;
    2) INSTALL_MODE="project"; PROJECT_PATH="$(pwd)" ;;
    *) error "Invalid choice"; exit 1 ;;
  esac
fi

if [[ "$INSTALL_MODE" == "project" && -z "$PROJECT_PATH" ]]; then
  PROJECT_PATH="$(pwd)"
fi

# =============================================================================
# Step 5 — Determine install destinations
# =============================================================================
if [[ "$INSTALL_MODE" == "global" ]]; then
  CLAUDE_DIR="$HOME/.claude/commands"
  OPENCODE_DIR="$HOME/.opencode/instructions"
else
  CLAUDE_DIR="$PROJECT_PATH/.claude/commands"
  OPENCODE_DIR="$PROJECT_PATH/.opencode/instructions"
fi

# Ensure Claude directory exists (Claude Code is primary)
mkdir -p "$CLAUDE_DIR"
ok "Claude Code skills dir: $CLAUDE_DIR"

# =============================================================================
# Step 6 — Deploy ai-coworker skills to OpenCode skill directory
# =============================================================================
OPENCODE_SKILLS_DIR="$HOME/.config/opencode/skills/ai-coworker"
log "Deploying ai-coworker skills to OpenCode skill directory..."

if [[ ! -d "$REPO_ROOT/skills" ]]; then
  warn "No skills/ directory found in ai-coworker repo — skipping"
else
  mkdir -p "$OPENCODE_SKILLS_DIR"

  # Save old skill content hashes before sync
  declare -a OLD_DIRS=()
  declare -a OLD_DIR_HASHES=()
  if [[ -d "$OPENCODE_SKILLS_DIR" ]]; then
    for skill_dir in "$OPENCODE_SKILLS_DIR"/*/; do
      [[ -d "$skill_dir" ]] || continue
      skill_file="${skill_dir}SKILL.md"
      [[ -f "$skill_file" ]] || continue
      OLD_DIRS+=("$(basename "$skill_dir")")
      OLD_DIR_HASHES+=("$(md5sum "$skill_file" | cut -d' ' -f1)")
    done
  fi

  # Sync without --delete (preserve skills deleted from source)
  rsync -a "$REPO_ROOT/skills/" "$OPENCODE_SKILLS_DIR/"

  # Build source skill hash map for rename detection
  declare -a SRC_DIRS=()
  declare -a SRC_DIR_HASHES=()
  for skill_dir in "$REPO_ROOT/skills"/*/; do
    [[ -d "$skill_dir" ]] || continue
    skill_file="${skill_dir}SKILL.md"
    [[ -f "$skill_file" ]] || continue
    SRC_DIRS+=("$(basename "$skill_dir")")
    SRC_DIR_HASHES+=("$(md5sum "$skill_file" | cut -d' ' -f1)")
  done

  # Detect renames: old dir gone from source, content moved to new dir.
  # Indexed parallel arrays (bash-3.2 compatible; declare -A breaks on macOS).
  if [[ ${#OLD_DIRS[@]} -gt 0 && ${#SRC_DIRS[@]} -gt 0 ]]; then
    for old_i in "${!OLD_DIRS[@]}"; do
      old_dir="${OLD_DIRS[$old_i]}"
      old_hash="${OLD_DIR_HASHES[$old_i]}"
      [[ -d "$REPO_ROOT/skills/$old_dir" ]] && continue
      for src_i in "${!SRC_DIRS[@]}"; do
        if [[ "${SRC_DIR_HASHES[$src_i]}" == "$old_hash" ]]; then
          log "Renamed skill: $old_dir → ${SRC_DIRS[$src_i]} (cleaning up old)"
          rm -rf "$OPENCODE_SKILLS_DIR/$old_dir"
          break
        fi
      done
    done
  fi

  ok "Deployed skills to $OPENCODE_SKILLS_DIR"
fi

# =============================================================================
# Step 7 — List available skills from skill-factory
# =============================================================================
log "Loading available skills from skill-factory..."

declare -a AVAILABLE_SKILLS=()
declare -a SKILL_PATHS=()
declare -a SKILL_LABELS=()

index_skills() {
  local dir="$1"
  local prefix="$2"
  for skill_dir in "$dir"/*/; do
    [[ -d "$skill_dir" ]] || continue
    local skill_file="${skill_dir}SKILL.md"
    [[ -f "$skill_file" ]] || continue
    local name
    name=$(grep -m1 '^name:' "$skill_file" 2>/dev/null | sed 's/name: *//' | xargs)
    [[ -n "$name" ]] || continue
    AVAILABLE_SKILLS+=("$name")
    SKILL_PATHS+=("$skill_file")
    SKILL_LABELS+=("${prefix}$(basename "$skill_dir")")
  done
}

index_skills "$SKILL_FACTORY_DIR/ai-coworker-skills" "[factory] "
index_skills "$SKILL_FACTORY_DIR/personal-skills" "[personal] "
index_skills "$SKILL_FACTORY_DIR/import-skills" "[import] "

if [[ ${#AVAILABLE_SKILLS[@]} -eq 0 ]]; then
  warn "No skills found in skill-factory."
else
  ok "Found ${#AVAILABLE_SKILLS[@]} skills in skill-factory."
fi

# =============================================================================
# Step 8 — Skill selection
# =============================================================================
echo ""
echo "Skill selection:"
echo "  0) None — skip skill installation [default]"
echo "  1) All — install all available skills"
echo "  2) Select — pick individual skills"
read -rp "  Choose [0]: " SKILL_CHOICE
SKILL_CHOICE="${SKILL_CHOICE:-0}"

SELECTED_SKILLS=()

case "$SKILL_CHOICE" in
  0)
    log "Skipping skill installation."
    ;;
  1)
    SELECTED_SKILLS=("${AVAILABLE_SKILLS[@]}")
    log "Installing all ${#SELECTED_SKILLS[@]} skills."
    ;;
  2)
    echo ""
    echo "Available skills (enter numbers, space-separated):"
    for i in "${!SKILL_LABELS[@]}"; do
      printf "  %2d) %s  (%s)\n" "$((i+1))" "${SKILL_LABELS[$i]}" "${AVAILABLE_SKILLS[$i]}"
    done
    read -rp "  Select: " SELECTED_NUMS
    for num in $SELECTED_NUMS; do
      idx=$((num-1))
      if [[ $idx -ge 0 && $idx -lt ${#AVAILABLE_SKILLS[@]} ]]; then
        SELECTED_SKILLS+=("${AVAILABLE_SKILLS[$idx]}")
      fi
    done
    log "Selected ${#SELECTED_SKILLS[@]} skills."
    ;;
  *)
    error "Invalid choice"; exit 1 ;;
esac

# =============================================================================
# Step 9 — Always install the core init skill
log "Installing core skill (init)..."
SETUP_SKILL_SRC="$REPO_ROOT/skills/init/SKILL.md"
if [[ -f "$SETUP_SKILL_SRC" ]]; then
  cp "$SETUP_SKILL_SRC" "$CLAUDE_DIR/init.md"
  ok "Installed init skill (core, always installed)"
else
  warn "skills/init/SKILL.md not found at $SETUP_SKILL_SRC"
fi

# =============================================================================
# Step 10 — Install selected skills to Claude Code (primary)
# =============================================================================
CREATED=0
UPDATED=0
SKIPPED=0

install_skill() {
  local src="$1"
  local target_dir="$2"
  local folder_name=""
  folder_name="$(basename "$(dirname "$src")")"
  local filename="${folder_name}.md"

  if [[ ! -f "$src" ]]; then
    warn "Source not found: $src"
    return
  fi

  mkdir -p "$target_dir"
  if [[ ! -f "$target_dir/$filename" ]]; then
    cp "$src" "$target_dir/$filename"
    ((CREATED++)) || true
    ok "  Created: $filename"
  elif ! diff -q "$src" "$target_dir/$filename" &>/dev/null; then
    cp "$src" "$target_dir/$filename"
    ((UPDATED++)) || true
    ok "  Updated: $filename"
  else
    ((SKIPPED++)) || true
  fi
}

if [[ ${#SELECTED_SKILLS[@]} -gt 0 ]]; then
  echo ""
  log "Installing skills to Claude Code..."
  for i in "${!SELECTED_SKILLS[@]}"; do
    install_skill "${SKILL_PATHS[$i]}" "$CLAUDE_DIR"
  done
fi

# =============================================================================
# Step 11 — OpenCode: symlink or copy
# =============================================================================
if [[ -n "$OPENCODE_DIR" ]]; then
  echo ""
  log "Syncing skills to OpenCode..."

  mkdir -p "$OPENCODE_DIR"

  # Symlink init skill if possible
  if [[ -f "$CLAUDE_DIR/init.md" ]]; then
    if [[ -L "$OPENCODE_DIR/init.md" ]]; then
      ok "  OpenCode symlink already exists: init.md"
    else
      ln -sf "$CLAUDE_DIR/init.md" "$OPENCODE_DIR/init.md" 2>/dev/null || \
        cp "$CLAUDE_DIR/init.md" "$OPENCODE_DIR/init.md"
      ok "  Synced to OpenCode: init.md"
    fi
  fi

  # Sync selected skills
  for skill_file in "$CLAUDE_DIR"/*.md; do
    [[ -f "$skill_file" ]] || continue
    name="${skill_file##*/}"
    [[ "$name" == "init.md" ]] && continue
    if [[ ! -f "$OPENCODE_DIR/$name" ]]; then
      ln -sf "$skill_file" "$OPENCODE_DIR/$name" 2>/dev/null || cp "$skill_file" "$OPENCODE_DIR/$name"
    elif ! diff -q "$skill_file" "$OPENCODE_DIR/$name" &>/dev/null; then
      cp "$skill_file" "$OPENCODE_DIR/$name"
    fi
  done
  ok "OpenCode sync complete."
fi

# =============================================================================
# Step 12 — Symlink CLAUDE.md for OpenCode
# =============================================================================
if [[ "$INSTALL_MODE" == "project" ]]; then
  CLAUDE_MD="$REPO_ROOT/CLAUDE.md"
  OPENCODE_AGENTS="$PROJECT_PATH/AGENTS.md"
  if [[ -f "$CLAUDE_MD" ]]; then
    ln -sf "$CLAUDE_MD" "$OPENCODE_AGENTS" 2>/dev/null || true
  fi
fi

# =============================================================================
# Step 13 — Update .gitignore (project mode)
# =============================================================================
if [[ "$INSTALL_MODE" == "project" ]]; then
  GITIGNORE="$PROJECT_PATH/.gitignore"
  [[ -f "$GITIGNORE" ]] || touch "$GITIGNORE"
  for entry in "personal/" ".local_config.yaml" ".env" ".cursorrules" "AGENTS.md" "GEMINI.md"; do
    grep -qxF "$entry" "$GITIGNORE" 2>/dev/null || echo "$entry" >> "$GITIGNORE"
  done
fi

# =============================================================================
# Step 14 — Analytics Listener Setup
# =============================================================================
echo ""
log "Setting up analytics listener..."

ANALYTICS_DIR="$HOME/.coworker/analytics"
mkdir -p "$ANALYTICS_DIR/sessions"
mkdir -p "$ANALYTICS_DIR/hooks"

HOOKS_SRC="$REPO_ROOT/src/coworker/analytics/hooks"
if [[ -d "$HOOKS_SRC" ]]; then
  cp "$HOOKS_SRC/"*.sh "$ANALYTICS_DIR/hooks/"
  chmod +x "$ANALYTICS_DIR/hooks/"*.sh
  ok "Hook scripts installed to $ANALYTICS_DIR/hooks/"
else
  warn "Hook scripts not found — skipping"
fi

# Configure Claude Code hooks
CLAUDE_SETTINGS="$HOME/.claude/settings.json"
if [[ ! -f "$CLAUDE_SETTINGS" ]]; then
  echo '{}' > "$CLAUDE_SETTINGS"
fi
python3 -c "
import json
with open('$CLAUDE_SETTINGS') as f: cfg = json.load(f)
cfg.setdefault('hooks', {})
cfg['hooks']['UserPromptSubmit'] = [{'matcher': '', 'hooks': [{'type': 'command', 'command': '$HOME/.coworker/analytics/hooks/on-user-prompt.sh'}]}]
cfg['hooks']['PreToolUse'] = [{'matcher': '', 'hooks': [{'type': 'command', 'command': '$HOME/.coworker/analytics/hooks/on-pre-tool.sh'}]}]
cfg['hooks']['PostToolUse'] = [{'matcher': '', 'hooks': [{'type': 'command', 'command': '$HOME/.coworker/analytics/hooks/on-post-tool.sh'}]}]
cfg['hooks']['Stop'] = [{'matcher': '', 'hooks': [{'type': 'command', 'command': '$HOME/.coworker/analytics/hooks/on-stop.sh'}]}]
with open('$CLAUDE_SETTINGS', 'w') as f: json.dump(cfg, f, indent=2)
" 2>/dev/null && ok "Claude Code hooks configured" || warn "Failed to configure Claude Code hooks"

# Register OpenCode analytics plugin
OPENCODE_CONFIG="$HOME/.config/opencode/config.json"
if [[ -f "$OPENCODE_CONFIG" ]]; then
  python3 -c "
import json
with open('$OPENCODE_CONFIG') as f: cfg = json.load(f)
plugins = cfg.setdefault('plugin', [])
plugin_path = '$REPO_ROOT/.opencode/coworker-analytics'
if plugin_path not in plugins:
    plugins.append(plugin_path)
with open('$OPENCODE_CONFIG', 'w') as f: json.dump(cfg, f, indent=2)
print('OpenCode plugin registered')
" 2>/dev/null && ok "OpenCode analytics plugin registered" || warn "Failed to register OpenCode plugin"
fi

# Initialize analytics DB
python3 -c "
import sys; sys.path.insert(0, '$REPO_ROOT/src')
from coworker.analytics.db import init_db
init_db()
print('Analytics DB initialized')
" 2>/dev/null && ok "Analytics database initialized" || warn "Analytics DB init skipped"

echo "Analytics listener setup complete."

# =============================================================================
# Step 15 — MCP config sync
# =============================================================================
if command -v coworker &>/dev/null; then
  echo ""
  log "Syncing MCP config via coworker CLI..."

  MCP_JSON="$REPO_ROOT/.mcp.json"
  if [[ -f "$MCP_JSON" ]]; then
    :  # (MCP import removed — handled via sync)
  fi
    coworker sync && ok "Config synced to all tools"
else
  warn "coworker CLI not found. Run: pipx install $REPO_ROOT"
  warn "Then re-run this script to sync MCP config."
fi

# =============================================================================
# Step 16 — Deploy tmux status bar
# =============================================================================
echo ""
log "Setting up tmux status bar..."

TMUX_SCRIPTS_DIR="$HOME/.tmux/scripts"
mkdir -p "$TMUX_SCRIPTS_DIR"

cp "$REPO_ROOT/setup/status_info.sh" "$TMUX_SCRIPTS_DIR/status_info.sh"
chmod +x "$TMUX_SCRIPTS_DIR/status_info.sh"
ok "Status bar script deployed to $TMUX_SCRIPTS_DIR/status_info.sh"

TMUX_CONF="$HOME/.tmux.conf"
if [[ -f "$TMUX_CONF" ]]; then
  if grep -q "status_info.sh" "$TMUX_CONF" 2>/dev/null; then
    ok "tmux.conf already references status_info.sh"
  else
    {
      echo ""
      echo "# ai-coworker status bar"
      echo "set -g status-style 'bg=colour236,fg=white'"
      echo "set -g status-left-length 40"
      echo "set -g status-left \"#[fg=yellow]#{session_created_string} \""
      echo "set -g status-right-length 250"
      echo "set -g status-right \"#(~/.tmux/scripts/status_info.sh) \""
    } >> "$TMUX_CONF"
    ok "tmux.conf updated with status bar config"
  fi
else
  warn "$TMUX_CONF not found — skipping tmux config update"
fi

# =============================================================================
# Done
# =============================================================================
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ok "Setup complete!"
echo "   Mode    : $INSTALL_MODE"
echo "   Claude  : $CLAUDE_DIR"
[[ -n "$OPENCODE_DIR" ]] && echo "   OpenCode: $OPENCODE_DIR"
echo "   Created : $CREATED files"
echo "   Updated : $UPDATED files"
echo "   Skipped : $SKIPPED files (already up-to-date)"
echo ""
echo "Next steps:"
echo "  Add env vars to ~/.coworker/.env or ~/.zshrc:"
echo "    GITHUB_PERSONAL_ACCESS_TOKEN=..."
echo "    SLACK_BOT_TOKEN=..."
echo "    TELEGRAM_BOT_TOKEN=..."
echo "    DISCORD_TOKEN=..."
echo "  Run: coworker sync"
echo "  Analytics: coworker analytics dashboard"
echo "  Sessions recorded to: ~/.coworker/analytics/sessions/"
echo "  Start coding — skills are ready!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
