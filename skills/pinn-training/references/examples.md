# PINN Worked Examples (DeepXDE)

Complete, runnable programs. Each follows the same six-step pipeline: geometry →
residual → constraints → data → network → compile/train. They assume a backend
is installed and selected (`export DDE_BACKEND=pytorch`).

---

## 1. Forward: 1D Heat Equation

Solve `u_t = alpha * u_xx` on `x in [0,1]`, `t in [0,1]` with `u(0,t)=u(1,t)=0`
and `u(x,0)=sin(pi x)`. The analytic solution is
`u = sin(pi x) exp(-alpha pi^2 t)`, so we can measure the error.

```python
import deepxde as dde
import numpy as np

alpha = 0.01  # thermal diffusivity

def pde(x, u):
    # x[:, 0:1] is space, x[:, 1:2] is time
    u_t  = dde.grad.jacobian(u, x, i=0, j=1)   # du/dt
    u_xx = dde.grad.hessian(u, x, i=0, j=0)    # d2u/dx2
    return u_t - alpha * u_xx

geom       = dde.geometry.Interval(0, 1)
timedomain = dde.geometry.TimeDomain(0, 1)
geomtime   = dde.geometry.GeometryXTime(geom, timedomain)

bc = dde.icbc.DirichletBC(geomtime, lambda x: 0, lambda x, on_boundary: on_boundary)
ic = dde.icbc.IC(geomtime, lambda x: np.sin(np.pi * x[:, 0:1]),
                 lambda x, on_initial: on_initial)

data = dde.data.TimePDE(geomtime, pde, [bc, ic],
                        num_domain=2000, num_boundary=100,
                        num_initial=100, num_test=500)

net   = dde.nn.FNN([2] + [64] * 3 + [1], "tanh", "Glorot uniform")
model = dde.Model(data, net)

model.compile("adam", lr=1e-3)
model.train(iterations=10000, display_every=2000)
model.compile("L-BFGS")
model.train()

# Evaluate against the exact solution
x_test = np.linspace(0, 1, 100)
for t_val in [0.1, 0.3, 0.5, 0.8]:
    X = np.column_stack([x_test, np.full_like(x_test, t_val)])
    u_pred  = model.predict(X).flatten()
    u_exact = np.sin(np.pi * x_test) * np.exp(-alpha * np.pi**2 * t_val)
    print(f"t={t_val:.1f}: max error = {np.max(np.abs(u_pred - u_exact)):.4e}")
```

---

## 2. Inverse: Discover an Unknown Diffusion Coefficient

Given noisy measurements of `u(x,t)`, recover the true `alpha`. The unknown
becomes a `dde.Variable`; a `PointSetBC` supplies the data; the variable is
passed to the optimizer via `external_trainable_variables`.

```python
import deepxde as dde
import numpy as np

geom       = dde.geometry.Interval(0, 1)
timedomain = dde.geometry.TimeDomain(0, 1)
geomtime   = dde.geometry.GeometryXTime(geom, timedomain)

alpha_var = dde.Variable(0.05)   # initial guess; true value is 0.01

def pde_inverse(x, u):
    u_t  = dde.grad.jacobian(u, x, i=0, j=1)
    u_xx = dde.grad.hessian(u, x, i=0, j=0)
    return u_t - alpha_var * u_xx

# Synthetic noisy observations
def generate_data(n_obs=50):
    x_obs = np.random.rand(n_obs, 1)
    t_obs = np.random.rand(n_obs, 1) * 0.5
    u_obs = np.sin(np.pi * x_obs) * np.exp(-0.01 * np.pi**2 * t_obs)
    u_obs += 0.01 * np.random.randn(n_obs, 1)   # measurement noise
    return np.hstack([x_obs, t_obs]), u_obs

observe_x, observe_u = generate_data()
observe_bc = dde.icbc.PointSetBC(observe_x, observe_u)

bc = dde.icbc.DirichletBC(geomtime, lambda x: 0, lambda x, on_boundary: on_boundary)
ic = dde.icbc.IC(geomtime, lambda x: np.sin(np.pi * x[:, 0:1]),
                 lambda x, on_initial: on_initial)

data = dde.data.TimePDE(geomtime, pde_inverse, [bc, ic, observe_bc],
                        num_domain=2000, num_boundary=100, num_initial=100)

net   = dde.nn.FNN([2] + [64] * 3 + [1], "tanh", "Glorot uniform")
model = dde.Model(data, net)

# Track the recovered coefficient during training
tracker = dde.callbacks.VariableValue(alpha_var, period=1000)

model.compile("adam", lr=1e-3, external_trainable_variables=[alpha_var])
model.train(iterations=20000, display_every=5000, callbacks=[tracker])
model.compile("L-BFGS", external_trainable_variables=[alpha_var])
model.train()

print(f"Discovered alpha = {alpha_var.numpy():.6f}  (true: 0.010000)")
```

Notes:
- More observation points and a reasonable initial guess make inverse problems
  converge far more reliably.
- `alpha_var.numpy()` works on the PyTorch/TF backends; on JAX read the value via
  the tracked callback history.

---

## 3. Forward: 2D Poisson Equation

Steady-state (no time domain) `u_xx + u_yy = f` on the unit square, with a
manufactured source so `u = sin(pi x) sin(pi y)`.

```python
import deepxde as dde
import numpy as np

def pde_poisson(x, u):
    u_xx = dde.grad.hessian(u, x, i=0, j=0)
    u_yy = dde.grad.hessian(u, x, i=1, j=1)
    f = -2 * np.pi**2 * np.sin(np.pi * x[:, 0:1]) * np.sin(np.pi * x[:, 1:2])
    return u_xx + u_yy - f

geom = dde.geometry.Rectangle([0, 0], [1, 1])
bc   = dde.icbc.DirichletBC(geom, lambda x: 0, lambda x, on_boundary: on_boundary)

data  = dde.data.PDE(geom, pde_poisson, [bc], num_domain=2000, num_boundary=200)
net   = dde.nn.FNN([2] + [64] * 4 + [1], "tanh", "Glorot uniform")
model = dde.Model(data, net)

model.compile("adam", lr=1e-3)
model.train(iterations=15000)
model.compile("L-BFGS")
model.train()
```

Use `dde.data.PDE` for time-independent problems and `dde.data.TimePDE` when a
`TimeDomain` is involved.

---

## 4. Hard-Constraint Boundaries via Output Transform

Instead of penalising a Dirichlet BC in the loss, you can bake it into the
network so it is satisfied *exactly*. For `u(0)=u(1)=0`, multiply the raw network
output by `x(1-x)`:

```python
net.apply_output_transform(lambda x, u: x[:, 0:1] * (1 - x[:, 0:1]) * u)
```

This removes the boundary loss term entirely, which often speeds convergence and
improves accuracy. Design the multiplier so it vanishes exactly where the BC must
hold. `apply_feature_transform` similarly rescales/encodes inputs (e.g. Fourier
features) before the first layer. See `training-and-troubleshooting.md` for when
hard constraints help.
