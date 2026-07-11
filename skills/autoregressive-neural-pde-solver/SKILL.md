---
name: autoregressive-neural-pde-solver
version: 0.1.0
description: >-
  Training patterns for autoregressive neural operators (FNO, DeepONet, CNO) that
  predict time-dependent PDE solutions by feeding their own outputs back as input.
  Covers rollout (autoregressive) training instead of teacher forcing, noise
  injection for rollout stability, multi-component losses (Sobolev H1,
  frequency-banded, boundary-aware), per-channel normalization for coupled
  multi-variable systems, and both PDEBench nRMSE definitions. Use when training or
  debugging any neural operator whose inference is multi-step rollout and single-step
  accuracy is not enough — e.g. Burgers, Navier-Stokes, MHD, reaction-diffusion.
  Do NOT use for steady-state or single-shot operator learning with no time rollout,
  physics-informed residual training (PINNs), classical numerical PDE solvers, or
  merely loading raw PDEBench HDF5 tensors (that is `hdf5-pde-data-loading`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# Autoregressive Neural PDE Solver Training

## Overview

A neural operator (FNO, DeepONet, CNO, U-Net surrogate) that solves a
time-dependent PDE is used autoregressively at inference: it predicts one (or a
few) timesteps ahead, then its own prediction is fed back as input for the next
step. Errors compound over the rollout. This skill collects the training-time
techniques that make long rollouts stable and accurate: training the way you
infer, injecting noise, shaping the loss for gradients/frequencies/boundaries,
normalizing coupled variables per channel, and reporting the metric benchmarks
actually use.

This is a training-recipe skill, not a model-architecture skill. It assumes you
already have a neural operator and a dataset of PDE trajectories; it tells you how
to train and evaluate it so rollouts do not blow up.

## When to Use This Skill

- Training any neural operator to predict a **time-dependent** PDE solution where
  inference is **multi-step rollout** (predict, feed back, repeat).
- Single-step (one-timestep-ahead) accuracy looks fine but rollouts diverge after
  a handful of steps.
- **Multi-variable coupled** systems (compressible Navier-Stokes, MHD,
  multi-species reaction-diffusion) where variables live on very different scales.
- Shock-, front-, or high-frequency-dominated problems where plain MSE smears
  sharp features.
- Reproducing PDEBench-style baselines and you need the correct nRMSE definition.

## When NOT to Use This Skill

- **Steady-state / single-shot** operator learning with no time rollout (map
  parameters → solution once). Autoregressive machinery adds nothing.
- **Physics-informed (PINN) training** that minimizes a PDE residual against
  collocation points rather than fitting supervised trajectory data — a different
  loss regime; use a PINN-focused skill instead.
- **Classical numerical solvers** (finite difference/volume/element, spectral).
  This skill is about *learned* surrogates.
- **Loading the data**: parsing raw PDEBench/HDF5 tensors, striding, and building
  DataLoaders is `hdf5-pde-data-loading`. Start there, then return here to train.

## Core Principle: Train the Way You Roll Out

The single most common failure is training with **teacher forcing** (every step
sees ground truth) but inferring with rollout (every step sees the model's own,
imperfect output). The model never learns to correct its own drift, so inference
errors compound exponentially.

```python
# WRONG — teacher forcing: input is always perfect ground truth
for t in range(T):
    pred = model(ground_truth[:, :, t])          # never sees its own mistakes
    loss += mse(pred, ground_truth[:, :, t + 1])

# RIGHT — autoregressive rollout: input is the model's own prediction
inp = initial_condition                          # [B, X, init_steps, C]
for t in range(init_steps, T_total):
    pred = model(inp)                            # sees its OWN previous output
    loss += mse(pred, ground_truth[:, :, t:t + 1, :])
    inp = torch.cat([inp[:, :, 1:, :], pred], dim=-2)   # slide window, append
loss.backward()                                  # ONE backward after full rollout
```

Accumulate the loss across the whole rollout window and call `backward()` **once**
at the end. Do not backpropagate per step with `retain_graph=True` — that leaks
the graph across the whole trajectory and causes GPU OOM.

Full training loop, the spatial-first data layout FNO expects, and gradient/memory
details are in **[references/rollout-training.md](references/rollout-training.md)**.

## Noise Injection for Rollout Stability

Add small Gaussian noise to each prediction **before** feeding it back during
training. This forces the model to be robust to the kind of imperfect input it
sees at inference instead of relying on artificially clean features.

```python
if model.training and NOISE_STD > 0:
    pred_fed = pred + NOISE_STD * torch.randn_like(pred)
inp = torch.cat([inp[:, :, 1:, :], pred_fed], dim=-2)
```

Rough dial: `σ = 0` for very smooth well-resolved problems, `1e-3` for moderate
dynamics (reaction-diffusion), `5e-3` for shock-dominated or chaotic problems.
Too much noise smears sharp features; too little does nothing for stability. See
the noise-vs-problem table in **[references/rollout-training.md](references/rollout-training.md)**.

## Loss Functions Beyond MSE

Plain MSE underweights gradients, high frequencies, and boundaries — exactly where
PDE surrogates fail. Add targeted terms:

- **Sobolev H1** — penalizes errors in spatial derivatives; essential for steep
  gradients, reaction fronts, shocks.
- **Frequency-banded** — splits the Fourier spectrum into bands with increasing
  weights to upweight high-frequency content.
- **Boundary-aware** — element-wise weight that upweights the domain edges where
  spectral operators struggle with non-periodic BCs.

Copy-paste implementations, weight-tuning guidance, and a per-problem-type
recommended-combination table (MSE / H1 / freq / noise / boundary) are in
**[references/loss-functions.md](references/loss-functions.md)**.

## Per-Channel Normalization and the Right Metric

For coupled multi-variable systems, variables can differ by orders of magnitude
(density ~O(6), velocity ~O(0.5), pressure ~O(59)); the loss silently becomes
"predict the largest-scale variable." Normalize **each channel independently**
using statistics from the **training split only**, and denormalize back to
original scale before computing any reported metric.

The PDEBench **nRMSE** has more than one valid definition (per-timestep RMS ratio
vs. per-sample Frobenius ratio) that can differ 5–10%. Compute **both** and verify
you beat baselines under both. Normalization code, both nRMSE implementations, the
denormalize helper, and the train/val/test discipline (select checkpoints on val,
touch test exactly once) are in
**[references/normalization-and-metrics.md](references/normalization-and-metrics.md)**.

## Common Pitfalls

| Pitfall | Symptom | Fix |
|---|---|---|
| Teacher forcing in training | Good train loss, rollout diverges | Autoregressive rollout training |
| Data laid out `[N,T,X]` not `[N,X,T]` | Model won't converge | Transpose before the DataLoader |
| No per-channel normalization | One variable dominates the loss | Normalize each channel independently |
| No noise injection | Rollout diverges after ~10 steps | Add `σ=1e-3` noise during training |
| Model selected on the test set | Optimistic reported metrics | Separate validation split |
| Per-step `backward(retain_graph=True)` | GPU OOM | One `backward()` after the full rollout |
| Reporting one nRMSE flavor | Looks better/worse than it is | Report both definitions |

## References

- **[references/rollout-training.md](references/rollout-training.md)** — data layout, full autoregressive loop, noise-vs-problem table, gradient/memory notes.
- **[references/loss-functions.md](references/loss-functions.md)** — H1, frequency-banded, and boundary-aware loss code plus the recommended-combination table.
- **[references/normalization-and-metrics.md](references/normalization-and-metrics.md)** — per-channel normalization, both nRMSE definitions, train/val/test split.

## Related Skills

- `hdf5-pde-data-loading` — load and stride raw PDEBench/HDF5 trajectories into tensors before training here.
- `pytorch-lightning` — wrap this training loop in a `LightningModule` for checkpointing, mixed precision, and multi-GPU.
