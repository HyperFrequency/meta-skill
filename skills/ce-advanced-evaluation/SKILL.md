---
name: ce-advanced-evaluation
version: 2.1.0
description: "Advanced LLM-as-judge evaluation: direct scoring, pairwise comparison with position-swap, rubric calibration, bias mitigation, and confidence scoring. Use when building or debugging judge systems, comparing model responses, or validating judges against human labels. NOT for deterministic checks/regression/quality gates (use `evaluation`); NOT for autonomous-loop governance or locked rubrics (use `harness-engineering`)."
---

# Advanced Evaluation

Production-grade techniques for evaluating LLM outputs using LLMs as judges: choosing the right approach and mitigating known judge biases.

**Key insight**: LLM-as-a-Judge is a family of approaches, each suited to a different evaluation context — not a single technique.

## When to Activate

Activate this skill when:

- Building LLM-as-judge systems for LLM outputs
- Comparing multiple model responses to select the best one
- Establishing consistent quality standards across evaluation teams
- Debugging evaluation systems that show inconsistent results
- Designing A/B tests for prompt or model changes
- Creating rubrics specifically for LLM or human/LLM hybrid judges
- Analyzing correlation between automated and human judgments

Do not activate this skill for adjacent work owned by other skills:
- General deterministic checks, regression suites, production quality gates, or outcome metrics: `evaluation`.
- Autonomous loop governance, locked rubrics, rollback, or PR approval boundaries: `harness-engineering`.
- Tool API contracts for evaluation tools: `tool-design`.

## Core Concepts

### The Evaluation Taxonomy

Select between two primary approaches based on whether ground truth exists:

**Direct Scoring** — Use when objective criteria exist (factual accuracy, instruction following, toxicity). A single LLM rates one response on a defined scale. Achieves moderate-to-high reliability for well-defined criteria. Watch for score calibration drift and inconsistent scale interpretation.

**Pairwise Comparison** — Use for subjective preferences (tone, style, persuasiveness). An LLM compares two responses and selects the better one. Pairwise methods often correlate better with human preference than open-ended direct scoring for subjective tasks (claim-advanced-evaluation-position-swap). Watch for position bias and length bias.

### The Bias Landscape

Mitigate these systematic judge biases (mechanisms, code, and full mitigation matrix in [Bias Mitigation](./references/bias-mitigation.md)):

- **Position bias**: first-position responses favored -> swap positions, consistency-check.
- **Length bias**: longer scores higher -> length-neutral prompting + length-normalized scoring.
- **Self-enhancement bias**: models favor own outputs -> separate generator and evaluator models.
- **Verbosity bias**: excess detail scores higher -> rubric verbosity penalties.
- **Authority bias**: confident tone scores higher -> require evidence citation + fact-check layer.

### Metric Selection Framework

