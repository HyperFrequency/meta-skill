---
name: cnn-pattern-recognition
description: CNN-based pattern recognition on financial price data. Cover both 2-D image CNNs over rendered price charts (torchvision / Keras Conv2D) and 1-D temporal CNNs over OHLCV tensors (Conv1D / nn.Conv1d), with notes on chart construction, look-ahead leakage, and small-model defaults for direction classification or regime tagging.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
license: Apache-2.0
metadata:
    skill-author: HyperFrequency
    skill-domain: deep-learning / quant
---

# CNN Pattern Recognition

## When to use

Use this skill when you want to learn visual/temporal patterns on price + volume directly with a convolutional model:

- Predict next-bar direction (up/down/flat) from a window of past bars.
- Classify chart regions as a named pattern (e.g. flag, double-top, breakout) where you already have labels.
- Score one-shot chart screenshots from a screener.
- Build a small CNN as a feature extractor whose embedding feeds a downstream model.

Two flavors:

1. **Image CNN (2-D)** — render an OHLCV window to a fixed-size chart image, then train a Conv2D net (torchvision or `keras.layers.Conv2D`). Best when the visual gestalt of the chart matters (candlestick shapes, overlap of MAs, volume bars under price).
2. **1-D temporal CNN (Conv1D)** — feed a `(window, channels)` tensor directly (`channels = [open, high, low, close, volume, indicator_1, ...]`). Best when the inputs are clean numerical series and you don't need image-level rendering. This is what most quant papers actually do.

If you need long-range dependencies and attention, prefer a `transformers` or `mamba` skill. If you need recurrence, prefer LSTM/GRU. CNNs are right when the pattern is *local in time*.

## Install / setup

PyTorch + torchvision (image and 1-D both):

```bash
uv pip install torch torchvision torchaudio
uv pip install pandas numpy matplotlib
```

Keras 3 (multi-backend):

```bash
uv pip install keras tensorflow  # or jax / torch backend
```

GPU notes:

- For CUDA 12.x on Linux/Windows, prefer the pre-built wheels: `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121`.
- On Apple Silicon, use the default `torch` wheel; pass `device="mps"` to move tensors. `torch.backends.mps.is_available()` should return `True`.
- For Keras + TF, install `tensorflow[and-cuda]` to pull a matching CUDA/cuDNN; for Keras + Torch backend, set `KERAS_BACKEND=torch`.

Verify install:

```python
import torch, torchvision
print(torch.__version__, torchvision.__version__, torch.cuda.is_available())
```

## Minimal example — 1-D Conv over OHLCV (PyTorch, ≤60 lines)

End-to-end: load OHLCV → sliding window → tiny Conv1D net → predict next-bar up/down. Replace `pd.read_csv("ohlcv.csv")` with whatever loader you have (`ccxt`, `nautilus`, etc.).

```python
import numpy as np, pandas as pd, torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

WINDOW = 64
df = pd.read_csv("ohlcv.csv")  # columns: open, high, low, close, volume
X_raw = df[["open", "high", "low", "close", "volume"]].values.astype("float32")
ret = np.diff(np.log(X_raw[:, 3]))  # close-to-close log returns
y_full = (ret > 0).astype("int64")  # 1 = up, 0 = down/flat

# z-score per-channel using ONLY past data (no future leakage)
mu = X_raw.cumsum(0) / np.arange(1, len(X_raw) + 1)[:, None]
sd = np.sqrt(((X_raw - mu) ** 2).cumsum(0) / np.arange(1, len(X_raw) + 1)[:, None] + 1e-6)
Xz = (X_raw - mu) / sd

# build windows: x[t-WINDOW : t]  ->  y[t]   (predict the NEXT bar)
X = np.stack([Xz[i - WINDOW:i] for i in range(WINDOW, len(Xz) - 1)])
y = y_full[WINDOW:]                              # aligned with the NEXT close
X = torch.tensor(X).permute(0, 2, 1)             # (N, channels=5, time=WINDOW)
y = torch.tensor(y)
split = int(0.8 * len(X))
train_ds = TensorDataset(X[:split], y[:split])
test_ds  = TensorDataset(X[split:], y[split:])

class TinyConv1D(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(5, 32, kernel_size=5, padding=2), nn.BatchNorm1d(32), nn.ReLU(),
            nn.Conv1d(32, 64, kernel_size=5, padding=2), nn.BatchNorm1d(64), nn.ReLU(),
            nn.AdaptiveAvgPool1d(1), nn.Flatten(), nn.Linear(64, 2),
        )
    def forward(self, x): return self.net(x)

device = "cuda" if torch.cuda.is_available() else "cpu"
model = TinyConv1D().to(device)
opt = torch.optim.Adam(model.parameters(), lr=1e-3)
loss_fn = nn.CrossEntropyLoss()
loader = DataLoader(train_ds, batch_size=128, shuffle=True)

for epoch in range(5):
    for xb, yb in loader:
        xb, yb = xb.to(device), yb.to(device)
        opt.zero_grad()
        loss = loss_fn(model(xb), yb)
        loss.backward(); opt.step()
    print(f"epoch {epoch} train_loss {loss.item():.4f}")

with torch.no_grad():
    Xt, yt = test_ds.tensors
    pred = model(Xt.to(device)).argmax(-1).cpu()
    print("test acc", (pred == yt).float().mean().item())
```

