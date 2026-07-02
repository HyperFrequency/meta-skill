---
name: gepa-evolve
description: >
  Evolve a PROMPT (instruction text) against a scored metric using GEPA — reflective, LLM-guided
  mutation plus multi-objective Pareto-front selection — via the user's Rust `gepa` crate at
  ~/neuro-centrifuge-repos/gepars. Use when optimizing one or more named prompt components against an
  evaluation you can score, when you want the paper's sample-efficient alternative to RL/GRPO (~35x
  fewer rollouts), when several objectives must be traded off on a Pareto front, or when reflection
  over failure cases should drive the edits. Also use to wire GEPA to an external eval binary via
  ProcessAdapter. NOT for evolving PROGRAM/model CODE over a MAP-Elites archive (use alpha-evolve),
  NOT for single-metric hill-climbing with one edit per round and no Pareto/reflection (use
  prompt-optimize), NOT for tuning model weights or hyperparameters, and NOT for authoring a prompt
  from scratch with no metric to score against.
metadata:
  version: "0.1.0"
---

# GEPA-Evolve

> **G**enetic-**E**volutionary **P**areto **A**daptation of prompts. Paper: "GEPA: Reflective Prompt
> Evolution Can Outperform Reinforcement Learning" — https://arxiv.org/pdf/2507.19457 (ICLR 2026 Oral).
> Wraps the user's Rust crate `gepa` (MIT, nicholasjpaterno/gepa) at
> `~/neuro-centrifuge-repos/gepars`. The crate is a **library** (no CLI binary) — you drive it by
> writing a small Rust harness or by pointing its `ProcessAdapter` at an external eval command.

GEPA evolves the **text of one or more prompt components** (`"instructions"`, `"parser"`,
`"solver"`, …) toward a higher score. Each iteration: sample a base candidate from the **per-instance
Pareto front**, run it on a **minibatch**, ask a **reflection LM** to read the failure cases and
propose a rewritten instruction (Algorithm 3), then **accept** the mutation only if it improves the
minibatch score. Periodically it **merges** complementary Pareto candidates (Algorithm 4). The
frontier keeps whichever candidate is best *on each validation example*, so diverse specialists
survive instead of collapsing to one average-best prompt — this is what makes it beat GRPO with up to
**35x fewer rollouts**.

## When to use

Use when the user has a prompt (or a multi-component prompt system) and an evaluation that returns a
numeric score, and wants the prompt automatically improved. Strong fits: reflection over concrete
failures should steer edits; multiple objectives (accuracy vs. brevity vs. safety) must be traded off
on a Pareto front; the rollout budget is tight; the eval already lives behind a binary you can shell
out to.

**Pick the right sibling — do not use gepa-evolve for these:**

| You want to evolve… | Signal | Skill |
|---|---|---|
| **Prompt text**, reflection-driven, **Pareto** over instances/objectives, budget-controlled | "outperform RL", "Pareto front", "reflective mutation", multi-component prompt | **gepa-evolve** (this) |
| **A prompt**, single scalar metric, **one edit per round, keep-if-better** (no Pareto, no reflection LM) | "hill-climb my prompt against my eval command" | `neuro-code/prompt-optimize` |
| **Program / model CODE** as SEARCH/REPLACE diffs kept in a **MAP-Elites archive** across islands | "evolve my model", "AlphaEvolve", "diversity archive" | `neuro-code/alpha-evolve` |

If the artifact being edited is *code that runs*, it is alpha-evolve. If it is *instruction text scored
by one number with no frontier*, it is prompt-optimize. GEPA is the middle: **prompt text, but with
reflection + a Pareto frontier + merge.**

## The core loop (what actually happens)

1. **Seed** — a `Candidate` (`IndexMap<String, String>`): component name → starting text.
2. **Select** — pick a base candidate (`Pareto` / `CurrentBest` / `EpsilonGreedy`).
3. **Sample** — draw a `minibatch_size` minibatch from the trainset.
4. **Evaluate** — your `GEPAAdapter::evaluate` runs the candidate, returns `outputs`, `scores`, and
   (when asked) `trajectories`.
5. **Reflect** — `make_reflective_dataset` distills failures into `{Inputs, Generated Outputs,
   Feedback}` records; the reflection LM rewrites the selected component(s).
6. **Accept/reject** — re-evaluate on the same minibatch; keep the child only if its summed score rises.
7. **Track** — accepted children are scored on the full valset and folded into the Pareto front.
8. **Merge** (optional) — combine complementary Pareto candidates (Algorithm 4).
9. **Stop** — when `max_metric_calls`, `max_iterations`, or `timeout` fires (whichever is first).

Output is a `GEPAResult`: `best_candidate()`, `best_idx()`, per-candidate `val_aggregate_scores`,
lineage `parents`, the instance frontier, and `total_metric_calls`. It round-trips through JSON.

