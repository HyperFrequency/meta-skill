#!/usr/bin/env bash
# install_hooks.sh — wire /relentless-inception hooks into ~/.claude/settings.json.
#
# Idempotent: safe to re-run. Refuses to overwrite hooks it doesn't recognize.
#
# Adds three hook entries:
#   UserPromptSubmit → relentless_relay.sh   (recognizes RELENTLESS-INBOX / RELENTLESS-RESCUE)
#   Stop             → stall_watchdog.sh     (records Stop events; background-agent reads the trail)
#   statusLine       → status_line.sh        (run-id + phase + retries + last gate)

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SETTINGS=~/.claude/settings.json
BACKUP="$SETTINGS.bak.$(date -u +%Y%m%dT%H%M%SZ)"

if [[ ! -f "$SETTINGS" ]]; then
  echo "error: $SETTINGS not found" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "error: jq is required but not installed. brew install jq" >&2
  exit 1
fi

if ! python3 -c "import json; json.load(open('$SETTINGS'))" >/dev/null 2>&1; then
  echo "error: $SETTINGS is not valid JSON. Refusing to edit." >&2
  exit 1
fi

cp "$SETTINGS" "$BACKUP"
echo "backup: $BACKUP"

RELAY="$SKILL_DIR/scripts/relentless_relay.sh"
WATCHDOG="$SKILL_DIR/scripts/stall_watchdog.sh"
STATUS="$SKILL_DIR/scripts/status_line.sh"

for f in "$RELAY" "$WATCHDOG" "$STATUS"; do
  if [[ ! -f "$f" ]]; then
    echo "error: missing script $f — install_hooks.sh expects the skill bundle to be intact" >&2
    exit 1
  fi
  chmod +x "$f"
done

# Add UserPromptSubmit entry (relay) if not already present.
jq --arg cmd "$RELAY" '
  if (.hooks.UserPromptSubmit // []) | length == 0 then
    .hooks.UserPromptSubmit = [{hooks:[{type:"command", command:$cmd}]}]
  elif (.hooks.UserPromptSubmit[0].hooks | map(.command) | index($cmd)) == null then
    .hooks.UserPromptSubmit[0].hooks += [{type:"command", command:$cmd}]
  else
    .
  end
' "$SETTINGS" > "$SETTINGS.tmp" && mv "$SETTINGS.tmp" "$SETTINGS"

# Add Stop entry (watchdog).
jq --arg cmd "$WATCHDOG" '
  if (.hooks.Stop // []) | length == 0 then
    .hooks.Stop = [{hooks:[{type:"command", command:$cmd}]}]
  elif (.hooks.Stop[0].hooks | map(.command) | index($cmd)) == null then
    .hooks.Stop[0].hooks += [{type:"command", command:$cmd}]
  else
    .
  end
' "$SETTINGS" > "$SETTINGS.tmp" && mv "$SETTINGS.tmp" "$SETTINGS"

# Set statusLine to our status_line.sh — but refuse if a different statusLine
# is already configured (don't silently clobber).
EXISTING_STATUSLINE=$(jq -r '.statusLine.command // ""' "$SETTINGS")
if [[ -z "$EXISTING_STATUSLINE" ]] || [[ "$EXISTING_STATUSLINE" == "$STATUS" ]]; then
  jq --arg cmd "$STATUS" '.statusLine = {type:"command", command:$cmd, padding:0}' \
    "$SETTINGS" > "$SETTINGS.tmp" && mv "$SETTINGS.tmp" "$SETTINGS"
  echo "statusLine: set to $STATUS"
else
  echo "statusLine: already set to $EXISTING_STATUSLINE — leaving untouched."
  echo "  (manually set .statusLine.command to $STATUS if you want the relentless-inception indicator)"
fi

# Validate result.
if ! python3 -c "import json; json.load(open('$SETTINGS'))" >/dev/null 2>&1; then
  echo "error: settings.json broken after edit — restoring backup" >&2
  cp "$BACKUP" "$SETTINGS"
  exit 1
fi

echo
echo "hooks installed:"
jq '{UserPromptSubmit: (.hooks.UserPromptSubmit // []),
     Stop:             (.hooks.Stop // []),
     statusLine:        (.statusLine // null)}' "$SETTINGS"
