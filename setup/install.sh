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
THE_SUPER_LAB_OPENCODE_PERSONAL_DIR="$HOME/.config/opencode/skills/the-super-lab-personal"
# Cursor loads Agent Skills from <root>/skills/<name>/SKILL.md. The flat
# ~/.cursor/rules/<name>.md files an earlier release wrote are rules, not
# skills, and current Cursor does not discover them as skills.
CURSOR_SKILLS_DIR="$HOME/.cursor/skills"
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
    --skills)   PRESELECTED_SKILLS="$2"; shift 2 ;;
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
#
# Guarded by a marker file rather than the directory's existence. On a fresh
# machine neither file exists yet, so the loop copied nothing — but mkdir still
# created the directory, and from then on `! -d` was false forever: the
# snapshot was never taken, and --restore-pristine found an empty directory on
# every install. Absence is recorded instead, because "this file was not here"
# is the pristine state for a fresh machine and restoring it means deleting it.
PRISTINE_DIR="$HOME/.coworker/backups/pristine"
PRISTINE_TAKEN="$PRISTINE_DIR/.taken"
if [[ ! -f "$PRISTINE_TAKEN" ]]; then
  mkdir -p "$PRISTINE_DIR"
  : > "$PRISTINE_DIR/absent.txt"
  for f in "$HOME/.claude/settings.json" "$GLOBAL_CLAUDE_MD"; do
    if [[ -f "$f" ]]; then
      cp "$f" "$PRISTINE_DIR/$(basename "$f")"
    else
      echo "$f" >> "$PRISTINE_DIR/absent.txt"
    fi
  done
  touch "$PRISTINE_TAKEN"
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

# Whether this run created it, which decides if the manifest may claim it. An
# existing CLAUDE.md is deliberately left alone here, so it is the user's and
# uninstall has no business deleting it — but the manifest used to claim the
# file whenever it existed, and a plain uninstall then removed it silently.
CREATED_GLOBAL_MD=0
if [[ -f "$GLOBAL_CLAUDE_MD" ]]; then
  ok "Global CLAUDE.md already exists at $GLOBAL_CLAUDE_MD"
  log "Run 'coworker upgrade' to merge template updates into your existing CLAUDE.md."
else
  log "Creating global CLAUDE.md at $GLOBAL_CLAUDE_MD..."
  mkdir -p "$(dirname "$GLOBAL_CLAUDE_MD")"
  echo "$CLAUDE_MD_CONTENT" > "$GLOBAL_CLAUDE_MD"
  # The template as written, so 'coworker upgrade' can merge three-way and
  # tell the user's later edits from the template's.
  mkdir -p "$HOME/.coworker"
  echo "$CLAUDE_MD_CONTENT" > "$HOME/.coworker/claude-md-base.md"
  ok "Created $GLOBAL_CLAUDE_MD"
  CREATED_GLOBAL_MD=1
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
log "Loading the bundle skills offered as commands..."

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

# Only the bundle's own skills are offered as commands. Step 11b deploys every
# the-super-lab skill (skills/ and personal-skills/) to ~/.claude/skills/<name>/
# regardless of this answer, so one selected here as well was written twice and
# showed up twice in the / menu: once as a command, once as a skill.
index_skills "$REPO_ROOT/skills" "[bundle] "

