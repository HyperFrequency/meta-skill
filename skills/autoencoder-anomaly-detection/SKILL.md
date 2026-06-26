---
name: autoencoder-anomaly-detection
description: Autoencoder-based anomaly detection on returns and order-flow features. Wraps PyOD's deep detectors (AutoEncoder, VAE, MO-GAAL) for one-line use and shows a hand-rolled PyTorch autoencoder for when you need control over architecture, loss, or streaming inference.
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
2. **Hand-rolled PyTorch AE** — when you need a non-MLP architecture (1-D conv AE, recurrent AE for variable-length order-flow), custom losses (Huber, quantile), or online incremental updates that PyOD doesn't ship.

Skip this skill if you already have labels — supervised classifiers crush AEs when labels exist. Skip it if the data is low-dimensional and roughly elliptical — `EllipticEnvelope` / `IsolationForest` are simpler and often as good.

## Install / setup

```bash
uv pip install pyod torch
uv pip install numpy pandas scikit-learn
```

PyOD's deep detectors auto-detect GPU via `torch.cuda.is_available()`. To force CPU pass `device="cpu"`; to pin a GPU pass `device="cuda:0"`. PyOD versions ≥ 2.0 use a PyTorch backend (older versions used Keras/TF). Check with `import pyod; pyod.__version__`.

For Keras-based autoencoders (older docs you might find online), install `tensorflow` and use `keras.Model` directly — the API surface in the hand-rolled section below ports cleanly.

## Minimal example — PyOD AutoEncoder on returns (≤60 lines)

Train an AE on "normal" rolling-feature rows, then score the test set; rows with high reconstruction error are flagged. Adapted from the canonical PyOD AutoEncoder example.

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

# unverified — older PyOD used `hidden_neurons`; newer (≥2.0) uses `hidden_neuron_list`.
# See https://github.com/yzhao062/pyod/blob/master/pyod/models/auto_encoder.py for the exact signature your version exposes.
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

Drop-in swap for the GAN-based detector:

```python
from pyod.models.mo_gaal import MO_GAAL
clf = MO_GAAL(k=3, stop_epochs=20, lr_d=1e-4, lr_g=1e-4, contamination=0.05)  # unverified — see https://github.com/yzhao062/pyod/blob/master/pyod/models/mo_gaal.py
clf.fit(X_train)
```

And for VAE:

```python
from pyod.models.vae import VAE
clf = VAE(encoder_neuron_list=[16, 8], decoder_neuron_list=[8, 16], latent_dim=4, epoch_num=50)  # unverified — see https://github.com/yzhao062/pyod/blob/master/pyod/models/vae.py
clf.fit(X_train)
```

## Minimal example — hand-rolled PyTorch AE

When PyOD's MLP-style AE isn't flexible enough:

```python
import torch, torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

class AE(nn.Module):
    def __init__(self, d_in, latent=4):
        super().__init__()
        self.enc = nn.Sequential(nn.Linear(d_in, 16), nn.ReLU(), nn.Linear(16, latent))
        self.dec = nn.Sequential(nn.Linear(latent, 16), nn.ReLU(), nn.Linear(16, d_in))
    def forward(self, x):
        z = self.enc(x); return self.dec(z)

device = "cuda" if torch.cuda.is_available() else "cpu"
X = torch.tensor(X_train)                                 # from earlier features()
ds = TensorDataset(X)
loader = DataLoader(ds, batch_size=64, shuffle=True)

model = AE(d_in=X.shape[1], latent=4).to(device)
opt = torch.optim.Adam(model.parameters(), lr=1e-3)
loss_fn = nn.MSELoss()

for epoch in range(50):
    for (xb,) in loader:
        xb = xb.to(device)
        opt.zero_grad(); loss = loss_fn(model(xb), xb); loss.backward(); opt.step()

with torch.no_grad():
    test = torch.tensor(X_test).to(device)
    scores = ((model(test) - test) ** 2).mean(dim=1).cpu().numpy()  # per-row recon error

threshold = np.quantile(scores, 0.95)        # top 5%
anoms = scores > threshold
```

