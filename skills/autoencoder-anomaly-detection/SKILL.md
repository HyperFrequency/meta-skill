---
name: autoencoder-anomaly-detection
version: 0.1.1
description: Autoencoder-based unsupervised anomaly detection on returns and order-flow features. Wraps PyOD's deep detectors (AutoEncoder, VAE, MO_GAAL) for one-line use, plus a hand-rolled PyTorch autoencoder for when you need control over architecture, loss, or streaming inference. Use to flag regime shifts, flash events, broken/stale ticks, or as a cheap pre-filter gate before an expensive model. Do NOT use when you already have labels (supervised classifiers win) or when data is low-dimensional and roughly elliptical (EllipticEnvelope / IsolationForest are simpler and as good).
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
license: BSD-2-Clause (PyOD upstream)
metadata:
    skill-author: HyperFrequency
    skill-domain: deep-learning / quant
---

# Autoencoder Anomaly Detection

## When to use

Use this skill when you want an unsupervised detector for "weird" rows in a feature matrix derived from market data:

- Spot regime shifts or flash events in returns / spread / depth-imbalance features.
- Flag broken or stale ticks in order-flow logs.
- Pre-filter rows before running an expensive model (cheap gate).
- Build a feature for a strategy: anomaly score over a rolling window.

Two main paths:

1. **PyOD** — one-line API. `clf = AutoEncoder(...)` / `fit` / `decision_function`. Use this 80% of the time. PyOD also exposes `VAE` and `MO_GAAL` (a GAN-based detector) under the same interface.
2. **Hand-rolled PyTorch AE** — when you need a non-MLP architecture (1-D conv AE, recurrent AE for variable-length order-flow), custom losses (Huber, quantile), or online incremental updates that PyOD doesn't ship. See `references/pytorch-handrolled.md`.

**Skip this skill** if you already have labels — supervised classifiers crush AEs when labels exist. Skip it if the data is low-dimensional and roughly elliptical — `EllipticEnvelope` / `IsolationForest` are simpler and often as good. For broader OD algorithm coverage outside autoencoders, reach for the parent `outlier-detection` workflow / PyOD's classical models directly.

## Install / setup

```bash
uv pip install pyod torch numpy pandas scikit-learn
```

PyOD's deep detectors auto-detect GPU via `torch.cuda.is_available()`. To force CPU pass `device="cpu"`; to pin a GPU pass `device="cuda:0"`. PyOD versions ≥ 2.0 use a PyTorch backend (older v1.x used Keras/TF with different kwargs — `hidden_neurons`, `epochs`). Check with `import pyod; pyod.__version__`.

## Minimal example — PyOD AutoEncoder on returns

Train an AE on "normal" rolling-feature rows, then score the test set; rows with high reconstruction error are flagged.

```python
import numpy as np, pandas as pd
from pyod.models.auto_encoder import AutoEncoder

df = pd.read_csv("ohlcv.csv")
close = df["close"].values.astype("float64")
ret = np.diff(np.log(close))

# build a small rolling-feature matrix: (ret_t, ret_{t-1}, ret_{t-2}, |ret_t|, rolling std)
def features(r, lags=3, win=20):
    X = []
    for i in range(max(lags, win), len(r)):
        row = list(r[i - lags : i + 1])
        row.append(abs(r[i]))
        row.append(r[i - win : i].std())
        X.append(row)
    return np.array(X, dtype="float32")

X = features(ret)
split = int(0.7 * len(X))
X_train, X_test = X[:split], X[split:]

# kwargs below are verified against PyOD v2.0+ (see references/api.md)
clf = AutoEncoder(
    hidden_neuron_list=[16, 8, 8, 16],   # symmetric encoder/decoder
    epoch_num=50,
    batch_size=64,
    dropout_rate=0.2,
    contamination=0.05,                  # expected outlier fraction
    preprocessing=True,                  # internal StandardScaler
    verbose=1,
    random_state=42,
)
clf.fit(X_train)

# 0/1 labels and continuous reconstruction-error scores
y_test_pred = clf.predict(X_test)            # 1 = anomaly
y_test_scores = clf.decision_function(X_test)
print("flagged rows:", y_test_pred.sum(), "of", len(y_test_pred))

# inspect the top-5 most anomalous test rows
top = np.argsort(-y_test_scores)[:5]
print(pd.DataFrame({"idx": top, "score": y_test_scores[top]}))
```

Drop-in swap for the GAN-based detector (all kwargs verified against v2.0+ source):

```python
from pyod.models.mo_gaal import MO_GAAL
clf = MO_GAAL(k=3, stop_epochs=20, lr_d=1e-4, lr_g=1e-4, contamination=0.05)
clf.fit(X_train)
```

And for VAE (verified against v2.0+ source):

```python
from pyod.models.vae import VAE
clf = VAE(encoder_neuron_list=[16, 8], decoder_neuron_list=[8, 16], latent_dim=4, epoch_num=50)
clf.fit(X_train)
```

## Where to go next

This file is a router. Detailed material lives in `references/`:

- **`references/api.md`** — full verified `__init__` signatures (every kwarg + default) for `AutoEncoder`, `VAE`, `MO_GAAL`, plus the shared `.fit` / `.predict` / `.decision_function` / `.threshold_` method surface and PyOD eval utilities.
- **`references/pytorch-handrolled.md`** — the hand-rolled PyTorch AE (conv/recurrent/custom-loss path), building-block table, and architecture choices (latent dim, symmetry, activations, loss, regularisation, denoising trick).
- **`references/operations.md`** — common pitfalls (contaminated training data, oversized latent, scale mismatch, threshold drift, non-stationarity, synthetic-anomaly traps), scaling to production (streaming, rolling retrain, calibration, two-stage filters, persistence), and a diagnostics checklist for "AE flags everything / nothing".
- **`references/bibliography.md`** — primary library links, deep-dive doc pages, adjacent libraries (anomalib, Alibi Detect, DeepOD, SUOD), academic papers, tutorials, and standard benchmark datasets.

## Sibling skills

- `isolation-forest` / classical PyOD detectors — simpler baselines; always benchmark the AE against `IsolationForest`.
- `regime-detection` (HMM / change-point) — pair with this when non-stationarity causes constant false positives.
- `feature-engineering` — the rolling-feature matrix here is deliberately minimal; richer features change which path wins.
