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
  echo "    - ~/.claude/skills/<name>/ for each skill install.sh deployed"
  echo "    - ~/.claude/commands/<name>.md for the bundle skills"
  echo "    - ~/.cursor/rules/<name>.md and ~/.opencode/instructions/<name>.md"
  echo "  Keep ~/.coworker/analytics/ and ~/.coworker/backups/ — this"
  echo "  script preserves both, and there is no manifest-free way to tell"
  echo "  your data from its own scripts."
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
import json, os, sys
m = json.load(open('$MANIFEST'))

# Manifest schema 1 claimed files by directory: everything under ~/.claude,
# ~/.opencode and ~/.coworker/analytics, which on a real machine is 27k+ paths
# including plugin caches, session transcripts and the analytics database the
# closing banner promises to keep. Removing from one of those destroys data
# this script exists to preserve, so refuse it and say what to do instead.
# Skipping is the safe direction: nothing is lost, and re-running install.sh
# regenerates the manifest in the current form.
if m.get('schema_version') != 2:
    print('  SKIPPED: this manifest has no schema_version, so it predates the')
    print('           fix that stopped it claiming files walter-worker never')
    print('           wrote, and may list files belonging to other tools.')
    print('           Nothing was removed. Run setup/install.sh to regenerate')
    print('           the manifest, then uninstall again.')
    sys.exit(0)

for f in m.get('files', []):
    p = os.path.normpath(f)
    if os.path.isfile(p) or os.path.islink(p):
        os.remove(p)
        print(f'  removed: {p}')
" > /tmp/.coworker-uninstall-$$ 2>/dev/null || true
cat /tmp/.coworker-uninstall-$$
# Counted here rather than in the loop: `python3 ... | while read` runs the
# loop in a subshell, so every increment was discarded and the closing banner
# could only say "at least those in manifest".
REMOVED_FILES=$(grep -c '^  removed: ' /tmp/.coworker-uninstall-$$ 2>/dev/null || true)
rm -f /tmp/.coworker-uninstall-$$

# Remove hook entries by command path
echo ""
log "Removing hook entries..."
REMOVED_HOOKS=0
if [[ -f "$CLAUDE_SETTINGS" ]]; then
  python3 -c "
import json
m = json.load(open('$MANIFEST'))
recorded = set(m.get('hook_commands', []))

# The manifest is the primary source, but it goes stale: `coworker sync` adds
# `coworker state-update` on any later run and does not rewrite the manifest,
# so uninstall left it firing while the closing banner said coworker entries
# had been stripped. These are the same patterns install.sh uses to claim its
# own hooks, so the two sides agree on what is ours.
OUR_PATH = '/.coworker/analytics/hooks/'
OUR_CMDS = {'coworker state-update', 'coworker memory capture', 'coworker memory close'}

def is_ours(cmd):
    return bool(cmd) and (cmd in recorded or cmd in OUR_CMDS or OUR_PATH in cmd)

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
            if isinstance(h, dict) and is_ours(h.get('command')):
                n += 1
            else:
                kept_inner.append(h)
        if kept_inner:
            g['hooks'] = kept_inner
            cleaned.append(g)
        else:
            # The group goes with it, but a group is a wrapper, not a hook.
            # Counting both reported 12 removals for 6 hooks.
            pass
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
#
# ~/.coworker is recorded as an owned dir, but it also holds data this script
# promises to keep: analytics/ is reported as "preserved", and backups/ holds
# the pristine snapshot --restore-pristine needs. Removing the directory whole
# deleted both, so the closing message was false and the restore below could
# never find its source.
echo ""
# Retire what the removal emptied. install.sh does this after its own prune;
# here nothing did, so 15 empty ~/.claude/skills/<name>/ survived uninstall,
# along with ~/.cursor/rules, ~/.opencode/instructions and the hooks dir —
# directories that still look installed to anything listing them.
python3 -c "
import json, os
m = json.load(open('$MANIFEST'))
# Strictly *below* these, never the roots themselves: ~/.claude/skills and
# friends are standard locations, empty or not.
TREES = [os.path.normpath(os.path.expanduser(p)) for p in (
    '~/.claude/skills', '~/.claude/commands', '~/.cursor/rules',
    '~/.opencode/instructions', '~/.config/opencode/skills/walter-worker',
    '~/.config/opencode/skills/the-super-lab', '~/.coworker/analytics/hooks',
)]
def inside(p):
    return any(p.startswith(t + os.sep) for t in TREES)

n = 0
parents = {os.path.dirname(os.path.normpath(f)) for f in m.get('files', [])}
for p in sorted(parents, key=len, reverse=True):
    cur = p
    while inside(cur):
        try:
            if not os.path.isdir(cur) or os.listdir(cur):
                break
            os.rmdir(cur)
        except OSError:
            break
        n += 1
        cur = os.path.dirname(cur)
if n:
    print(f'  removed {n} emptied directory(ies)')
" 2>/dev/null || true

log "Cleaning directories..."
python3 -c "
import json, shutil, os
m = json.load(open('$MANIFEST'))
PRESERVE = {os.path.normpath(os.path.expanduser('~/.coworker')): {'analytics', 'backups'}}
for d in reversed(sorted(m.get('owned_dirs', []))):
    d = os.path.normpath(d)
    if not os.path.isdir(d):
        continue
    keep = PRESERVE.get(d, set())
    if keep:
        for entry in sorted(os.listdir(d)):
            if entry in keep:
                print(f'  preserved: {os.path.join(d, entry)}')
                continue
            p = os.path.join(d, entry)
            try:
                shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
                print(f'  removed: {p}')
            except OSError:
                pass  # permission issue — leave it
    else:
        try:
            shutil.rmtree(d)
            print(f'  removed dir: {d}')
        except OSError:
            pass  # not empty or permission issue — leave it
" 2>/dev/null || warn "Partial directory cleanup — some items may remain."

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
ok "Uninstall complete!"
echo "   Files removed    : $REMOVED_FILES"
echo "   Hook entries     : coworker entries stripped from settings.json"
echo "   Analytics data   : ~/.coworker/analytics/ (preserved — delete manually)"
echo ""
if $RESTORE_PRIS; then
  PRIS="$HOME/.coworker/backups/pristine"
  # A marker, or any file actually in it. Snapshots written before the marker
  # existed have neither the marker nor, on a fresh machine, any file — and an
  # empty directory is an empty directory, not a backup.
  if [[ -f "$PRIS/.taken" || -f "$PRIS/settings.json" || -f "$PRIS/CLAUDE.md" ]]; then
    log "Restoring pristine backup from $PRIS..."
    cp "$PRIS/settings.json" "$CLAUDE_SETTINGS" 2>/dev/null || warn "Could not restore settings.json"
    cp "$PRIS/CLAUDE.md" "$HOME/.claude/CLAUDE.md" 2>/dev/null || warn "Could not restore CLAUDE.md"

    # Files that did not exist before the install. "Pristine" for those is
    # absent, so restoring means removing what we created — otherwise a fresh
    # machine restores to a state it was never in.
    if [[ -f "$PRIS/absent.txt" ]]; then
      while read -r p; do
        if [[ -n "$p" && -e "$p" ]]; then
          rm -f "$p" && log "  removed (was absent before install): $p"
        fi
      done < "$PRIS/absent.txt"
    fi
  else
    warn "No pristine backup found at $PRIS"
  fi
fi
