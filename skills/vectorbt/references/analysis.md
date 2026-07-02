---
title: vectorbt portfolio analysis
domain: trading
last_updated: 2026-06-29
---

# Analysis — reading the portfolio

Standard stats live on the portfolio object:

```python
pf.total_return()
pf.sharpe_ratio()
pf.max_drawdown()
pf.trades.stats()              # per-trade level
pf.positions.stats()           # per-position level
pf.stats()                     # kitchen sink, pandas Series
pf.returns_stats()             # returns-centric slice
pf.plot().show()               # interactive Plotly tearsheet
```

For reportable outputs, emit `pf.stats()` plus a saved `pf.plot()`.

## Custom metric patterns

- **Rolling drawdown windows** — `pf.drawdowns` exposes a `Records`
  object; reduce over rolling windows for regime-aware drawdown.
- **Regime-conditioned returns** — slice `pf.returns()` by a boolean
  regime mask (e.g. high/low realised vol) and compare sub-period stats.
- **Per-column (parameter) stats** — when `close` was broadcast across a
  parameter grid, every metric above returns one value per column; sort
  to rank parameter combos, but read `optimization.md` first for the
  overfit caveats before trusting the top of that ranking.

`pf.stats()` and `pf.returns_stats()` annualise using the `freq=` passed
at construction. If `freq` was omitted, annualised numbers are ambiguous
— fix construction, don't reinterpret the output. Verify metric names
against the live source; some are Pro-only.
