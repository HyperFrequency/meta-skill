# Adapter guide — the single integration point

Everything task-specific lives in a `GEPAAdapter`. The engine owns Pareto bookkeeping, selection,
budget, and mutation orchestration; the adapter owns exactly two things: **evaluate a batch** and
**build a reflective dataset**. Trait (`gepa::GEPAAdapter`, from `src/core/adapter.rs`):

```rust
#[async_trait]
pub trait GEPAAdapter<DataInst, T, RO>: Send + Sync
where DataInst: Send, T: Send, RO: Send + Serialize {
    async fn evaluate(
        &self,
        batch: &[DataInst],
        candidate: &Candidate,          // IndexMap<String,String>: component name -> text
        capture_traces: bool,
    ) -> Result<EvaluationBatch<T, RO>>;

    async fn make_reflective_dataset(
        &self,
        candidate: &Candidate,
        eval_batch: &EvaluationBatch<T, RO>,   // result of evaluate(..., capture_traces=true)
        components_to_update: &[String],
    ) -> Result<ReflectiveDataset>;            // HashMap<String, Vec<serde_json::Value>>
}
```

Type params: `DataInst` = a training/val item (any `Clone + Send + Sync + 'static`); `T` = opaque
trace type (use `()` if you capture none); `RO` = raw output, must be `Serialize` (often `String` or
`serde_json::Value`).

## `evaluate`

- Read the component text you care about: `candidate.get("instructions").map_or("", String::as_str)`.
- Run your program/LLM on each item, produce an `output` and a numeric `score` (**higher is better**).
- Return `EvaluationBatch::new(outputs, scores)` — `outputs.len() == scores.len() == batch.len()`.
- When `capture_traces == true` you **must** attach traces: `.with_trajectories(traces)` with one
  trace per output. The engine calls with `capture_traces=true` right before reflection so
  `make_reflective_dataset` has material.
- Multi-objective: attach `.with_objective_scores(vec_of_maps)` — one `HashMap<String,f64>` per
  example. Required if you use any `FrontierType` other than `Instance`.

### Error-handling contract (critical)

> Do **not** return `Err` for a single bad example. Give it a `0.0` score in the batch. Reserve `Err`
> for unrecoverable systemic failures (network down, malformed config). A per-example `Err` aborts the
> entire optimization run.

Non-finite scores (`NaN`/`inf`) are rejected by `EvaluationBatch::validate_lengths`; clamp or map them
to a finite failure score.

## `make_reflective_dataset`

Return, for **each** name in `components_to_update`, a `Vec` of JSON records that teach the reflection
LM what went wrong. The record schema the built-in meta-prompt expects:

```json
{ "Inputs": { "...": "..." }, "Generated Outputs": "...", "Feedback": "..." }
```

`Feedback` is the highest-value field — write *why* an output failed and, when possible, the corrective
signal (expected answer, rubric violation, missing fact). Returning an **empty** vec for a component
tells the engine to skip reflection for it this round (this is how the offline mock examples avoid ever
calling the LM). Minimal skeleton:

```rust
async fn make_reflective_dataset(&self, _c: &Candidate,
    eval: &EvaluationBatch<(), String>, components: &[String]) -> Result<ReflectiveDataset> {
    let records: Vec<Value> = eval.scores.iter().zip(&eval.outputs).map(|(s, out)| json!({
        "Inputs": { "output": out },
        "Generated Outputs": out,
        "Feedback": if *s >= 0.5 { "acceptable" } else { "wrong — <explain>" },
    })).collect();
    Ok(components.iter().map(|k| (k.clone(), records.clone())).collect())
}
```

## Component metadata — steering the teacher per component

`OptimizeConfig::component_metadata` (a `ComponentMetaMap`) tags each component so the engine picks the
right meta-prompt (`Text`/`Code`/`Config`) and gives the teacher context:

```rust
use gepa::core::component::{ComponentMeta, ComponentMetaMap};
let mut meta = ComponentMetaMap::new();
meta.insert("instructions".into(), ComponentMeta::text("System instruction for the QA assistant"));
meta.insert("architecture".into(), ComponentMeta::code("Model architecture", "rust"));
meta.insert("hyperparams".into(),  ComponentMeta::config("Training hyperparameters")
    .with_constraints(HashMap::from([("lr".into(), "1e-5..1e-2".into())])));
```

`ComponentKind::{Text, Code, Config}` selects `META_PROMPT_TEMPLATE` / `CODE_META_PROMPT_TEMPLATE` /
`CONFIG_META_PROMPT_TEMPLATE` respectively.

## Multi-component prompts

A `Candidate` can hold many components (e.g. `"parser"` + `"solver"`, as in `examples/merge_demo.rs`).
`ComponentSelectorKind::RoundRobin` mutates one component per iteration (advancing each round);
`All` mutates every component each iteration. Multi-component is the setup where `use_merge = true`
pays off, since merge recombines per-component winners across lineages.

## `ProcessAdapter` — evaluate via an external binary

When "evaluate a candidate" means "run a training script / benchmark / compiled program and read a
metric from stdout", use the built-in `gepa::adapters::ProcessAdapter` instead of hand-writing an
adapter. It spawns a child process per evaluation, injects the candidate, and parses metrics:

```rust
use gepa::adapters::ProcessAdapter;
use gepa::adapters::process::{ScoreDirection, parse_key_value_metrics, PassMode};
use std::time::Duration;

let adapter = ProcessAdapter::new("cargo")
    .args(["run", "--release", "--", "train"])
    .working_dir("/path/to/project")
    .timeout(Duration::from_secs(330))
    .pass_mode(PassMode::EnvVars)                 // GEPA_<COMPONENT_NAME>=<text> in the child env
    .metric_parser(|stdout| parse_key_value_metrics(stdout))  // reads "key: value" lines
    .score_key("val_bpb")
    .score_direction(ScoreDirection::Lower)       // Lower-is-better metrics are negated internally
    .env("EXTRA", "1")
    .objective_keys(vec!["val_bpb".into(), "tokens_per_sec".into()]);  // optional multi-objective
```

- **Passing the candidate**: `PassMode::EnvVars` sets `GEPA_<COMPONENT_NAME>=<value>` env vars;
  `PassMode::JsonFile { path }` writes all components to a JSON file and passes its path.
- **Score direction**: GEPA is internally higher-is-better; `ScoreDirection::Lower` negates the parsed
  metric so loss/BPB-style objectives sort correctly.
- **Parser**: `parse_key_value_metrics` reads `key: value` lines from stdout; supply your own
  `Fn(&str) -> HashMap<String,f64>` for other formats.

This is the pattern for wiring GEPA to any evaluator you already run from the shell — including a
prompt served by a separate process. If your evaluator is a Python/other-language eval command that
prints a JSON score, `ProcessAdapter` is the bridge (conceptually the same black-box eval that
`neuro-code/prompt-optimize` shells out to, but here feeding GEPA's reflective/Pareto machinery).
