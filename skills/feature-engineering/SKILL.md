---
name: feature-engineering
version: 0.1.0
description: Feature engineering for quant ML — turn raw price, volume, and order-book data into a leakage-safe feature matrix with appropriate labels. Use when building the inputs to a trading model, designing labels for supervised learning, or auditing an existing feature pipeline for look-ahead bias. Covers returns transforms (log, simple, fractional differencing), rolling statistics, technical indicators (talib/ta), microstructure features (book imbalance, trade signs, realized variance), regime indicators, and the triple-barrier labeling method. Triggers on phrases like "build features for", "engineer features", "triple-barrier", "meta-labeling", "fractional differencing", "leakage check", "what features should I use", or "how do I label this". For pure microstructure detail use microstructure-analysis; for evaluating the resulting model use model-evaluation.
allowed-tools: Read Write Edit Bash
---

# Feature Engineering for Quantitative ML

## Overview

A trading ML model is its feature matrix. Architecture choices matter, but the gap between a working strategy and noise is almost always in how the features were constructed and the labels were defined. The two failure modes that dominate this work are subtle and lethal: **look-ahead leakage** (a feature at time t encodes information from after t) and **label leakage** (the label for sample i overlaps in time with sample j, so training and test are not independent).

This skill is the discipline for avoiding both. It covers the standard transforms, the indicator libraries, the microstructure features that earn their place in the matrix, and — most importantly — the triple-barrier labeling method from López de Prado (2018) that makes events well-defined and labels honest.

## When to Use This Skill

Use this skill when:

- Starting a new quant ML project and need to build the X matrix from raw prices/volumes/book data
- Adding microstructure features to an existing daily-bar pipeline
- A model's out-of-sample performance is suspiciously good and you suspect leakage
- Choosing a labeling scheme (fixed horizon vs triple-barrier vs meta-labels)
- Auditing whether a target column was constructed without future information
- Deciding between log returns, simple returns, and fractional differencing

Do **not** use this for: pure microstructure analysis without modeling intent (use `microstructure-analysis`); or post-fit evaluation (use `model-evaluation`).

## Core Framework

### Step 1 — Choose the feature horizon and the label horizon explicitly

These are two separate decisions and conflating them is the #1 source of confusion.

- **Feature horizon:** how far back in time each feature looks. A 20-day SMA has horizon 20; book imbalance at t has horizon 0+.
- **Label horizon:** how far forward the target is computed over. A 5-day forward return has horizon 5.

The two together define the **information set** and the **prediction problem**. Every leakage check downstream assumes you've stated them.

### Step 2 — Build returns and stationarity transforms

Raw prices are non-stationary; you almost never want them as features directly. Standard transforms:

- **Log returns** `r_t = log(P_t / P_{t-1})` — additive across time, symmetric, good for high-frequency.
- **Simple returns** `r_t = P_t / P_{t-1} - 1` — additive across portfolio weights at a single time, good for portfolio-level work.
- **Fractional differencing** (López de Prado 2018, Ch. 5) — apply `(1-L)^d` for non-integer d (typically 0 < d < 1). Preserves memory (long-run dependence) while inducing stationarity. The classical first-difference (d=1) destroys all level information; fractional differencing keeps the minimum needed.

For most equity/crypto bar data, log returns are the default. Fractional differencing is worth its complexity when level information matters (regime, mean-reversion priors) and the series fails an ADF test.

### Step 3 — Standard derived features

Rolling statistics over the chosen feature horizon: mean, std, skew, kurtosis, autocorrelation. These are the bread-and-butter and span most of what "technical indicators" actually compute.

**Technical indicators (talib / ta).** Use established libraries; do not hand-roll RSI. Two reasonable choices:

- `talib` (C library + Python wrapper): fast, 200+ indicators, requires native install.
- `ta` (pure Python, pandas-native): slower but easier to install; `add_all_ta_features` is convenient for prototyping.

Both are bar-aligned (OHLCV in, indicator out). Be aware: most indicators have a warm-up period; the first N rows are NaN and must be dropped, not zero-filled.

**Realized variance / volatility.** `RV_t = Σ r_τ^2` over the window. The basis of any vol-regime feature; also the denominator for Sharpe-style normalization.

### Step 4 — Microstructure features (when frequency justifies)

For sub-daily strategies, microstructure features outperform technical indicators. The five that earn their place in nearly every short-horizon ML model:

1. **Book imbalance** at top-of-book and over the top N levels (see `microstructure-analysis` for the formula).
2. **Order Flow Imbalance (OFI)** — windowed, the Cont-Kukanov-Stoikov flow integral.
3. **Trade-sign aggregates** — buy volume / total volume, signed volume sum, over the window.
4. **Realized variance from tick data** — the "true" volatility, free of bar discretization.
5. **VPIN** — toxic-flow regime indicator; used as a meta-feature or sizing input rather than a directional signal.

Operational detail and code for each lives in `microstructure-analysis`. This skill assembles them into a feature matrix.

### Step 5 — Label engineering: the triple-barrier method

Fixed-horizon labels ("5-day forward return > 0") are biased toward path-independent moves and lose any notion of stop-loss/take-profit, which is what the strategy will actually trade. The **triple-barrier method** (López de Prado 2018, Ch. 3) labels each event by which of three barriers is hit first:

1. **Upper barrier** (e.g. +2σ above entry) → label = +1 (take profit hit)
2. **Lower barrier** (e.g. -1σ below entry) → label = -1 (stop loss hit)
3. **Vertical barrier** (e.g. after N bars) → label = 0 or sign of return at expiry

