# Topology as a Config component

The whole skill rests on one move: represent a **declarative workflow/graph topology** as a serialized
spec document, place it in a `gepa` `Candidate` as a single component, and mark that component
`ComponentKind::Config` so GEPA's config-aware reflective mutation rewrites the *structure* instead of
prose. This file is the concrete how.

## 1. What ComponentKind::Config actually buys you

From `gepars/src/core/component.rs`:

```rust
pub enum ComponentKind { Text, Code, Config }   // Text is #[default]

pub struct ComponentMeta {
    pub kind: ComponentKind,
    pub description: String,                     // shown to the reflection LM
    pub language: Option<String>,                // for Code
    pub constraints: Option<HashMap<String, String>>,  // for Config
}
impl ComponentMeta {
    pub fn config(description: impl Into<String>) -> Self { /* kind = Config */ }
    pub fn with_constraints(self, c: HashMap<String,String>) -> Self { /* … */ }
}
pub type ComponentMetaMap = HashMap<String, ComponentMeta>;   // name → meta
```

`OptimizeConfig` carries a `component_metadata: ComponentMetaMap` field (`gepars/src/api.rs`), default
empty (everything falls back to `Text`). Set the entry for your topology key and GEPA switches to
`CONFIG_META_PROMPT_TEMPLATE` (`gepars/src/strategies/instruction_proposal.rs`) for that component:

```text
I have a system configured with the following parameters:
```
<curr_param>            ← your current spec document
```
<constraints>           ← rendered from with_constraints(...)
The following are results from running with this configuration:
```
<side_info>             ← the reflective dataset (failures + metrics from your traces)
```
Your task is to propose an improved configuration.
Analyze the metrics carefully. Consider:
1. Which parameters most likely influence the observed metrics
2. Whether to make small incremental changes or larger exploratory jumps
3. The trade-offs between different objectives (if multiple metrics shown)
Provide the complete improved configuration within ``` blocks.
Change only the values, not the format or parameter names.
```

The last line is the pivot: this prompt is **value-tuning oriented**. It reliably mutates numeric and
enum fields (fanout width, rounds, thresholds, a stage's `kind`) but resists inventing new nodes. See
§4 for structural add/remove.

## 2. The workflow spec schema

Keep the spec a single, self-contained document so the reflection LM sees the whole shape at once and
so `<curr_param>` round-trips cleanly. A pragmatic JSON schema (mirror it in YAML if you prefer):

```json
{
  "entry": "start",
  "nodes": [
    {"id": "start",     "kind": "input"},
    {"id": "plan",      "kind": "llm",      "prompt_ref": "plan.v3"},
    {"id": "research",  "kind": "fanout",   "width": 3, "child_kind": "llm", "child_prompt_ref": "probe.v1"},
    {"id": "synthesize","kind": "llm",      "prompt_ref": "synth.v2"},
    {"id": "review",    "kind": "judge_panel", "topology": "debate", "rounds": 2, "judges": 3},
    {"id": "end",       "kind": "output"}
  ],
  "edges": [
    {"from": "start",      "to": "plan"},
    {"from": "plan",       "to": "research"},
    {"from": "research",   "to": "synthesize", "join": "concat"},
    {"from": "synthesize", "to": "review"}
  ],
  "conditional_edges": [
    {"from": "review", "on": "score>=0.7", "to": "end"},
    {"from": "review", "on": "score<0.7",  "to": "plan", "max_revisits": 2}
  ],
  "retry": {"default_attempts": 2, "backoff": "exponential"}
}
```

What is **mutable topology** (the point of this skill) vs. what is **not**:

| Field | Mutable here? | Notes |
|---|---|---|
| `edges`, `conditional_edges` (wiring, routing) | **yes** | the core of topology evolution |
| node `kind`, presence/absence of a node | **yes** (structural, §4) | add a validator, drop a redundant stage |
| `fanout.width`, `rounds`, `judges`, routing thresholds, `retry.*` | **yes** (value-tuning, §3) | the Config prompt handles these directly |
| `judge_panel.topology` enum | **yes** | swap parallel ↔ debate ↔ council |
| `prompt_ref` **contents** (the actual instruction text) | **no — use gepa-evolve** | evolve prompts in a separate loop |
| a node's executor **code** | **no — use alpha-evolve** | evolve code in a separate loop |

Keep `prompt_ref` a *reference* (a label into a prompt registry), never inline prose — that keeps the
topology loop from accidentally drifting into prompt editing and keeps the two loops composable.

## 3. Value-tuning mutation (the direct path)

For tuning structural *values* on a fixed node/edge set, the built-in config prompt is enough. Encode
the envelope in `constraints` so the LM stays legal:

```rust
use std::collections::HashMap;
use gepa::{ComponentMeta, ComponentMetaMap};

