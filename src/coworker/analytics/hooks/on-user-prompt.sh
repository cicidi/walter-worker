#!/usr/bin/env bash
source "${0%/*}/common.sh"
raw=$(cat)
ensure_session "$raw"

# `prompt` is a top-level sibling of session_id. There is no `data` wrapper in
# any Claude Code hook payload, so reading data.prompt returned "" for every
# prompt ever recorded — every messages.jsonl entry was the string "\n".
# One interpreter, and it emits the JSON-escaped form directly. This started
# two: one to read the field, another to escape what the first returned — so
# the prompt made a second round trip through a pipe to be quoted. json.dumps
# also fixes the escaping the pipeline used to lose.
escaped="\"\""
{ read -r escaped; } < <(echo "$raw" | python3 -c "
import sys, json
print(json.dumps(json.load(sys.stdin).get('prompt', '')))
" 2>/dev/null)
seq=$(next_seq)
ts=$(date '+%Y-%m-%dT%H:%M:%S%z')

printf '{"ts":"%s","type":"user","seq":%s,"content":%s}' "$ts" "$seq" "$escaped" | append_jsonl "messages.jsonl"
