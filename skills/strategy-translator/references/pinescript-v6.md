---
title: Pine Script v6 — translation reference
domain: software-engineering
confidence: high
last_updated: 2026-04-19
---

# Pine Script v6 translation reference

Everything you need when Pine Script v6 is the source or target in a
translation. Consolidates the pitfall catalogues from two validated
translation grading sessions (Pine→Python avg 13.9/15, Pine→C++ avg 14/15)
plus the tooling workflow that produced them.

## Canonical Pine resources

Before emitting or interpreting Pine, consult these curated sources.
They're authoritative; do not rely on training-data recall for Pine
function signatures or language features.

| Resource | Where | Use for |
|---|---|---|
| Pine v6 official user manual | <https://www.tradingview.com/pine-script-docs/welcome/> | language features, syntax changes, migration notes |
| Pine v6 language reference | <https://www.tradingview.com/pine-script-reference/v6/> | exact function signatures, parameter defaults, return types |
| `pine-lsp` via Serena | stdio LSP, already registered | hover, go-to-def, find-references on `.pine` files; preferred over regex parsing |
| `pine-validate` CLI | ships with `folknor/pine-tools` fork | one-shot compiler check on emitted Pine (TradingView-compatible) |
| Auto-Quant vault awesome-pinescript index | `/Library/Obsidian-Vault/Auto-Quant/_Awesome-Resources/awesome-pinescript.md` | canonical list of indicators, strategies, libraries, tools, automated-execution endpoints — **check here first** for "where is the reference implementation of X" before rewriting from scratch |
| Pine Coders publications | <https://www.tradingview.com/u/PineCoders/#published-scripts> | vetted reference implementations by the Pine-Coders community |
| Pine Script chat room | <https://www.tradingview.com/chat/#BfmVowG1TZkKO235> | live community for edge cases / undocumented behaviour |

The awesome-pinescript index covers: indicators (by category), strategies,
math libraries, tools (stopwatches, filter-response analyzers, signal
generators), Pine libraries, and automated-execution bridges
(PSStrategyX, open-source webhook bots, closed-source services like
3Commas / Alertatron / Capitalise.ai). When a translation target mentions
live execution or third-party automation, consult this file first.

## Tooling

When Pine is in play, use these three tools in this order of preference:

1. **`pine-lsp` (from `folknor/pine-tools`)** — full LSP over stdio. Drive
   through Serena. Use `get_symbols_overview` to enumerate user-defined
   functions, `find_symbol` to locate `indicator()`/`strategy()` declarations,
   `find_referencing_symbols` to trace helper use, hover for type info on
   every identifier. This is the primary path for extracting a Pine
   source's behavioral contract without hand-parsing.
2. **`pine-validate` CLI** (same repo) — run on every Pine v6 file you emit
   as a target. Non-zero exit = TradingView's compiler would reject it; do
   not return invalid Pine to the user.
3. **`tree-sitter-pine` (from `zelosleone/pinescript-vsc-server-rust`)** —
   raw concrete syntax tree. Reach for this only when you need to walk
   the tree programmatically (e.g. enumerate every `ta.*` call with args
   to generate a mechanical vectorbt translation). `pine-lsp` semantic
   views cover almost all navigation needs; tree-sitter is the escape
   hatch when you need the literal syntax tree.

If none of the three is available in the environment, say so in your reply
and fall back to careful manual reading. **Do not silently degrade to regex
pattern-matching and claim the same rigor.**

## Behavioral contract: what to capture from the source

Before emitting anything, write down:

- **Instruments & timeframes** — what ticker, what bar size, any MTF
  `request.security` calls and their lookahead mode (`lookahead_off` vs
  `lookahead_on`).
- **Indicators** — every `ta.*` call with its parameters. Note whether it
  uses Wilder smoothing (`ta.rsi`, `ta.atr`, `ta.rma`) or standard EMA
  (`ta.ema`). See Pitfall 1.
- **Entry & exit conditions** — the boolean expressions. Note every
  `ta.crossover`/`ta.crossunder` and every `[1]` lag operator. See Pitfalls 3–4.
- **Position sizing & risk rules** — `strategy.entry(qty=...)`,
  `strategy.exit` stop/limit, `strategy.risk.*`.
- **Fill convention** — the source's assumed fill point (signal-bar close
  vs next-bar open). Default Pine strategies fill on the *next bar's open*
  when `process_orders_on_close=false` (the default); on signal-bar close
  when `process_orders_on_close=true`. See Pitfall 5.
- **Warmup** — how many bars until the first signal is valid? Wilder
  indicators need `length` seed bars before they're reliable.

## Pitfall catalogue

### Pitfall 1 — Wilder smoothing vs standard EMA

