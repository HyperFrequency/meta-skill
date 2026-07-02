---
title: Example — Splitter walk-forward
domain: trading
last_updated: 2026-06-29
---

# Worked example: Splitter-based walk-forward

`vbt.Splitter` produces the in-sample / out-of-sample folds (the vbt
machinery). Epoch-selection *policy* belongs to `adaptive-wfo-epoch`;
this example only wires the folds and reports per-fold OOS metrics.
vectorbt-pro assumed (`Splitter` is Pro-grade).

```python
import vectorbtpro as vbt
import numpy as np

# Rolling walk-forward: 365-bar train, 90-bar test, step 90.
splitter = vbt.Splitter.from_rolling(
    close.index,
    length=365 + 90,
    split=365 / (365 + 90),   # fraction that is in-sample
    set_labels=["train", "test"],
)

def backtest(price, fast_w, slow_w):
    fast = vbt.MA.run(price, window=fast_w)
    slow = vbt.MA.run(price, window=slow_w)
    pf = vbt.Portfolio.from_signals(
        price,
        entries=fast.ma_crossed_above(slow),
        exits=fast.ma_crossed_below(slow),
        size=1.0, size_type="percent",
        fees=0.001, slippage=0.0005,
        freq="1D", init_cash=10_000,
    )
    return pf.sharpe_ratio()

# Apply across folds; pick params on train, score on test.
results = splitter.apply(
    backtest,
    vbt.Takeable(close),
    fast_w=10, slow_w=50,
    _execute_kwargs=dict(show_progress=False),
)
print(results)   # one Sharpe per (split, set)
```

For purged k-fold use `vbt.CVSplitter`. For "is the OOS Sharpe real?"
(PBO, deflated Sharpe) hand off to `model-evaluation`. Verify
`Splitter.from_rolling` / `.apply` kwargs against the live source —
these drift between Pro releases.
