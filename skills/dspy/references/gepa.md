# GEPA in DSPy (Reflective Prompt Evolution)

`dspy.GEPA` is a teleprompter that **evolves the instruction text of the
predictors inside a DSPy program** using reflection instead of blind search. It
plugs into the same `optimizer.compile(student, trainset=..., valset=...)`
workflow as `BootstrapFewShot`, `MIPRO`, and `COPRO` — but the search operator is
an LM that *reads the failures and rewrites the instruction*, and surviving
candidates are kept on a **per-validation-instance Pareto front** rather than by a
single average score.

Paper: "GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning"
(arXiv 2507.19457). The headline claim is sample efficiency — competitive with or
beating RL/GRPO while using far fewer rollouts — because reflection extracts a
learning signal from each failure instead of only a scalar reward.

## GEPA vs. gepa-evolve — read this first

There are **two GEPAs** in this ecosystem. Pick the right one:

| | Optimizes | Interface | Use when |
|---|---|---|---|
| **`dspy.GEPA`** (this doc) | Instruction text of predictors *inside a DSPy `Module`* | Python `optimizer.compile(program, trainset, valset)` | Your program is already written in DSPy (Signatures + Modules) |
| **`gepa-evolve` skill** | Arbitrary named prompt components (`"instructions"`, `"solver"`, …) behind any eval | Rust `gepa` crate (gepars) / `ProcessAdapter` shelling out to an eval binary | Your prompt system is *not* DSPy — a raw prompt, a non-Python harness, or an eval that already lives behind a command |

Same algorithm family (reflective mutation + Pareto front + optional merge). The
difference is the substrate: **`dspy.GEPA` mutates predictors of a DSPy program;
the standalone GEPA engine (`gepa-evolve`) mutates free-standing prompt strings.**
If you are choosing between GEPA and MIPRO/COPRO for a DSPy program, stay here. If
you want GEPA without adopting DSPy, cross over to the **`gepa-evolve`** skill.

## When to reach for GEPA over MIPRO / COPRO

- You can write a metric that returns **textual feedback**, not just a number
  (e.g. "answer was not a valid integer", "leaked PII on turn 2"). GEPA's whole
  advantage is turning that feedback into a targeted instruction rewrite.
- The program has **multiple predictors** and you want each one's instruction
  improved from *its own* trace, not one global prompt tuned in aggregate.
- Rollout budget is tight — GEPA is designed to extract more signal per LM call.
- You want **diverse specialists** preserved (Pareto front) rather than collapsing
  to a single average-best prompt.

Prefer **MIPRO** when you want joint Bayesian search over *instructions and
few-shot demos* with a scalar metric; prefer **COPRO** for lightweight
coordinate-ascent instruction refinement. GEPA primarily evolves **instructions**
(it does not bootstrap demos the way `BootstrapFewShot` does) and depends on a
good feedback metric — with a bare binary metric it loses most of its edge.

## The feedback metric contract (the critical part)

GEPA calls a metric with an **extended signature** and expects a `dspy.Prediction`
carrying both a `score` and a `feedback` string:

```python
def metric_with_feedback(gold, pred, trace=None, pred_name=None, pred_trace=None):
    # gold      : the labeled dspy.Example
    # pred      : the dspy.Prediction from the program
    # trace     : full execution trace (all predictors)
    # pred_name : name of the predictor under mutation; None for the aggregate call
    # pred_trace: (predictor, inputs, outputs) tuples for just that predictor
    correct = int(gold.answer) == _safe_int(pred.answer)
    if pred_name is None:
        # module-level aggregate score
        return dspy.Prediction(score=float(correct), feedback="")
    # per-predictor feedback: say WHY, concretely, so the reflection LM can act on it
    fb = ("Correct." if correct
          else f"Wrong. Gold answer is {gold.answer}. "
               f"Your output '{pred.answer}' did not match; check the parsing step.")
    return dspy.Prediction(score=float(correct), feedback=fb)
```

Rules that matter:

- **Return a `dspy.Prediction(score=..., feedback=...)`**, not a bare float. The
  `feedback` string is injected verbatim into the reflection prompt.
- The metric is invoked **twice per example** — once at the module level
  (`pred_name is None`) for scoring the candidate, and once per predictor
  (`pred_name` set) to source the reflection text. Handle both cases.
- Make feedback **specific and actionable**: name the failing step, the expected
  value, the constraint that was violated. Vague feedback ("try harder") wastes
  the reflection call. Expose the *components* of a composite score so the LM
  knows which sub-objective to fix.
- Keep the metric deterministic and cheap; it runs on every rollout.

## Minimal usage

