---
title: vectorbt vs vectorbt-pro — API differences
domain: trading
last_updated: 2026-04-20
---

# vectorbt vs vectorbt-pro

Both libraries share the NumPy-first mental model and the same core
classes (`Portfolio`, `IndicatorFactory`, `Data`, `ArrayWrapper`,
`Records`, `MappedArray`). The Pro version extends + replaces certain
subsystems; treat them as related but distinct libraries.

**Always state the variant in the first line of the emitted code.**

```python
# vectorbt-pro assumed (imported as `vbt`).
import vectorbtpro as vbt
```

## Feature matrix

| Feature | vanilla `vectorbt` | `vectorbt-pro` |
|---|---|---|
| Licence | Apache 2.0 + Commons Clause | proprietary, paid |
| Install | `pip install vectorbt` | `pip install "vectorbtpro @ git+..."` (token gated) |
| `Portfolio.from_signals` | ✅ | ✅ |
| `Portfolio.from_orders` | ✅ | ✅ |
| `Portfolio.from_holding` | ✅ | ✅ |
| `Portfolio.from_order_func` | ✅ | ✅ (more kwargs) |
| `PortfolioOptimizer` (target-weight / target-vol sizing) | ❌ | ✅ |
| `Splitter` / `CVSplitter` (walk-forward, purged CV) | partial | ✅ |
| Signal expression language (`SignalContext`, `Expression`) | ❌ | ✅ |
| Chunked execution (larger-than-RAM universes) | ❌ | ✅ |
| `BBANDS.run(..., wtype=...)` | `alpha` for stddev mult | `alpha` for stddev mult + `wtype` for MA type |
| `BBANDS` attribute name | `.middle` | `.middle` (both use middle, not basis) |
| `Data` providers | `BinanceData`, `CCXTData`, `YFData` | + `PolygonData`, `AlpacaData`, `BybitData`, `FeatherData`, `DuckDBData`, etc. |
| NB indicators (`bbands_nb`, `atr_nb`, `rsi_nb`) | limited | extensive, Pine-compatible defaults |
| Knowledge base (inline docs queryable at runtime) | ❌ | ✅ (Pro 0.27+) |
| Registry (discoverable `Parameterized` classes) | partial | full |
| Persistent Numba cache | partial | ✅ |
| Official support | community / GitHub issues | paid support channel |

## When they differ silently

These are the gotchas — silently-different behaviour with no runtime
error to flag it.

1. **`size_type="percent"` semantics** — in vectorbt-pro 0.26+ it's
   fractional (0.0–1.0). In older vbt-pro and in some vanilla versions
   it was 0–100. Verify your installed version before emitting.
2. **`BBANDS` `wtype` parameter** — Pro accepts `wtype=0` (SMA, default),
   `wtype=1` (EMA), `wtype=2` (WMA), etc. Vanilla typically has only
   SMA. If the Pine source uses an EMA-based BB, Pro is
   ergonomic; vanilla requires a manual EMA + stddev.
3. **`ATR` smoothing** — Pro's `ATR.run(...).atr` uses Wilder by
   default (Pine-compatible). Vanilla's varies per release; check with
   a Context7 query.
4. **Indicator parameter broadcasting** — both support it, but Pro's
   `IndicatorFactory.run(...)` handles nested parameter product
   explosions more gracefully.

## Choosing the variant for the task

| User context | Variant |
|---|---|
| "I want to backtest a Pine script I have" | Pro if available (better indicators), vanilla if the user says they only have vanilla |
| "I want parameter optimization at scale" | Pro — `Splitter` + chunked execution + `PortfolioOptimizer` pay off |
| "I want a quick equity-curve plot" | either — `pf.plot()` works identically |
| "I'm on an open-source-only stack" | vanilla |
| "I'm on the HyperFrequency quant stack" | Pro (HF fork is the canonical path) |

When in doubt, ask the user which they're on.
