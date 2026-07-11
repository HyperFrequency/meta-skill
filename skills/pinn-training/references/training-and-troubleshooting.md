# PINN Training Strategy & Troubleshooting

Practical guidance for getting a DeepXDE PINN to converge. PINN training is
notoriously finicky; most failures are one of a handful of recurring issues
below.

---

## The Two-Stage Schedule (Adam → L-BFGS)

This is the standard recipe and you should default to it.

| Phase | Optimizer | Iterations | Learning rate | Purpose |
|---|---|---|---|---|
| 1 | Adam | 10k–30k | `1e-3` (decay optional) | Move into the basin of the minimum |
| 2 | L-BFGS | to convergence | (auto) | Polish to high accuracy |

```python
model.compile("adam", lr=1e-3)
model.train(iterations=15000, display_every=2000)
model.compile("L-BFGS")
model.train()
```

- L-BFGS is second-order and drives the loss much lower than Adam alone, but it
  needs a good starting point — never start with L-BFGS from random weights.
- Optionally decay the Adam learning rate:
  `model.compile("adam", lr=1e-3, decay=("inverse time", 2000, 0.9))`.

---

## Network Architecture Sizing

Start small; grow only if the loss plateaus above your target.

| PDE difficulty | Layer sizes | Activation |
|---|---|---|
| Simple 1D/2D | `[2] + [32]*3 + [1]` | `tanh` |
| Moderate 2D | `[2] + [64]*4 + [1]` | `tanh` |
| Complex / 3D | `[3] + [128]*5 + [1]` | `tanh` or `sin` |
| High-frequency solution | `[d] + [128]*5 + [1]` + Fourier feature transform | `sin` |

Guidance:
- Depth adds representational power for sharp features; width smooths.
- `sin` activation (SIREN-style) captures oscillatory solutions the `tanh` net
  struggles with — but is more sensitive to initialization.
- Never use `relu`: its second derivative is zero almost everywhere, so any
  residual containing `u_xx` collapses.

---

## Loss Weighting

The total loss is a weighted sum of the PDE residual and each BC/IC/data term.
When one term dominates or lags, the network satisfies it at the expense of the
others. Rebalance with `loss_weights` (ordered `[pde, *bcs]` matching the list
you passed to the data object):

```python
model.compile("adam", lr=1e-3, loss_weights=[1, 100, 100])
# weight 1 on the PDE residual, 100 on each of two BC/IC terms
```

Alternatives when static weights are not enough:
- **Hard constraints**: enforce a Dirichlet BC exactly via
  `net.apply_output_transform` so it drops out of the loss entirely (see
  `examples.md` §4). Often the most robust fix.
- Normalize inputs/outputs to O(1) with `apply_feature_transform` /
  `apply_output_transform` so gradients are well-scaled.

---

## Adaptive Collocation (RAR)

Uniformly sampled collocation points waste capacity where the solution is easy
and under-resolve where the residual is large (sharp gradients, boundary
layers). Residual-based adaptive refinement adds points where the residual is
worst:

- Add anchors mid-training by evaluating the residual on a dense candidate grid
  (`model.predict(X, operator=pde)`), taking the highest-residual points, and
  calling `data.add_anchors(new_points)` before continuing training.
- Or resample periodically with `dde.callbacks.PDEPointResampler(period=N)`.

Reach for this when a stubborn region of the domain refuses to converge.

---

## Symptom → Fix

| Symptom | Likely cause | Fix |
|---|---|---|
| Loss doesn't decrease at all | LR too high/low, net too small, bug in residual | Try `lr=1e-3`, enlarge the net, print residual on a known point |
| BC/IC loss ≫ PDE loss (or vice-versa) | Imbalanced loss terms | Set `loss_weights`, or enforce BCs as hard constraints |
| Solution is flat / constant | Sign error or wrong index in the residual | Re-derive `pde`; check `i`/`j` in `jacobian`/`hessian` and time-column index |
| Training unstable / diverges | `relu` activation, LR too high, unnormalized scales | Use `tanh`/`sin`, lower LR, normalize inputs/outputs |
| Accurate interior, wrong at boundary | BC under-weighted or under-sampled | Raise BC weight, increase `num_boundary`, or hard-constrain |
| Sharp gradient region stays wrong | Uniform sampling under-resolves it | Apply RAR / `PDEPointResampler`; add `sin` activation |
| Inverse problem won't converge | Too few observations, bad initial guess, or unidentifiable parameter | Add more `PointSetBC` data, improve the `dde.Variable` initial value, check identifiability |
| L-BFGS stops immediately | Started from random weights | Run Adam first, then switch to L-BFGS |
| Very slow | CPU-bound | Use the PyTorch backend with CUDA (`export DDE_BACKEND=pytorch`) |

---

## Sanity Checklist Before a Long Run

1. Does the residual return ~0 when you feed it the known/analytic solution?
   (Manufacture a solution and test.)
2. Are inputs and outputs O(1)? If not, normalize.
3. Is `num_test` set so the reported test loss is meaningful?
4. For time problems, is the time column index correct in every derivative call?
5. For inverse problems, is the `dde.Variable` passed to *every* `compile` call
   via `external_trainable_variables`?
