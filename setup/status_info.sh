#!/bin/sh

SESSION=$(tmux display-message -p '#{session_name}' 2>/dev/null)
PANE_PATH=$(tmux display-message -p -F '#{pane_current_path}' 2>/dev/null)

[ -d "$PANE_PATH" ] || exit 0
cd "$PANE_PATH" || exit 0

# ── State: read AI session state, prefer OpenCode over Claude ──
STATE_OP="$HOME/.coworker/status/opencode/current.state"
STATE_CL="$HOME/.coworker/status/claude/current.state"
STATE_FILE=""

if [ -f "$STATE_OP" ]; then
  STATE_FILE="$STATE_OP"
elif [ -f "$STATE_CL" ]; then
  STATE_FILE="$STATE_CL"
fi

get() { grep "^${1}=" "$STATE_FILE" 2>/dev/null | head -1 | cut -d= -f2-; }

MODE=""
MODEL=""
EFFORT=""
CTX_PCT=""
COST=""

if [ -n "$STATE_FILE" ]; then
  MODE=$(get mode)
  MODEL=$(get model)
  EFFORT=$(get effort)
  CTX_PCT=$(get ctx_pct)
  COST=$(get cost)

  update_ts=$(get updated)
  if [ -n "$update_ts" ]; then
    now=$(date +%s)
    then_ts=$(date -d "$update_ts" +%s 2>/dev/null || echo 0)
    [ $((now - then_ts)) -gt 300 ] && STATE_FILE="" # stale > 5 min
  fi
fi

[ -z "$MODE" ] && MODE="?"
[ -z "$MODEL" ] && MODEL="?"
[ -z "$EFFORT" ] && EFFORT="?"
[ -z "$CTX_PCT" ] && CTX_PCT="?%"
[ -z "$COST" ] && COST="?"

# ── Git: project, branch, worktree ──
PROJECT_DIR=$(git rev-parse --show-toplevel 2>/dev/null)

GIT_DIR=$(git rev-parse --git-dir 2>/dev/null)
GIT_COMMON=$(git rev-parse --git-common-dir 2>/dev/null)
SUPERPROJECT=$(git rev-parse --show-superproject-working-tree 2>/dev/null)
IS_WORKTREE=0
if [ "$GIT_DIR" != "$GIT_COMMON" ] && [ -z "$SUPERPROJECT" ]; then
  IS_WORKTREE=1
fi

if [ -n "$PROJECT_DIR" ]; then
  if [ "$IS_WORKTREE" -eq 1 ] && [ -n "$GIT_COMMON" ]; then
    MAIN_REPO=$(dirname "$GIT_COMMON")
    FOLDER=$(basename "$MAIN_REPO")
  else
    FOLDER=$(basename "$PROJECT_DIR")
  fi
else
  FOLDER=$(basename "$PWD")
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ "$IS_WORKTREE" -eq 1 ] && [ -n "$BRANCH" ]; then
  WORKTREE_NAME=$(basename "$GIT_DIR")
  BRANCH="${BRANCH} (${WORKTREE_NAME})"
fi

# ── Initiative: from CLAUDE.local.md ──
INITIATIVE=""
for DIR in "$PANE_PATH" "$PROJECT_DIR" "$HOME"; do
  if [ -n "$DIR" ] && [ -f "$DIR/CLAUDE.local.md" ]; then
    INITIATIVE=$(sed -n 's/.*<!--\s*INITIATIVE:\([^ ]*\)\s*START\s*-->.*/\1/p' "$DIR/CLAUDE.local.md" 2>/dev/null | head -1)
    [ -n "$INITIATIVE" ] && break
  fi
done

# ── Shorten path for display ──
PATH_DISPLAY="$PANE_PATH"
HOME_PFX="$HOME/"
case "$PATH_DISPLAY" in
  "$HOME_PFX"*) PATH_DISPLAY="~/${PATH_DISPLAY#$HOME_PFX}" ;;
esac

# ── Build output lines ──
LINE1="$MODE | ${MODEL} | ${EFFORT} | tmux:${SESSION} | project:${FOLDER}"
LINE1="${LINE1} | branch:${BRANCH:-?}"
[ -n "$INITIATIVE" ] && LINE1="${LINE1} | initiative:${INITIATIVE}"

LINE2="ctx:${CTX_PCT} | cost:\$${COST} | path:${PATH_DISPLAY}"

# ── Output based on --line argument ──
case "$1" in
  --line1) printf "%s" "$LINE1" ;;
  --line2) printf "%s" "$LINE2" ;;
  *)
    printf "#[fg=colour240]Line1:#[fg=white]%s#[fg=colour240] | Line2:#[fg=white]%s" "$LINE1" "$LINE2"
    ;;
esac
