---
name: microstructure-feature-engineering
version: 0.1.0
description: Turn raw microstructure indicators (VPIN, OFI, book imbalance, trade signs) into ML-ready features. Covers information-driven bar construction (tick, volume, dollar, imbalance — Lopez de Prado AFML Ch. 2), microstructure noise filtering (two-time-scale RV, bipower variation jump decomposition), Hawkes intensity features, micro-price (Stoikov), HMM regime features, Bouchaud trade-sign autocorrelation, and leakage-safe assembly into a bar-aligned feature matrix. Triggers on phrases like "microstructure features", "OFI features", "volume bars", "dollar bars", "realized variance", "Hawkes features for trading", "L2 order-book features for ML", "tick-level feature engineering", "micro-price feature", "information-driven bars", "imbalance bars". For raw indicator computation use microstructure-analysis; for general feature engineering use feature-engineering; for regime fitting use markov-regime-detection; for purged CV use model-evaluation.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Skill
license: HyperFrequency original (citations to external academic + library work)
---

# Microstructure Feature Engineering

This skill is the bridge between a stream of raw microstructure *indicators* (the OFI, VPIN, queue-position, trade-sign output of the sibling `microstructure-analysis` skill) and an ML-ready *feature matrix*. It is opinionated about bar construction, normalization, noise filtering, jump/continuous variance decomposition, regime augmentation, and the leakage discipline required when the sample frequency is ticks rather than days.

## When to use

Use this skill when:

- You have a stream of raw microstructure indicators (OFI, VPIN, book imbalance, signed trade flow) and need to turn them into rows of an ML feature matrix.
- You are deciding between time bars, tick bars, volume bars, dollar bars, or imbalance bars for sub-daily / intraday work.
- A short-horizon model trained on time bars is being killed by intra-day non-stationarity (volume seasonality, opening auction, lunch lull) and you suspect the bar clock is the problem.
- You need realized-variance features that separate continuous diffusion from jumps (BNS bipower).
- You are adding trade-clustering intensity (Hawkes) or hidden-state (HMM) features to a model.
- You are auditing a microstructure ML pipeline for look-ahead leakage at the *bar boundary* (the leakage modes here are different from those at daily-bar scale).

Do **not** use this for:

- Raw indicator math (OFI definition, Lee-Ready classification, VPIN formula) → `microstructure-analysis`.
- General feature pipelines for daily/weekly bars (technical indicators, daily fracdiff) → `feature-engineering`.
- The CV / out-of-sample design for the model that consumes these features → `model-evaluation`.

## Required tooling — the unified gateway contract

Route documentation lookup, AST parsing, and code-graph queries through the unified mcp2cli gateway (see the `neuro-harness` skill in this repo for the full endpoint table):

| Task | Use | Why |
| --- | --- | --- |
| Confirm current API for `mlfinlab`, `nautilus_trader`, `hmmlearn`, `statsmodels`, `tick` (Hawkes) | `docs-dual-lookup` skill (Context7 + Auggie in parallel) | These libraries have drifted APIs (mlfinlab went closed-source around 2022 — the OSS API of the last public v0.x is the reference here; flag the version explicitly). |
| Parse an existing feature-engineering script | `tree-sitter` skill via `mcp2cli tree-sitter parse` | Reliable function/decorator extraction beats grep. |
| Locate every caller of a feature transform across the repo | `mcp2cli gitnexus` or the `gitnexus-exploring` skill | Critical when renaming a feature column — the blast radius is large. |

**Do not** hand-roll an API call from training memory when wiring `mlfinlab.data_structures.standard_data_structures.get_dollar_bars` or `hmmlearn.hmm.GaussianHMM` — both have had breaking signature changes. Query the gateway first. If `neuro-harness` is unreachable, degrade to: Context7 → WebFetch on upstream docs → training-data recall as last resort, flagging the source of each claim.

## Pipeline relative to siblings

```
raw tape + L2/L3 deltas
        |
        v
+-------------------------+
| microstructure-analysis |  indicators (Lee-Ready, OFI, VPIN, queue,
|  -- units: events/ticks |  Kyle's lambda) at native event resolution
+-------------------------+
        |
        v
+----------------------------------+
| microstructure-feature-engineer. |  THIS SKILL: bars + noise filter +
|  -- units: ML feature ROWS       |  RV decomp + Hawkes + HMM-state +
|     one per bar, leakage-safe    |  fracdiff + leakage-safe assembly
+----------------------------------+
        |
        v
[ML / RL models]   [vectorbt / nautilus]   [model-evaluation: purged CV]
```

Contract: **indicators in, feature rows out** — every row is keyed by a single bar timestamp `ts_event` and uses only information observable at or before `ts_event`.

## Feature taxonomy

