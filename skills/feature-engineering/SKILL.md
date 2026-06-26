---
name: feature-engineering
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

### Triple-barrier labeling

```python
import numpy as np
import pandas as pd


def triple_barrier_labels(
    close: pd.Series,
    events: pd.DatetimeIndex,
    pt_sl: tuple[float, float],
    vol: pd.Series,
    vertical_barrier_bars: int,
) -> pd.DataFrame:
    """Label each event by which barrier is hit first.

    Args:
        close: Series of close prices indexed by timestamp.
        events: Event timestamps (e.g. from a CUSUM filter on returns).
        pt_sl: (profit_target_mult, stop_loss_mult) in units of vol.
               E.g. (2.0, 1.0) for +2σ profit / -1σ stop.
        vol: Series of per-bar volatility forecasts (e.g. EWMA of squared returns,
             aligned to event index).
        vertical_barrier_bars: Max bars before the vertical barrier fires.

    Returns:
        DataFrame indexed by event timestamp with columns:
          ['t1' (barrier-hit timestamp), 'ret' (return at exit), 'label' (-1, 0, +1)].

    Reference: López de Prado (2018), Advances in Financial Machine Learning, Ch. 3.
    """
    pt_mult, sl_mult = pt_sl
    out = pd.DataFrame(index=events, columns=["t1", "ret", "label"])

    # Pre-compute the vertical barrier timestamps
    close_idx = close.index
    for event_ts in events:
        i = close_idx.get_loc(event_ts)
        end_i = min(i + vertical_barrier_bars, len(close_idx) - 1)
        vert_ts = close_idx[end_i]

        # Path of prices from event to vertical barrier
        path = close.iloc[i:end_i + 1]
        entry_price = path.iloc[0]
        sigma = vol.loc[event_ts] if event_ts in vol.index else vol.asof(event_ts)

        if pd.isna(sigma) or sigma == 0:
            out.loc[event_ts] = [vert_ts, 0.0, 0]
            continue

        pt_price = entry_price * (1 + pt_mult * sigma)
        sl_price = entry_price * (1 - sl_mult * sigma)

        # First barrier hit
        hit_pt = path[path >= pt_price]
        hit_sl = path[path <= sl_price]

        ts_pt = hit_pt.index[0] if len(hit_pt) > 0 else None
        ts_sl = hit_sl.index[0] if len(hit_sl) > 0 else None

        candidates = [(ts, lbl) for ts, lbl in
                      [(ts_pt, 1), (ts_sl, -1), (vert_ts, 0)] if ts is not None]
        # Earliest barrier wins
        t1, label = min(candidates, key=lambda x: x[0])

        exit_price = close.loc[t1]
        ret = exit_price / entry_price - 1
        out.loc[event_ts] = [t1, ret, label]

    return out.astype({"ret": float, "label": int})
```

### Fractional differencing (López de Prado)

```python
def frac_diff_weights(d: float, threshold: float = 1e-4) -> np.ndarray:
    """Weights for fractional differencing, truncated when |w| < threshold."""
    weights = [1.0]
    k = 1
    while True:
        w = -weights[-1] * (d - k + 1) / k
        if abs(w) < threshold:
            break
        weights.append(w)
        k += 1
    return np.array(weights[::-1])  # most recent observation gets weight 1


def fractional_difference(series: pd.Series, d: float, threshold: float = 1e-4) -> pd.Series:
    """Apply fractional differencing (1-L)^d with truncated weights.

    Reference: López de Prado (2018), Advances in Financial Machine Learning, Ch. 5.
    """
    w = frac_diff_weights(d, threshold)
    width = len(w)
    out = pd.Series(index=series.index, dtype=float)
    for i in range(width - 1, len(series)):
        window = series.iloc[i - width + 1 : i + 1].values
        if np.isnan(window).any():
            continue
        out.iloc[i] = float(np.dot(w, window))
    return out
```

### Leakage-safe feature assembly