Sliding-window construction and the cumulative-mean normalisation are the leakage-prone parts — double-check them on a tiny slice before scaling up. (1-D Conv1D pipeline pattern follows the Keras EEG / FCN time-series examples; see References.)

## Minimal example — Image CNN over rendered charts (sketch)

```python
import matplotlib.pyplot as plt
from torchvision import transforms
from torch.utils.data import Dataset

class ChartDataset(Dataset):
    def __init__(self, df, window=64, img_size=64):
        self.df, self.window, self.tf = df, window, transforms.Compose([
            transforms.Grayscale(), transforms.Resize((img_size, img_size)), transforms.ToTensor(),
        ])
    def __len__(self): return len(self.df) - self.window - 1
    def __getitem__(self, i):
        win = self.df["close"].iloc[i : i + self.window].values
        fig, ax = plt.subplots(figsize=(1, 1), dpi=64)
        ax.plot(win); ax.axis("off"); fig.tight_layout(pad=0)
        fig.canvas.draw()
        img = plt.imread(fig.canvas.buffer_rgba(), format="raw")  # unverified — see https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.html
        plt.close(fig)
        nxt = int(self.df["close"].iloc[i + self.window + 1] > self.df["close"].iloc[i + self.window])
        return self.tf(img), nxt
```

Then drop the dataset into any torchvision classifier — e.g. `torchvision.models.resnet18(num_classes=2, weights=None)` and train with `CrossEntropyLoss`. In production, pre-render charts once and cache as `.npy` or `.pt`; rendering inside `__getitem__` is too slow for real training.

## Key API surface

### PyTorch / torchvision (1-D and 2-D)

| Symbol | What it does |
|---|---|
| `torch.nn.Conv1d(in_channels, out_channels, kernel_size, padding, dilation)` | Core 1-D conv over (B, C, T). |
| `torch.nn.Conv2d(in_channels, out_channels, kernel_size, padding)` | 2-D conv over (B, C, H, W). |
| `torch.nn.BatchNorm1d / BatchNorm2d` | Stabilises training; standard between conv + activation. |
| `torch.nn.AdaptiveAvgPool1d / AdaptiveAvgPool2d` | Pool to a fixed size before the classifier head — robust to window-length changes. |
| `torchvision.models.resnet18(weights=None, num_classes=K)` | Drop-in 2-D CNN for chart-image classification. |
| `torchvision.transforms.Compose([...])` | Standard chart-image preprocessing pipeline. |
| `torch.optim.Adam`, `torch.optim.AdamW` | Default optimisers; `AdamW` if you care about weight decay. |

### Keras 3

| Symbol | What it does |
|---|---|
| `keras.layers.Conv1D(filters, kernel_size, padding, activation)` | 1-D conv over `(B, T, C)` (channels-last). |
| `keras.layers.Conv2D(filters, kernel_size, padding, activation)` | 2-D conv over `(B, H, W, C)`. |
| `keras.layers.BatchNormalization()` | Stabilises Conv stacks; see EEG / FCN reference examples. |
| `keras.layers.GlobalAveragePooling1D / 2D` | Replace `Flatten + Dense` for fewer params and better generalisation. |
| `keras.Model(inputs, outputs).compile(...).fit(...)` | Standard functional-API training loop. |

## Architecture choices

- **Depth**: start at 2–4 conv blocks. CNNs over price overfit fast; deeper is rarely better unless you have millions of bars.
- **Channel widths**: `32 -> 64 -> 128` is a safe ladder. Doubling each block keeps receptive-field growth and parameter count balanced.
- **Kernel size**: 1-D over price favours `kernel=3 or 5`. Larger kernels (7, 9) help capture multi-bar patterns; pair with `padding="same"` so the time axis is preserved.
- **Activations**: ReLU by default. `GELU` or `SiLU` sometimes nudges a few bps on noisy financial data — not worth fighting over.
- **Pooling**: prefer `AdaptiveAvgPool` over `MaxPool` for regression-style heads; price noise makes max-pool jumpy.
- **Normalisation**: BatchNorm is fine for big batches; switch to `LayerNorm` or `GroupNorm` if you batch in time-walking blocks where the batch distribution shifts.
- **Head**: 1 hidden FC then logits. Avoid deep MLP heads — the conv stack already did the work.

