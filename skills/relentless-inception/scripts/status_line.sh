#!/usr/bin/env bash
# status_line.sh — lightweight statusLine indicator for /relentless-inception.
#
# Shows: model + active run-id + current phase + retries remaining + last
# gate verdict. Silent (prints nothing) when no run is active.
#
# Claude Code calls this with a JSON payload on stdin; we read the model from
# there and the run state from the runs/ directory.

set -uo pipefail

payload=$(cat)

if command -v jq >/dev/null 2>&1; then
  model=$(printf '%s' "$payload" | jq -r '.model.display_name // .model.id // "claude"' 2>/dev/null)
else
  model="claude"
fi

RUNS_DIR=~/.claude/relentless-inception/runs

# Find the most recently modified manifest.json — that's the active run.
manifest=""
if [[ -d "$RUNS_DIR" ]]; then
  manifest=$(find "$RUNS_DIR" -maxdepth 2 -name manifest.json -type f 2>/dev/null \
             | xargs -I{} stat -f "%m %N" {} 2>/dev/null \
             | sort -rn | head -1 | awk '{print $2}' || echo "")
fi

if [[ -z "$manifest" ]] || [[ ! -f "$manifest" ]]; then
  # No active run — show only model.
  printf '%s' "$model"
  exit 0
fi

if command -v jq >/dev/null 2>&1; then
  run_id=$(jq -r '.run_id // "?"' "$manifest")
  current_phase=$(jq -r '
    [.phases[]? | select(.completed == false)][0].name // "(complete)"
  ' "$manifest")
  retries=$(jq -r '
    [.phases[]?.units[]? | select(.retries > 0)] | length
  ' "$manifest")
  last_verdict=$(jq -r '
    .gate_history[-1].verdict // "—"
  ' "$manifest" 2>/dev/null)
else
  run_id="?"; current_phase="?"; retries="?"; last_verdict="—"
fi

# Color codes — work in most terminals, silently ignored elsewhere.
RUN_COLOR=$'\033[36m'   # cyan
PHASE_COLOR=$'\033[35m' # magenta
WARN_COLOR=$'\033[33m'  # yellow
RESET=$'\033[0m'

retries_part=""
if [[ "$retries" != "0" ]] && [[ "$retries" != "?" ]]; then
  retries_part=" ${WARN_COLOR}retries:$retries${RESET}"
fi

printf '%s ${RUN_COLOR}[%s]${RESET} ${PHASE_COLOR}%s${RESET}%s last:%s' \
  "$model" "$run_id" "$current_phase" "$retries_part" "$last_verdict"
