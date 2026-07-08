#!/usr/bin/env bash
source "${0%/*}/common.sh"
raw=$(cat)
ensure_session "$raw"

tool=$(echo "$raw" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null)
call_id=$(echo "$raw" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_use_id',''))" 2>/dev/null)
args=$(echo "$raw" | python3 -c "import sys,json; d=json.load(sys.stdin); print(json.dumps(d.get('tool_input',{})))" 2>/dev/null)
seq=$(next_seq)
ts=$(date '+%Y-%m-%dT%H:%M:%S%z')

printf '{"ts":"%s","phase":"before","tool":"%s","tool_type":"builtin","call_id":"%s","seq":%s,"args":%s}' \
  "$ts" "$tool" "$call_id" "$seq" "${args:-null}" | append_jsonl "tools.jsonl"
