---
name: vectorbt
description: >
  Vectorized backtest AUTHORING + analysis with vectorbt / vectorbt-pro:
  IndicatorFactory indicators, Portfolio.from_signals / from_orders /
  from_order_func, broadcast parameter sweeps, Splitter / CVSplitter
  walk-forward, and Data loaders (Binance/CCXT/YF/Polygon). Use to write
  or debug a vectorbt backtest. Trigger even without "vectorbt" on
  "backtest this strategy" (vectorized), "parameter sweep",
  "IndicatorFactory", "from_signals", "PortfolioOptimizer", "Splitter
  walk-forward", or numpy/pandas backtest infra. For the event-driven
  backtest ENGINE / live / Hyperliquid use nautilus-trader; for porting /
  "Rust or Pine version" use strategy-translator; for walk-forward EPOCH
  / WFE / overfitting-epoch use adaptive-wfo-epoch; for "is this Sharpe
  real" / PBO / purged CV use model-evaluation; for tearsheet / MAE /
  leverage use tearsheet-generator (quantstats-rs); for comparing to an
  Optuna baseline or verifying a backtest use strategy-verify; for
  VPIN/OFI/L2 order-flow use microstructure-analyst.
version: "1.0.0"
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Skill, Agent
license: "Apache-2.0 + Commons Clause (vectorbt); proprietary (vectorbt-pro)"
metadata:
    skill-author: HyperFrequency
    skill-domain: trading
    upstream: https://vectorbt.pro/
---

# vectorbt / vectorbt-pro

This skill covers the **authoring and analysis** of vectorbt backtests —
distinct from `/strategy-translator` which handles cross-framework ports.
If the user hands you a Pine script to translate, delegate. If they hand
you a strategy idea / market thesis / research paper and ask for a
vectorbt implementation, that's this skill.

Both vectorbt (vanilla, Apache 2 + Commons Clause) and vectorbt-pro
(paid, proprietary) are covered. State which variant you assume in the
first line of output — their APIs differ (see `references/pro-vs-vanilla.md`).

## When to use

- The user hands you a strategy idea, market thesis, or research-paper
  signal and asks for a runnable **vectorbt backtest** from scratch.
- They want a **parameter sweep / grid search** over indicator windows,
  stops, or thresholds via array broadcasting.
- They need a **custom indicator** built with `IndicatorFactory`
  (`from_expr`, `with_apply_func`, or `with_custom_func`).
- They want **Splitter / CVSplitter walk-forward** mechanics wired
  inside vectorbt (the vbt machinery — not epoch-selection policy).
- They construct a portfolio via `Portfolio.from_signals` /
  `from_orders` / `from_order_func` and read `pf.stats()` / `pf.plot()`.
- A backtest "looks wrong" (too many signals, suspiciously smooth
  equity) and needs the look-ahead / re-firing sanity checks.

Hand off when the request is an event-driven engine, a cross-framework
port, walk-forward EPOCH selection, PBO/Sharpe-realism auditing, a
standalone tearsheet, an Optuna-baseline comparison, or microstructure
order-flow indicators — see the cross-link table below.

## Mental model

vectorbt is **NumPy-first**. Every input — prices, signals, sizes, fees
— is a 2D array where rows are time steps and columns are strategy
instances (parameter combinations, universe constituents, or both).
When you run `vbt.MA.run(price, window=[10, 20, 50])` on a single price
series, you get a DataFrame with three columns, one per window. When
you compute `fast.ma_crossed_above(slow)`, the comparison broadcasts
across all column pairs and returns another DataFrame of boolean
masks — one entry/exit pair per parameter combo. This flows directly
into `Portfolio.from_signals`, which runs the entire simulation in one
compiled Numba loop.

No Python per-bar iteration. You orchestrate arrays; Numba does the
work. This is the whole game — every idiom below follows from it.

## MANDATORY live lookups before emitting code

**Preference order**, best source first:

