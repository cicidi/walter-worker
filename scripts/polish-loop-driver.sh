#!/usr/bin/env bash
# Polish-loop driver — runs one manager cycle every POLISH_INTERVAL seconds (default 30 min).
# Designed to run inside tmux so it survives terminal close.
# Stop:  touch .polish-loop-stop   (checked between cycles)
# Cap:   POLISH_MAX_CYCLES (default 20)
set -u

REPO="${POLISH_REPO:-/home/cicidi/project/ai-coworker}"
STATE="$REPO/docs/state/polish-loop.md"
RUNNER="$REPO/docs/state/RUNNER.md"
STOP="$REPO/.polish-loop-stop"
LOG="$REPO/docs/state/loop.log"
MANAGER_MODEL="${POLISH_MANAGER_MODEL:-zai-coding-plan/glm-5.2}"
INTERVAL="${POLISH_INTERVAL:-1800}"
MAX_CYCLES="${POLISH_MAX_CYCLES:-20}"

mkdir -p "$REPO/docs/state" "$REPO/docs/state/tasks"
echo "[driver] START $(date -Is) repo=$REPO interval=${INTERVAL}s max=$MAX_CYCLES model=$MANAGER_MODEL" | tee -a "$LOG"

cycle=0
while (( cycle < MAX_CYCLES )); do
  if [[ -f "$STOP" ]]; then
    echo "[driver] STOP file present at cycle $cycle — exiting" | tee -a "$LOG"
    break
  fi
  cycle=$((cycle + 1))
  start=$(date +%s)
  echo "[driver] === cycle $cycle START $(date -Is) ===" | tee -a "$LOG"

  # One manager cycle. cd so opencode runs in repo context.
  cd "$REPO" || { echo "[driver] cd failed" | tee -a "$LOG"; break; }
  set +e
  opencode run --dir "$REPO" -m "$MANAGER_MODEL" "$(cat "$RUNNER")" >> "$LOG" 2>&1
  rc=$?
  set -e
  end=$(date +%s); elapsed=$((end - start))
  echo "[driver] cycle $cycle END rc=$rc elapsed=${elapsed}s" | tee -a "$LOG"

  # Read-only early-stop check: if state says no pending tasks or only needs-human left.
  if grep -q "LOOP-HALT: no actionable tasks" "$STATE" 2>/dev/null; then
    echo "[driver] LOOP-HALT marker found — exiting" | tee -a "$LOG"
    break
  fi

  remaining=$(( INTERVAL - elapsed ))
  if (( remaining > 0 )); then
    echo "[driver] sleeping ${remaining}s..." | tee -a "$LOG"
    sleep "$remaining"
  fi
done

echo "[driver] FINISHED after $cycle cycles $(date -Is)" | tee -a "$LOG"
