# Config reference — every knob, with defaults

All from `~/neuro-centrifuge-repos/gepars/src/api.rs`. Build `OptimizeConfig::new(seed, trainset,
valset, adapter, lm_config)` and set fields directly; everything past the five required args has a
sensible default.

## `OptimizeConfig` fields

| Field | Type | Default | Meaning |
|---|---|---|---|
| `seed_candidate` | `Candidate` | — (required) | Starting `name→text` map |
| `trainset` | `Arc<dyn DataLoader<Id,Item>>` | — (required) | Training split (minibatches drawn here) |
| `valset` | `Arc<dyn DataLoader<Id,Item>>` | — (required) | Validation split — **Pareto tracking + `best_candidate`** run here |
| `adapter` | `Arc<dyn GEPAAdapter<Item,T,RO>>` | — (required) | Your eval + reflection logic |
| `lm_config` | `LMConfig` | — (required) | Reflection LM settings (below) |
| `stop_condition` | `StopConditionConfig` | `max_metric_calls: Some(500)` | When to stop (below) |
| `candidate_selector` | `CandidateSelectorKind` | `Pareto` | Base-candidate strategy |
| `epsilon` | `f64` | `0.1` | ε for `EpsilonGreedy` (ignored otherwise) |
| `component_selector` | `ComponentSelectorKind` | `RoundRobin` | Which components to mutate each round |
| `minibatch_size` | `usize` | `3` | Training examples per iteration |
| `use_merge` | `bool` | `false` | Enable Algorithm-4 system-aware merge |
| `max_merge_invocations` | `usize` | `5` | Merge budget across the whole run |
| `val_overlap_floor` | `usize` | `5` | Min shared val IDs before a merge is attempted |
| `frontier_type` | `FrontierType` | `Instance` | Pareto strategy (below) |
| `perfect_score` | `Option<f64>` | `Some(1.0)` | Threshold for the skip optimization |
| `skip_perfect_score` | `bool` | `true` | Skip reflection when the whole minibatch already scores `perfect_score` |
| `reflection_prompt_template` | `Option<PromptTemplateConfig>` | `None` | Override the Appendix-C meta-prompt |
| `component_metadata` | `ComponentMetaMap` | `{}` | Per-component kind/description/constraints |
| `callbacks` | `Vec<Box<dyn GEPACallback<Id>>>` | `[]` | Observers (below) |
| `rng_seed` | `Option<u64>` | `None` | Reproducibility seed (also stored in result) |
| `run_dir` | `Option<String>` | `None` | Artifact directory (stored in result metadata) |
| `str_candidate_key` | `Option<String>` | `None` | If set, `best_candidate` returns the plain string under this key |
| `track_best_outputs` | `bool` | `true` | Track per-val-id best output seen |
| `cache_evaluation` | `bool` | `false` | Enable eval cache — cached (candidate,example) pairs don't consume budget |

## `StopConditionConfig` — combined with OR (first to fire wins)

| Field | Default | Meaning |
|---|---|---|
| `max_metric_calls` | `Some(500)` | Budget in **per-example metric evaluations**; cached examples are free. `None` = unlimited |
| `max_iterations` | `None` | Hard iteration cap |
| `timeout` | `None` | Wall-clock limit (`std::time::Duration`) |

If **all three are `None`**, a safety valve caps the run at 10,000 iterations (it never runs forever).
Other stoppers are exported for manual engine use: `NoImprovementStopper`, `TimeoutStopper`,
`FileStopper`, `SignalStopper`, `MaxIterationsStopper`, `MaxMetricCallsStopper`, combined via
`CompositeStopper` / `CompositeMode`.

## `LMConfig` — the reflection (teacher) LM

| Field | Default | Meaning |
|---|---|---|
| `model` | `"gpt-4o-mini"` | LiteLLM-style model id |
| `api_key` | `""` | Bearer token; `""` for local/unauthenticated servers. Redacted in `Debug` |
| `base_url` | `"https://api.openai.com"` | API base, **no trailing slash** |
| `temperature` | `Some(1.0)` | Sampling temperature for rewrites |
| `max_tokens` | `Some(4096)` | Max tokens for a reflection output |
| `max_retries` | `3` | HTTP retries with exponential back-off |

