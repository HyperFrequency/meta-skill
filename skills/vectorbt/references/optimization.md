---
title: vectorbt optimization
domain: trading
last_updated: 2026-06-29
---

# Optimization

| Method | Use for |
|---|---|
| Grid search via broadcasting | fast, exhaustive, <5 dims — just pass lists/ranges as params |
| `vbt.Splitter` / `vbt.CVSplitter` (pro) | walk-forward, purged k-fold |
| `PortfolioOptimizer` (pro) | target-weight / target-vol allocation |
| External (optuna, ray tune) | high-dim Bayesian / distributed sweeps |

## Grid search via broadcasting

Pass lists/ranges directly as indicator or portfolio params; vbt builds
the Cartesian product as columns and runs them in one compiled pass.
Stays ergonomic up to ~5 dimensions before the column count explodes.

```python
ma = vbt.MA.run(close, window=np.arange(10, 60, 10))   # 5 columns, one sweep
```

## Walk-forward with Splitter / CVSplitter (Pro)

Use `vbt.Splitter` for rolling/expanding walk-forward windows and
`vbt.CVSplitter` for purged k-fold. These produce the in-sample /
out-of-sample folds — they are the vbt *machinery*. Epoch-selection
*policy* (which window to trust, WFE, overfitting-epoch control) is NOT
this skill's job — hand that to `adaptive-wfo-epoch`.

## Overfit caveats

A top-ranked grid cell is almost always overfit. Before trusting it:
- Check out-of-sample stability across Splitter folds.
- For "is this Sharpe real?", PBO, deflated Sharpe, purged/combinatorial
  CV → hand off to `model-evaluation`.

## External HPO

For high-dim Bayesian or distributed sweeps, integrate optuna / ray
tune; for fan-out infra (Optuna/Ray/Dask/MLflow) hand off to
`neuro-quant-distributed-optimization`. Verify Splitter/CVSplitter and
`PortfolioOptimizer` signatures against the live source — these are
Pro-only and drift between releases.
