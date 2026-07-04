# Running the loop & wiring it into the harness

Standalone, workflow-evolution is a `gepa::optimize(cfg).await` call whose candidate is a topology spec.
In the neuro-centrifuge harness it is **Loop 1's config-component instantiation** — a durable Temporal
workflow. This file covers both.

## 1. The standalone `OptimizeConfig`

Same shape as gepa-evolve, three differences: (a) the seed candidate holds a **spec document**, (b)
`component_metadata` marks it `Config` with topology constraints, (c) the `GEPAAdapter` compiles+scores
a graph (see `eval-gate.md`) instead of running a prompt.

```rust
use std::sync::Arc;
use std::collections::HashMap;
use gepa::core::data_loader::VecLoader;
use gepa::{optimize, Candidate, ComponentMeta, ComponentMetaMap,
           LMConfig, OptimizeConfig, StopConditionConfig, FrontierType};

let mut seed = Candidate::new();
seed.insert("topology".into(), serde_json::to_string_pretty(&seed_spec)?);  // the graph spec

let mut meta = ComponentMetaMap::new();
meta.insert("topology".into(),
    ComponentMeta::config("Agent research graph (JSON: nodes/edges/conditional_edges).")
        .with_constraints(HashMap::from([
            ("research.width".into(), "integer, 1-6".into()),
            ("review.rounds".into(), "integer, 1-4".into()),
            ("_invariant".into(), "reachable entry->output, no orphans, bounded revisits".into()),
        ])));

let mut cfg = OptimizeConfig::new(
    seed,
    Arc::new(VecLoader::new(train_tasks)),   // task instances the graph must solve
    Arc::new(VecLoader::new(val_tasks)),     // valset — Pareto tracking + best_candidate()
    Arc::new(TopologyAdapter::new(compiler, scorer)),   // compiles + runs + scores a spec
    LMConfig { model: "gpt-4o-mini".into(),
               api_key: std::env::var("OPENAI_API_KEY").unwrap_or_default(),
               base_url: "https://api.openai.com".into(), ..LMConfig::default() },
);
cfg.component_metadata = meta;                          // <-- the Config hook
cfg.frontier_type      = FrontierType::Instance;        // or Objective for task/latency/cost Pareto
cfg.use_merge          = true;                          // Algorithm-4 merge of complementary shapes
cfg.cache_evaluation   = true;                          // don't re-run an unchanged spec
cfg.stop_condition     = StopConditionConfig {
    max_metric_calls: Some(150),   // graph runs are expensive — budget tightly
    timeout: Some(std::time::Duration::from_secs(3600)),
    ..Default::default()
};

let result = optimize(cfg).await?;
let best_spec: String = result.best_candidate()?["topology"].clone();
```

`GEPAResult` gives `best_candidate()`, `best_idx()`, per-candidate `val_aggregate_scores`, lineage
`parents`, the per-instance frontier, and `total_metric_calls`; it round-trips through JSON. To have
`best_candidate()` return just the spec string set `cfg.str_candidate_key = Some("topology".into())`.

**Merge for topology** (`use_merge = true`, Algorithm 4): combines complementary Pareto specs that each
win on different instances. Only trust a merged spec if it still passes the hard structural gate —
merging two valid graphs can produce an invalid one, which your adapter must reject as `0.0`.

## 2. Stop conditions & HITL

`gepa` ships composable stoppers (`gepars/src/utils/stop_condition.rs`, `StopCondition::should_stop`):
`MaxMetricCallsStopper`, `MaxIterationsStopper`, `TimeoutStopper`, `NoImprovementStopper`, and
**`SignalStopper`** (stops after SIGTERM/SIGINT). In the harness the `SignalStopper` is the HITL seam:
map a Temporal **signal** onto the stopper so a human can pause/stop the topology search from the SSE
bridge (spec §b Loop 1: "SignalStopper ↔ Temporal signal"). `NoImprovementStopper` is worth setting for
topology because structural search plateaus hard once the good shape is found.

## 3. Temporal-workflow wrapping (Loop 1)

Per spec §b, the loop is a durable workflow mutating **payloads only** (the spec doc), never generated
code — D1-safe, ADAS-cautious:

```
EvolutionWorkflow(spec: EvolutionSpec{ target: GraphSpecRef, adapter, budget, stop })
  state: GEPAState JSON (gepars) persisted in workflow state; continue-as-new per K iterations
  per iteration:  Select -> SampleMinibatch -> EvaluateCandidate ×k (activities, single exec owner)
                  -> BuildReflectiveDataset (from trace-store) -> ProposeMutation (Config meta-prompt)
                  -> MergeMaybe -> UpdateParetoFrontier + PersistLineage -> Gate (n>=3 trials, variance)
```

Key wiring points:

- **State**: `GEPAState` (Pareto frontier + eval cache + budget) is JSON-serializable — persist it in
  workflow state and `continue-as-new` every K iterations to bound history size.
- **Determinism**: keep all I/O (compile, run graph, LM reflect) inside **activities**; the workflow
  body stays deterministic (single execution owner per candidate — FIX-18).
- **Observability** (via `GEPACallback`, `gepars/src/core/callbacks.rs`): `on_iteration_end`,
  `on_candidate_accepted/rejected`, `on_pareto_front_updated`, `on_state_saved`, `on_error`, and
  **`on_budget_updated`** (`BudgetUpdatedEvent`). Route these to emit OTel GenAI spans into
  `trace-store`, write scores to `_llm_scores`, and log topology lineage to `experiment-tracker`.
- **Budget guard**: `on_budget_updated` carries the running cost (from `llm-router`); trip a stop signal
  when it exceeds the budget — graph-running loops overspend faster than prompt loops.

## 4. Promotion = a label move, not a code change

The winning topology deploys by flipping a **spec-registry label** (Langfuse deployment-label pattern,
spec §b Loop 1 promotion): the serving path reads whatever spec the `prod` label points at, so
promoting a new topology is a label move gated on the class-5 eval beating the pinned baseline — no
redeploy, no code edit. Record the config-snapshot hash (from `topology-as-config.md` §6) alongside the
label so any served topology is exactly reproducible.

## 5. Composing with the sibling loops

Topology and content evolve on **separate** loops, in order:

1. **workflow-evolution** (this) fixes the *shape* — nodes, wiring, fanout, rounds, panel topology.
2. **gepa-evolve** then evolves the *prompt text* inside each node (`prompt_ref` → registry entry).
3. **alpha-evolve** separately evolves any *executor code* a node runs.

Interleaving them in one loop conflates the search space and destroys attribution (you can't tell
whether a win came from a rewire or a reworded prompt). Evolve one layer at a time; pin the others.
Scoring stages inside an evolved graph call **judge-panel** for their verdicts, and trajectory feedback
for the reflective dataset can be mined by **trajectory-miner**.
