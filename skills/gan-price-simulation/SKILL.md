---
name: gan-price-simulation
description: GAN-based synthetic price and return simulation. Walks the vanilla 1-D GAN baseline (eriklindernoren/PyTorch-GAN style) for univariate return series and points to TimeGAN for sequential conditional generation. Covers training loop, sample-vs-real statistics check (mean, std, ACF), and the standard failure modes.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
license: MIT (PyTorch-GAN upstream)
metadata:
    skill-author: HyperFrequency
    skill-domain: deep-learning / quant
---

# GAN Price Simulation

## When to use

Use this skill when you want to *generate* synthetic return / price series that match real-data statistics — for augmentation, stress testing, or Monte-Carlo backtests with a learned generator:

- Augment a small dataset before training a downstream model.
- Stress-test a strategy by drawing from a learned distribution of returns instead of i.i.d. Gaussian.
- Build a "what-if" simulator for an asset where you have limited history.
- Generate paired regime / conditional samples (TimeGAN, with auxiliary regime label).

Do not use a GAN if:

- You just need i.i.d. samples from an empirical distribution — bootstrap is simpler and unbiased.
- You need calibrated uncertainty for a forecast — GANs do not give you density estimates (use normalizing flows or PyMC).
- You only have a few thousand bars. GANs are data-hungry; with <10k samples, mode collapse is near-guaranteed.

Two paths:

1. **Vanilla 1-D GAN** — small MLP generator + discriminator on flattened return windows. Reference: `eriklindernoren/PyTorch-GAN` and `eriklindernoren/Keras-GAN`. Easy to debug, easy to break.
2. **TimeGAN** — Yoon, Jarrett, van der Schaar 2019. Combines a supervised reconstruction loss + adversarial loss + embedder/recovery network. Best off-the-shelf option for *sequential* generation that preserves temporal correlations. Reference: https://github.com/jsyoon0823/TimeGAN.

## Install / setup

```bash
uv pip install torch numpy pandas matplotlib statsmodels
# Optional, for TimeGAN reference implementation (TF1-era; use a fork or port):
uv pip install tensorflow  # if running the original repo
```

GPU notes:

- A vanilla 1-D GAN on returns trains fine on CPU. Move to GPU only if you scale to >32-dim windows or batch > 1024.
- The original TimeGAN code is TensorFlow 1.x — most users today reach for the PyTorch port `ydataai/ydata-synthetic` (which wraps TimeGAN) or `birdx0810/timegan-pytorch`. Both are unofficial — read the code before trusting outputs.

Verify install:

```python
import torch; print(torch.__version__, torch.cuda.is_available())
```

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

## Architecture choices

- **Generator width**: 64–128 hidden units is enough for univariate 32-bar return windows. Wider G is a quick path to overfitting.
- **Discriminator depth**: keep D shallower than G (or roughly equal). A too-strong D saturates and stops giving useful gradients to G.
- **Activations**: LeakyReLU(0.2) in hidden layers (standard GAN trick — avoids zero-gradient regions). Sigmoid only at D output; linear + `BCEWithLogitsLoss` is the more numerically stable variant.
- **Latent dim**: 8–32 for return windows. Smaller than your window length is fine; the G has to *expand* the latent to a meaningful path.
- **Window length**: 32–64 returns is a sane starting point. Longer windows magnify the temporal-correlation problem and push you toward TimeGAN.
- **Batch size**: 64–256. Smaller batches give noisier gradients (sometimes helpful for GANs), but anything <32 is fragile.
- **Tanh on G output**: clip the simulated returns. Without it, occasional samples will be 50-sigma outliers; with it, you must rescale by the real std to recover units.

## Common pitfalls

1. **Mode collapse.** G learns to emit one or two "winning" samples that fool D. Symptom: all generated windows look identical, or histogram has a single peak. Mitigations: (a) instance noise (add small noise to D inputs), (b) two-time-scale update rule (different LRs for G vs D), (c) Wasserstein-GP loss (`Critic` + gradient penalty) instead of vanilla BCE, (d) MO-GAAL-style multiple sub-generators.
2. **D wins instantly, G stops learning.** If `loss_d` crashes to near zero in <100 steps, D is too strong. Cut D capacity, add dropout to D (already in the snippet), or train G twice per D step.
3. **Stat mismatch after training.** Even a stable GAN can match marginal mean/std but break on ACF, volatility clustering, or fat-tailedness. **Always** compare ACF and kurtosis between real and fake — not just mean/std.
4. **Look-ahead in evaluation.** Don't compute "real stats" on the same windows you trained on. Split chronologically, train on the first 70%, eval against the last 30%.
5. **Rescaling errors.** If you normalised inputs to N(0,1) and put a Tanh on the output, samples are in [-1, 1]. You must `samples * train_std + train_mean` to put them back in return units — easy to forget.
6. **Learning rate tuning.** GANs are notoriously LR-sensitive. The DCGAN defaults `(lr=2e-4, betas=(0.5, 0.999))` work surprisingly often; if they don't, sweep LR over `[5e-5, 1e-4, 2e-4, 5e-4]` for both G and D *separately*.

