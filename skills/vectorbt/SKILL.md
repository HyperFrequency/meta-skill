---
name: vectorbt
description: >
  Vectorized PARAMETER SWEEPS + fast strategy screening with vectorbt(-pro):
  IndicatorFactory indicators, Portfolio.from_signals / from_orders /
  from_order_func, broadcast parameter sweeps, Splitter / CVSplitter
  walk-forward, and Data loaders (Binance/CCXT/YF/Polygon). Use to sweep
  parameters and check whether a strategy plausibly has edge — NOT for
  real backtests. Trigger without "vectorbt" on "parameter sweep",
  "IndicatorFactory", "from_signals", "PortfolioOptimizer", "Splitter
  walk-forward", or numpy/pandas sweep infra. For real / event-driven
  backtests, live, or Hyperliquid use nautilus-trader; for HFT / MBO
  order-book backtests use hftbacktest; for porting /
  "Rust or Pine version" use strategy-translator; for walk-forward EPOCH
  / WFE / overfitting-epoch use adaptive-wfo-epoch; for "is this Sharpe
  real" / PBO / purged CV use model-evaluation; for tearsheet / MAE /
  leverage use tearsheet-generator; for verifying a backtest use
  strategy-verify; for VPIN/OFI/L2 order-flow use microstructure-analyst.
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
distinct from `/strategy-translator` (cross-framework ports). Hand a Pine
script to translate → delegate; a strategy idea / thesis / paper to
implement in vectorbt → this skill.

Both vectorbt (vanilla, Apache 2 + Commons Clause) and vectorbt-pro
(paid, proprietary) are covered. State which variant you assume in the
first line of output — their APIs differ (`references/pro-vs-vanilla.md`).

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
instances (parameter combinations, universe constituents, or both). A
parameter sweep is just extra columns: `vbt.MA.run(price, window=[10,
20, 50])` returns three columns, comparisons broadcast across them, and
`Portfolio.from_signals` runs the whole grid in one compiled Numba loop.
No Python per-bar iteration — you orchestrate arrays, Numba does the
work. Every idiom below follows from it.

## MANDATORY live lookups before emitting code

vectorbt releases frequently; defaults drift. Before emitting any
non-trivial call, verify via the best available source (in order) and
cite the snippet heading in your Diff vs spec section:

1. **VBT Pro's own MCP server** (`vectorbtpro.mcp_server`, if installed)
   — the INSTALLED version's actual API, zero drift. Setup:
   `references/ai-workflows.md`.
2. **Context7** — vectorbt-pro llms-full corpus
   (`/llmstxt/vectorbt_pro_pvt_4f8d7c01_llms-full_txt`, ~13.9k snippets,
   default) or `/websites/vectorbt_pro`; vanilla `/polakowo/vectorbt`
   and `/websites/vectorbt_dev`.
3. **Static reference files** in this skill — last resort for patterns
   that don't change between releases.

Also consult the vault via `mcp__neuro-link-recursive__nlr_wiki_search`
(query `"vectorbt <concern>"`); hits ≥ 0.7 confidence supersede static
guidance.

## Standard authoring workflow

Follow these 6 steps. Skipping steps is how bugs appear.

### 1. State the variant + strategy intent in one line

"vectorbt-pro: long-only EMA cross on BTC/USDT daily, 100% of equity
per trade, fees 0.1%, slippage 0.05%." One line — ambiguity elsewhere
blocks downstream decisions.

### 2. Load data

