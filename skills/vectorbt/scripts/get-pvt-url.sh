#!/usr/bin/env bash
# get-pvt-url.sh — fetch the current VBT Pro authenticated URL.
#
# The VBT Pro pvt hash rotates. Polakow maintains a stable pointer
# branch `pvt-links` on the private `polakowo/vectorbt.pro` repo whose
# README.md contains the current URL. Requires a GitHub PAT with access
# to the private repo (your VBT Pro purchase unlocks it).
#
# Usage:
#     ./get-pvt-url.sh              # prints just the base URL
#     ./get-pvt-url.sh --llms       # appends /llms-full.txt
#     ./get-pvt-url.sh --api        # appends /api/
#     ./get-pvt-url.sh --raw        # prints the README verbatim
#
# Auth: uses `gh` (reads keychain token) by default. If `gh` isn't
# authenticated, falls back to GITHUB_ACCESS_TOKEN env var.

set -euo pipefail

SUFFIX=""
MODE="url"
case "${1:-}" in
  --llms)  SUFFIX="llms-full.txt" ;;
  --api)   SUFFIX="api/" ;;
  --raw)   MODE="raw" ;;
  "")      ;;
  *) echo "usage: $0 [--llms|--api|--raw]" >&2; exit 2 ;;
esac

if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
  README=$(gh api "repos/polakowo/vectorbt.pro/contents/README.md?ref=pvt-links" \
           -H "Accept: application/vnd.github.raw" 2>/dev/null)
elif [ -n "${GITHUB_ACCESS_TOKEN:-}" ]; then
  README=$(curl -sSf \
           -H "Authorization: token $GITHUB_ACCESS_TOKEN" \
           -H "Accept: application/vnd.github.raw" \
           "https://api.github.com/repos/polakowo/vectorbt.pro/contents/README.md?ref=pvt-links")
else
  echo "ERROR: need either \`gh\` authenticated or GITHUB_ACCESS_TOKEN in env" >&2
  exit 3
fi

if [ "$MODE" = "raw" ]; then
  printf '%s\n' "$README"
  exit 0
fi

URL=$(printf '%s\n' "$README" | grep -oE "https://vectorbt\.pro/pvt_[a-z0-9]+" | head -1)
if [ -z "$URL" ]; then
  echo "ERROR: no pvt URL found in pvt-links README" >&2
  exit 4
fi

printf '%s/%s\n' "$URL" "$SUFFIX"
