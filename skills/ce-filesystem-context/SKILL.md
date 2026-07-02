---
name: ce-filesystem-context
version: 1.2.1
description: "This skill should be used when agent work needs file-backed context: durable scratchpads, tool-output offloading, just-in-time discovery, cross-agent handoff files, filesystem memory, or cleanup policies for context stored outside the prompt. Do not use for: semantic/entity/temporal memory (use memory-systems), conversation summarization or compaction (use context-compression), token-efficiency tactics without file storage (use context-optimization), or multi-agent topology and handoff-protocol design (use multi-agent-patterns)."
---

# Filesystem-Based Context Engineering

Use the filesystem as the primary overflow layer for agent context because context windows are limited while tasks often require more information than fits in a single window. Files let agents store, retrieve, and update an effectively unlimited amount of context through a single interface.

Prefer dynamic context discovery -- pulling relevant context on demand -- over static inclusion, because static context consumes tokens regardless of relevance and crowds out space for task-specific information.

## When to Activate

Activate this skill when:
- Tool outputs are bloating the context window
- Agents need to persist state across long trajectories
- Sub-agents must share information without direct message passing
- Tasks require more context than fits in the window
- Building agents that learn and update their own instructions
- Implementing scratch pads for intermediate results
- Terminal outputs or logs need to be accessible to agents

Do not activate this skill for adjacent work owned by other skills:
- Semantic cross-session memory, entity tracking, or temporal knowledge graphs: `memory-systems`.
- Conversation summarization, compaction, or durable handoff wording: `context-compression`.
- Token-efficiency tactics that do not require file-backed storage: `context-optimization`.
- Multi-agent topology or handoff protocol design: `multi-agent-patterns`.

## Core Concepts

Diagnose context failures against these four modes, because each requires a different filesystem remedy:

1. **Missing context** -- needed information is absent from the total available context. Fix by persisting tool outputs and intermediate results to files so nothing is lost.
2. **Under-retrieved context** -- retrieved content fails to encapsulate what the agent needs. Fix by structuring files for targeted retrieval (grep-friendly formats, clear section headers).
3. **Over-retrieved context** -- retrieved content far exceeds what is needed, wasting tokens and degrading attention. Fix by offloading bulk content to files and returning compact references.
4. **Buried context** -- niche information is hidden across many files. Fix by combining glob and grep for structural search alongside semantic search for conceptual queries.

Use the filesystem as the persistent layer that addresses all four: write once, store durably, retrieve selectively.

## Pattern Index

Six patterns implement filesystem-backed context. Each row is a pointer; load the
detail file only when applying that pattern.

| Pattern | Use when | Detail |
|---------|----------|--------|
| 1. Scratch pad | A tool returns >~2000 tokens | Write output to file, return summary + reference; grep/line-range to retrieve |
| 2. Plan persistence | Long-horizon task loses coherence | Persist structured plan (YAML); re-read each turn to re-orient ("recitation") |
| 3. Sub-agent workspaces | Sub-agents must share findings | Each agent writes its own dir; coordinator reads files (avoids telephone-game loss) |
| 4. Dynamic skill loading | Instructions exceed prompt budget | Static = names + one-liners; load full skill file on demand (O(n)→O(1) tokens) |
| 5. Terminal/log persistence | Process output accumulates | Persist to files; `grep -A 5 "error"` instead of loading full history |
| 6. Self-modification | Agent should learn across sessions | Write preferences to instruction files; guard with validation, review periodically |

Underpinning trade-off: static context (instructions, tool defs, rules) costs tokens
every turn, so keep it minimal and load dynamically — except critical safety/correctness
constraints, which stay static because weaker models may fail to trigger a load.

Discovery: use `ls`/`glob`/`grep`/`read_file` (line ranges) for structural and exact-match
queries; semantic search for conceptual queries; combine both.

Conceptual prose and inline snippets for all six patterns, the static/dynamic trade-off,
and search techniques: [references/context-patterns.md](./references/context-patterns.md).
Runnable managers, guards, and full classes:
[references/implementation-patterns.md](./references/implementation-patterns.md).

## Practical Guidance

### When to Use Filesystem Context

Apply filesystem patterns when the situation matches these criteria, because they add I/O overhead that is only justified by token savings or persistence needs:

**Use when:**
- Tool outputs exceed ~2000 tokens
- Tasks span multiple conversation turns
- Multiple agents need shared state
- Skills or instructions exceed comfortable system prompt size
- Logs or terminal output need selective querying

**Avoid when:**
- Tasks complete in single turns (overhead not justified)
- Context fits comfortably in window (no problem to solve)
- Latency is critical (file I/O adds measurable delay)
- Model lacks filesystem tool capabilities

### File Organization

Structure files for agent discoverability, because agents navigate by listing and reading directory names:
```
project/
  scratch/           # Temporary working files
    tool_outputs/    # Large tool results
    plans/           # Active plans and checklists
  memory/            # Persistent learned information
    preferences.yaml # User preferences
    patterns.md      # Learned patterns
  skills/            # Loadable skill definitions
  agents/            # Sub-agent workspaces
```

Use consistent naming conventions and include timestamps or IDs in scratch files for disambiguation.

