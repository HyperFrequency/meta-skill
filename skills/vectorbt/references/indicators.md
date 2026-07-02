---
title: vectorbt built-in indicators
domain: trading
last_updated: 2026-06-29
---

# Built-in indicators and NB primitives

Prefer VBT's built-in indicators and NB primitives over hand-rolled
pandas. VBT Pro NB indicators (`bbands_1d_nb`, `atr_nb`, `rsi_nb`)
default to Pine-compatible params (`adjust=False`, `ddof=0`).
Hand-rolled `.ewm()` inherits pandas' `adjust=True` default and
diverges.

```python
# parameter sweep is free: one call, three columns
ma = vbt.MA.run(close, window=[10, 20, 50])
fast = vbt.MA.run(close, window=10)
slow = vbt.MA.run(close, window=50)
entries = fast.ma_crossed_above(slow)
exits = fast.ma_crossed_below(slow)
```

## Why not hand-roll `.ewm()`

- pandas `.ewm()` defaults to `adjust=True`; VBT Pro NB indicators
  default to `adjust=False` (Pine-compatible). Mixing them produces
  silently different values, especially in the warm-up window.
- Hand-rolled NumPy functions bypass VBT's caching + broadcasting, so
  you lose the parameter-sweep speedup that is the whole point of vbt.

If no built-in fits, build a custom indicator via `IndicatorFactory`
rather than an ad-hoc function — see `indicator-factory.md`.

Verify indicator param names/defaults against the live source (VBT Pro
MCP or Context7) before emitting; vanilla and Pro differ on some params.
