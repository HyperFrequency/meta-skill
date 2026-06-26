#!/usr/bin/env bash
# relentless_relay.sh — UserPromptSubmit hook for /relentless-inception.
#
# Rebuilt from inception-clear-relay.sh.original (archived 2026-05-19) with
# the GIGAPROMPT sentinel replaced by RELENTLESS-* and the model + effort
# defaults updated for the consolidated skill.
#
# Two sentinels are recognized as the FIRST LINE of the user prompt:
#
#   # RELENTLESS-INBOX   — automatic rescue relay. Saves the body, fires
#                          /clear in the active tmux pane, then pastes the
#                          body (minus the sentinel) back in for a fresh run.
#                          Triggered programmatically by the rescue agent
#                          via scripts/rescue.sh.
#
#   # RELENTLESS-RESCUE  — manual rescue trigger. User types this to ask the
#                          background-agent to inspect and propose a rescue.
#                          Body is whatever the user wants the rescue
#                          consortium to know.
#
# Both follow the same tmux-driven /clear + paste flow. Behavior:
#   1. Save the body to ~/.claude/lateral-pass/pending-relentless.md
#      (or pending-relentless-rescue.md for the manual variant).
#   2. Block the current prompt with a status message.
#   3. Spawn a detached daemon into the same tmux pane that runs:
#        sleep 1   → tmux send-keys "/clear" Enter
#        sleep 5   → tmux send-keys "/model <FORCE_MODEL>" Enter (if set)
#        sleep 3   → paste the body (sentinel stripped) + Enter
#      The daemon archives the pending file BEFORE pressing Enter so the
#      paste's re-trigger of this hook hits Case 3 (passthrough), not Case 2.
#
# Manual fallback when no tmux: print remediation banner; the user can
# /clear + /model + retype manually.
#
# Safe for non-matching prompts: passthrough (exit 0 with no decision).

set -euo pipefail

INBOX_AUTO=~/.claude/lateral-pass/pending-relentless.md
INBOX_MANUAL=~/.claude/lateral-pass/pending-relentless-rescue.md
ARCHIVE=~/.claude/lateral-pass/archive
LOG=~/.claude/lateral-pass/relay.log

# Force these on every auto-relay. Override via env (e.g. RELENTLESS_MODEL=
# claude-sonnet-4-6) before starting the tmux pane; the default is the
# max-reasoning Opus 1M variant the skill pins to.
FORCE_MODEL="${RELENTLESS_MODEL:-claude-opus-4-7[1m]}"

mkdir -p "$(dirname "$INBOX_AUTO")" "$ARCHIVE"

payload=$(cat)

if command -v jq >/dev/null 2>&1; then
  prompt=$(printf '%s' "$payload" | jq -r '.prompt // ""' 2>/dev/null || echo "")
else
  prompt=""
fi

first_line=$(printf '%s' "$prompt" | head -n1)

ts() { date -u +%Y%m%dT%H%M%SZ; }
log() { printf '[%s] %s\n' "$(ts)" "$*" >> "$LOG"; }

# ----- Case 1A — auto-relay (RELENTLESS-INBOX sentinel) -----
if [[ "$first_line" == "# RELENTLESS-INBOX" ]]; then
  printf '%s' "$prompt" > "$INBOX_AUTO"
  log "RELENTLESS-INBOX captured ($(wc -c < "$INBOX_AUTO") bytes)"

  SESSION=""
  if [[ -n "${TMUX:-}" ]] && command -v tmux >/dev/null 2>&1; then
    SESSION=$(tmux display-message -p '#S' 2>/dev/null || echo "")
  fi

  if [[ -n "$SESSION" ]]; then
    ARCHIVED="$ARCHIVE/relentless-injected-$(ts).md"
    setsid bash -c "
      set -e
      sleep 1
      tmux send-keys -t '$SESSION' '/clear' Enter
      sleep 5
      tmux send-keys -t '$SESSION' '/model $FORCE_MODEL' Enter
      sleep 3
      mv '$INBOX_AUTO' '$ARCHIVED'
      tail -n +3 '$ARCHIVED' | tmux load-buffer -
      tmux paste-buffer -t '$SESSION'
      sleep 0.3
      tmux send-keys -t '$SESSION' Enter
    " >> "$LOG" 2>&1 </dev/null &
    disown || true

    reason="Relentless rescue staged. Auto-firing /clear now — injection in ~9s. Do NOT type anything."
    if command -v jq >/dev/null 2>&1; then
      jq -nc --arg reason "$reason" '{decision:"block", reason:$reason}'
    else
      printf '%s\n' '{"decision":"block","reason":"Relentless rescue staged. Auto-firing /clear."}'
    fi
    log "auto-fire daemon spawned for session $SESSION"
    exit 0
  fi

  # No tmux → manual fallback banner.
  bytes=$(wc -c < "$INBOX_AUTO")
  manual_reason="Relentless rescue staged at $INBOX_AUTO ($bytes bytes).

