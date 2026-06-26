---
title: VectorBT Pro — translation reference
domain: software-engineering
confidence: high
last_updated: 2026-04-20
---

# VectorBT Pro reference

Dedicated target guidance for `vectorbtpro` (distinct from vanilla
`vectorbt`). The two libraries have different APIs, different defaults,
and different recommended idioms — translations must not conflate them.

## Live-lookup gate (mandatory)

**Before emitting any VBT Pro function call, verify the current API via
Context7.** VBT Pro ships new releases frequently; signatures and
defaults drift.

Primary source (Context7):
- Library ID: `/llmstxt/vectorbt_pro_pvt_16ebf9ef_llms-full_txt`
  (the `llms-full` corpus — 13,000+ snippets, highest fidelity)
- Fallback: `/websites/vectorbt_pro` (392 snippets, lighter coverage)

Invoke via `docs-dual-lookup` or directly:
```
mcp__context7__query-docs
  libraryId: /llmstxt/vectorbt_pro_pvt_16ebf9ef_llms-full_txt
  query: "<specific function or pattern you are about to emit>"
```

In the translation's `### Diff vs source` section, **cite the Context7
snippet heading** that confirmed each non-trivial API usage. A
translation with zero citations is a translation you have not verified.

## Vault-curated knowledge (conditional)

If `neuro-link-recursive` is reachable, also query the vault:
```
mcp__neuro-link-recursive__nlr_wiki_search
  query: "vectorbt pro <the specific concern>"
```
Vault entries under `02-KB-main/` supersede the bullets below when
present — they're curated by the user and reflect project-specific
conventions. If the vault returns a page, cite its title + confidence.

## The critical insight: NB indicators vs `.ewm()`

**Use VBT Pro's NB-level indicators before hand-rolling pandas calls.**

VBT Pro's numba-compiled indicators default to Pine-compatible
parameters (verified via Context7 `/llmstxt/vectorbt_pro_*`):

| Function | Key default |
|---|---|
| `bbands_1d_nb(close, window, wtype=0, alpha=2.0, adjust=False, ddof=0)` | `adjust=False, ddof=0` ← **already Pine-compatible** |
| `bbands_nb` (2D) | same defaults |
| `vbt.IF.run()` wrappers | inherit from the underlying NB function |
| Raw `pandas.DataFrame.ewm()` | defaults `adjust=True` ← **diverges from Pine** |

**Translation rule:** Prefer `vbt.IndicatorFactory.list_indicators()` to
find a Pro-native indicator first. If one exists, use it — its defaults
are usually Pine-compatible. Only fall through to hand-rolled `.ewm()`
when no Pro equivalent exists, and in that case **pass `adjust=False`
explicitly**.

## Sizing — "100% of equity"

Pine's `default_qty_type=strategy.percent_of_equity, default_qty_value=100`
maps to:

```python
pf = vbt.Portfolio.from_signals(
    close,
    entries=entries,
    exits=exits,
    size=1.0,                    # fractional (NOT 100, NOT np.inf)
    size_type="percent",         # or "valuepercent" (see below)
    fees=0.0,                    # state explicitly
    slippage=0.0,                # state explicitly
    freq=close.index.inferred_freq or "1D",
)
```

**Size-type distinctions** (verify via Context7 for your installed
version):

- `size_type="percent"` — size is interpreted as a fraction of the
  current target (cash or asset). VBT Pro 0.26+ uses 0.0–1.0 fractional.
  Earlier releases used 0–100. State the assumed version.
- `size_type="valuepercent"` — size is the fraction of total portfolio
  *value* (asset + cash). Use this for "asset allocation as a fraction
  of portfolio" semantics.
- `size_type="value"` — size is an absolute $ amount (NOT a percent).
  `size=1, size_type="value"` puts **$1** per trade, not 100%.
- `size=np.inf` with `size_type="percent"` is **not** "100%" — `np.inf`
  is a sentinel meaning "max-available", interpreted differently per
  size_type and version.

When in doubt, verify the exact semantics via Context7:
```
query: "Portfolio.from_signals size_type percent valuepercent semantics 0-1 vs 0-100"
```

## Wilder smoothing (ATR, RSI)

Pine's `ta.atr`, `ta.rsi`, `ta.rma` use Wilder smoothing
(`alpha = 1/length`). VBT Pro's `atr_nb` and `rsi_nb` use Wilder by
default — verify per function:

```python
# Pro's ATR (Wilder by default — matches Pine)
atr = vbt.ATR.run(high, low, close, window=14).atr

# Pro's RSI (Wilder by default)
rsi = vbt.RSI.run(close, window=14).rsi
```

Do **not** pass `ewm_kwargs={"adjust": True}` or swap to a standard-EMA
variant without stating why in the diff. Most translations should
leave these as-is.

## Bollinger Bands — use `bb.middle` not `bb.basis`

```python
bb = vbt.BBANDS.run(close, window=20, alpha=2.0)
basis = bb.middle    # NOT bb.basis — that attribute does not exist
upper = bb.upper
lower = bb.lower
```

## Crossover detection

