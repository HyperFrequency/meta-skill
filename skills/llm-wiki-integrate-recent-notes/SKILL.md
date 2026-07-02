---
name: llm-wiki-integrate-recent-notes
version: 0.2.0
description: >
  Sweep the neuro-quant Obsidian vault for notes created or modified in a recent
  window (default 14 days), score how well each new note is wired into the rest of
  the vault via turbovault semantic search, classify each as well-connected /
  partial / isolated, and write a dated integration report with concrete linking
  suggestions for the orphans. Use WHEN the user wants to triage, surface, or
  integrate RECENTLY-ADDED notes as a batch — "which new notes are still
  orphaned/unlinked", "integrate this week's notes", "run the note-integration
  sweep" — or on its autonomous schedule. Do NOT use for connection discovery
  around ONE note/topic (use llm-wiki-find-connections), whole-vault
  structure/hub/cluster audits (use llm-wiki-analyze-kb), mining cross-domain
  links across the WHOLE vault (use llm-wiki-auto-discovery), or ingesting new
  external sources (use scrape-ingest-organize). Read-mostly: writes only the
  report, never edits notes or adds links.
automation: autonomous
schedule: "0 19 1,15 * *"
allowed-tools: Read, Write, Bash, Glob, Grep, Skill
---

# Integrate Recent Notes

Freshly-captured notes tend to land in the vault disconnected — no `[[wikilinks]]`
in or out, invisible to the graph. This skill finds those recent arrivals, measures
how integrated each one is, and produces a report telling the user (or a downstream
agent) exactly which notes are orphaned and what they should link to.

It is a **batch triage over a time window**, not a per-note explorer. For a single
note or topic use `llm-wiki-find-connections`; for the whole graph's shape use
`llm-wiki-analyze-kb`.

## Scope

- **Vault root:** `~/Vaults/neuro-quant-vault` (override via `$NEURO_QUANT_VAULT`).
- **Window:** last 14 days by default; honor any window the user gives ("this week").
- **Connection engine:** the `turbovault` skill for semantic neighbors; falls back
  to Grep/Glob wikilink discovery if the index is unavailable.

## Process

### 1. Resolve vault + window
```bash
VAULT="${NEURO_QUANT_VAULT:-$HOME/Vaults/neuro-quant-vault}"
DAYS=14   # override if the user named a different window
date '+%Y-%m-%d'
```

### 2. Find recent notes
Scan the vault for `.md` files touched within the window, excluding meta/system
folders (changelogs, templates, `.obsidian`):
```bash
find "$VAULT" -name '*.md' -type f -mtime -"$DAYS" \
  -not -path '*/.obsidian/*' -not -path '*/05-Meta/*' -not -path '*/Templates/*'
```
If none, log "no notes in the last $DAYS days" and exit cleanly.

### 3. Score connectivity per note
For each recent note, gather two signals:

1. **Semantic neighbors** — invoke the `turbovault` skill with the note's title/body
   to get the top matches with similarity scores. Record the top 5.
   - If turbovault is unavailable, fall back: Grep the vault for the note's title and
     count existing `[[wikilinks]]` pointing to/from it, and mark scores `heuristic`.
2. **Explicit links** — count outgoing `[[...]]` in the note and incoming references
   to it (`grep -rl "[[<title>]]"`).

### 4. Classify
| Class | Rule |
|-------|------|
| **Well-connected** | 3+ neighbors > 0.70 sim, OR 3+ explicit links |
| **Partial** | 1-2 neighbors > 0.70, OR 1-2 explicit links |
| **Isolated** | 0 neighbors > 0.70 and 0 explicit links → priority |

For each isolated/partial note, keep its highest sub-threshold matches as
**suggested links** (they didn't clear 0.70 but are the best candidates).

### 5. Write the report
Write to `<VAULT>/05-Meta/Changelogs/CHANGELOG - Note Integration YYYY-MM-DD.md`.
Keep it terse — it is a worklist, not prose. Suggested links are the top
sub-0.70 matches for partial/isolated notes (best candidates even below the bar):

```markdown
## Note Integration Report: YYYY-MM-DD

Window: last N days • Notes analyzed: [N]
Connection engine: turbovault | heuristic-fallback

### Well-Connected ([N])
- [[Note A]] — 5 neighbors, 4 explicit links

### Partially Connected ([N])
- [[Note B]] — 2 neighbors > 0.70
  - Suggested links: [[X]], [[Y]]

### Isolated — Priority ([N])
- [[Note C]] — 0 neighbors > 0.70, 0 explicit links
  - Best sub-threshold matches: [[X]] (0.65), [[Y]] (0.62)
  - Integration note: [one-line recommendation for where this belongs]

### Suggested Actions
1. [specific link the user should add]
2. [synthesis / merge opportunity, if any]
```

## Boundaries

- Read-mostly. This skill **reports**; it does not add links or edit notes. Applying
  a suggested link is a separate, user-approved action (or a `propagate` pass).
- One time window, many notes. Single-note work → `llm-wiki-find-connections`.
- Not a structural audit (`llm-wiki-analyze-kb`) and not a serendipity/cross-domain
  miner (`llm-wiki-auto-discovery`).

## Error handling
| Situation | Recovery |
|-----------|----------|
| No recent notes | Log and exit 0 |
| turbovault unavailable | Fall back to Grep/Glob; mark scores `heuristic` |
| A single note fails to score | Note the error, continue to the next |
| Changelogs dir missing | `mkdir -p` it before writing |

## Completion checklist
- [ ] Vault + window resolved
- [ ] Recent notes enumerated
- [ ] Connectivity scored (semantic + explicit) per note
- [ ] Notes classified well-connected / partial / isolated
- [ ] Suggested links captured for partial/isolated notes
- [ ] Dated report written to `05-Meta/Changelogs/`
