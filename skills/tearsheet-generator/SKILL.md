---
name: tearsheet-generator
description: >
  Generate strategy performance tear sheets via quantstats-rs (the Rust QuantStats
  engine — Sharpe/Sortino/Calmar, drawdown curves, monthly heatmaps, embedded SVG
  charts) PLUS this skill's own MAE (Maximum Adverse Excursion)
  percentile analysis, optimal-leverage / liquidation-buffer recommendations, and a
  full trade list. Use when the user wants a tearsheet, a performance report, a "tear
  sheet from my trades or returns", MAE analysis, or "what leverage is safe for this
  strategy". Trigger even without the word "tearsheet" on phrases like "report on this
  backtest", "show me Sharpe and drawdown", "max adverse excursion", "optimal leverage",
  "liquidation buffer". Owns reporting + MAE/leverage. For the event-driven backtest
  ENGINE use nautilus-trader; for vectorized authoring/sweeps use vectorbt; for
  is-this-Sharpe-real / PBO / purged CV validation use model-evaluation; to compare a
  backtest against an Optuna/Ray baseline use strategy-verify; to port a strategy across
  frameworks use strategy-translator.
version: "2.0.0"
allowed-tools: Read, Write, Edit, Bash, Glob
license: MIT
metadata:
  skill-author: HyperFrequency
  upstream: quantstats-rs (HyperFrequency fork of netcan/quantstats-rs)
---

# Tearsheet Generator Skill

## About

This skill produces two layers and stitches them together:

1. **Performance tear sheet** — rendered by **quantstats-rs**, a Rust reimplementation of
   QuantStats (HyperFrequency fork of `netcan/quantstats-rs`). It emits a standalone HTML
   report with the full QuantStats metric table and embedded SVG charts (returns, log
   returns, rolling Sharpe/Sortino/vol, drawdown periods + underwater curve, monthly
   heatmap, EOY table). No Python QuantStats / matplotlib dependency.
2. **MAE & leverage analysis** — this skill's own layer (`tearsheet_helpers.py`, numpy +
   scipy only): MAE percentile distribution, safe-leverage recommendations, liquidation
   risk, and buffer analysis. This is the differentiator quantstats-rs does not provide.

> Migrated from the Python `ranaroussi/quantstats` library to the in-house Rust engine
> (June 2026). The old external `StrategyComparisonTearsheet` path is retired.

**Key features:**
- Standalone HTML tear sheet with embedded SVG (no JS, opens directly in a browser)
- MAE (Max Adverse Excursion) percentile analysis (p50–p99)
- Optimal leverage recommendations with stop-loss levels
- Fixed Position (Static) vs Full Position (Dynamic) analysis
- 10% / 20% / 30% liquidation buffer calculations
- Full trade list with entry/exit details and MAE/MFE stats
- Copyable strategy config text boxes

## When to use

- "Generate a tearsheet / performance report for this strategy."
- "I have a trades CSV (or a returns series) — show me Sharpe, drawdown, monthly returns."
- "Run MAE analysis and tell me the safe leverage / liquidation buffer."
- "Compare strategy vs benchmark in a tear sheet."

For the things this skill hands off, see the Cross-links table below.

## Required tooling

| Dependency | What for | How it's invoked |
| --- | --- | --- |
| `quantstats-rs` binary | the performance tear sheet (HTML + SVG) | `quantstats-rs report --returns <csv> -o <out>.html` |
| Python 3.10+ (numpy, scipy) | MAE / leverage / liquidation layer | `tearsheet_helpers.py` (library) via `scripts/generate_tearsheet.py` |

Build the engine once (the crate lives at `~/neuro-centrifuge-repos/quantstats-rs`):

```bash
cargo install --path ~/neuro-centrifuge-repos/quantstats-rs   # puts `quantstats-rs` on PATH
# or run in place: cargo run --manifest-path ~/neuro-centrifuge-repos/quantstats-rs/Cargo.toml --bin quantstats-rs -- report ...
```

The orchestrator script auto-discovers the binary on `PATH` and falls back to `cargo run`.

## Quick Start

```bash
# From a returns CSV (date,return — return is a decimal fraction, 0.01 = +1%)
python scripts/generate_tearsheet.py --returns returns.csv -o SOL_MTF_EMA_001.html \
    --strategy-title "SOL MTF EMA"

# From a trades CSV + starting capital (derives a daily returns series, then renders)
python scripts/generate_tearsheet.py --trades trades.csv --capital 10000 \
    --mae -o SOL_MTF_EMA_001.html

# Strategy vs benchmark
python scripts/generate_tearsheet.py --returns returns.csv --benchmark spy.csv \
    --benchmark-title SPY -o report.html

# Or call the engine directly for the performance sheet alone
quantstats-rs report --returns returns.csv -o tearsheet.html
```

The three slash commands wrap these flows:

### /generate-tearsheet
Generate a complete tear sheet (performance + MAE/leverage sections).

### /verify-backtest
Verify tear sheet results against NautilusTrader for accuracy validation (delegates the
engine-side replay to `nautilus-trader`).

### /verify-mae-lev
Run a backtest with the optimal leverage config derived from MAE analysis.

## Output Files

- `{strategy}.html` — standalone HTML tear sheet (quantstats-rs performance report)
- `{strategy}_mae.json` — MAE / leverage analysis (when `--mae` is passed)

## Key Sections

### 1. Key Performance Metrics
Cumulative Return, CAGR, Sharpe, Sortino, Max DD, Calmar, volatility, win rates — from
quantstats-rs (mirrors the QuantStats metric table). Add `--benchmark` for a side-by-side
column with beta / R² / information ratio.

### 2. MAE Analysis & Optimal Leverage
- MAE distribution table (min, mean, p50, p75, p90–p99, max)
- Safe leverage recommendations per percentile
- Stop loss table with % PRICE movement (not position cost)

### 3. Fixed Position (Static) Analysis
- Leverage table: 5x, 10x, 15x, 20x, 25x, 30x
- Columns: Liq @ %Price, Rec. SL, Max Loss, +10% Buffer, +20% Buffer, Risk Level

### 4. Full Position (Dynamic) Analysis
- Warning about compounding risk
- Leverage table: 1x, 2x, 3x, 5x, 10x with per-level recommendation

### 5. Buffer Analysis Summary
- +10%, +20%, +30% buffers above worst MAE; safety check for 10x / 15x / 20x leverage

### 6. Full Trade List
- All trades with entry/exit times, prices, side, PnL, MAE, MFE, duration

### 7. Strategy Configuration
- Original config + MAE-optimized config (copyable JSON), plus backtest methodology

## Cross-links

| Need | Use |
| --- | --- |
| Event-driven backtest engine / live / Hyperliquid | `nautilus-trader` |
| Vectorized backtest authoring + parameter sweeps | `vectorbt` |
| "Is this Sharpe real?" / PBO / purged CV | `model-evaluation` |
| Compare a backtest to an Optuna/Ray baseline | `strategy-verify` |
| Port the strategy to another framework/language | `strategy-translator` |
| Walk-forward epoch selection | `adaptive-wfo-epoch` |

## References

- `references/mae_analysis.md` — MAE percentile + leverage methodology
- `references/leverage_math.md` — liquidation distance / buffer formulas
- `references/html_templates.md` — section layout notes
- quantstats-rs: `~/neuro-centrifuge-repos/quantstats-rs` (README → CLI Usage). Upstream:
  `netcan/quantstats-rs`. Python reference for parity: `ranaroussi/quantstats` (MIT).
- Last cross-checked: 2026-06-27.
