---
name: workflow-evolution
description: >
  Evolve the declarative TOPOLOGY of a workflow / agent graph — which nodes exist and how they wire
  (edges, conditional routing, fanout width, debate/council rounds, retry-fallback structure, panel
  shape) — under an eval gate, by treating the serialized graph SPEC as a gepars `ComponentKind::Config`
  component and driving GEPA reflective + Pareto mutation over it. Use when the improvement you want is
  the SHAPE of a workflow/graph and you can score a compiled spec: rewire or add/remove nodes, tune
  fanout/rounds/routing, swap a stage's type, or generate adversarial mutants for a class-5 graph eval.
  NOT for mutating a node's PROMPT TEXT (use gepa-evolve), NOT for
  mutating PROGRAM / model CODE in a MAP-Elites archive (use alpha-evolve), NOT for single-metric prompt
  hill-climbing (use prompt-optimize), NOT for scoring/ranking candidates (use judge-panel), and NOT for
  authoring a graph from scratch with no eval to score against.
metadata:
  version: "0.1.0"
---

# Workflow-Evolution

> Loop that mutates declarative **workflow / graph TOPOLOGY** under an eval gate. Engine: the user's
> Rust crate `gepa` v0.1.0 (MIT, `nicholasjpaterno/gepa`) at `~/neuro-centrifuge-repos/gepars`, the same
> GEPA engine `gepa-evolve` wraps — but pointed at a **config genome** (`ComponentKind::Config`) that
> encodes graph structure, not at prompt text. Design source: `neuro-centrifuge-autoresearch.md` §b
> Loop 1 (config meta-prompt = "workflow/graph-spec evolution") and §c class 5 ("graph-spec evolution
> generates adversarial graph mutants").

Every other evolution loop in this library mutates **text**: `alpha-evolve` mutates program/model code
as SEARCH/REPLACE diffs; `gepa-evolve` / `prompt-optimize` mutate the instruction text inside a node.
Workflow-evolution mutates the **wiring between nodes** — the serialized graph spec (node set, edge
set, conditional routing, fanout width, debate rounds, panel topology, retry/fallback structure). The
mutable unit is the *shape of the computation*, not the code that runs a node and not the prompt a node
sends. The artifact you evolve is a declarative spec document (JSON/YAML) that **compiles** into a
runnable graph (a `weavegraph`/`rust-langgraph`-style `add_node`/`add_edge`/`add_conditional_edge`
builder) and is scored under a graph eval gate.

## When to use

Use when the improvement you want lives in a workflow's **structure** and you have an evaluation that
scores a *compiled* spec:

- Rewire an agent graph: change which node feeds which, add a validator/rescue branch, split a serial
  chain into fanout+join, collapse redundant stages.
- Tune structural knobs: fanout width, debate/council rounds `R`, conditional-routing thresholds,
  retry/fallback depth, which judge-panel topology a scoring stage uses.
- Search over topology *families* on a Pareto front (accuracy vs. latency vs. token cost per shape).
- Generate **adversarial graph mutants** to stress a class-5 graph-workflow eval (spec §c row 5).

**Pick the right sibling — do not use workflow-evolution for these:**

| You want to evolve… | Signal | Skill |
|---|---|---|
| **Graph TOPOLOGY** (nodes/edges/routing/fanout/rounds), score a compiled spec, Pareto | "rewire the graph", "evolve the workflow shape", "tune the panel topology" | **workflow-evolution** (this) |
| **Prompt TEXT** inside a node, reflection-driven, Pareto | "improve this instruction", "outperform RL", "reflective mutation" | `neuro-code/gepa-evolve` |
| **A prompt**, single scalar metric, one edit/round keep-if-better | "hill-climb my prompt against my eval" | `neuro-code/prompt-optimize` |
| **Program / model CODE** as diffs in a MAP-Elites archive | "evolve my model", "AlphaEvolve", "diversity archive" | `neuro-code/alpha-evolve` |
| **Score/rank** candidates (returns a verdict, mutates nothing) | "get a panel verdict", "LLM jury" | `neuro-centrifuge/judge-panel` |

If the artifact you edit is *instruction text* → gepa-evolve. If it is *code that runs* → alpha-evolve.
If it is *the graph that orchestrates those nodes* → workflow-evolution. The three compose: evolve the
topology here, then evolve the prompt inside each node with gepa-evolve.

## The core idea (why Config, not Text)

`gepa` annotates each candidate component with a `ComponentKind` (`src/core/component.rs`): `Text`
(default, the Appendix-C prompt meta-prompt), `Code`, or **`Config`**. A `Config` component is driven by
`CONFIG_META_PROMPT_TEMPLATE` (`src/strategies/instruction_proposal.rs`) — a config-aware reflection
prompt that reasons over key→value structure and honors declared `constraints`. That is the exact hook
the design calls out for workflow-spec evolution:

1. Serialize the workflow/graph as a **spec document** (nodes, edges, conditional edges, fanout,
   rounds, panel topology, retry policy) and put it in a `Candidate` under one key, e.g. `"topology"`.
2. Annotate it: `component_metadata["topology"] = ComponentMeta::config("agent graph topology")
   .with_constraints({...})` — constraints encode the valid-topology envelope (reachable Start→End, no
   orphan nodes, fanout ≤ N, DAG-only unless loops are allowed, allowed node/edge kinds).
3. GEPA's config reflective mutation proposes a **new spec**; your `GEPAAdapter::evaluate` **compiles**
   it into a runnable graph and **scores** it; accepted mutants fold into the per-instance Pareto front.

The loop mechanics (select → minibatch → evaluate ×k → reflect → accept-if-better → Pareto → merge →
stop) are identical to `gepa-evolve`; only the **mutable unit and the evaluator** differ. See
`references/topology-as-config.md` for the spec schema, value-tuning vs. structural add/remove-node
mutation, and when to override the built-in config prompt with a custom `reflection_prompt_template`.

## Boundaries & failure modes (read before trusting a run)

- **A topology mutation is only real if it compiles.** The reflection LM emits a spec *string*; it may
  be malformed or violate invariants. Every candidate must pass **compile + structural validation**
  (reachability, no orphan/dangling edges, no-loss/no-dup fanout-join) as a **hard gate** before it is
  scored — an invalid spec scores `0.0`, it does not crash the run. See `references/eval-gate.md`.
- **The gate is not the topology under evolution.** Disjoint-write-scope (spec §c meta-loop): the loop
  may propose graph shapes but may **never** edit its own eval criteria/dataset. Reward-hack watch: a
  mutant that wins by deleting the work (empty graph, skipped validators) must be caught by the
  hard-fail invariants, not rewarded.
- **Config prompt tunes values; structural add/remove needs help.** `CONFIG_META_PROMPT_TEMPLATE` says
  "change only the values, not the format or parameter names" — perfect for fanout width / rounds /
  enum swaps / enable-disable, but it will resist *adding a node*. For structural mutation supply a
  custom `reflection_prompt_template` that permits emitting a new node/edge list, and lean on
  validate-then-repair. Detail in `references/topology-as-config.md`.
- **Valset is the metric that counts** (as in gepa-evolve): Pareto tracking and `best_candidate()` come
  from the valset. A tiny/unrepresentative task set gives a misleadingly "best" topology that overfits
  one instance.
- **Budget is per-example metric calls, not iterations.** Compiling+running a graph per candidate is
  far more expensive than a prompt eval — set `stop_condition.max_metric_calls` and a `timeout`
  deliberately, and use `cache_evaluation` so unchanged specs don't re-run. Cost flows through the
  `on_budget_updated` callback → budget guard.
- **This is a library, not a CLI.** There is no `gepa run`; you drive it from a small Rust harness or an
  external eval binary via `ProcessAdapter`. In the harness it runs as a Temporal workflow (GEPAState
  JSON in workflow state, continue-as-new); see `references/loop-integration.md`.

## Reference material (load what the task needs)

- **`references/topology-as-config.md`** — the workflow/graph spec schema (nodes / edges / conditional
  edges / fanout / rounds / panel-topology / retry); representing it as a `ComponentKind::Config`
  component with topology constraints; value-tuning vs. structural add/remove-node mutation; when and
  how to override `reflection_prompt_template`; validate-then-repair; mapping the spec onto a
  `weavegraph` / `rust-langgraph` builder.
- **`references/eval-gate.md`** — the class-5 graph eval gate: hard-fail structural invariants
  (reachability, no-orphan, no-loss/no-dup fanout-join, checkpoint/resume, interrupt round-trip, replay
  equivalence) run *before* scoring, then the soft task-success + latency + cost signals that feed the
  Pareto front; wiring `GEPAAdapter::evaluate` to compile→run→score a spec; adversarial-mutant
  generation for class 5; disjoint-write-scope and reward-hack defenses.
- **`references/loop-integration.md`** — running the loop: `OptimizeConfig` with `component_metadata`
  and a topology seed; the Temporal-workflow wrapping (GEPAState JSON, continue-as-new per K
  iterations); `SignalStopper` ↔ Temporal signal for HITL pause/stop; callbacks → `trace-store` /
  `experiment-tracker` lineage; promotion = flipping a spec-registry **label** (deploy a new topology
  with no code change); budget guard.
- **`references/worked-example.md`** — end-to-end: evolving a **judge/deliberation graph topology**
  (parallel-independent vs. R-round debate vs. 3-stage council) under a scored task — seed spec,
  `ComponentMeta::config` + constraints, the `GEPAAdapter` that compiles and runs each shape, what a
  concrete topology mutation looks like, and reading the `GEPAResult`.
