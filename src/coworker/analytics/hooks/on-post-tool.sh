#!/usr/bin/env bash
source "${0%/*}/common.sh"
raw=$(cat)
ensure_session "$raw"

# record.py builds the line with json.dumps and numbers it under a lock;
# see its docstring for the two ways the old field-by-field version broke.
echo "$raw" | python3 "${0%/*}/record.py" after "$SEQ_FILE" "$SESSIONS/$SESSION_ID/tools.jsonl" 2>/dev/null || true
