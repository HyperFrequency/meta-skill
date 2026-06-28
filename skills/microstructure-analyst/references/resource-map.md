# Resource map — MAE-exhaustion entry timing (`order-flow-opt` fold-in)

This file preserves the operational detail of the original `order-flow-opt`
workflow that was folded into Section G of the parent `SKILL.md`. It documents
the runnable modules in this `references/` directory, the data-path conventions
the original workflow assumed, the extract → backtest → compare CLI flow, the
integration recipes, and troubleshooting notes.

The premise (see Section G): the indicator owns **direction**, order-flow
exhaustion owns **timing**. The indicator logic stays 100% unchanged; exhaustion
detection only shifts *when* the entry fires inside the signal window, to
minimise Maximum Adverse Excursion (MAE).

---

## Runnable modules (in this directory)

| File | Class(es) | Purpose |
| --- | --- | --- |
| `features.py` | `OrderFlowFeatures`, `OrderFlowSnapshot` | Calculates 33 features per bar from L2 book state: book imbalance, spread, depth, microprice, volume profile, wall detection, temporal dynamics |
| `exhaustion.py` | `ExhaustionDetector`, `ExhaustionType` | Detects the six exhaustion signal types and combines them into a weighted score |
| `mae_strategy.py` | `MAEOptimizedStrategy`, `MAEStrategyConfig` | NautilusTrader base strategy: IDLE → PENDING → POSITIONED entry state machine, exhaustion-based entry timing, MAE tracking + logging, flow filtering |

`exhaustion.py` and `mae_strategy.py` import `OrderFlowSnapshot` from
`features.py` via relative import (`from .features import ...`), so the three
files must stay co-located.

---

## Exhaustion signals

| Signal | Description | Weight |
| --- | --- | --- |
| `IMBALANCE_RECOVERY` | Adverse imbalance returning to neutral | 0.25 |
| `IMBALANCE_FLIP` | Imbalance flipped to favorable (strongest) | 0.20 |
| `SPREAD_NORMALIZED` | Wide spread returning to normal | 0.15 |
| `DEPTH_RECOVERY` | Depleted side recovering | 0.15 |
| `MOMENTUM_DECAY` | Rate of adverse change slowing | 0.15 |
| `WALL_ABSORBED` | Large opposing orders consumed | 0.10 |

Entry triggers when the combined score crosses the threshold (default 0.5).

## Configuration presets

| Preset | Entry window | Threshold | Trade-off |
| --- | --- | --- | --- |
| `conservative` | 20 bars | 0.6 | Best MAE, more missed trades |
| `balanced` (default) | 15 bars | 0.5 | Balanced |
| `aggressive` | 10 bars | 0.35 | Fewer missed trades, higher MAE |

---

## Data-path conventions (original workflow layout)

The original `order-flow-opt` module lived under
`$HOME/Desktop/HyperFrequency/order-flow-opt/` and assumed the following
layout. These paths are workflow conventions, not hard dependencies of the
modules in this directory — adapt to wherever your catalog lives.

| Data | Path |
| --- | --- |
| L2 book raw (hourly `.lz4` snapshots per symbol) | `$HOME/Desktop/HyperFrequency/data-historical/hyperliquid/l2book/<SYMBOL>/YYYYMMDD_HH.lz4` |
| Extracted features | `$HOME/Desktop/HyperFrequency/data-historical/features/<SYMBOL>_flow_features_5m.parquet` |
| OHLCV | `$HOME/Desktop/HyperFrequency/data-historical/hyperliquid/futures/parquet/` |
| Module root | `$HOME/Desktop/HyperFrequency/order-flow-opt/` |
| Config | `$HOME/Desktop/HyperFrequency/order-flow-opt/configs/default.yaml` |

The original module also shipped `src/data_loader.py` (`L2BookLoader`, a
memory-efficient `.lz4` reader) and `src/example_ema_strategy.py` (a complete
EMA-crossover example). Those two helpers were not carried into this skill —
the parent skill's Section A/B already cover L2 ingestion and reconstruction,
and Section D covers the backtest wiring. Re-create the loader against the
parent skill's parquet/catalog conventions rather than the `.lz4` originals.

---

