#!/usr/bin/env bash
BASE="$HOME/.coworker/analytics"
SESSIONS="$BASE/sessions"

generate_session_id() {
  echo "$(date +%Y-%m-%d-T%H%M%S)-$(openssl rand -hex 3)"
}

# Parse session_id from stdin JSON (is piped in via ensure_session's caller).
# Claude Code never sets $SESSION_ID env var; the real id is in the hook JSON.
_parse_session_id() {
  echo "$1" | python3 -c "import sys,json; print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null || true
}

ensure_session() {
  local input="$1"
  local sid
  sid=$(_parse_session_id "$input")

  if [[ -n "$sid" ]]; then
    SESSION_ID="$sid"
    if [[ ! -d "$SESSIONS/$SESSION_ID" ]]; then
      mkdir -p "$SESSIONS/$SESSION_ID"
      cat > "$SESSIONS/$SESSION_ID/session.yaml" <<YAML
session_id: "$SESSION_ID"
created: "$(date '+%Y-%m-%dT%H:%M:%S%z')"
ide: "claude-code"
cwd: "$(pwd)"
YAML
    fi
  else
    # Quarantine — no session_id in the JSON payload
    mkdir -p "$SESSIONS/_unattributed"
    SESSION_ID="_unattributed"
  fi
  SEQ_FILE="$SESSIONS/$SESSION_ID/.seq"
}

next_seq() {
  local seq=0
  [[ -f "$SEQ_FILE" ]] && seq=$(cat "$SEQ_FILE")
  seq=$((seq + 1))
  echo "$seq" > "$SEQ_FILE"
  echo "$seq"
}

append_jsonl() {
  local file="$1" json="${2:-}"
  if [[ -z "$json" ]]; then
    json=$(cat)
  fi
  echo "$json" >> "$SESSIONS/$SESSION_ID/$file" 2>/dev/null || true
}

escape_json() {
  echo "$1" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr -d '\n'
}
