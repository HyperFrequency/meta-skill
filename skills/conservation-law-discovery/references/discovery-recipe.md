# Discovery Recipe — Runnable Code

End-to-end code for finding and validating conserved quantities from trajectory data. Uses
only NumPy, SciPy, and Matplotlib. Copy the pieces you need.

## 0. Generate or load a high-accuracy trajectory

Use tight integrator tolerances — see [pitfalls.md](pitfalls.md) for why this dominates
result quality. The Kepler two-body problem is a good testbed: it conserves energy `E`,
angular momentum `L`, and the (system-specific) Laplace–Runge–Lenz vector `A`.

```python
import numpy as np
from scipy.integrate import solve_ivp

def kepler(t, y):
    x, ypos, vx, vy = y
    r = np.sqrt(x**2 + ypos**2)
    return [vx, vy, -x / r**3, -ypos / r**3]

sol = solve_ivp(
    kepler, (0, 50), [1.0, 0.0, 0.0, 0.8],
    t_eval=np.linspace(0, 50, 5000), rtol=1e-12, atol=1e-14,
)
x, ypos, vx, vy = sol.y
dt = sol.t[1] - sol.t[0]
trajectory = np.column_stack([x, ypos, vx, vy])   # shape (T, n_vars)
```

## 1. Check known invariants and plot the drift

```python
import matplotlib.pyplot as plt

E = 0.5 * (vx**2 + vy**2) - 1.0 / np.sqrt(x**2 + ypos**2)   # energy
L = x * vy - ypos * vx                                       # angular momentum

# Laplace–Runge–Lenz magnitude (Kepler-specific extra invariant)
r = np.sqrt(x**2 + ypos**2)
A_x = vy * L - x / r
A_y = -vx * L - ypos / r
A_mag = np.sqrt(A_x**2 + A_y**2)

def relative_drift(values):
    """Dimensionless conservation quality; ≲ 1e-6 means well conserved."""
    return values.std() / (abs(values.mean()) + 1e-15)

for name, vals in [("E", E), ("L", L), ("|A| (LRL)", A_mag)]:
    print(f"{name:10s} relative drift = {relative_drift(vals):.2e}")

fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
for ax, (name, vals) in zip(axes, [(r"$\Delta E$", E), (r"$\Delta L$", L),
                                    (r"$\Delta |A|$", A_mag)]):
    ax.plot(sol.t, vals - vals[0], linewidth=0.6)
    ax.set_ylabel(name)
    ax.ticklabel_format(style="sci", axis="y", scilimits=(-3, 3))
    ax.grid(True, alpha=0.3)
axes[-1].set_xlabel("time")
plt.tight_layout()
plt.savefig("conservation_check.png", dpi=150, bbox_inches="tight")
```

Rising or oscillating drift above ~1e-6 usually means the *trajectory* is under-resolved,
not that the quantity is unconserved — tighten the integrator before concluding anything.

## 2. Polynomial null-space invariant finder

Build a monomial library `Φ(x)`, differentiate it in time, and read invariants off the
small singular values of `dΦ/dt`. A conserved `I = Φ·c` satisfies `(dΦ/dt)·c ≈ 0`, so `c`
is an (approximate) right null vector.

```python
from itertools import combinations_with_replacement

def poly_features(x, degree):
    """All monomials up to `degree`. Returns (Phi, names); index 0 is the constant '1'."""
    n = x.shape[0]
    features, names = [np.ones(n)], ["1"]
    n_vars = x.shape[1]
    for d in range(1, degree + 1):
        for combo in combinations_with_replacement(range(n_vars), d):
            feat = np.ones(n)
            parts = []
            for idx in combo:
                feat = feat * x[:, idx]
                parts.append(f"x{idx}")
            features.append(feat)
            names.append("*".join(parts))
    return np.column_stack(features), names


def find_polynomial_invariant(trajectory, dt, max_degree=2, trim=10,
                              tol_ratio=1e-6, vector_field=None):
    """
    Search for polynomial conserved quantities I(x) with dI/dt ≈ 0.

    trajectory   : (T, n_vars) array of states, uniformly sampled in time.
    dt           : sample spacing (used only for finite-difference derivatives).
    vector_field : optional f(X)->(T, n_vars); if given, derivatives are EXACT
                   (dPhi/dt = J_Phi · f) instead of finite-differenced. Strongly preferred.

    Returns list of (coeffs, I_values, relative_drift), best-conserved first, and `names`.
    """
    Phi, names = poly_features(trajectory, max_degree)

    if vector_field is not None:
        dPhi_dt = _exact_time_derivative(trajectory, max_degree, vector_field)
    else:
        dPhi_dt = np.gradient(Phi, dt, axis=0)

    # The constant column '1' has zero derivative -> a trivial null direction. Drop it here.
    Psi = dPhi_dt[trim:-trim, 1:]            # exclude constant, trim noisy edges
    U, S, Vt = np.linalg.svd(Psi, full_matrices=False)

    print("smallest singular values (0 = perfectly conserved):")
    for s in S[-min(8, len(S)):][::-1]:
        print(f"  {s:.3e}")

    tol = tol_ratio * S[0]
    n_conserved = max(1, int((S < tol).sum()))
    print(f"\n{n_conserved} candidate invariant(s) below tol = {tol:.2e}")

    results = []
    for i in range(n_conserved):
        c_reduced = Vt[-(i + 1)]                       # coeffs for non-constant features
        coeffs = np.concatenate([[0.0], c_reduced])    # re-insert constant slot (gauge)
        I_values = Phi @ coeffs
        drift = I_values.std() / (abs(I_values.mean()) + 1e-15)

        terms = [f"{c:+.4f}*{nm}" for c, nm in zip(coeffs, names) if abs(c) > 1e-6]
        expr = " ".join(terms[:10]) + (" + ..." if len(terms) > 10 else "")
        print(f"  invariant {i+1}: drift={drift:.2e}  I = {expr}")
        results.append((coeffs, I_values, drift))

    results.sort(key=lambda t: t[2])   # best-conserved first
    return results, names


results, names = find_polynomial_invariant(trajectory, dt, max_degree=2)
```

