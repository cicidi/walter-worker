#!/usr/bin/env bash
source "${0%/*}/common.sh"
raw=$(cat)
ensure_session "$raw"

tool=$(echo "$raw" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>/dev/null)
call_id=$(echo "$raw" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_use_id',''))" 2>/dev/null)
result=$(echo "$raw" | python3 -c "import sys,json; d=json.load(sys.stdin); o=d.get('tool_output',''); print(json.dumps(str(o)[:10000]))" 2>/dev/null)
duration=$(echo "$raw" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('duration_ms',0))" 2>/dev/null)
seq=$(next_seq)
ts=$(date '+%Y-%m-%dT%H:%M:%S%z')

printf '{"ts":"%s","phase":"after","tool":"%s","tool_type":"builtin","call_id":"%s","seq":%s,"result":%s,"duration_ms":%s}' \
  "$ts" "$tool" "$call_id" "$seq" "${result:-null}" "${duration:-0}" | append_jsonl "tools.jsonl"