The single most common silent-drift bug. **Name the exact Pine function
and map it to the exact target equivalent.** Glossing as "EMA" is
where translations go wrong.

| Pine function | Formula | pandas `.ewm` equivalent |
|---|---|---|
| `ta.ema(close, n)` | α = 2/(n+1) — standard EMA | `close.ewm(span=n, adjust=False).mean()` |
| `ta.rma(close, n)` | α = 1/n — Wilder | `close.ewm(alpha=1.0/n, adjust=False).mean()` |
| `ta.rsi(close, n)` | uses `ta.rma` internally on up/down deltas | Wilder smoothing of deltas, not price |
| `ta.atr(n)` | uses `ta.rma` internally on true range | Wilder smoothing of TR, not price |
| `ta.sma(close, n)` | simple mean | `close.rolling(n).mean()` |
| `ta.wma(close, n)` | weighted mean (linear weights) | custom rolling apply |

**`ta.ema` is NOT Wilder.** `ta.rma` is. RSI and ATR use `ta.rma`
internally. If the translation's diff says "Pine's ta.ema (Wilder
smoothing)", that's wrong and must be corrected — even if the
EMITTED code happens to be right, the mental model is broken and the
next strategy port will break.

**Python:**
```python
# Standard EMA (matches ta.ema)
close.ewm(span=length, adjust=False).mean()

# Wilder (matches ta.rsi, ta.atr, ta.rma)
close.ewm(alpha=1.0 / length, adjust=False).mean()
```
Always pass `adjust=False` — the default pandas behaviour uses a bias-corrected
weighting that does not match Pine's recursion.

**C++:**
```cpp
const double alpha_ema    = 2.0 / (static_cast<double>(length) + 1.0);
const double alpha_wilder = 1.0 / static_cast<double>(length);
```
Always `static_cast<double>(length)` before the divide — integer division
silently zeroes alpha for `length >= 2`.

### Pitfall 2 — Biased vs sample standard deviation

Pine's `ta.stdev` is the **biased** (population) stdev: divisor `N`.
Pandas' `.std()` defaults to **sample** stdev: divisor `N-1`. Bollinger
Bands and z-score indicators come out silently wider in Python unless you
pass `ddof=0`:

```python
close.rolling(length).std(ddof=0)  # matches Pine
```

In C++, Welford's online algorithm with divisor `N` gives the biased
estimator directly.

### Pitfall 3 — Look-ahead in self-referential channels

Donchian, swing-high/low, chandelier exits — anything using a rolling
extreme as a breakout level — must compute the level from **prior** bars
only. Pine writes `ta.highest(high, length)[1]` (the `[1]` is a one-bar lag).

**Wrong** (peeks at the breakout bar, signal never fires):
```python
upper = high.rolling(length).max()
```

**Right:**
```python
upper = high.rolling(length).max().shift(1)
```

The bug produces silently-flat backtests, not exceptions. In C++, use a
circular buffer of the last `length` highs/lows and update it *after*
computing the breakout decision for the current bar.

### Pitfall 3b — Pre-lagged indicators in crossovers — NEVER shift again

When Pine writes `ta.crossover(close, upper[1])`, the `[1]` ALREADY
applied the lag to `upper`. The crossover is literally:
`close > upper[1]  AND  close[1] <= upper[2]`. The *both sides* of the
`<=` compare at the SAME lag — only `close` advances one step
"backwards"; `upper` stays on the same pre-lagged series.

**The lethal translation bug:** shifting the already-lagged series
AGAIN inside the prior-bar comparison.

```python
# Pine: ta.crossover(close, upper[1])
# meaning: close crosses above the PRIOR bar's upper band

upper_prev = upper.shift(1)            # apply Pine's [1]  ← correct

# CORRECT — compare prior close vs same pre-lagged upper
cross_up = (close > upper_prev) & (close.shift(1) <= upper_prev)

# WRONG — double-shifts upper, produces signal one bar late
cross_up = (close > upper_prev) & (close.shift(1) <= upper_prev.shift(1))
```

Rule: **the reference level inside the prior-bar half of the crossover
check is the SAME series, NOT a further-shifted copy.** The only
`.shift(1)` that belongs inside the crossover expression is on the
value being compared (here: `close`), not on the reference (here:
`upper_prev`).

Same rule for `ta.crossover(close, basis)` where `basis` is
CURRENT-bar (not pre-lagged): do **not** shift basis at all in the
crossover — compare `close > basis` AND `close.shift(1) <= basis.shift(1)`
where both `.shift(1)`s apply symmetrically to both sides.

Decision table:

