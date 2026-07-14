#!/usr/bin/env bash
source "${0%/*}/common.sh"
source "${0%/*}/write-state.sh"
raw=$(cat)
ensure_session "$raw"

prompt=$(echo "$raw" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('prompt',''))" 2>/dev/null || echo "")
seq=$(next_seq)
ts=$(date '+%Y-%m-%dT%H:%M:%S%z')
escaped=$(echo "$prompt" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null || echo "\"$prompt\"")

printf '{"ts":"%s","type":"user","seq":%s,"content":%s}' "$ts" "$seq" "$escaped" | append_jsonl "messages.jsonl"

model=$(python3 -c "import json,sys; c=json.load(open('$HOME/.claude/settings.json')); print(c.get('model',''))" 2>/dev/null || echo "")
project=""
branch=""
if git rev-parse --git-dir &>/dev/null; then
  project=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo "")
  branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
fi

update=$(date '+%Y-%m-%dT%H:%M:%S%z')
write_state "claude" \
  "session_id=$SESSION_ID" \
  "mode=Code" \
  "model=$model" \
  "effort=default" \
  "ctx_pct=?" \
  "cost=?" \
  "project=$project" \
  "branch=$branch" \
  "path=$(pwd)" \
  "updated=$update"
