---
title: vectorbt fill timing
domain: trading
last_updated: 2026-06-29
---

# Fill timing — close vs next-bar open

`Portfolio.from_signals` fills at the **signal bar's CLOSE by default**,
not next-bar open. This is the single most common source of inflated,
look-ahead-flavoured results when a backtest is compared against a Pine
or live reference that fills next-bar.

## Decision tree

1. **Does the signal use only information available at the close of bar
   `t`?** (e.g. a moving-average cross computed from closes up to `t`.)
   - If you intend to *act on that close* (mark-to-close fills), the
     default `from_signals` behaviour is correct.
   - If you intend to *act at the next bar's open* (realistic for most
     EOD strategies), pass `price=open_next` so fills land on `open[t+1]`.

2. **Are your signals pre-lagged?** If you already shifted signals by one
   bar (`entries.shift(1)`) AND also pass `price=open_next`, you have
   double-lagged. Pick one mechanism, not both.

3. **Matching a Pine/live reference?** Pine `strategy.entry` with default
   `process_orders_on_close=false` fills on the next bar's open. To match
   it in vectorbt, supply `price=open_next` and do NOT pre-shift signals.

```python
open_next = data.get("Open").vbt.fshift(-1)   # next bar's open aligned to t
pf = vbt.Portfolio.from_signals(close, entries, exits, price=open_next, ...)
```

## Anti-pattern

Do **not** claim `from_signals` fills at next-bar open by default — it
does not. State the fill convention explicitly in the emitted code's
first line, and confirm it against the reference being matched.
