#!/usr/bin/env bash
# verify_frontmatter.sh — post-edit schema check for a 02-KB-main page.
#
# Step 5 of the surgery loop: after an nlr_wiki_update write, confirm the
# YAML frontmatter still parses and carries every required field. Catches
# the silent-frontmatter-drop failure mode the HITL protocol guards against.
#
# Usage:
#   verify_frontmatter.sh <path-to-md>
#   verify_frontmatter.sh <path-to-md> --require title,type,last_synthesized,source_count,confidence
#
# Exit codes:
#   0  frontmatter present, parses, all required fields non-empty
#   1  bad arguments / file missing
#   2  no frontmatter block found
#   3  one or more required fields missing or empty
set -euo pipefail

REQUIRED_DEFAULT="title,type,last_synthesized,source_count,confidence"

if [[ $# -lt 1 ]]; then
  echo "usage: verify_frontmatter.sh <path-to-md> [--require f1,f2,...]" >&2
  exit 1
fi

target="$1"; shift
required="$REQUIRED_DEFAULT"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --require) required="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ ! -f "$target" ]]; then
  echo "FAIL: file not found: $target" >&2
  exit 1
fi

# Frontmatter must be a leading --- ... --- block on line 1.
if [[ "$(head -n 1 "$target")" != "---" ]]; then
  echo "FAIL: no frontmatter block (file does not start with ---): $target" >&2
  exit 2
fi

# Extract the block between the first two --- fences.
fm="$(awk 'NR==1{next} /^---[[:space:]]*$/{exit} {print}' "$target")"
if [[ -z "$fm" ]]; then
  echo "FAIL: empty frontmatter block: $target" >&2
  exit 2
fi

# Prefer a real YAML parse when a parser is available; fall back to grep.
if command -v yq >/dev/null 2>&1; then
  if ! printf '%s\n' "$fm" | yq -e '.' >/dev/null 2>&1; then
    echo "FAIL: frontmatter is not valid YAML: $target" >&2
    exit 2
  fi
fi

missing=()
IFS=',' read -ra fields <<< "$required"
for field in "${fields[@]}"; do
  field="$(echo "$field" | tr -d '[:space:]')"
  [[ -z "$field" ]] && continue
  # Match "field:" with a non-empty value after it.
  if ! printf '%s\n' "$fm" | grep -Eq "^${field}:[[:space:]]*[^[:space:]].*$"; then
    missing+=("$field")
  fi
done

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "FAIL: missing/empty required fields: ${missing[*]}" >&2
  exit 3
fi

echo "OK: frontmatter valid, required fields present: $target"
exit 0
