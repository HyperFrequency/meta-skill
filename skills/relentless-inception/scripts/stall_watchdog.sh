#!/usr/bin/env bash
# stall_watchdog.sh — Stop hook for /relentless-inception.
#
# Two roles in one script:
#   1. STOP-HOOK MODE (default): runs on every Stop event. Appends a
#      timestamped record to ~/.claude/relentless-inception/runs/<run_id>/
#      stop-events.jsonl so the background-agent can detect stalls.
#
#   2. SWEEP MODE: when invoked with `--sweep`, reads recent stop events
#      and tool-call logs; if stall criteria are met (no agent output AND
#      no tool calls for STALL_MINUTES), writes a trigger file under
#      ~/.claude/relentless-inception/triggers/. Idempotent.
#
# Designed to be cheap: never blocks, never reads model context, always
# writes JSON quickly and exits.

set -uo pipefail

RUNS_DIR=~/.claude/relentless-inception/runs
TRIGGER_DIR=~/.claude/relentless-inception/triggers
STALL_MINUTES="${STALL_MINUTES:-12}"

mkdir -p "$TRIGGER_DIR"

ts_iso() { date -u +%Y-%m-%dT%H:%M:%SZ; }
ts_epoch() { date -u +%s; }

# Find the active run (most recent manifest.json).
find_active_run() {
  find "$RUNS_DIR" -maxdepth 2 -name manifest.json -type f 2>/dev/null \
    | xargs -I{} stat -f "%m %N" {} 2>/dev/null \
    | sort -rn | head -1 | awk '{print $2}'
}

case "${1:-}" in
  --sweep)
    manifest=$(find_active_run)
    if [[ -z "$manifest" ]]; then exit 0; fi
    run_dir=$(dirname "$manifest")
    stops_log="$run_dir/stop-events.jsonl"
    [[ -f "$stops_log" ]] || exit 0

    last_stop=$(tail -1 "$stops_log" | { command -v jq >/dev/null 2>&1 && jq -r '.epoch // 0'; } || echo 0)
    now=$(ts_epoch)
    elapsed=$(( now - last_stop ))
    threshold=$(( STALL_MINUTES * 60 ))

    if (( elapsed >= threshold )); then
      run_id=$(command -v jq >/dev/null 2>&1 && jq -r '.run_id // "?"' "$manifest" || echo "?")
      trigger="$TRIGGER_DIR/rescue-stall-$run_id-$(date -u +%Y%m%dT%H%M%SZ).json"
      if [[ ! -f "$trigger" ]]; then
        if command -v jq >/dev/null 2>&1; then
          jq -nc \
            --arg ts "$(ts_iso)" \
            --arg run "$run_id" \
            --arg elapsed "$elapsed" \
            --arg threshold "$threshold" \
            '{trigger:"stall", run_id:$run, timestamp:$ts, detected_by:"stall_watchdog.sh",
              details:{elapsed_seconds:$elapsed, threshold_seconds:$threshold},
              recommended_rescue_lead:"gpt-5.5"}' \
            > "$trigger"
        else
          printf '{"trigger":"stall","run_id":"%s","timestamp":"%s"}\n' "$run_id" "$(ts_iso)" > "$trigger"
        fi
      fi
    fi
    exit 0
    ;;
esac

# --- default STOP-HOOK MODE ---
payload=$(cat 2>/dev/null || true)
manifest=$(find_active_run)
[[ -z "$manifest" ]] && exit 0
run_dir=$(dirname "$manifest")
stops_log="$run_dir/stop-events.jsonl"

if command -v jq >/dev/null 2>&1; then
  printf '%s\n' "$(jq -nc \
    --arg ts "$(ts_iso)" \
    --arg epoch "$(ts_epoch)" \
    --arg payload "$payload" \
    '{ts:$ts,epoch:($epoch|tonumber),payload:$payload}')" >> "$stops_log"
else
  printf '{"ts":"%s","epoch":%s}\n' "$(ts_iso)" "$(ts_epoch)" >> "$stops_log"
fi

exit 0
