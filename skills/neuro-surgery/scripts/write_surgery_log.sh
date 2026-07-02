#!/usr/bin/env bash
# write_surgery_log.sh — append one surgery-log entry in the canonical format.
#
# Step 6 of the surgery loop. Writes under today's "Surgery log" subsection
# in 06-Recursive/daily.md, creating the date heading and subsection if they
# don't exist yet. Every action is logged — including skips — so
# /recursive-self-improvement can grade the surgery skill the next day.
#
# Usage:
#   write_surgery_log.sh \
#     --vault <vault-root> \
#     --item "<item label>" \
#     --action applied|skipped|rolled-back \
#     --target "<path>" \
#     --change "<one-line diff summary>" \
#     --rollback "<command>" \
#     [--approver "<handle>"]
#
# Exit codes: 0 ok, 1 bad args.
set -euo pipefail

vault="" item="" action="" target="" change="" rollback="" approver=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --vault)    vault="$2";    shift 2 ;;
    --item)     item="$2";     shift 2 ;;
    --action)   action="$2";   shift 2 ;;
    --target)   target="$2";   shift 2 ;;
    --change)   change="$2";   shift 2 ;;
    --rollback) rollback="$2"; shift 2 ;;
    --approver) approver="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

for req in vault item action target; do
  if [[ -z "${!req}" ]]; then
    echo "missing required --$req" >&2
    exit 1
  fi
done

case "$action" in
  applied|skipped|rolled-back) ;;
  *) echo "--action must be applied|skipped|rolled-back (got: $action)" >&2; exit 1 ;;
esac

log="$vault/06-Recursive/daily.md"
mkdir -p "$(dirname "$log")"
[[ -f "$log" ]] || : > "$log"

today="$(date +%Y-%m-%d)"
now="$(date +%H:%M)"
date_heading="## $today"
subsection="### Surgery log"

# Ensure today's date heading exists.
if ! grep -qF "$date_heading" "$log"; then
  { printf '\n%s\n' "$date_heading"; } >> "$log"
fi

# Ensure the Surgery log subsection exists under today (idempotent enough for
# the common single-section-per-day case).
if ! grep -qF "$subsection" "$log"; then
  { printf '\n%s\n' "$subsection"; } >> "$log"
fi

{
  printf -- '- %s %s — %s\n' "$now" "$item" "$action"
  printf -- '  - Target: %s\n' "$target"
  [[ -n "$change" ]]   && printf -- '  - Change: %s\n' "$change"
  [[ -n "$rollback" ]] && printf -- '  - Rollback: %s\n' "$rollback"
  [[ -n "$approver" ]] && printf -- '  - Approver: %s\n' "$approver"
} >> "$log"

echo "logged: $now $item — $action -> $log"
exit 0
