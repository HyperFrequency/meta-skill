---
title: VectorBT Pro IndicatorFactory
domain: trading
last_updated: 2026-04-20
---

# IndicatorFactory (`vbt.IF`)

Canonical way to wrap a signal-generation expression or a Numba kernel
as a first-class vbt indicator with parameter broadcasting, caching,
and column alignment baked in. **Prefer this over hand-rolled NumPy
functions** — hand-rolls bypass vbt's caching + broadcasting and
lose the parameter-sweep speedup that is the whole point of vbt.

Three construction paths:

1. **`from_expr(expr_string)`** — most ergonomic. Write the logic as
   a string using `@p_*` for params, `@in_*` for inputs, `@out_*` for
   outputs. vbt parses, broadcasts, and JIT-compiles.
2. **`with_custom_func(custom_func)`** — pass a numpy/pandas function
   that handles parameter iteration itself. Used when `from_expr` can't
   express the logic (custom loops, external libraries).
3. **`with_apply_func(apply_func)`** — pass a function that processes
   ONE parameter combination; vbt iterates and stacks.

Quick decision:
- "My logic is a formula on inputs and scalar params" → `from_expr`
- "I need to call an external library per param combo" → `with_apply_func`
- "I need full control over parameter iteration" → `with_custom_func`

## `from_expr` prefix syntax

Verified against Context7 corpus
`/llmstxt/vectorbt_pro_pvt_4f8d7c01_llms-full_txt`:

| Prefix | Meaning |
|---|---|
| `@in_<name>` | Named INPUT (maps to `input_names`); vbt provides the broadcast array |
| `@p_<name>` | Named PARAMETER (maps to `param_names`); vbt broadcasts across combos |
| `@out_<name>:expr` | Named OUTPUT binding (maps to `output_names`) |
| `@res_<builtin>` | RESOLVED call to a built-in vbt indicator (e.g. `@res_talib_bbands`) |
| `@settings` | Access the SETTINGS singleton inside the expression |

## Canonical example: parametric Bollinger-squeeze generator

Pattern from `signal-development/generation`:

```python
MaskGenerator = vbt.IF.from_expr("""
upperband, middleband, lowerband = @res_talib_bbands
bandwidth = (upperband - lowerband) / middleband
cond1 = low < lowerband
cond2 = bandwidth > @p_cond2_th
cond3 = high > upperband
cond4 = bandwidth < @p_cond4_th
@out_mask:(cond1 & cond2) | (cond3 & cond4)
""")

mask_generator = MaskGenerator.run(
    high=data.get("High"),
    low=data.get("Low"),
    close=data.get("Close"),
    cond2_th=[0.3, 0.4],
    cond4_th=[0.1, 0.2],
    bbands_timeperiod=vbt.Default(14),   # default for the @res call
    param_product=True,                   # cartesian product of params
)
```

Notes:
- `@res_talib_bbands` calls talib's BBANDS through vbt's wrapper — ALL
  talib indicators are reachable via `@res_talib_*`.
- `param_product=True` produces every combination of `cond2_th` × `cond4_th` × … as separate output columns.
- `vbt.Default(14)` sets a parameter default that can be overridden per
  run call.

## Pairs-trading example (OLS regression + z-score)

Pattern from `tutorials/pairs-trading`:

```python
PTS_expr = """
    x = @in_close.iloc[:, 0]
    y = @in_close.iloc[:, 1]
    ols = vbt.OLS.run(x, y, window=@p_window, hide_params=True)
    upper = st.norm.ppf(1 - @p_upper_alpha / 2)
    lower = -st.norm.ppf(1 - @p_lower_alpha / 2)
    upper_crossed = ols.zscore.vbt.crossed_above(upper)
    lower_crossed = ols.zscore.vbt.crossed_below(lower)
    long_entries = wrapper.fill(False)
    short_entries = wrapper.fill(False)
    short_entries.loc[upper_crossed, x.name] = True
    long_entries.loc[upper_crossed, y.name] = True
    long_entries.loc[lower_crossed, x.name] = True
    short_entries.loc[lower_crossed, y.name] = True
    long_entries, short_entries
"""

PTS = vbt.IF.from_expr(PTS_expr, keep_pd=True, st=st)   # st=scipy.stats injected
PTS.run(close, window=[20, 50], upper_alpha=0.05, lower_alpha=0.05)
```

