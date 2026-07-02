# Section G — Reasoning + documentation discipline, worked example, pitfalls, references

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
