# Leakage + stationarity

The macro story (ADF / KPSS / fractional differencing for stationarity, purged-and-embargoed CV for leakage) is covered in detail by the sibling `feature-engineering` skill and the `model-evaluation` skill. Read those first. The microstructure-specific additions follow.

## Stationarity at the bar level

- **Volume / dollar / imbalance bars** make returns *much* closer to stationary than time bars. Run ADF on returns under each bar clock and pick the clock that produces the strongest rejection of the unit root. Lopez de Prado AFML Ch. 2.6 calls this out explicitly: the choice of bar clock is itself a stationarity intervention.
- **Fractional differencing** (`(1-L)^d` for non-integer `d`; AFML Ch. 5) is still worth it for *price-level* features (micro-price level, mid level) even after the bar clock is chosen well. Use `d` in `[0.3, 0.7]` for liquid intraday data; verify ADF passes at the chosen `d`.
- **Intraday seasonality** persists even under volume bars on instruments with strong session structure (open/close in equities, daily funding on perps). Subtract a rolling-window seasonal mean *computed without look-ahead* (use only past sessions' empirical seasonality) before fitting any model that assumes a stationary mean.

## Leakage modes specific to microstructure

| Mode | Where it bites | Fix |
|---|---|---|
| Bar-edge ffill direction | Aligning indicators to bars with `method='bfill'` instead of `'ffill'` | Always `'ffill'`. Treat `'bfill'` as a code smell in this skill. |
| HMM fit on full sample | Decoded state at time t depends on data from t+1..T | Roll-fit HMM on expanding window; decode only the latest state. |
| Triple-barrier overlap | Sample i's label depends on prices through `t1_i`, which overlaps sample j > i's *feature window*. Train/test partitions become non-IID. | Use purged + embargoed CV (`model-evaluation`); sample-uniqueness weights (AFML Ch. 4). |
| Volume-bar boundary look-ahead | The exact bar boundary depends on the trade that *crosses* the threshold; if you set features at `bar.close`, some features use info from a trade beyond the threshold | Set features at the *last trade with cumulative volume strictly less than the threshold*; alternatively, accept the small overshoot and document it. |
| Realized variance scale-mismatch | RV computed at sub-bar grid leaks into the bar's *own* return if you sample too finely | Choose sub-bar grid so that the bar's terminal return is computed only at the bar's last price, not at any intra-bar mid. |

## Cross-asset feature transfer

A feature trained on BTC-PERP at Binance does not, in general, transfer to ETH-PERP at Hyperliquid. The dimensions that break transfer:

- **Tick size** (book imbalance is scale-sensitive to it).
- **Tape granularity** (some venues coalesce; OFI computed on coalesced trades is biased low).
- **Maker rebates / funding cycle** (changes the optimal trade-sign autocorrelation regime).
- **Lit-vs-dark fraction** (irrelevant on most crypto venues, dominant on US equities).

When transferring, normalize features by venue-and-symbol *running statistics* (z-score against a 30-day rolling window of the same symbol-venue), and validate with a *within-symbol* CV before claiming cross-symbol generalization.