Prefer the `.vbt.crossed_above` / `.vbt.crossed_below` accessors over
hand-rolling `(a > b) & (a.shift(1) <= b.shift(1))` — the accessors
handle the lag bookkeeping and match Pine's `ta.crossover` semantics:

```python
long_signal = close.vbt.crossed_above(upper.shift(1))  # still shift the
                                                         # channel to avoid
                                                         # look-ahead
```

## Look-ahead prevention

Donchian, Bollinger, Keltner, and any channel derived from the
current bar's own high/low must shift the channel by one bar before
comparing the current close — otherwise the signal never fires
(the close is always within its own channel).

```python
upper_prev = upper.shift(1)
lower_prev = lower.shift(1)
long_signal = close.vbt.crossed_above(upper_prev)
```

## Fill timing — `from_signals` fills at CLOSE by default

A common translation bug: claiming `Portfolio.from_signals` fills at
the next bar's open. **It doesn't.** The default fill price is the
**close** of the signal bar itself.

To actually emulate Pine's default `process_orders_on_close=false`
(next-bar open execution), do ONE of:

```python
# Option A: pass an open-price series as the execution price
pf = vbt.Portfolio.from_signals(
    close,
    entries=entries,
    exits=exits,
    price=open_next,   # execute at the NEXT bar's open
    size=1.0,
    size_type="percent",
    fees=0.0,
    slippage=0.0,
    freq=close.index.inferred_freq or "1D",
)

# Option B: shift signals forward by one bar, accept close-fill
pf = vbt.Portfolio.from_signals(
    close,
    entries=entries.shift(1).fillna(False),
    exits=exits.shift(1).fillna(False),
    # default price is close; fill happens on the bar AFTER signal
    size=1.0, size_type="percent", fees=0.0, slippage=0.0,
    freq=close.index.inferred_freq or "1D",
)
```

Note on **already-lagged signals**: if your entry/exit conditions use
pre-shifted indicators (`upper_prev = upper.shift(1)` then
`close.vbt.crossed_above(upper_prev)`), the signal already fires on
the correct "breakout bar". Passing `price=open_next` (option A)
gives the cleanest next-bar-open match without double-shifting. Option
B shifts signals AGAIN and produces a two-bar lag — a common bug.

Decision tree:

| Indicator uses | Want fill at | Signal handling | Execution price |
|---|---|---|---|
| current bar | same bar close | raw signals | default (close) |
| current bar | next bar open | raw signals | `price=open_next` |
| pre-lagged `[1]` | same bar close | raw signals (already correct bar) | default (close) |
| pre-lagged `[1]` | next bar open | raw signals | `price=open_next` |

**Never:** shift signals a second time when the indicator already has
`[1]` applied — this pushes fills two bars out.

State the chosen convention in the Diff vs source section. If you
passed `price=open_next`, say so. If you accepted close-fill, say so.

## Validation recipe

Before returning a VBT Pro translation, verify numeric equivalence
against a Pine reference (see `references/pinescript-v6.md` "vectorbt
validation recipe" section). VBT Pro's NB indicators reduce divergence
at the indicator level, but crossover logic + sizing + fill timing
still require comparison.

## When to reach for vanilla `vectorbt` instead

VBT Pro is paid/private. Translations for users on the open-source
`vectorbt` should use `import vectorbt as vbt` and follow
`references/pinescript-v6.md`'s "Python / pandas / vectorbt" section
(notably: `.ewm(adjust=False)` is **not** the default there). State
in the translation's preamble which variant is assumed.

## Required env for live lookups

- `CONTEXT7_API_KEY` — higher rate limits for Context7 queries (optional
  but recommended for dense translation runs). Sourced from
  `$HOME/hyperfrequency/.env` by the shakedown container.
- `GITHUB_TOKEN` — needed for DeepWiki queries via
  `/deep-tool-wiki` (Devin-backed), and for cloning private VBT Pro
  repos if present in the user's workspace. Export in same .env file.

## Anti-patterns specific to VBT Pro

- **Don't hand-roll `.ewm()` when an NB indicator exists.** Pro-level
  NB indicators already default to Pine-compatible params; hand-rolled
  code bypasses those defaults.
- **Don't use `bb.basis`** — it's a vanilla-vectorbt attribute name that
  does not exist in Pro. Use `bb.middle`.
- **Don't assume `size=np.inf` means 100%** — it's a max-available
  sentinel, version-dependent. Use `size=1.0, size_type='percent'`.
- **Don't conflate vanilla `vectorbt` and `vectorbtpro`** in the same
  translation. State the variant assumed.
- **Don't emit without a Context7 citation.** The shakedown consortium
  judge penalizes translations that claim API behavior without evidence.

## Source

- Primary: Context7 `/llmstxt/vectorbt_pro_pvt_16ebf9ef_llms-full_txt`
  (13932 code snippets, benchmark score 90.4, high reputation)
- Secondary: Context7 `/websites/vectorbt_pro` (392 snippets)
- Validation findings: shakedown judge consortium runs in
  `~/hyperfrequency/neuro-link/dev/shakedown/reports/cycle5b-*`
