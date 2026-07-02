---
title: vectorbt backtest validation
domain: trading
last_updated: 2026-06-29
---

# Validation — verify the backtest isn't silently wrong

Before returning a backtest, run at least these checks and state which
ran and their outcomes at the bottom of the deliverable. Unvalidated
backtests are flagged as incomplete by the consortium judge.

1. **Sanity on signal count** — print `entries.sum()`, `exits.sum()`.
   If the strategy should fire twice a year and shows 200 signals, you
   have a look-ahead or re-firing bug.
2. **No-trade sanity** — `pf.trades.count()` should match expectation.
3. **Equity curve shape** — if monotonically upward with no drawdowns,
   suspect look-ahead.
4. **Compare against a reference if one exists** — if the user provided
   a Pine script or published backtest, run the numeric-equivalence
   recipe (`scripts/compare-pine-reference.py`) and cite the delta.

## Common silent-failure modes

- **Look-ahead**: a signal that reads bar `t`'s close but is acted on at
  bar `t`'s close while the reference acts next-bar (see `fill-timing.md`).
- **Re-firing**: entries that stay `True` for many bars without exits,
  producing far more trades than intended.
- **Fee/slippage omission**: a too-smooth, too-high return is often a
  zero-cost backtest. State fees and slippage explicitly even when zero.
- **`freq` omission**: annualised Sharpe/return become meaningless.

The `scripts/validate-backtest.py` helper smoke-runs an emitted backtest
file and prints these sanity metrics automatically.
