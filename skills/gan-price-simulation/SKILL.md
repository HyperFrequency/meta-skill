---
name: gan-price-simulation
version: 0.1.0
description: GAN-based synthetic price and return simulation. Walks the vanilla 1-D GAN baseline (eriklindernoren/PyTorch-GAN style) for univariate return series and points to TimeGAN for sequential conditional generation. Covers training loop, sample-vs-real statistics check (mean, std, ACF), and the standard failure modes. Not for i.i.d. bootstrap sampling, density estimation, or small datasets (<10k bars).
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
license: MIT (PyTorch-GAN upstream)
metadata:
    skill-author: HyperFrequency
    skill-domain: deep-learning / quant
---

# GAN Price Simulation

Generate synthetic return / price series that match real-data statistics — for augmentation, stress testing, or Monte-Carlo backtests with a learned generator. This file is a router; detailed material lives in `references/`.

## When to use

- Augment a small dataset before training a downstream model.
- Stress-test a strategy by drawing from a learned distribution of returns instead of i.i.d. Gaussian.
- Build a "what-if" simulator for an asset where you have limited history.
- Generate paired regime / conditional samples (TimeGAN, with auxiliary regime label).

Do **not** use a GAN if:

- You just need i.i.d. samples from an empirical distribution — bootstrap is simpler and unbiased.
- You need calibrated uncertainty for a forecast — GANs do not give density estimates (use normalizing flows or PyMC).
- You only have a few thousand bars. GANs are data-hungry; with <10k samples, mode collapse is near-guaranteed.

## Two paths

1. **Vanilla 1-D GAN** — small MLP generator + discriminator on flattened return windows. Reference: `eriklindernoren/PyTorch-GAN`. Easy to debug, easy to break. Use when real-return ACF is ~0 (the typical daily-returns case).
2. **TimeGAN** — Yoon, Jarrett, van der Schaar (NeurIPS 2019). Supervised reconstruction + adversarial loss + embedder/recovery network. Best off-the-shelf option for *sequential* generation that preserves temporal correlations (non-zero ACF, volatility clustering). Reference: https://github.com/jsyoon0823/TimeGAN.

## Workflow

1. Install deps and verify torch — see `references/training-guide.md` (Install / setup) → verify: `import torch` prints version + CUDA flag.
2. Build the vanilla G+D training loop, sample, compare stats — see `references/code-examples.md` → verify: fake mean/std within ~10% of real; fake ACF[1:5] ≈ real ACF[1:5].
3. If real ACF is non-zero or volatility clusters, switch to TimeGAN — see `references/code-examples.md` (TimeGAN section).
4. Evaluate beyond marginal moments before trusting samples — see `references/evaluation.md` → verify: ACF, kurtosis, KS test, and downstream-task checks pass.
5. Tune architecture / debug instability / scale to production — see `references/training-guide.md`.

## Reference map

| File | Contents |
|---|---|
| `references/code-examples.md` | Vanilla 1-D GAN minimal example (≤60 lines), TimeGAN runner pseudocode, key API surface (PyTorch building blocks + TimeGAN networks) |
| `references/training-guide.md` | Install/setup + GPU notes, architecture choices, common pitfalls (mode collapse, D-wins-instantly, rescaling, LR tuning), diagnostics, scaling to production (CGAN, WGAN-GP, snapshotting) |
| `references/evaluation.md` | The synthetic-series evaluation checklist (marginal moments, ACF, vol clustering, fat tails, two-sample test, downstream Sharpe) |
| `references/references.md` | Libraries, deep-dive docs, academic papers, tutorials, datasets/benchmarks, last cross-check date |

## Gotchas (top-level)

- **Always check ACF and kurtosis**, not just mean/std. A GAN matching only mean/std is worse than Gaussian noise for stress tests.
- **Rescale outputs.** Normalised inputs + Tanh output → samples in [-1, 1]; multiply by `train_std` and add `train_mean` to recover return units.
- **No look-ahead.** Split chronologically; evaluate on held-out windows.
- **TimeGAN ports are unofficial** (`ydataai/ydata-synthetic`, `birdx0810/timegan-pytorch`) — read the code before trusting outputs.

## Adjacent skills

- `autoencoder-anomaly-detection` — shares the GAN/AE machinery (MO-GAAL).
- `strategy-translator` / nautilus-backtest skills — consume synthetic series for stress tests.
- For diffusion-based alternatives when GAN training keeps failing, see HuggingFace `diffusers` (noted in `references/references.md`).