## Common pitfalls

1. **Look-ahead in chart construction.** Rendering an image of bars `t-WINDOW : t` is fine *only* if your label is for `t+1` and you do **not** include bar `t` in both. Off-by-one here will silently make your model look brilliant. Verify on a held-out chunk by shifting labels by ±1 and confirming acc drops.
2. **Future-statistic normalisation.** Z-scoring with global mean/std uses the *whole* series — including the test set. Always use rolling / expanding statistics, like the cumulative mean+std in the minimal example.
3. **Class imbalance + tiny edges.** If most bars are flat, a CNN learns to predict the majority class. Either rebalance with `class_weight` (`compile(..., class_weight={0: 1, 1: 1.4})` in Keras) or threshold returns to make labels balanced (e.g. up = top tertile, down = bottom tertile).
4. **Resolution-vs-bars tradeoff (image CNN).** A 64×64 image of 256 bars hides candle shapes; a 256×256 image of 64 bars is mostly whitespace. Pick a ratio that keeps individual candles 4–10 px wide.
5. **Cross-validation that ignores time.** Standard k-fold is **wrong** here. Use a walk-forward / purged split (see `adaptive-wfo-epoch` skill).
6. **Cached charts going stale.** If you pre-render images and later change the windowing, you must invalidate the cache — date-stamp the cache directory.

## Scaling to production

- **Batch the windowing.** The `np.stack([Xz[i-WINDOW:i] ...])` in the minimal example is O(n*WINDOW) memory. For >1M bars switch to a strided view (`np.lib.stride_tricks.sliding_window_view`) or a streaming `IterableDataset`.
- **Mixed precision.** `torch.autocast("cuda")` + `GradScaler` cuts memory ~40% on the 2-D image branch with no accuracy loss. The 1-D branch is usually too small to benefit.
- **Compile.** `model = torch.compile(model)` (PyTorch 2.x) gives a 1.2-2x speedup on these tiny conv stacks. Keras users get the same from `jit_compile=True` in `model.compile`.
- **Walk-forward retrain.** Don't train once and forget. Schedule a retrain every N bars / N days (see `adaptive-wfo-epoch` skill). The CNN's weights go stale faster than people expect.
- **Inference latency.** For real-time signal generation, a 1-D CNN on a 64-bar window runs in <100 us on CPU; the image-rendering branch is the bottleneck — pre-render or skip.

## Diagnostics

When the model trains but performs at chance, the order of investigation:

1. Verify labels: shuffle `y` and confirm acc collapses to ~0.5. If it doesn't, you have leakage.
2. Visualise inputs: plot the first 4 windows. If they all look identical, your normalisation is broken.
3. Check activations: `torchinfo.summary(model, input_size=(1, 5, WINDOW))` to confirm shapes flow correctly.
4. Sanity-check with an MLP baseline. If a flat MLP beats your CNN, the CNN is mis-specified (kernel too big, BN exploding).
5. Loss curve shape: oscillating train loss → LR too high. Flat → LR too low or dead ReLUs.

## References

