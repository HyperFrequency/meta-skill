# Optional: auto-fix a failing skill with `gepa`

This is **opt-in and off the critical path.** The runner's job is to *score and
gate*; fixing a skill is normally skill-creator's job. But when a skill fails on
a text-shaped dimension — usually a weak `description` (FORMAT WHEN/WHEN-NOT) or
thin FRONTIER-MODEL GUIDELINES — you can close the loop automatically by treating
the rubric score as a fitness signal and evolving the text.

Use the user's own **`gepa`** crate for this: a Rust implementation of
Genetic-Pareto reflective prompt optimization
(`/Users/DanBot/neuro-centrifuge-repos/gepars`, crate name `gepa`, **MIT** — free
to wrap). It evolves candidates via LLM-guided reflective mutation and
Pareto-front selection.

> Scope guard: gepa is well-suited to optimizing a *single bounded string* (the
> `description`, or one over-long section). Do **not** point it at a whole SKILL.md
> rewrite — depth, completeness, and factual accuracy are not things a prompt
> optimizer should hallucinate. Optimize the trigger text; leave the substance to
> a human or skill-creator.

## Verified API surface (gepa 0.1)

From the crate's `examples/minimal.rs` and `src/api.rs`:

- `pub async fn optimize<Id, Item, T, RO>(config: OptimizeConfig<Id, Item, T, RO>) -> Result<GEPAResult<Id>>`
- `trait GEPAAdapter<Id, Item, T>` with two async methods:
  - `evaluate(&self, batch, candidate: &Candidate, capture_traces) -> Result<EvaluationBatch<Item, T>>`
  - `make_reflective_dataset(&self, candidate, batch, components) -> Result<ReflectiveDataset>`
- `Candidate` is a component map; read a component with `candidate.get("description")`.
- `EvaluationBatch::new(outputs, scores)` — `scores: Vec<f64>`, higher is better.
- Config types: `OptimizeConfig`, `LMConfig`, `StopConditionConfig`, and
  `gepa::core::data_loader::VecLoader` for the dataset.

## Wiring the rubric as fitness

Implement one adapter whose `evaluate` scores a candidate **description** by
splicing it into the skill and running `scripts/eval_skill.py`, then mapping the
scorecard to a scalar. Sketch (compile against the real signatures above):

```rust
use async_trait::async_trait;
use gepa::core::adapter::{Candidate, EvaluationBatch, GEPAAdapter, ReflectiveDataset};

struct RubricAdapter { skill_dir: std::path::PathBuf }

#[async_trait]
impl GEPAAdapter<String, (), String> for RubricAdapter {
    async fn evaluate(
        &self,
        batch: &[String],
        candidate: &Candidate,
        _capture_traces: bool,
    ) -> gepa::Result<EvaluationBatch<(), String>> {
        let description = candidate.get("description").map_or("", String::as_str);

        // 1. Write a temp copy of the skill with this candidate description.
        // 2. Shell out: python3 scripts/eval_skill.py <tmp> --out card.json
        //    (deterministic FORMAT + router size only — no model in this loop).
        // 3. Parse card.json; turn it into a scalar fitness, e.g.:
        //      fitness = format_score
        //              + (1.0 if description states WHAT+WHEN+WHEN-NOT else 0.0)
        //              - penalty(description_length)   // discourage nearing 1024
        let (scores, outputs) = score_candidates(&self.skill_dir, description, batch);
        Ok(EvaluationBatch::new(outputs, scores))
    }

    async fn make_reflective_dataset(
        &self,
        _candidate: &Candidate,
        batch: &EvaluationBatch<(), String>,
        _components: &[String],
    ) -> gepa::Result<ReflectiveDataset> {
        // Feed the FORMAT failure notes back as reflection text so gepa's
        // mutation proposer knows *why* a candidate scored low.
        Ok(ReflectiveDataset::new())
    }
}
```

Then run `optimize` with an `OptimizeConfig` carrying an `LMConfig` (any
OpenAI-compatible endpoint), a `StopConditionConfig` (bound the rollout budget —
gepa's headline result is doing this in far fewer rollouts than RL), and a
`VecLoader` over a handful of held-out trigger prompts. `GEPAResult` gives you the
best candidate description; splice it back, then re-run the **full** hybrid runner
(including the human/model judge pass) to confirm the real PASS.

## The loop, honestly

1. `eval_skill.py` fails a skill on FORMAT WHEN/WHEN-NOT or you judge
   FRONTIER-MODEL GUIDELINES < 4 for a weak trigger.
2. Run the gepa loop on the `description` only. Fitness = the deterministic
   FORMAT score (+ a WHAT/WHEN/WHEN-NOT bonus, − a length penalty).
3. Splice the winning description back into the SKILL.md.
4. **Re-run the whole runner, judge pass included.** gepa optimizes only the auto-
   checkable signal; a human/model judge still has to confirm DEPTH,
   COMPLETENESS, and that the new description isn't misleading.
5. If it now PASSES, update the baseline (`references/regression-gate.md`).

Deterministic fitness cannot see accuracy or completeness, so **never ship a
gepa-evolved description without the judge pass.** This loop tightens triggers; it
does not author substance.

## License note

`gepa` is MIT — wrap it freely. Everything in *this* skill is original; it shells
out to gepa as an external tool and copies no gepa source. Do not, in the course
of an autofix, pull text or code from any noncommercial (`gitnexus*`), BUSL
(`copula-dependency`), AGPL (`meta_skill` internals), or Anthropic-proprietary
source into the skill under repair.
