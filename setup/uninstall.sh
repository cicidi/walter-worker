#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# walter-worker uninstall.sh — manifest-driven
# Reads ~/.coworker/install-manifest.json and removes exactly what install.sh
# recorded. User/third-party files and hook entries are never touched.
# Option: --restore-pristine restores the pre-install backup snapshot.
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="$HOME/.coworker/install-manifest.json"

YELLOW='\033[1;33m'
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

warn()  { echo -e "${YELLOW}⚠${NC}  $*"; }
error() { echo -e "${RED}✗${NC} $*"; }
ok()    { echo -e "${GREEN}✓${NC} $*"; }
log()   { echo -e "${BLUE}→${NC} $*"; }

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Walter Worker — Uninstall"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

RESTORE_PRIS=false
[[ "${1:-}" == "--restore-pristine" ]] && RESTORE_PRIS=true

if [[ ! -f "$MANIFEST" ]]; then
  error "No install manifest found at $MANIFEST"
  echo "  This may be a pre-manifest install. To clean up manually:"
  echo "  rm -rf ~/.coworker ~/.claude/commands/walter-worker-*"
  echo "  Also remove coworker hook entries from ~/.claude/settings.json hooks.*"
  exit 1
fi

echo ""
if $RESTORE_PRIS; then
  warn "This will restore your pre-install backup AND remove all coworker files."
  warn "Post-install edits to settings.json will be DISCARDED."
else
  warn "This will remove AI coworker files and hook entries."
fi
read -rp "Continue? (y/n) [n]: " CONFIRM || CONFIRM=""
CONFIRM="${CONFIRM:-n}"
[[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]] && echo "Aborted." && exit 0

# Backup settings.json before mutation
CLAUDE_SETTINGS="$HOME/.claude/settings.json"
if [[ -f "$CLAUDE_SETTINGS" ]]; then
  BACKUP_DIR="$HOME/.coworker/backups/uninstall-$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$BACKUP_DIR"
  cp "$CLAUDE_SETTINGS" "$BACKUP_DIR/settings.json"
  ok "Backup saved to $BACKUP_DIR"
fi

echo ""
log "Removing files..."

REMOVED_FILES=0
python3 -c "
import json, os
m = json.load(open('$MANIFEST'))
for f in m.get('files', []):
    p = os.path.normpath(f)
    if os.path.isfile(p) or os.path.islink(p):
        os.remove(p)
        print(f'  removed: {p}')
" | while read -r line; do
  echo "$line"
  ((REMOVED_FILES++)) || true
done

# Remove hook entries by command path
echo ""
log "Removing hook entries..."
REMOVED_HOOKS=0
if [[ -f "$CLAUDE_SETTINGS" ]]; then
  python3 -c "
import json
m = json.load(open('$MANIFEST'))
our_cmds = set(m.get('hook_commands', []))
if not our_cmds:
    print('  (no hook commands in manifest)')
    exit(0)
cfg = json.load(open('$CLAUDE_SETTINGS'))
hooks = cfg.get('hooks', {})
n = 0
for event in list(hooks.keys()):
    entries = hooks.get(event, [])
    if not isinstance(entries, list):
        continue
    cleaned = []
    for g in entries:
        if not isinstance(g, dict):
            continue
        inner = g.get('hooks', [])
        kept_inner = []
        for h in inner:
            if isinstance(h, dict) and h.get('command') in our_cmds:
                n += 1
            else:
                kept_inner.append(h)
        if kept_inner:
            g['hooks'] = kept_inner
            cleaned.append(g)
        else:
            n += 1  # entire group removed
    if cleaned:
        hooks[event] = cleaned
    else:
        hooks.pop(event, None)
if hooks:
    cfg['hooks'] = hooks
else:
    cfg.pop('hooks', None)
json.dump(cfg, open('$CLAUDE_SETTINGS', 'w'), indent=2)
print(f'  {n} hook entries removed')
" | while read -r line; do
  echo "$line"
  if [[ "$line" =~ ^[[:space:]]*([0-9]+)[[:space:]].* ]]; then
    REMOVED_HOOKS="${BASH_REMATCH[1]}"
  fi
done
fi

# Clean up owned directories
echo ""
log "Cleaning directories..."
python3 -c "
import json, shutil, os
m = json.load(open('$MANIFEST'))
for d in reversed(sorted(m.get('owned_dirs', []))):
    d = os.path.normpath(d)
    if os.path.isdir(d):
        try:
            shutil.rmtree(d)
            print(f'  removed dir: {d}')
        except OSError:
            pass  # not empty or permission issue — leave it
" 2>/dev/null || warn "Partial directory cleanup — some items may remain."

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ok "Uninstall complete!"
echo "   Files removed    : at least those in manifest"
echo "   Hook entries     : coworker entries stripped from settings.json"
echo "   Analytics data   : ~/.coworker/analytics/ (preserved — delete manually)"
echo ""
if $RESTORE_PRIS; then
  PRIS="$HOME/.coworker/backups/pristine"
  if [[ -d "$PRIS" ]]; then
    log "Restoring pristine backup from $PRIS..."
    cp "$PRIS/settings.json" "$CLAUDE_SETTINGS" 2>/dev/null || warn "Could not restore settings.json"
    cp "$PRIS/CLAUDE.md" "$HOME/.claude/CLAUDE.md" 2>/dev/null || warn "Could not restore CLAUDE.md"
  else
    warn "No pristine backup found at $PRIS"
  fi
fi
