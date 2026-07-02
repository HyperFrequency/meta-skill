---
name: cnn-pattern-recognition
version: 0.1.0
description: CNN-based pattern recognition on financial price data. Cover both 2-D image CNNs over rendered price charts (torchvision / Keras Conv2D) and 1-D temporal CNNs over OHLCV tensors (Conv1D / nn.Conv1d), with notes on chart construction, look-ahead leakage, and small-model defaults for direction classification or regime tagging. Use when the pattern is local in time; NOT for long-range/attention models (use transformers/mamba) or recurrence (use LSTM/GRU).
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

Defaults that work for price CNNs: 2–4 conv blocks (they overfit fast), a `32 -> 64 -> 128` channel ladder, `kernel=3 or 5` for 1-D, ReLU, `AdaptiveAvgPool` over `MaxPool`, and a single FC head. Full tuning rationale (depth, kernels, activations, pooling, normalisation choices) is in [`references/architecture-and-ops.md`](references/architecture-and-ops.md).

## Common pitfalls

1. **Look-ahead in chart construction.** Rendering an image of bars `t-WINDOW : t` is fine *only* if your label is for `t+1` and you do **not** include bar `t` in both. Off-by-one here will silently make your model look brilliant. Verify on a held-out chunk by shifting labels by ±1 and confirming acc drops.
2. **Future-statistic normalisation.** Z-scoring with global mean/std uses the *whole* series — including the test set. Always use rolling / expanding statistics, like the cumulative mean+std in the minimal example.
3. **Class imbalance + tiny edges.** If most bars are flat, a CNN learns to predict the majority class. Either rebalance with `class_weight` (`compile(..., class_weight={0: 1, 1: 1.4})` in Keras) or threshold returns to make labels balanced (e.g. up = top tertile, down = bottom tertile).
4. **Resolution-vs-bars tradeoff (image CNN).** A 64×64 image of 256 bars hides candle shapes; a 256×256 image of 64 bars is mostly whitespace. Pick a ratio that keeps individual candles 4–10 px wide.
5. **Cross-validation that ignores time.** Standard k-fold is **wrong** here. Use a walk-forward / purged split (see `adaptive-wfo-epoch` skill).
6. **Cached charts going stale.** If you pre-render images and later change the windowing, you must invalidate the cache — date-stamp the cache directory.

## Scaling to production & diagnostics

For production scaling (strided windowing for >1M bars, mixed precision, `torch.compile`, walk-forward retrain cadence, inference latency) and the step-by-step "trains but performs at chance" diagnostic checklist, see [`references/architecture-and-ops.md`](references/architecture-and-ops.md). Walk-forward retrain and purged splits live in the `adaptive-wfo-epoch` skill.

## References

Full curated reference set — primary library docs (PyTorch / torchvision / Keras 3), adjacent libraries (timm, tsai, aeon, sktime), academic papers (LeNet, Wang 2017 FCN, Sezer-Ozbayoglu chart-image, Bai TCN, Ismail Fawaz survey), tutorials, and benchmark datasets (UCR/UEA, LOBSTER) — is in [`references/references.md`](references/references.md). Last cross-checked 2026-05-20.
