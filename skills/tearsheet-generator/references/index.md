# Tearsheet Generator Reference Index

## Core Files

| File | Description |
|------|-------------|
| `SKILL.md` | Main skill documentation with commands and examples |
| `tearsheet_helpers.py` | Python helper module for MAE analysis and leverage recommendations |

## Reference Documents

| Document | Topics Covered |
|----------|----------------|
| `mae_analysis.md` | MAE theory, percentile calculations, risk scoring |
| `leverage_math.md` | Leverage formulas, buffer calculations, Kelly criterion |
| `html_templates.md` | CSS templates, HTML components, responsive design |

## Related Scripts

| Script | Location | Purpose |
|--------|----------|---------|
| `generate_tearsheet.py` | `scripts/` | Tear sheet orchestrator: quantstats-rs performance report + MAE/leverage layer |

## Quick Reference

### Generate Tearsheet
```bash
python scripts/generate_tearsheet.py --trades trades.csv --capital 10000 --mae \
    --strategy-title SOL_MTF -o ./tearsheets/SOL_MTF.html
```

### MAE Analysis
```python
from skills.tearsheet_generator.tearsheet_helpers import calculate_mae_percentiles, recommend_leverage

stats = calculate_mae_percentiles(trades)
recs = recommend_leverage(stats.p95)
```

### Liquidation Risk
```python
from skills.tearsheet_generator.tearsheet_helpers import analyze_liquidation_risk

risk = analyze_liquidation_risk(trades, leverage=10.0)
print(f"Survival rate: {risk.survival_rate}%")
```

## Key Formulas

| Metric | Formula |
|--------|---------|
| Liquidation Threshold | `100% / leverage` |
| Buffer Threshold | `(100% / leverage) * (1 - buffer)` |
| Max Safe Leverage | `100% / p95_mae * (1 - buffer)` |
| Leveraged Return | `base_return * leverage` |
| Dynamic Leverage | `max(1, base_lev * (1 - drawdown))` |

## Output Files

When generating a tearsheet, these files are created:

```
tearsheets/
├── STRATEGY_NAME.html        # Performance tear sheet (quantstats-rs)
└── STRATEGY_NAME_mae.json    # MAE distribution + leverage/liquidation analysis
```

## Integration Points

| Tool | Integration |
|------|-------------|
| Nautilus Trader | Load trades with `source_type="nautilus"` for verification badge |
| Ray Tune | Generate tearsheets for optimized configurations |
| quantstats-rs | Rust QuantStats engine — renders the performance tear sheet HTML |
| Hyperliquid | Apply recommended leverage via SDK patch |

## Common Issues

1. **Missing MAE data**: Falls back to using `return_pct` for losing trades
2. **Large numbers**: Automatically formatted with K/M/B/T/Q suffixes
3. **Extreme leverage returns**: Capped display at `>10^100`
4. **Monthly gaps**: Check trade date range for continuity
