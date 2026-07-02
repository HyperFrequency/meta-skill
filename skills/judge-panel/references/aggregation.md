# Aggregation

Aggregation turns `JudgeVote[]` into one `Verdict`. Choose the aggregator that matches the
*decision type* (categorical vs scalar vs ranking) and the *noise profile* of your judges.

## Scalar aggregators

| Aggregator | Rule | Best when | Breaks when |
|---|---|---|---|
| **mean** | Weighted arithmetic mean of judge scores. | Rubric is well-calibrated, no rogue judges, you want smooth sensitivity. | One outlier judge drags the whole score. |
| **median** | Middle score (average the two middles if N even). | **Default for scalars.** Robust to a single outlier. | Loses information when judges genuinely bimodal. |
| **trimmed** | Drop top `k` and bottom `k`, mean the rest. Requires N ≥ 2k+1. | N ≥ 5 with one known-flaky judge. | Small panels (N=3 → trimmed = median). |

Weighted forms use the **effective weight** `w = w_caller * w_calibrated` (calibration weights
default to 1.0 when no ledger is attached). Normalize weights to sum to 1 before combining.

```
weighted_mean   = Σ wᵢ·scoreᵢ
weighted_median = value where cumulative weight crosses 0.5 (interpolate for even split)
trimmed_mean    = mean of scores after removing the k highest- and k lowest-weighted extremes
```

## Categorical aggregator

| Aggregator | Rule | Notes |
|---|---|---|
| **majority** | Modal `decision` across judges (weighted vote count). | Use an **odd** panel so PASS/FAIL cannot tie. Ties (from abstentions or even weights) → `ABSTAIN` and escalate, never silently pick one side. |

For gates: `decision = PASS` iff weighted PASS votes > weighted FAIL votes. If a `pass_threshold`
is set and the aggregator is scalar, `PASS = aggregated_score >= pass_threshold`.

## Ranking aggregators (cross_ranking topology)

Judges emit rankings, not scalars. Combine with one of:

- **Borda count** — each candidate gets points for its position in each judge's ranking; sum,
  highest wins. Simple, smooth, good default.
- **Copeland** — count pairwise wins across all judges; the candidate that beats the most others
  wins. Closer to a Condorcet winner; better when you care about head-to-head robustness.
- **Median rank** — take each candidate's median position across judges; lowest median wins.
  Most robust to one judge with an eccentric ordering.

The winner is `decision`; the full ordering is returned as `ranked[]`. Break ties by (1) higher
mean per-criterion score, then (2) lower rank variance (more agreement), then (3) coin flip on
`seed` — and *record* which tiebreaker fired.

## Confidence

`confidence` is **not** the mean of judge self-reported confidences (judges are overconfident).
Derive it from **agreement**, then fold in calibration:

```
agreement (scalars) = 1 - normalized_variance(scores)            # 0 = total disagreement, 1 = identical
agreement (ranks)   = Krippendorff's alpha over the rankings     # or mean pairwise Kendall tau
confidence = clamp( 0.5 + 0.5 * agreement , 0.5 , 0.99 )         # a split panel is never confident
```

Then adjust with the ledger (self-calibration.md): if the panel's *historical* realized accuracy
at this agreement level is lower than `confidence`, shrink toward the realized rate. **Cap at 0.99**
(invariant #5) — and never below 0.5 for a decided verdict, because 0.5 means "no information."

Also fold the judges' own confidences in only as a *tie-breaker* between equally-agreeing panels,
never as the primary signal.

## Dissent is a first-class output

Always populate `dissent[]` with the judges whose `decision` differs from the panel's, plus their
one-line reason. Downstream callers (and the ledger) use dissent to decide whether to escalate to a
human, a larger panel, or a debate round. **Suppressed dissent is how bad panels hide being wrong.**

## Picking an aggregator

```
Categorical verdict (PASS/FAIL, winner)         -> majority (odd N; ties -> abstain)
Scalar score, judges trustworthy                -> median  (default), or mean if you want smoothness
Scalar score, N>=5 with a flaky judge           -> trimmed (k=1)
Ranking K candidates                            -> Borda (default) / Copeland (head-to-head) / median-rank (robust)
```

## Interaction with calibration

When `calibration.apply_weights` is true, aggregation uses learned per-judge weights and subtracts
each judge's learned **bias offset** from its raw score *before* combining. This is what lets a
chronically-lenient judge stay on the panel without inflating verdicts. Details and the update rule:
[self-calibration.md](self-calibration.md).
