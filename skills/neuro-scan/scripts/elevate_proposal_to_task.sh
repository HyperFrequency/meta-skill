#!/usr/bin/env bash
# Convert an approved self-improvement proposal into a pending task spec so the
# job scanner can pick it up. Reads a proposal block from
# 07-self-improvement-HITL/overview.md (or a single proposal file) and writes a
# task file to 00-neuro-link/tasks/<slug>.md with source=neuro-scan.
#
# Usage: elevate_proposal_to_task.sh <proposal-slug> [proposal-file]
#   proposal-slug : slug used for the output task filename and task id
#   proposal-file : optional path to a file holding the proposal frontmatter;
#                   defaults to 07-self-improvement-HITL/overview.md

set -uo pipefail

REPO_ROOT="${NLR_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)}"
TASKS_DIR="$REPO_ROOT/00-neuro-link/tasks"
PROPOSAL_FILE="${2:-$REPO_ROOT/07-self-improvement-HITL/overview.md}"

slug="${1:-}"
if [[ -z "$slug" ]]; then
  echo "ERROR: proposal slug required" >&2
  echo "usage: $0 <proposal-slug> [proposal-file]" >&2
  exit 2
fi

if [[ ! -f "$PROPOSAL_FILE" ]]; then
  echo "ERROR: proposal file not found: $PROPOSAL_FILE" >&2
  exit 1
fi

mkdir -p "$TASKS_DIR"
out="$TASKS_DIR/$slug.md"

if [[ -e "$out" ]]; then
  echo "SKIP: task already exists for $slug ($out)" >&2
  exit 0
fi

# Pull priority and a one-line target/description from the proposal if present.
# Falls back to safe defaults so an elevated proposal is never dropped silently.
priority=$(grep -E "^priority:" "$PROPOSAL_FILE" 2>/dev/null | head -1 | sed 's/^priority: *//' | tr -d ' ')
target=$(grep -E "^target:" "$PROPOSAL_FILE" 2>/dev/null | head -1 | sed 's/^target: *//')
priority="${priority:-3}"
target="${target:-$slug}"
today="$(date +%Y-%m-%d)"

cat > "$out" <<EOF
---
type: repair
status: pending
priority: $priority
created: $today
depends_on: []
assigned_harness: claude-code
source: neuro-scan
origin: self-improvement-HITL
proposal: $slug
---

# Elevated proposal: $slug

Target: $target

Approved in 07-self-improvement-HITL but not yet applied. Elevated by
/neuro-scan so the job scanner can route it to /neuro-surgery (HITL) or
/hyper-sleep (non-HITL) for execution.
EOF

echo "WROTE: $out"
