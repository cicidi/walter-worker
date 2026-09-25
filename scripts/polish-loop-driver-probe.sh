#!/usr/bin/env bash
# Polish-loop driver — runs one manager cycle every POLISH_INTERVAL seconds (default 30 min).
# Designed to run inside tmux so it survives terminal close.
# Stop:  touch .polish-loop-stop   (checked between cycles)
# Cap:   POLISH_MAX_CYCLES (default 20)
set -u

# Default to the checkout this script lives in. It used to name the author's
# absolute path, so on any other machine the default pointed at a directory
# that does not exist and the driver failed on its first mkdir.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${POLISH_REPO:-$(cd "$SCRIPT_DIR/.." && pwd)}"
echo "  resolved REPO=$REPO"