Notes:
- `keep_pd=True` makes inputs/outputs pandas objects (not raw arrays)
  so `.iloc`/`.loc` work.
- Extra kwargs like `st=st` inject Python objects into the expression
  namespace (scipy.stats here).
- `wrapper.fill(False)` is vbt's way to create an array matching the
  input shape — use this rather than `pd.DataFrame(...)` constructors.
- Multiple outputs return as a tuple on the last expression line.

## Canonical example: simple WMA indicator

Pattern from `api/indicators/factory`:

```python
WMA = vbt.IF(
    class_name='WMA',
    input_names=['close'],
    param_names=['window'],
    output_names=['wma']
).from_expr("wm_mean_nb(close, window)")

wma = WMA.run(price, window=[2, 3])
wma.wma                    # DataFrame with 2 columns (one per window)
```

Note that `wm_mean_nb` is a vbt-exported Numba function; the expression
can call any function in the vbt namespace directly.

## Stop-loss / take-profit parameter prep

Pattern from `documentation/portfolio/from-signals`:

```python
StopOrderPrep = vbt.IF.from_expr("""
    sl_stop = @p_sl_mult * @in_atr / @in_close
    tp_stop = @p_tp_mult * @in_atr / @in_close
    sl_stop, tp_stop
""")

stop_order_prep = StopOrderPrep.run(
    close=sub_data.close,
    atr=sub_atr,
    sl_mult=[np.nan, 1],
    tp_mult=[np.nan, 1],
    param_product=True,
)
```

Use this pattern when you need ATR-scaled stops — the resulting
stop-arrays plug straight into `Portfolio.from_signals(sl_stop=..., tp_stop=...)`.

## `with_custom_func` escape hatch

Use when you need full control over parameter iteration (e.g., to
call an external library that's not thread-safe inside the Numba
kernel):

```python
@njit
def apply_func_nb(i, ts1, ts2, p1, p2, arg1, arg2):
    return ts1 * p1[i] + arg1, ts2 * p2[i] + arg2

@njit
def custom_func(ts1, ts2, p1, p2, arg1, arg2):
    return vbt.base.combining.apply_and_concat_multiple_nb(
        len(p1), apply_func_nb, ts1, ts2, p1, p2, arg1, arg2)

MyInd = vbt.IF(
    input_names=['ts1', 'ts2'],
    param_names=['p1', 'p2'],
    output_names=['o1', 'o2']
).with_custom_func(custom_func, var_args=True, arg2=200)

myInd = MyInd.run(price, price * 2, [1, 2], [3, 4], 100)
```

Key points:
- `custom_func` gets the raw param arrays `p1, p2, ...` and iterates
  itself via `apply_and_concat_multiple_nb`.
- `var_args=True` means extra positional args after params are forwarded.
- Fixed keyword args (like `arg2=200`) are baked in at construction.

## Running with cached results

Every `.run(...)` call is cached by default — calling with the same
params returns the cached result instantly. Override with
`cache=False` during development if you're iterating on the expression.

## When NOT to use IndicatorFactory

- Simple one-off calculations (use `.vbt.` accessors directly).
- Indicators that already exist as first-class vbt classes (use those
  instead — they're more thoroughly tested).
- Logic that genuinely needs Python per-bar state machines (use
  `Portfolio.from_order_func` instead; `IF` is signal-layer).

## Source

- Primary: Context7 `/llmstxt/vectorbt_pro_pvt_4f8d7c01_llms-full_txt`
- Live dump: `~/Dev/neuro-link/01-raw/vectorbt-pro/llms-full.txt`
  (fetched 2026-04-20 from user's `pvt_16ebf9ef` URL, 18MB)
- Cross-reference: `tutorials/signal-development/generation`,
  `tutorials/pairs-trading`, `api/indicators/factory`,
  `documentation/portfolio/from-signals`