Prefer VBT's `Data` loaders (`BinanceData`, `CCXTData`, `YFData`,
`PolygonData`/`AlpacaData` in Pro, file-backed `HDFData` / `CSVData` /
`ParquetData`) over yfinance directly — they cache, reshape, and handle
multi-symbol uniformly. For reviewable/reproducible backtests prefer a
cached local file (a frozen parquet doesn't drift) and state the cache
policy in the first line of the emitted code. Full loader table +
caching guidance: `references/data-loading.md`.

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

**Always pass `size`/`size_type`, `fees`, `slippage`, `freq`, and
`init_cash` explicitly** — never omit one without stating why. The
canonical `from_signals` call, the other three constructors, and the
close-vs-next-bar-open fill decision live in
`references/portfolio-constructors.md` and `references/fill-timing.md`.

### 5. Analyze

Standard stats live on the portfolio object — `pf.stats()` (kitchen
sink), `pf.returns_stats()`, `pf.sharpe_ratio()`, `pf.max_drawdown()`,
`pf.trades.stats()`, `pf.plot().show()`. For reportable outputs, emit
`pf.stats()` + a saved `pf.plot()`. Custom metric patterns (rolling
drawdown windows, regime-conditioned returns, per-param ranking) are in
`references/analysis.md`.

### 6. Optimize (if the user asked for it)

Grid search via broadcasting (fast, exhaustive, <5 dims) for most cases;
`vbt.Splitter` / `vbt.CVSplitter` (Pro) for walk-forward and purged
k-fold; `PortfolioOptimizer` (Pro) for target-weight/target-vol; external
optuna / ray for high-dim or distributed sweeps. Walk-forward recipes,
overfit diagnostics, and optuna/ray integration: `references/optimization.md`.

## Validation — always verify the backtest isn't silently wrong

Before returning a backtest, run at least: (1) signal-count sanity —
print `entries.sum()` / `exits.sum()`; 200 signals for a twice-a-year
strategy means a look-ahead or re-firing bug; (2) `pf.trades.count()`
matches expectation; (3) equity-curve shape — monotonic-up with no
drawdowns suggests look-ahead; (4) if the user gave a Pine/published
reference, run `scripts/compare-pine-reference.py` and cite the delta.
Full checklist + silent-failure catalogue: `references/validation.md`.

State which validations ran and their outcomes at the bottom of the
deliverable. Unvalidated backtests are flagged as incomplete by the
consortium judge.

## Anti-patterns

- **No Python for-loop over bars** — the escape hatch is
  `from_order_func` with Numba callbacks, not Python loops.
- **Don't hand-roll `.ewm()` when a VBT indicator exists** — Pine-param
  mismatch (`references/indicators.md`).
- **`from_signals` fills at the signal bar's CLOSE, not next-bar open** —
  pass `price=open_next` for next-bar (`references/fill-timing.md`).
- **Don't use `size=np.inf` for "100% of equity"** — use `size=1.0,
  size_type="percent"`; and never skip `freq=` (annualised metrics
  depend on it).
- **Don't emit vectorbt-pro API without a Context7 citation** — VBT Pro
  ships new releases frequently.
- **Don't cache-bust** (`@functools.lru_cache` over VBT's
  `cached_property`/`cache_func`) or **confuse vanilla vs Pro imports** —
  `vbt.BBANDS` differs between them.

## Bundled files

Reference depth under `references/` — read the relevant one(s):
`pro-vs-vanilla.md` (vanilla↔Pro API diffs), `indicators.md` (built-ins
+ NB calls), `indicator-factory.md` (custom indicators),
`portfolio-constructors.md` (the four constructors + canonical
`from_signals`), `fill-timing.md` (close vs next-bar open),
`data-loading.md` (loaders + caching), `analysis.md` (metrics /
tearsheets), `optimization.md` (grid / walk-forward / optuna),
`validation.md` (correctness checks), `ai-workflows.md` (VBT Pro MCP).

Worked patterns under `examples/`: `signal-portfolio.md`,
`custom-indicator.md`, `walk-forward.md`, `parameter-sweep.md`.

Runnable helpers under `scripts/`: `validate-backtest.py` (smoke-runs an
emitted backtest, prints sanity metrics), `compare-pine-reference.py`
(numeric equivalence vs a Pine reference), `get-pvt-url.sh` (resolve the
hash-rotating vectorbt.pro docs URL).

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

If the request includes porting FROM Pine Script, delegate to
`/strategy-translator` (it owns the translation contract); this skill's
job begins after the translation lands, or when authoring from scratch.

## References

- vectorbt-pro (HyperFrequency fork): `HyperFrequency/vectorbt.pro`
  (private; install via `GITHUB_ACCESS_TOKEN`).
- vectorbt-pro docs: https://vectorbt.pro/ — hash-rotating
  `pvt_<hash>`; resolve the live URL with `scripts/get-pvt-url.sh`.
- vectorbt (vanilla): https://github.com/polakowo/vectorbt
- Context7 corpora: see "MANDATORY live lookups" above.
- License: vectorbt is Apache-2.0 + Commons Clause; vectorbt-pro is
  proprietary (paid). This skill's own content follows the repo LICENSE.
- Last cross-checked: 2026-04-20 (against the `pvt_16ebf9ef` llms-full
  dump; re-verify drifting APIs via the live MCP / Context7 first).
