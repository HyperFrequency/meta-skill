---
title: Example — signals to from_signals
domain: trading
last_updated: 2026-06-29
---

# Worked example: entries/exits → `from_signals`

The standard 95% case: boolean masks into `Portfolio.from_signals`.
vectorbt-pro assumed (imported as `vbt`).

```python
import vectorbtpro as vbt
import numpy as np

# 1. Load data (cached parquet for a reviewable backtest).
data = vbt.ParquetData.pull("BTCUSDT.parquet")
close = data.get("Close")

# 2. Build signals from built-in indicators (parameter sweep is free,
#    but here a single combo for clarity).
fast = vbt.MA.run(close, window=10)
slow = vbt.MA.run(close, window=50)
entries = fast.ma_crossed_above(slow)
exits = fast.ma_crossed_below(slow)

# 3. Construct the portfolio — every param explicit.
pf = vbt.Portfolio.from_signals(
    close,
    entries=entries,
    exits=exits,
    size=1.0,
    size_type="percent",
    fees=0.001,
    slippage=0.0005,
    freq=close.index.inferred_freq or "1D",
    init_cash=10_000,
)

# 4. Analyse.
print(pf.stats())

# 5. Validate.
print("entries:", int(entries.sum()), "exits:", int(exits.sum()))
print("trades:", pf.trades.count())
```

Fill convention here is **signal-bar close** (the `from_signals`
default). For next-bar-open fills, pass `price=open_next` — see
`references/fill-timing.md`.