## Evaluating synthetic series

Marginal stats (mean / std / kurtosis) are necessary but not sufficient. The checklist that catches most fakes:

| Check | Reasonable test |
|---|---|
| Marginal moments | `np.mean`, `np.std`, `scipy.stats.kurtosis` — within 10% of real |
| Autocorrelation | `statsmodels.tsa.stattools.acf(samples, nlags=20)` matches real at lags 1-5 |
| Volatility clustering | ACF of squared returns — most return series show slow decay; vanilla GAN usually misses this, TimeGAN can capture it |
| Fat tails | QQ-plot against real returns; or compare 1st/99th percentiles |
| Two-sample test | Kolmogorov-Smirnov or Anderson-Darling: real-vs-fake |
| Downstream task | Train your strategy on fake-only data, evaluate on real. Sharpe degradation tells you how useful the GAN actually is |

If any of these fail, do not use the samples for backtesting. A GAN that matches mean and std but has zero kurtosis is *worse than Gaussian noise* for stress tests.

## Scaling to production

- **Snapshot the generator.** Save `g.state_dict()` after training; ditch the discriminator at deploy time. Inference is just `g(z)`, dirt cheap.
- **Conditional sampling.** Concatenate a one-hot regime label to `z` to get a conditional GAN (CGAN). Train on labeled regimes (e.g. bull/bear/range) and sample from the regime you want. Easy 5-line extension to the minimal example.
- **Wasserstein-GP variant.** Replace BCE with the Wasserstein loss + gradient penalty (`WGAN-GP`) when vanilla training is unstable. The eriklindernoren repo has a reference `wgan_gp.py` worth copying line-for-line.
- **Reproducibility.** Set `torch.manual_seed(0)` *and* `np.random.seed(0)` before training. GAN training trajectories are extremely sensitive to seed.

## Diagnostics

Standard "is my GAN learning" sanity checks:

1. Plot G and D loss over training. Healthy: both oscillate in a band around 0.5-0.7 BCE. Sick: D loss → 0 fast (D too strong), or G loss → ∞ (collapse).
2. Histogram of generated samples vs. real, refreshed every 500 steps. Watch the modes appear.
3. Sample 1000 latents, generate, compute pairwise distances. If all generated samples are within 1e-3 of each other → mode collapse.
4. Inspect `(d(real) - d(fake)).mean()` — should be ~0 in steady-state training.

## References

