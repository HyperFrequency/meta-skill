#!/usr/bin/env bash
# Re-run indexing for a single already-registered repo (SKILL.md Steps 2, 3, 6):
#   - Step 2: Context7 — re-resolve happens in Claude Code via MCP (printed reminder)
#   - Step 3: Auggie    — re-index locally if auggie is installed
#   - Step 6: bump last_indexed in the spec file
#
# Usage:
#   reindex.sh <repo-slug> <local-path>
#
# Does NOT re-register the auto-RAG route (Step 4) — that entry already exists and
# must not be duplicated. Use /main-codebase-tools remove + add to change keywords.

set -euo pipefail

SLUG="${1:?repo-slug required}"
LOCAL_PATH="${2:?local path required}"

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPEC_FILE="$SKILL_DIR/$SLUG.md"

if [[ ! -f "$SPEC_FILE" ]]; then
  echo "ERROR: $SPEC_FILE not found — repo '$SLUG' is not registered. Use register_repo.sh first." >&2
  exit 1
fi
if [[ ! -d "$LOCAL_PATH/.git" ]]; then
  echo "ERROR: $LOCAL_PATH is not a git repo" >&2
  exit 1
fi

echo "Reindexing $SLUG"

# Step 2: Context7 (MCP-only — cannot resolve from a plain shell)
echo "Step 2: Context7"
echo "  Run in Claude Code: mcp__context7__resolve-library-id for this repo,"
echo "  then update context7_id / index_context7 in $SPEC_FILE if it now resolves."

# Step 3: Auggie
if command -v auggie >/dev/null 2>&1; then
  echo "Step 3: Auggie re-indexing (backgrounded)"
  (cd "$LOCAL_PATH" && auggie index --path . --project "$SLUG" &) > /dev/null 2>&1
  echo "  check with: auggie status $SLUG"
else
  echo "Step 3: Auggie not installed; skipping (index_auggie stays as-is)"
fi

# Step 6: bump last_indexed in the spec frontmatter
TODAY="$(date -I)"
TMP="$(mktemp)"
sed -E "s/^last_indexed:.*/last_indexed: $TODAY/" "$SPEC_FILE" > "$TMP" && mv "$TMP" "$SPEC_FILE"
echo "Step 6: bumped last_indexed to $TODAY in $SPEC_FILE"

echo "Reindex complete for $SLUG."
