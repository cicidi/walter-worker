#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# walter-worker install.sh
# Installs coworker skills. Skills sourced from the-super-lab are deployed to
# Claude Code, OpenCode, and Cursor; walter-worker's own bundle skills go to
# Claude Code (primary) and OpenCode (symlink/copy).
#
# Usage:
#   ./setup/install.sh              # interactive mode
#   ./setup/install.sh --global     # install to ~/.claude/commands/ (default)
#   ./setup/install.sh --project /path/to/project
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# the-super-lab is the source of truth for skills. Edit there first; this
# script deploys its skills to Claude Code, OpenCode, and Cursor.
THE_SUPER_LAB_DIR="${THE_SUPER_LAB_DIR:-$HOME/project/the-super-lab}"
THE_SUPER_LAB_OPENCODE_DIR="$HOME/.config/opencode/skills/the-super-lab"
CURSOR_RULES_DIR="$HOME/.cursor/rules"
GLOBAL_CLAUDE_MD="$HOME/.claude/CLAUDE.md"

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
echo "  Walter Worker — Setup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# =============================================================================
# Step 1b — Save a pristine snapshot before touching anything
# =============================================================================
# uninstall.sh --restore-pristine copies settings.json and CLAUDE.md back out of
# here. Nothing created this directory, so that option could only ever end at
# "No pristine backup found". Taken once, on the first install, while both files
# are still unmodified — the two the uninstaller restores.
PRISTINE_DIR="$HOME/.coworker/backups/pristine"
if [[ ! -d "$PRISTINE_DIR" ]]; then
  mkdir -p "$PRISTINE_DIR"
  for f in "$HOME/.claude/settings.json" "$GLOBAL_CLAUDE_MD"; do
    [[ -f "$f" ]] && cp "$f" "$PRISTINE_DIR/$(basename "$f")"
  done
  log "Saved pristine snapshot to $PRISTINE_DIR"
fi

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
  log "Run 'coworker upgrade' to merge template updates into your existing CLAUDE.md."
else
  log "Creating global CLAUDE.md at $GLOBAL_CLAUDE_MD..."
  mkdir -p "$(dirname "$GLOBAL_CLAUDE_MD")"
  echo "$CLAUDE_MD_CONTENT" > "$GLOBAL_CLAUDE_MD"
  ok "Created $GLOBAL_CLAUDE_MD"
fi

# =============================================================================
# Step 3 — Update the-super-lab (skill source of truth)
# =============================================================================
log "Checking the-super-lab..."

if [[ -d "$THE_SUPER_LAB_DIR/.git" ]]; then
  log "Updating the-super-lab..."
  git -C "$THE_SUPER_LAB_DIR" pull --ff-only 2>/dev/null || \
    warn "Could not update the-super-lab (dirty or offline). Continuing with current version."
  ok "the-super-lab ready at $THE_SUPER_LAB_DIR"
elif [[ -d "$THE_SUPER_LAB_DIR" ]]; then
  warn "the-super-lab at $THE_SUPER_LAB_DIR is not a git repo — using it as-is."
else
  warn "the-super-lab not found at $THE_SUPER_LAB_DIR — skills will not be deployed."
  warn "Clone it with: git clone git@github.com:cicidi/the-super-lab.git \"$THE_SUPER_LAB_DIR\""
fi

# =============================================================================
# Step 4 — Install mode
# =============================================================================
if [[ -z "$INSTALL_MODE" ]]; then
  echo ""
  echo "Install location:"
  echo "  1) Global (~/.claude/commands/) — available in all projects [default]"
  echo "  2) Project (current directory) — only this project"
  read -rp "  Choose [1]: " CHOICE || CHOICE=""
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

# Content hash for a file, portable across GNU and BSD userlands.
#
# This used `md5sum | cut`, which is GNU coreutils. macOS has no md5sum, and
# under `set -euo pipefail` the failed command substitution aborted the whole
# install — on the very platform this script goes out of its way to support
# (see the bash-3.2 note below). python3 is already required throughout this
# script, so it is the one hashing tool guaranteed to be present.
_hash_file() {
  python3 -c "import hashlib, sys; print(hashlib.md5(open(sys.argv[1], 'rb').read()).hexdigest())" "$1"
}