```python
from ta import add_all_ta_features
from ta.utils import dropna


def build_feature_matrix(
    ohlcv: pd.DataFrame,
    lookback_windows: list[int] = [5, 20, 60],
) -> pd.DataFrame:
    """Assemble a leakage-safe feature matrix from OHLCV bars.

    All rolling operations are right-aligned (one-sided); no .shift(-N) anywhere.
    """
    df = dropna(ohlcv.copy())
    log_ret = np.log(df["close"] / df["close"].shift(1))

    feats = pd.DataFrame(index=df.index)

    for w in lookback_windows:
        feats[f"ret_mean_{w}"] = log_ret.rolling(w).mean()
        feats[f"ret_std_{w}"]  = log_ret.rolling(w).std()
        feats[f"ret_skew_{w}"] = log_ret.rolling(w).skew()
        feats[f"rv_{w}"]       = (log_ret ** 2).rolling(w).sum()

    # Technical indicators from the `ta` library (pandas-native)
    df = add_all_ta_features(
        df, open="open", high="high", low="low", close="close", volume="volume",
        fillna=False,  # do NOT zero-fill; drop NaN warm-up rows downstream
    )
    indicator_cols = [c for c in df.columns if c not in ohlcv.columns]
    feats = pd.concat([feats, df[indicator_cols]], axis=1)

    # Critical: never assign a feature whose construction touches a future row.
    # If you must compute a feature that uses time-t+1 inside a helper, .shift(1) the result.
    return feats.dropna()  # drop the warm-up window
```

### Sample-weight uniqueness for overlapping labels

```python
def label_uniqueness(t1: pd.Series) -> pd.Series:
    """Average uniqueness weight for each labeled event with end-time t1.

    Args:
        t1: Series indexed by event start time; values are barrier-hit timestamps.

    Returns:
        Series of weights in (0, 1] for each event. Pass as sample_weight to the classifier.

    Reference: López de Prado (2018), Advances in Financial Machine Learning, Ch. 4.
    """
    # Concurrency: number of active labels at each bar
    bar_index = pd.date_range(t1.index.min(), t1.max(), freq=t1.index.freq or "T")
    concurrency = pd.Series(0, index=bar_index)
    for start, end in t1.items():
        concurrency.loc[start:end] += 1

    # Each event's weight = mean of 1/concurrency over its life
    weights = pd.Series(index=t1.index, dtype=float)
    for start, end in t1.items():
        weights.loc[start] = (1.0 / concurrency.loc[start:end]).mean()
    return weights
```

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

### Primary library
This skill is methodology-first; operational implementations live across `mlfinlab`, `ta-lib`, `ta`, and `pandas` rolling-window operators.

