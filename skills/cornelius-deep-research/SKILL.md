---
name: cornelius-deep-research
version: 0.2.0
description: Autonomous research-to-knowledge-base pipeline that researches a topic with recent (2024-2025) sources, extracts novel insights, and maps them into an Obsidian-style "second brain". Orchestrates research-specialist, document-insight-extractor, and connection-finder subagents across 6 gated phases. USE WHEN the user wants to grow a personal knowledge base / second brain with cutting-edge insights, says "deep research pipeline", "research and integrate", "find gaps in my KB and fill them", or passes a topic (or "auto" for autonomous topic selection). DO NOT USE for a one-off cited web report with no KB integration (use the deep-research skill), library/API docs (docs-dual-lookup, context7-mcp), academic paper lookup (paper-lookup, perplexity-search), or indexed-tool questions (deep-tool-wiki).
argument-hint: [optional topic or "auto" for autonomous selection]
automation: gated
allowed-tools: Task, Read, Bash, Glob, Grep
---

# Deep Research & Knowledge Integration Pipeline

Orchestrate a fully autonomous research → extraction → connection-discovery
workflow that expands a personal knowledge base ("second brain") with
cutting-edge, well-integrated insights. **All extracted insights MUST be stored
under `Brain/Document Insights/` to stay separate from the main Brain.**

## Input

**`$ARGUMENTS`** selects the mode:
- **Directed** — a topic or comma-separated topics (`"neuroscience of habits"`,
  `"multi-agent systems, safety alignment"`). Research exactly those.
- **Autonomous** — `""` or `"auto"`. You analyze the KB and pick 1-3 topics that
  fill gaps or bridge existing hubs.

## Subagents this skill drives

| Phase | `subagent_type` | Produces |
|-------|-----------------|----------|
| Research | `research-specialist` | `resources/[Topic]-Research-Report-YYYY-MM-DD.md` (15-25 recent papers) |
| Extract | `document-insight-extractor` | Permanent notes + changelog in the session folder |
| Connect | `connection-finder` | Connection map + changelog in `Brain/05-Meta/Changelogs/` |

Sibling skill: **`insight-interview`** (optional Phase 4 gate, captures the user's
own angles before connection discovery).

## Orchestration (execute in order)

1. **Parse input** → directed vs. autonomous mode.
2. **Select topics** → use provided topics, or analyze the KB for gaps
   (autonomous). [Phase 1]
3. **Timestamp** → `date '+%Y-%m-%d %H:%M:%S %Z'` for session-folder naming
   (`YYYY-MM-DD Topic Description`).
4. **Research** → launch `research-specialist` per topic (recent sources only).
   [Phase 2]
5. **Extract** → launch `document-insight-extractor` per report into
   `Brain/Document Insights/[Session-Folder]/`. [Phase 3]
6. **Insight interview** → APPROVAL GATE: present top findings, offer
   `insight-interview` to capture the user's angles. [Phase 4]
7. **Connect** → launch `connection-finder` across both document and personal
   insights. [Phase 5]
8. **Summarize** → generate the session report + actionable next steps. [Phase 6]

Phases run autonomously with no human intervention except the Phase 4 gate.

→ **Full phase instructions and the exact subagent prompts:**
[`references/pipeline.md`](references/pipeline.md)
→ **Phase 6 session-summary template + quality standards:**
[`references/session-summary-template.md`](references/session-summary-template.md)

## State Dependencies

| Source | Location | R | W |
|--------|----------|---|---|
| Knowledge base analysis | `knowledge-base-analysis.md` | X | |
| Document Insights | `Brain/Document Insights/` | X | X |
| Research reports | `resources/` | X | X |
| Changelogs | `Brain/05-Meta/Changelogs/` | X | X |
| Master changelog | `Brain/CHANGELOG.md` | X | X |
| Local Brain Search (dedupe) | `resources/local-brain-search/` | X | |

## Completion Checklist

- [ ] Execution mode determined (directed vs autonomous)
- [ ] Topics selected with rationale
- [ ] Research reports generated and saved to `resources/`
- [ ] Session folder created in Document Insights
- [ ] Insights extracted with deduplication + extraction changelog
- [ ] Insight interview offered (ran or skipped)
- [ ] Connection discovery completed + changelog in `Brain/05-Meta/Changelogs/`
- [ ] Master `CHANGELOG.md` updated
- [ ] Session summary generated with recommendations & synthesis opportunities

Error-handling guidance for each phase lives in `references/pipeline.md`.
