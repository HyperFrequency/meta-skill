# Self-calibration: the predicted-vs-realized ledger

A panel's verdicts are only as trustworthy as the judges in it — and judges drift, flatter,
and mis-scale. The **calibration ledger** is an append-only record that pairs each judge's
*prediction* with a later *realized outcome*, so the panel learns which judges to trust and how
to correct their systematic biases. This is the piece that makes judge-panel a *durable* primitive
rather than a one-shot vote.

## The ledger

The ledger records **predicted-vs-realized metric deltas** per judge — the same tracking
`tournament-autoresearch` uses to keep its proposers honest (a proposer/judge that *predicts* a
gain the *realized* metric never delivers is down-weighted). An append-only JSONL file (one row per
judge, per candidate, per call):

```jsonc
{
  "ts": "2026-07-02T10:00:00Z",
  "call_id": "c-8f3",
  "judge_id": "j-opus",
  "candidate_id": "cand-1",
  "predicted_score": 4.6,          // this judge's score on the rubric scale
  "predicted_decision": "PASS",
  "panel_decision": "PASS",        // what the whole panel decided (for herding analysis)
  "realized": null,                // filled in LATER when ground truth arrives
  "realized_source": null,         // "human" | "market_pnl" | "downstream_test" | "large_panel"
  "reconciled_ts": null
}
```

### What "realized" means (the outcome side)

The realized value is whatever independent signal eventually reveals whether the judgment was
right. Pick the strongest one available to the caller:

