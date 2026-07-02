# Examples and Gotchas

Worked examples and failure-mode traps for context degradation diagnosis.
Read when you need a concrete template or want to rule out false-positive
diagnoses.

## Examples

**Example 1: Detecting Degradation**
```yaml
# Context grows during long conversation
turn_1: 1000 tokens
turn_5: 8000 tokens
turn_10: 25000 tokens
turn_20: 60000 tokens (degradation begins)
turn_30: 90000 tokens (significant degradation)
```

**Example 2: Mitigating Lost-in-Middle**
```markdown
# Organize context with critical info at edges

[CURRENT TASK]                      # At start
- Goal: Generate quarterly report
- Deadline: End of week

[DETAILED CONTEXT]                  # Middle (less attention)
- 50 pages of data
- Multiple analysis sections
- Supporting evidence

[KEY FINDINGS]                     # At end
- Revenue up 15%
- Costs down 8%
- Growth in Region A
```

**Example 3: Context poisoning circuit breaker**
```text
symptom: agent keeps citing an incorrect retrieved claim after correction
diagnosis: poisoned context, not a missing-instruction problem
action:
  1. identify first turn where the bad claim entered
  2. truncate or restart from before that point
  3. reload only verified sources
  4. record the rejected claim and source provenance
```

**Example 4: Context clash annotation**
```yaml
conflict:
  topic: billing API version
  source_a: docs/v1.md says endpoint is /charges
  source_b: docs/v2.md says endpoint is /payments
  precedence: docs/v2.md
  reason: current production version
```

## Guidelines

1. Monitor context length and performance correlation during development
2. Place critical information at beginning or end of context
3. Implement compaction triggers before degradation becomes severe
4. Validate retrieved documents for accuracy before adding to context
5. Use versioning to prevent outdated information from causing clash
6. Segment tasks to prevent context confusion across different objectives
7. Design for graceful degradation rather than assuming perfect conditions
8. Test with progressively larger contexts to find degradation thresholds

## Gotchas

1. **Normal variance looks like degradation**: Model output quality fluctuates naturally across runs. Do not diagnose degradation from a single drop in quality — establish a baseline over multiple runs and look for sustained, correlated decline tied to context growth. A 5-10% quality dip on one run is noise; the same dip consistently appearing after 40K tokens is signal.

2. **Model-specific thresholds go stale**: The degradation onset values in benchmark tables reflect specific model versions. Provider updates, fine-tuning changes, and infrastructure shifts can move thresholds by 20-50% in either direction. Re-benchmark quarterly and after any major model update rather than treating published thresholds as permanent.

3. **Needle-in-haystack scores create false confidence**: A model scoring 99% on needle-in-haystack does not mean it handles 128K tokens well in production. Needle tests measure single-fact retrieval from passive context — real workloads require multi-fact reasoning, instruction following, and synthesis across the full window. Use task-specific benchmarks that mirror actual workload patterns.

4. **Contradictory retrieved documents poison silently**: When a RAG pipeline retrieves two documents that disagree on a fact, the model may silently pick one without signaling the conflict. This looks like a correct response but is effectively random. Implement contradiction detection in the retrieval layer before documents enter context.

5. **Prompt quality problems masquerade as degradation**: Poor prompt structure (ambiguous instructions, missing constraints, unclear task framing) produces symptoms identical to context degradation — inconsistent outputs, ignored instructions, wrong tool usage. Before diagnosing degradation, verify the same prompt works correctly at low context lengths. If it fails at 2K tokens, the problem is the prompt, not the context.

6. **Degradation is non-linear with a cliff edge**: Performance does not degrade gradually — it holds steady until a model-specific threshold, then drops sharply. Systems designed for "graceful degradation" often miss this pattern because monitoring checks assume linear decline. Set compaction triggers well before the cliff (at 70% of known onset), not at the onset itself.

7. **Over-organizing context can backfire**: Intuitively, well-structured and coherent context should outperform disorganized content. Research shows shuffled haystacks sometimes outperform coherent ones for retrieval tasks because coherent context creates false associations. Test whether heavy structural formatting actually helps for the specific task — do not assume it does.
