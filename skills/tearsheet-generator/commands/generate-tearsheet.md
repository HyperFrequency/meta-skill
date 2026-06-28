---
name: generate-tearsheet
description: Generate a comprehensive performance tear sheet (quantstats-rs) plus MAE / optimal-leverage analysis from a trades CSV
argument-hint: "[strategy_name] [--trades PATH] [--config PATH] [--capital AMOUNT] [--output DIR]"
---

# Generate Tearsheet Command

Generate a professional trading strategy tearsheet with comprehensive analysis.

## Usage

```bash
# Basic usage
/generate-tearsheet SOL_MTF_EMA_001 --trades /path/to/trades.csv

# With custom capital and output
/generate-tearsheet SOL_MTF_EMA_001 --trades ./trades.csv --capital 10000 --output ./tearsheets

# With strategy config
/generate-tearsheet SOL_MTF_EMA_001 --trades ./trades.csv --config ./strategy_config.json
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| strategy_name | Yes | Name of the strategy (used in output filenames) |
| --trades | Yes | Path to trades CSV file |
| --config | No | Path to strategy config JSON |
| --capital | No | Initial capital (default: 10000) |
| --output | No | Output directory (default: ./tearsheets) |

## Trades CSV Format

Required columns:
- `side` - LONG/SHORT or BUY/SELL
- `entry_time` - Entry timestamp
- `exit_time` - Exit timestamp
- `entry_price` - Entry price
- `exit_price` - Exit price
- `gross_pnl_pct` or `pnl_pct` - Trade P&L percentage
- `mae_pct` or `mae` - Max Adverse Excursion percentage

Optional columns:
- `net_pnl_pct` - Net P&L after fees
- `mfe_pct` or `mfe` - Max Favorable Excursion
- `duration_hours` or `bars` - Trade duration
- `reason_open` - Entry reason
- `reason_close` - Exit reason

## Implementation

This command wraps `scripts/generate_tearsheet.py` (see the skill's SKILL.md). The
performance section is rendered by the `quantstats-rs` engine; the MAE / leverage
section by the local `tearsheet_helpers.py`.

```bash
SKILL_DIR="$(dirname "$(dirname "$0")")"   # .../tearsheet-generator
OUT_DIR="${output_dir:-./tearsheets}"
mkdir -p "$OUT_DIR"

python "$SKILL_DIR/scripts/generate_tearsheet.py" \
    --trades "$trades_path" --capital "${capital:-10000}" --mae \
    --strategy-title "$strategy_name" \
    -o "$OUT_DIR/${strategy_name}.html"

# Produces:
#   $OUT_DIR/${strategy_name}.html       — performance tear sheet (quantstats-rs)
#   $OUT_DIR/${strategy_name}_mae.json   — MAE / leverage analysis
```

Prefer `--returns returns.csv` over `--trades` when you already have an exact period
returns series (the trades path derives daily returns as net-PnL/capital).

## Output

The command generates:

1. **HTML tear sheet** (`{strategy}.html`) — rendered by quantstats-rs
   - QuantStats-style metric table + embedded SVG charts (cumulative/log returns,
     rolling Sharpe/Sortino/vol, drawdown periods + underwater, monthly heatmap, EOY)
   - Standalone (no JS); add `--benchmark` for a strategy-vs-benchmark column

2. **MAE / leverage JSON** (`{strategy}_mae.json`) — from `tearsheet_helpers.py`
   - MAE distribution and percentiles (p50–p99)
   - Optimal-leverage recommendations per safety buffer
   - Per-leverage liquidation risk (5x/10x/15x/20x/25x): survival rate, risk score

> Known gap (not yet ported from the retired engine): multi-scenario *equity-curve*
> overlays (Buy & Hold vs Fixed-Nx vs Dynamic-Nx in one chart). Per-leverage risk now
> lives in the MAE JSON; render overlays per-series via `quantstats-rs` if needed.

## Example Output

```
wrote ./tearsheets/SOL_MTF_EMA_001.html (67089 bytes) from trades.csv
wrote ./tearsheets/SOL_MTF_EMA_001_mae.json
```
