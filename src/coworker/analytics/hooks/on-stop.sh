#!/usr/bin/env bash
source "${0%/*}/common.sh"
raw=$(cat)
ensure_session "$raw"

# idlempotently write closed: line (replace if present, don't append per turn)
if grep -q "^closed:" "$SESSIONS/$SESSION_ID/session.yaml" 2>/dev/null; then
  ts=$(date '+%Y-%m-%dT%H:%M:%S%z')
  sed -i "s/^closed:.*/closed: \"$ts\"/" "$SESSIONS/$SESSION_ID/session.yaml"
else
  echo "closed: \"$(date '+%Y-%m-%dT%H:%M:%S%z')\"" >> "$SESSIONS/$SESSION_ID/session.yaml"
fi

# Dedupe index entry — skip if this session is already indexed
INDEX="$BASE/index.jsonl"
if [[ -f "$INDEX" ]] && grep -qF "\"$SESSION_ID\"" "$INDEX" 2>/dev/null; then
  exit 0
fi

msg_count=$(wc -l < "$SESSIONS/$SESSION_ID/messages.jsonl" 2>/dev/null || echo 0)
tool_count=$(wc -l < "$SESSIONS/$SESSION_ID/tools.jsonl" 2>/dev/null || echo 0)
created=$(grep "created:" "$SESSIONS/$SESSION_ID/session.yaml" 2>/dev/null | head -1 | cut -d'"' -f2)

printf '{"session_id":"%s","created":"%s","ide":"claude-code","message_count":%s,"tool_count":%s}\n' \
  "$SESSION_ID" "$created" "$msg_count" "$tool_count" >> "$INDEX"
