# Implementation Guide, Ratios, and Approach Selection

Step-by-step procedures and calibration figures. Read this when actually building a
compression pipeline or choosing between the three approaches for a session profile.

## Apply the Three-Phase Compression Workflow for Large Codebases

For codebases or agent systems exceeding context windows, compress through three sequential phases. Each phase narrows context so the next phase operates within budget.

1. **Research Phase**: Explore architecture diagrams, documentation, and key interfaces. Compress exploration into a structured analysis of components, dependencies, and boundaries. Output: a single research document that replaces raw exploration.

2. **Planning Phase**: Convert the research document into an implementation specification with function signatures, type definitions, and data flow. A 5M-token codebase compresses to approximately 2,000 words of specification at this stage.

3. **Implementation Phase**: Execute against the specification. Context stays focused on the spec plus active working files, not raw codebase exploration. This phase rarely needs further compression because the spec is already compact.

## Use Example Artifacts as Compression Seeds

When provided with a manual migration example or reference PR, use it as a template to understand the target pattern rather than exploring the codebase from scratch. The example reveals constraints static analysis cannot surface: which invariants must hold, which services break on changes, and what a clean implementation looks like.

This matters most when the agent cannot distinguish essential complexity (business requirements) from accidental complexity (legacy workarounds). The example artifact encodes that distinction implicitly, saving tokens that would otherwise go to trial-and-error exploration.

## Implement Anchored Iterative Summarization Step by Step

1. Define explicit summary sections matching the agent's domain (debugging, migration, feature development)
2. On first compression trigger, summarize the truncated history into those sections
3. On subsequent compressions, summarize only newly truncated content — do not re-summarize the existing summary
4. Merge new information into existing sections rather than regenerating them, deduplicating by file path and decision identity
5. Tag which information came from which compression cycle — this enables debugging when summaries drift

## Select the Right Approach for the Session Profile

**Use anchored iterative summarization when:**
- Sessions are long-running (100+ messages)
- File tracking matters (coding, debugging)
- Verification of preserved information is needed

**Use opaque compression when:**
- Maximum token savings are required
- Sessions are relatively short
- Re-fetching costs are low (e.g., no file system access needed)

**Use regenerative summaries when:**
- Summary interpretability is critical for human review
- Sessions have clear phase boundaries
- Full context review is acceptable on each compression trigger

## Calibrate Compression Ratios by Method

| Method | Compression Ratio | Quality Score | Trade-off |
|--------|-------------------|---------------|-----------|
| Anchored Iterative | 98.6% | 3.70 | Best quality, slightly less compression |
| Regenerative | 98.7% | 3.44 | Good quality, moderate compression |
| Opaque | 99.3% | 3.35 | Best compression, quality loss |

Use these as source-specific benchmark figures, not universal constants (claim-context-compression-factory-benchmark). For any task where re-fetching costs exist, this tradeoff generally favors structured approaches.

## Worked Examples

### Example 1: Debugging Session Compression

Original context (89,000 tokens, 178 messages):
- 401 error on /api/auth/login endpoint
- Traced through auth controller, middleware, session store
- Found stale Redis connection
- Fixed connection pooling, added retry logic
- 14 tests passing, 2 failing

Structured summary after compression:

```markdown
## Session Intent
Debug 401 Unauthorized error on /api/auth/login despite valid credentials.

## Root Cause
Stale Redis connection in session store. JWT generated correctly but session could not be persisted.

## Files Modified
- auth.controller.ts: No changes (read only)
- middleware/cors.ts: No changes (examined)
- config/redis.ts: Fixed connection pooling configuration
- services/session.service.ts: Added retry logic for transient failures
- tests/auth.test.ts: Updated mock setup

## Test Status
14 passing, 2 failing (mock setup issues)

## Next Steps
1. Fix remaining test failures (mock session service)
2. Run full test suite
3. Deploy to staging
```

### Example 2: Probe Response Quality

After compression, asking "What was the original error?":

Good response (structured summarization):
> "The original error was a 401 Unauthorized response from the /api/auth/login endpoint. Users received this error with valid credentials. Root cause was stale Redis connection in session store."

Poor response (aggressive compression):
> "We were debugging an authentication issue. The login was failing. We fixed some configuration problems."

The structured response preserves endpoint, error code, and root cause. The aggressive response loses all technical detail.