### Primary library
- [eriklindernoren/PyTorch-GAN](https://github.com/eriklindernoren/PyTorch-GAN) — the reference repository for vanilla GAN, DCGAN, WGAN, WGAN-GP, CGAN, CycleGAN; the patterns this skill ports
- [eriklindernoren/Keras-GAN](https://github.com/eriklindernoren/Keras-GAN) — same algorithms in Keras; useful for cross-framework reading
- [jsyoon0823/TimeGAN](https://github.com/jsyoon0823/TimeGAN) — the original TimeGAN repo (TF 1.x); read for the three-phase training schedule
- [ydataai/ydata-synthetic](https://github.com/ydataai/ydata-synthetic) — maintained Python library that wraps TimeGAN + several other generators; PyTorch-friendly
- [birdx0810/timegan-pytorch](https://github.com/birdx0810/timegan-pytorch) — unofficial PyTorch port of TimeGAN; read the code before trusting outputs
- [PyTorch on GitHub](https://github.com/pytorch/pytorch) — for the hand-rolled training loops

### Deep-dive docs (specific pages worth bookmarking)
- [PyTorch `torch.nn.BCEWithLogitsLoss`](https://pytorch.org/docs/stable/generated/torch.nn.BCEWithLogitsLoss.html) — the numerically-stable replacement for `BCELoss` + sigmoid; should be the default
- [PyTorch `torch.optim.Adam`](https://pytorch.org/docs/stable/generated/torch.optim.Adam.html) — covers the `betas=(0.5, 0.999)` recipe; the lone optimizer config most GAN papers settle on
- [PyTorch-GAN: WGAN-GP implementation](https://github.com/eriklindernoren/PyTorch-GAN/blob/master/implementations/wgan_gp/wgan_gp.py) — the gradient-penalty trick worth copying line for line when vanilla BCE training is unstable
- [TimeGAN supplementary material (van der Schaar lab)](https://www.vanderschaar-lab.com/papers/NIPS2019_TGAN_Supplementary.pdf) — the math of the embedder/recovery/supervisor losses; the gap between the paper and the code
- [statsmodels `tsa.stattools.acf`](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.acf.html) — used in the evaluation checklist; computes ACF and confidence bands

### Adjacent / alternative libraries
- [Synthcity](https://github.com/vanderschaarlab/synthcity) — the van der Schaar lab's broader synthetic data library; TimeGAN, DoppelGANger, GoggleGAN under one API
- [PyTorch Lightning Bolts](https://github.com/Lightning-Universe/lightning-bolts) — pre-built `LitGAN` / `LitDCGAN` modules
- [HuggingFace diffusers](https://github.com/huggingface/diffusers) — denoising diffusion alternative to GANs; more stable, higher-quality samples; relevant when GAN training keeps failing
- [PyOD's `MO_GAAL`](https://github.com/yzhao062/pyod/blob/master/pyod/models/mo_gaal.py) — multi-generator GAN repurposed as anomaly detector; pairs with `autoencoder-anomaly-detection` skill
- [DoppelGANger](https://github.com/fjxmlzn/DoppelGANger) — purpose-built for time series with metadata; an alternative to TimeGAN when conditional generation matters

### Academic papers
- Goodfellow, I., Pouget-Abadie, J., Mirza, M., Xu, B., Warde-Farley, D., Ozair, S., Courville, A., & Bengio, Y. (2014). "Generative Adversarial Nets." *NeurIPS 2014*. [arXiv:1406.2661](https://arxiv.org/abs/1406.2661) — the original GAN paper.
- Radford, A., Metz, L., & Chintala, S. (2016). "Unsupervised Representation Learning with Deep Convolutional Generative Adversarial Networks (DCGAN)." *ICLR 2016*. [arXiv:1511.06434](https://arxiv.org/abs/1511.06434) — the `lr=2e-4, betas=(0.5, 0.999)` recipe + architectural guidelines.
- Salimans, T., Goodfellow, I., Zaremba, W., Cheung, V., Radford, A., & Chen, X. (2016). "Improved Techniques for Training GANs." *NeurIPS 2016*. [arXiv:1606.03498](https://arxiv.org/abs/1606.03498) — instance noise, feature matching, minibatch discrimination, virtual batch norm.
- Arjovsky, M., Chintala, S., & Bottou, L. (2017). "Wasserstein GAN." [arXiv:1701.07875](https://arxiv.org/abs/1701.07875) — the loss change that single-handedly fixes most vanilla-GAN instability.
- Gulrajani, I., Ahmed, F., Arjovsky, M., Dumoulin, V., & Courville, A. (2017). "Improved Training of Wasserstein GANs." *NeurIPS 2017*. [arXiv:1704.00028](https://arxiv.org/abs/1704.00028) — WGAN-GP; the gradient penalty variant that's the practical default now.
- Yoon, J., Jarrett, D., & van der Schaar, M. (2019). "Time-series Generative Adversarial Networks." *NeurIPS 2019*. [NIPS paper page](https://papers.nips.cc/paper/8789-time-series-generative-adversarial-networks) — TimeGAN; the embedder/recovery/supervisor architecture.
- Heusel, M., Ramsauer, H., Unterthiner, T., Nessler, B., & Hochreiter, S. (2017). "GANs Trained by a Two Time-Scale Update Rule Converge to a Local Nash Equilibrium." *NeurIPS 2017*. [arXiv:1706.08500](https://arxiv.org/abs/1706.08500) — TTUR + FID metric; the standard convergence-acceleration trick.

### Tutorials & write-ups
- [PyTorch DCGAN tutorial](https://pytorch.org/tutorials/beginner/dcgan_faces_tutorial.html) — the official walkthrough this skill's minimal example follows
- [Machine Learning for Trading (Jansen) — synthetic time series with GANs](https://stefan-jansen.github.io/machine-learning-for-trading/21_gans_for_synthetic_time_series/) — Stefan Jansen's chapter showing TimeGAN on financial returns end to end
- [TimeGAN reproducibility study (Hagner et al.)](https://arxiv.org/abs/2102.12001) — independent reproduction; useful failure-mode catalogue

### Standard datasets / benchmarks
- Stock daily returns from `yfinance` (any ticker, 5+ years) — the standard reproducibility setup; train on years 1-3, evaluate marginal moments and ACF on years 4-5
- Sines + autoregressive synthetic data from the TimeGAN repo — the "definitely works" sanity check
- UCI HEPMASS / energy / quark-gluon datasets — non-finance benchmarks the TimeGAN paper uses; if your model fails on these, the bug is implementation not data

### Last cross-checked
2026-05-20 — via Context7 `/pytorch/pytorch` + WebSearch verification of all paper arXiv IDs / NeurIPS URLs.
