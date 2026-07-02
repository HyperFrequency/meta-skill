# Section B — Automated feature extraction

## B.1 `tsfresh` — automated time-series feature computation

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

## B.2 `featuretools` — Deep Feature Synthesis (DFS)

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

## B.3 `autofeat` — automatic non-linear feature construction

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

## B.4 HFT-specific indicator libraries

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

## B.5 Microstructure features — cross-link, don't duplicate

For order-book features (OFI, queue position, footprint, tick-rule sign, Lee-Ready, Kyle's lambda) use **`microstructure-analysis`**. This skill consumes the resulting columns. The HFT indicator catalogue covers *which* microstructure indicators to compute; the math lives there.

## B.6 Feature selection — pruning the kitchen sink

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
