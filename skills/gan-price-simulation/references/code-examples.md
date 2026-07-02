# Code Examples — vanilla 1-D GAN and TimeGAN

## Minimal example — vanilla 1-D GAN on returns (≤60 lines)

End-to-end: load returns → train tiny G+D → sample → compare statistics. Pattern follows the canonical `eriklindernoren/PyTorch-GAN/implementations/gan/gan.py`.

```python
import numpy as np, pandas as pd, torch
import torch.nn as nn

WINDOW, LATENT = 32, 16
df = pd.read_csv("ohlcv.csv")
ret = np.diff(np.log(df["close"].values))[-20000:].astype("float32")  # ~20k bars
ret = (ret - ret.mean()) / ret.std()                                  # normalise to ~N(0,1)
real_windows = np.stack([ret[i : i + WINDOW] for i in range(len(ret) - WINDOW)])
real = torch.tensor(real_windows)

class G(nn.Module):
    def __init__(self): super().__init__(); self.net = nn.Sequential(
        nn.Linear(LATENT, 64), nn.LeakyReLU(0.2),
        nn.Linear(64, 128), nn.LeakyReLU(0.2),
        nn.Linear(128, WINDOW), nn.Tanh())          # Tanh keeps outputs bounded
    def forward(self, z): return self.net(z)

class D(nn.Module):
    def __init__(self): super().__init__(); self.net = nn.Sequential(
        nn.Linear(WINDOW, 128), nn.LeakyReLU(0.2), nn.Dropout(0.3),
        nn.Linear(128, 64), nn.LeakyReLU(0.2), nn.Dropout(0.3),
        nn.Linear(64, 1), nn.Sigmoid())
    def forward(self, x): return self.net(x)

device = "cuda" if torch.cuda.is_available() else "cpu"
g, d = G().to(device), D().to(device)
opt_g = torch.optim.Adam(g.parameters(), lr=2e-4, betas=(0.5, 0.999))   # eriklindernoren defaults
opt_d = torch.optim.Adam(d.parameters(), lr=2e-4, betas=(0.5, 0.999))
bce = nn.BCELoss()
BATCH = 128

for step in range(3000):
    idx = np.random.choice(len(real), BATCH)
    real_b = real[idx].to(device)
    z = torch.randn(BATCH, LATENT, device=device)
    fake = g(z)

    # train D
    opt_d.zero_grad()
    loss_d = 0.5 * (bce(d(real_b), torch.ones(BATCH, 1, device=device)) +
                    bce(d(fake.detach()), torch.zeros(BATCH, 1, device=device)))
    loss_d.backward(); opt_d.step()

    # train G
    opt_g.zero_grad()
    loss_g = bce(d(fake), torch.ones(BATCH, 1, device=device))
    loss_g.backward(); opt_g.step()
    if step % 500 == 0:
        print(f"step {step}  d {loss_d.item():.3f}  g {loss_g.item():.3f}")

# sample and compare stats
with torch.no_grad():
    samples = g(torch.randn(4096, LATENT, device=device)).cpu().numpy().reshape(-1)
print("real mean/std", real_windows.mean(), real_windows.std())
print("fake mean/std", samples.mean(), samples.std())

# autocorrelation sanity check
from statsmodels.tsa.stattools import acf
print("real acf[1:5]", acf(ret, nlags=5)[1:5])
print("fake acf[1:5]", acf(samples, nlags=5)[1:5])   # expect close to zero like real returns
```

If `real_acf[1:5]` is close to zero on returns (the typical case), the vanilla GAN does fine. If real ACF is non-zero (e.g. on intraday returns with autocorrelation), you almost certainly want **TimeGAN**, which is structured to preserve that.

## Minimal example — TimeGAN (reference, ≤10 lines)

The TimeGAN reference repo provides an end-to-end runner. Pseudocode:

```python
# unverified — see https://github.com/jsyoon0823/TimeGAN for the canonical implementation
from timegan import timegan                          # from the original repo (TF1)
parameters = {"module": "gru", "hidden_dim": 24, "num_layer": 3,
              "iterations": 10000, "batch_size": 128}
synthetic_data = timegan(real_3d_array, parameters)  # real_3d_array: (num_windows, seq_len, features)
```

`ydata-synthetic` (PyTorch-friendly) exposes a similar TimeGAN wrapper; check its current API at https://github.com/ydataai/ydata-synthetic before pasting kwargs.

## Key API surface

### Vanilla GAN building blocks (PyTorch)

| Symbol | What it does |
|---|---|
| `nn.Linear / nn.LeakyReLU(0.2) / nn.Tanh` | Generator MLP stack. Tanh on output keeps the range bounded; rescale to match real std. |
| `nn.Sigmoid` | Discriminator output (binary real/fake). |
| `nn.BCELoss / nn.BCEWithLogitsLoss` | Adversarial loss. Prefer `BCEWithLogitsLoss` + linear output for numerical stability. |
| `torch.optim.Adam(lr=2e-4, betas=(0.5, 0.999))` | Standard GAN optimiser settings from DCGAN paper; copy them unless you have a reason. |
| `torch.randn(B, LATENT)` | Latent noise sampler. |

### TimeGAN (reference repo)

| Symbol | What it does |
|---|---|
| `embedder` / `recovery` | Encode real sequences to a latent space + decode back (autoencoder pair). |
| `generator` / `supervisor` | Generate latent sequences; supervisor adds a teacher-forced one-step loss. |
| `discriminator` | Real-vs-fake on latent sequences. |
| Three training phases | (1) embedder + recovery, (2) supervisor (one-step prediction), (3) joint adversarial. Skipping any phase tanks quality. |
