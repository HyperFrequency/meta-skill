# Detailed Topics: Per-Pattern Detection and Mitigation

Implementation-level detail for each degradation pattern. Read the relevant
subsection when the router in SKILL.md has identified which pattern is active.

## Lost-in-Middle: Detection and Placement Strategy

Place critical information at the beginning and end of context, never in the middle. The U-shaped attention curve means middle-positioned information suffers 10-40% reduced recall accuracy. For contexts over 4K tokens, this effect becomes significant.

Use summary structures that surface key findings at attention-favored positions. Add explicit section headers and structural markers — these help models navigate long contexts by creating attention anchors. When a document must be included in full, prepend a summary of its key points and append the critical conclusions.

Monitor for lost-in-middle symptoms: correct information exists in context but the model ignores it, responses contradict provided data, or the model "forgets" instructions given earlier in a long prompt.

## Context Poisoning: Prevention and Recovery

Validate all external inputs before they enter context. Tool outputs, retrieved documents, and model-generated summaries are the three primary poisoning vectors. Each introduces unverified claims that subsequent reasoning treats as ground truth.

Detect poisoning through these signals: degraded output quality on previously-successful tasks, tool misalignment (wrong tools or parameters), and hallucinations that persist despite explicit correction. When these cluster, suspect poisoning rather than model capability issues.

Recover by removing poisoned content, not by adding corrections on top. Truncate to before the poisoning point, restart with clean context preserving only verified information, or explicitly mark the poisoned section and request re-evaluation from scratch. Layering corrections over poisoned context rarely works — the original errors retain attention weight.

## Context Distraction: Curation Over Accumulation

Curate what enters context rather than relying on models to ignore irrelevant content. Research shows even a single distractor document triggers measurable performance degradation — the effect follows a step function, not a linear curve. Multiple distractors compound the problem.

Apply relevance filtering before loading retrieved documents. Use namespacing and structural organization to make section boundaries clear. Prefer tool-call-based access over pre-loading: store reference material behind retrieval tools so it enters context only when directly relevant to the current reasoning step.

## Context Confusion: Task Isolation

Segment different tasks into separate context windows. Context confusion is distinct from distraction — it concerns the model applying wrong-context constraints to the current task, not just attention dilution. Signs include responses addressing the wrong aspect of a query, tool calls appropriate for a different task, and outputs mixing requirements from multiple sources.

Implement clear transitions between task contexts. Use state management that isolates objectives, constraints, and tool definitions per task. When task-switching within a single session is unavoidable, use explicit "context reset" markers that signal which constraints apply to the current segment.

## Context Clash: Conflict Resolution Protocols

Establish source priority rules before conflicts arise. Context clash differs from poisoning — multiple pieces of information are individually correct but mutually contradictory (version conflicts, perspective differences, multi-source retrieval with divergent facts).

Implement version filtering to exclude outdated information before it enters context. When contradictions are unavoidable, mark them explicitly with structured conflict annotations: state what conflicts, which source each claim comes from, and which source takes precedence. Without explicit priority rules, models resolve contradictions unpredictably.

## Empirical Benchmarks and Thresholds

Use these benchmarks to set design constraints — not as universal truths. RULER-style evidence shows advertised long-context support does not guarantee satisfactory task performance at that length (claim-context-degradation-lost-middle-ruler). Near-perfect needle-in-haystack scores do not predict real-world long-context performance.

**Model-Specific Degradation Thresholds**

Degradation onset varies significantly by model family and task type. As a general rule, expect degradation to begin at 60-70% of the advertised context window for complex retrieval tasks (RULER benchmark found only 50% of models claiming 32K+ context maintain satisfactory performance at that length). Key patterns:

- **Models with extended thinking** reduce hallucination through step-by-step verification but at higher latency and token cost
- **Models optimized for agents/coding** tend to have better attention management for tool-output-heavy contexts
- **Models with very large context windows (1M+)** handle more raw context but still follow U-shaped degradation curves — bigger windows do not eliminate the problem, they delay it

Always benchmark degradation thresholds with your specific workload rather than relying on published benchmarks. Model-specific thresholds go stale with each model update (see Gotcha 2 in examples-and-gotchas.md).

## Counterintuitive Findings

Account for these research-backed surprises when designing context strategies:

**Shuffled context can outperform coherent context.** Studies found incoherent (shuffled) haystacks can outperform logically ordered ones for some retrieval tasks (claim-context-degradation-distractor-shuffled). Coherent context may create false associations that confuse retrieval; incoherent context can force exact matching. Do not assume that better-organized context always yields better results — test both arrangements.

**Single distractors have outsized impact.** The performance hit from one irrelevant document is disproportionately large compared to adding more distractors after the first. Treat distractor prevention as binary: either keep context clean or accept significant degradation.

**Low needle-question similarity accelerates degradation.** Tasks requiring inference across dissimilar content degrade faster with context length than tasks with high surface-level similarity. Design retrieval to maximize semantic overlap between queries and retrieved content.

## When Larger Contexts Hurt

Do not assume larger context windows improve performance. Performance remains stable up to a model-specific threshold, then degrades rapidly — the curve is non-linear with a cliff edge, not a gentle slope. For many models, meaningful degradation begins at 8K-16K tokens even when windows support much larger sizes.

Factor in cost: processing a 400K token context costs exponentially more than 200K in both time and compute, not linearly more. For many applications, this makes large-context processing economically impractical.

Recognize the cognitive bottleneck: even with infinite context, asking a single model to maintain quality across dozens of independent tasks creates degradation that more context cannot solve. Split tasks across sub-agents instead of expanding context.

## Architectural Patterns for Resilience

Implement just-in-time context loading: retrieve information only when the current reasoning step needs it, not preemptively. Use observation masking to replace verbose tool outputs with compact references after processing. Deploy sub-agent architectures where each agent holds only task-relevant context. Trigger compaction before context exceeds the model-specific degradation onset threshold — not after symptoms appear.
