#!/usr/bin/env bash

input=$(cat)
# Colors
reset=$'\033[0m'
green=$'\033[32m'
red=$'\033[31m'
magenta=$'\033[35m'
cyan=$'\033[36m'
dim=$'\033[2m'

# --- Workspace + Git context ---
workspace_dir=$(echo "$input" | jq -r '.workspace.current_dir // empty')
[ -z "$workspace_dir" ] && workspace_dir="$PWD"

# Project folder (git repo root basename)
project=""
project_dir=$(git -C "$workspace_dir" rev-parse --show-toplevel 2>/dev/null)
if [ -n "$project_dir" ]; then
  project=$(basename "$project_dir")
fi

# --- Line 1: Model + Project + Git + Context ---

# Model
model=$(echo "$input" | jq -r '.model.display_name // "Unknown"')

# Git branch + diff stats
branch=$(git -C "$workspace_dir" rev-parse --abbrev-ref HEAD 2>/dev/null)
if [ -n "$branch" ]; then
  diff_stats=$(git -C "$workspace_dir" diff --shortstat HEAD 2>/dev/null)
  added=$(echo "$diff_stats" | grep -oE '[0-9]+ insertion' | grep -oE '[0-9]+' || echo "0")
  deleted=$(echo "$diff_stats" | grep -oE '[0-9]+ deletion' | grep -oE '[0-9]+' || echo "0")
  [ -z "$added" ] && added=0
  [ -z "$deleted" ] && deleted=0
  git_info="🌿 ${branch} ${green}+${added}${reset}/${red}-${deleted}${reset}"
else
  git_info="🌿 no git"
fi

# Project display
if [ -n "$project" ]; then
  project_str="${cyan}📁${reset} ${project}"
else
  project_str="${cyan}📁${reset} $(basename "$workspace_dir")"
fi

# Context bar
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // 0')
used_int=${used_pct%.*}
used_int=${used_int:-0}

bar_filled=$(( used_int / 5 ))
bar_empty=$(( 20 - bar_filled ))
bar=""
for ((i=0; i<bar_filled; i++)); do bar+="█"; done
for ((i=0; i<bar_empty; i++)); do bar+="░"; done

if [ "$used_int" -lt 50 ]; then
  bar_color=$'\033[32m'   # green
elif [ "$used_int" -lt 80 ]; then
  bar_color=$'\033[33m'   # yellow
else
  bar_color=$'\033[31m'   # red
fi

context_bar="💭 ${bar_color}${bar}${reset} ${used_int}%"

# --- Initiative: from CLAUDE.local.md ---
initiative=""
for dir in "$workspace_dir" "$project_dir" "$HOME"; do
  if [ -n "$dir" ] && [ -f "$dir/CLAUDE.local.md" ]; then
    initiative=$(sed -n 's/.*<!--\s*INITIATIVE:\([^ ]*\)\s*START\s*-->.*/\1/p' "$dir/CLAUDE.local.md" 2>/dev/null | head -1)
    [ -n "$initiative" ] && break
  fi
done

# Shorten path for display
path_display="$workspace_dir"
case "$path_display" in
  "$HOME/"*) path_display="~/${path_display#$HOME/}" ;;
esac

# --- Line 2: Cost + Time + Path + Initiative ---

cache_file="$HOME/.claude/ccusage-cache.json"
cache_max_age=300  # 5 minutes in seconds

needs_refresh=1
if [ -f "$cache_file" ]; then
  cache_mtime=$(stat -c %Y "$cache_file" 2>/dev/null || stat -f %m "$cache_file" 2>/dev/null)
  now=$(date +%s)
  if [ $(( now - cache_mtime )) -lt $cache_max_age ]; then
    needs_refresh=0
  fi
fi

if [ "$needs_refresh" -eq 1 ]; then
  ccusage_out=$(ccusage blocks --json 2>/dev/null)
  if [ -n "$ccusage_out" ] && echo "$ccusage_out" | jq . >/dev/null 2>&1; then
    echo "$ccusage_out" > "$cache_file"
  fi
fi

if [ -f "$cache_file" ]; then
  ccusage_out=$(cat "$cache_file")
  active_block=$(echo "$ccusage_out" | jq '[.blocks[] | select(.isActive == true)] | last')
  if [ -z "$active_block" ] || [ "$active_block" = "null" ]; then
    active_block=$(echo "$ccusage_out" | jq '.blocks | last')
  fi

  cost_usd=$(echo "$active_block" | jq -r '.costUSD // 0')
  cost_str=$(printf "💰 \$%.2f spent" "$cost_usd")

  end_time=$(echo "$active_block" | jq -r '.endTime // empty')
  if [ -n "$end_time" ]; then
    # Pure bash time calculation (cross-platform)
    end_epoch=$(date -jf "%Y-%m-%dT%H:%M:%S" "${end_time%%.*}" +%s 2>/dev/null || \
                date -d "${end_time}" +%s 2>/dev/null || \
                echo "0")
    now_epoch=$(date +%s)
    diff_secs=$(( end_epoch - now_epoch ))
    if [ "$diff_secs" -gt 0 ]; then
      hours=$(( diff_secs / 3600 ))
      mins=$(( (diff_secs % 3600) / 60 ))
      time_str="⏱️  ${hours}h ${mins}m until reset"
    else
      time_str="⏱️  resetting…"
    fi
  else
    time_str="⏱️  —"
  fi
else
  cost_str="💰 —"
  time_str="⏱️  —"
fi

# --- Output ---
echo "🤖 ${model}   ${project_str}   ${git_info}   ${context_bar}"

line2="${cost_str}   ${time_str}   ${dim}📂${reset} ${path_display}"
[ -n "$initiative" ] && line2="${line2}   ${magenta}🎯${reset} ${initiative}"
echo "$line2"
