---
name: cornelius-integrate-recent-notes
version: 0.1.0
description: Find notes created or modified in the Obsidian "Brain" vault within the last 14 days, discover their connections to the rest of the knowledge base via Local Brain Search, classify each as well-connected/partial/isolated, and write an integration report to Brain/05-Meta/Changelogs/. Use WHEN the user asks to integrate, triage, or surface recently added notes, find which new notes are still orphaned/unlinked, or run the scheduled note-integration sweep. Do NOT use for one-off connection discovery from a single note or topic (use cornelius-find-connections), whole-vault structure/cluster/hub analysis (use cornelius-analyze-kb), or ingesting new external sources (use scrape-ingest-organize).
automation: autonomous
schedule: "0 19 1,15 * *"
allowed-tools: Read, Write, Bash, Glob, Grep
---

# Integrate Recent Notes

Find recently created notes and map their connections to the existing knowledge base.

## Purpose

New notes often sit unconnected. This playbook identifies notes from the last 14 days and discovers how they integrate with existing knowledge.

## State Dependencies

| Source | Location | Read | Write | Description |
|--------|----------|------|-------|-------------|
| Permanent Notes | `Brain/02-Permanent/` | ✓ | | Recent notes source |
| AI Extracted Notes | `Brain/AI Extracted Notes/` | ✓ | | Recent notes source |
| Document Insights | `Brain/Document Insights/` | ✓ | | Recent notes source |
| Local Brain Search | `resources/local-brain-search/` | ✓ | | Connection discovery (optional, has fallback) |
| Brain Graph (BDG) | `resources/brain-graph/` | ✓ | | Layer classification (optional, skippable) |
| Session Changelogs | `Brain/05-Meta/Changelogs/` | | ✓ | Integration report |

## Prerequisites

- Local Brain Search index up-to-date (`/refresh-index`)
- Connection scripts present and executable. Validate before the per-note loop:
  ```bash
  for script in resources/local-brain-search/run_connections.sh \
                resources/brain-graph/run_brain_graph.sh; do
    if [ ! -x "$script" ]; then
      echo "WARN: $script missing or not executable — degrading gracefully"
    fi
  done
  ```
  If `run_connections.sh` is unavailable, fall back to grep/Glob-based link
  discovery (search the vault for the note title and existing `[[wikilinks]]`).
  If `run_brain_graph.sh` is unavailable, skip BDG layer classification and
  note it in the report rather than aborting the run.

## Process

### Step 1: Find Recent Notes

Find notes modified in the last 14 days:

```bash
find Brain/02-Permanent -name "*.md" -mtime -14 -type f
find Brain/AI\ Extracted\ Notes -name "*.md" -mtime -14 -type f
find Brain/Document\ Insights -name "*.md" -mtime -14 -type f
```

Compile list of recent notes.

### Step 2: Get Current Date

```bash
date '+%Y-%m-%d'
```

### Step 3: Analyze Connections for Each

For each recent note:

1. Extract note title from filename
2. Run connection discovery (only if the script validated above):
   ```bash
   resources/local-brain-search/run_connections.sh "Note Title" --json
   ```
   On non-zero exit or missing script, fall back to grep/Glob link discovery
   and mark the note's scores as "heuristic".
3. Record top 5 connections with similarity scores
4. Check BDG layer classification (skip if script unavailable):
   ```bash
   resources/brain-graph/run_brain_graph.sh inspect "Note Title" --json
   ```

### Step 4: Identify Integration Opportunities

For each note, categorize:

- **Well-connected** (3+ connections > 0.70): Already integrated
- **Partially connected** (1-2 connections > 0.70): Needs attention
- **Isolated** (0 connections > 0.70): Priority for integration

### Step 5: Create Integration Report

Write to `Brain/05-Meta/Changelogs/CHANGELOG - Note Integration YYYY-MM-DD.md`:

```markdown
## Note Integration Report: YYYY-MM-DD

### Recent Notes Analyzed
Total: [N] notes from last 14 days

### Integration Status

**Well-Connected** ([N]):
- [[Note A]] - 5 connections

**Partially Connected** ([N]):
- [[Note B]] - 2 connections
  - Suggested: Link to [[X]], [[Y]]

**Isolated - Priority** ([N]):
- [[Note C]] - 0 connections
  - Top semantic matches: [[X]] (0.65), [[Y]] (0.62)
  - Integration suggestion: [brief recommendation]

### Suggested Actions
1. [specific linking recommendations]
2. [synthesis opportunities]
```

## Outputs

- Integration report in `Brain/05-Meta/Changelogs/`
- List of isolated notes needing attention
- Suggested connections for each

## Error Handling

| Error | Recovery |
|-------|----------|
| No recent notes | Log "no notes in period" and exit |
| Connection search fails | Note error, continue with next note |
| Index outdated | Run `/refresh-index` first |

## Completion Checklist

- [ ] Recent notes identified (last 14 days)
- [ ] Connections analyzed for each note
- [ ] Notes categorized (well-connected, partial, isolated)
- [ ] Integration suggestions provided for isolated notes
- [ ] Report created in `Brain/05-Meta/Changelogs/`