# =============================================================================
# Step 6 — Deploy walter-worker skills to OpenCode skill directory
# =============================================================================
OPENCODE_SKILLS_DIR="$HOME/.config/opencode/skills/walter-worker"
log "Deploying walter-worker skills to OpenCode skill directory..."

if [[ ! -d "$REPO_ROOT/skills" ]]; then
  warn "No skills/ directory found in walter-worker repo — skipping"
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
      OLD_DIR_HASHES+=("$(_hash_file "$skill_file")")
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
    SRC_DIR_HASHES+=("$(_hash_file "$skill_file")")
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
# Step 7 — List available skills from the-super-lab
# =============================================================================
log "Loading available skills from the-super-lab..."

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

index_skills "$THE_SUPER_LAB_DIR/skills" "[superlab] "
index_skills "$THE_SUPER_LAB_DIR/personal-skills" "[personal] "
index_skills "$REPO_ROOT/skills" "[bundle] "

if [[ ${#AVAILABLE_SKILLS[@]} -eq 0 ]]; then
  warn "No skills found in the-super-lab or the local bundle."
else
  ok "Found ${#AVAILABLE_SKILLS[@]} available skills."
fi

# =============================================================================
# Step 8 — Skill selection
# =============================================================================
echo ""
echo "Skill selection:"
echo "  0) None — skip skill installation [default]"
echo "  1) All — install all available skills"
echo "  2) Select — pick individual skills"
read -rp "  Choose [0]: " SKILL_CHOICE || SKILL_CHOICE=""
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
    read -rp "  Select: " SELECTED_NUMS || SELECTED_NUMS=""
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

  # Prune entries this sync no longer produces. Without this the directory only
  # ever grows: a symlink made by an earlier run keeps pointing at CLAUDE_DIR
  # after its target is deleted or renamed, and nothing ever removes it. 78 such
  # dangling links had accumulated here.
  #
  # Symlinks only. A regular file may be something the user placed there, while
  # a symlink with no CLAUDE_DIR counterpart is one this script created and
  # whose target is now gone.
  #
  # Recurses, because an earlier release symlinked whole directories in here, so
  # a dangling link can sit below the top level. Directories the prune empties
  # go too, or it would trade dangling links for a tree of empty shells.
  pruned=0
  while IFS= read -r existing; do
    rm -f "$existing"
    pruned=$((pruned + 1))
  done < <(find "$OPENCODE_DIR" -xtype l 2>/dev/null)
  find "$OPENCODE_DIR" -mindepth 1 -type d -empty -delete 2>/dev/null || true
  [[ $pruned -gt 0 ]] && ok "  Pruned $pruned stale OpenCode symlink(s)"
  ok "OpenCode sync complete."
fi

# =============================================================================
# Step 11b — Deploy the-super-lab skills to Claude, OpenCode, and Cursor
# =============================================================================
# the-super-lab is the source of truth. Each skill deploys to three harnesses:
#   Claude Code  ~/.claude/skills/<name>/SKILL.md                (directory copy)
#   OpenCode     ~/.config/opencode/skills/the-super-lab/<name>  (symlink to source)
#   Cursor       ~/.cursor/rules/<name>.md                       (verbatim copy)
# Claude and OpenCode receive whole directories so sibling files (for example
# domain-modeling/ADR-FORMAT.md) travel with the skill. A flattened SKILL.md
# copy silently drops them.
if [[ -d "$THE_SUPER_LAB_DIR/skills" ]]; then
  echo ""
  log "Deploying the-super-lab skills to Claude, OpenCode, Cursor..."

  mkdir -p "$HOME/.claude/skills" "$THE_SUPER_LAB_OPENCODE_DIR" "$CURSOR_RULES_DIR"
  DEPLOYED=0

  for skill_dir in "$THE_SUPER_LAB_DIR/skills"/*/; do
    [[ -d "$skill_dir" ]] || continue
    skill_file="${skill_dir}SKILL.md"
    [[ -f "$skill_file" ]] || continue
    name="$(basename "$skill_dir")"

    # Claude Code — directory, so sibling files travel
    mkdir -p "$HOME/.claude/skills/$name"
    cp "$skill_file" "$HOME/.claude/skills/$name/SKILL.md"
    for sibling in "$skill_dir"*; do
      [[ -f "$sibling" ]] || continue
      [[ "$(basename "$sibling")" == "SKILL.md" ]] && continue
      cp "$sibling" "$HOME/.claude/skills/$name/"
    done

    # OpenCode — symlink the whole directory to the source
    opencode_target="$THE_SUPER_LAB_OPENCODE_DIR/$name"
    if [[ -e "$opencode_target" && ! -L "$opencode_target" ]]; then
      rm -rf "$opencode_target"
    fi
    ln -sfn "${skill_dir%/}" "$opencode_target"

    # Cursor — verbatim flattened copy
    cp "$skill_file" "$CURSOR_RULES_DIR/$name.md"

    ((DEPLOYED++)) || true
  done

  ok "Deployed $DEPLOYED the-super-lab skills to Claude, OpenCode, and Cursor."
fi

# =============================================================================
# Step 12 — Symlink CLAUDE.md for OpenCode
# =============================================================================
if [[ "$INSTALL_MODE" == "project" ]]; then
  CLAUDE_MD="$PROJECT_PATH/CLAUDE.md"
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
  for entry in "personal/" ".local_config.yaml" ".env" ".cursorrules" "AGENTS.md" "GEMINI.md" "CLAUDE.local.md" "docs/state/"; do
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
  # .py hooks as well as .sh: the repo ships on-correction.py and settings.json
  # registers it, but this glob only matched shell scripts, so a fresh install
  # never received it and an existing one never picked up changes to it.
  cp "$HOOKS_SRC/"*.sh "$HOOKS_SRC/"*.py "$ANALYTICS_DIR/hooks/" 2>/dev/null || \
    cp "$HOOKS_SRC/"*.sh "$ANALYTICS_DIR/hooks/"
  chmod +x "$ANALYTICS_DIR/hooks/"*.sh "$ANALYTICS_DIR/hooks/"*.py 2>/dev/null || true
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

def _merge_hook(event, cmd):
    entries = cfg['hooks'].setdefault(event, [])
    has_it = any(
        h.get('command') == cmd
        for g in entries if isinstance(g, dict)
        for h in (g.get('hooks') or [])
    )
    if not has_it:
        entries.append({'matcher': '', 'hooks': [{'type': 'command', 'command': cmd}]})

_merge_hook('UserPromptSubmit', '$HOME/.coworker/analytics/hooks/on-user-prompt.sh')
# The correction detector is the first stage of the self-heal loop: it reads
# the prompt, writes a draft trace when the user is correcting the agent, and
# the self-heal skill picks that up. The file was being copied into the hooks
# dir but never wired to an event, so it ran only on machines where someone
# had registered it by hand. python3 is explicit rather than relying on the
# shebang and the exec bit, which install.sh only sets best-effort.
_merge_hook('UserPromptSubmit', 'python3 $HOME/.coworker/analytics/hooks/on-correction.py')
_merge_hook('PreToolUse',        '$HOME/.coworker/analytics/hooks/on-pre-tool.sh')
_merge_hook('PostToolUse',       '$HOME/.coworker/analytics/hooks/on-post-tool.sh')
_merge_hook('Stop',              '$HOME/.coworker/analytics/hooks/on-stop.sh')
# Session-end capture: the memory loop's first stage. It reads the hook
# payload on stdin, back-fills captures missed during the session and stages
# skill candidates for review. One LLM call per session, so it is the cheap
# half of capture; the per-tool-call half is deliberately left unwired.
#
# Bare "coworker", matching the state-update hook that sync() manages. The
# command exits 0 without a word when no API key is configured, so an
# unconfigured machine is quiet rather than nagging after every session.
#
# NOTE: this block is a double-quoted bash string, so backticks and dollar-paren
# inside these comments are command substitutions to bash, not comments. A
# previous pair of backticks here ran the coworker CLI and pasted its usage text
# into the middle of the Python, so the hooks silently stopped being written.
# Write such things out in words, or quote them with double quotes.
_merge_hook('Stop',              'coworker memory capture')

with open('$CLAUDE_SETTINGS', 'w') as f: json.dump(cfg, f, indent=2)
" 2>/dev/null && ok "Claude Code hooks configured" || warn "Failed to configure Claude Code hooks"

# Register OpenCode analytics plugin
#
# .opencode/ is gitignored and its plugin sources were removed from the repo,
# so a fresh clone has no .opencode/coworker-analytics. Registering the path
# anyway wrote an entry pointing at nothing into the user's OpenCode config,
# which OpenCode then failed to load. Only claim a plugin that is really there.
OPENCODE_CONFIG="$HOME/.config/opencode/config.json"
OPENCODE_PLUGIN="$REPO_ROOT/.opencode/coworker-analytics"
if [[ -f "$OPENCODE_CONFIG" && -d "$OPENCODE_PLUGIN" ]]; then
  python3 -c "
import json
with open('$OPENCODE_CONFIG') as f: cfg = json.load(f)
plugins = cfg.setdefault('plugin', [])
plugin_path = '$OPENCODE_PLUGIN'
if plugin_path not in plugins:
    plugins.append(plugin_path)
with open('$OPENCODE_CONFIG', 'w') as f: json.dump(cfg, f, indent=2)
print('OpenCode plugin registered')
" 2>/dev/null && ok "OpenCode analytics plugin registered" || warn "Failed to register OpenCode plugin"
elif [[ -f "$OPENCODE_CONFIG" ]]; then
  warn "No OpenCode plugin at $OPENCODE_PLUGIN — skipping registration"
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

  # MCP import lived here and was folded into `coworker sync`; .mcp.json itself
  # was removed from the repo in 0f5824bf, so the check for it was dead.
  coworker sync && ok "Config synced to all tools"
else
  warn "coworker CLI not found. Run: pipx install $REPO_ROOT"
  warn "Then re-run this script to sync MCP config."
fi

# =============================================================================
# =============================================================================
# Step 16 — Write install manifest
# =============================================================================
MANIFEST="$HOME/.coworker/install-manifest.json"

# What this installer wrote, so the manifest can claim it by name instead of by
# directory. Used to be an os.walk over ~/.claude, ~/.opencode and
# ~/.coworker/analytics, which claimed everything under those shared
# directories — plugin caches, session transcripts, other tools' skills, and the
# analytics database uninstall's own banner promises to preserve — and then
# deleted all of it.
MANIFEST_SKILLS="${SELECTED_SKILLS[*]:-}"
MANIFEST_SUPERLAB=""
if [[ -d "$THE_SUPER_LAB_DIR/skills" ]]; then
  for _d in "$THE_SUPER_LAB_DIR/skills"/*/; do
    [[ -f "${_d}SKILL.md" ]] && MANIFEST_SUPERLAB+="$(basename "$_d") "
  done
fi

python3 -c "
import json, os, glob, shutil
home = os.environ['HOME']
claude_dir = '${CLAUDE_DIR}'
selected = '${MANIFEST_SKILLS}'.split()
deployed = '${MANIFEST_SUPERLAB}'.split()
manifest = {
    # 2 = files are claimed by name, only what this installer wrote. Manifest 1
    # claimed every file found under ~/.claude, ~/.opencode and
    # ~/.coworker/analytics, which uninstall would then delete. uninstall.sh
    # refuses to remove anything from a manifest without this key.
    'schema_version': 2,
    'install_mode': '${INSTALL_MODE}',
    'repo_root': '${REPO_ROOT}',
    'hook_commands': [],
    'files': [],
    'owned_dirs': [],
    'project_path': '${PROJECT_PATH}',
}

# Claim ONLY paths this installer writes. Anything not listed here is left
# alone, which is the safe direction: an unclaimed file survives uninstall.
files = []
def claim(p):
    if os.path.isfile(p) or os.path.islink(p):
        files.append(p)

# Hook scripts copied into the analytics dir.
for p in glob.glob(f'{home}/.coworker/analytics/hooks/*'):
    claim(p)

# Skills selected in step 10, flattened to <name>.md, plus their OpenCode mirror.
for name in selected:
    claim(f'{claude_dir}/{name}.md')
    claim(f'{home}/.opencode/instructions/{name}.md')

# the-super-lab skills deployed in step 11b, by name: the Claude directory copy
# and the Cursor rules file. The OpenCode side is a symlink to the source repo
# and is removed with owned_dirs.
for name in deployed:
    for root, _dirs, fns in os.walk(f'{home}/.claude/skills/{name}'):
        for fn in fns:
            claim(os.path.join(root, fn))
    claim(f'{home}/.cursor/rules/{name}.md')

# The walter-worker skill tree this installer owns outright. Claim what the
# rsync in step 6 PRODUCES, read from the source tree rather than from the
# destination: walking the destination also claimed skills an earlier release
# had left behind, so every run re-claimed them and the prune below could never
# retire them.
_wm_src = '${REPO_ROOT}/skills'
_wm_dst = f'{home}/.config/opencode/skills/walter-worker'
for _wm_root, _wm_dirs, _wm_fns in os.walk(_wm_src):
    _wm_rel = os.path.relpath(_wm_root, _wm_src)
    for fn in _wm_fns:
        if _wm_rel == '.':
            claim(os.path.join(_wm_dst, fn))
        else:
            claim(os.path.join(_wm_dst, _wm_rel, fn))

# Deliberately NOT claimed: ~/.coworker/analytics (data), ~/.coworker/backups,
# ~/.coworker/skills (skills the user accumulated), ~/.claude/{plugins,projects,
# file-history,sessions,tasks,docs,backups}, ~/.opencode/node_modules, and any
# ~/.claude/skills/<name> this install did not deploy.
manifest['files'] = files
# Global CLAUDE.md
md = f'{home}/.claude/CLAUDE.md'
if os.path.isfile(md): manifest['files'].append(md)
# Hook commands from settings.json
sf = f'{home}/.claude/settings.json'
if os.path.isfile(sf):
    cfg = json.load(open(sf))
    for entries in cfg.get('hooks', {}).values():
        if isinstance(entries, list):
            for g in entries:
                if isinstance(g, dict):
                    for h in g.get('hooks', []):
                        manifest['hook_commands'].append(h.get('command', ''))
# Owned dirs
for d in [f'{home}/.coworker', f'{home}/.config/opencode/skills/walter-worker']:
    if os.path.isdir(d):
        manifest['owned_dirs'].append(d)

# Prune what an earlier run wrote and this run no longer produces.
#
# The manifest is rewritten once per run and lists exactly what that run
# claimed, so the difference between the previous manifest and the current
# claim set is precisely the set of paths this installer used to own and has
# stopped producing: a skill that was renamed, merged, or dropped from the
# sources. Without this the mirrors only ever grow -- 42 dangling links and 91
# retired skill directories had accumulated across four of them.
#
# Prune is one-directional by construction. A path is removed only because a
# previous run claimed it, so a file this installer never wrote is never
# touched: user files, and skills installed by another tool, survive.
#
# A failure here must not cost us the manifest, so the block is guarded.
pruned = []
try:
    _prev = {}
    if os.path.isfile('$MANIFEST'):
        try:
            _prev = json.load(open('$MANIFEST')) or {}
        except (ValueError, OSError):
            _prev = {}

    # A prune that removes the last file in a skill directory would otherwise
    # leave the bare directory behind, so emptied ones are retired with it. The
    # walk stops at each tree root, never above it.
    _trees = (f'{home}/.claude/skills',
              f'{home}/.config/opencode/skills/walter-worker')

    def _retire_empty(d):
        while any(d.startswith(t + os.sep) for t in _trees):
            try:
                os.rmdir(d)
            except OSError:
                return
            d = os.path.dirname(d)

    if _prev.get('schema_version') == 2:
        _current = set(files)
        for _p in _prev.get('files', []):
            if _p in _current or not os.path.lexists(_p):
                continue
            try:
                if os.path.isdir(_p) and not os.path.islink(_p):
                    shutil.rmtree(_p)
                else:
                    os.remove(_p)
            except OSError:
                continue
            pruned.append(_p)
            _retire_empty(os.path.dirname(_p))
except Exception:
    pruned = []
manifest['pruned'] = pruned
if pruned:
    print(f'  Retired {len(pruned)} path(s) this install no longer produces')

os.makedirs(f'{home}/.coworker', exist_ok=True)
json.dump(manifest, open('$MANIFEST', 'w'), indent=2)
" 2>/dev/null && ok "Install manifest written to $MANIFEST" || warn "Manifest write skipped"

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
echo "  Add env vars to ~/.coworker/.env:"
echo "    DEEPSEEK_API_KEY=...     # required by /memory and /knowledge;"
echo "                             # fallbacks: GEMINI_API_KEY, ANTHROPIC_API_KEY"
echo "  Run: coworker sync"
echo "  Analytics: coworker analytics dashboard"
echo "  Sessions recorded to: ~/.coworker/analytics/sessions/"
echo "  Start coding — skills are ready!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
