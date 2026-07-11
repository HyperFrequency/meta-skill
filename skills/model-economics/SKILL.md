---
name: model-economics
version: 0.1.0
description: >-
  Cost-model and ROI framework for the build-vs-buy decision on specialized LLMs: estimate
  one-time training cost, per-token self-hosted inference cost, and the break-even timeline
  versus paying a frontier API. Use as the FIRST step of any model-specialization assessment
  — when deciding whether to fine-tune or distill a smaller custom model, sizing total
  investment, computing months-to-break-even, or building the business case for replacing an
  API with an in-house model. Also covers hybrid routing (cheap specialist + frontier
  fallback) and the utilization, retraining, latency, and frontier-price failure modes that
  erase paper savings. NOT for actually running training (use `peft`, `unsloth`,
  `trl-fine-tuning`, `ml-training-recipes`), serving the model (use `vllm`, `sglang`,
  `tensorrt-llm`), provisioning GPUs (use `modal`, `lambda-labs`, `skypilot`), or measuring
  model quality (use `lm-evaluation-harness`) — this is the economics layer only.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
---

# Model Economics

## Overview

Deciding whether to train a specialized model instead of paying a frontier API is a
build-vs-buy problem, and it is answered with three numbers: the **one-time cost** to train
the specialist, the **ongoing per-token cost** to serve it, and the **break-even timeline**
where cumulative savings overtake that upfront cost. This skill gives you the methodology,
the calculators, and the pricing anchors to produce those numbers — and, just as important,
the failure modes that quietly erase them.

Run this *before* any fine-tuning or serving work. It tells you whether the project is worth
starting, roughly what it will cost, and when it pays back. It does not train, serve, or
evaluate anything — it decides whether you should.

## When to Use This Skill

- Deciding whether to train/distill a custom model versus staying on a frontier API.
- Estimating total investment (training + engineering) for a specialization project.
- Computing months-to-break-even and building a cost/ROI business case.
- Comparing self-hosted inference cost against a frontier API bill.
- Designing a hybrid setup (cheap specialist for the common case, frontier fallback for the
  hard tail) and costing the blend.
- Sanity-checking a vendor or teammate's "we'll save X by self-hosting" claim.

## When NOT to Use This Skill

- **Running the training** — use `peft`, `unsloth`, `trl-fine-tuning`, `axolotl`,
  `llama-factory`, `ml-training-recipes`; distillation → `knowledge-distillation`.
- **Serving / benchmarking throughput** — use `vllm`, `sglang`, `tensorrt-llm`, `llama-cpp`.
- **Provisioning GPUs** — use `modal`, `lambda-labs`, `skypilot`.
- **Measuring model quality** — use `lm-evaluation-harness` or `judge-panel`.
- **Task is diverse, open-ended, or frontier-reasoning-dependent** — specialization will not
  pay off; stay on the API.

## The core question

> Does the recurring saving from serving a cheaper specialist outrun the one-time cost of
> building it, soon enough and robustly enough to matter?

Answer it in five steps:

1. **Intake** — capture monthly frontier spend on the *target task*, task constraint, data
   availability, and quality bar. Questions in `references/decision-framework.md`.
2. **Estimate training cost** — pick a training path (managed LoRA, serverless GPU, or
   dedicated GPU) and read the anchor from `references/pricing-tables.md`.
3. **Estimate inference cost** — compute self-hosted $/M tokens with the calculator, using
   *measured* throughput and *realistic* utilization.
4. **Break-even** — run `break_even_analysis(...)` and lay out the ROI timeline.
5. **Decide** — check the qualitative fit and stress-test against the failure modes before
   you trust the number.

## Break-even at a glance

The one calculation everything else feeds:

```
monthly_savings        = monthly_api_spend − monthly_inference_cost − monthly_maintenance
total_upfront          = training_cost + (setup_hours × hourly_rate)
months_to_break_even   = total_upfront / monthly_savings      # only if monthly_savings > 0
```

If `monthly_savings <= 0` the specialist costs more to run than the API and the project is
dead regardless of upfront cost. The full function (with maintenance, year-1/year-2 net, a
worked example, and the ROI timeline template) is in `references/calculators.md`.

**Rule of thumb on savings gap:** a specialized 8B model self-served costs roughly
**$0.05–0.15 per 1M tokens** versus **$5–25/M** for the premium frontier tier — about
50–500x cheaper per request. That gap collapses against the budget tier, so below ~$500/mo
of spend, or against already-cheap models, specialization rarely pays for itself on cost
alone — justify it with a quality or latency edge instead.

## Decision shortcuts

| Monthly spend on the task | Verdict |
|---------------------------|---------|
| < $500 | Usually not worth it — upfront cost dominates |
| $500–2K | Worth investigating |
| $2K+ | Strong candidate |
| $10K+ | Almost certainly worth it |

**Hybrid is often the right answer:** route ~90% of requests to the cheap specialist and
~10% to a frontier fallback for novel/hard cases → 80–90% cost reduction while keeping
frontier quality on the tail. Cost it as a blend and measure router accuracy, not just the
blended price. Details and the strong/weak-case checklist: `references/decision-framework.md`.

## Watch these before you trust the number

The four estimates that most often turn a "great ROI" into a loss — each expanded, with
fixes, in `references/decision-framework.md`:

- **Utilization** — self-hosted $/M assumes a full GPU; a bursty dedicated GPU at 30% busy
  costs ~3x the headline. Prefer serverless (scale-to-zero) or size to sustained load.
- **Retrain/drift treadmill** — specialists decay; budget periodic retrains + eval as a
  recurring line (`monthly_maintenance_hours`), not a one-off.
- **Frontier price cuts** — the frontier trends cheaper; stress-test at frontier −30%.
- **Engineering underestimate** — "one week" is usually 2–3x; double it and re-check.

Always run the sensitivity check (0.5x/2x traffic, frontier −30%, setup ×2) in
`references/calculators.md`. If break-even survives all of them, the case is robust.

## References

- `references/pricing-tables.md` — frontier API tiers, training-cost anchors (managed LoRA /
  serverless / dedicated GPU), self-hosted inference throughput tables, and a
  verify-before-quoting checklist. **All figures are volatile — websearch current prices.**
- `references/calculators.md` — the `inference_cost_per_million_tokens` and
  `break_even_analysis` functions (plain Python, no deps), a worked example, the ROI timeline
  template, and the sensitivity check.
- `references/decision-framework.md` — intake questions, strong/weak-case checklists, hybrid
  routing, the full failure-mode list with fixes, and the hand-off boundaries to sibling
  skills.