## CLI flow (original workflow)

```bash
# 1. Download L2 book data (memory-safe chunked downloader)
python3 datapull_hl_chunked.py --start YYYY-MM-DD --end YYYY-MM-DD --workers 4

# 2. Extract order-flow features
python3 scripts/extract_features.py --symbol BTC --start YYYY-MM-DD --end YYYY-MM-DD
python3 scripts/extract_features.py --all-symbols

# 3. Run backtest (and with/without-flow comparison)
python3 scripts/run_backtest.py --symbol BTC --start 2024-01-01 --end 2024-06-30
python3 scripts/run_backtest.py --symbol BTC --compare
```

The `extract_features.py` / `run_backtest.py` driver scripts were part of the
original module's `scripts/` directory and are **not** bundled here — only the
three core library modules above are. Treat the commands as the intended shape
of a driver you wire against the parent skill's ingestion (Section A) and
backtest engines (Section D), not as runnable entry points in this skill.

---

## Integration recipes

### Level 1 — filter only (minimal change)

```python
signal = your_indicator(bar)
if flow.spread_bps > 12 or flow.book_imbalance * signal < -0.3:
    signal = 0  # block entry into clearly adverse flow
```

### Level 2 — timing only

```python
signal = your_indicator(bar)
if signal == 1:
    result = detector.detect_sell_exhaustion(flow, signal_flow)
    if result.ready:
        execute()
```

### Level 3 — full integration (recommended)

```python
from mae_strategy import MAEOptimizedStrategy, MAEStrategyConfig

class MyStrategy(MAEOptimizedStrategy):
    def indicator_signal(self, bar) -> int:
        return your_indicator(bar)        # UNCHANGED: 1=BUY, -1=SELL, 0=FLAT

    def should_exit(self, bar, flow) -> bool:
        return self.hit_stop or self.hit_target
```

---

## Quick verification of the detector

```python
from features import OrderFlowFeatures
from exhaustion import ExhaustionDetector

flow = OrderFlowFeatures(levels=5)
detector = ExhaustionDetector()

# Snapshot with selling pressure (asks heavier than bids)
bids = [(100.0, 50), (99.9, 100)]
asks = [(100.1, 200), (100.2, 300)]
signal = flow.update(bids, asks, 0)
detector.update(signal)
print(f"signal imbalance: {signal.book_imbalance:.3f}")

# Simulate sellers exhausting (bids replenish, asks consumed)
for i in range(6):
    bids = [(100.0, 50 * (1 + i * 0.3)), (99.9, 100 * (1 + i * 0.3))]
    asks = [(100.1, 200 * (1 - i * 0.15)), (100.2, 300 * (1 - i * 0.15))]
    snap = flow.update(bids, asks, i + 1)
    detector.update(snap)
    result = detector.detect_sell_exhaustion(snap, signal)
    print(f"bar {i+1}: imb={snap.book_imbalance:+.3f} "
          f"score={result.exhaustion_score:.2f} ready={result.ready}")
    if result.ready:
        print("*** ENTER ***")
        break
```

---

## Troubleshooting

| Issue | Solution |
| --- | --- |
| No L2 data | Run the chunked downloader first (Section A of the parent skill covers ingestion) |
| Memory overflow on ingest | Use the chunked / lazy readers (Polars `scan_csv`, DuckDB), not eager loads — Section A.2 |
| Entry window expires before exhaustion | Lower the score threshold (e.g. 0.4) or widen the entry window |
| Too many trades filtered out | Increase `max_spread_bps`, lower `min_depth_percentile` |
| `nautilus_trader` import error | `pip install nautilus_trader` (the base strategy targets the Nautilus `Strategy` API — Section D.2) |

---

## Expected results (illustrative — re-validate)

| Metric | Without flow | With flow |
| --- | --- | --- |
| Avg MAE | -1.8% | -0.8% |
| Win rate | 52% | 58–62% |
| Trade count | 100% | 60–75% |
| Sharpe | 1.0 | 1.3–1.6 |

These figures are from the source workflow's own Hyperliquid backtests and are
**not** validated in this skill. Re-run on your own data and evaluate
MAE/leverage with the `tearsheet-generator` skill before quoting them.