```python
import dspy
from dspy import GEPA

dspy.configure(lm=dspy.LM("anthropic/claude-opus-4-8"))

program = dspy.ChainOfThought("question -> answer")

optimizer = GEPA(
    metric=metric_with_feedback,
    auto="light",                       # budget preset: "light" | "medium" | "heavy"
    num_threads=16,
    track_stats=True,                   # attach detailed results to the output program
    reflection_minibatch_size=3,        # failures shown to the reflection LM per step
    reflection_lm=dspy.LM(              # a STRONG model at temperature 1.0
        "anthropic/claude-opus-4-8", temperature=1.0, max_tokens=32000,
    ),
)

optimized_program = optimizer.compile(
    program,
    trainset=train_examples,
    valset=val_examples,               # GEPA scores the Pareto front on this set
)
```

## Key parameters

- **Budget (exactly one)** — set **`auto="light"|"medium"|"heavy"`** for a preset,
  or an explicit cap via **`max_full_evals=N`** (N full passes over the valset) or
  the lower-level **`max_metric_calls=N`**. Start `light` to sanity-check the loop;
  the DSPy tutorials recommend `heavy` for production-quality results.
- **`reflection_lm`** — the model that reads failures and rewrites instructions.
  Use a **strong** model, `temperature=1.0`, and a large `max_tokens`; this is the
  single biggest quality lever. It can differ from the task/inference LM.
- **`reflection_minibatch_size`** — how many failing traces are distilled into the
  reflective dataset shown to the reflection LM each step (default ~3).
- **`candidate_selection_strategy`** — `"pareto"` (default; sample a base candidate
  from the instance-level Pareto front, preserving diversity) or `"current_best"`
  (greedy hill-climb on the best-so-far).
- **`use_merge`** — periodically combine two complementary Pareto candidates
  (System-Aware Merge). Turn **off** for single-predictor programs where merging
  has nothing to recombine.
- **`track_stats`** — attach the full run history to the returned program so you
  can inspect the frontier and lineage (see below).
- **`track_best_outputs`**, **`failure_score`**, **`seed`**, **`num_threads`** —
  record best per-instance outputs, the score assigned to hard failures/parse
  errors, RNG seed for reproducibility, and evaluation parallelism.

## The optimization loop (what actually happens)

1. **Score** the current candidate program on a minibatch, capturing full traces.
2. **Reflect** — distill the failing traces (inputs, generated outputs, feedback)
   into a reflective dataset and ask `reflection_lm` to rewrite the selected
   predictor's instruction to fix the observed errors.
3. **Accept/reject** — re-score the mutated candidate on the same minibatch; keep
   the child only if it improves.
4. **Track** — evaluate accepted children on the full `valset` and fold them into
   the **per-instance Pareto front** (best candidate *for each example* survives).
5. **Merge** (optional) — recombine complementary frontier candidates.
6. **Stop** when the budget (`auto` / `max_full_evals` / `max_metric_calls`) is hit;
   return the best candidate, re-instantiated as an optimized program.

## Inspecting results

```python
optimized_program.save("models/gepa_program.json")   # instructions are baked in

# With track_stats=True, the run history rides along on the returned program:
results = optimized_program.detailed_results
print(results.best_idx)                 # index of the winning candidate
print(results.val_aggregate_scores)     # valset score per discovered candidate
print(results.parents)                  # lineage (which candidate each descends from)
print(results.total_metric_calls)       # rollout accounting / sample efficiency
```

`detailed_results` exposes the discovered candidates, their validation scores,
the parent lineage, and the total metric-call budget consumed — use it to compare
GEPA's sample efficiency against MIPRO on the same task and to read the actual
evolved instruction text.

## Pitfalls

- **Binary metric, no feedback** — GEPA degenerates toward blind search. Always
  return a `feedback` string; if you only have a scalar, MIPRO is the better fit.
- **Weak reflection LM** — a small/cheap reflection model produces bland rewrites.
  Spend the tokens here, not on the inference LM.
- **Optimizing on the test set** — GEPA folds accepted candidates into the
  **`valset`** frontier; keep a separate untouched **`testset`** for the final
  `dspy.evaluate.Evaluate` so reported gains are honest.
- **Merge on a one-predictor program** — nothing to recombine; set
  `use_merge=False` to save budget.
- **Expecting few-shot demos** — GEPA evolves *instructions*. If you need
  bootstrapped demonstrations too, stack it with `BootstrapFewShot` or use MIPRO.

## Cross-links

- Sibling optimizers and metric design: `optimizers.md`.
- GEPA **outside** DSPy (raw prompt components, non-Python evals, `ProcessAdapter`
  over an eval binary, Rust `gepa`/gepars engine): the **`gepa-evolve`** skill.

## Resources

- Paper: "GEPA: Reflective Prompt Evolution Can Outperform Reinforcement Learning"
  (arXiv 2507.19457).
- DSPy GEPA overview: https://dspy.ai/api/optimizers/GEPA/
- GEPA in depth (metric anatomy, reflection): https://dspy.ai/api/optimizers/GEPA/GEPA_Advanced/
