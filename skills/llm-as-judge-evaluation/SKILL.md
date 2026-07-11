---
name: llm-as-judge-evaluation
version: 0.1.0
description: >-
  Evaluate free-form LLM text outputs using frontier models as judges. WHAT:
  pairwise A/B comparison and Likert rubric scoring, mitigation of position /
  length / format / self-preference bias, bootstrap significance testing on win
  rates, and conversion of judge verdicts into (chosen, rejected) preference
  pairs for DPO/RLHF. WHEN: comparing a fine-tuned student against a teacher,
  quality-gating a model release, monitoring production quality over time, or
  mining preference data for open-ended tasks with no ground-truth answer. WHEN
  NOT: tasks with verifiable answers (math, code execution — use exact match or
  unit tests), trivial classification (use accuracy/F1), or safety evaluation
  (use dedicated safety benchmarks). For a reusable multi-judge verdict
  PRIMITIVE that other skills call, use `judge-panel`; for single-judge prompt
  design and calibration, use `ce-advanced-evaluation`; for whole
  agent-pipeline eval systems and regression suites, use `ce-evaluation`.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# LLM-as-Judge Evaluation

## Overview

Use a strong LLM to judge the quality of other models' text outputs when there is
no verifiable ground truth. This skill covers the two workhorse methods —
**pairwise comparison** (which of A/B is better) and **Likert scoring** (rate one
response 1-5 against a rubric) — plus the bias controls, sample-size math, and
preference-data plumbing that turn noisy judge calls into a defensible deployment
decision.