1. **VBT Pro's own MCP server** (`vectorbtpro.mcp_server`) — if
   installed, query via `mcp__vectorbt-pro__search`,
   `mcp__vectorbt-pro__get_source`, `mcp__vectorbt-pro__run_code`.
   This is the INSTALLED version's actual API — zero version drift.
   See `references/ai-workflows.md` for setup.
2. **Context7 live doc queries** — covers vectorbt-pro + vanilla +
   llms-full corpus. Second-best; snapshot may lag the installed version.
3. **Static reference files** in this skill — last resort for patterns
   that don't change between releases (mental model, pitfall catalogue).

vectorbt releases frequently; defaults drift. Before emitting any
non-trivial call, verify via the best available source above and cite
the snippet heading in your Diff vs spec section.

| Library | Context7 ID | Coverage |
|---|---|---|
| vectorbt-pro (llms-full corpus) | `/llmstxt/vectorbt_pro_pvt_4f8d7c01_llms-full_txt` | 13,932 snippets — use this by default |
| vectorbt-pro (website docs) | `/websites/vectorbt_pro` | 392 snippets — lighter fallback |
| vectorbt (vanilla) | `/polakowo/vectorbt` | 1,407 snippets |
| vectorbt (vanilla website) | `/websites/vectorbt_dev` | 5,232 snippets |

Also consult the vault:
```
mcp__neuro-link-recursive__nlr_wiki_search  query: "vectorbt <specific concern>"
```
Vault hits ≥ 0.7 confidence supersede static guidance. If the vault
surfaces a project-specific convention, use it.

## Standard authoring workflow

Follow these 6 steps. Skipping steps is how bugs appear.

### 1. State the variant + strategy intent in one line

"vectorbt-pro: long-only EMA cross on BTC/USDT daily, 100% of equity
per trade, fees 0.1%, slippage 0.05%." One line — ambiguity elsewhere
blocks downstream decisions.

### 2. Load data

Prefer VBT's `Data` loaders over yfinance directly — they cache,
reshape, and handle multi-symbol uniformly.

| Source | Class | Notes |
|---|---|---|
| Crypto (binance) | `vbt.BinanceData` | free, needs API key for high rate limits |
| Crypto (ccxt-backed) | `vbt.CCXTData` | 100+ exchanges via ccxt |
| US equities / ETFs | `vbt.YFData` | yfinance wrapper; cheap, inexact |
| Institutional | `vbt.PolygonData` (pro) | needs polygon.io API key |
| Alpaca | `vbt.AlpacaData` (pro) | needs alpaca creds |
| Local file | `vbt.HDFData` / `vbt.CSVData` / `vbt.ParquetData` | deterministic for reviewable backtests |

**For reviewable/reproducible backtests, prefer a cached local file.**
Live downloads drift; a frozen parquet does not. State the cache policy
in the first line of the emitted code as a comment.

### 3. Build signals / indicators

Prefer VBT's built-in indicators and NB primitives over hand-rolled
pandas. VBT Pro NB indicators (`bbands_1d_nb`, `atr_nb`, `rsi_nb`)
default to Pine-compatible params (`adjust=False`, `ddof=0`).
Hand-rolled `.ewm()` inherits pandas' `adjust=True` default and
diverges. See `references/indicators.md`.

If no built-in fits, create one via `IndicatorFactory`. Don't write
ad-hoc numpy functions that bypass VBT's caching + broadcasting —
you'll lose the parameter-sweep benefit. See
`references/indicator-factory.md`.

### 4. Construct the portfolio

Pick the right constructor (in order of most-common to least):

| Constructor | Use for |
|---|---|
| `Portfolio.from_signals` | boolean entry/exit masks — 95% of cases |
| `Portfolio.from_orders` | explicit size arrays (you decide size per bar) |
| `Portfolio.from_holding` | buy-and-hold baseline |
| `Portfolio.from_order_func` | custom per-bar logic (Numba callbacks) — escape hatch |

**Canonical `from_signals` call** — never omit any of these params
without stating why:

