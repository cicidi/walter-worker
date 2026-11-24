#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# walter-worker update.sh
# Updates coworker itself from upstream. Optionally updates the-super-lab,
# which is what skill-factory was renamed to — the script itself has used
# THE_SUPER_LAB_DIR for a while, so this line was the last thing still saying
# the old name.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
THE_SUPER_LAB_DIR="${THE_SUPER_LAB_DIR:-$HOME/project/the-super-lab}"

default_branch() {
    local ref
    ref=$(git ls-remote --symref origin HEAD 2>/dev/null | \
          awk '/^ref:/ {sub("refs/heads/","",$2); print $2}')
    echo "${ref:-main}"
}

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}→${NC} $*"; }
ok()  { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC}  $*"; }

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Walter Worker — Update"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# =============================================================================
# Step 1 — Update coworker repository
# =============================================================================
log "Updating walter-worker..."

cd "$REPO_ROOT"

BRANCH="$(default_branch)"
before=$(git rev-parse HEAD)

if ! git remote get-url upstream &>/dev/null; then
  log "Fetching from origin ($BRANCH)..."
  if git fetch origin "$BRANCH"; then
    git merge "origin/$BRANCH" --no-edit || {
      warn "Merge conflict or local changes detected. Resolve manually."
      exit 1
    }
  else
    warn "Could not fetch from origin. Is the network available?"
    exit 1
  fi
else
  log "Fetching from upstream ($BRANCH)..."
  if git fetch upstream "$BRANCH"; then
    git merge "upstream/$BRANCH" --no-edit || {
      warn "Merge conflict or local changes detected. Resolve manually."
      exit 1
    }
  else
    warn "Could not fetch upstream."
    exit 1
  fi
fi

after=$(git rev-parse HEAD)
if [[ "$before" == "$after" ]]; then
  ok "walter-worker repository already up to date"
else
  ok "walter-worker repository updated ($before → $after)"
fi

# =============================================================================
# Step 2 — Re-run install with saved mode
# =============================================================================
log "Re-running install to sync skills..."

CONFIG="$HOME/.coworker/coworker.yaml"
MANIFEST="$HOME/.coworker/install-manifest.json"

# install.sh records the install mode in the manifest — install_mode is never
# written to coworker.yaml. Reading it from the yaml therefore matched nothing,
# and the `|| echo global` fallback hid that (it fires because grep's non-zero
# status propagates under pipefail), so the mode was always "global" no matter
# how the machine had been installed: setup/update.sh on a project-mode install
# re-installed globally, without saying so.
SAVED_MODE=""
PROJECT_PATH=""
if [[ -f "$MANIFEST" ]]; then
  SAVED_MODE=$(python3 -c "
import json, sys
print(json.load(open(sys.argv[1])).get('install_mode') or '')
" "$MANIFEST" 2>/dev/null || true)
  PROJECT_PATH=$(python3 -c "
import json, sys
print(json.load(open(sys.argv[1])).get('project_path') or '')
" "$MANIFEST" 2>/dev/null || true)
  # The skills the last install selected, derived from the files it claimed.
  # Passed back so the re-install does not re-ask a question whose answer is on
  # disk — and cannot take the default answer, which is None, on a run nobody
  # is watching. That default is what let an update uninstall every skill.
  SAVED_SKILLS=$(python3 -c "
import json, os, sys
m = json.load(open(sys.argv[1]))
names = []
for f in m.get('files', []):
    parts = os.path.normpath(f).split(os.sep)
    if len(parts) >= 2 and parts[-2] == 'commands' and f.endswith('.md'):
        names.append(os.path.basename(f)[:-3])
print(' '.join(dict.fromkeys(names)))
" "$MANIFEST" 2>/dev/null || true)
fi
# Fall back to the yaml for manifests predating schema_version, then to global.
if [[ -z "$SAVED_MODE" && -f "$CONFIG" ]]; then
  SAVED_MODE=$(sed -n 's/^install_mode:[[:space:]]*//p' "$CONFIG" 2>/dev/null | head -1 || true)
fi
SAVED_MODE="${SAVED_MODE:-global}"
log "Resuming install in mode: $SAVED_MODE"

# --project takes its path as an argument, so project mode has to pass the
# recorded one; `--project` alone would fail the same way `--` did.
SKILLS_ARG=()
if [[ -n "${SAVED_SKILLS:-}" ]]; then
  SKILLS_ARG=(--skills "$SAVED_SKILLS")
  log "Reusing the previous skill selection: ${SAVED_SKILLS// /, }"
fi

if [[ "$SAVED_MODE" == "project" && -n "$PROJECT_PATH" ]]; then
  bash "$SCRIPT_DIR/install.sh" --project "$PROJECT_PATH" "${SKILLS_ARG[@]+"${SKILLS_ARG[@]}"}"
else
  bash "$SCRIPT_DIR/install.sh" --global "${SKILLS_ARG[@]+"${SKILLS_ARG[@]}"}"
fi

# =============================================================================
# Step 3 — Optionally update the-super-lab
# =============================================================================
echo ""
if [[ -d "$THE_SUPER_LAB_DIR/.git" ]]; then
  read -rp "  Update the-super-lab from GitHub? (y/n) [n]: " UPDATE_SL || UPDATE_SL=""
  UPDATE_SL="${UPDATE_SL:-n}"
  if [[ "$UPDATE_SL" == "y" || "$UPDATE_SL" == "Y" ]]; then
    log "Updating the-super-lab..."
    git -C "$THE_SUPER_LAB_DIR" pull --ff-only 2>/dev/null && \
      ok "the-super-lab updated" || \
      warn "Could not update the-super-lab (dirty, offline, or no upstream)."
  else
    log "Skipped the-super-lab update."
  fi
else
  # The test is for a .git directory, so a plain checkout lands here while
  # sitting right there — and the old wording said it was not found at
  # all, in a run that had just deployed skills from it.
  log "$THE_SUPER_LAB_DIR is not a git checkout, so it was not pulled. Skills from it were still deployed."
fi

echo ""
ok "Update complete!"