This gives path-dependent, asymmetric, vol-normalized labels that match how the strategy would actually exit. Crucially, the barriers are computed *forward in time* from the event — which means labels for events too close together **overlap**, breaking the i.i.d. assumption.

Overlapping labels are the canonical reason for the **purged + embargoed CV** in `model-evaluation`. Always pass the label end-times to your CV splitter.

### Step 6 — Leakage prevention checklist

Before training, audit:

1. **No future data in any feature at time t.** Every rolling/aggregation operation must be one-sided (right-aligned), not centered. Pandas `rolling()` is right-aligned by default; `pandas.DataFrame.shift(-N)` is the most common silent leakage source.
2. **No target leakage.** The label must be constructible only from data strictly after t. If the label uses the same close that the feature uses, you have a 0-horizon leak.
3. **No standardization on the full sample.** Mean/std for z-scoring must be computed on the training window only and *applied* to the test window. Use `sklearn.preprocessing.StandardScaler.fit` on train, `.transform` on test.
4. **No survivorship bias.** Universes built from "today's S&P 500" backward in time are biased; companies that were delisted are missing. Use point-in-time universes.
5. **No look-ahead in the universe.** A "top 100 by market cap" filter must use market cap at time t, not at backtest start.
6. **No data revision leakage.** Macroeconomic series get revised; use vintage data (e.g. ALFRED for FRED) so each timestamp reflects what was actually known then.

### Step 7 — Sample weights for overlapping labels

If you used the triple-barrier method, samples are not i.i.d. — events close in time share future returns. López de Prado's recipe:

- Compute the **average uniqueness** of each label (1 - average concurrency with other labels in its window).
- Use these as sample weights during fitting. `sample_weight=` is supported by sklearn classifiers, LightGBM, XGBoost.

This down-weights labels in dense event clusters and prevents the model from fitting the same forward window N times.

## Code Snippets

Reference implementations live in [`references/code-snippets.md`](references/code-snippets.md):

- `triple_barrier_labels` — Step 5 path-dependent labeling (AFML Ch. 3)
- `frac_diff_weights` / `fractional_difference` — Step 2 stationarity transform (AFML Ch. 5)
- `build_feature_matrix` — Step 3 leakage-safe OHLCV assembly (right-aligned rolling, no `.shift(-N)`)
- `label_uniqueness` — Step 7 sample weights for overlapping labels (AFML Ch. 4)

These are minimal teaching implementations; `mlfinlab` is the canonical, optimized source.

## Common Pitfalls

1. **`.shift(-N)` anywhere outside the label column.** This is look-ahead bias. The label may legitimately use `.shift(-N)`; nothing else may.
2. **Fillna with zero on indicators.** Indicators have warm-up periods. Zero-filling the warm-up makes those rows look like "neutral RSI = 0" instead of "unknown". Drop them.
3. **Z-scoring with global statistics.** Train-time normalization with full-sample mean/std leaks the test distribution into training. Always fit scaler on train, transform test.
4. **Treating triple-barrier labels as i.i.d.** Overlapping label windows violate the i.i.d. assumption. Use sample-weight uniqueness and purged CV (`model-evaluation`).
5. **Survivorship bias in the universe.** "All current S&P 500 stocks from 2010 to today" excludes 2010's S&P 500 members who got delisted. Use point-in-time index membership.
6. **Mixing fundamental data with quarterly release timestamps.** Earnings are reported with a lag; using fundamentals as-of period end leaks the announcement. Use release timestamps.
7. **Re-using the same volatility forecast for the barriers and the model features.** If the barrier uses σ_t and a feature also encodes σ_t, the label and the feature share information. Either decorrelate them or accept the redundancy explicitly.

## Tooling References

This skill defines methodology. Operationalize it with:

- **`microstructure-analysis`** skill (sister skill) — the source of microstructure features and trade-sign classification used in Step 4.
- **`model-evaluation`** skill (sister skill) — for the purged + embargoed CV that the triple-barrier method requires.
- **`ml-hypothesis-design`** skill (sister skill) — for the trial budget. Every feature is a hyperparameter; every label-rule choice is a hyperparameter.
- **`scikit-learn`** skill — for the `Pipeline`, `ColumnTransformer`, and `StandardScaler` that enforce train/test discipline.
- **`xgboost`** / **`lightgbm`** / **`catboost`** skills — for the gradient-boosting backbone that consumes these features; all support `sample_weight`.
- **`vectorbt`** skill — for translating predictions into a backtested PnL.
- **`mlfinlab`** (library, not yet a skill) — implements the López de Prado triple-barrier and fractional-differencing canonically; the snippets above are minimal reference implementations.

## References

Full bibliography — primary libraries, deep-dive doc pages, adjacent libraries, academic papers (López de Prado AFML, Cont-Kukanov-Stoikov OFI, Easley VPIN/PIN, Hosking fracdiff, Bailey backtest-overfitting), tutorials, and benchmark datasets — lives in [`references/bibliography.md`](references/bibliography.md). Last cross-checked 2026-05-20.

Quick anchors:
- **mlfinlab** ([GitHub](https://github.com/hudson-and-thames/mlfinlab)) — canonical AFML implementation (triple-barrier, fracdiff, sample weights)
- **ta-lib-python** ([GitHub](https://github.com/TA-Lib/ta-lib-python)) / **ta** ([GitHub](https://github.com/bukosabino/ta)) — technical indicators
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley. ISBN 9781119482086 — the bible of this skill (Ch. 3 labeling, Ch. 4 weights, Ch. 5 fracdiff, Ch. 7 purged CV).