- **human label** — a reviewer's later verdict on the same candidate.
- **market / PnL** — for a scored trading strategy, the *out-of-sample realized* Sharpe/return
  (get it from `model-evaluation` / `strategy-verify`, don't recompute it here).
- **downstream test** — did the merged diff pass CI / the graded task succeed?
- **large-panel proxy** — a rare, expensive N=15 panel treated as ground truth for the cheap N=3.

Reconciliation is asynchronous: rows are written at judgment time with `realized: null`, then
updated in place (or via a paired `reconcile` row) when the outcome lands. A judge with zero
reconciled rows gets **cold-start defaults** (weight 1.0, offset 0.0).

## What the ledger buys you

Once a judge has ≥ `min_reconciled` (default 20) reconciled rows, compute per judge:

1. **Bias offset** `bᵢ` — mean signed error `mean(predicted - realized)`. A judge that runs
   +0.8 high gets 0.8 subtracted from its raw score before aggregation. Fixes systematic
   leniency/harshness *without* dropping the judge.
2. **Reliability weight** `wᵢ` — inverse of its error variance, normalized:
   `wᵢ ∝ 1 / (var(predicted - realized) + ε)`. Noisy judges shrink; sharp judges grow.
   Clamp to `[0.25, 3.0]` so no single judge can dominate or vanish.
3. **Agreement→accuracy map** — realized accuracy of the *panel* bucketed by `agreement`. This is
   what recalibrates `confidence` (aggregation.md): if agreement=0.7 historically corresponds to
   72% correct, report ~0.72, not the naive 0.85.
4. **Herding penalty** — how often a judge's Round-2 (debate) or its vote flips *toward* the panel
   yet is later realized *wrong*. High herding → down-weight in debate topology.

### The de-biasing update rule

Use an exponentially-weighted update so recent behavior dominates (judges/models change):

```
on each reconciliation for judge i with error e = predicted - realized:
    bᵢ   ← (1-α)·bᵢ   + α·e                      # bias offset, α ≈ 0.1
    vᵢ   ← (1-α)·vᵢ   + α·(e - bᵢ)²              # error variance
    wᵢ   ← clamp( 1 / (vᵢ + ε), 0.25, 3.0 )      # reliability weight
```

`apply_weights: true` in the request folds `bᵢ` and `wᵢ` into aggregation (offset subtracted from
raw score; `w_calibrated = wᵢ`). With `apply_weights: false` the ledger is *recorded but not
applied* — useful while a judge is still accumulating history.

## Guardrails

- **Cold start:** never apply weights from < `min_reconciled` rows — early noise would entrench a
  wrong prior. Default to equal weights until the threshold is met.
- **Circularity:** if `realized_source = "large_panel"` uses the *same* judges as the small panel,
  you are grading judges against themselves. Prefer human/market/test signals; when you must use a
  panel proxy, exclude the judge being scored from its own ground truth.
- **Regime change:** a model version bump invalidates that judge's history. Key ledger rows by
  `model` id; reset (or heavily discount) `bᵢ, vᵢ` when the id changes.
- **Never let calibration hide dissent.** Down-weighting is for *aggregation*; the raw vote and the
  offset applied are always in the audit trail.

## Align-Evals: closing the human-agreement loop

Re-weighting (`bᵢ, wᵢ`) corrects a judge's *numbers*. **Align-Evals** corrects its *judgment* by
folding human corrections back into the prompt and then **measuring whether the judge now agrees
with humans**. The loop:

1. **Collect corrections.** When a human overrides a verdict (or a reconciled `realized_source =
   "human"` row disagrees with the judge), capture the candidate, the judge's wrong call, and the
   human's correct call with its rationale.
2. **Promote to few-shot exemplars.** Splice the highest-signal corrections into the judge's system
   prompt as **in-context exemplars** ("here is a case like this and the correct scoring"). Keep the
   exemplar set small and de-duplicated; rotate stale ones out.
3. **Track judge/human agreement as its own metric.** Compute the judge's agreement with the human
   labels (Cohen's κ for categorical, correlation / MAE for scalar) on a **held-out** slice of
   labeled cases. This agreement is a *first-class, regression-gated* metric of the panel.
4. **Regression-gate prompt changes.** Any edit to a judge prompt (new exemplars, a `gepa`-evolved
   variant, a hand tweak) must be **rejected if it lowers held-out judge/human agreement** below the
   prior best minus a tolerance. This stops "improvements" that overfit the correction set and drift
   the judge away from human intent.

```
align_evals(judge, correction_pool, held_out):
    candidate_prompt = judge.prompt + few_shot(select_top(correction_pool))
    kappa_new = agreement(run(candidate_prompt, held_out), human_labels(held_out))
    if kappa_new >= judge.best_kappa - tolerance:
        judge.prompt = candidate_prompt;  judge.best_kappa = max(kappa_new, judge.best_kappa)
    else:
        reject(candidate_prompt)   # regression — keep the old prompt, log the drop
```

Enable via `calibration.align_evals: { correction_pool, held_out, tolerance }` in the request. The
ledger supplies the corrections and the realized labels; Align-Evals turns them into prompt
exemplars *and* the agreement gate that keeps prompt evolution honest.

## Optional: evolving judge prompts with `gepa` (MIT)

The ledger gives a *reward signal* (realized accuracy per judge). The user's MIT **`gepa`** crate
(`gepa` on crates.io — Genetic-Pareto reflective **prompt** optimization) can consume that signal to
*evolve the judge system prompts themselves*, not just re-weight them:

- Treat each judge's scoring prompt as a **GEPA candidate**.
- Implement a `GEPAAdapter` whose `evaluate` runs the judge over a held-out slice of reconciled
  ledger rows and returns the judge's realized accuracy (and a reflective trace of its mistakes) as
  the score.
- Run `optimize(...)`; GEPA's reflective mutation + Pareto-front selection breeds prompts that
  correlate better with realized outcomes — typically with far fewer rollouts than RL-style tuning.

This is *optional and heavy*: only reach for it when re-weighting (`bᵢ, wᵢ`) has plateaued and a
judge's prompt itself is the bottleneck. The ledger is the primitive; `gepa` is an upgrade path.
Keep the `gepa` dependency behind a feature flag so the panel runs without it.