tmux NOT detected — autonomous rehydrate can only fire inside tmux.
To resume the run, do ONE of:

  A. Keep this terminal interactive:
     1. /clear
     2. /model $FORCE_MODEL
     3. Type any char + Enter to inject the staged prompt.

  B. Restart under tmux (recommended for unattended runs):
     1. Ctrl-C to exit.
     2. tmux new-session -s relentless
     3. claude --dangerously-skip-permissions --model $FORCE_MODEL --effort max
     4. Paste the staged prompt body — the auto-relay daemon will take over.

Effort must be max: CLI flag --effort max overrides settings default."
  if command -v jq >/dev/null 2>&1; then
    jq -nc --arg reason "$manual_reason" '{decision:"block", reason:$reason}'
  else
    printf '%s\n' '{"decision":"block","reason":"Relentless rescue staged. tmux absent."}'
  fi
  log "manual-mode fallback (no tmux) for INBOX"
  exit 0
fi

# ----- Case 1B — manual rescue trigger (RELENTLESS-RESCUE sentinel) -----
if [[ "$first_line" == "# RELENTLESS-RESCUE" ]]; then
  printf '%s' "$prompt" > "$INBOX_MANUAL"
  log "RELENTLESS-RESCUE captured ($(wc -c < "$INBOX_MANUAL") bytes)"

  # Write a trigger file so the background-agent picks it up next sweep.
  TRIGGER_DIR=~/.claude/relentless-inception/triggers
  mkdir -p "$TRIGGER_DIR"
  TRIGGER_FILE="$TRIGGER_DIR/rescue-manual-$(ts).json"
  if command -v jq >/dev/null 2>&1; then
    jq -nc \
      --arg ts "$(ts)" \
      --arg body "$prompt" \
      '{trigger:"manual",timestamp:$ts,detected_by:"relentless_relay.sh",details:{body:$body},recommended_rescue_lead:"gpt-5.5"}' \
      > "$TRIGGER_FILE"
  else
    printf '{"trigger":"manual","timestamp":"%s","detected_by":"relentless_relay.sh"}\n' "$(ts)" > "$TRIGGER_FILE"
  fi

  reason="Manual rescue trigger received. background-agent will diagnose on next sweep; the run will pause until the rescue cycle completes."
  if command -v jq >/dev/null 2>&1; then
    jq -nc --arg reason "$reason" '{decision:"block", reason:$reason}'
  else
    printf '%s\n' '{"decision":"block","reason":"Manual rescue trigger received."}'
  fi
  log "manual rescue trigger written to $TRIGGER_FILE"
  exit 0
fi

# ----- Case 2 — manual-mode injection (no tmux auto-fire was used) -----
if [[ -f "$INBOX_AUTO" ]]; then
  content=$(cat "$INBOX_AUTO")
  ARCHIVED="$ARCHIVE/relentless-injected-$(ts).md"
  mv "$INBOX_AUTO" "$ARCHIVED"
  if command -v jq >/dev/null 2>&1; then
    jq -nc --arg ctx "$content" \
      '{hookSpecificOutput:{hookEventName:"UserPromptSubmit", additionalContext:$ctx}}'
  fi
  log "manual-mode inject ($(wc -c < "$ARCHIVED") bytes)"
  exit 0
fi

# ----- Case 3 — passthrough -----
exit 0