The core insight: judges are far more reliable at *relative* judgments ("which is
better") than *absolute* ones ("how good, on a scale"). Default to pairwise for
model selection and A/B testing; reserve Likert for continuous monitoring and
fixed thresholds.

## When to Use This Skill

- **Student vs teacher** — does a fine-tuned model beat the frontier model it was
  distilled from, on your task?
- **Release quality gate** — automated go/no-go before shipping a model or prompt.
- **Continuous evaluation** — track production output quality over time against a
  frozen judge + rubric.
- **Preference-data mining** — turn comparisons into (chosen, rejected) pairs for
  DPO/RLHF training.
- **No ground truth** — creative, open-ended, or subjective tasks where exact
  answers do not exist.

## When NOT to Use This Skill

- **Verifiable answers** (math, code that runs, structured extraction) — use exact
  match, unit tests, or execution, not a judge.
- **Simple classification** — report accuracy / F1 directly; a judge adds cost and
  variance.
- **Safety / harm evaluation** — use dedicated safety benchmarks and red-team
  suites, not a general-purpose quality judge.
- **You need a reusable verdict object other code calls** — reach for `judge-panel`
  (typed `PanelRequest`/`Verdict`, five topologies, aggregators). This skill is the
  *evaluation workflow* around such judges, oriented at model comparison and
  preference data.
- **You are designing or calibrating a single judge prompt** — `ce-advanced-evaluation`
  owns rubric anchoring and bias mechanisms at the prompt level.

## Core Methods

**Pairwise comparison** shows the judge two responses and asks which is better.
Always run it twice with positions swapped and require agreement, or the judge's
position bias leaks into your results. Minimal shape:

```python
from openai import OpenAI
import json

client = OpenAI()

def judge_pair(user_input, response_a, response_b, criteria, model="gpt-4o"):
    prompt = (
        f"Compare two responses. Criteria:\n{criteria}\n\n"
        f"Input:\n{user_input}\n\nResponse A:\n{response_a}\n\nResponse B:\n{response_b}\n\n"
        'Return JSON: {"winner": "A"|"B"|"tie", "reasoning": "..."}'
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(resp.choices[0].message.content)["winner"]
```

The full position-swapped `pairwise_compare`, the eval-set driver
`evaluate_model_pair`, chain-of-thought judging, reference-grounded comparison,
and tie-rate diagnostics live in
[references/pairwise-comparison.md](references/pairwise-comparison.md).

**Likert scoring** rates one response per dimension on a 1-5 scale against a
rubric. Use it when you need an absolute number to threshold against, not a
head-to-head winner. Rubric design is what separates signal from noise — every
score level must name an *observable* behavior, dimensions must not overlap, and
dimensions get weights. Templates for general quality, code generation, customer
support, and summarization, plus the composite weighted-score helper, are in
[references/scoring-rubrics.md](references/scoring-rubrics.md).

## Controlling Judge Bias

Judges have systematic biases; leaving them uncontrolled invalidates the eval.

- **Position bias** (prefers whichever response is first) — swap A/B, run twice,
  count a win only if both orderings agree; otherwise call it a tie. This is
  non-negotiable for pairwise.
- **Length bias** (prefers longer answers) — add an explicit conciseness criterion.
- **Format bias** (prefers markdown/structure) — normalize formatting before judging.
- **Self-preference** (a model favors its own style) — judge one family's outputs
  with a *different* family (e.g. Claude judges GPT outputs and vice versa).
- **Sycophancy** — keep criteria neutral; don't reveal which response the user
  "expected".

See [references/pairwise-comparison.md](references/pairwise-comparison.md) for the
tie-rate table that tells you whether your rubric is too vague.

## Statistical Significance

A win rate of 55% on 40 examples is noise. Bootstrap a confidence interval and
require it to clear 50% before you act on a result:

```python
import numpy as np

def bootstrap_win_ci(wins, total, n=10000, ci=0.95):
    rate = wins / total
    samples = np.random.binomial(total, rate, n) / total
    lo, hi = np.percentile(samples, [(1-ci)/2*100, (1+ci)/2*100])
    return {"win_rate": rate, "ci_lower": lo, "ci_upper": hi,
            "significant": lo > 0.5 or hi < 0.5}
```

Sample-size targets: ~100 examples for a directional deployment call, 200-400 for a
reliable ±5% win rate, 500-1000+ for production/publication decisions. The full
table and derivation are in
[references/statistics-and-preference-data.md](references/statistics-and-preference-data.md).

## Generating Preference Data (DPO/RLHF)

Every decisive pairwise comparison yields a training pair: the winner is `chosen`,
the loser is `rejected`. Skip ties. Run both models across your eval set, judge each
pair with position-swap mitigation, and emit `{"prompt", "chosen", "rejected"}`
records. Full `generate_dpo_pairs` implementation is in
[references/statistics-and-preference-data.md](references/statistics-and-preference-data.md).

## Multi-Judge Ensembles

For high-stakes calls, poll several judge models and take a majority (or aggregate
scores). Rather than hand-roll vote math here, delegate to `judge-panel` — it owns
the reusable multi-judge contract (parallel-independent, debate, council,
hierarchical topologies; median/mean/weighted/majority/Borda aggregators; sigma
confidence and a calibration ledger). This skill's job is the model-comparison and
preference-data workflow *on top of* those verdicts.

## Workflow Checklist

1. **Write a rubric** specific to your task (observable anchors, weighted dims).
2. **Assemble a held-out eval set** — 100+ realistic production inputs.
3. **Generate responses** from both models across the set.
4. **Run pairwise comparison** with position-swap mitigation.
5. **Bootstrap the win rate** — require the CI to exclude 50%.
6. **Gate the decision** — student > 50% with a significant CI → proceed.
7. **Export preference pairs** from the decisive comparisons for DPO.

## References

- [references/pairwise-comparison.md](references/pairwise-comparison.md) — full
  position-swapped comparison, eval-set driver, CoT and reference-grounded judging,
  tie-rate and bias diagnostics.
- [references/scoring-rubrics.md](references/scoring-rubrics.md) — Likert scorer,
  rubric design principles, four domain templates, composite weighted scoring.
- [references/statistics-and-preference-data.md](references/statistics-and-preference-data.md)
  — bootstrap CIs, sample-size table, DPO pair generation.
