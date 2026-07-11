---
name: pinn-training
version: 0.1.0
description: >-
  Train Physics-Informed Neural Networks (PINNs) with DeepXDE to solve forward
  and inverse PDE problems by embedding the governing equations directly in the
  training loss (PDE residual via autodiff + boundary/initial-condition penalties
  + optional data-fit terms). Use when solving PDEs on complex or mesh-hostile
  geometries, discovering unknown PDE coefficients or fields from sparse/noisy
  measurements (inverse problems), building a differentiable surrogate of a
  solution, or coupling multiple physics. Covers geometry/time-domain setup,
  residual definition, the Adam then L-BFGS two-stage schedule, loss weighting,
  adaptive collocation sampling, and architecture choices. Do NOT use for simple
  low-dimensional problems on regular grids where finite-difference/finite-element
  solvers are faster and more accurate, when you need rigorous a-posteriori error
  bounds, or when you require better than roughly 1e-6 relative accuracy —
  classical numerical solvers win decisively there.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "LGPL-2.1 (DeepXDE)"
---

# PINN Training with DeepXDE

## Overview

A Physics-Informed Neural Network approximates the solution of a PDE, `u(x, t)`,
with a small feed-forward network. Instead of fitting labelled data, you train
the network to make the PDE *residual* vanish: automatic differentiation gives
the network's own derivatives (`u_t`, `u_xx`, ...), you plug them into the
governing equation, and the squared residual becomes a loss term. Boundary and
initial conditions add more loss terms; optional measurement data adds a fit
term.

DeepXDE turns this into a declarative pipeline. You always follow the same six
steps:

1. **Geometry** — the spatial domain (and a time domain if transient).
2. **Residual** — a Python function returning the PDE residual using
   `dde.grad.jacobian` / `dde.grad.hessian`.
3. **Constraints** — boundary conditions, initial conditions, and/or observed
   data points.
4. **Data object** — bundles geometry + residual + constraints and samples
   collocation points.
5. **Network** — a fully-connected net sized to the problem.
6. **Compile & train** — Adam to get near the minimum, then L-BFGS to polish.

**Forward problems** solve a fully specified PDE. **Inverse problems** make one
or more unknown coefficients (or fields) trainable and recover them from data —
the same pipeline with a `dde.Variable` in the residual and a data constraint.

## When to Use This Skill

- Complex or high-dimensional geometries where meshing is painful or expensive.
- **Inverse problems**: discovering unknown PDE parameters or source fields from
  sparse, noisy measurements when you know the governing equation.
- Data assimilation: blending a known PDE with scattered observations.
- Coupled / multi-physics systems expressed as several PDE residuals.
- You need a smooth, **differentiable surrogate** of the solution (e.g. for
  downstream optimization or sensitivity analysis).

## When NOT to Use This Skill

- Simple 1D/2D problems on regular grids — finite differences or finite elements
  are faster, more accurate, and come with theory.
- You need **rigorous error bounds** — PINNs give no a-posteriori guarantees.
- You need very high accuracy (better than ~1e-6 relative error is hard).
- Sharp shocks / discontinuities without special handling — vanilla PINNs
  smear them.
- You have dense labelled solution data and no physics you care to enforce —
  train an ordinary regressor (see the `pytorch-lightning` skill).

## Setup and Backend

```bash
pip install deepxde
```

DeepXDE runs on TensorFlow, PyTorch, JAX, or PaddlePaddle. Pick one explicitly —
the choice affects which optimizers and features are available:

```bash
export DDE_BACKEND=pytorch   # then install the backend (e.g. torch + CUDA)
```

PyTorch is the most-exercised backend and the simplest path to GPU training.
See `references/api-reference.md` for backend-specific caveats.

## Minimal Forward-Problem Skeleton

1D heat equation `u_t = alpha * u_xx` on `x in [0,1]`, `t in [0,1]`, with zero
Dirichlet boundaries and `u(x,0) = sin(pi x)`:

```python
import deepxde as dde
import numpy as np

alpha = 0.01

def pde(x, u):                                    # x[:,0]=space, x[:,1]=time
    u_t  = dde.grad.jacobian(u, x, i=0, j=1)      # du/dt
    u_xx = dde.grad.hessian(u, x, i=0, j=0)       # d2u/dx2
    return u_t - alpha * u_xx

geom      = dde.geometry.Interval(0, 1)
timedomain = dde.geometry.TimeDomain(0, 1)
geomtime  = dde.geometry.GeometryXTime(geom, timedomain)

bc = dde.icbc.DirichletBC(geomtime, lambda x: 0, lambda x, on_bnd: on_bnd)
ic = dde.icbc.IC(geomtime, lambda x: np.sin(np.pi * x[:, 0:1]),
                 lambda x, on_init: on_init)

data = dde.data.TimePDE(geomtime, pde, [bc, ic],
                        num_domain=2000, num_boundary=100,
                        num_initial=100, num_test=500)

net   = dde.nn.FNN([2] + [64] * 3 + [1], "tanh", "Glorot uniform")
model = dde.Model(data, net)

model.compile("adam", lr=1e-3)
model.train(iterations=10000, display_every=2000)   # 'epochs=' is the old alias
model.compile("L-BFGS")
model.train()
```

Then `model.predict(X)` on an `(N, 2)` array of `(x, t)` points returns the
solution. Full runnable versions — including exact-solution error checks — are in
`references/examples.md`.

## Where to Go Next

The body above is the router. Reach for the references for depth:

- **`references/examples.md`** — complete, runnable programs: 1D heat (forward),
  inverse diffusion-coefficient discovery, 2D Poisson, and hard-constraint
  (output-transform) boundary enforcement.
- **`references/api-reference.md`** — the DeepXDE building blocks by category:
  geometry & time domains, `icbc` constraint types, `data` classes, `nn`
  architectures, `dde.grad` autodiff helpers, `Model` methods, optimizers,
  callbacks (including `VariableValue` for tracking inverse variables), and
  save/plot utilities.
- **`references/training-and-troubleshooting.md`** — the Adam→L-BFGS schedule,
  network-architecture sizing guide, loss weighting for imbalanced BC/IC/PDE
  terms, residual-based adaptive refinement (RAR), and a symptom→fix table for
  the failures you will actually hit (flat solutions, sign errors, stalled
  inverse problems, instability).

## Inverse Problems in One Line

Make the unknown trainable, add measurements, and pass the variable to the
optimizer:

```python
alpha_var = dde.Variable(0.05)                       # initial guess
# ... use alpha_var inside pde(); add dde.icbc.PointSetBC(x_obs, u_obs) ...
model.compile("adam", lr=1e-3, external_trainable_variables=[alpha_var])
```

Track the recovered value across training with
`dde.callbacks.VariableValue(alpha_var, period=1000)`. See
`references/examples.md` for the full inverse workflow.

## Related Skills

For visualizing predicted fields and error maps, use the `matplotlib` or
`scientific-visualization` skills. For general (non-physics) neural-network
training, use `pytorch-lightning`.
