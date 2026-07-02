# Section D — Pattern recognition setups

## D.1 Chart-pattern recognition via CNN

When to use: you believe the *visual* shape of a chart carries information the underlying numeric features haven't encoded (debatable — see the DL decision tree). Useful when human traders use chart patterns and you want to backtest *whether the patterns themselves work*. **Cross-link to `cnn-pattern-recognition`** for chart rendering (GAFs, recurrence plots, raw images) and 1D vs 2D architectures. Wrap the CNN as sklearn-compatible (via `skorch`) so it can sit in a PyCaret / FLAML leaderboard.

## D.2 Sequence patterns via Transformers

When to use: long-range dependencies (>100 steps) that LSTMs lose. Self-attention helps when "what happened ~500 bars ago in a specific microstructure regime" matters.

**Recommendation:** start with a small encoder-only Transformer (4–6 layers, d_model=128, 4 heads) on positionally-encoded returns + book imbalance. Benchmark against an LSTM of equal parameter count. If the Transformer doesn't win by ≥5% relative AUC, you don't have a long-range problem and the LSTM is the right answer. For context >1000 steps, switch to linear-attention (Performer, Linformer) or state-space models (S4, Mamba). *Unverified for HFT — no published benchmarks on tick data; treat as research.*

## D.3 Anomaly detection — autoencoder, isolation forest, one-class SVM

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

## D.4 Clustering for regime discovery

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

## D.5 Topological data analysis (TDA) — `gudhi`, `giotto-tda`

Persistent homology measures multi-scale topological shape (loops, voids, components) of a point cloud. On finance: sliding-window embedding of returns → persistence diagrams → features (persistence entropy, lifetimes).

**Honest assessment:** TDA finance papers exist (e.g., Gidea-Katz 2018) but the signal is weak and rare at HFT scales; compute is heavy. **Recommendation:** don't add TDA features without a specific paper-backed reason — they will not earn compute on most tape-data problems. *Author opinion, not a cited empirical claim.*