## Key API surface

### PyOD detectors

| Symbol | What it does |
|---|---|
| `pyod.models.auto_encoder.AutoEncoder(...)` | MLP autoencoder, reconstruction-error scoring. Core kwargs: `hidden_neuron_list`, `epoch_num`, `batch_size`, `dropout_rate`, `contamination`. |
| `pyod.models.vae.VAE(...)` | Variational AE; uses KL + recon loss. Kwargs typically `encoder_neuron_list`, `decoder_neuron_list`, `latent_dim`. |
| `pyod.models.mo_gaal.MO_GAAL(...)` | GAN-based detector with `k` sub-generators to avoid mode collapse. |
| `.fit(X)` | Train on "normal" data (or mixed with low contamination). |
| `.predict(X)` | Binary labels: 1 = anomaly, 0 = inlier. |
| `.decision_function(X)` | Raw anomaly score (higher = more anomalous). |
| `.threshold_` | Auto-computed cutoff from `contamination`. |
| `pyod.utils.data.generate_data(...)` | Synthetic data helper for sanity checks. |

### Hand-rolled PyTorch

| Symbol | What it does |
|---|---|
| `nn.Linear / nn.Conv1d` | Encoder/decoder building blocks. |
| `nn.MSELoss / nn.SmoothL1Loss` | Reconstruction loss. Smooth L1 (Huber) is more robust to fat tails. |
| `torch.optim.Adam(lr=1e-3)` | Default optimiser. |
| `torch.no_grad()` + per-row MSE | Compute scores at inference. |

## Architecture choices

- **Latent dim**: set so that `latent_dim ≈ effective rank of features / 2`. Too small → underfits and flags *everything*; too large → AE memorises and flags *nothing*. Sweep `latent ∈ {2, 4, 8, 16}` and pick by held-out recon error on clean data.
- **Symmetry**: encoder and decoder mirror layer widths. Asymmetric ("undercomplete" decoder) can help when the true generator is simpler than the observed signal, but start symmetric.
- **Activations**: ReLU in hidden layers, **no activation on the final decoder layer** if features can be negative (returns!). Sigmoid/Tanh outputs squash returns and pollute scores.
- **Loss**: MSE for Gaussian-ish features, Huber/SmoothL1 for fat-tailed financial returns. For binary order-flow events (cancel/trade flags), use BCE.
- **Regularisation**: `dropout_rate=0.2` and L2 weight decay (`weight_decay=1e-5` in Adam) prevent the AE from memorising the train set.
- **Denoising trick**: add Gaussian noise to inputs (`x + 0.05 * randn_like(x)`) but reconstruct the *clean* `x`. Forces the AE to learn the manifold, not the noise — usually +5-10% on AUROC on financial data.

## Common pitfalls

1. **Training on contaminated data.** AEs are unsupervised but assume the train set is *mostly* normal. If 30% of your "training" rows are anomalies, the AE learns to reconstruct them too. Either (a) pre-filter with a cheap detector first, or (b) set `contamination` honestly so PyOD's loss / threshold handle it.
2. **Latent dim too large.** A latent of 16 on a 20-dim feature matrix is basically an identity function. Reconstruction error becomes constant → no signal. Rule of thumb: `latent ≤ d_in / 4`.
3. **Scale mismatch.** Mixing raw price ($100) with log-return (1e-3) in the same feature row — the AE will only "see" the big-magnitude features. Always standardise; PyOD's `preprocessing=True` does this internally, hand-rolled code does not.
4. **Threshold drift.** A fixed threshold from training data goes stale as volatility changes. Recompute the threshold on a rolling window of recent scores (e.g. `np.quantile(recent_scores, 0.95)`).
5. **Non-stationarity = constant false positives.** A regime change isn't an anomaly per row — but per row, every row in the new regime looks anomalous. Use a rolling retrain or an explicit regime model (HMM, change-point detector) on top.
6. **Evaluating on synthetic anomalies you injected.** AE trivially detects "add a huge spike to one row". Evaluate on real labeled events (flash crashes, halts) or by precision-at-k.