- [mlfinlab on GitHub](https://github.com/hudson-and-thames/mlfinlab) — Hudson & Thames implementation of Lopez de Prado's AFML; triple-barrier, fractional differencing, sample weights
- [mlfinlab documentation](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/) — pinned to v1.x
- [ta-lib-python on GitHub](https://github.com/TA-Lib/ta-lib-python) — Python bindings to the C TA-Lib library; 200+ indicators, very fast
- [ta (Bukosabino) on GitHub](https://github.com/bukosabino/ta) — pure-Python pandas-native alternative; slower but no native install
- [pandas documentation](https://pandas.pydata.org/docs/) — `rolling`, `expanding`, `shift`, `groupby` are the leakage-safety toolset

### Deep-dive docs (specific pages worth bookmarking)
- [mlfinlab Labeling module (triple-barrier)](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/labeling/labeling.html) — canonical implementation of the snippet above; verify your version's API
- [mlfinlab Fractional Differentiation](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/feature_engineering/fracdiff_features.html) — both fixed-width (truncated) and expanding-window variants
- [mlfinlab Sample Weights](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/sample_weights/sample_weights.html) — uniqueness + return attribution weights
- [mlfinlab Structural Breaks](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/structural_breaks/introduction.html) — CUSUM event filters that generate the `events` index for triple-barrier
- [mlfinlab Information-Driven Bars](https://hudson-and-thames-mlfinlab.readthedocs-hosted.com/en/latest/sample_data/information_driven_bars.html) — dollar/volume/imbalance bars; the right "samples" for triple-barrier on intraday data
- [ta-lib indicator reference](https://ta-lib.github.io/ta-lib-python/funcs.html) — the 200+ indicators with parameter docs
- [ta library reference](https://technical-analysis-library-in-python.readthedocs.io/en/latest/ta.html) — every momentum / volatility / volume indicator; `add_all_ta_features` convenience function
- [pandas `rolling` window docs](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.rolling.html) — right-aligned by default; the leakage-safety guarantee

### Adjacent / alternative libraries
- [tsfresh](https://github.com/blue-yonder/tsfresh) — automated time-series feature extraction; 4000+ features over rolling windows
- [feature-engine](https://github.com/feature-engine/feature_engine) — sklearn-compatible feature engineering pipelines; useful for the ColumnTransformer / Pipeline contract
- [stumpy](https://github.com/TDAmeritrade/stumpy) — matrix profile features; useful when "this pattern repeats" is the signal
- [pyts](https://github.com/johannfaouzi/pyts) — time-series feature engineering (BOSS, SAX, shapelets) and classification baselines
- [riskfolio-lib](https://github.com/dcajasn/Riskfolio-Lib) — when "features" become portfolio constraints (factor exposures)
- [statsmodels.tsa.stattools.adfuller](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html) — ADF test used in deciding the right fractional-differencing `d` parameter

### Academic papers
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley. ISBN 9781119482086 — the bible of this skill.
  - Ch. 3 — Labeling (triple-barrier method)
  - Ch. 4 — Sample weights for overlapping labels
  - Ch. 5 — Fractional differencing
  - Ch. 7 — Purged/embargoed cross-validation (see `model-evaluation`)
- Cont, R., Kukanov, A., & Stoikov, S. (2014). "The Price Impact of Order Book Events." *Journal of Financial Econometrics* 12(1), 47-88. [DOI: 10.1093/jjfinec/nbt003](https://doi.org/10.1093/jjfinec/nbt003) — OFI feature.
- Hasbrouck, J. (2007). *Empirical Market Microstructure*. Oxford University Press. ISBN 9780195301649 — background for tick-data features and microstructure noise.
- Easley, D., López de Prado, M. M., & O'Hara, M. (2012). "Flow Toxicity and Liquidity in a High-Frequency World." *Review of Financial Studies* 25(5), 1457-1493. [SSRN 1695596](https://papers.ssrn.com/abstract=1695596) — VPIN, dollar / volume bars.
- Hosking, J. R. M. (1981). "Fractional Differencing." *Biometrika* 68(1), 165-176. [DOI: 10.2307/2335817](https://doi.org/10.2307/2335817) — the original fractional differencing paper that Ch. 5 of AFML builds on.
- Bailey, D. H., Borwein, J., López de Prado, M., & Zhu, Q. J. (2014). "Pseudo-Mathematics and Financial Charlatanism: The Effects of Backtest Overfitting on Out-of-Sample Performance." *Notices of the AMS* 61(5), 458-471. [SSRN 2326253](https://papers.ssrn.com/abstract=2326253) — why "feature engineering" alone can produce false discoveries; pairs with `ml-hypothesis-design`.
- Easley, D., Kiefer, N. M., O'Hara, M., & Paperman, J. B. (1996). "Liquidity, Information, and Infrequently Traded Stocks." *Journal of Finance* 51(4), 1405-1436. [DOI: 10.1111/j.1540-6261.1996.tb04074.x](https://doi.org/10.1111/j.1540-6261.1996.tb04074.x) — PIN; theoretical foundation for the toxic-flow microstructure features.
- Bouchaud, J.-P., Bonart, J., Donier, J., & Gould, M. (2018). *Trades, Quotes and Prices: Financial Markets Under the Microscope*. Cambridge UP. ISBN 9781107156050 — modern empirical microstructure; the impact / OFI / queue chapters complement Hasbrouck.
- Ferreira, M. A., & Santa-Clara, P. (2011). "Forecasting Stock Market Returns: The Sum of the Parts Is More Than the Whole." *Journal of Financial Economics* 100(3), 514-537. [DOI: 10.1016/j.jfineco.2011.02.003](https://doi.org/10.1016/j.jfineco.2011.02.003) — feature-decomposition arguments; useful for thinking about which features carry edge.
- Asness, C. S., Moskowitz, T. J., & Pedersen, L. H. (2013). "Value and Momentum Everywhere." *Journal of Finance* 68(3), 929-985. [DOI: 10.1111/jofi.12021](https://doi.org/10.1111/jofi.12021) — the canonical feature-as-factor reference for cross-sectional features.

### Tutorials & write-ups
- [Hudson & Thames Advances in Financial ML series](https://hudsonthames.org/articles/) — operational write-ups for every chapter of AFML
- [QuantConnect feature engineering tutorials](https://www.quantconnect.com/research/) — full pipelines with QuantConnect data
- [Marcos Lopez de Prado lectures (Cornell)](https://github.com/cornell-tech/financial-data-science) — pairing slides + code with AFML chapters
- [Stefan Jansen's Machine Learning for Trading book repo](https://github.com/stefan-jansen/machine-learning-for-trading) — the broadest open-source feature pipeline catalog

### Standard datasets / benchmarks
- The "100 random features" reproducibility test — generate 100 random walks, label them with triple-barrier, fit a model, compute deflated Sharpe; should reject all features. The standard sanity check for label/feature independence.
- AFML Ch. 3 example data — Dollar bar reconstruction from TAQ; the canonical reproduction case
- yfinance equity universe with point-in-time S&P 500 membership (CRSP for institutional) — the standard avoid-survivorship-bias benchmark

### Last cross-checked
2026-05-20 — via WebSearch verification of all paper DOIs + cross-check of mlfinlab / ta-lib / ta API surfaces.
