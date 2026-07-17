#!/usr/bin/env bash
source "${0%/*}/common.sh"
source "${0%/*}/write-state.sh"
raw=$(cat)
ensure_session "$raw"

prompt=$(echo "$raw" | python3 -c "
import sys, json
d = json.load(sys.stdin)
# Try multiple possible paths for the prompt field
p = (d.get('data') or {}).get('prompt', '')
if not p:
    p = d.get('prompt', '')
if not p:
    p = (d.get('data') or {}).get('text', '')
if not p:
    p = (d.get('data') or {}).get('message', '')
print(p)
" 2>/dev/null || echo "")
seq=$(next_seq)
ts=$(date '+%Y-%m-%dT%H:%M:%S%z')
escaped=$(echo "$prompt" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null || echo "\"$prompt\"")

printf '{"ts":"%s","type":"user","seq":%s,"content":%s}' "$ts" "$seq" "$escaped" | append_jsonl "messages.jsonl"

model=$(python3 -c "import json,sys; c=json.load(open('$HOME/.claude/settings.json')); print(c.get('model',''))" 2>/dev/null || echo "")
project=""
branch=""
initiative=""
if git rev-parse --git-dir &>/dev/null; then
  project=$(basename "$(git rev-parse --show-toplevel 2>/dev/null)" 2>/dev/null || echo "")
  branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
  # Extract initiative from CLAUDE.local.md
  local_md="$(git rev-parse --show-toplevel 2>/dev/null)/CLAUDE.local.md"
  [ -f "$local_md" ] && initiative=$(grep -oP '<!-- INITIATIVE:\K[^ ]+' "$local_md" 2>/dev/null | head -1 || echo "")
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

# Also write model/project/branch/initiative to session.yaml so import pipeline can read them
[ -n "$model" ] && sed -i "/^model:/d" "$SESSIONS/$SESSION_ID/session.yaml" 2>/dev/null; [ -n "$model" ] && echo "model: \"$model\"" >> "$SESSIONS/$SESSION_ID/session.yaml"
[ -n "$project" ] && sed -i "/^project:/d" "$SESSIONS/$SESSION_ID/session.yaml" 2>/dev/null; [ -n "$project" ] && echo "project: \"$project\"" >> "$SESSIONS/$SESSION_ID/session.yaml"
[ -n "$branch" ] && sed -i "/^branch:/d" "$SESSIONS/$SESSION_ID/session.yaml" 2>/dev/null; [ -n "$branch" ] && echo "branch: \"$branch\"" >> "$SESSIONS/$SESSION_ID/session.yaml"
[ -n "$initiative" ] && sed -i "/^initiative:/d" "$SESSIONS/$SESSION_ID/session.yaml" 2>/dev/null; [ -n "$initiative" ] && echo "initiative: \"$initiative\"" >> "$SESSIONS/$SESSION_ID/session.yaml"
