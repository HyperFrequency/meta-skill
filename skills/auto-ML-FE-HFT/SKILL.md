---
name: auto-ML-FE-HFT
description: Guided, opinionated playbook for AutoML, automated feature extraction, and HFT-specific indicators on price-feed data. Use when the user has tick / bar / L2 data and asks "what model should I train", "which features should I extract", "should I use deep learning here", "run AutoML on this price series", or names any of `h2o`, `autogluon`, `flaml`, `tpot`, `pycaret`, `tsfresh`, `featuretools`, `autofeat`, `mlfinlab`, `pandas-ta`, `ta-lib`, `finta`. Covers framework selection (H2O AutoML, AutoGluon, FLAML, TPOT, PyCaret), automated feature extraction (tsfresh, featuretools, autofeat), HFT indicator catalogue (realized vol, OFI, VPIN, Kyle's lambda, Hasbrouck, Hawkes, Roll, Amihud), pattern recognition (CNN charts, Transformer sequences, anomaly detection, regime clustering, TDA), neural-net training recipes per scenario, and an explicit decision tree for when deep learning earns its keep over boosting.
allowed-tools: Read, Write, Edit, Bash, Skill
license: HyperFrequency original
metadata:
    skill-author: HyperFrequency
    style: opinionated playbook with code
---

# Auto-ML + Automated Feature Extraction + HFT Indicator Catalogue

Opinionated walkthrough for "I have a price feed, what do I model and how". Picks an AutoML framework, runs automated FE on tick/bar/L2 data, surfaces the right HFT indicators, and tells you when DL is worth the GPU and when a boosted tree dominates. Grounded against canonical references and cross-linked to sibling skills rather than duplicating their math. Sections labelled **Recommendation** are author's call; **Fact** cites a paper.

## When to use

Use when you have tick / bar / L2 data and need to pick model class + feature set in one pass; want AutoML rather than hand-tuning; want automated feature extraction over raw tape; need a sober opinion on whether DL will beat XGBoost/LightGBM/CatBoost on your data; need an HFT indicator catalogue with code; or want to plug pattern-recognition into an automated pipeline.

Do **not** use for: pure microstructure derivation (`microstructure-analysis`); hand-tuning one learner (`xgboost` / `lightgbm` / `catboost` / `cnn-pattern-recognition`); hypothesis design (`ml-hypothesis-design` first); post-fit evaluation rigour (`model-evaluation`).

## The required tooling — unified gateway contract

Standard neuro-harness toolchain: Python 3.11+ in a `uv`-managed venv (pin via `uv-mcp`), Pandas/NumPy/pyarrow + parquet, scikit-learn 1.4+, Optuna for manual tuning, SHAP for interpretability (*unverified whether a dedicated in-repo `shap` skill exists; check local catalog*), and one of MLflow or W&B for tracking (don't mix).

Every production artefact must include: (1) a pinned lockfile (`uv pip compile`), (2) seeded randomness (`random_state=42` everywhere), (3) the feature matrix as parquet with a hash-stamped filename, (4) a Markdown experiment summary alongside the model artefact (Section G).

---

## Section A — AutoML framework comparison + canonical usage

### A.1 The framework matrix

| Framework  | Sweet spot                          | Compute     | TS native?               | Interpretability       | Wall-clock      |
|------------|-------------------------------------|-------------|--------------------------|------------------------|-----------------|
| H2O AutoML | Large tabular, distributed          | CPU (cluster)| Limited                 | High (leaderboard+viz) | Minutes–hours   |
| AutoGluon  | Mixed types, tabular+text+image+TS  | CPU + GPU   | Yes (TimeSeriesPredictor)| Medium                 | Minutes–hours   |
| FLAML      | Fast iteration, small budget        | CPU         | Limited                  | High (single learner)  | Seconds–minutes |
| TPOT       | Exportable sklearn pipelines (GP)   | CPU         | No                       | Very high (.py export) | Hours           |
| PyCaret    | Prototyping, EDA, low-code          | CPU + some GPU| Yes (TSForecasting)    | High (compare_models)  | Minutes         |

**Recommendation:** fresh CPU-only quant project — FLAML for a 30-min baseline, then H2O AutoML or AutoGluon for the production candidate. TPOT only when you need an exportable readable sklearn pipeline. PyCaret for EDA + leaderboard before committing. With heavy categoricals (symbol/exchange/regime), bypass AutoML and go to **CatBoost** (`catboost` skill) — the others mis-encode high-cardinality categoricals.

### A.2 H2O AutoML — canonical usage

Large tabular CPU; leaderboard across GLM/GBM/XGBoost/DL/stacked ensembles; distributed CPU > GPU.

```python
# H2O AutoML — binary direction classification. Verified API via Context7.
import h2o
from h2o.automl import H2OAutoML

h2o.init()  # spins up a local JVM cluster

train = h2o.import_file("features_train.parquet")  # or .csv
test  = h2o.import_file("features_test.parquet")

y = "direction"                       # 1 = up, 0 = down
x = [c for c in train.columns if c != y]

# Binary classification — response must be a factor.
train[y] = train[y].asfactor()
test[y]  = test[y].asfactor()

aml = H2OAutoML(
    max_runtime_secs=1800,            # 30 minutes
    sort_metric="AUC",
    nfolds=5,                          # k-fold; for time series, see note below
    balance_classes=True,
    seed=42,
)
aml.train(x=x, y=y, training_frame=train)

print(aml.leaderboard.head(20))       # ranked candidate models
perf = aml.leader.model_performance(test)
print(perf.auc(), perf.logloss())
```

**Time-series caveat:** H2O AutoML k-folds by default — pre-split chronologically and pass `validation_frame` or accept the leakage. Cross-link `model-evaluation` for the walk-forward pattern.

### A.3 AutoGluon — canonical usage (tabular + time-series)

Mixed data types or one-shot **TimeSeriesPredictor**. `presets='best_quality'` ensembles ~14 base learners — heavy on disk/RAM.

```python
# AutoGluon Tabular — direction classification. Verified via Context7.
from autogluon.tabular import TabularPredictor
import pandas as pd

train_df = pd.read_parquet("features_train.parquet")
test_df  = pd.read_parquet("features_test.parquet")

predictor = TabularPredictor(
    label="direction",
    eval_metric="roc_auc",
    path="./ag_tabular_run",
).fit(
    train_df,
    time_limit=1800,             # 30 minutes
    presets="best_quality",      # 'medium_quality' for faster baseline
)

print(predictor.leaderboard(test_df))
print(predictor.evaluate(test_df))
```

```python
# AutoGluon TimeSeries — panel multi-step forecast. Verified via Context7.
from autogluon.timeseries import TimeSeriesDataFrame, TimeSeriesPredictor

# Expect long-format dataframe: columns [item_id, timestamp, target, ...covariates].
ts_df = TimeSeriesDataFrame.from_data_frame(
    pd.read_parquet("panel.parquet"),
    id_column="symbol",
    timestamp_column="ts",
)

predictor = TimeSeriesPredictor(
    prediction_length=48,        # forecast horizon (e.g., 48 bars)
    target="close",
    eval_metric="MASE",
    quantile_levels=[0.1, 0.5, 0.9],   # probabilistic intervals
    path="./ag_ts_run",
).fit(
    ts_df,
    presets="medium_quality",    # 'best_quality' includes Chronos foundation models
    time_limit=1800,
)

forecasts = predictor.predict(ts_df)
print(predictor.leaderboard(ts_df))
```

### A.4 FLAML — canonical usage

CPU laptop, ≤5-min budget, baseline that beats default-hyperparameter XGBoost. CFO/BlendSearch converges fast on small budgets. *Inline API unverified — check `flaml --version`.*

```python
# FLAML AutoML — fast tabular baseline. NOT verified via Context7 — confirm against docs.
from flaml import AutoML
import pandas as pd

df = pd.read_parquet("features_train.parquet")
X = df.drop(columns=["direction"])
y = df["direction"]

automl = AutoML()
automl.fit(
    X_train=X, y_train=y,
    task="classification",
    metric="roc_auc",
    time_budget=300,              # 5 minutes
    estimator_list=["lgbm", "xgboost", "catboost", "rf", "extra_tree"],
    eval_method="cv",
    n_splits=5,
    seed=42,
)
print(automl.best_estimator, automl.best_config)
print("Best ROC AUC:", 1 - automl.best_loss)
```

### A.5 TPOT — canonical usage

Use when you need an **exportable sklearn pipeline as .py** — useful when ML governance demands you read every preprocessing step. Wall-clock expensive (GP).

```python
# TPOT — genetic programming over sklearn pipelines. Verified via Context7.
import tpot
import sklearn.datasets, sklearn.model_selection, sklearn.metrics

X, y = sklearn.datasets.load_breast_cancer(return_X_y=True)  # replace with your features
X_train, X_test, y_train, y_test = sklearn.model_selection.train_test_split(
    X, y, test_size=0.2, random_state=42
)

if __name__ == "__main__":      # TPOT requires guard when run from a script
    clf = tpot.TPOTClassifier(
        search_space="linear-light",
        scorers=["roc_auc_ovr"],
        scorers_weights=[1],
        cv=5,
        max_time_mins=30,
        max_eval_time_mins=5,
        n_jobs=4,
        early_stop=5,
        random_state=42,
        verbose=2,
    )
    clf.fit(X_train, y_train)
    auroc = sklearn.metrics.roc_auc_score(y_test, clf.predict_proba(X_test)[:, 1])
    print(f"AUROC: {auroc:.4f}")
    print(clf.fitted_pipeline_)   # exportable sklearn Pipeline
```

### A.6 PyCaret — canonical usage

Rapid prototyping, low-code, leaderboard-driven. Good for the first 30 min of a project; weaker for production hand-off.

```python
# PyCaret time-series forecasting — leaderboard + tuned model. Verified via Context7.
from pycaret.time_series import TSForecastingExperiment
import pandas as pd

y = pd.read_parquet("univariate_target.parquet")["close"]  # DateTimeIndex required

exp = TSForecastingExperiment()
exp.setup(
    data=y,
    fh=24,                       # forecast horizon
    fold=5,
    session_id=42,
)
best = exp.compare_models(sort="MASE", turbo=False)
tuned = exp.tune_model(best)
preds = exp.predict_model(tuned, fh=24)
```

### A.7 Cross-skill integration with `xgboost` / `lightgbm` / `catboost`

Every AutoML framework above tends to fit a boosted tree as the leader on tabular HFT data (matches Borisov 2022 — Section F). When the leaderboard picks XGBoost / LightGBM / CatBoost, hand off to the dedicated skill for walk-forward CV (`has_time=True` is CatBoost-only), categorical handling (CatBoost > LightGBM > XGBoost), GPU (`task_type="GPU"` for CatBoost, `tree_method="hist", device="cuda"` for XGBoost ≥2.0), and per-model SHAP.

---

## Section B — Automated feature extraction

### B.1 `tsfresh` — automated time-series feature computation

Computes hundreds of canonical TS features (autocorrelation, Fourier, entropy, peak counts, etc.) over rolled windows, then filters via **Benjamini-Yekutieli** FDR tests in `select_features`. Use any time you want a "kitchen sink + prune" feature matrix. Scale: `ComprehensiveFCParameters` ~750 features per series; `EfficientFCParameters` ~75; `MinimalFCParameters` ~10.

```python
# tsfresh — features on rolled price windows + BY-FDR filtering. Verified via Context7.
import pandas as pd
from tsfresh import extract_features, select_features
from tsfresh.utilities.dataframe_functions import roll_time_series, impute
from tsfresh.feature_extraction import EfficientFCParameters

# Long-format: one row per (symbol, ts), one column 'close' to featurise.
df_long = pd.read_parquet("ticks_long.parquet")[["symbol", "ts", "close"]]
df_long = df_long.sort_values(["symbol", "ts"]).reset_index(drop=True)

# Build rolling windows of length 60 bars per symbol.
df_rolled = roll_time_series(
    df_long,
    column_id="symbol",
    column_sort="ts",
    max_timeshift=59,
    min_timeshift=20,           # require ≥20 bars of context
    n_jobs=4,
)

X = extract_features(
    df_rolled,
    column_id="id",             # rolled-window id
    column_sort="ts",
    default_fc_parameters=EfficientFCParameters(),
    n_jobs=4,
)
impute(X)                        # tsfresh imputes inf / NaN in place

# Align labels to rolled windows (label at end-of-window).
y = df_long.groupby("symbol")["close"].pct_change(5).shift(-5)
y = y.reindex(X.index).dropna()
X = X.loc[y.index]

# Benjamini-Yekutieli filtering — keeps features with FDR-corrected significance.
X_selected = select_features(X, y, fdr_level=0.05)
print(X_selected.shape)          # << X.shape, only survivors remain
X_selected.to_parquet("tsfresh_selected.parquet")
```

**Pitfalls:** (1) `roll_time_series` is memory-hungry — chunk by symbol. (2) `select_features` assumes IID; for time-ordered data, select on the train slice only and apply that column subset to test. (3) Feature names are deterministic and verbose — store them.

### B.2 `featuretools` — Deep Feature Synthesis (DFS)

Automated feature construction over **relational** data (parent-child tables). Stacks primitives (mean, max, time-since-last, count-distinct) across foreign keys. *Not found in Context7; snippet reflects documented v1.x public API — verify against install.* Use for cross-asset / multi-venue panels with a "trades → symbols" relationship. For univariate price series, tsfresh dominates.

```python
# featuretools — DFS across (symbols ← trades). NOT verified via Context7 — confirm.
import featuretools as ft
import pandas as pd

symbols = pd.read_parquet("symbols.parquet")   # symbol, sector, exchange, ...
trades  = pd.read_parquet("trades.parquet")    # trade_id, symbol, ts, size, side, ...

es = ft.EntitySet(id="hft")
es = es.add_dataframe(dataframe_name="symbols", dataframe=symbols, index="symbol")
es = es.add_dataframe(
    dataframe_name="trades",
    dataframe=trades,
    index="trade_id",
    time_index="ts",
)
es = es.add_relationship("symbols", "symbol", "trades", "symbol")

feature_matrix, feature_defs = ft.dfs(
    entityset=es,
    target_dataframe_name="symbols",
    agg_primitives=["mean", "std", "max", "min", "count", "num_unique"],
    trans_primitives=["time_since_previous", "hour", "day", "weekday"],
    max_depth=2,
    cutoff_time=pd.Timestamp("2025-05-01"),     # no leakage past this timestamp
)
feature_matrix.to_parquet("dfs_features.parquet")
```

### B.3 `autofeat` — automatic non-linear feature construction

Generates non-linear feature combinations (ratios, products, log/sqrt transforms) and prunes with L1 regression. Use when you suspect alpha lives in interactions you don't want to hand-craft.

```python
# autofeat — non-linear feature construction. NOT verified via Context7 — confirm.
from autofeat import AutoFeatRegressor
import pandas as pd

df = pd.read_parquet("features_numeric.parquet")
X, y = df.drop(columns=["fwd_return"]), df["fwd_return"]

afr = AutoFeatRegressor(
    feateng_steps=2,            # depth of feature engineering
    featsel_runs=3,             # repeated L1 selection
    transformations=("1/", "log", "abs", "sqrt", "exp"),
    n_jobs=4,
)
X_new = afr.fit_transform(X, y)
print(X_new.shape, afr.new_feat_cols_)
```

### B.4 HFT-specific indicator libraries

Pick **one** per project (mixing yields inconsistent column naming). **`ta-lib`** — C-backed, fastest, ~150 classical indicators; painful install (system C dep), use `TA-Lib` pip wheel or conda-forge. **`pandas-ta`** — pure-Python pandas-native (`df.ta.<indicator>`), ~130 indicators, slower but trivial install. **`finta`** — small pure-Python, ~80 indicators, simplest API; use when others fail. **`mlfinlab`** — Hudson & Thames' López de Prado toolkit (triple-barrier, fractional diff, meta-labelling, dollar/imbalance bars); not a general indicator library — cross-link `feature-engineering`.

Minimal `pandas-ta` example:

```python
# pandas-ta — apply a standard indicator suite to OHLCV.
import pandas as pd
import pandas_ta as ta

df = pd.read_parquet("ohlcv_1m.parquet")     # cols: open, high, low, close, volume
df.ta.strategy("AllStrategy", verbose=False)  # adds ~70 indicators in place
# Or pick specific ones:
df["rsi_14"] = df.ta.rsi(length=14)
df["atr_14"] = df.ta.atr(length=14)
df["adx_14"] = df.ta.adx(length=14)["ADX_14"]
df["macd_hist"] = df.ta.macd()["MACDh_12_26_9"]
```

### B.5 Microstructure features — cross-link, don't duplicate

For order-book features (OFI, queue position, footprint, tick-rule sign, Lee-Ready, Kyle's lambda) use **`microstructure-analysis`**. This skill consumes the resulting columns. Section C covers *which* microstructure indicators to compute; the math lives there.

### B.6 Feature selection — pruning the kitchen sink

After tsfresh / featuretools / autofeat / ta-lib you typically have 500–5000 features. Four canonical pruners, increasing rigour: **permutation importance** (sklearn, fast, biased toward correlated features); **BorutaPy** (RF + shadow features, rigorous, slow); **mRMR** (informative + mutually decorrelated; package `mrmr-selection`); **SHAP-based ranking** (boosted tree → global mean-|SHAP| threshold; use the `shap` skill).

```python
# BorutaPy on RF backbone for HFT feature pruning. NOT verified via Context7 — confirm.
from boruta import BorutaPy
from sklearn.ensemble import RandomForestClassifier
import pandas as pd

X = pd.read_parquet("tsfresh_selected.parquet").values
y = pd.read_parquet("labels.parquet")["direction"].values

rf = RandomForestClassifier(
    n_estimators=200, n_jobs=-1, class_weight="balanced", max_depth=8, random_state=42
)
boruta = BorutaPy(rf, n_estimators="auto", random_state=42, verbose=1, max_iter=50)
boruta.fit(X, y)

X_pruned = X[:, boruta.support_]
print("Confirmed features:", boruta.support_.sum())
print("Tentative:", boruta.support_weak_.sum())
```

**Recommendation:** for HFT direction-classification, run mRMR first (cheap), then BorutaPy on survivors. Skip permutation importance unless you want a per-feature ablation story.

---

## Section C — HFT indicator catalogue

Each entry: intuition + ≤25-line code + when-to-use. Cross-link where the math has its own skill home.

### C.1 Realized volatility with bipower variation jump component

Realized variance = sum of squared intraday returns. **Bipower variation** (Barndorff-Nielsen & Shephard 2004) = sum of products of adjacent absolute returns — jump-robust. The gap `RV − BV` isolates the jump contribution. Use jump-detected vol when news events drive your asset.

```python
# Realized volatility + bipower variation jump detection.
import numpy as np
import pandas as pd

def realized_vol(returns: pd.Series, window: int) -> pd.DataFrame:
    rv = returns.pow(2).rolling(window).sum()
    bv = (returns.abs() * returns.abs().shift(1)).rolling(window).sum() * (np.pi / 2)
    jump = (rv - bv).clip(lower=0)
    return pd.DataFrame({
        "rv": rv,
        "bv": bv,
        "jump_component": jump,
        "rv_annualized": np.sqrt(rv * (252 * 1440 / window)),  # 1-min bars → annualised
    })

r = pd.read_parquet("returns_1m.parquet")["log_ret"]
features = pd.concat([
    realized_vol(r, w).add_suffix(f"_{w}m") for w in (5, 60, 1440)
], axis=1)
```

When to use: any model where conditional vol matters — direction, vol-of-vol carry, breakout detection. Pairs with `garch-volatility` for parametric forecasts.

### C.2 Order-flow toxicity (VPIN) — cross-link

VPIN (Easley-López de Prado-O'Hara 2012) = buy/sell volume imbalance in volume-time buckets. High VPIN → toxic flow → execution risk. **See `microstructure-analysis`.** Consume as a column; don't recompute here.

### C.3 Order-flow imbalance (OFI) — cross-link

OFI = signed sum of top-of-book quantity changes (Cont-Kukanov-Stoikov 2014). Sharp predictor of next-second mid-price moves. **See `microstructure-analysis`.**

### C.4 Effective / realized / quoted spread

**Quoted** = `ask − bid` at trade time. **Effective** = `2·|P_t − M_t|` (actual trade cost vs mid). **Realized** = `2·D_t·(P_t − M_{t+5min})` (cost net of permanent impact).

```python
# Quoted, effective, realized spread on a trades-with-quotes table.
import pandas as pd

q = pd.read_parquet("quotes.parquet")           # ts, bid, ask, mid
tr = pd.read_parquet("trades.parquet")          # ts, price, size, side (+1 buy / -1 sell)
tr = pd.merge_asof(tr.sort_values("ts"), q.sort_values("ts"), on="ts", direction="backward")

tr["quoted_spread"]   = tr["ask"] - tr["bid"]
tr["effective_spread"]= 2.0 * (tr["price"] - tr["mid"]).abs()

# Realized spread vs mid 5 minutes ahead.
future_mid = q.set_index("ts")["mid"].reindex(
    tr["ts"] + pd.Timedelta("5min"), method="nearest"
).values
tr["realized_spread"] = 2.0 * tr["side"] * (tr["price"] - future_mid)
```

When to use: execution cost models, market-making calibration, TCA on backtests.

### C.5 Trade-sign autocorrelation (Bouchaud et al.)

Trade signs are heavily autocorrelated at HFT scales — Bouchaud-Farmer-Lillo (2009) document power-law decay over hundreds of trades. Use lag-k autocorrelation as a feature; anomalously low → regime shift.

```python
# Trade-sign autocorrelation at multiple lags.
import pandas as pd

signs = pd.read_parquet("trades.parquet")["side"]  # ±1
acf = pd.Series({
    f"sign_acf_lag_{k}": signs.autocorr(lag=k) for k in (1, 5, 10, 50, 100, 500)
})
```

When to use: trade-flow continuation, market-impact models, regime detection.

### C.6 Roll's spread estimator

Roll (1984): `effective_spread ≈ 2·sqrt(−Cov(Δp_t, Δp_{t−1}))` when autocovariance is negative (bid-ask bounce). Cheap spread proxy from trade prices alone — use when quotes are missing.

```python
# Roll's implicit spread from trade-price autocovariance.
import numpy as np
import pandas as pd

def roll_spread(prices: pd.Series, window: int = 1000) -> pd.Series:
    dp = prices.diff()
    cov = dp.rolling(window).cov(dp.shift(1))
    return 2.0 * np.sqrt((-cov).clip(lower=0))

spread_proxy = roll_spread(pd.read_parquet("trades.parquet")["price"])
```

When to use: quote-poor venues, pre-2010 historical backtests.

### C.7 Amihud illiquidity ratio

Amihud (2002): `ILLIQ_t = |return_t| / dollar_volume_t`. Big return on low volume → illiquid. Strong cross-sectional risk factor, useful conditioning feature.

```python
# Amihud illiquidity at daily or intraday scale.
import pandas as pd

df = pd.read_parquet("ohlcv.parquet")
df["dollar_volume"] = df["close"] * df["volume"]
df["amihud_illiq"] = df["close"].pct_change().abs() / df["dollar_volume"].replace(0, pd.NA)
df["amihud_illiq_20"] = df["amihud_illiq"].rolling(20).mean()
```

When to use: cross-asset conditioning, TCA models, sizing constraints.

### C.8 Kyle's lambda — cross-link

Kyle (1985) `λ` is the slope of price impact per unit signed volume: `Δp_t ≈ λ · signed_volume_t`. Higher λ → less liquidity. **See `microstructure-analysis`.** Use rolling-windowed λ as a feature.

### C.9 Hasbrouck information share (multi-venue same asset)

Hasbrouck (1995) decomposes the variance of the common efficient price into per-venue contributions; the highest-share venue is the price leader. Non-trivial: VECM + Cholesky bounds — use `mlfinlab.microstructural_features` or hand-roll via statsmodels. **Recommendation:** do not roll Hasbrouck at HFT cadence; compute monthly on full panels and treat as a slow conditioning variable.

```python
# Sketch only — implementation requires VECM. See mlfinlab.microstructural_features.
# Expect ~100 lines or a library call.
```

### C.10 Hawkes self-exciting intensity — cross-link

Hawkes processes model self- and cross-excitation: a trade raises the probability of another nearby. Intensity `λ(t)` is itself a feature — high intensity → continued activity. **See [`microstructure-analyst`](../microstructure-analyst/SKILL.md) §C.Hawkes for the implementation, and [`microstructure-feature-engineering`](../microstructure-feature-engineering/SKILL.md) for the bar-aligned feature.** No standalone `hawkes-process` skill exists; Hawkes is owned by the two microstructure skills above.

### C.11 Realized skewness and kurtosis at intraday scale

Higher moments of intraday returns are predictive (Amaya-Christoffersen-Jacobs-Vasquez 2015 — realized skew predicts cross-sectional next-week returns). Cheap to compute, often missed.

```python
# Intraday realized skewness and kurtosis over rolling windows.
import pandas as pd

r = pd.read_parquet("returns_1m.parquet")["log_ret"]
rskew = r.pow(3).rolling(390).sum() / (r.pow(2).rolling(390).sum().pow(1.5))
rkurt = r.pow(4).rolling(390).sum() / (r.pow(2).rolling(390).sum().pow(2))
features = pd.DataFrame({"rskew_1d": rskew, "rkurt_1d": rkurt})
```

When to use: as conditioning features for tail-risk models, for cross-sectional ranking, alongside realized vol.

---

## Section D — Pattern recognition setups

### D.1 Chart-pattern recognition via CNN

When to use: you believe the *visual* shape of a chart carries information the underlying numeric features haven't encoded (debatable — Section F). Useful when human traders use chart patterns and you want to backtest *whether the patterns themselves work*. **Cross-link to `cnn-pattern-recognition`** for chart rendering (GAFs, recurrence plots, raw images) and 1D vs 2D architectures. Wrap the CNN as sklearn-compatible (via `skorch`) so it can sit in a PyCaret / FLAML leaderboard.

### D.2 Sequence patterns via Transformers

When to use: long-range dependencies (>100 steps) that LSTMs lose. Self-attention helps when "what happened ~500 bars ago in a specific microstructure regime" matters.

**Recommendation:** start with a small encoder-only Transformer (4–6 layers, d_model=128, 4 heads) on positionally-encoded returns + book imbalance. Benchmark against an LSTM of equal parameter count. If the Transformer doesn't win by ≥5% relative AUC, you don't have a long-range problem and the LSTM is the right answer. For context >1000 steps, switch to linear-attention (Performer, Linformer) or state-space models (S4, Mamba). *Unverified for HFT — no published benchmarks on tick data; treat as research.*

### D.3 Anomaly detection — autoencoder, isolation forest, one-class SVM

For HFT, anomaly = "this bar / order / trade doesn't look like the recent past". Use cases: flash-crash detection, spoofing, pre-directional regime breaks.

**Isolation Forest** (sklearn) — first choice; cheap, robust. **One-class SVM** (sklearn) — heavier, kernel-sensitive; use only with a clear "normal" regime. **Autoencoder** — cross-link `autoencoder-anomaly-detection`; use when the anomaly lives in feature *correlations*. **PyOD** — meta-library wrapping all three plus ~40 more.

```python
# Isolation Forest on a rolling HFT feature matrix.
from sklearn.ensemble import IsolationForest
import pandas as pd

X = pd.read_parquet("features.parquet")
iso = IsolationForest(
    n_estimators=200, contamination=0.01, random_state=42, n_jobs=-1
)
iso.fit(X.iloc[:100000])                       # fit on a normal-regime training slice
X["anomaly_score"] = -iso.score_samples(X)     # higher = more anomalous
X["is_anomaly"] = iso.predict(X) == -1
```

### D.4 Clustering for regime discovery

Cluster windowed feature vectors and use the cluster id as a regime label. **K-Means** — cheap, requires preset `k`, assumes convex equal-size regimes. **GMM** — softer, gives probability-of-regime, handles overlap. **DBSCAN / HDBSCAN** — density-based, arbitrary shapes + outliers. **Recommendation:** HDBSCAN is the default for HFT regime work (`min_cluster_size=50` is a sane start). **HMM** — explicit temporal structure; cross-link `markov-regime-detection`.

```python
# HDBSCAN regime clustering over windowed realized-vol + skew + kurt features.
import hdbscan
import pandas as pd

X = pd.read_parquet("rolling_moments.parquet")[["rv_60m", "rskew_1d", "rkurt_1d"]].dropna()
clusterer = hdbscan.HDBSCAN(min_cluster_size=50, min_samples=10, prediction_data=True)
labels = clusterer.fit_predict(X)
X["regime"] = labels   # −1 = noise
```

### D.5 Topological data analysis (TDA) — `gudhi`, `giotto-tda`

Persistent homology measures multi-scale topological shape (loops, voids, components) of a point cloud. On finance: sliding-window embedding of returns → persistence diagrams → features (persistence entropy, lifetimes).

**Honest assessment:** TDA finance papers exist (e.g., Gidea-Katz 2018) but the signal is weak and rare at HFT scales; compute is heavy. **Recommendation:** don't add TDA features without a specific paper-backed reason — they will not earn compute on most tape-data problems. *Author opinion, not a cited empirical claim.*

---

## Section E — NN training techniques per scenario (sharp opinions)

Each scenario is a Recommendation. Baseline = **XGBoost / LightGBM / CatBoost first**; justify the DL step with a quantified gap.

- **E.1 Tabular HFT, ≤1M rows.** Boosting (XGBoost / LightGBM / CatBoost). **Skip DL.** Borisov 2022 + Shwartz-Ziv 2021 find boosting wins on tabular below ~10M rows; tabular NNs (TabNet, SAINT, FT-Transformer) only catch up at scale. Spend time on features.
- **E.2 Tabular HFT, >>1M rows + heavy categoricals.** CatBoost `task_type="GPU"` first. If >50M rows AND boosting plateaus, try a tabular Transformer (SAINT, FT-Transformer). In HFT you can usually downsample / debias before that.
- **E.3 Sequence data, short horizon (≤30 steps).** LSTM + attention head, or small Transformer encoder (2–4 layers). Gap is small; pick what your team maintains.
- **E.4 Sequence data, long context (>1000 steps).** Linear-attention Transformer (Performer / Linformer) or state-space model (S4 / Mamba). Skip vanilla O(n²) attention. Mamba is plausibly the right inductive bias for HFT but evidence is thin. *Unverified for HFT.*
- **E.5 Image-encoded charts.** Small ResNet (ResNet-18, ImageNet pretrain, finetune last block) on 224×224 candle/volume renders. Or a Conv1D-on-features → Conv2D-on-image hybrid. **Cross-link `cnn-pattern-recognition`.**
- **E.6 Multi-modal (price + news + on-chain).** Per-modality encoders (Transformer for price, pretrained LM for news, MLP for on-chain), late-fusion into a shared head. Train with modality-dropout (randomly zero one modality) to prevent collapse.
- **E.7 High noise → low signal.** Denoise with wavelet (cross-link `wavelet-decomposition`) before training. Stronger `weight_decay` (`1e-3` start), higher dropout, label smoothing. If SNR < 1 no architecture saves you — improve features.
- **E.8 Class imbalance (rare events).** Priority order: (1) probability-threshold tuning over a fine grid; (2) `class_weight={0:1, 1:imbalance_ratio}`; (3) focal loss (`α=0.25, γ=2.0`, Lin 2017); (4) SMOTE on train only. Do **not** undersample majority — you discard information.
- **E.9 Regime breaks.** Either per-regime models (cross-link `markov-regime-detection` for the gating model) or a single model with regime appended as a one-hot. Single-model usually wins on data efficiency; per-regime wins when regimes are economically distinct.
- **E.10 RL when action affects market.** Only when your action changes the next state (large orders moving the book, market-making fills). Otherwise supervised alpha + sizing rule dominates with less training instability. **Cross-link `deep-q-learning`, `policy-gradients`.**

---

## Section F — When to apply deep learning (decision tree)

Walk this in order. Stop at the first **No** that disqualifies deep learning.

```
Q1. Do you have ≥100K labelled rows?
    No  → boosting (XGBoost / LightGBM / CatBoost). Stop.
    Yes → Q2.

Q2. Does sequence / spatial structure matter for the prediction?
    (i.e., would shuffling row order destroy the signal?)
    No  → boosting will dominate. Borisov 2022 / Shwartz-Ziv 2021. Stop.
    Yes → Q3.

Q3. Do you have GPU budget for both initial training AND a retrain cycle?
    (Retraining on stale models is the #1 killer of HFT DL in production.)
    No  → boosting on CPU. Stop.
    Yes → Q4.

Q4. Is interpretability a release requirement?
    (Risk team needs SHAP attributions, counterfactuals, monotonicity constraints.)
    Yes → boosting + SHAP, OR deep model wrapped in SHAP DeepExplainer + counterfactual
          notebooks. Add ~2 weeks of work and a tighter MRM review. Proceed only if
          the deep model has a quantified accuracy gap over boosting that justifies the cost.
    No  → Q5.

Q5. Is your label noisy at the per-sample level?
    (Per-tick noise typically >> than your alpha signal.)
    Yes → use boosting with regularization, or a deep model with heavy weight decay +
          label smoothing + Mixup-style data augmentation. Increased risk of overfitting.
    No  → Q6.

Q6. Do you need to combine modalities (price + book + news + sentiment + macro)?
    Yes → deep multi-modal architecture is the right choice (Section E.6).
    No  → Q7.

Q7. Is your effective context length >1000 steps AND the dependency is non-Markovian?
    (i.e., 30-step LSTM truly cannot capture the signal.)
    Yes → Transformer / linear-attention / SSM. Section E.4.
    No  → small LSTM or just engineered lag features into boosting wins.

Q8. Have you already exhausted feature engineering on a boosting baseline?
    (You can recite the top-10 SHAP features and tell a microstructure story for each.)
    Yes → deep learning is the next legitimate experiment.
    No  → go back to features. Boosting + features is almost always the right answer.
```

**Fact** (cited): Borisov et al. (2022) "Deep Neural Networks and Tabular Data: A Survey" (TNNLS) finds gradient-boosted decision trees outperform deep tabular models on most benchmark datasets. Shwartz-Ziv & Armon (2021) "Tabular Data: Deep Learning Is Not All You Need" (NeurIPS workshop) reaches the same conclusion across 11 datasets.

**Recommendation** (opinionated): in 5+ years of HFT work, the single most common failure mode is "we trained a fancy Transformer because we had GPUs" rather than "we asked whether a boosted tree on better features would have been enough". Default to boosting. Earn the right to use deep learning.

---

## Section G — Reasoning + documentation discipline

Every experiment must produce four artefacts. No exceptions.

### G.1 Hypothesis preregistration

Before any AutoML run, write down: (1) the null hypothesis ("5-min forward return is unpredictable from features X"), (2) test statistic + rejection threshold, (3) train/val/test slice boundaries with timestamps, (4) pre-specified evaluation metric. **Cross-link `ml-hypothesis-design`** for Deflated Sharpe corrections and minimum backtest length.

### G.2 Evaluation rigor

**Cross-link `model-evaluation`** for walk-forward CV, purged k-fold, embargo design, Probability of Backtest Overfitting (PBO), Deflated Sharpe. No model graduates to production without: walk-forward OOS over ≥5 retraining windows; embargo gap ≥ label horizon; DSR computed against the number of trials.

### G.3 Documentation — the mandatory experiment summary

Every experiment commits a Markdown file alongside the model artefact:

```markdown
# Experiment 2026-05-20-btc-perp-direction

**Hypothesis.** 1-min forward direction on BTC perp is predictable from tsfresh + microstructure features.

**Data.** <venue> trades + L2, 2024-01-01 → 2026-04-30. SHA256(features.parquet): <hash>.
Train 2024-01-01 → 2025-12-31; Test 2026-01-01 → 2026-04-30; Embargo 5 minutes.

**Feature set.** tsfresh EfficientFCParameters (60-bar windows, rolled per symbol);
pandas-ta RSI(14)/ATR(14)/MACD-hist/ADX(14);
microstructure OFI top-5, VPIN(50), Kyle's lambda(1000), trade-sign ACF lags {1,5,50};
after mRMR(k=100) + BorutaPy: 47 surviving features.

**Model.** CatBoostClassifier GPU, depth=6, iterations=2000, l2_leaf_reg=3.0, lr=0.05,
early_stopping_rounds=100, eval_metric=AUC.

**Metrics (test OOS).** ROC AUC 0.547; Brier 0.244; PF (long top-decile) 1.18; Deflated Sharpe (250 trials) 0.34.

**Decision.** Borderline. Re-running with regime-aware splitting before production.
```

### G.4 Reproducibility

Pin via **`uv-mcp`** (`uv pip compile pyproject.toml -o uv.lock`). Seed everything: `random_state=42`, `np.random.seed(42)`, `torch.manual_seed(42)`, AutoML `seed=42`. Store the feature matrix as parquet with a hash-stamped name (`features_<git_sha>_<sha256[:8]>.parquet`). Log the full AutoML leaderboard, not just the leader.

---

## End-to-end worked example

Concrete case: **BTC perp 1-min bars + L2 → tsfresh feature extraction → BorutaPy selection → CatBoost classifier → walk-forward CV → tearsheet.**

```python
# end_to_end.py — full pipeline. Run as: uv run python end_to_end.py
import hashlib
import numpy as np
import pandas as pd
from pathlib import Path

# 1. Load raw inputs.
trades = pd.read_parquet("data/btcusdt_perp_trades.parquet")     # ts, price, size, side
quotes = pd.read_parquet("data/btcusdt_perp_l2_top5.parquet")    # ts, bid_n, ask_n, bid_q_n, ask_q_n

# 2. 1-min OHLCV bars + microstructure aggregates.
trades["ts"] = pd.to_datetime(trades["ts"])
bars = trades.set_index("ts").resample("1min").agg(
    open=("price", "first"), high=("price", "max"),
    low=("price", "min"),    close=("price", "last"),
    volume=("size", "sum"),  trade_count=("price", "count"),
)
bars["log_ret"] = np.log(bars["close"]).diff()

# OFI top-5 — derivation in microstructure-analysis; assume precomputed.
ofi = pd.read_parquet("data/btc_ofi_top5_1min.parquet")
bars = bars.join(ofi, how="left")

# 3. tsfresh on rolled log-return windows.
from tsfresh import extract_features, select_features
from tsfresh.utilities.dataframe_functions import roll_time_series, impute
from tsfresh.feature_extraction import EfficientFCParameters

long = bars.reset_index().assign(symbol="BTC")[["symbol", "ts", "log_ret"]].dropna()
rolled = roll_time_series(long, column_id="symbol", column_sort="ts",
                          max_timeshift=59, min_timeshift=20, n_jobs=4)
X_ts = extract_features(rolled, column_id="id", column_sort="ts",
                        default_fc_parameters=EfficientFCParameters(), n_jobs=4)
impute(X_ts)

# Label: sign of 5-min forward return, embargoed.
y = np.sign(bars["log_ret"].rolling(5).sum().shift(-5)).rename("direction")
y = y.replace({-1: 0, 1: 1}).dropna().astype(int)

# Align X to y by end-of-window timestamp.
X_ts.index = X_ts.index.get_level_values(1)
X = X_ts.join(bars[["ofi_top5_sum"]], how="inner").join(y, how="inner")
X, y_aligned = X.drop(columns=["direction"]), X["direction"]

# 4. Time-ordered train/test split.
split_ts = pd.Timestamp("2026-01-01")
train_mask = X.index < split_ts
X_tr, y_tr = X.loc[train_mask], y_aligned.loc[train_mask]
X_te, y_te = X.loc[~train_mask], y_aligned.loc[~train_mask]

# 5. tsfresh select_features on TRAINING ONLY.
X_tr_sel = select_features(X_tr, y_tr, fdr_level=0.05)
keep_cols = X_tr_sel.columns.tolist()
X_te_sel = X_te[keep_cols]

# 6. BorutaPy on tsfresh survivors.
from boruta import BorutaPy
from sklearn.ensemble import RandomForestClassifier
rf = RandomForestClassifier(n_estimators=200, n_jobs=-1, max_depth=8,
                            class_weight="balanced", random_state=42)
boruta = BorutaPy(rf, n_estimators="auto", random_state=42, max_iter=30)
boruta.fit(X_tr_sel.values, y_tr.values)
final_cols = X_tr_sel.columns[boruta.support_].tolist()
X_tr_final = X_tr_sel[final_cols]
X_te_final = X_te_sel[final_cols]

# 7. CatBoost classifier.
from catboost import CatBoostClassifier
clf = CatBoostClassifier(
    iterations=3000, depth=6, learning_rate=0.05, l2_leaf_reg=3.0,
    eval_metric="AUC", task_type="GPU",
    early_stopping_rounds=200, random_seed=42, verbose=200,
)
clf.fit(X_tr_final, y_tr, eval_set=(X_te_final, y_te))

# 8. Walk-forward CV — see model-evaluation for the rigorous template.
from sklearn.model_selection import TimeSeriesSplit
tss = TimeSeriesSplit(n_splits=5, gap=5)   # embargo == label horizon
oos_aucs = []
for tr_idx, te_idx in tss.split(X_tr_final):
    fold = CatBoostClassifier(iterations=2000, depth=6, learning_rate=0.05,
                              eval_metric="AUC", verbose=0, random_seed=42)
    fold.fit(X_tr_final.iloc[tr_idx], y_tr.iloc[tr_idx],
             eval_set=(X_tr_final.iloc[te_idx], y_tr.iloc[te_idx]))
    oos_aucs.append(fold.best_score_["validation"]["AUC"])
print(f"Walk-forward AUC: {np.mean(oos_aucs):.3f} ± {np.std(oos_aucs):.3f}")

# 9. Tearsheet — cross-link tearsheet-generator for QuantStats.
proba = clf.predict_proba(X_te_final)[:, 1]
signal = pd.Series(proba > 0.55, index=X_te_final.index).astype(int)
fwd_ret = bars["log_ret"].shift(-1).loc[X_te_final.index].fillna(0)
strat_ret = signal * fwd_ret
print("Test Sharpe (annualised, 1-min bars):",
      strat_ret.mean() / strat_ret.std() * np.sqrt(252 * 1440))

# 10. Persist + experiment summary.
out_dir = Path("artefacts") / f"btc_perp_direction_{pd.Timestamp.now():%Y%m%d_%H%M%S}"
out_dir.mkdir(parents=True, exist_ok=True)
X.to_parquet(out_dir / "features.parquet")
clf.save_model(str(out_dir / "catboost.cbm"))
feat_hash = hashlib.sha256(open(out_dir / "features.parquet", "rb").read()).hexdigest()[:8]
(out_dir / "summary.md").write_text(
    f"Feature SHA: {feat_hash}\nWalk-forward AUC: {np.mean(oos_aucs):.3f}\n"
)
```

Adapt data path, symbol, and label — you have a defensible end-to-end run.

---

## Common pitfalls

1. **K-fold CV on time-ordered HFT data.** AutoML defaults shuffle. Override with `TimeSeriesSplit`, walk-forward, or `nfolds=0 + validation_frame=`.
2. **tsfresh `select_features` on combined train+test.** Leaks test labels. Select on train only; apply the column subset to test.
3. **Leaderboard 0.91 AUC → live 55% accuracy.** Almost always feature-matrix leakage or shuffled CV. Audit before deploying.
4. **Treating tsfresh as a black box.** ComprehensiveFCParameters ~750 features; some are correlated with rolling means at trivially small lags and leak if your label horizon is short. Read surviving feature names.
5. **One-hot encoding high-cardinality categoricals into AutoGluon / FLAML / TPOT.** Symbol/venue blow up dimensionality. Use CatBoost (native) or target-encode first.
6. **SMOTE on test, or on the full set before splitting.** SMOTE is training-only.
7. **Deep learning on <1M tabular HFT rows** (Borisov 2022 / Shwartz-Ziv 2021). Don't.
8. **TDA features for sophistication.** Compute cost > signal at HFT scale.
9. **Skipping the experiment summary "to move faster".** You'll rediscover the same dead-ends in 6 months.
10. **Not pinning AutoML versions.** AutoGluon / FLAML / TPOT break APIs regularly. Lock in `uv.lock`.

---

## References

**AutoML frameworks** (APIs verified via Context7 unless noted). LeDell & Poirier (2020), H2O AutoML, ICML AutoML workshop. Erickson et al. (2020), AutoGluon-Tabular, arXiv:2003.06505. Ansari et al. (2024), Chronos foundation model used by AutoGluon-TS, arXiv:2403.07815. Wang et al. (2021), FLAML, MLSys *(inline API unverified — confirm)*. Le-Fu-Moore (2020), TPOT, Bioinformatics. Ali (2020), PyCaret.

**Automated feature extraction.** Christ-Braun-Neuffer-Kempa-Liehr (2018), tsfresh, Neurocomputing (BY-FDR in `select_features`). Kanter & Veeramachaneni (2015), Deep Feature Synthesis (featuretools), IEEE DSAA. Horn-Pack-Rieger (2020), autofeat, arXiv:1901.07329.

**HFT indicators.** Barndorff-Nielsen & Shephard (2004), bipower variation. Easley-López de Prado-O'Hara (2012), VPIN, RFS. Cont-Kukanov-Stoikov (2014), OFI, JFE. Kyle (1985), Econometrica. Roll (1984), JF. Amihud (2002), JFM. Hasbrouck (1995), JF. Bouchaud-Farmer-Lillo (2009), Handbook of Financial Markets. Amaya-Christoffersen-Jacobs-Vasquez (2015), realized skewness, JFE.

**Pattern recognition / DL claims.** **Borisov et al. (2022)**, Deep NN + Tabular Data: A Survey, IEEE TNNLS — canonical "boosting beats DL on tabular". **Shwartz-Ziv & Armon (2021)**, Tabular DL Is Not All You Need, NeurIPS workshop — confirms across 11 datasets. Lin et al. (2017), Focal loss, ICCV. Gidea & Katz (2018), TDA on finance, Physica A. Gu-Kelly-Xiu (2020), Empirical Asset Pricing via ML, RFS. López de Prado (2018), *Advances in Financial Machine Learning*.

**Cross-linked sibling skills.** `microstructure-analysis` (OFI/VPIN/Kyle/trade classification), `feature-engineering` (leakage-safe pipelines, triple-barrier), `xgboost`/`lightgbm`/`catboost` (boosted trees), `cnn-pattern-recognition` (1D/2D CNNs), `wavelet-decomposition` (DWT/CWT denoising), `markov-regime-detection` (HMM regimes, Section E.9), `autoencoder-anomaly-detection` (Section D.3), `model-evaluation` (walk-forward, PBO, DSR), `ml-hypothesis-design` (Section G.1), `deep-q-learning`/`policy-gradients` (Section E.10), `garch-volatility` (Section C.1), `tearsheet-generator` (reporting), `uv-mcp` (lockfiles).

**Unverified — confirm before shipping.** FLAML inline API (A.4); featuretools `add_relationship` signature (B.2, changed in 1.x); `AutoFeatRegressor` constructor (B.3); BorutaPy package name on PyPI (B.6 + end-to-end); TDA-doesn't-pay claim (D.5, author opinion); S4/Mamba performance on tick-level HFT (E.4, no published benchmarks).

**Confirmed cross-link targets (2026-05-20):** `shap` → `k-dense-scientific-agent-skills/shap/`; `multimodal` → `neuro-centrifuge/multimodal/` (Orchestra AI Research set); no standalone `hawkes-process` — Hawkes is in `microstructure-analyst` §C.Hawkes and `microstructure-feature-engineering`.
