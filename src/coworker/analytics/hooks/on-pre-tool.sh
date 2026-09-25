#!/usr/bin/env bash
source "${0%/*}/common.sh"
raw=$(cat)
ensure_session "$raw"

# One interpreter, one parse. This started three — one per field — on the path
# that runs before every tool call.
tool=""; call_id=""; args=""
{ read -r tool; read -r call_id; read -r args; } < <(echo "$raw" | python3 -c "
import sys, json
d = json.load(sys.stdin)
print(d.get('tool_name', ''))
print(d.get('tool_use_id', ''))
print(json.dumps(d.get('tool_input', {})))
" 2>/dev/null)
seq=$(next_seq)
ts=$(date '+%Y-%m-%dT%H:%M:%S%z')

# The payload fields are escaped before they are interpolated. A quote
# or backslash in any of them broke the JSONL line, and both importers
# skip a line they cannot parse — so the record vanished silently.
printf '{"ts":"%s","phase":"before","tool":"%s","tool_type":"builtin","call_id":"%s","seq":%s,"args":%s}' \
  "$ts" "$(escape_json "$tool")" "$(escape_json "$call_id")" "$seq" "${args:-null}" | append_jsonl "tools.jsonl"