| Feature family | Input data layer | Aggregation scale | Stationarity | Expected predictive horizon | Decay |
|---|---|---|---|---|---|
| OFI integrated over bar | L1/L2 deltas | tick / volume / dollar | stationary at short horizons; drifts intraday | seconds → minutes | fast (seconds) |
| Static book imbalance, top-N | L2 snapshot | bar end | weakly stationary; depends on tick size | seconds → minutes | very fast |
| Trade-sign aggregates (Σ b_i, %buy_vol) | tape (signed via tick rule / Lee-Ready) | bar | stationary if symbol liquid | seconds → minutes | medium |
| Trade-sign autocorrelation (Bouchaud) | tape (signed) | over a window of N trades | stationary; long-memory by construction | minutes → hours (memory) | slow |
| Realized variance | tape, log-prices | bar | non-stationary in level, scale with vol regime | minutes → day | medium |
| RV jump component (BNS bipower) | tape, log-prices | bar | event-like, heavy-tail | minutes → day | medium |
| Two-time-scale RV (TSRV) | tape, ultra-HF prices | bar | as RV, with noise correction | minutes → day | medium |
| Hawkes intensity / branching ratio | tape (event times) | rolling window | non-stationary across regimes | seconds → minutes | fast |
| Micro-price (Stoikov) | L1 (bid, ask, sizes) | bar end snapshot | stationary in spread units | seconds | very fast |
| HMM decoded state | returns + RV (or returns alone) | bar | categorical; persistent | hours → days | slow |
| Queue position (own order) | L3 (MBO) | tick | not predictive on its own; conditions fill prob | n/a (execution feature) | n/a |
| Spread features (quoted, effective, realized) | L1 quotes + trades | bar | scale with vol regime | seconds → minutes | medium |
| VPIN | volume bars, signed flow | volume bar | regime indicator | minutes → hours | slow |

"Decay" is the rough timescale over which the feature loses informational value. Very-fast-decay features are typically used as *state* features (consumed within the same bar) rather than as multi-bar lags.

## Detailed references

Implementation code and derivations live in `references/` to keep this router lean. Load the file you need:

- **`references/bar-construction.md`** — time / tick / volume / dollar / imbalance bars; why information-driven bars beat clock time (AFML Ch. 2); `volume_bars`, `dollar_bars`, `tick_imbalance_bars`.
- **`references/feature-families.md`** — the microstructure feature catalogue with code: RV + BNS bipower jump decomposition (`rv_bipower`), two-time-scale RV (`two_scale_rv`), Bouchaud trade-sign autocorrelation (`trade_sign_autocorr`), Hawkes intensity + branching ratio (`fit_hawkes_branching`), micro-price (`weighted_mid`), HMM state (`hmm_state_feature`), spread features, OFI bar alignment (`ofi_bar_aligned`), triple-barrier labeling (`triple_barrier_micro`), and the leakage-safe assembly join (`assemble_feature_matrix`).
- **`references/leakage-stationarity.md`** — bar-level stationarity (bar clock as a stationarity intervention, fracdiff for price-level features, intraday seasonality) and the microstructure-specific leakage-mode table + cross-asset transfer rules.
- **`references/end-to-end-example.md`** — full worked pipeline: BTC-USD perp on Hyperliquid, 100-volume-coin bars → OFI + micro-price + HMM-state + triple-barrier labels → parquet.
- **`references/bibliography.md`** — libraries (mlfinlab, tick, hmmlearn, nautilus_trader, statsmodels), academic papers (BNS, Zhang-Mykland-Aït-Sahalia, Hawkes, Bacry, Bouchaud, Stoikov, Cont-Kukanov-Stoikov, Huang-Stoll, Lee-Ready), standard datasets (Databento, Tardis, LOBSTER), and unverified/flagged API claims.

## Common pitfalls

- **Treating volume bars as if they were time bars.** Their timestamps are non-uniform; do not resample-to-frequency or align with exogenous time-bar features without explicit join logic. Bar duration is itself a feature.
- **Fitting HMM / VPIN / Hawkes once on the full sample and using the fitted parameters as features.** Each is a *training-leakage* sin. Roll-fit on expanding or sliding windows.
- **Mixing bar clocks within one feature matrix.** OFI on volume bars + RV on time bars + HMM trained on dollar-bar returns → the model is learning a clock, not a market.
- **Hawkes branching ratio confused with kernel norm.** Some libraries return `α`, others `α/β`. Confirm against docstrings; flag in the feature name (`branching_ratio` vs `alpha_raw`).
- **`weighted_mid` reported as `micro_price`.** Weighted-mid is the zeroth-order Stoikov approximation, not the full micro-price. Either implement the full Markov-chain calibration or rename the feature honestly.
- **Triple-barrier vol-window in the wrong units.** A 200 *tick* window inside a *volume bar* labeling routine is a unit error. Match the window to the bar clock.
- **Realized-variance jump component going negative.** Always clip `J = max(RV - BV, 0)` — finite-sample noise produces tiny negative jump components otherwise.
- **Bar-edge ffill direction.** Aligning indicators to bars with `method='bfill'` is a textbook look-ahead bug; always `'ffill'`.
- **`join(..., validate='one_to_one')` removed "for speed".** This removes the only safeguard against silent many-to-one alignment. Keep it.

## Cross-links to other skills

- `microstructure-analysis` — raw indicators (OFI, VPIN, Lee-Ready, Kyle's lambda, queue position). This skill consumes them.
- `feature-engineering` — general ML features and labels, fractional differencing, meta-labeling, sample weights. This skill *specializes* it for microstructure data.
- `markov-regime-detection` — rigorous HMM fitting workflow (model selection, label-permutation, rolling estimation). Required if HMM-state is used as a feature.
- `model-evaluation` — purged + embargoed CV, deflated Sharpe, multiple-testing budget for the model that consumes these features.
- `nautilus-trader` — production execution layer; the source of L2/L3 in live and the right place to reimplement the feature pipeline as a strategy.
- `vectorbt` — bar-level backtest of the resulting signals.
- `tardis-data-agent` — historical tape + L2/L3 ingest (the most common data source for offline microstructure feature engineering).
- `ml-hypothesis-design` — microstructure features explode the trial space; deflate Sharpe accordingly.
