#!/usr/bin/env bash
source "${0%/*}/common.sh"
raw=$(cat)
ensure_session "$raw"

# `prompt` is a top-level sibling of session_id. There is no `data` wrapper in
# any Claude Code hook payload, so reading data.prompt returned "" for every
# prompt ever recorded — every messages.jsonl entry was the string "\n".
prompt=$(echo "$raw" | python3 -c "import sys,json; print(json.load(sys.stdin).get('prompt',''))" 2>/dev/null || echo "")
seq=$(next_seq)
ts=$(date '+%Y-%m-%dT%H:%M:%S%z')
# printf, not echo: echo appends a newline, so every recorded prompt carried a
# trailing "\n" that was never part of what the user typed.
escaped=$(printf '%s' "$prompt" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null || echo "\"$prompt\"")

printf '{"ts":"%s","type":"user","seq":%s,"content":%s}' "$ts" "$seq" "$escaped" | append_jsonl "messages.jsonl"