Notes:

- For Kepler, angular momentum `L = x·vy − y·vx` is polynomial (degree 2) and should
  surface directly; energy's `1/r` term is **not** polynomial, so `E` cannot appear in a
  pure monomial library — enrich it (see [methods.md](methods.md)) to recover `E` exactly.
- Recovered invariants span a *subspace*; different singular vectors may be linear
  combinations of the same underlying invariants. Orthogonalize and rank-check before
  claiming "k independent laws" — see [pitfalls.md](pitfalls.md).

## 3. Test a specific candidate function

```python
def test_conservation(trajectory, dt, candidate_func, name="I", trim=10, tol=1e-6):
    I = candidate_func(trajectory)
    dI_dt = np.gradient(I, dt)
    drift = I.std() / (abs(I.mean()) + 1e-15)
    print(f"{name}: mean={I.mean():.6f}  std={I.std():.2e}  "
          f"max|dI/dt|={np.abs(dI_dt[trim:-trim]).max():.2e}  "
          f"drift={drift:.2e}  conserved={'YES' if drift < tol else 'NO'}")
    return I, drift < tol

energy = lambda t: 0.5 * (t[:, 2]**2 + t[:, 3]**2) - 1.0 / np.sqrt(t[:, 0]**2 + t[:, 1]**2)
ang_mom = lambda t: t[:, 0] * t[:, 3] - t[:, 1] * t[:, 2]
test_conservation(trajectory, dt, energy, "energy")
test_conservation(trajectory, dt, ang_mom, "angular momentum")
```

## 4. Find GLOBAL invariants across many trajectories

The single most important upgrade. A quantity constant on one orbit may be a coincidence;
a genuine integral of motion is constant on *every* orbit. Integrate several initial
conditions, stack their feature/derivative matrices, and take one SVD over the pooled data.

```python
def multi_trajectory_invariants(initial_conditions, rhs, t_span, n_pts,
                                max_degree=2, trim=10):
    all_Phi, all_dPhi = [], []
    for y0 in initial_conditions:
        s = solve_ivp(rhs, t_span, y0, t_eval=np.linspace(*t_span, n_pts),
                      rtol=1e-12, atol=1e-14)
        traj = s.y.T
        Phi, names = poly_features(traj, max_degree)
        dPhi = np.gradient(Phi, s.t[1] - s.t[0], axis=0)
        all_Phi.append(Phi[trim:-trim])
        all_dPhi.append(dPhi[trim:-trim, 1:])   # drop constant column
    Psi = np.vstack(all_dPhi)
    U, S, Vt = np.linalg.svd(Psi, full_matrices=False)
    return S, Vt, names   # small S values -> invariants valid across ALL trajectories

ics = [[1.0, 0.0, 0.0, 0.8], [1.0, 0.0, 0.0, 0.9], [1.5, 0.0, 0.0, 0.6]]
S, Vt, names = multi_trajectory_invariants(ics, kepler, (0, 50), 5000)
```

## 5. Exact time derivatives from a known vector field

When you know `f` (`dx/dt = f(x)`), skip finite differences entirely. For monomials the
chain rule is `d(x_a·x_b·…)/dt = Σ_i (∂/∂x_i)(monomial)·f_i(x)`. Implement `_exact_time_derivative`
symbolically (e.g. with SymPy to differentiate each monomial once, then lambdify) or
analytically for low degrees. This is the highest-precision path and removes edge-trim
artifacts. See [pitfalls.md](pitfalls.md#derivative-noise) for the trade-off.
