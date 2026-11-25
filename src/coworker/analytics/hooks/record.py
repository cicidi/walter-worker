"""Append one hook record to a session's JSONL file.

Usage: record.py <before|after|prompt> <seq_file> <out_file>, payload on stdin.

The hooks used to print one field per line from Python and read them back with
read -r, then splice them into JSON with printf. A field holding a newline
(Cursor's tool_use_id does) shifted every later field, so the line was invalid.
And next_seq read and rewrote .seq with no lock: tool calls run in parallel, so
two hooks took the same number, or one read the file mid-write and wrote
"seq":, which no importer can parse. Here the whole record is built by one
json.dumps, and the number is taken and the line appended under one lock.
fcntl is in the standard library on Linux and macOS; flock(1) is not on macOS.
"""
import fcntl
import json
import sys
import time

kind, seq_file, out_file = sys.argv[1:4]
try:
    d = json.load(sys.stdin)
except ValueError:
    d = {}
if not isinstance(d, dict):
    d = {}

if kind == "prompt":
    # prompt is a top-level sibling of session_id; there is no data wrapper.
    rec = {"type": "user", "content": d.get("prompt", "")}
elif kind == "before":
    rec = {"phase": "before", "tool": d.get("tool_name", ""), "tool_type": "builtin",
           "call_id": d.get("tool_use_id", ""), "args": d.get("tool_input", {})}
else:
    out = d.get("tool_response")
    out = d.get("tool_output", "") if out is None else out
    # The full output stays in the transcript, which is kept; the record keeps
    # the first 10,000 characters.
    rec = {"phase": "after", "tool": d.get("tool_name", ""), "tool_type": "builtin",
           "call_id": d.get("tool_use_id", ""), "result": str(out)[:10000],
           "duration_ms": d.get("duration_ms", 0)}

with open(seq_file, "a+") as s:
    fcntl.flock(s, fcntl.LOCK_EX)
    s.seek(0)
    try:
        seq = int(s.read().strip() or 0) + 1
    except ValueError:
        seq = 1
    s.seek(0)
    s.truncate()
    s.write(str(seq))
    s.flush()
    line = json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "seq": seq, **rec},
                      ensure_ascii=False)
    with open(out_file, "a", encoding="utf-8") as o:
        o.write(line + "\n")
