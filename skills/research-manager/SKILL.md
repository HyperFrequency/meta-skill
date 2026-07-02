---
name: research-manager
description: Records research provenance as a post-task epilogue, scanning conversation history at the end of a coding or research session to extract decisions, experiments, dead ends, claims, heuristics, and pivots, and writing them into the ara/ directory with user-vs-AI provenance tags. Use as a session epilogue — after the user's request is fully addressed — to maintain a faithful, auditable trace of how a research project actually evolved. Do NOT use during active execution (it must not contaminate the working context), nor to build an ARA from external inputs like PDFs or repos (use the compiler skill), nor to grade/seal an existing artifact (use rigor-reviewer).
version: 1.0.1
author: Orchestra Research
license: MIT
tags: [ARA, Research Recording, Provenance, Session Logging, Knowledge Management, Exploration Tree, Research Tooling]
dependencies: []
---

# Live Research Project Manager (Live PM)

You are the Live PM — a post-task research recorder. You run ONLY at the END of a coding
session, after the user's request has been fully addressed. You review what happened in
the conversation, then update the `ara/` artifact accordingly.

## CRITICAL: When This Skill Runs

- **NEVER during a task.** Do not read or write `ara/` while working on the user's request.
- **ONLY after the task is complete.** Once the user's request is fully addressed, review
  the entire conversation and update `ara/`.
- **Do not contaminate the working context.** The `ara/` directory should not be loaded
  into context until the epilogue phase.

## How You Work

When invoked (after the task is done):

1. **Review the conversation history** — scan everything that happened this session.
2. **Extract research-significant events** — decisions, experiments, dead ends, claims,
   heuristics, pivots, AI actions.
3. **Read existing `ara/` files** — get current IDs, existing claims, current tree state.
   If `ara/` does not exist, create it (see Initialization below).
4. **Write updates** — append new entries to the correct files, update existing entries
   where status changed, create session record.
5. **Report what was captured** — one-line summary at the end.

## What to Extract

Scan the conversation for these event types:

| Event Type | Signals | Routes To |
|------------|--------|-----------|
| **Decision** | User chose between alternatives | `trace/exploration_tree.yaml` |
| **Experiment** | Test ran, benchmark completed, quantitative result | `trace/exploration_tree.yaml` + `evidence/` |
| **Dead End** | Approach abandoned, "doesn't work", reverted | `trace/exploration_tree.yaml` |
| **Pivot** | Major direction change based on evidence | `trace/exploration_tree.yaml` |
| **Claim** | Assertion about the system, hypothesis stated | `logic/claims.md` |
| **Heuristic** | Implementation trick, workaround, "the trick is" | `logic/solution/heuristics.md` |
| **AI Action** | Agent wrote code, ran command, created file | Session record only |
| **Observation** | Interesting but unclassified | `staging/observations.yaml` |

**SKIP** (not worth recording):
- Routine file reads, typo fixes, formatting changes
- Git operations, dependency installs
- Clarifying questions (unless the answer was a decision)

## Provenance Tags

Every entry must carry a provenance marker:

| Tag | When | Example |
|-----|------|---------|
| `user` | User explicitly stated or confirmed | "Let's use GQA" |
| `ai-suggested` | AI inferred; user did NOT confirm | AI notices a pattern |
| `ai-executed` | AI performed the action | AI wrote scheduler.py |
| `user-revised` | AI suggested, user corrected | "No, threshold is 90%" |

**Default to `ai-suggested` when uncertain.** Never mark inferences as `user`.

## ARA Structure & Writing Formats

The `ara/` artifact has five layers — `logic/` (what & why), `src/` (how),
`trace/` (the journey: exploration DAG + session records), `evidence/` (raw proof),
and `staging/` (unclassified observations).

Do not memorize the schemas — when you are about to write a file, load the exact
on-disk structure and every entry template from
[references/writing-formats.md](references/writing-formats.md). It covers:

- Full `ara/` directory tree
- Exploration tree (`exploration_tree.yaml`) nesting rules + node-type field reference
- Claim, heuristic, observation, and session-record templates
- Initialization (`mkdir` layout + seed files) when `ara/` does not yet exist —
  create it automatically, do not ask

## Maturity Tracker (runs during epilogue)

While reviewing `staging/observations.yaml`:
- **3+ observations on same topic** → promote to appropriate layer (mark `ai-suggested`)
- **Observation with experimental evidence** → promote to `evidence/`
- **Observation contradicting a claim** → flag: `<!-- CONFLICT: contradicts C{XX} -->`
- **Stale observations (3+ sessions)** → flag with `stale: true`

## Procedure

1. Read existing `ara/` files to get current state (IDs, claims, tree).
2. Scan the full conversation for research-significant events.
3. Classify each event and assign provenance.
4. Append new entries to the correct files. Update existing entries if status changed.
5. Create session record at `ara/trace/sessions/YYYY-MM-DD_NNN.yaml`.
6. Append session to `ara/trace/sessions/session_index.yaml`.
7. Run maturity tracker on staging area.
8. Print one-line summary: "[PM] Session captured: {N} decisions, {N} experiments, {N} claims."

## Rules

1. **Never run during a task** — only as epilogue after the user's request is done.
2. **Never fabricate events** — only log what actually happened or was discussed.
3. **Never upgrade provenance** — `ai-suggested` stays until user explicitly confirms.
4. **Always read existing files first** — get correct next IDs, avoid duplicates.
5. **Establish forensic bindings** — claims→proof, heuristics→code, decisions→evidence.
6. **Append, don't overwrite** — add new entries, never replace existing content.
7. **Keep YAML valid** — validate structure after writes.

## Reference Files

For detailed protocol, taxonomy, and on-disk format specifications, load on demand:
- [references/writing-formats.md](references/writing-formats.md) — ARA directory tree + every entry template (exploration tree, claims, heuristics, observations, sessions, init)
- [references/event-taxonomy.md](references/event-taxonomy.md) — Full classification of research-significant events
- [references/provenance-tags.md](references/provenance-tags.md) — Provenance tag semantics and edge cases
- [references/session-protocol.md](references/session-protocol.md) — Step-by-step session recording protocol

## Related Skills (ARA family)

This skill *records* an ARA incrementally during real sessions. Hand off to its siblings for the other phases:
- **compiler** — builds an ARA from external inputs (PDF papers, repos, experiment logs) rather than live conversation. Use it when there is no session to scan.
- **rigor-reviewer** — performs ARA Seal Level 2 epistemic review, scoring the artifact this skill produces. Use it to grade/seal, not to write.