## Scaling to production

- **Streaming scoring.** Once a PyOD AE is fit, calling `decision_function` per new row is fine for low-frequency signals (every minute). For high-frequency, pre-load the underlying `clf.model_` and call it directly with a torch tensor — avoids PyOD's scaler refit overhead.
- **Rolling retrain cadence.** Anomaly definitions drift. Retrain on the last 30-60 days of "normal" data daily or weekly. Keep a small held-out clean window as a regression check.
- **Score calibration.** Raw recon errors are not comparable across retrains because the AE re-initialises. Always re-derive the threshold from the new train set's score distribution; do not carry a hard-coded threshold across retrains.
- **Two-stage filters.** Use the AE as a *recall-heavy* first stage (low threshold, many flags), then run a slower expensive model (LLM, human, hand-crafted rule) on the flags. AEs are great gates, mediocre final classifiers.
- **Persistence.** PyOD models pickle cleanly: `joblib.dump(clf, "ae.pkl")`. For the underlying torch model, save `state_dict` separately if you want to deploy without the PyOD wrapper.

## Diagnostics

When the AE flags everything (or nothing), the order of investigation:

1. Plot per-row recon error on the train set: it should be a tight distribution with a thin right tail. If it's bimodal, the train set is contaminated.
2. Confirm preprocessing actually ran (`preprocessing=True`): print `clf.scaler_.mean_` and check it isn't all zeros.
3. Reduce `latent_dim` aggressively (set to 2). If AE still reconstructs perfectly, your features carry no information; if it now flags everything sensibly, latent was too large.
4. Compare against `IsolationForest` as a baseline. If IF beats the AE by a wide margin, the AE is mis-specified — usually wrong loss or wrong scale.

## References