```python
pf = vbt.Portfolio.from_signals(
    close,
    entries=entries,
    exits=exits,
    size=1.0,                       # fractional (not np.inf, not 100)
    size_type="percent",            # version-check: 0-1 in vbt 0.26+, 0-100 earlier
    fees=0.001,                     # 10 bps — state explicitly even if zero
    slippage=0.0005,                # 5 bps — same
    freq=close.index.inferred_freq or "1D",   # annualised stats depend on this
    init_cash=10_000,               # matters for % metrics
    # price=open_next,              # uncomment for next-bar-open fills
)
```

See `references/portfolio-constructors.md` for the other three
constructors, and `references/fill-timing.md` for the close-vs-next-bar-open
decision tree.

### 5. Analyze

Standard stats are on the portfolio object:

```python
pf.total_return()
pf.sharpe_ratio()
pf.max_drawdown()
pf.trades.stats()              # per-trade level
pf.positions.stats()           # per-position level
pf.stats()                     # kitchen sink, pandas Series
pf.returns_stats()             # returns-centric slice
pf.plot().show()               # interactive Plotly tearsheet
```

For reportable outputs, emit `pf.stats()` + `pf.plot()` save. See
`references/analysis.md` for custom metric patterns (rolling
drawdown windows, regime-conditioned returns, etc.).

### 6. Optimize (if the user asked for it)

| Method | Use for |
|---|---|
| Grid search via broadcasting | fast, exhaustive, <5 dims — just pass lists/ranges as params |
| `vbt.Splitter` / `vbt.CVSplitter` (pro) | walk-forward, purged k-fold |
| `PortfolioOptimizer` (pro) | target-weight / target-vol allocation |
| External (optuna, ray tune) | high-dim Bayesian / distributed sweeps |

See `references/optimization.md` for walk-forward recipes, overfit
diagnostics, and integration with optuna / ray.

## Validation — always verify the backtest isn't silently wrong

Before returning a backtest, run at least:

1. **Sanity on signal count** — print `entries.sum()`, `exits.sum()`.
   If the strategy should fire twice a year and shows 200 signals,
   you have a look-ahead or re-firing bug.
2. **No-trade sanity** — `pf.trades.count()` should match expectation.
3. **Equity curve shape** — if monotonically upward with no drawdowns,
   suspect look-ahead.
4. **Compare against reference if one exists** — if user provided a
   Pine script or published backtest, run the validation recipe from
   `references/validation.md` and cite the delta.

State which validations ran and their outcomes at the bottom of the
deliverable. Unvalidated backtests are flagged as incomplete by the
consortium judge.

## Anti-patterns

- **Don't write a Python for-loop over bars.** If you're iterating per
  bar, you're abandoning vectorbt's entire value prop. The escape hatch
  is `Portfolio.from_order_func` with Numba callbacks — not Python loops.
- **Don't hand-roll `.ewm()` when a VBT indicator exists.** VBT Pro NB
  indicators default to Pine-compatible params; pandas doesn't.
- **Don't claim `Portfolio.from_signals` fills at next-bar open by
  default.** Default is the signal bar's CLOSE. For next-bar open, pass
  `price=open_next` explicitly.
- **Don't use `size=np.inf` for "100% of equity".** It's a
  max-available sentinel with version-dependent behaviour. Use
  `size=1.0, size_type="percent"`.
- **Don't skip `freq=`** on `from_signals`. Annualised metrics depend
  on it; silent default is ambiguous.
- **Don't emit vectorbt-pro API without a Context7 citation.** The
  llms-full corpus is the authoritative source; VBT Pro ships new
  releases frequently.
- **Don't cache-bust needlessly.** VBT's `cached_property` and
  `cache_func` are load-bearing. Decorating with `@functools.lru_cache`
  or similar interferes.
- **Don't confuse vectorbt and vectorbtpro imports.** State which at
  the top. `vbt.BBANDS` in vanilla ≠ `vbt.BBANDS` in Pro on every
  param.

## Reference files

Read the relevant ones for the task at hand. All under `references/`:

