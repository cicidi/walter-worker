#!/usr/bin/env bash
source "${0%/*}/common.sh"
raw=$(cat)
ensure_session "$raw"

# Idempotently write the closed: line (replace if present, don't append per turn).
#
# -i takes its suffix attached because BSD sed — the one macOS ships, and this
# project supports macOS — reads a bare `-i` as "the next argument is my
# backup suffix". `sed -i "s/…/" file` therefore hands it the script as a
# suffix and fails. The hooks set no -e, so it failed silently and the session
# kept its original timestamp: every duration derived from it was wrong.
if grep -q "^closed:" "$SESSIONS/$SESSION_ID/session.yaml" 2>/dev/null; then
  ts=$(date '+%Y-%m-%dT%H:%M:%S%z')
  yaml="$SESSIONS/$SESSION_ID/session.yaml"
  sed -i.bak "s/^closed:.*/closed: \"$ts\"/" "$yaml" && rm -f "$yaml.bak"
else
  echo "closed: \"$(date '+%Y-%m-%dT%H:%M:%S%z')\"" >> "$SESSIONS/$SESSION_ID/session.yaml"
fi

# Curator (spec §4.3, "every 7 days"). Lazy check: the interval lives in
# curator.py, and --if-due answers from a stamp file without loading mem0, so
# the usual cost is one short-lived process (~0.1s) that does nothing. It must
# sit before the dedupe exit below, which skips every turn after the first.
# Deliberately not backgrounded: a child can be reaped when the hook exits,
# which would make this silently never run — the failure it exists to fix.
# The real run happens at most once per 7 days.
coworker memory curate --if-due >/dev/null 2>&1 || true

# Dedupe index entry — skip if this session is already indexed
INDEX="$BASE/index.jsonl"
if [[ -f "$INDEX" ]] && grep -qF "\"$SESSION_ID\"" "$INDEX" 2>/dev/null; then
  exit 0
fi

# Counted only when the file exists. `wc -l < missing 2>/dev/null` suppresses
# nothing: the shell opens the file for the redirection before wc runs, so the
# "No such file or directory" came from bash itself and reached stderr anyway,
# twice, for every session that had no messages or no tools.
msg_file="$SESSIONS/$SESSION_ID/messages.jsonl"
tool_file="$SESSIONS/$SESSION_ID/tools.jsonl"
msg_count=0
tool_count=0
[[ -f "$msg_file" ]] && msg_count=$(wc -l < "$msg_file")
[[ -f "$tool_file" ]] && tool_count=$(wc -l < "$tool_file")
created=$(grep "created:" "$SESSIONS/$SESSION_ID/session.yaml" 2>/dev/null | head -1 | cut -d'"' -f2)

printf '{"session_id":"%s","created":"%s","ide":"claude-code","message_count":%s,"tool_count":%s}\n' \
  "$(escape_json "$SESSION_ID")" "$(escape_json "$created")" "$msg_count" "$tool_count" >> "$INDEX"
