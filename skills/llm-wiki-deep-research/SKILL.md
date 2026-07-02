---
name: llm-wiki-deep-research
version: 0.3.0
description: End-to-end LLM pipeline that RESEARCHES a topic from recent web/academic sources, EXTRACTS novel insights, and INTEGRATES them as permanent notes into the user's Obsidian/turbovault knowledge base, then maps connections to existing notes. Orchestrates research, insight-extraction, and connection subagents across gated phases. USE WHEN the user wants the full research-to-vault pipeline — "research X and add it to my vault", "grow my KB with recent findings on Y", "find gaps in my KB and fill them", or passes a topic (or "auto" for autonomous gap-driven selection). DO NOT USE for a one-off cited web report with no vault write (deep-research); insights from a document/PDF already in hand, no web step (llm-wiki-extract-document-insights); triaging notes ALREADY in the vault (llm-wiki-integrate-recent-notes); profiling vault structure (llm-wiki-analyze-kb); linking existing notes (llm-wiki-find-connections); library docs (docs-dual-lookup); paper lookup (paper-lookup); or indexed-tool questions (deep-tool-wiki).
argument-hint: [optional topic or "auto" for autonomous gap-driven selection]
automation: gated
allowed-tools: Task, Read, Bash, Glob, Grep
---

# LLM Wiki — Deep Research & Knowledge Integration

Orchestrate an autonomous **research → insight-extraction → connection-discovery**
workflow that expands the user's Obsidian vault (accessed via the `turbovault`
skill) with recent, well-integrated insights. Externally-researched material is
kept in a dedicated `Document Insights/` area so it stays separable from the
user's own permanent notes.

This skill is a router: it decides the mode, sequences the phases, and delegates
the heavy work to subagents. Full phase instructions and the exact subagent
prompts live in the references below.

## Input

**`$ARGUMENTS`** selects the mode:
- **Directed** — a topic or comma-separated topics (`"neuroscience of habits"`,
  `"multi-agent systems, safety alignment"`). Research exactly those.
- **Autonomous** — `""` or `"auto"`. Analyze the vault and pick 1-3 topics that
  fill gaps or bridge existing hubs (see Phase 1 in `references/pipeline.md`).

## Subagents this skill drives

| Phase | `subagent_type` | Produces |
|-------|-----------------|----------|
| Research | `research-specialist` | `resources/[Topic]-Research-Report-YYYY-MM-DD.md` (15-25 recent sources) |
| Extract | `document-insight-extractor` | Permanent notes + changelog in the session folder |
| Connect | `connection-finder` | Connection map + changelog under the vault's `Changelogs/` |

## Orchestration (execute in order)

1. **Parse input** → directed vs. autonomous mode.
2. **Select topics** → use provided topics, or analyze the vault for gaps
   (autonomous). [Phase 1]
3. **Timestamp** → `date '+%Y-%m-%d %H:%M:%S %Z'` for session-folder naming
   (`YYYY-MM-DD Topic Description`).
4. **Research** → launch `research-specialist` per topic (recent sources only).
   [Phase 2]
5. **Extract** → launch `document-insight-extractor` per report into
   `Document Insights/[Session-Folder]/`. [Phase 3]
6. **Insight interview** → APPROVAL GATE: present top findings, optionally capture
   the user's own angles before connection discovery. [Phase 4]
7. **Connect** → launch `connection-finder` across the document and personal
   insights. [Phase 5]
8. **Summarize** → generate the session report + actionable next steps. [Phase 6]

Phases run autonomously with no human intervention except the Phase 4 gate.

→ **Full phase instructions and the exact subagent prompts:**
[`references/pipeline.md`](references/pipeline.md)
→ **Phase 6 session-summary template + quality standards:**
[`references/session-summary-template.md`](references/session-summary-template.md)

## State dependencies

| Source | Location (relative to vault root) | R | W |
|--------|-----------------------------------|---|---|
| Vault structure analysis | `knowledge-base-analysis.md` (from `llm-wiki-analyze-kb`) | X | |
| Document Insights | `Document Insights/` | X | X |
| Research reports | `resources/` | X | X |
| Changelogs | `Changelogs/` | X | X |
| Master changelog | `CHANGELOG.md` | X | X |
| Semantic search index (dedupe) | vault search index | X | |

## Completion checklist

- [ ] Execution mode determined (directed vs autonomous)
- [ ] Topics selected with rationale
- [ ] Research reports generated and saved to `resources/`
- [ ] Session folder created in `Document Insights/`
- [ ] Insights extracted with deduplication + extraction changelog
- [ ] Insight interview offered (ran or skipped)
- [ ] Connection discovery completed + changelog written
- [ ] Master `CHANGELOG.md` updated
- [ ] Session summary generated with recommendations & synthesis opportunities

Error-handling guidance for each phase lives in `references/pipeline.md`.
