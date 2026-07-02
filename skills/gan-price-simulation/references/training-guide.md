# Training Guide — architecture, pitfalls, diagnostics, scaling

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

## Diagnostics

Standard "is my GAN learning" sanity checks:

1. Plot G and D loss over training. Healthy: both oscillate in a band around 0.5-0.7 BCE. Sick: D loss → 0 fast (D too strong), or G loss → ∞ (collapse).
2. Histogram of generated samples vs. real, refreshed every 500 steps. Watch the modes appear.
3. Sample 1000 latents, generate, compute pairwise distances. If all generated samples are within 1e-3 of each other → mode collapse.
4. Inspect `(d(real) - d(fake)).mean()` — should be ~0 in steady-state training.

## Scaling to production

- **Snapshot the generator.** Save `g.state_dict()` after training; ditch the discriminator at deploy time. Inference is just `g(z)`, dirt cheap.
- **Conditional sampling.** Concatenate a one-hot regime label to `z` to get a conditional GAN (CGAN). Train on labeled regimes (e.g. bull/bear/range) and sample from the regime you want. Easy 5-line extension to the minimal example.
- **Wasserstein-GP variant.** Replace BCE with the Wasserstein loss + gradient penalty (`WGAN-GP`) when vanilla training is unstable. The eriklindernoren repo has a reference `wgan_gp.py` worth copying line-for-line.
- **Reproducibility.** Set `torch.manual_seed(0)` *and* `np.random.seed(0)` before training. GAN training trajectories are extremely sensitive to seed.

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
