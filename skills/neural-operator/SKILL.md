---
name: neural-operator
version: 0.1.0
description: >-
  Train neural operators (Fourier Neural Operator / FNO, tensorized TFNO, and
  branch-trunk DeepONet) with the neuraloperator (`neuralop`) PyTorch library to
  learn the solution map of a parametric PDE family from a dataset of solved
  instances; once trained, evaluate new instances (new initial/boundary
  conditions or coefficients) in milliseconds, and — for FNO — at resolutions
  never seen in training. Use when you must solve the SAME PDE family many times
  with varying parameters, build a fast surrogate for an expensive solver, or
  need real-time inference for design, control, or optimization. Do NOT use for a
  single one-off PDE solve (use `pde-solver`), when you have no training data yet
  (generate it first), when you need very high accuracy (below ~0.1% relative
  error), or for long-horizon autoregressive time-stepping (use
  `autoregressive-neural-pde-solver`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "MIT (neuraloperator / neuralop)"
---

# Neural Operators (FNO, TFNO, DeepONet)

## Overview

A neural operator learns a mapping between *function spaces*: given an input
function sampled on a grid (an initial condition, a forcing term, a coefficient
field, a boundary), it predicts the output function (the PDE solution). Unlike a
classical solver that runs from scratch for every new instance, a trained
operator amortizes the cost — one forward pass, milliseconds, for any new
instance drawn from the same PDE family. The **Fourier Neural Operator (FNO)** is
the default: it mixes information globally through learned filters in the Fourier
domain and is *discretization-invariant*, so it can be trained on one grid
resolution and evaluated on a finer one (zero-shot super-resolution).

This skill uses the `neuralop` package (PyPI name `neuraloperator`), which ships
FNO, TFNO, SFNO, UNO, GINO and a `Trainer`. DeepONet is not in the library; a
compact branch-trunk implementation is provided in the references.

## When to Use This Skill

- You must solve the **same PDE family** repeatedly with different parameters,
  initial/boundary conditions, or coefficient fields.
- You are building a **surrogate** to replace an expensive FEM/spectral/FD solver
  inside an outer loop (design optimization, control, uncertainty quantification).
- You need **real-time** or **batched** inference where a classical solve is too slow.
- You already have (or can cheaply generate) a few hundred to a few thousand
  solved instances to train on.

## When NOT to Use This Skill

- You need to solve **one** PDE instance — a direct solve is faster and exact; use
  `pde-solver`.
- You have **no training data**. Generate it first (e.g. run `pde-solver` a few
  hundred times over sampled parameters), then return here.
- You need **very high accuracy** (below ~0.1% relative L2). Neural operators
  typically land at 0.5–5% relative error.
- The **physics changes fundamentally** between instances (different governing
  equations, not just different parameters) — one operator cannot cover it.
- You want **long-horizon autoregressive rollouts** of a time-dependent PDE; that
  is a different training regime — use `autoregressive-neural-pde-solver`.

## Setup

```bash
pip install neuraloperator torch
```

Import gotcha: the PyPI distribution is `neuraloperator` but the **import
namespace is `neuralop`** (e.g. `from neuralop.models import FNO`). Older tutorials
that import `neuraloperator.models` or class names like `FNO1d` target a removed
API — use `FNO(n_modes=(...))`.

## The minimal FNO recipe

Five steps: generate solved instances → normalize → instantiate FNO →
train → evaluate on held-out instances with **relative L2** (not raw MSE).

```python
import torch
from neuralop.models import FNO

# FNO input is CHANNEL-FIRST: (batch, in_channels, *spatial).
# 1D field of length N -> (B, 1, N);  2D field HxW -> (B, 1, H, W).
model = FNO(
    n_modes=(16,),        # Fourier modes kept per spatial dim; (16, 16) in 2D
    hidden_channels=64,   # channel width
    in_channels=1,        # e.g. the initial condition
    out_channels=1,       # e.g. the solution at final time
    n_layers=4,
)

optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)

for epoch in range(500):                 # x_train, y_train: (N, 1, grid...)
    model.train()
    pred = model(x_train)
    loss = torch.nn.functional.mse_loss(pred, y_train)
    optimizer.zero_grad(); loss.backward(); optimizer.step()

# Report relative L2, which is scale-invariant and standard for operators:
model.eval()
with torch.no_grad():
    pred = model(x_test)
rel_l2 = (torch.linalg.norm((pred - y_test).flatten(1), dim=1)
          / torch.linalg.norm(y_test.flatten(1), dim=1)).mean()
```

Always **normalize inputs and outputs** (zero mean, unit variance) before
training and de-normalize predictions before reporting. The full worked example —
Burgers data generation, normalization, mini-batching, the library `Trainer` with
`LpLoss`/`H1Loss`, `load_darcy_flow_small` for 2D Darcy flow, evaluation and
plotting, plus zero-shot super-resolution — is in
[references/fno-workflow.md](references/fno-workflow.md).

## Choosing an architecture

| Architecture | Best for | Notes |
|---|---|---|
| **FNO** | Regular grids, (quasi-)periodic domains | Default; discretization-invariant |
| **TFNO** | Same as FNO, fewer parameters | Tucker-factorized spectral weights |
| **DeepONet** | Irregular sampling, arbitrary query points | Branch-trunk; not in `neuralop` (roll your own) |
| **GINO / GNO** | Unstructured meshes, point clouds, complex geometry | Graph/geometry-informed |
| **SFNO / UNO** | Spherical data / multiscale features | Sphere-aware / U-shaped variants |

Full selection guidance, input conventions per architecture, and a complete
DeepONet branch-trunk implementation are in
[references/architectures.md](references/architectures.md).

## Tuning and debugging

Key knobs are `n_modes` (frequency resolution — too few over-smooths the output),
`hidden_channels`, `n_layers`, learning rate, and training-set size. The
hyperparameter table, normalization advice, metrics (relative L2 vs H1), and a
symptom→fix troubleshooting table (over-smoothing, channel-order bugs, overfitting,
resolution mismatch, OOM, non-periodic boundaries) are in
[references/hyperparameters-and-troubleshooting.md](references/hyperparameters-and-troubleshooting.md).

## Related skills

- `pde-solver` — solve a single PDE instance directly, and generate the training
  data this skill consumes.
- `autoregressive-neural-pde-solver` — learned time-stepping for long-horizon
  rollouts of time-dependent PDEs.
- `fluid-dynamics` — governing equations and reference solvers for common
  fluid-flow PDE families you might surrogate.