### Primary library
- [PyOD on GitHub](https://github.com/yzhao062/pyod) — upstream repo, issues, releases (v2.0+)
- [PyOD documentation](https://pyod.readthedocs.io/en/latest/) — pinned to v2.x for the snippets above
- [PyOD examples directory](https://github.com/yzhao062/pyod/tree/master/examples) — `auto_encoder_example.py`, `vae_example.py`, `mo_gaal_example.py` — drop-in templates
- [PyTorch on GitHub](https://github.com/pytorch/pytorch) — for the hand-rolled section

### Deep-dive docs (specific pages worth bookmarking)
- [`AutoEncoder` model docs](https://pyod.readthedocs.io/en/latest/pyod.models.html#module-pyod.models.auto_encoder) — `hidden_neuron_list`, `epoch_num`, `dropout_rate`, `contamination`; the kwargs that drive results
- [`VAE` model docs](https://pyod.readthedocs.io/en/latest/pyod.models.html#module-pyod.models.vae) — `encoder_neuron_list`, `decoder_neuron_list`, `latent_dim`; KL + reconstruction loss
- [`MO_GAAL` model docs](https://pyod.readthedocs.io/en/latest/pyod.models.html#module-pyod.models.mo_gaal) — `k` sub-generators against mode collapse; `lr_d` / `lr_g` separately tuned
- [`AutoEncoder` source](https://github.com/yzhao062/pyod/blob/master/pyod/models/auto_encoder.py) — read the source to see exact signature your installed version exposes (API drifted across v1 → v2)
- [PyOD utility module](https://pyod.readthedocs.io/en/latest/pyod.utils.html) — `generate_data`, `evaluate_print` helpers for sanity checks
- [PyOD benchmarking guide](https://pyod.readthedocs.io/en/latest/benchmark.html) — `pyod.utils.utility.precision_n_scores` and the standard ROC / AUPR / P@N evaluation

### Adjacent / alternative libraries
- [PyTorch Anomaly Detection (anomalib)](https://github.com/openvinotoolkit/anomalib) — production-grade industrial anomaly detection; PaDiM, PatchCore, EfficientAD; not finance-specific but the same recon-error paradigm
- [TensorFlow Anomaly Detection examples](https://www.tensorflow.org/tutorials/generative/autoencoder) — Keras-native autoencoder anomaly detection tutorial
- [Alibi Detect](https://github.com/SeldonIO/alibi-detect) — anomaly + drift detection with VAE / Mahalanobis / KS test
- [DeepOD](https://github.com/xuhongzuo/DeepOD) — deep learning OD; broader algorithm coverage than PyOD's deep models alone
- [Suod (PyOD parallel ensemble)](https://github.com/yzhao062/SUOD) — when you want to ensemble PyOD detectors at scale

### Academic papers
- Kingma, D. P., & Welling, M. (2014). "Auto-Encoding Variational Bayes." *ICLR 2014*. [arXiv:1312.6114](https://arxiv.org/abs/1312.6114) — the VAE paper; the loss function `VAE` model implements.
- Liu, Y., Li, Z., Zhou, C., Jiang, Y., Sun, J., Wang, M., & He, X. (2019). "Generative Adversarial Active Learning for Unsupervised Outlier Detection." *IEEE Transactions on Knowledge and Data Engineering* 32(8), 1517-1528. [DOI: 10.1109/TKDE.2019.2905606](https://doi.org/10.1109/TKDE.2019.2905606) — the MO-GAAL / SO-GAAL paper.
- Sakurada, M., & Yairi, T. (2014). "Anomaly Detection Using Autoencoders with Nonlinear Dimensionality Reduction." *Proc. MLSDA 2014*. [DOI: 10.1145/2689746.2689747](https://doi.org/10.1145/2689746.2689747) — early demonstration of AE-based anomaly detection on industrial sensor data.
- Zhao, Y., Nasrullah, Z., & Li, Z. (2019). "PyOD: A Python Toolbox for Scalable Outlier Detection." *Journal of Machine Learning Research* 20(96), 1-7. [JMLR](https://www.jmlr.org/papers/v20/19-011.html) — the PyOD library paper; benchmarks the AE detector across standard datasets.
- Aggarwal, C. C. (2017). *Outlier Analysis* (2nd ed.). Springer. [DOI: 10.1007/978-3-319-47578-3](https://doi.org/10.1007/978-3-319-47578-3) — Chapter 3 (deep autoencoder section) is the textbook reference PyOD cites.
- Bengio, Y., Yao, L., Alain, G., & Vincent, P. (2013). "Generalized Denoising Auto-Encoders as Generative Models." *NeurIPS 2013*. [arXiv:1305.6663](https://arxiv.org/abs/1305.6663) — denoising trick used in the "Architecture choices" section.

### Tutorials & write-ups
- [Keras autoencoder anomaly detection tutorial](https://keras.io/examples/timeseries/timeseries_anomaly_detection/) — hand-rolled reference for time series; the snntorch-equivalent of this skill
- [PyOD AutoEncoder example notebook](https://github.com/yzhao062/pyod/blob/master/notebooks/Compare%20All%20Models.ipynb) — comparison against IsolationForest / LOF / OCSVM baselines
- [Anomaly Detection Resources (Zhao curated list)](https://github.com/yzhao062/anomaly-detection-resources) — the broader bibliography that PyOD draws from

### Standard datasets / benchmarks
- ODDS benchmark — [odds.cs.stonybrook.edu](http://odds.cs.stonybrook.edu/) — Stony Brook outlier detection benchmark; the most-cited multivariate evaluation set
- KDD'99 / NSL-KDD — network intrusion detection; standard "deep AE works" benchmark
- Yahoo S5 time-series anomaly benchmark — [research.yahoo.com](https://yahooresearch.tumblr.com/post/114590420346/a-benchmark-dataset-for-time-series-anomaly) — labeled real and synthetic anomalies; closest to financial time-series setup

### Last cross-checked
2026-05-20 — via Context7 `/yzhao062/pyod` (1252 snippets, High, benchmark 90.6) + WebSearch verification of all paper DOIs/arXiv IDs.