if [[ ${#AVAILABLE_SKILLS[@]} -eq 0 ]]; then
  warn "No skills found in the-super-lab or the local bundle."
else
  ok "Found ${#AVAILABLE_SKILLS[@]} available skills."
fi

# =============================================================================
# Step 8 — Skill selection
# =============================================================================
SELECTED_SKILLS=()
#: Paired with SELECTED_SKILLS by position. The install loop uses this, not
#: SKILL_PATHS — that array is indexed by AVAILABLE order, so using it with a
#: subset paired every selection with another skill's file. Any selection that
#: was not "all of them, in order" installed the wrong content under the right
#: name, including the manual Select path entering "3 1".
SELECTED_PATHS=()

# A caller that knows the previous selection passes it, so an update does not
# re-ask a question it already has the answer to — and cannot take the default
# answer by accident on a run nobody is watching. It skips the prompt entirely
# rather than answering it: routing it through SKILL_CHOICE=1 would mean "All"
# to the case below, which silently overrode the selection.
if [[ -n "${PRESELECTED_SKILLS:-}" ]]; then
  # Walked in AVAILABLE order, not the caller's. SELECTED_SKILLS and
  # SKILL_PATHS are parallel arrays and the install loop pairs them by index,
  # so appending names in any other order pairs each name with another skill's
  # file — it installs the wrong content under the right name.
  for i in "${!AVAILABLE_SKILLS[@]}"; do
    for name in $PRESELECTED_SKILLS; do
      if [[ "${AVAILABLE_SKILLS[$i]}" == "$name" ]]; then
        SELECTED_SKILLS+=("$name")
        SELECTED_PATHS+=("${SKILL_PATHS[$i]}")
        break
      fi
    done
  done
  # Set as well as used: the manifest block below reads it, and under set -u an
  # unset variable aborts the script there. 2 is "selected individually", which
  # is what a passed-in list is — and it is not 0, so the prune still runs.
  SKILL_CHOICE=2
  log "Reusing the previous selection: ${#SELECTED_SKILLS[@]} skill(s)."
else
echo ""
echo "Skill selection:"
echo "  0) None — skip skill installation [default]"
echo "  1) All — install all available skills"
echo "  2) Select — pick individual skills"
read -rp "  Choose [0]: " SKILL_CHOICE || SKILL_CHOICE=""
SKILL_CHOICE="${SKILL_CHOICE:-0}"

case "$SKILL_CHOICE" in
  0)
    log "Skipping skill installation."
    ;;
  1)
    SELECTED_SKILLS=("${AVAILABLE_SKILLS[@]}")
    SELECTED_PATHS=("${SKILL_PATHS[@]}")
    log "Installing all ${#SELECTED_SKILLS[@]} skills."
    ;;
  2)
    echo ""
    echo "Available skills (enter numbers, space-separated):"
    for i in "${!SKILL_LABELS[@]}"; do
      printf "  %2d) %s  (%s)\n" "$((i+1))" "${SKILL_LABELS[$i]}" "${AVAILABLE_SKILLS[$i]}"
    done
    read -rp "  Select: " SELECTED_NUMS || SELECTED_NUMS=""
    # Collected, then walked in index order. SELECTED_SKILLS is paired with
    # SKILL_PATHS by index, so entering "3 1" would otherwise install the
    # third skill's file under the first skill's name.
    _picked=""
    for num in $SELECTED_NUMS; do
      idx=$((num-1))
      if [[ $idx -ge 0 && $idx -lt ${#AVAILABLE_SKILLS[@]} ]]; then
        _picked="$_picked $idx"
      fi
    done
    for idx in $(echo $_picked | tr ' ' '\n' | sort -n -u); do
      SELECTED_SKILLS+=("${AVAILABLE_SKILLS[$idx]}")
      SELECTED_PATHS+=("${SKILL_PATHS[$idx]}")
    done
    log "Selected ${#SELECTED_SKILLS[@]} skills."
    ;;
  *)
    error "Invalid choice"; exit 1 ;;
esac
fi

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

# Retire the command copies of the-super-lab skills an earlier release wrote
# here; Step 11b now deploys them as skills. Removed only while still identical
# to the source, so a copy someone edited is kept and reported instead. Done
# before step 11 mirrors this directory into OpenCode, so no mirror link is left
# pointing at a removed file.
for _src in "$THE_SUPER_LAB_DIR"/skills/*/SKILL.md "$THE_SUPER_LAB_DIR"/personal-skills/*/SKILL.md; do
  [[ -f "$_src" ]] || continue
  _old="$CLAUDE_DIR/$(basename "$(dirname "$_src")").md"
  [[ -f "$_old" && ! -L "$_old" ]] || continue
  if cmp -s "$_src" "$_old"; then
    rm -f "$_old"
    ok "  Retired command copy: ${_old##*/} (now a skill)"
  else
    warn "  Kept ${_old##*/}: it differs from the-super-lab, so it may hold local edits. It duplicates the skill of the same name."
  fi
done

if [[ ${#SELECTED_SKILLS[@]} -gt 0 ]]; then
  echo ""
  log "Installing skills to Claude Code..."
  for i in "${!SELECTED_SKILLS[@]}"; do
    install_skill "${SELECTED_PATHS[$i]}" "$CLAUDE_DIR"
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

  # Retire the pre-2026 layout: an earlier release symlinked each skill as
  # $OPENCODE_DIR/<name>/SKILL.md. Nothing reads a directory named
  # `instructions` -- OpenCode takes skills from <config>/skill and
  # <config>/skills, and commands from {command,commands}/**/*.md -- so these
  # were inert the day they were written and only accumulated. Eleven of them
  # were still sitting here.
  #
  # A directory goes only when its sole entry is a symlink named SKILL.md, which
  # is exactly and only what that release produced. rmdir is the guard: it
  # refuses a directory that turns out to hold anything else, so a guess here
  # cannot delete real content.
  for legacy in "$OPENCODE_DIR"/*/; do
    [[ -d "$legacy" && ! -L "${legacy%/}" && -L "${legacy}SKILL.md" ]] || continue
    [[ "$(find "$legacy" -mindepth 1 -maxdepth 1 | wc -l)" -eq 1 ]] || continue
    if rm -f "${legacy}SKILL.md" && rmdir "${legacy}" 2>/dev/null; then
      pruned=$((pruned + 1))
    fi
  done

  [[ $pruned -gt 0 ]] && ok "  Pruned $pruned stale OpenCode entr(y|ies)"
  ok "OpenCode sync complete."
fi

# =============================================================================
# Step 11b — Deploy the-super-lab skills to Claude, Cursor, and OpenCode
# =============================================================================
# the-super-lab is the source of truth. Each skill deploys to three harnesses:
#   Claude Code  ~/.claude/skills/<name>/SKILL.md                (directory copy)
#   Cursor       ~/.cursor/skills/<name>/SKILL.md                (directory copy)
#   OpenCode     <opencode dir>/<name>                            (symlink to source)
# Directory copies keep sibling files (domain-modeling/ADR-FORMAT.md) with the
# skill; a flattened SKILL.md copy silently drops them.
#
# Both source trees deploy: skills/ into the-super-lab, personal-skills/ into
# the-super-lab-personal. Keeping the OpenCode mirrors apart means a personal
# skill cannot silently shadow a same-named the-super-lab skill.
if [[ -d "$THE_SUPER_LAB_DIR" ]]; then
  echo ""
  log "Deploying the-super-lab skills to Claude, Cursor, OpenCode..."

  # Copy the top-level files of one skill into <dest_root>/<name>. A sibling
  # directory (tests/) stays behind; SKILL.md does not reference it at runtime.
  deploy_skill_copy() {
    local src_dir="$1" dest_root="$2" name="$3"
    local target="$dest_root/$name"
    local f dst
    mkdir -p "$target"
    for f in "$src_dir"/*; do
      [[ -f "$f" ]] || continue
      dst="$target/$(basename "$f")"
      # -ef catches a destination symlinked back to the source. cp reports
      # "same file" and exits 1 there, which under set -e aborted the whole
      # install part-way through the skill loop.
      if [[ -e "$dst" && "$f" -ef "$dst" ]]; then
        continue
      fi
      cp "$f" "$dst"
    done
  }

  deploy_superlab_tree() {
    local src_root="$1" opencode_dir="$2" label="$3"
    local skill_dir skill_file name deployed=0
    [[ -d "$src_root" ]] || { warn "No $label at $src_root — skipping."; return; }
    for skill_dir in "$src_root"/*/; do
      [[ -d "$skill_dir" ]] || continue
      skill_file="${skill_dir}SKILL.md"
      [[ -f "$skill_file" ]] || continue
      name="$(basename "$skill_dir")"

      deploy_skill_copy "${skill_dir%/}" "$HOME/.claude/skills" "$name"
      deploy_skill_copy "${skill_dir%/}" "$CURSOR_SKILLS_DIR" "$name"

      # OpenCode — symlink the whole directory to the source
      if [[ -e "$opencode_dir/$name" && ! -L "$opencode_dir/$name" ]]; then
        rm -rf "$opencode_dir/$name"
      fi
      ln -sfn "${skill_dir%/}" "$opencode_dir/$name"

      deployed=$((deployed + 1))
    done
    ok "Deployed $deployed $label skill(s) to Claude, Cursor, and OpenCode."
  }

  mkdir -p "$HOME/.claude/skills" "$CURSOR_SKILLS_DIR" \
           "$THE_SUPER_LAB_OPENCODE_DIR" "$THE_SUPER_LAB_OPENCODE_PERSONAL_DIR"

  deploy_superlab_tree "$THE_SUPER_LAB_DIR/skills" \
                       "$THE_SUPER_LAB_OPENCODE_DIR" "the-super-lab"
  deploy_superlab_tree "$THE_SUPER_LAB_DIR/personal-skills" \
                       "$THE_SUPER_LAB_OPENCODE_PERSONAL_DIR" "personal-skills"
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
  # docs/state is constants.STATE_DIR; asked for rather than written out, so
  # the ignore rule and the directory the state files go into are the same fact.
  STATE_DIR=$(python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT/src')
from coworker.constants import STATE_DIR
print(STATE_DIR)
" 2>/dev/null || echo "docs/state")
  for entry in "personal/" ".local_config.yaml" ".env" ".cursorrules" "AGENTS.md" "GEMINI.md" "CLAUDE.local.md" "$STATE_DIR/"; do
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
import json, re
with open('$CLAUDE_SETTINGS') as f: cfg = json.load(f)
cfg.setdefault('hooks', {})

# A hook counts as present when cmd is the whole command or one step of a
# compound one. A machine that joined capture and close into one async hook
# with a semicolon got both added back as separate hooks on every install, so
# session-end capture, an LLM call, ran twice.
def _steps(command):
    return [s.strip() for s in re.split(r';|&&|[|][|]', command or '')]

def _merge_hook(event, cmd):
    entries = cfg['hooks'].setdefault(event, [])
    has_it = any(
        cmd in _steps(h.get('command'))
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
# Session summary: memory capture (one LLM call) then memory close, which folds
# the result into graph.json. It ran on Stop, which fires after every reply, so
# it made one 15-20 s LLM call per reply. Stop now only records the chat
# (on-stop.sh imports it into analytics.db); the summary runs once, when the
# session ends. on-session-end.sh detaches the work, because Claude Code
# cancels a SessionEnd hook after 1.5 s.
#
# Earlier installs put capture and close on Stop, alone or joined into one
# compound hook; those steps are taken off Stop here.
#
# NOTE: this block is a double-quoted bash string. A double quote in these
# comments ends it early; a backtick or dollar-paren runs a command and splices
# the output in. Describe such characters in words; never write them.
_OLD_STOP_STEPS = {'coworker memory capture', 'coworker memory close'}
_stop = []
for g in cfg['hooks'].get('Stop', []):
    if isinstance(g, dict) and isinstance(g.get('hooks'), list):
        kept = [h for h in g['hooks']
                if not (isinstance(h, dict)
                        and set(_steps(h.get('command'))) <= _OLD_STOP_STEPS)]
        if not kept:
            continue
        g = {**g, 'hooks': kept}
    _stop.append(g)
if 'Stop' in cfg['hooks']:
    cfg['hooks']['Stop'] = _stop
_merge_hook('SessionEnd',        '$HOME/.coworker/analytics/hooks/on-session-end.sh')

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
MANIFEST_SUPERLAB_PERSONAL=""
if [[ -d "$THE_SUPER_LAB_DIR/personal-skills" ]]; then
  for _d in "$THE_SUPER_LAB_DIR/personal-skills"/*/; do
    [[ -f "${_d}SKILL.md" ]] && MANIFEST_SUPERLAB_PERSONAL+="$(basename "$_d") "
  done
fi

python3 -c "
import json, os, glob, shutil
home = os.environ['HOME']
claude_dir = '${CLAUDE_DIR}'
selected = '${MANIFEST_SKILLS}'.split()
deployed = '${MANIFEST_SUPERLAB}'.split()
deployed_personal = '${MANIFEST_SUPERLAB_PERSONAL}'.split()
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
    # Not {home}: in project mode these are written under $PROJECT_PATH, so
    # claiming the home path meant uninstall removed nothing here and left
    # every mirror behind as a dangling symlink.
    claim(f'$OPENCODE_DIR/{name}.md')

# the-super-lab skills deployed in step 11b, by name: the Claude and Cursor
# directory copies, and the OpenCode symlink. The OpenCode symlink was not
# claimed before, and the comment here claimed owned_dirs covered it — it does
# not, it holds only .../skills/walter-worker. So a skill dropped from the
# source left a symlink to a deleted directory behind for ever.
#
# A Claude or Cursor target that is itself a symlink back into the-super-lab is
# claimed as that link, never walked: walking it would claim the source files,
# and uninstall would then delete them out of the repository.
def claim_tree(root):
    if os.path.islink(root):
        claim(root)
        return
    for dirpath, _dirs, fns in os.walk(root):
        for fn in fns:
            claim(os.path.join(dirpath, fn))

for name in deployed:
    claim(f'$THE_SUPER_LAB_OPENCODE_DIR/{name}')
    claim_tree(f'{home}/.claude/skills/{name}')
    claim_tree(f'{home}/.cursor/skills/{name}')

# personal-skills/ deploys to its own OpenCode mirror, so a personal skill never
# shadows a same-named the-super-lab skill (and vice versa).
for name in deployed_personal:
    claim(f'$THE_SUPER_LAB_OPENCODE_PERSONAL_DIR/{name}')
    claim_tree(f'{home}/.claude/skills/{name}')
    claim_tree(f'{home}/.cursor/skills/{name}')

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
# Global CLAUDE.md — only if an install created it. Claiming it whenever it
# existed meant a user's own hand-written CLAUDE.md was deleted by uninstall,
# on a file install.sh had just deliberately declined to touch.
# The claim is carried forward once made: only the run that created the file
# could claim it, so the next run dropped the claim and its own prune then
# deleted the file the previous run had created, edits and all.
try:
    _prev_claims = set(json.load(open('$MANIFEST')).get('files', []))
except Exception:
    _prev_claims = set()
md = f'{home}/.claude/CLAUDE.md'
if os.path.isfile(md) and ('$CREATED_GLOBAL_MD' == '1' or md in _prev_claims):
    manifest['files'].append(md)
# The upgrade merge base is always ours, whether install or upgrade wrote it.
merge_base = f'{home}/.coworker/claude-md-base.md'
if os.path.isfile(merge_base):
    manifest['files'].append(merge_base)
# Hook commands from settings.json — only the ones this project installs.
#
# This used to claim every hook in the file, including the user's own, so
# uninstall stripped their hooks along with ours. Ours are identifiable: they
# point into our hooks directory, or they are our own CLI subcommands.
sf = f'{home}/.claude/settings.json'
OUR_HOOK_PATH = '/.coworker/analytics/hooks/'
OUR_HOOK_CMDS = ('coworker memory capture', 'coworker memory close', 'coworker state-update')
if os.path.isfile(sf):
    cfg = json.load(open(sf))
    for entries in cfg.get('hooks', {}).values():
        if isinstance(entries, list):
            for g in entries:
                if isinstance(g, dict):
                    for h in g.get('hooks', []):
                        cmd = h.get('command', '')
                        if OUR_HOOK_PATH in cmd or cmd in OUR_HOOK_CMDS:
                            manifest['hook_commands'].append(cmd)
# Owned dirs
# Not ~/.coworker: it holds the user's .env, coworker.yaml and memory graph,
# which install.sh never writes, and uninstall emptied whatever was listed here.
for d in [f'{home}/.config/opencode/skills/walter-worker']:
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
              f'{home}/.cursor/skills',
              f'{home}/.config/opencode/skills/walter-worker',
              f'{home}/.config/opencode/skills/the-super-lab',
              f'{home}/.config/opencode/skills/the-super-lab-personal')

    def _retire_empty(d):
        while any(d.startswith(t + os.sep) for t in _trees):
            try:
                os.rmdir(d)
            except OSError:
                return
            d = os.path.dirname(d)

    # Answering None means do not install skills — it is not an instruction to
    # delete the ones already present. The prune is a diff against what this run
    # claimed, and a run that skipped skills claims none of them, so they were
    # all retired. update.sh re-invokes this installer with None as the default
    # answer, so pressing Enter during an update wiped every skill on the
    # machine, including the core init skill the same run had just reported
    # installing. Carry the previous bundle skills forward instead; the mirrors
    # the-super-lab feeds are deployed regardless of this answer and are still
    # pruned normally below.
    _carried = 0
    if '$SKILL_CHOICE' == '0':
        for _p in _prev.get('files', []):
            if _p.startswith(f'{home}/.claude/commands/') and os.path.lexists(_p):
                files.append(_p)
                _carried += 1
        if _carried:
            print(f'  Skills skipped, so {_carried} existing skill(s) were kept.')

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
