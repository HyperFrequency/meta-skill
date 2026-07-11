# Metrics: Match the Formula Exactly

A metric *name* is not a definition. "nRMSE", "F1", "mAP", "accuracy", and
"relative-L2" each name a family of inequivalent formulas. Two papers reporting
"nRMSE" on the same predictions can differ by 1-10% purely from normalization
and averaging choices. If your formula differs from the benchmark's, you are not
comparing like with like — and a 5% "improvement" can be entirely an artifact of
the formula.

**Rule:** read the benchmark's *own metrics code* (not just its paper prose) and
reproduce that exact computation. When the paper and the code disagree, the code
is authoritative.

## Worked example: PDEBench-style nRMSE

```python
import torch

def calc_nrmse(preds, targets, init_step):
    """Per-timestep spatial RMSE, normalized per timestep, then averaged.
    Tensor layout here: [N, X, T, C] -> permute to [N, C, X, T]."""
    p  = preds[:, :, init_step:, :].permute(0, 3, 1, 2)    # [N, C, X, T]
    tg = targets[:, :, init_step:, :].permute(0, 3, 1, 2)
    err = torch.sqrt(torch.mean((p - tg) ** 2, dim=2))     # spatial RMSE: [N, C, T]
    nrm = torch.sqrt(torch.mean(tg ** 2, dim=2)) + 1e-20   # per-timestep norm
    return torch.mean(err / nrm).item()                    # average over N, C, T
```

Cross-check the output against the benchmark's shipped metrics module (for
PDEBench, `pdebench/models/metrics.py`) on the same arrays before trusting it.

## The same name, three different numbers

These three "nRMSE" definitions are all defensible and all different:

```text
# A. Per-timestep normalize, then average  (common in code implementations)
err_per_t   = sqrt(mean_spatial((pred - target)^2))     # [N, C, T]
nrm_per_t   = sqrt(mean_spatial(target^2))
nrmse_A     = mean_over(N, C, T)  err_per_t / nrm_per_t

# B. Per-sample Frobenius-norm ratio  (canonical PDEBench definition)
nrmse_B     = mean_over_N( ||pred_i - target_i||_F / ||target_i||_F )

# C. Global RMSE / global RMS  (single ratio over the whole tensor)
nrmse_C     = sqrt(mean_all((pred - target)^2)) / sqrt(mean_all(target^2))
```

A and B differ because A normalizes and averages ratios timestep-by-timestep
while B forms one ratio per sample; C differs from both because it never forms a
ratio until the very end. On the same predictions these can span several percent.

When the correct variant is genuinely ambiguous:

1. Read the benchmark's `metrics.py` and reproduce that variant as primary.
2. If you cannot determine which the baseline used, compute **all** plausible
   variants and show you win under each — a claim that survives every reasonable
   formula is robust.
3. Record which formula produced the reported number in your results artifact.

The same discipline applies beyond nRMSE: macro vs micro vs weighted F1;
top-1 vs top-5 accuracy; mAP at different IoU thresholds; relative-L2 with
different norm orders. Always pin the exact variant.

## Physics-Informed Validation

For PDE surrogates, simulation emulators, and other physically-grounded models,
a low error metric is necessary but not sufficient. A surrogate can have small
nRMSE while violating conservation or producing negative densities — physically
useless despite the good number. Verify consistency:

| Check              | What to compute                                   | Pass criterion            |
| ------------------ | ------------------------------------------------- | ------------------------- |
| Conservation laws  | Mass / momentum / energy integral over time       | Drift < 5% of baseline    |
| Physical bounds    | Density ≥ 0, temperature ≥ 0, mass fraction ∈ [0,1] | Zero violations          |
| Symmetry           | If the PDE has a symmetry, the solution must too   | Error < 1%                |
| Known limits       | Compare to an analytical solution in a special case | Match to < 1%           |
| Error vs time      | nRMSE at each rollout step                          | No exponential blow-up   |
| Spectral content   | FFT of prediction vs truth                          | No spurious high-freq energy |

Rollout error growth deserves special attention: autoregressive surrogates can
look excellent one step out and diverge over a long horizon. Always plot the
per-step error curve rather than reporting only a horizon-averaged number.
