# Flywheel Architecture — the four planes and the donor→plane map

This is the structural spec for the neuro-centrifuge inference→feedback→optimization loop. It defines the
planes, how they connect, and which TensorZero-donor feature is the behavioral reference for each. All plane
names are neuro-centrifuge targets from the autoresearch PRD §6 (D6/D12 phase-1); the donor names are
TensorZero-core modules at pinned SHA `62eb8f63e`.

## The four planes (plus the router that feeds them)

```
llm-router ──emits──▶ feedback-store ──reads──▶ experiment-tracker ──drives──▶ model-optimizer
   │  (inference,        │  (Chat/Json/ModelInf     │  (variant sampling,          │  prompt-evolver
   │   variant sample,   │   rows, episodes,        │   weighted A/B + Track-      │  (GEPA loop)
   │   cache, cost)      │   feedback/metrics,      │   and-Stop, per-variant      │
   │                     │   datapoints, DPO)       │   regression queries)        │
   └─────────────────────┴──────── flywheel-config (functions/variants/metrics/evals) ┘
                                    ── the shared genome every plane reads ──
```

### 1. `flywheel-config` — the genome (port FIRST)

The config model is the spine every other plane reads. Port it before inference types or the dependency graph
fights you (explicit donor risk note: *"tensorzero-core is one large cross-referencing crate — port
flywheel-config + inference types first"*).

Core config objects (donor `config/mod.rs`, `config/built_in.rs`):

- **Function** — a named task with an I/O contract (Chat or Json). Holds a set of **variants**.
- **VariantInfo / VariantConfig** — one concrete way to serve a function: a prompt template + schema + model
  + inference strategy (chat_completion, best_of_n, mixture_of_n, dicl, chain_of_thought). The variant's
  **prompt template + schemas are the GEPA mutation unit** — evolving a variant = mutating a payload.
- **MetricConfig** — `{ type: boolean|float, optimize: min|max, level: inference|episode, description }`.
  This is the reward definition. See `feedback-and-metrics.md`.
- **Eval config** — evaluators (heuristic or LLM-judge) attached to a function, referenced by GEPA via
  `evaluator_names`.
- **Config snapshot + canonical hash** — every config state hashes to a canonical id so any inference can be
  re-run under its **exact** config. This is what makes lineage reproducible; `experiment-tracker` stores the
  snapshot hash alongside every experiment/optimization result.

Lifecycle: donor uses `Uninitialized*` → validated → loaded (`UninitializedVariantInfo::load`,
`GEPAConfig::load`, etc.). Mirror that: deserialize untrusted TOML/JSON into `Uninitialized…`, validate,
then hand a validated struct to the runtime. ts-rs + JsonSchema give TS/Rust parity for the UI.

### 2. `feedback-store` — durable memory of what happened

Stores every inference and everything said about it. Postgres migrations are canonical; ClickHouse skipped.
Owns: Chat/Json/ModelInference rows, the **episode** model (UUIDv7 `episode_id`), the feedback/metrics
tables (boolean, float, comment, demonstration), and **datapoint curation** (`into_datapoint_insert`) that
promotes live inferences into training datasets, including DPO `dispreferred_outputs`. Full detail:
`feedback-and-metrics.md`.

### 3. `experiment-tracker` — which variant is winning, and is it real

Owns variant selection at inference time (weighted `VariantSampler`, namespaced) and the anytime-valid
Track-and-Stop bandit; owns the **regression queries** (per-variant mean/variance/cost from
`FeedbackByVariant` / variant-statistics rows); owns the prompt registry (variants + their labels) and
config-snapshot lineage. Promotion = **moving a label** (Langfuse pattern), never a code deploy. Full
detail: `experimentation.md`.

### 4. `model-optimizer` + `prompt-evolver` — turn feedback into better artifacts

`prompt-evolver` runs the GEPA loop (analyze → mutate → pareto → evaluate) as a durable, sequential
optimizer job; `model-optimizer` launches SFT/RFT fine-tune jobs (P2) against curated datapoints. Both read
the feedback store and write new variants back into the registry for the experiment plane to A/B. Full
detail: `optimization.md`.

## The Autopilot tool surface (D6 demo activity spec)

TensorZero's **Autopilot** is a durable agent whose tools are exactly the flywheel verbs — a ready-made
activity surface to re-host on the first-party Temporal spine (donor `autopilot-tools` crate):

- `InferenceTool` — run a function/variant, optionally under a **historical config snapshot**.
- `FeedbackTool` — attach a metric/comment/demonstration to an inference or episode.
- `RunEvaluationTool` — score inferences/workflows with the eval config.
- `LaunchOptimizationWorkflowTool` — kick a GEPA/SFT/RFT job.

Re-host these as Temporal activities in `harness_worker` + `prompt-evolver`. The `TaskTool`/`SimpleTool`
"hidden side-info" pattern is a pattern reference only (not a literal port).

## How this maps to Loop 1 (the phase-1 evolution workflow)

The PRD's **Loop 1 — Prompt/workflow evolution** is this architecture in motion: a durable Temporal
`EvolutionWorkflow` that mutates payloads only (prompts, graph specs, skill specs, config genomes). Each
iteration selects a candidate (gepars selector), samples a pinned-version minibatch from
`experiment-tracker`, evaluates via the `harness_eval` runner, builds a reflective dataset from
`trace-store` failures, proposes a mutation, optionally merges (Algorithm 4), updates the Pareto frontier +
persists lineage, and gates with a variance-aware baseline compare. See `optimization.md` for the full step
list and where the donor pieces slot in.

## Non-negotiable invariants

- **Provenance headers + pinned donor SHA (`62eb8f63e`) on every ported file** (D2).
- **Budget guard on every loop** — a `BudgetUpdated → stop` signal, cost sourced from `llm-router`.
- **Every loop emits OTel GenAI spans** into `trace-store`, **writes scores** to `_llm_scores`, and **logs
  lineage** to `experiment-tracker`. A loop that improves an artifact without leaving this trail is a bug.
