# MAE-exhaustion entry timing

Section G of the toolkit. Folded in from the `order-flow-opt` workflow. This
is the operational answer to a specific question: *your indicator already told
you the direction — when, within the resulting signal window, do you actually
enter?* The premise is that the indicator owns **direction** and order-flow
exhaustion owns **timing**; the indicator logic stays 100% unchanged, and
exhaustion detection only shifts *when* the entry fires inside the signal
window. The goal is to minimise **Maximum Adverse Excursion (MAE)** — the worst
unrealised drawdown a position sees between entry and exit — by waiting for
adverse flow to exhaust before committing.

## G.1 Core concept

```
Signal: BUY (e.g. EMA crossed)
├── Bar 1: imbalance = -0.33 (sellers active)      → WAIT
├── Bar 2: imbalance = -0.20 (sellers weakening)   → WAIT
├── Bar 3: imbalance = -0.07 (sellers exhausting)  → WAIT
├── Bar 4: imbalance = +0.07 (buyers emerging)     → WAIT
└── Bar 5: imbalance = +0.20, score = 0.60         → ENTER NOW
```

Entering at Bar 1 (the moment the indicator fires) eats the full adverse
excursion; waiting for the exhaustion score to clear threshold at Bar 5 enters
near the local trough of adverse pressure. The trade-off is missed trades when
the entry window expires before exhaustion is detected — tuned via the presets
in G.3.

## G.2 The six exhaustion signals

The `ExhaustionDetector` (see `references/exhaustion.py`) combines six
weighted sub-signals into a single exhaustion score in [0, 1]. Entry triggers
when the combined score crosses the threshold (default 0.5).

| Signal | Description | Weight |
| --- | --- | --- |
| `IMBALANCE_RECOVERY` | Adverse book imbalance returning toward neutral | 0.25 |
| `IMBALANCE_FLIP` | Imbalance flipped to favorable (strongest confirmation) | 0.20 |
| `SPREAD_NORMALIZED` | Wide spread contracting back to normal | 0.15 |
| `DEPTH_RECOVERY` | Depleted side of the book replenishing | 0.15 |
| `MOMENTUM_DECAY` | Rate of adverse change slowing | 0.15 |
| `WALL_ABSORBED` | Large opposing resting orders consumed | 0.10 |

These are heuristics over the same L2 features computed in the indicators
reference (book imbalance, spread, depth) — they are a *timing throttle*, not
directional alpha, and share the spoofing-detector caveat: confirm against
your own venue's shadow-mode logs before trusting the exact thresholds.

## G.3 Configuration presets

| Preset | Entry window | Score threshold | Trade-off |
| --- | --- | --- | --- |
| `conservative` | 20 bars | 0.6 | Best MAE reduction, more missed trades |
| `balanced` (default) | 15 bars | 0.5 | Balanced |
| `aggressive` | 10 bars | 0.35 | Fewer missed trades, higher residual MAE |

The window is how long after the indicator fires the detector keeps looking for
exhaustion before abandoning the entry; the threshold is the combined score
required to enter.

## G.4 Three integration levels

1. **Filter only** (minimal change to an existing strategy): block the signal
   when flow is clearly adverse — e.g. skip a long when `spread_bps > 12` or
   `book_imbalance * signal < -0.3`.
2. **Timing only**: keep the indicator signal, but defer execution until
   `detector.detect_*_exhaustion(...)` reports `ready`.
3. **Full integration** (recommended): subclass `MAEOptimizedStrategy` (see
   `references/mae_strategy.py`) and implement only `indicator_signal(bar)` and
   `should_exit(bar, flow)`; the base class owns the
   IDLE → PENDING → POSITIONED entry state machine and MAE tracking.

## G.5 Indicative results and honesty caveat

The source workflow reports the following on its own (Hyperliquid L2) backtests;
treat as **illustrative, not validated here** — re-run on your own data before
quoting:

| Metric | Without flow timing | With flow timing |
| --- | --- | --- |
| Avg MAE | -1.8% | -0.8% |
| Win rate | 52% | 58–62% |
| Trade count | 100% | 60–75% |
| Sharpe | 1.0 | 1.3–1.6 |

The trade-count drop is the cost: better entries come at the price of skipping
trades whose window expired before exhaustion. Whether that is net-positive is
strategy- and instrument-specific — validate with the backtest engines in the
backtest-and-live reference and the `tearsheet-generator` skill, and evaluate
MAE/leverage there.

## G.6 Runnable references

| File | Class | Purpose |
| --- | --- | --- |
| `references/features.py` | `OrderFlowFeatures`, `OrderFlowSnapshot` | 33 L2-derived features per bar (imbalance, spread, depth, microprice, wall detection) |
| `references/exhaustion.py` | `ExhaustionDetector`, `ExhaustionType` | The six-signal weighted exhaustion model above |
| `references/mae_strategy.py` | `MAEOptimizedStrategy`, `MAEStrategyConfig` | NautilusTrader base strategy with the entry state machine + MAE logging |

These three modules import each other (`exhaustion` and `mae_strategy` import
from `features`), so keep them co-located. Data-path conventions, the
extract → backtest → compare CLI flow, and troubleshooting notes from the
original workflow are preserved in `references/resource-map.md`.