Match metrics to task structure (binary, ordinal, pairwise, multi-label). The full selection table plus formulas and code live in [Metric Selection Guide](./references/metrics-guide.md#quick-selection-by-task-structure). Prioritize systematic disagreement patterns over absolute agreement rates: a judge that consistently disagrees with humans on specific criteria is more problematic than one with random noise.

## Evaluation Approaches

### Direct Scoring Implementation

Build direct scoring with three components: clear criteria, a calibrated scale, and structured output format.

**Criteria Definition Pattern**:
```
Criterion: [Name]
Description: [What this criterion measures]
Weight: [Relative importance, 0-1]
```

**Scale Calibration** — Choose scale granularity based on rubric detail:
- 1-3: Binary with neutral option, lowest cognitive load
- 1-5: Standard Likert, best balance of granularity and reliability
- 1-10: Use only with detailed per-level rubrics because calibration is harder

Require evidence before the score in scoring prompts so the judge must anchor its decision in observable output features before emitting a number. See the copy-ready direct-scoring prompt template in [Implementation Patterns](./references/implementation-patterns.md#prompt-templates).

### Pairwise Comparison Implementation

Apply position bias mitigation in every pairwise evaluation:

1. Run deterministic pre-checks first: both candidates must satisfy the same schema, source-evidence requirements, and scope constraints.
2. First judge pass: Response A in first position, Response B in second.
3. Second judge pass: Response B in first position, Response A in second.
4. Consistency check: If passes disagree, return TIE with reduced confidence.
5. Final verdict: Consistent winner with averaged confidence and explicit tie-breaker rationale.

The copy-ready pairwise-comparison prompt template (with length- and position-neutrality instructions) lives in [Implementation Patterns](./references/implementation-patterns.md#prompt-templates).

**Confidence Calibration** — Map confidence to position consistency:
- Both passes agree: confidence = average of individual confidences
- Passes disagree: confidence = 0.5, verdict = TIE

### Rubric Generation

Generate rubrics to reduce evaluation variance compared to open-ended scoring. Treat exact variance reduction as workload-specific unless measured on the target eval set.

**Include these rubric components**:
1. **Level descriptions**: Clear boundaries for each score level
2. **Characteristics**: Observable features that define each level
3. **Examples**: Representative text for each level (optional but valuable)
4. **Edge cases**: Guidance for ambiguous situations
5. **Scoring guidelines**: General principles for consistent application

**Set strictness calibration** for the use case:
- **Lenient**: Lower passing bar, appropriate for encouraging iteration
- **Balanced**: Typical production expectations
- **Strict**: High standards for safety-critical or high-stakes evaluation

Adapt rubrics to the domain — use domain-specific terminology. A code readability rubric mentions variables, functions, and comments. A medical accuracy rubric references clinical terminology and evidence standards.

## Practical Guidance

### Evaluation Pipeline Design

Build production evaluation systems with these layers: Criteria Loader (rubrics + weights) -> Primary Scorer (direct or pairwise) -> Bias Mitigation (position swap, etc.) -> Confidence Scoring (calibration) -> Output (scores + justifications + confidence). See [Evaluation Pipeline Diagram](./references/evaluation-pipeline.md) for the full visual layout.

### Decision Framework: Direct vs. Pairwise

Apply this decision tree:

```
Is there an objective ground truth?
+-- Yes -> Direct Scoring
|   Examples: factual accuracy, instruction following, format compliance
|
+-- No -> Is it a preference or quality judgment?
    +-- Yes -> Pairwise Comparison
    |   Examples: tone, style, persuasiveness, creativity
    |
    +-- No -> Consider reference-based evaluation
        Examples: summarization (compare to source), translation (compare to reference)
```

### Scaling Evaluation

For high-volume evaluation, apply one of these strategies:

1. **Panel of LLMs (PoLL)**: aggregate votes from multiple judge models to reduce individual model bias — more expensive, more reliable for high-stakes calls.
2. **Hierarchical evaluation**: fast cheap model screens; expensive model handles edge cases. Requires calibrating the screening threshold.
3. **Human-in-the-loop**: automate clear cases, route low-confidence decisions to human review, and feed results back to improve the automated evaluator.

## Examples

Worked input/output examples for direct scoring, pairwise comparison with position swap, and rubric generation live in [Worked Examples](./references/examples.md) — read when you need a concrete I/O template to copy.

## Guidelines

Core rules (the Gotchas section below explains the failure each one prevents):

1. Require evidence before scores; never emit an ungrounded number.
2. Always swap positions in pairwise comparison and check consistency.
3. Match scale granularity to rubric specificity (no 1-10 without per-level rubrics).
4. Separate objective (direct scoring) from subjective (pairwise) criteria.
5. Include confidence scores calibrated to position consistency and evidence strength.
6. Define edge cases explicitly in rubrics.
7. Use domain-specific rubrics, not generic ones.
8. Validate against human judgments — automated eval is only useful if it correlates.
9. Monitor for systematic bias by criterion, response type, and model.
10. Design for iteration — evaluation systems improve with feedback loops.

## Gotchas

1. **Scoring without justification**: ungrounded, hard to debug. Require evidence before the score.
2. **Single-pass pairwise comparison**: position bias corrupts results. Evaluate twice with swapped positions and check consistency.
3. **Overloaded criteria**: multi-aspect criteria score unreliably. Enforce one criterion = one measurable aspect.
4. **Missing edge case guidance**: ambiguous cases handled inconsistently. Include edge cases with clear resolution rules.
5. **Ignoring confidence calibration**: high-confidence wrong judgments are the worst kind. Calibrate to position consistency and evidence strength.
6. **Rubric drift**: standards and model capabilities evolve. Schedule periodic reviews and re-anchor levels against fresh human-annotated examples.
7. **Evaluation prompt sensitivity**: minor wording changes cause material score swings. Version-control prompts and run regression tests before deploying changes.
8. **Uncontrolled length bias**: longer responses score higher even when conciseness is preferred. Add length-neutrality instructions and validate with length-controlled pairs.

## Integration

This skill owns judge design and bias mitigation. Adjacent skills own broader quality gates and infrastructure:

- `evaluation`: general deterministic checks, regression suites, quality gates, and production monitoring.
- `context-fundamentals`: context structure for judge prompts.
- `tool-design`: schemas and error handling for evaluation tools.
- `context-optimization`: token and latency efficiency for high-volume evals.
- `harness-engineering`: locked evaluator surfaces and governance for autonomous loops.

## References

Internal reference:
- [LLM-as-Judge Implementation Patterns](./references/implementation-patterns.md) - Read when: building an evaluation pipeline from scratch or integrating LLM judges into CI/CD
- [Bias Mitigation Techniques](./references/bias-mitigation.md) - Read when: evaluation results show inconsistent or suspicious scoring patterns
- [Metric Selection Guide](./references/metrics-guide.md) - Read when: choosing statistical metrics to validate evaluation reliability
- [Evaluation Pipeline Diagram](./references/evaluation-pipeline.md) - Read when: designing the architecture of a multi-stage evaluation system
- [Worked Examples](./references/examples.md) - Read when: you need concrete input/output templates for direct scoring, pairwise comparison, or rubric generation

External research:
- [Eugene Yan: Evaluating the Effectiveness of LLM-Evaluators](https://eugeneyan.com/writing/llm-evaluators/) - Read when: surveying the state of the art in LLM evaluation
- [Judging LLM-as-a-Judge (Zheng et al., 2023)](https://arxiv.org/abs/2306.05685) - Read when: understanding position bias and MT-Bench methodology
- [G-Eval: NLG Evaluation using GPT-4 (Liu et al., 2023)](https://arxiv.org/abs/2303.16634) - Read when: implementing chain-of-thought evaluation scoring
- [Large Language Models are not Fair Evaluators (Wang et al., 2023)](https://arxiv.org/abs/2305.17926) - Read when: diagnosing systematic bias in evaluation outputs

---

## Skill Metadata

**Created**: 2025-12-24 | **Last Updated**: 2026-05-15 | **Version**: 2.1.0
**Author**: Agent Skills for Context Engineering Contributors