## Fastest path — run an example first

The crate ships runnable examples that need **no API key** (mock adapters). Run one before writing your
own harness so you see the loop and the `GEPAResult` shape:

```bash
cd ~/neuro-centrifuge-repos/gepars
cargo run --example minimal          # 1 component, keyword-overlap scorer
cargo run --example custom_adapter   # multi-component prompt
cargo run --example merge_demo       # Algorithm-4 system-aware merge
cargo run --example quickstart       # QA task; add `-- --live` + OPENAI_API_KEY for a real LM
```

Reflection only calls the LM when `make_reflective_dataset` returns non-empty records, so mock runs
stay fully offline even with an unreachable `base_url`.

## Minimal integration (the shape you write)

```rust
use std::sync::Arc;
use async_trait::async_trait;
use gepa::core::data_loader::VecLoader;
use gepa::{optimize, Candidate, EvaluationBatch, GEPAAdapter, ReflectiveDataset,
           LMConfig, OptimizeConfig, StopConditionConfig, Result};

struct MyAdapter;   // implements evaluate + make_reflective_dataset — see references/adapter-guide.md

#[tokio::main]
async fn main() -> std::result::Result<(), Box<dyn std::error::Error>> {
    let mut seed = Candidate::new();
    seed.insert("instructions".into(), "Answer the question.".into());

    let mut cfg = OptimizeConfig::new(
        seed,
        Arc::new(VecLoader::new(train)),          // trainset
        Arc::new(VecLoader::new(val)),            // valset — Pareto tracking runs here
        Arc::new(MyAdapter),
        LMConfig { model: "gpt-4o-mini".into(),
                   api_key: std::env::var("OPENAI_API_KEY").unwrap_or_default(),
                   base_url: "https://api.openai.com".into(), ..LMConfig::default() },
    );
    cfg.stop_condition = StopConditionConfig { max_metric_calls: Some(200), ..Default::default() };

    let result = optimize(cfg).await?;
    println!("best: {:?}", result.best_candidate()?);
    Ok(())
}
```

Add the dep: `gepa = "0.1"` (or `gepa = { path = "…/gepars" }`), plus `tokio`, `async-trait`.

## Boundaries & failure modes (read before trusting a run)

- **Valset is the metric that counts.** Pareto tracking and `best_candidate()` come from the *valset*,
  not the trainset. A tiny/unrepresentative valset gives a misleadingly "best" prompt.
- **Budget is per-example metric calls, not iterations.** Default `max_metric_calls = 500`; cached
  examples don't consume budget. A big minibatch or valset burns the budget in few iterations.
- **Adapter errors ≠ example failures.** Return a `0.0` score for a bad example; reserve `Err` for
  systemic failures (network down). Returning `Err` per example aborts the whole run. See the contract
  in `references/adapter-guide.md`.
- **Multi-objective needs `objective_scores`.** `FrontierType::Objective/Hybrid/Cartesian` require your
  adapter to populate `EvaluationBatch::objective_scores`, or the engine errors at startup.
- **Reflection LM cost is real.** Every accepted-mutation iteration calls the LM with `max_tokens`
  (default 4096) at `temperature` 1.0. Point `base_url` at a local Ollama/vLLM server to run free.
- **`unsafe_code = "forbid"`, no unsafe, no CLI.** This is a library; there is nothing to `gepa run`.
  Wrap it in Rust or via `ProcessAdapter`.

## Reference material (load what the task needs)

- **`references/algorithm.md`** — GEPA concepts, how reflective mutation + per-instance Pareto beat
  GRPO, the paper→code mapping (Algorithms 2/3/4), when the ~35x rollout saving holds.
- **`references/adapter-guide.md`** — writing `GEPAAdapter` (`evaluate`, `make_reflective_dataset`),
  the reflective-dataset record schema, `capture_traces` / trajectory contract, error-handling
  contract, component metadata (`ComponentMeta::text/code/config`), and the built-in **`ProcessAdapter`**
  for evaluating via an external binary (env-var / JSON-file passing, metric parsing, score direction).
- **`references/config-reference.md`** — every `OptimizeConfig`, `LMConfig`, and `StopConditionConfig`
  field with defaults; selectors (`CandidateSelectorKind`, `ComponentSelectorKind`), `FrontierType`,
  merge knobs, caching, callbacks/`GEPACallback` events, `GEPAResult` accessors, error variants,
  supported LLM providers, and testing commands.
- **`references/tuning-playbook.md`** — recipes: single vs. multi-component, offline mock-first
  bring-up, budget/minibatch sizing, enabling merge, multi-objective setup, epsilon-greedy vs. Pareto,
  local-LLM wiring, and diagnosing "no candidate beats the seed".
