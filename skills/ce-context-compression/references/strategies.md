# Compression Strategies — Detailed Guidance

Detailed mechanics behind the three approaches in SKILL.md. Read this when designing or
tuning a compression pipeline.

## Optimize for Tokens-Per-Task, Not Tokens-Per-Request

Measure total tokens consumed from task start to completion, not tokens per individual request. When compression drops file paths, error messages, or decision rationale, the agent must re-explore, re-read files, and re-derive conclusions — wasting far more tokens than the compression saved. A strategy saving 0.5% more tokens per request but causing 20% more re-fetching costs more overall. Track re-fetching frequency as the primary quality signal: if the agent repeatedly asks to re-read files it already processed, compression is too aggressive.

## Solve the Artifact Trail Problem First

Artifact trail integrity is often the weakest dimension in compression evaluations (claim-context-compression-factory-benchmark). Address this proactively because general summarization cannot reliably maintain it.

Preserve these categories explicitly in every compression cycle:
- Which files were created (full paths)
- Which files were modified and what changed (include function names, not just file names)
- Which files were read but not changed
- Specific identifiers: function names, variable names, error messages, error codes

Implement a separate artifact index or explicit file-state tracking in agent scaffolding rather than relying on the summarizer to capture these details. Even structured summarization with dedicated file sections struggles with completeness over long sessions.

## Structure Summaries with Mandatory Sections

Build structured summaries with explicit sections that prevent silent information loss. Each section acts as a checklist the summarizer must populate, making omissions visible rather than silent.

```markdown
## Session Intent
[What the user is trying to accomplish]

## Files Modified
- auth.controller.ts: Fixed JWT token generation
- config/redis.ts: Updated connection pooling
- tests/auth.test.ts: Added mock setup for new config

## Decisions Made
- Using Redis connection pool instead of per-request connections
- Retry logic with exponential backoff for transient failures

## Current State
- 14 tests passing, 2 failing
- Remaining: mock setup for session service tests

## Next Steps
1. Fix remaining test failures
2. Run full test suite
3. Update documentation
```

Adapt sections to the agent's domain. A debugging agent needs "Root Cause" and "Error Messages"; a migration agent needs "Source Schema" and "Target Schema." The structure matters more than the specific sections — any explicit schema outperforms freeform summarization.

## Choose Compression Triggers Strategically

When to trigger compression matters as much as how to compress. Select a trigger strategy based on session predictability:

| Strategy | Trigger Point | Trade-off |
|----------|---------------|-----------|
| Fixed threshold | 70-80% context utilization | Simple but may compress too early |
| Sliding window | Keep last N turns + summary | Predictable context size |
| Importance-based | Compress low-relevance sections first | Complex but preserves signal |
| Task-boundary | Compress at logical task completions | Clean summaries but unpredictable timing |

Default to sliding window with structured summaries for coding agents — it provides the best balance of predictability and quality. Use task-boundary triggers when sessions have clear phase transitions (e.g., research then implementation then testing).

## Evaluate Compression with Probes, Not Metrics

Traditional metrics like ROUGE or embedding similarity fail to capture functional compression quality. A summary can score high on lexical overlap while missing the one file path the agent needs to continue.

Use probe-based evaluation: after compression, pose questions that test whether critical information survived. If the agent answers correctly, compression preserved the right information. If not, it guesses or hallucinates.

| Probe Type | What It Tests | Example Question |
|------------|---------------|------------------|
| Recall | Factual retention | "What was the original error message?" |
| Artifact | File tracking | "Which files have we modified?" |
| Continuation | Task planning | "What should we do next?" |
| Decision | Reasoning chain | "What did we decide about the Redis issue?" |

See `evaluation-framework.md` for the full probe pipeline, scoring rubrics, and LLM judge configuration.

## Score Compression Across Six Dimensions

Evaluate compression quality for coding agents across these dimensions. Accuracy and artifact-trail preservation tend to separate methods more clearly than lexical similarity (claim-context-compression-factory-benchmark), so compression needs specialized handling beyond general summarization.

1. **Accuracy**: Are technical details correct — file paths, function names, error codes?
2. **Context Awareness**: Does the response reflect current conversation state?
3. **Artifact Trail**: Does the agent know which files were read or modified?
4. **Completeness**: Does the response address all parts of the question?
5. **Continuity**: Can work continue without re-fetching information?
6. **Instruction Following**: Does the response respect stated constraints?
