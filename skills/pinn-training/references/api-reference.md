# DeepXDE API Reference (PINN Essentials)

The building blocks you assemble into a PINN, grouped by role. Signatures reflect
DeepXDE 1.x; the library evolves, so confirm exact keyword names against the
installed version when something errors. Import as `import deepxde as dde`.

---

## Geometry (`dde.geometry`)

Define the spatial domain. Collocation points are sampled inside it.

| Constructor | Domain |
|---|---|
| `Interval(a, b)` | 1D segment `[a, b]` |
| `Rectangle(xmin, xmax)` — e.g. `Rectangle([x0,y0], [x1,y1])` | 2D axis-aligned box |
| `Disk(center, radius)` | 2D disk |
| `Polygon(vertices)` | 2D polygon |
| `Cuboid([x0,y0,z0], [x1,y1,z1])` | 3D box |
| `Sphere(center, radius)` | 3D ball |

Compose geometries with `CSGUnion`, `CSGDifference`, `CSGIntersection` for
complex shapes.

### Time

- `TimeDomain(t0, t1)` — the temporal interval.
- `GeometryXTime(geom, timedomain)` — space-time domain. The last input column is
  time; earlier columns are space. In residuals, use `j=<time index>` in
  `jacobian` for time derivatives.

---

## Constraints (`dde.icbc`)

Each becomes a loss term. Most take `(geom_or_geomtime, func, on_boundary/on_initial)`.

| Class | Enforces |
|---|---|
| `DirichletBC(geom, func, on_boundary)` | `u = func` on the boundary |
| `NeumannBC(geom, func, on_boundary)` | normal derivative `du/dn = func` |
| `RobinBC(geom, func, on_boundary)` | `du/dn = func(x, u)` |
| `PeriodicBC(geom, component, on_boundary)` | periodicity in a coordinate |
| `OperatorBC(geom, func, on_boundary)` | arbitrary differential operator = 0 |
| `IC(geomtime, func, on_initial)` | initial condition at `t = t0` |
| `PointSetBC(points, values, component=0)` | data fit at explicit points (inverse problems / data assimilation) |

The `on_boundary` / `on_initial` selector receives `(x, flag)` and returns a
boolean array; use it to apply a BC only on part of the boundary, e.g.
`lambda x, on_b: on_b and np.isclose(x[0], 0)`.

---

## Data objects (`dde.data`)

Bundle geometry + residual + constraints and control sampling.

- `dde.data.PDE(geom, pde, bcs, num_domain, num_boundary, num_test=..., ...)`
  — steady / time-independent problems.
- `dde.data.TimePDE(geomtime, pde, ic_bcs, num_domain, num_boundary, num_initial, num_test=..., ...)`
  — time-dependent problems.

Key sampling arguments:
- `num_domain` — interior collocation points (residual is enforced here).
- `num_boundary` — points on the boundary.
- `num_initial` — points at `t = t0` (TimePDE only).
- `num_test` — held-out points for reported test loss.
- `train_distribution` — e.g. `"Hammersley"`, `"uniform"`, `"pseudo"`,
  `"sobol"`; low-discrepancy sequences often help.
- `anchors` — a fixed array of points always included.

---

## The residual function

You write `pde(x, u)` returning the residual (or a list of residuals for
coupled systems). Derivatives come from automatic differentiation:

- `dde.grad.jacobian(u, x, i=0, j=k)` — `d u_i / d x_k` (first derivative).
- `dde.grad.hessian(u, x, component=0, i=k, j=l)` — `d^2 u_component / (d x_k d x_l)`;
  `component` selects the output, `i`/`j` are the coordinate indices. Equal indices
  give a pure second derivative like `u_xx` (e.g. `hessian(u, x, i=0, j=0)`).

Convention: `x[:, k:k+1]` slices coordinate `k`; keep the trailing dimension.
For a system with multiple outputs, select the output component with `i`.

---

## Networks (`dde.nn`)

| Constructor | Use |
|---|---|
| `FNN(layer_sizes, activation, initializer)` | standard fully-connected net |
| `PFNN(layer_sizes, activation, initializer)` | parallel sub-nets per output (coupled systems) |
| `DeepONet(...)` / `DeepONetCartesianProd(...)` | operator learning (map functions to functions) |

- `layer_sizes` — e.g. `[2] + [64]*4 + [1]` means 2 inputs, four hidden layers of
  width 64, 1 output.
- `activation` — `"tanh"` is the default choice; `"sin"` helps high-frequency
  solutions; avoid `"relu"` (non-smooth second derivatives break the residual).
- `initializer` — typically `"Glorot uniform"` / `"Glorot normal"`.
- `net.apply_output_transform(fn)` — post-process outputs (hard BCs, scaling).
- `net.apply_feature_transform(fn)` — pre-process inputs (normalization, Fourier
  features).

---

## Model (`dde.Model`)

```python
model = dde.Model(data, net)
model.compile(optimizer, lr=..., loss_weights=..., metrics=..., external_trainable_variables=...)
model.train(iterations=..., display_every=..., callbacks=..., model_save_path=...)
pred = model.predict(X, operator=None)   # operator lets you predict derivatives / residuals
```

- `optimizer` — `"adam"` (specify `lr`), `"L-BFGS"` / `"L-BFGS-B"` (second-order,
  no `lr`), or an SGD variant.
- `loss_weights` — one weight per loss term, ordered `[pde, *bcs]`. Raise the
  BC/IC weights when those losses dominate or lag (see troubleshooting).
- `external_trainable_variables` — the `dde.Variable`s to optimize in inverse
  problems; must be passed on every `compile` call.
- `metrics` — e.g. `["l2 relative error"]` when an exact solution is supplied.

`model.train` historically used `epochs=`; newer versions prefer `iterations=`
(both work, `epochs` warns). Two-stage training: `compile("adam")` + `train`,
then `compile("L-BFGS")` + `train()` with no iteration count (runs to
convergence).

---

## Inverse-problem variables

- `dde.Variable(initial_value)` — a trainable scalar embedded in the residual.
- `dde.callbacks.VariableValue(var, period=N, filename=...)` — logs the value
  every `N` iterations so you can watch it converge.

---

## Callbacks (`dde.callbacks`)

| Callback | Purpose |
|---|---|
| `ModelCheckpoint(filepath, save_better_only=True, period=N)` | periodic checkpoints |
| `EarlyStopping(min_delta, patience)` | stop when loss plateaus |
| `VariableValue(var, period)` | track inverse variables |
| `PDEPointResampler(period)` | resample collocation points during training (adaptive) |

---

## Save & plot

- `dde.saveplot(losshistory, train_state, issave=True, isplot=True)` — dump loss
  curves and a solution plot from the objects returned by `train`.
- `model.save(path)` / `model.restore(path)` — persist and reload weights.

For custom figures (fields, error maps, slices), export predictions with
`model.predict` and plot with the `matplotlib` or `scientific-visualization`
skills.

---

## Backend caveats

`export DDE_BACKEND=` selects `tensorflow`, `tensorflow.compat.v1`, `pytorch`,
`jax`, or `paddle`. Not every feature exists on every backend (L-BFGS behaviour,
`Variable.numpy()`, some transforms differ). PyTorch is the best-supported path
to GPU training; TensorFlow 1.x compat mode is the oldest and most feature-
complete for legacy examples. Pick one and keep it fixed across a project.
