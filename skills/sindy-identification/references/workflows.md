# SINDy Workflows and Recipes

Copy-paste recipes that extend the core workflow in `SKILL.md`. All assume
`import numpy as np`, `import pysindy as ps`, and a training array `x_train` of
shape `(n_samples, n_features)` on a uniform grid with timestep `dt`.

## 1. Threshold sweep (choose sparsity honestly)

Never hand-pick a single threshold. Sweep it, then read the trade-off between
model complexity (term count) and simulation error. Pick the threshold at the
"elbow": the largest value before simulation error starts climbing.

```python
t_train = np.arange(0, x_train.shape[0] * dt, dt)
for thresh in [0.001, 0.01, 0.05, 0.1, 0.5, 1.0]:
    model = ps.SINDy(
        feature_library=ps.PolynomialLibrary(degree=2),
        optimizer=ps.STLSQ(threshold=thresh),
    )
    model.fit(x_train, t=dt)
    x_sim = model.simulate(x_train[0], t_train)
    rmse = np.sqrt(np.mean((x_sim - x_train) ** 2))
    print(f"threshold={thresh:<6} terms={model.complexity:<3} RMSE={rmse:.4f}")
```

If `simulate` raises or returns NaNs at some thresholds, the discovered model is
unstable there — treat that as disqualifying, not as a low error.

## 2. Custom and combined libraries

Add libraries with `+` to concatenate their terms. Build a `CustomLibrary` for
nonlinearities not covered by polynomials or Fourier terms.

```python
# Polynomials plus three Fourier harmonics for a mixed oscillatory system
library = ps.PolynomialLibrary(degree=2) + ps.FourierLibrary(n_frequencies=3)

# Fully custom nonlinear terms — functions and their string formatters must align
custom = ps.CustomLibrary(
    library_functions=[
        lambda x: x,
        lambda x: x ** 2,
        lambda x: np.sin(x),
        lambda x: np.cos(x),
    ],
    function_names=[
        lambda x: x,
        lambda x: f"{x}^2",
        lambda x: f"sin({x})",
        lambda x: f"cos({x})",
    ],
)

model = ps.SINDy(feature_library=custom, optimizer=ps.STLSQ(threshold=0.1))
model.fit(x_train, t=dt)
model.print()
```

## 3. Noisy data (smoothed differentiation)

Real measurements corrupt the derivative estimate. Use a denoising
differentiation method and a higher threshold to reject spurious terms.

```python
x_noisy = x_train + 0.1 * np.random.randn(*x_train.shape)

model = ps.SINDy(
    differentiation_method=ps.SmoothedFiniteDifference(),
    feature_library=ps.PolynomialLibrary(degree=2),
    optimizer=ps.STLSQ(threshold=0.2),   # raise threshold under noise
)
model.fit(x_noisy, t=dt)
model.print()
```

For heavier noise, use `ps.SINDyDerivative` (total-variation / spline kinds) or
the weak formulation described in `references/advanced.md`.

## 4. Forced systems (control inputs)

If the system is driven by an external input `u(t)` — e.g. a controlled
actuator — discover `dx/dt = f(x, u)` by passing `u` to `fit` and `simulate`.

```python
# u_train: shape (n_samples, n_controls); u_fun: callable u(t) for simulation
model = ps.SINDy(feature_library=ps.PolynomialLibrary(degree=2),
                 optimizer=ps.STLSQ(threshold=0.1))
model.fit(x_train, t=dt, u=u_train)
model.print()

x_sim = model.simulate(x_train[0], t_train, u=u_fun)  # u_fun(t) -> control vector
```

## 5. Validation plot (model vs. ground truth)

```python
import matplotlib.pyplot as plt

x_sim = model.simulate(x_train[0], t_train)
labels = ["x", "y", "z"]
fig, axes = plt.subplots(len(labels), 1, figsize=(10, 8), sharex=True)
for i, ax in enumerate(axes):
    ax.plot(t_train, x_train[:, i], "b-", lw=0.6, label="ground truth")
    ax.plot(t_train, x_sim[:, i], "r--", lw=0.6, label="SINDy")
    ax.set_ylabel(labels[i]); ax.legend(loc="upper right"); ax.grid(alpha=0.3)
axes[-1].set_xlabel("time [s]"); axes[0].set_title("SINDy vs ground truth")
plt.tight_layout(); plt.savefig("sindy_validation.png", dpi=150)

rmse = np.sqrt(np.mean((x_sim - x_train) ** 2, axis=0))
print("per-variable RMSE:", rmse)
```

## 6. Coefficient extraction (build the equation table yourself)

```python
coeffs = model.coefficients()            # (n_equations, n_library_terms)
names = model.get_feature_names()
for i, lhs in enumerate(["dx/dt", "dy/dt", "dz/dt"]):
    terms = [f"{coeffs[i, j]:+.3f}*{names[j]}"
             for j in range(len(names)) if abs(coeffs[i, j]) > 1e-10]
    print(f"{lhs} = {' '.join(terms)}")
```

## 7. Multiple trajectories

Fit across several runs with different initial conditions for better coverage of
state space:

```python
# trajectories: list of arrays, each (n_samples_i, n_features)
model.fit(trajectories, t=dt, multiple_trajectories=True)
```
