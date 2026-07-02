---
name: research-strategy
version: 0.1.0
description: Conduct systematic research with confidence scoring, source validation, and structured reporting for technology decisions and codebase analysis. Use for complex research tasks, technology selection, or best practice discovery. Not for direct code implementation—this skill completes research that informs decisions before handoff to execution.
---

# Research Strategy Skill

## Required tooling — the unified gateway contract

Information sources are pulled through the unified mcp2cli gateway (see the `neuro-harness` skill in this repo for the full endpoint list). Default routing for the six investigation surfaces this skill touches:

| Surface | Use | Notes |
| --- | --- | --- |
| Library / framework / API docs | `docs-dual-lookup` skill (Context7 + Auggie in parallel) | Cross-validation is the point — single-source docs claims get marked Low confidence. |
| Web research | `parallel-web` skill or `perplexity-search` | Both go through the gateway; pick by query shape (Parallel for synthesis + citations, Perplexity for recent web). |
| Academic / paper search | `paper-lookup`, `research-lookup`, `bgpt-paper-search`, `citation-management` | These already wrap the right gateway endpoints. |
| Codebase analysis | `mcp2cli gitnexus` or the `gitnexus-exploring` skill | Code-graph queries beat grep when "where is X used" is the question. |
| AST / language-aware extraction | `mcp2cli tree-sitter` or the `tree-sitter` skill | Especially for Pine, where grep is unreliable. |
| Knowledge-graph / topical-gap analysis | `mcp2cli infranodus` or the `infranodus` skill | Use the LOCAL OSS engine — never default to infranodus.com. |

**Confidence scoring rule:** any finding that comes from a single source through training-data recall (no gateway lookup) is **Low confidence** by default. Promote to Medium with one gateway-sourced confirmation, High with two independent gateway sources.

If the gateway is unreachable, say so explicitly and degrade gracefully: Context7 direct → WebFetch → training-data recall. Mark each finding with which tier it came from.

---

## When to Activate

Activate this skill when:
- Researching technology options
- Evaluating libraries or frameworks
- Investigating best practices
- Analyzing security concerns
- Making architectural decisions
- Performing codebase analysis

## Core Principles

- **Research and report, don't implement**
- **Multiple sources beat single sources**
- **Document confidence levels for all findings**
- **Acknowledge knowledge gaps openly**
- **Present alternatives objectively**

## 7-Step Research Methodology

1. **Define Research Questions** - What exactly needs answering?
2. **Identify Information Sources** - Where to look?
3. **Gather Raw Information** - Collect systematically
4. **Cross-Reference Findings** - Verify across sources
5. **Validate Accuracy** - Check dates, authority, consensus
6. **Identify Gaps** - What's still unknown?
7. **Synthesize Insights** - Connect into actionable knowledge

## Source Prioritization

1. **Primary Sources** (Highest priority)
   - Official documentation
   - Technical specifications
   - API references

2. **Authoritative Sources**
   - Well-maintained libraries
   - Industry standards (OWASP, NIST)
   - Academic papers

3. **Community Sources**
   - Stack Overflow discussions
   - GitHub issues/PRs
   - Technical blogs

4. **Experimental Sources** (Use with caution)
   - Beta features
   - Draft proposals

## Confidence Scoring

Assign to ALL findings:

| Level | Range | Criteria |
|-------|-------|----------|
| **HIGH** | 90-100% | Multiple authoritative sources agree, widely adopted |
| **MEDIUM** | 60-89% | Good documentation, some adoption, minor disagreements |
| **LOW** | 30-59% | Limited sources, conflicting information |
| **SPECULATIVE** | <30% | Educated guess, no direct sources |

## Research Report Structure

```markdown
# Research Report: [Topic]

## Executive Summary
[2-3 paragraphs: key findings, recommendation, confidence]

## Research Questions
1. [Question 1]
2. [Question 2]

## Key Findings

### Finding 1: [Title]
**Confidence**: HIGH/MEDIUM/LOW
**Sources**: [List with links]
[Detailed explanation]
**Implications**: [How this affects decisions]

## Comparative Analysis

| Aspect | Option A | Option B |
|--------|----------|----------|
| Performance | Details | Details |
| Learning Curve | Details | Details |

## Best Practices
1. **[Practice]**: Why, Source, Adoption level

## Risks and Concerns
- **Risk**: Severity, Likelihood, Mitigation

## Knowledge Gaps
- **Gap**: Impact, How to address

## Recommendations
[Clear, actionable recommendations with confidence levels]
```

## Library/Framework Research Template

```markdown
## Overview
- Purpose: [One sentence]
- Maturity: Stable/Beta/Experimental
- Last commit: [Date]
- License: [Type]

## Technical Assessment
- Performance: [Benchmarks]
- Bundle Size: [KB]
- Dependencies: [Count, quality]

## Developer Experience
- Documentation: Excellent/Good/Fair/Poor
- TypeScript: Built-in/DefinitelyTyped/None
- Learning Curve: Steep/Moderate/Gentle

## Verdict
**Recommendation**: Use/Don't Use/Conditional
**Confidence**: HIGH/MEDIUM/LOW
**When to Use**: [Scenarios]
**When to Avoid**: [Scenarios]
```

## Analysis Framework

For each topic, answer:

**Current State**
- What exists today?
- What patterns are established?

**Best Practices**
- What do experts recommend?
- What anti-patterns to avoid?

**Trade-offs**
- What are alternatives?
- Pros/cons of each option?

**Risks**
- What could go wrong?
- Common pitfalls?

## Anti-Patterns to Avoid

❌ **Single Source Syndrome**
- "According to this one article..."
- ✅ "Multiple sources agree (A, B, C)..."

❌ **Premature Implementation**
- "Here's the code..."
- ✅ "Implementation would follow this approach..."

❌ **Missing Confidence Levels**
- "This is the way."
- ✅ "HIGH confidence: Recommended by [sources]..."

❌ **Outdated Information**
- Using 2020 practices without checking updates
- ✅ Verify current practices, note recent changes

## Research Quality Checklist

### Completeness
- [ ] All questions answered
- [ ] Multiple sources consulted (minimum 2-3)
- [ ] Advantages AND disadvantages investigated
- [ ] Edge cases considered

### Accuracy
- [ ] Sources are authoritative and current
- [ ] Publication dates checked
- [ ] Conflicting info acknowledged
- [ ] Assumptions stated

### Actionability
- [ ] Findings translate to next steps
- [ ] Risks quantified
- [ ] Alternatives provided
- [ ] Decision criteria clear

## Related Resources

See `AgentUsage/research_workflow.md` for complete documentation including:
- Security research template
- Detailed report examples
- Research mission template
- Quality checklists