For autonomous research loops, store raw retrieved evidence under the run that consumed it, for example `researcher/runs/<run-id>/sources/evidence/raw/`. Do not leave raw research dumps in the repository root; root-level artifacts become hard to audit and easy to cite without provenance.

### Token Accounting

Measure where tokens originate before and after applying filesystem patterns, because optimizing without measurement leads to wasted effort:
- Track static vs dynamic context ratio
- Monitor tool output sizes before and after offloading
- Measure how often dynamically-loaded context is actually used

## Examples

**Example 1: Tool Output Offloading**
```
Input: Web search returns 8000 tokens
Before: 8000 tokens added to message history
After:
  - Write to scratch/search_results_001.txt
  - Return: "[Results in scratch/search_results_001.txt. Key finding: API rate limit is 1000 req/min]"
  - Agent greps file when needing specific details
Result: ~100 tokens in context, 8000 tokens accessible on demand
```

**Example 2: Dynamic Skill Loading**
```
Input: User asks about database indexing
Static context: "database-optimization: Query tuning and indexing"
Agent action: read_file("skills/database-optimization/SKILL.md")
Result: Full skill loaded only when relevant
```

**Example 3: Chat History as File Reference**
```
Trigger: Context window limit reached, summarization required
Action:
  1. Write full history to history/session_001.txt
  2. Generate summary for new context window
  3. Include reference: "Full history in history/session_001.txt"
Result: Agent can search history file to recover details lost in summarization
```

## Guidelines

1. Write large outputs to files; return summaries and references to context
2. Store plans and state in structured files for re-reading
3. Use sub-agent file workspaces instead of message chains
4. Load skills dynamically rather than stuffing all into system prompt
5. Persist terminal and log output as searchable files
6. Combine grep/glob with semantic search for comprehensive discovery
7. Organize files for agent discoverability with clear naming
8. Measure token savings to validate filesystem patterns are effective
9. Implement cleanup for scratch files to prevent unbounded growth
10. Guard self-modification patterns with validation
11. Keep raw evidence next to the run, evaluation, and proposal that used it

## Gotchas

1. **Scratch directory unbounded growth**: Agents create temp files without cleanup, eventually consuming disk and making directory listings noisy. Implement a retention policy (age-based or count-based) and run cleanup at session boundaries.
2. **Race conditions in multi-agent file access**: Concurrent writes to the same file corrupt state silently. Enforce per-agent directory isolation or use append-only files with agent-prefixed entries.
3. **Stale file references after moves/renames**: Agents hold paths from prior turns that no longer exist after refactors or file reorganization. Always verify file existence before reading a cached path; re-discover with glob if the check fails.
4. **Glob pattern false matches**: Overly broad patterns (e.g., `**/*`) pull irrelevant files into context, wasting tokens and confusing the model. Scope globs to specific directories and extensions.
5. **File size assumptions**: Reading a file without checking size can dump 100K+ tokens into context in a single tool call. Check file size before reading; use line-range reads for large files.
6. **Missing file existence checks**: Agents assume files exist from prior turns, but they may have been deleted or moved. Always guard reads with existence checks and handle missing-file errors gracefully.
7. **Scratch pad format drift**: Unstructured scratch pads become unparseable after many writes because format conventions erode over successive appends. Define and enforce a schema (YAML, JSON, or structured markdown) from the first write.
8. **Hardcoded absolute paths**: Break when repositories are checked out at different locations or when running in containers. Use relative paths from the project root or resolve paths dynamically.

## Integration

This skill owns file-backed context storage and retrieval. Adjacent skills own semantic memory, summarization, and topology:

- `context-optimization`: filesystem offloading is one implementation of observation masking when full outputs remain retrievable.
- `memory-systems`: use when file-backed notes are no longer enough and semantic, entity, or temporal retrieval is required.
- `multi-agent-patterns`: sub-agent file workspaces enable context isolation and direct handoff.
- `context-compression`: file references can anchor summaries and preserve details omitted from compressed context.
- `tool-design`: tools should return file references for large outputs and expose safe read/search operations.

## References

Internal references:
- [Context Patterns](./references/context-patterns.md) - Read when: you need the conceptual detail and inline snippets for any of the six patterns, the static/dynamic trade-off, or filesystem search techniques
- [Implementation Patterns](./references/implementation-patterns.md) - Read when: implementing scratch pad, plan persistence, or tool output offloading and need concrete code beyond the inline examples

Related skills in this collection:
- context-optimization - Read when: applying token reduction techniques alongside filesystem offloading
- memory-systems - Read when: building persistent storage that outlasts a single session
- multi-agent-patterns - Read when: designing agent coordination with shared file workspaces

External resources:
- LangChain Deep Agents — Read when: implementing filesystem-based context patterns in LangChain/LangGraph pipelines
- Cursor context discovery — Read when: studying how production IDEs implement dynamic context loading
- Anthropic Agent Skills specification — Read when: building skills that leverage filesystem progressive disclosure

---

## Skill Metadata

**Created**: 2026-01-07
**Last Updated**: 2026-06-29
**Author**: Agent Skills for Context Engineering Contributors
**Version**: 1.2.1