let mut meta = ComponentMetaMap::new();
meta.insert("topology".into(), ComponentMeta::config(
    "Agent research graph. JSON with nodes/edges/conditional_edges. \
     You may retune structural values but must return a valid, fully-connected graph."
).with_constraints(HashMap::from([
    ("research.width".into(),  "integer, 1-6".into()),
    ("review.rounds".into(),   "integer, 1-4".into()),
    ("review.judges".into(),   "odd integer, 1-5".into()),
    ("review.topology".into(), "one of: parallel | debate | council | hierarchical".into()),
    ("retry.default_attempts".into(), "integer, 0-3".into()),
    ("_invariant".into(),      "graph must remain reachable start->end with no orphan nodes".into()),
])));
// cfg.component_metadata = meta;
```

`constraints` render into `<constraints>` in the prompt, so the LM sees the legal ranges and the
reachability invariant every iteration. This alone gives you a strong fanout/rounds/routing/topology-
enum optimizer.

## 4. Structural add/remove mutation (custom reflection template)

To let the loop **add or delete nodes and edges** (true structural search), the "change only the
values" instruction works against you. Two supported approaches:

**(a) Override the reflection template.** `OptimizeConfig.reflection_prompt_template:
Option<PromptTemplateConfig>` (`gepars/src/api.rs`) replaces the built-in template for the mutated
component. Supply a topology-structural template that keeps the config framing (it still gets
`<curr_param>` / `<constraints>` / `<side_info>`) but explicitly authorizes structural edits:

```text
You are editing an agent-graph SPEC (JSON: nodes, edges, conditional_edges).
The results below show where the current graph structure underperforms.
You MAY add, remove, rename, or rewire nodes and edges — this is a STRUCTURAL edit,
not just value tuning. You MUST honor every constraint and return a graph that is
fully connected from `entry` to an output node with no orphan or dangling references.
Prefer the smallest structural change that addresses the failures.
Return the complete new spec within ``` blocks.
```

**(b) ProcessAdapter with a repair step.** Point `gepa`'s `ProcessAdapter` at an external binary that
(i) receives the proposed spec, (ii) runs a **validate-then-repair** pass (drop dangling edges, prune
orphan nodes, clamp out-of-range values, reject cycles if DAG-only), (iii) compiles and scores it, and
(iv) returns the metric. Repair keeps a *slightly* malformed-but-fixable mutant alive at reduced score
instead of wasting the metric call — but never repair a spec that violates a **hard invariant** (that
scores `0.0`; see `eval-gate.md`).

Either way: **compile is the source of truth.** The reflection LM's output is a proposal; the validator
+ compiler decides whether it is a real candidate.

## 5. Mapping the spec onto a real graph engine

The spec compiles into a first-party graph (design donors: `weavegraph`, `rust-langgraph`,
`state-graph-rs`, `metalcraft`). Both donors expose the same declarative shape the spec mirrors:

- **weavegraph** (`~/neuro-centrifuge-repos/weavegraph`): `App::builder().add_node(NodeKind::Custom(id),
  node).add_edge(NodeKind::Start, …).add_conditional_edge(ConditionalEdge{…})`, with channels/reducers
  for fanout-join, checkpointers, and deterministic replay. `NodeKind::{Start, End, Custom}` and
  `ConditionalEdge` map 1:1 onto the spec's `nodes` / `conditional_edges`.
- **rust-langgraph** (`~/neuro-centrifuge-repos/rust-langgraph`): `StateGraph::new()` +
  `add_node(name, async closure)` → `CompiledGraph`.

Your compiler is a pure function `spec → CompiledGraph`. Because it is pure and deterministic, the same
spec always yields the same graph, which is what makes the eval gate's replay-equivalence check
meaningful (see `eval-gate.md`). Node executors (LLM calls, tools) are looked up by `kind` + `*_ref`
from the harness registries — the topology loop never synthesizes executor code.

## 6. Determinism & round-trip discipline

- The spec must **round-trip**: `parse(serialize(spec)) == spec`. A lossy serialization makes the
  Pareto lineage (`parents`) meaningless and can make `best_candidate()` un-recompilable.
- Canonicalize before hashing (stable key order, no incidental whitespace) so `experiment-tracker`
  config-snapshot hashes identify identical topologies — this is what lets you *re-run any topology
  under its exact spec* (spec §a.1 config-snapshot pattern) and dedupe the archive.
- Keep node `id`s stable across mutations where possible; renaming a node breaks lineage diffing and the
  reflective dataset's ability to attribute failures to a specific stage.