| Pine expression | pandas `cross_up` |
|---|---|
| `ta.crossover(a, b)` (both current-bar) | `(a > b) & (a.shift(1) <= b.shift(1))` |
| `ta.crossover(a, b[1])` (b pre-lagged) | `b_prev = b.shift(1); (a > b_prev) & (a.shift(1) <= b_prev)` |
| `ta.crossover(a[1], b)` (a pre-lagged) | `a_prev = a.shift(1); (a_prev > b) & (a_prev.shift(1) <= b.shift(1))` |

### Pitfall 4 — Crossover state requires the prior bar

Pine's `ta.crossover(a, b)` fires only on the bar where `a` first exceeds
`b`, not on every bar where `a > b`:

**Python:**
```python
cross_up = (a > b) & (a.shift(1) <= b.shift(1))
cross_dn = (a < b) & (a.shift(1) >= b.shift(1))
```
In vectorbt, prefer `close.vbt.crossed_above(upper)` — it does the lag
bookkeeping for you.

**C++** — store both prior values, update them **after** the comparison:
```cpp
const bool cross_up = (macd > sig) && (prev_macd <= prev_signal);
const bool cross_dn = (macd < sig) && (prev_macd >= prev_signal);
// update prev_macd and prev_signal AFTER using them
```
Updating either prior before the comparison eats the crossover bar and
turns a two-trade-a-year strategy into a two-hundred-trade-a-year one.

### Pitfall 5 — Fill-timing convention

Pine `strategy.entry` with default `process_orders_on_close=false` fills
on the **next bar's open**. vectorbt's `Portfolio.from_signals` also fills
on the next bar's open — but basic pandas loops often assume signal-bar
close. State the convention explicitly.

Safe pandas convention: `position.shift(1) * returns` — model entries as
effective from the bar after the signal. Document this in a comment.

Nautilus event-driven engines fill on bar close or next-bar open depending
on `BarSpec` and order type; be explicit in the translation's diff.

### Pitfall 6 — RSI divide-by-zero

When average loss is zero, Pine's `ta.rsi` returns 100. Naive
`100 - 100 / (1 + rs)` produces NaN. Guard:

```cpp
if (avg_down_ == 0.0) return 100.0;
const double rs = avg_up_ / avg_down_;
return 100.0 - (100.0 / (1.0 + rs));
```

### Pitfall 7 — MACD signal-line composition

Pine's MACD signal line is the EMA of the **MACD line**, not of price:

```cpp
const double macd = fast.update(close) - slow.update(close);
const double sig  = signal.update(macd);  // EMA of macd, NOT of close
```

Feeding `close` into the signal EMA produces a chart that looks plausible
but never reaches correct crossing points.

### Pitfall 8 — Wilder seed

Wilder RSI/ATR seed the recursion with a simple mean of the first `length`
deltas, then switch to recursive smoothing. Failing to gate on the seed
produces a noisy RSI for the first 14 bars. Implement explicitly — do not
rely on library defaults matching Pine.

## Target-specific notes

### Python / pandas / vectorbt

- Always `adjust=False` on `.ewm`. **This is non-negotiable.** pandas'
  `.ewm` default is `adjust=True` — a bias-corrected weighting that
  diverges from Pine's recursive EMA (`value = alpha*x + (1-alpha)*prev`).
  The first ~20 bars drift meaningfully, and the divergence doesn't
  damp out cleanly. vectorbt's `vbt.MA(ewm=True)` and `vbt.IF.run()`
  wrappers inherit pandas' default; do **not** assume they match Pine.
  Pass `adjust=False` (or wrap your own `.ewm`) *and* verify against a
  Pine reference (see validation recipe below).
- Always `ddof=0` on `.rolling().std()` when matching Pine.
- Prefer `.vbt.crossed_above` / `.vbt.crossed_below` over hand-rolled
  `(a > b) & (a.shift(1) <= b.shift(1))`.
- vectorbt renames some Pine parameters: Bollinger Bands' `mult` → `alpha`;
  the mid-band is `bb.middle`, not `bb.basis`.
- **Sizing — "100% of equity" recipe.** Pine's
  `default_qty_type=strategy.percent_of_equity, default_qty_value=100`
  maps to vectorbt as `size=1.0, size_type='percent'` — **not**
  `size=np.inf`, **not** `size=100`. `np.inf` is a max-quantity sentinel,
  not a percent; using it with `size_type='percent'` is a misuse that
  some vectorbt versions accept silently and others reject at runtime.
  vectorbt 0.26+ uses fractional percent semantics (0.0–1.0); earlier
  versions used 0–100. State which convention the translation assumes
  in the diff so the reader can confirm against their installed version.
- Always pass `freq=` to `Portfolio.from_signals` so annualized stats are
  correct (`freq=close.index.inferred_freq or '1D'`).
- Always pass `fees=` and `slippage=` explicitly, even when zero — it
  documents the assumption.
