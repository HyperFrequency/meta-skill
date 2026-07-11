# Physics-Informed Neural Networks with DeepXDE

DeepXDE (`pip install deepxde`, TensorFlow or PyTorch backend) trains a neural network to
satisfy a PDE by minimizing the PDE **residual** on collocation points plus the BC/IC error
— no mesh. PINNs shine for **inverse problems** (recover unknown parameters from data),
irregular domains, and high dimensions where meshing is painful. They are usually *slower
and less accurate than finite differences* on simple forward problems — reach for them when
the classical methods do not fit.

> API note: recent DeepXDE names the training-length argument `iterations=`; older releases
> used `epochs=` (still accepted with a deprecation warning). Boundary/initial conditions
> live under `dde.icbc.*` in current versions (older code used `dde.DirichletBC` directly).

---

## Forward problem — Laplace equation on the unit square

`u_xx + u_yy = 0`, with `u = sin(πx)` on the bottom edge and `u = 0` on the others.

```python
import deepxde as dde
import numpy as np

def pde(x, y):                                   # residual: u_xx + u_yy = 0
    u_xx = dde.grad.hessian(y, x, i=0, j=0)      # ∂²u/∂x²
    u_yy = dde.grad.hessian(y, x, i=1, j=1)      # ∂²u/∂y²
    return u_xx + u_yy

geom = dde.geometry.Rectangle([0, 0], [1, 1])

def on_bottom(x, on_boundary):
    return on_boundary and np.isclose(x[1], 0.0)

bc_bottom = dde.icbc.DirichletBC(
    geom, lambda x: np.sin(np.pi * x[:, 0:1]), on_bottom)
bc_rest = dde.icbc.DirichletBC(
    geom, lambda x: 0.0,
    lambda x, on_boundary: on_boundary and not np.isclose(x[1], 0.0))

data = dde.data.PDE(geom, pde, [bc_bottom, bc_rest],
                    num_domain=2000, num_boundary=200)
net = dde.nn.FNN([2] + [64] * 3 + [1], "tanh", "Glorot uniform")
model = dde.Model(data, net)

model.compile("adam", lr=1e-3)
model.train(iterations=10000)                    # Adam to get in the basin
model.compile("L-BFGS")                          # then L-BFGS to polish
model.train()

u_pred = model.predict(np.array([[0.5, 0.5]]))
```

**Two-stage training is standard**: Adam for a fixed number of iterations to reach a good
region, then L-BFGS (quasi-Newton, no learning rate) to converge to high accuracy.

### Time-dependent forward problems

Add time as an extra input dimension via a `dde.geometry.GeometryXTime` combining a spatial
geometry with `dde.geometry.TimeDomain(t0, t1)`, use `dde.icbc.IC(...)` for the initial
condition, and take time derivatives inside the residual with
`dde.grad.jacobian(y, x, i=0, j=t_index)`. Then build `dde.data.TimePDE(...)` instead of
`dde.data.PDE(...)`.

---

## Inverse problem — recover an unknown coefficient from data

Embed the unknown as a trainable `dde.Variable`, add measured observations as a
`PointSetBC`, and register the variable with `external_trainable_variables`. Example:
recover the diffusivity `C` in `u_t = C u_xx` from sampled `(x, t, u)` observations.

```python
C = dde.Variable(2.0)                             # initial guess for the unknown

def pde(x, y):
    u_t  = dde.grad.jacobian(y, x, i=0, j=1)      # ∂u/∂t   (x[:,1] is time)
    u_xx = dde.grad.hessian(y, x, i=0, j=0)       # ∂²u/∂x²
    return u_t - C * u_xx

observe = dde.icbc.PointSetBC(observe_x, observe_u)   # measured data anchors the fit
data = dde.data.TimePDE(geomtime, pde, [ic, bc, observe],
                        num_domain=2000, num_boundary=100,
                        anchors=observe_x)

model = dde.Model(data, net)
model.compile("adam", lr=1e-3, external_trainable_variables=[C])
track = dde.callbacks.VariableValue(C, period=1000, filename="C_history.dat")
model.train(iterations=20000, callbacks=[track])
print("recovered C =", C.value if hasattr(C, "value") else C)
```

Without observation data an inverse problem is unconstrained — you must supply measured
points (via `PointSetBC` and usually as `anchors`) or the parameter drifts freely.

---

## Practical tips

- **Loss weights.** BC/IC/residual/data terms compete. If the network satisfies the PDE but
  ignores the BCs (or vice versa), pass `loss_weights=[...]` to `model.compile` to rebalance
  — a large BC weight enforces boundaries harder.
- **Hard-constrain BCs.** Multiply the network output by a function that is zero on the
  boundary (an `output_transform` via `net.apply_output_transform`) so Dirichlet BCs hold
  *exactly*, removing that loss term entirely and often accelerating convergence.
- **Residual adaptive refinement (RAR).** Add collocation points where the residual is
  largest (`dde.callbacks` / resampling) to resolve sharp features and moving fronts.
- **Non-dimensionalize first.** PINNs train far better when inputs/outputs are O(1); rescale
  the domain and solution (see the `dimensional-analysis` skill).
- **GPU.** Training is the bottleneck; use a GPU for 2D/3D or long training runs. There is
  no CFL/stability constraint — accuracy is limited by optimization and network capacity.

## When PINNs are the wrong tool

- Simple forward problems on rectangles/boxes — finite differences or spectral methods are
  faster and more accurate (see `classical-methods.md`).
- **Learned operator surrogates** that map inputs → solution and roll out in time (FNO,
  DeepONet) are a *different* paradigm (supervised on trajectory data, not residual
  minimization) — use the `autoregressive-neural-pde-solver` skill.
