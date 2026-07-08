#!/usr/bin/env bash
source "${0%/*}/common.sh"
raw=$(cat)
ensure_session "$raw"

prompt=$(echo "$raw" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data',{}).get('prompt',''))" 2>/dev/null || echo "")
seq=$(next_seq)
ts=$(date '+%Y-%m-%dT%H:%M:%S%z')
escaped=$(echo "$prompt" | python3 -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null || echo "\"$prompt\"")

printf '{"ts":"%s","type":"user","seq":%s,"content":%s}' "$ts" "$seq" "$escaped" | append_jsonl "messages.jsonl"