- `pro-vs-vanilla.md` — API differences between `vectorbt` and `vectorbtpro`
- `indicators.md` — built-in indicators, parameter broadcasting, NB-level calls
- `indicator-factory.md` — custom indicators via `IndicatorFactory`
- `portfolio-constructors.md` — `from_signals` / `from_orders` / `from_holding` / `from_order_func` in depth
- `fill-timing.md` — close vs next-bar open decision tree, pre-lagged signal pitfalls
- `data-loading.md` — `BinanceData`, `CCXTData`, `YFData`, `PolygonData`, file-backed loaders, caching
- `analysis.md` — portfolio metrics, tearsheets, custom reporting
- `optimization.md` — grid search, walk-forward, CVSplitter, optuna/ray integration
- `validation.md` — verifying correctness before returning a backtest

Plus `examples/` for worked canonical patterns:
- `examples/signal-portfolio.md` — standard entries/exits → `from_signals` flow
- `examples/custom-indicator.md` — `IndicatorFactory` end-to-end
- `examples/walk-forward.md` — Splitter-based WFO with metrics
- `examples/parameter-sweep.md` — broadcasting-based grid search

## Scripts

Runnable helpers under `scripts/`:
- `scripts/validate-backtest.py` — smoke-runs an emitted backtest file
  and prints sanity metrics (`entries.sum()`, trade count, stats)
- `scripts/compare-pine-reference.py` — runs the Pine-reference
  comparison recipe for numeric equivalence checks

## Required env

- `CONTEXT7_API_KEY` — higher rate limits for Context7 queries.
- `GITHUB_ACCESS_TOKEN` — needed for installing vectorbt-pro from the
  private fork (`HyperFrequency/vectorbt.pro`) and for DeepWiki queries.
- Optional data-source keys: `BINANCE_API_KEY` / `BINANCE_API_SECRET`,
  `POLYGON_API_KEY`, `ALPACA_KEY_ID` / `ALPACA_SECRET_KEY`.

All sourced by the shakedown container from `$HOME/hyperfrequency/.env`.

## Cross-links to sibling skills

This skill owns vectorized backtest authoring. Hand the rest off:

| If the user wants… | Use sibling |
|---|---|
| Event-driven backtest ENGINE, venue/execution mechanics, live + Hyperliquid | `nautilus-trader` |
| Port / translate to Rust / Pine v6 / Nautilus / C++ / from a paper | `strategy-translator` |
| Walk-forward EPOCH selection / WFE / overfitting-epoch control | `adaptive-wfo-epoch` |
| "Is this Sharpe real?", PBO, purged/embargoed/combinatorial CV, deflated Sharpe | `model-evaluation` |
| Performance tearsheet, MAE analysis, optimal-leverage (via quantstats-rs) | `tearsheet-generator` |
| Compare a backtest to an Optuna/Ray baseline, root-cause logic discrepancies | `strategy-verify` |
| VPIN / OFI / Kyle / micro-price, order-book reconstruction | `microstructure-analyst` |
| Distributed HPO infra (Optuna/Ray/Dask/MLflow fan-out) | `neuro-quant-distributed-optimization` |

## Delegation

If the user's request includes porting FROM Pine Script, delegate to
`/strategy-translator` — that skill owns the translation contract
(Diff vs source, fill-timing equivalence, pitfall catalogue). This
skill's job begins AFTER the translation lands, or when the user is
authoring a vectorbt backtest from scratch without a Pine source.

## References

- vectorbt-pro (HyperFrequency fork): `HyperFrequency/vectorbt.pro`
  (private; install via `GITHUB_ACCESS_TOKEN`).
- vectorbt-pro docs: https://vectorbt.pro/ — hash-rotating
  `pvt_<hash>`; resolve the live URL with `scripts/get-pvt-url.sh`.
- vectorbt (vanilla): https://github.com/polakowo/vectorbt
- Context7 corpora: see the live-lookup table under "MANDATORY live
  lookups before emitting code" above.
- License: vectorbt is Apache-2.0 + Commons Clause; vectorbt-pro is
  proprietary (paid). This skill's own content follows the repo LICENSE.
- Last cross-checked: 2026-04-20 (against the `pvt_16ebf9ef` llms-full
  dump; re-verify drifting APIs via the live MCP / Context7 first).
