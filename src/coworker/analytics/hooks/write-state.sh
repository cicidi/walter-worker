#!/usr/bin/env bash
BASE="$HOME/.coworker/status"

write_state() {
  local ide="$1"
  local dir="$BASE/$ide"
  mkdir -p "$dir"

  local file="$dir/current.state"
  > "$file"
  for pair in "${@:2}"; do
    echo "$pair" >> "$file"
  done
}

read_state() {
  local ide="$1" key="$2"
  local file="$BASE/$ide/current.state"
  if [[ -f "$file" ]]; then
    grep "^${key}=" "$file" 2>/dev/null | head -1 | cut -d= -f2-
  fi
}
