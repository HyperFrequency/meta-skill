---
title: Example — broadcasting parameter sweep
domain: trading
last_updated: 2026-06-29
---

# Worked example: broadcasting grid search

vectorbt runs an entire parameter grid in one compiled pass by treating
each parameter combination as a column. No Python loop. vectorbt-pro
assumed.

```python
import vectorbtpro as vbt
import numpy as np

# Two-dimensional grid: fast in {5,10,20}, slow in {50,100,200}.
fast = vbt.MA.run(close, window=[5, 10, 20], short_name="fast")
slow = vbt.MA.run(close, window=[50, 100, 200], short_name="slow")

# Cross every fast against every slow → Cartesian product of columns.
entries = fast.ma_crossed_above(slow, param_product=True)
exits = fast.ma_crossed_below(slow, param_product=True)

pf = vbt.Portfolio.from_signals(
    close,
    entries=entries,
    exits=exits,
    size=1.0, size_type="percent",
    fees=0.001, slippage=0.0005,
    freq="1D", init_cash=10_000,
)

# Every metric returns one value per column (per param combo).
sharpe = pf.sharpe_ratio()
print(sharpe.sort_values(ascending=False).head())
```

Stays ergonomic up to ~5 dimensions before the column count explodes;
beyond that move to optuna / ray (see `references/optimization.md`).

**The top of this ranking is almost always overfit.** Confirm
out-of-sample stability (see `examples/walk-forward.md`) and, for
Sharpe-realism / PBO, hand off to `model-evaluation`. Verify
`param_product` and `short_name` kwargs against the live source.
