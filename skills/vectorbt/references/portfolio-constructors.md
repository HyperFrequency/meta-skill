---
title: vectorbt portfolio constructors
domain: trading
last_updated: 2026-06-29
---

# Portfolio constructors

Pick the right constructor (in order of most-common to least):

| Constructor | Use for |
|---|---|
| `Portfolio.from_signals` | boolean entry/exit masks — 95% of cases |
| `Portfolio.from_orders` | explicit size arrays (you decide size per bar) |
| `Portfolio.from_holding` | buy-and-hold baseline |
| `Portfolio.from_order_func` | custom per-bar logic (Numba callbacks) — escape hatch |

## Canonical `from_signals` call

Never omit any of these params without stating why:

```python
pf = vbt.Portfolio.from_signals(
    close,
    entries=entries,
    exits=exits,
    size=1.0,                       # fractional (not np.inf, not 100)
    size_type="percent",            # version-check: 0-1 in vbt 0.26+, 0-100 earlier
    fees=0.001,                     # 10 bps — state explicitly even if zero
    slippage=0.0005,                # 5 bps — same
    freq=close.index.inferred_freq or "1D",   # annualised stats depend on this
    init_cash=10_000,               # matters for % metrics
    # price=open_next,              # uncomment for next-bar-open fills
)
```

## from_orders

Use when you compute an explicit size per bar (e.g. volatility-targeted
sizing). Pass a `size` array aligned to `close`; positive = buy,
negative = sell, `0`/`np.nan` = hold.

## from_holding

Buy-and-hold baseline. Always emit one alongside a strategy backtest so
the reader can see whether the strategy beat passive exposure.

## from_order_func

The escape hatch for genuinely per-bar logic that masks can't express.
Write Numba callbacks — **not** a Python for-loop over bars (see the
anti-patterns in SKILL.md). Reserve this for path-dependent sizing,
inventory limits, or cross-asset rebalancing.

Fill timing (close vs next-bar open) is a separate decision — see
`fill-timing.md`. Verify constructor kwargs against the live source
before emitting; defaults drift between releases.
