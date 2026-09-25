#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# walter-worker update.sh
# Updates coworker itself from upstream. Optionally updates skill-factory.
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
if [[ -f "$CONFIG" ]]; then
  SAVED_MODE=$(grep "install_mode:" "$CONFIG" 2>/dev/null | awk '{print $2}' || echo "global")
  bash "$SCRIPT_DIR/install.sh" "--$SAVED_MODE"
else
  bash "$SCRIPT_DIR/install.sh" --global
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
  log "the-super-lab not found at $THE_SUPER_LAB_DIR. Run install.sh first to set it up."
fi

echo ""
ok "Update complete!"
