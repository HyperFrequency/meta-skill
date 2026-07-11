# Honest Disclosure and Reporting

A benchmark result is only as credible as what you disclose around it. Present
it so that a skeptical reviewer can see the seeds, the splits, the confounders,
and the failure cases — and reach your conclusion themselves.

## Results table template

```markdown
## Results

| Test | Our metric        | Published | Improvement | Seeds | Val split      |
| ---- | ----------------- | --------- | ----------- | ----- | -------------- |
| A    | X.Xe-Y ± Z.Ze-Y   | P.Pe-Q    | N.N×        | 3     | Yes (8K/1K/1K) |

### Comparison fairness notes
- Our model differs from the baseline in: [more modes / higher resolution /
  more training data / larger parameter count / longer training budget].
- Every such confounder is listed in Table X.
- The ablation in Table Y isolates the contribution of each change, so the
  headline improvement is not attributable to a confound alone.

### Limitations
- [List every known weakness honestly — regimes where the model degrades,
  assumptions it depends on, cases it does not cover.]
```

The `± Z.Ze-Y` is not optional: give mean ± std over ≥3 seeds for any headline
number. If two methods' intervals overlap, say so rather than declaring a winner.

## What every reported number must carry

- **Seeds**: how many, and the summary as mean ± std (not a single lucky run).
- **Split**: sizes and roles (train/val/test), and the split seed, so it is
  reconstructable.
- **Metric variant**: exactly which formula produced the number (see
  `metrics-and-formulas.md`) — and both variants if the correct one was
  ambiguous.
- **Confounders**: every way your setup differs from the baseline's, with an
  ablation that isolates the real contribution.
- **Provenance of the baseline**: source paper, arXiv id, table/figure, and
  configuration (see `verify-baselines.md`).
- **The worst case**: show the failure sample, not only the best epoch or the
  cherry-picked example.

Persist these fields in a machine-readable `results.json` next to the paper so
the exact evaluation is recoverable — the split seed, per-seed scores, the metric
variant string, and the baseline provenance.

## Common Pitfalls

| Pitfall                              | Why it is wrong                 | Fix                                       |
| ------------------------------------ | ------------------------------- | ----------------------------------------- |
| Model selection on the test set      | Optimistic bias, ~1-10%          | Use a validation split; touch test once   |
| Single-seed result                   | Could be luck                    | Report ≥3 seeds with std                  |
| Trusting a secondary baseline number | Frequently wrong                 | Parse the original paper / benchmark code |
| Comparing across metric variants     | RMSE ≠ nRMSE ≠ MSE; A ≠ B ≠ C    | Reproduce the benchmark's exact formula   |
| Not disclosing confounding factors   | Unfair, unattributable gain      | Table of ALL differences + ablation       |
| Cherry-picking the best epoch        | Not reproducible                 | Use final-epoch OR val-selected only      |
| Hiding failure cases                 | Dishonest                        | Show the worst-case sample explicitly     |
| Looser protocol than the baseline    | Comparison is not fair           | Match or exceed the baseline's rigor      |

## The bar to clear before publishing a claim

Ask, for each row of your results table: is my protocol at least as strict as the
baseline's in *every* dimension — test peeks, metric variant, model/data budget,
split? If any dimension is looser, the number is not yet a fair claim. Tighten it
or disclose the gap explicitly; do not let a looser protocol masquerade as an
improvement.
