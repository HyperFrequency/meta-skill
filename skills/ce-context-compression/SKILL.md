---
name: ce-context-compression
version: 0.1.0
description: This skill should be used when long-running agent sessions need context compression, structured summarization, compaction, token-per-task optimization, or durable handoff summaries that preserve decisions, files, risks, and next actions. Do not use for general token-efficiency tactics like masking or prefix caching (context-optimization), diagnosing context degradation (context-degradation), writing outputs without summarizing (filesystem-context), or cross-session semantic memory (memory-systems).
---

# Context Compression Strategies

When agent sessions generate millions of tokens of conversation history, compression becomes mandatory. The naive approach is aggressive compression to minimize tokens per request. The correct optimization target is **tokens per task**: total tokens consumed to complete a task, including re-fetching costs when compression loses critical information.

This file is a router. Read the linked reference for the depth you need.

## When to Activate

Activate this skill when:
- Agent sessions exceed context window limits
- Codebases exceed context windows (5M+ token systems)
- Designing conversation summarization strategies
- Debugging cases where agents "forget" what files they modified
- Building evaluation frameworks for compression quality
- Creating durable handoff summaries that preserve decisions, files, risks, and next actions

Do not activate this skill for adjacent work owned by other skills:
- General token-efficiency tactics such as masking, prefix caching, or partitioning: `context-optimization`.
- Diagnosing why a long context is failing before choosing a mitigation: `context-degradation`.
- Writing raw outputs, logs, or plans to files without summarizing them: `filesystem-context`.
- Designing long-term semantic memory across sessions: `memory-systems`.

## Core Concepts — Pick an Approach

Context compression trades token savings against information loss. Select from three production-ready approaches based on session characteristics:

1. **Anchored Iterative Summarization** — for long-running sessions where file tracking matters. Maintain structured, persistent summaries with explicit sections (session intent, file modifications, decisions, next steps). On each trigger, summarize only the newly-truncated span and merge into the existing summary rather than regenerating from scratch. Structure forces preservation and prevents the drift that accumulates with wholesale regeneration.

2. **Opaque Compression** — for short sessions where re-fetching costs are low and maximum token savings are required. Produces compressed representations optimized for reconstruction fidelity (99%+ ratios) but sacrifices interpretability entirely. Never use when debugging or artifact tracking is critical — there is no way to verify what was preserved without probe-based evaluation.

3. **Regenerative Full Summary** — for sessions where summary readability is critical and there are clear phase boundaries. Generates a detailed structured summary on each trigger. Weakness: cumulative detail loss, since each regeneration may deprioritize details preserved earlier.

For the selection matrix (which approach fits which session profile) and benchmark ratios, see `references/implementation.md`.

## Detailed Guidance (References)

- **`references/strategies.md`** — tokens-per-task economics, solving the artifact-trail problem, mandatory-section summary schemas, trigger-strategy matrix (fixed/sliding/importance/task-boundary), probe-based evaluation, and the six scoring dimensions. Read when designing or tuning a pipeline.
- **`references/implementation.md`** — three-phase workflow for large codebases, example-artifact seeding, step-by-step anchored iterative summarization, approach-selection criteria, compression-ratio calibration, and worked examples. Read when building a pipeline or choosing an approach.
- **`references/gotchas.md`** — seven failure modes (never compress tool schemas, hallucinated facts, broken artifact references, irreplaceable early turns, compounding ratios, code-vs-prose, false-confidence probes). Read before shipping.
- **`references/evaluation-framework.md`** — full probe pipeline, scoring rubrics, and LLM judge configuration. Read when building or calibrating compression-quality evaluation.

## Guidelines (Quick Reference)

1. Optimize for tokens-per-task, not tokens-per-request
2. Use structured summaries with explicit sections for file tracking
3. Trigger compression at 70-80% context utilization
4. Implement incremental merging rather than full regeneration
5. Test compression quality with probe-based evaluation
6. Track artifact trail separately if file tracking is critical
7. Accept slightly lower compression ratios for better quality retention
8. Monitor re-fetching frequency as a compression quality signal

## Integration

Related skills in this collection:
- `context-degradation` — Read when diagnosing why agent performance drops over long sessions, before applying compression as a mitigation.
- `context-optimization` — Read when compression alone is insufficient and broader optimization strategies (pruning, caching, routing) are needed.
- `evaluation` — Read when designing evaluation frameworks beyond compression-specific probes, including general LLM-as-judge methodology.
- `memory-systems` — Read when compression relates to scratchpad and summary memory patterns across sessions.

## External Resources

- Factory Research: Evaluating Context Compression for AI Agents (December 2025) — benchmark data on compression method comparisons and the 36,000-message evaluation dataset.
- Zheng et al., 2023 — LLM-as-judge evaluation methodology; bias patterns and calibration.
- Netflix Engineering: "The Infinite Software Crisis" (AI Summit 2025) — three-phase workflow and context compression at production scale.

---

## Skill Metadata

**Created**: 2025-12-22
**Last Updated**: 2026-06-29
**Author**: Agent Skills for Context Engineering Contributors
