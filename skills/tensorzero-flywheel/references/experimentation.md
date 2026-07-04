# Experimentation — variants, A/B, Track-and-Stop & regression queries (`experiment-tracker`)

Behavioral spec for variant selection and statistical comparison, distilled from TensorZero-core
`experimentation/` (`static_experimentation.rs`, `adaptive_experimentation.rs`, `track_and_stop/`,
`asymptotic_confidence_sequences.rs`), `variant/`, and `db/variant_statistics.rs` at pinned SHA `62eb8f63e`.

## 1. Variants — the unit of experimentation

A **function** has N **variants**; a variant is one concrete serving strategy (prompt template + schema +
model + inference strategy). At inference time the experiment plane samples one variant, records which
variant served the call on the inference row, and lets feedback accrue per-variant. Variant **inference
strategies** (donor `variant/`):

- `chat_completion` — the plain single-call variant.
- `best_of_n_sampling` — draw N samples, a judge picks one (→ `harness_deliberation`).
- `mixture_of_n` — draw N, fuse them (→ `harness_deliberation`).
- `dicl` — dynamic in-context learning: retrieve nearest curated examples as few-shot (P2).
- `chain_of_thought` — **SKIP** (deprecated upstream #5298).
- `dynamic` — variant chosen/parameterized at request time.

Because judges are *also* functions-with-variants, judges are themselves evolvable by the optimization loop.

## 2. Static experimentation — weighted A/B

The `StaticExperimentationConfig` replaces the older `uniform` / `static_weights` split with one type that
deserializes from **either** form:

- a list of variant names `["a", "b"]` → each gets weight 1.0 (uniform), **or**
- a map `{"a": 0.7, "b": 0.3}` → explicit weights (`WeightedVariants`, a `BTreeMap<String, f64>`).

Sampling (`sample_weighted`): intersect the configured weighted variants with the currently **active** set
(a variant can be temporarily disabled), sum their weights, draw `uniform_sample * total_weight`, walk the
cumulative weight. Edge cases the donor handles and you must too:

- **Total weight ≤ 0** (all configured variants inactive, or all-zero weights) → fall back deterministically
  (don't divide by zero; pick from candidates or error explicitly).
- **Empty intersection** between configured and active variants → defined fallback, not a panic.
- Weights are relative, not probabilities — they need not sum to 1. Document this so config authors aren't
  surprised.

### Namespaces

`ExperimentationConfigWithNamespaces` lets one function carry **different experiment configs per namespace**
(e.g. tenant, environment, cohort). `get_for_namespace(ns)` returns the namespace's config or the default.
Use namespaces to run an experiment for one cohort without disturbing everyone else's traffic split.

## 3. Adaptive experimentation — Track-and-Stop (P2, port WITH its tests)

`AdaptiveExperimentationConfig` currently supports one algorithm: **Track-and-Stop**, an anytime-valid
best-arm-identification bandit. Instead of a fixed 50/50 split for a fixed horizon, it adaptively routes more
traffic to promising variants and **stops as soon as** an asymptotic confidence sequence proves one variant
best at the target confidence — you don't pre-commit a sample size.

- Backed by `asymptotic_confidence_sequences.rs` — anytime-valid means you may peek at results continuously
  without inflating the false-positive rate (unlike a fixed-n t-test).
- **Port discipline:** the PRD marks this *"port with its tests or defer"*. The statistics are subtle; do
  **not** re-derive the stopping rule from memory — bring the donor's tests across as parity oracles or leave
  it in P2 and use static weighted A/B for phase-1.

## 4. Per-variant regression queries — the promotion gate's evidence

The experiment plane's read side aggregates feedback **by variant** so the loop can ask "is variant B
actually better than variant A, or is it noise?". The donor's `VariantStatisticsRow` (per
function_name × variant_name) carries:

- `inference_count`
- `total_input_tokens` / `total_output_tokens`
- `total_cost` (Decimal) + `count_with_cost`
- `total_provider_cache_read_input_tokens` / `..._write_input_tokens`
- `processing_time_ms_quantiles` / `ttft_ms_quantiles` — **ClickHouse-only; `None` on Postgres**

Join these against the metric feedback tables (`FeedbackByVariant` pattern) to get **per-variant mean and
variance** of each metric. That mean±variance, plus cost, is exactly what the promotion gate compares.

## 5. The promotion gate (regression-gated deploy)

No variant is promoted on a raw mean. The Loop-1 gate (PRD §b) requires:

1. **n ≥ 3 trials per input** (Braintrust rule) — enough samples per datapoint to estimate variance.
2. **Variance-aware compare vs. baseline** — the candidate must beat the *current* baseline accounting for
   spread, respecting the metric's `optimize: min|max` direction. A higher mean with overlapping variance is
   not a win.
3. **Hill-climb framing** (BaseExperiment): generation N's winner *is* generation N+1's expected baseline.
   Each promotion raises the bar for the next.

**Promotion mechanism = label move, not code deploy.** The winning variant already exists in the prompt
registry; "deploying" it flips a registry **label** (Langfuse pattern) to point at the new variant. There is
no code change, so rollback is instant (move the label back) and every deploy is auditable as a lineage
event with the config-snapshot hash.

## 6. Lineage

Every experiment and every promotion is logged to `experiment-tracker` with the **config-snapshot canonical
hash** (see `flywheel-architecture.md`). This is what lets you re-run any historical inference under its
exact config and reconstruct *why* a given variant was chosen — the audit trail the whole flywheel depends
on. A promotion without a persisted snapshot hash is not reproducible; treat that as a bug.
