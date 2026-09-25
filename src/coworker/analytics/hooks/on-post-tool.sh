#!/usr/bin/env bash
source "${0%/*}/common.sh"
raw=$(cat)
ensure_session "$raw"

# One interpreter, one parse. This started four — one per field — on the path
# that runs after every tool call, so seven processes were started per call
# counting the PreToolUse hook, to read one JSON object.
tool=""; call_id=""; result=""; duration=""
{ read -r tool; read -r call_id; read -r result; read -r duration; } < <(echo "$raw" | python3 -c "
import sys, json
d = json.load(sys.stdin)
o = d.get('tool_response')
o = d.get('tool_output', '') if o is None else o
print(d.get('tool_name', ''))
print(d.get('tool_use_id', ''))
print(json.dumps(str(o)[:10000]))
print(d.get('duration_ms', 0))
" 2>/dev/null)
seq=$(next_seq)
ts=$(date '+%Y-%m-%dT%H:%M:%S%z')

printf '{"ts":"%s","phase":"after","tool":"%s","tool_type":"builtin","call_id":"%s","seq":%s,"result":%s,"duration_ms":%s}' \
  "$ts" "$(escape_json "$tool")" "$(escape_json "$call_id")" "$seq" "${result:-null}" "${duration:-0}" | append_jsonl "tools.jsonl"
