#!/usr/bin/env bash
# SessionEnd hook: the session summary, once per session.
#
# The summary (memory capture, one LLM call, then memory close to fold it into
# the graph) ran on the Stop hook, which fires after every reply, not once per
# session: one 15-20 s LLM call per reply. Stop now only records the chat; the
# summary moved here.
#
# Claude Code gives SessionEnd hooks 1.5 s before it cancels them, and the
# summary takes 15-20 s. So the hook saves its payload and starts the work in
# a session of its own, which outlives both the hook and the claude process,
# and returns at once. macOS has no setsid; nohup is the fallback there.
payload=$(mktemp "${TMPDIR:-/tmp}/coworker-session-end.XXXXXX") || exit 0
cat > "$payload"
run='coworker memory capture < "$1"; coworker memory close; rm -f "$1"'
if command -v setsid >/dev/null 2>&1; then
  setsid sh -c "$run" sh "$payload" </dev/null >/dev/null 2>&1 &
else
  nohup sh -c "$run" sh "$payload" </dev/null >/dev/null 2>&1 &
fi
exit 0