### Primary library
- [PyTorch on GitHub](https://github.com/pytorch/pytorch) — upstream repo, issues, releases (v2.5+)
- [torchvision on GitHub](https://github.com/pytorch/vision) — Conv2D models and pretrained weights
- [Keras on GitHub](https://github.com/keras-team/keras) — multi-backend (TF / JAX / Torch); for the Conv1D pipeline
- [PyTorch documentation (stable)](https://pytorch.org/docs/stable/) — pinned to v2.5
- [Keras 3 documentation](https://keras.io/) — current 3.x API surface
- [Keras examples directory (time series)](https://keras.io/examples/timeseries/) — Conv1D FCN, EEG, anomaly detection patterns

### Deep-dive docs (specific pages worth bookmarking)
- [`torch.nn.Conv1d`](https://pytorch.org/docs/stable/generated/torch.nn.Conv1d.html) — input shape `(B, C, T)`, dilation, groups; the bar/window orientation gotcha
- [`torch.nn.Conv2d`](https://pytorch.org/docs/stable/generated/torch.nn.Conv2d.html) — for rendered chart pipelines
- [`torch.nn.BatchNorm1d / BatchNorm2d`](https://pytorch.org/docs/stable/generated/torch.nn.BatchNorm1d.html) — running mean/var semantics during eval; the silent bug source in walk-forward pipelines
- [`torch.nn.AdaptiveAvgPool1d`](https://pytorch.org/docs/stable/generated/torch.nn.AdaptiveAvgPool1d.html) — fixed-size head independent of input window length
- [torchvision models reference](https://pytorch.org/vision/stable/models.html) — `resnet18` / `efficientnet` / `mobilenet`; choose by FLOPs vs accuracy budget
- [`keras.layers.Conv1D`](https://keras.io/api/layers/convolution_layers/convolution1d/) — channels-last `(B, T, C)` orientation contrasted with PyTorch
- [Keras time-series classification from scratch](https://keras.io/examples/timeseries/timeseries_classification_from_scratch/) — canonical 1-D FCN walkthrough; the architecture template the snippet above follows
- [Keras EEG signal classification](https://keras.io/examples/timeseries/eeg_signal_classification/) — deeper Conv1D stack, good reference for longer windows
- [PyTorch tutorial: training a classifier](https://pytorch.org/tutorials/beginner/blitz/cifar10_tutorial.html) — the 2-D loop the chart-CNN section adapts

### Adjacent / alternative libraries
- [KerasCV](https://github.com/keras-team/keras-cv) — modular pretrained vision models (EfficientNet, YOLOX, RetinaNet) when chart classification crosses into detection
- [timm (PyTorch Image Models)](https://github.com/huggingface/pytorch-image-models) — Ross Wightman's image-model zoo; broader than torchvision, faster to swap backbones
- [tsai](https://github.com/timeseriesAI/tsai) — fastai-style time-series CNNs (InceptionTime, ResCNN, TST); good 1-D baselines beyond plain Conv1D
- [aeon](https://github.com/aeon-toolkit/aeon) — scikit-learn-compatible time-series classifier zoo, includes deep models
- [sktime](https://github.com/sktime/sktime) — broader time-series toolkit; CNN baselines and the canonical UCR/UEA benchmark wrappers

### Academic papers
- LeCun, Y., Bottou, L., Bengio, Y., & Haffner, P. (1998). "Gradient-Based Learning Applied to Document Recognition." *Proceedings of the IEEE* 86(11), 2278-2324. [DOI: 10.1109/5.726791](https://doi.org/10.1109/5.726791) — the LeNet paper; the 2-D CNN ancestor.
- Wang, Z., Yan, W., & Oates, T. (2017). "Time Series Classification from Scratch with Deep Neural Networks: A Strong Baseline." *IJCNN 2017*. [arXiv:1611.06455](https://arxiv.org/abs/1611.06455) — FCN / ResNet baselines for 1-D time-series classification; the architecture the Keras example uses.
- Sezer, O. B., & Ozbayoglu, A. M. (2018). "Algorithmic Financial Trading with Deep Convolutional Neural Networks: Time Series to Image Conversion Approach." *Applied Soft Computing* 70, 525-538. [DOI: 10.1016/j.asoc.2018.04.024](https://doi.org/10.1016/j.asoc.2018.04.024) — the chart-image approach for financial CNN classification.
- Bai, S., Kolter, J. Z., & Koltun, V. (2018). "An Empirical Evaluation of Generic Convolutional and Recurrent Networks for Sequence Modeling." [arXiv:1803.01271](https://arxiv.org/abs/1803.01271) — TCN paper; argues 1-D CNN beats LSTM on many sequence tasks; relevant to whether to choose CNN over LSTM in this skill.
- Ismail Fawaz, H., Forestier, G., Weber, J., Idoumghar, L., & Muller, P.-A. (2019). "Deep Learning for Time Series Classification: A Review." *Data Mining and Knowledge Discovery* 33(4), 917-963. [DOI: 10.1007/s10618-019-00619-1](https://doi.org/10.1007/s10618-019-00619-1) — definitive survey; benchmarks every 1-D CNN family on UCR archive.

### Tutorials & write-ups
- [PyTorch time-series Conv1D tutorial](https://pytorch.org/tutorials/intermediate/seq2seq_translation_tutorial.html) — adapted Conv1D-based sequence models
- [Keras "Timeseries classification with a Transformer model"](https://keras.io/examples/timeseries/timeseries_classification_transformer/) — direct contrast against the Conv1D pipeline
- [torchinfo on GitHub](https://github.com/TylerYep/torchinfo) — `summary(model, input_size=(B, C, T))`; the right tool for verifying tensor shapes flow correctly through a Conv1D stack

### Standard datasets / benchmarks
- UCR / UEA time-series classification archive — [www.timeseriesclassification.com](http://www.timeseriesclassification.com/) — the canonical TSC benchmark; 128 univariate + 30 multivariate datasets
- Sezer-Ozbayoglu chart-image benchmark (Dow 30, 2007-2017) — used in the original "image conversion approach" paper
- LOBSTER limit order book data — used in `microstructure-analysis` but the standard 1-D CNN evaluation setup for short-horizon prediction

### Last cross-checked
2026-05-20 — via Context7 `/pytorch/pytorch` + `/keras-team/keras-io` + WebSearch verification of all paper DOIs/arXiv IDs.
