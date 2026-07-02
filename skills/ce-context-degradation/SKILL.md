---
name: ce-context-degradation
version: 0.1.0
description: "This skill should be used for diagnosing and mitigating context degradation: lost-in-middle failures, context poisoning, context clash, context confusion, attention-pattern issues, and agent performance degradation caused by accumulated or conflicting context. Do not use for foundational context mechanics, token-efficiency tactics, compression strategies, or offloading context outside the prompt—those are covered by adjacent skills."
---

# Context Degradation Patterns

Diagnose and fix context failures before they cascade. Context degradation is not binary — it is a continuum that manifests through five distinct, predictable patterns: lost-in-middle, poisoning, distraction, confusion, and clash. Each pattern has specific detection signals and mitigation strategies. Treat degradation as an engineering problem with measurable thresholds, not an unpredictable failure mode.

This file is a router. Identify the active pattern below, apply the matching mitigation bucket, then jump to the reference file for implementation detail.

## When to Activate

Activate this skill when:
- Agent performance degrades unexpectedly during long conversations
- Debugging cases where agents produce incorrect or irrelevant outputs
- Designing systems that must handle large contexts reliably
- Evaluating context engineering choices for production systems
- Investigating "lost in middle" phenomena in agent outputs

Do not activate this skill for adjacent work owned by other skills:
- Explaining foundational context mechanics without an active failure: `context-fundamentals`.
- Applying token-efficiency tactics after the failure pattern is known: `context-optimization`.
- Designing a compression or handoff summary strategy: `context-compression`.
- Persisting large outputs, logs, or scratch state outside the prompt: `filesystem-context`.

## Diagnose the Pattern

Match the symptom to one of the five patterns, then read the matching section in
[detailed-topics.md](./references/detailed-topics.md):

| Pattern | Core signal | Primary fix |
|---|---|---|
| **Lost-in-middle** | Correct info exists in context but is ignored; U-curve recall loss in long prompts | Place critical info at start/end; summarize at edges |
| **Poisoning** | A bad claim/tool error compounds and persists despite correction | Truncate to before entry point; reload verified-only |
| **Distraction** | One+ irrelevant docs degrade relevant-task performance | Filter before loading; move reference behind tool calls |
| **Confusion** | Wrong-task constraints or tools applied to current task | Isolate tasks into separate context windows |
| **Clash** | Individually-correct sources mutually contradict | Source precedence rules; version filtering; mark conflicts |

## Core Concepts

- **Attention U-curve.** Beginning and end positions receive reliable attention; middle positions suffer materially reduced recall (claim-context-degradation-lost-middle-ruler). The first token (often BOS) acts as an "attention sink." Middle tokens go under-attended as context grows.
- **Poisoning is a circuit-breaker problem.** Once a hallucination, tool error, or wrong fact enters context, it compounds through self-reference. Recovery means truncating to before the poisoning point — not layering corrections on top.
- **Filter before loading.** Even a single irrelevant document measurably degrades performance. Models cannot "skip" context; move not-immediately-relevant info behind tool calls.
- **Isolate task contexts.** Mixed task types cause constraint bleed and wrong-tool calls. Explicit task segmentation eliminates cross-contamination.
- **Resolve clash by priority, not accumulation.** Mark contradictions explicitly, establish source precedence, filter outdated versions before they enter context.

## The Four-Bucket Mitigation Framework

Apply based on which pattern is active:

- **Write** — Save context outside the window (scratchpads, files, external storage). Use when utilization exceeds ~70% of the window.
- **Select** — Pull only relevant context in via retrieval/filtering/prioritization. Use for distraction or confusion. Score relevance before loading; exclude below threshold.
- **Compress** — Reduce tokens while preserving information (summarization, observation masking). Use when context grows but all content is relevant.
- **Isolate** — Split context across sub-agents or sessions so no single context passes its degradation threshold. Use for confusion, clash, or independent tasks. Most aggressive, often most effective.

For architectural patterns (just-in-time loading, observation masking, sub-agent designs, pre-cliff compaction triggers), see the end of [detailed-topics.md](./references/detailed-topics.md).

## Thresholds and Surprises (quick reference)

- Expect degradation onset around 60-70% of the advertised window for complex retrieval; only ~50% of models claiming 32K+ stay satisfactory at that length (RULER).
- Degradation is **non-linear with a cliff edge** — steady, then sharp drop. Set compaction triggers at ~70% of known onset, not at onset.
- Needle-in-haystack scores do not predict real-world long-context performance.
- Counterintuitive: shuffled context can beat coherent context; a single distractor has outsized impact; low needle-question similarity accelerates degradation.

Full benchmarks, model-family patterns, and counterintuitive findings: [detailed-topics.md](./references/detailed-topics.md). Worked examples, the eight operating guidelines, and seven diagnostic traps (e.g. prompt-quality problems masquerading as degradation): [examples-and-gotchas.md](./references/examples-and-gotchas.md).

## Integration

This skill owns diagnosis and mitigation of active context failures. Adjacent skills own implementation tactics once the failure is identified:

- `context-fundamentals`: conceptual explanation of attention and context windows before a failure exists.
- `context-optimization`: masking, caching, partitioning, and other token-efficiency tactics after diagnosis.
- `context-compression`: structured summaries and handoffs when accumulated context must be compacted.
- `filesystem-context`: offloading raw outputs, logs, and scratch state so poisoned or bulky context can be inspected without staying in the prompt.
- `multi-agent-patterns`: isolating tasks into separate contexts to prevent confusion and clash.
- `evaluation`: degradation tests and production monitoring.

## References

Internal references:
- [Detailed Topics](./references/detailed-topics.md) — Read when: debugging a specific pattern and needing per-pattern detection/placement strategy, empirical thresholds, counterintuitive findings, or resilience architecture.
- [Examples and Gotchas](./references/examples-and-gotchas.md) — Read when: needing concrete templates (poisoning circuit breaker, clash annotation, lost-in-middle layout), the operating guidelines checklist, or to rule out false-positive diagnoses.
- [Degradation Patterns Reference](./references/patterns.md) — Read when: needing implementation-level detection code (attention analysis, poisoning tracking, relevance scoring, recovery procedures).

Related skills: `context-fundamentals` (foundations), `context-optimization` (mitigation techniques), `evaluation` (production monitoring).

External resources:
- Liu et al., 2023 "Lost in the Middle" — primary research for U-shaped attention claims.
- RULER benchmark documentation — evaluating model claims about long-context support.
- Production engineering guides from AI labs — implementing context management in production.

---

## Skill Metadata

**Created**: 2025-12-20
**Last Updated**: 2026-06-29
**Author**: Agent Skills for Context Engineering Contributors
