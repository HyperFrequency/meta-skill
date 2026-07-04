# Worked example: evolving a deliberation graph's topology

A concrete end-to-end run. The task: a QA-with-review workflow must answer hard questions accurately
under a token budget. We fix the prompts and executors and evolve only the **topology of the review
stage** — is a single parallel judge vote enough, or does the task need debate rounds or a full
council? We let workflow-evolution discover the shape.

This is deliberately the judge/deliberation case because it is the clearest instance of a decision that
lives in *topology*, not in prompt text: `parallel-independent` vs. `R-round debate` vs.
`3-stage council` are the exact same judges wired three different ways (spec §b Loop 2 topologies).

## Seed spec

```json
{
  "entry": "start",
  "nodes": [
    {"id": "start",  "kind": "input"},
    {"id": "answer", "kind": "llm",         "prompt_ref": "answer.v1"},
    {"id": "review", "kind": "judge_panel", "topology": "parallel", "judges": 3, "rounds": 1},
    {"id": "end",    "kind": "output"}
  ],
  "edges": [
    {"from": "start",  "to": "answer"},
    {"from": "answer", "to": "review"}
  ],
  "conditional_edges": [
    {"from": "review", "on": "verdict>=0.7", "to": "end"},
    {"from": "review", "on": "verdict<0.7",  "to": "answer", "max_revisits": 2}
  ],
  "retry": {"default_attempts": 1}
}
```

## Metadata & constraints

```rust
meta.insert("topology".into(),
    ComponentMeta::config(
        "QA-with-review graph. The `review` stage decides whether the answer is good enough; \
         you may change its topology, judge count, rounds, and the revisit routing. \
         `answer`/`start`/`end` are required and must stay reachable.")
    .with_constraints(HashMap::from([
        ("review.topology".into(), "one of: parallel | debate | council | hierarchical".into()),
        ("review.judges".into(),   "odd integer, 1-5".into()),
        ("review.rounds".into(),   "integer, 1-4 (only meaningful for debate)".into()),
        ("review.max_revisits".into(), "integer, 0-3".into()),
        ("_required_nodes".into(), "start, answer, review, end must all be present".into()),
        ("_invariant".into(),      "reachable start->end, no orphans, bounded revisits".into()),
    ])));
```

`_required_nodes` is the reward-hack fence: a mutant that deletes `review` to save tokens fails the hard
gate (see `eval-gate.md`).

## The adapter (compile → run → score)

```rust
#[async_trait]
impl GEPAAdapter<Task, Trace, Answer> for TopologyAdapter {
    async fn evaluate(&self, batch: &[Task], cand: &Candidate, capture: bool)
        -> Result<EvaluationBatch<Trace, Answer>>
    {
        let spec: GraphSpec = match serde_json::from_str(&cand["topology"]) {
            Ok(s) => s,
            Err(e) => return Ok(EvaluationBatch::all_zero(batch.len(),
                        format!("spec did not parse: {e}"))),   // 0.0, not Err
        };
        // HARD GATE
        if let Err(why) = structural_invariants(&spec) {
            return Ok(EvaluationBatch::all_zero(batch.len(), why));
        }
        let graph = self.compiler.compile(&spec)?;              // weavegraph-style builder
        let mut scores = Vec::new();
        let mut traces = Vec::new();
        for task in batch {
            let run = graph.run(task, RunBounds{ max_steps: 12, timeout_s: 60 }).await?;
            let acc  = self.scorer.task_success(&run.answer, task);   // judge-panel or exact-match
            let cost = run.tokens as f64 / 10_000.0;
            scores.push(0.8 * acc - 0.2 * cost.min(1.0));            // task dominates; cost bounded
            if capture { traces.push(run.trace); }                  // for the reflective dataset
        }
        Ok(EvaluationBatch { outputs: /*answers*/, scores, trajectories: traces })
    }

    fn make_reflective_dataset(&self, cand: &Candidate, batch: &EvaluationBatch<Trace, Answer>,
                               components: &[String]) -> Result<ReflectiveDataset> {
        // Emit structural feedback: rounds that didn't move the verdict, revisits that still failed,
        // judge disagreement that a bigger panel would have resolved, redundant parallel votes.
        // -> becomes <side_info> in the CONFIG meta-prompt.
    }
}
```

## What a mutation looks like

Iteration 3 reflective dataset (paraphrased `<side_info>`): *"On 4/5 hard questions the 3 parallel
judges split 2-1 and the answer was wrong; the single round gave no chance to resolve the disagreement.
On the 1 easy question all 3 agreed immediately."* The config reflection prompt proposes:

```diff
-  {"id": "review", "kind": "judge_panel", "topology": "parallel", "judges": 3, "rounds": 1},
+  {"id": "review", "kind": "judge_panel", "topology": "debate",   "judges": 3, "rounds": 2},
```

A **pure topology edit** — same three judges, rewired from independent-parallel into a 2-round debate so
they read each other and update. It re-evaluates on the minibatch; if the summed score rises it is
accepted and folded into the Pareto front. A later iteration might try `council` (adds an anonymized
cross-rank + chairman synthesis stage) and the frontier keeps whichever shape wins *per instance* — so
`parallel` may survive for easy questions while `debate`/`council` win the hard ones. That per-instance
survival is the Pareto behavior workflow-evolution inherits from GEPA.

## Reading the result

```rust
let result = optimize(cfg).await?;
println!("best topology:\n{}", result.best_candidate()?["topology"]);
println!("val scores per candidate: {:?}", result.val_aggregate_scores);
println!("lineage (parents): {:?}", result.parents);
println!("metric calls used: {}", result.total_metric_calls);
```

Promote the winner by pointing the `review`-graph registry's `prod` label at `best_candidate()`'s spec
(no code change; see `loop-integration.md` §4), gated on the class-5 eval beating the pinned baseline
with n≥3 trials. Then, as a *separate* pass, hand `answer.v1` to `gepa-evolve` to improve the prompt
text now that the review shape is fixed.

## Offline bring-up

Before spending LM/graph-run budget, dry-run the plumbing with a **mock scorer** (a deterministic
`task_success` that rewards, say, "debate on hard tasks") and a fake graph runner, exactly as
gepa-evolve's mock examples do. Confirm: specs parse and compile, the hard gate rejects a hand-broken
spec as `0.0` (not `Err`), an accepted mutation shows up in `parents`, and `best_candidate()`
recompiles. Only then wire the real compiler, judges, and reflection LM.