`OpenAICompatibleLM` speaks the standard `/v1/chat/completions` protocol. Supported providers (set
`base_url`): OpenAI `https://api.openai.com` · Anthropic OpenAI-shim `https://api.anthropic.com` ·
Ollama `http://localhost:11434` · LMStudio `http://localhost:1234` · vLLM `http://localhost:8000` ·
any OpenAI-compatible endpoint. Pass `api_key: ""` for unauthenticated local servers.

## Enums

- **`CandidateSelectorKind`**: `Pareto` (default, Algorithm 2, frequency-weighted frontier),
  `CurrentBest` (always the top average-score candidate), `EpsilonGreedy` (exploit `CurrentBest`
  w.p. `1−ε`, else random — uses `epsilon`).
- **`ComponentSelectorKind`**: `RoundRobin` (default, one component per iteration), `All` (every
  component each iteration).
- **`FrontierType`**: `Instance` (default — per validation example, the paper's approach), `Objective`
  (per named objective), `Hybrid` (per-example **and** per-objective), `Cartesian` (per
  `(example, objective)` pair). Anything but `Instance` **requires** the adapter to populate
  `EvaluationBatch::objective_scores` or the engine errors at construction.
- **`PromptTemplateConfig`**: `Single(String)` (one template for all components) or
  `PerComponent(IndexMap<String,String>)` (missing components fall back to the built-in template).

## `GEPAResult` — the run artifact

Accessors: `num_candidates()`, `num_val_instances()`, `best_idx() -> Result<ProgramIdx>`,
`best_candidate() -> Result<&Candidate>`, `best_candidate_str() -> Option<&str>` (set
`str_candidate_key`), `to_json()` / `from_json()`. Public fields: `candidates`, `parents` (lineage;
seed has `[None]`), `val_aggregate_scores` (`NEG_INFINITY` for unseen), `val_subscores`
(`{val_id: score}`), `per_val_instance_best_candidates` (the instance frontier), `discovery_eval_counts`,
optional `val_aggregate_subscores` / `per_objective_best_candidates` / `objective_pareto_front`
(multi-objective), `total_metric_calls`, `num_full_val_evals`, `run_dir`, `seed`. Schema is versioned
(`SCHEMA_VERSION = 2`) so old JSON is detected.

## Callbacks — `GEPACallback<Id>` (all methods default to no-op; override what you need)

Lifecycle events: `on_optimization_start/end`, `on_iteration_start/end`, `on_candidate_selected`,
`on_minibatch_sampled`, `on_evaluation_start/end/skipped`, `on_valset_evaluated`,
`on_reflective_dataset_built`, `on_proposal_start/end`, `on_candidate_accepted/rejected`,
`on_merge_attempted/accepted/rejected`, `on_pareto_front_updated`, `on_budget_updated`,
`on_state_saved`, `on_error`. Compose several with `CompositeCallback`. Use these for custom metrics,
progress, checkpointing, and early-stopping hooks. (Structured `tracing` logs are emitted regardless.)

## Errors — `GEPAError` variants

`AdapterEvaluation`, `AdapterReflectiveDataset`, `Evaluation`, `ProposalFailed`, `Proposal`,
`LMError`, `LmApi`, `RetriesExhausted`, `EmptyDataset`, `Config`, `AdapterError`, plus `From` for
`std::io::Error`, `serde_json::Error`, `reqwest::Error`. `EmptyDataset` at startup means an empty
valset; `Config` wraps invalid `epsilon`/`minibatch_size`/LM-client construction; `RetriesExhausted`
means the reflection LM endpoint kept failing (check `base_url`/`api_key`/network).

## Commands

```bash
cd ~/neuro-centrifuge-repos/gepars
cargo run --example minimal | custom_adapter | merge_demo | quickstart
OPENAI_API_KEY=sk-... cargo run --example quickstart -- --live   # real LM
cargo test                                                       # unit tests
cargo test --test e2e -- --ignored                              # hermetic e2e (HTTP LM path, cache, persistence)
cargo clippy -- -D warnings
```

The crate forbids `unsafe` (`unsafe_code = "forbid"`). Optional `wandb` / `mlflow` cargo features exist
but are stubs (full experiment-tracking integration is TBD).