- Idiomatic vectorized position state:
  ```python
  position = (
      pd.Series(np.where(entry, 1, np.where(exit, 0, np.nan)),
                index=close.index)
      .ffill().fillna(0).astype('int8')
  )
  ```

#### vectorbt validation recipe

Before returning a vectorbt translation, verify numeric equivalence
against a Pine reference. vectorbt accumulates small divergences from
Pine very quickly (Wilder seed, `.ewm` adjust default, stdev ddof); a
"looks fine" plot can hide cumulative drift that ruins backtests.

1. On TradingView, run the source Pine script on a known symbol/range.
   Export the first 200 bars of each computed series (EMAs, RSI, bands,
   etc.) via the Data Window copy or a CSV exporter. Save as
   `pine_reference.csv` with one column per series, index = bar time.
2. Run the vectorbt translation on the *same* OHLC slice.
3. Compare elementwise:
   ```python
   diff = (emitted - pine_reference).abs()
   # Allow a small tolerance on the warmup bars (Wilder seeds for the
   # first `length` bars). Past that, divergence means a translation bug.
   warmup = length  # or 0 for non-Wilder indicators
   max_abs_after_warmup = diff.iloc[warmup:].max()
   assert max_abs_after_warmup < 1e-6, (
       f"max abs diff after warmup {max_abs_after_warmup:.2e} — "
       "check adjust=False, ddof=0, Wilder seed, crossover lag"
   )
   ```
4. Tolerances beyond the warmup window almost always mean: missing
   `adjust=False`, missing `ddof=0`, or an off-by-one in the crossover
   lag. Diagnose before returning.

In the translation's `### Diff vs source` section, explicitly state
whether this recipe was run. If the user cannot provide a Pine reference,
say so — do not claim numeric equivalence without verification.

### C++ (HFT / embedded / exchange-collocated)

- Mental model: streaming, not vectorized. Each indicator is a class with
  `on_bar(...)` that returns the updated value and stores only the
  recursive state needed (last EMA, last RSI, prior crossover values).
  **No full-history buffers on the hot path.**
- Compose larger indicators from small streaming primitives
  (`Ema`, `Rma`, `RollingMax`). This is the pattern Nautilus and most
  production C++ engines use.
- `std::numeric_limits<double>::quiet_NaN()` as a not-ready sentinel is
  fast but leaks NaN downstream. For library-quality code, prefer
  `std::optional<double>` for the first read; the cost disappears once
  warmed up.
- Only translate to C++ when latency is in the order-flow critical path,
  when embedding in an exchange gateway, or when memory/cache layout
  matters more than developer ergonomics. For research and sweeps, stay
  in Python/vectorbt. For event-driven backtests with realistic fills,
  use NautilusTrader.

### NautilusTrader (Python or Rust)

- Prefer built-in Nautilus indicators (`ExponentialMovingAverage`, etc.)
  over hand-rolled ones — they're already bar-vs-tick aware.
- `BarSpec(step=1, aggregation=BarAggregation.MINUTE, price_type=PriceType.LAST)`
  — be explicit about aggregation and price type.
- Strategy `on_bar(bar)` is the analogue of Pine's per-bar evaluation, but
  the bar has already closed. Fill timing depends on `OrderType` and
  `TimeInForce` — state what you assume.

## Emitting Pine as a target

1. Write the Pine source in a single fenced block.
2. Run `pine-validate <file.pine>` — require exit code 0.
3. If validation fails, read the compiler errors, fix, re-validate. Do
   not return invalid Pine to the user.
4. In the `### Diff vs source` section, note any semantic differences
   the target's Pine idioms introduce (e.g. if you moved a condition
   from event-driven to bar-close, say so).

## Translation workflow checklist

1. Drive `pine-lsp` via Serena to extract symbols, types, and references
   from the source (if Pine is the source).
2. Write down the behavioral contract (indicators, entries/exits, sizing,
   fill convention, warmup).
3. Identify every Pine builtin used and look up its smoothing / biased /
   lag rules (Pitfalls 1, 2, 3).
4. Emit the translation in one fenced block.
5. Add a `### Diff vs source` section listing each semantic difference
   and *why*.
6. State the fill-timing convention explicitly.
7. If emitting Pine, run `pine-validate`.

## Sources

- Pine→Python translation grading session, 2026-04-16 (5 indicators,
  avg 13.9/15). Worktree: `compassionate-franklin-2583d0/.planning/translations/`.
- Pine→C++ translation grading session, 2026-04-17 (2 indicators,
  avg 14/15). Same worktree.
- Vault sources:
  - `neuro-link-vault-content/02-KB-main/swe/pine-to-python-translation.md`
  - `neuro-link-vault-content/02-KB-main/swe/pine-to-cpp-translation.md`
