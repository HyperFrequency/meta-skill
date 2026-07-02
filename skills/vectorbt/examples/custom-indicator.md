---
title: Example — IndicatorFactory end-to-end
domain: trading
last_updated: 2026-06-29
---

# Worked example: custom indicator via `IndicatorFactory`

When no built-in fits, wrap the logic in `IndicatorFactory` so you keep
parameter broadcasting + caching. vectorbt-pro assumed.

```python
import vectorbtpro as vbt

# A z-score-of-price indicator: (price - rolling mean) / rolling std.
# `from_expr` is the most ergonomic path — @p_* params, @in_* inputs.
ZScore = vbt.IF(
    class_name="ZScore",
    input_names=["close"],
    param_names=["window"],
    output_names=["z"],
).from_expr("""
mean = @talib_SMA(close, @p_window)
std  = rolling_std(close, @p_window)
z = (close - mean) / std
""")

# Parameter sweep: three windows in one call → three columns.
zscore = ZScore.run(close, window=[20, 50, 100])

# Turn the indicator into signals.
entries = zscore.z.vbt.crossed_below(-2.0)   # mean-reversion long
exits = zscore.z.vbt.crossed_above(0.0)
```

`from_expr` parses, broadcasts, and JIT-compiles the expression. If the
logic can't be expressed as a formula (external library per combo,
custom iteration), use `with_apply_func` / `with_custom_func` instead —
see `references/indicator-factory.md` for the decision tree and the
exact expression grammar (verify token names against the live source;
the `@`-prefix grammar is Pro-specific).
