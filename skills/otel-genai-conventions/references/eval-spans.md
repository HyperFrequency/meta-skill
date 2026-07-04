# Evaluation as Telemetry — `gen_ai.evaluation.*`

A judge, scorer, or metric run is itself an LLM/agent operation, so it belongs in the
same trace tree. OTel's GenAI conventions carry an **evaluation** shape so a score lands
on the trace it scored, queryable next to the run it judged. This is the telemetry
contract; the *runners* that produce these spans are **judge-panel** and
**skill-eval-runner**.

## Two things you can attach

An evaluation result can be recorded as a **span event** on the operation that was
evaluated, or as its own child **span** (`gen_ai.operation.name = evaluate`,
`SpanKind::INTERNAL`, name `evaluate <scorer>`). Use a child span when the judge is itself
an LLM call (you want its own tokens/latency); use a span event when the score is a cheap
deterministic post-hoc annotation on an existing span.

## The `gen_ai.evaluation.*` attributes

| Attribute | Type | Notes |
|---|---|---|
| `gen_ai.evaluation.name` | string | The scorer/criterion, e.g. `hallucination`, `context_precision`, `trajectory_accuracy`, `frontier_rubric.depth`. |
| `gen_ai.evaluation.score.value` | double | Numeric score (put the raw number here). |
| `gen_ai.evaluation.score.label` | string | Categorical verdict, e.g. `pass`/`fail`, `hallucinated`/`grounded`. Either or both of value/label may be present. |
| `gen_ai.evaluation.explanation` | string | The judge's rationale / evidence-before-score. |

Record as an event named `gen_ai.evaluation.result` (or the attributes on the `evaluate`
span). Multiple scorers on one run → multiple events/spans, one per `evaluation.name`.

## Evaluator identity (who scored)

The spec's attributes above capture *the score*. To make scores auditable and
regression-comparable you also need *who produced them* — carry these (extension
attributes; keep them namespaced and stable across your fleet):

- **Evaluator kind**: `human` | `model` (LLM-as-judge) | `deterministic` (heuristic/code).
- **Scorer id + version**: an immutable versioned identity, so a score is reproducible and
  a rubric change shows up as a new version rather than silently shifting history.
- **Level**: whether the score is over a single `span`, a whole `trace`, a `session`
  (thread), or an `experiment` — the same score stream serves all four.
- **Source type**: online (sampled on live traffic) vs. offline (dataset run).

If the judge is itself an LLM call, its `evaluate` span still carries normal `chat`-child
spans for the model call it makes — so a judge's own token cost and latency are visible,
and a judge can be evaluated by another judge (nested `evaluate` spans).

## Determinism of the score itself

A judge is non-deterministic; make its **record** deterministic enough to regression on:
pin the scorer version, the judge model, and the prompt template; store the raw judge
output alongside the parsed score so a parser change can be re-run without re-calling the
model. This is what lets `skill-eval-runner` gate on a *score delta* between versions.

## The other eval schema you'll meet: `llm.evaluation.*`

Some backends (the openobserve lineage) predate `gen_ai.evaluation.*` and use an
`llm.evaluation.*` family plus a canonical **score stream** table
(`level` = span|trace|session|experiment, `scorer_id`+`version`, `source_type`). Treat it
as the same idea in a different namespace: when ingesting such traces, map
`llm.evaluation.*` → `gen_ai.evaluation.*` on the way in (the crosswalk lists the
pairs). Do not emit both families on one span.

## Contract with the runner skills

- **judge-panel** emits one `evaluate` span per judge and one aggregated
  `gen_ai.evaluation.result` for the panel verdict; the per-judge spans carry
  `evaluation.explanation` (evidence-before-score) and the aggregate carries the
  consensus `score.value` + `score.label`.
- **skill-eval-runner** emits `evaluate` spans per criterion of a versioned rubric and
  gates on the `score.value` regression across scorer versions.

This file defines only the *attributes*; the aggregation policy, calibration ledger, and
gate logic live in those skills.
