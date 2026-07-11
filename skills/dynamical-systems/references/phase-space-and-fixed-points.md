# Phase Space & Fixed Points

Draw the flow, locate every equilibrium, and classify each one from its
linearization. Running example: the Van der Pol oscillator
`x'' - mu(1 - x^2)x' + x = 0`, written as the first-order system
`x' = v`, `v' = mu(1 - x^2)v - x`.

## Phase Portrait (2D)

Overlay the vector field (streamlines) with a handful of trajectories launched
from different initial conditions so limit cycles and basins are visible.

```python
import numpy as np
import matplotlib.pyplot as plt
from scipy.integrate import solve_ivp

mu = 1.0

def system(t, y):
    x, v = y
    return [v, mu * (1 - x**2) * v - x]

# Vector field on a grid (U, W are the component velocities)
x_range = np.linspace(-4, 4, 25)
v_range = np.linspace(-6, 6, 25)
X, V = np.meshgrid(x_range, v_range)
U = V
W = mu * (1 - X**2) * V - X

fig, ax = plt.subplots(figsize=(10, 8))
ax.streamplot(X, V, U, W, density=1.5, color="gray", linewidth=0.5, arrowsize=1)

# Sample orbits from several initial conditions
initial_conditions = [[0.1, 0], [3, 0], [0, 4], [-2, -3], [1, -5], [4, 4]]
colors = plt.cm.viridis(np.linspace(0, 1, len(initial_conditions)))
for ic, color in zip(initial_conditions, colors):
    sol = solve_ivp(system, (0, 30), ic, t_eval=np.linspace(0, 30, 3000),
                    rtol=1e-10, atol=1e-12)
    ax.plot(sol.y[0], sol.y[1], color=color, linewidth=1.2)
    ax.plot(*ic, "o", color=color, markersize=6)

ax.plot(0, 0, "rx", markersize=12, markeredgewidth=3, label="unstable fixed point")
ax.set_xlabel("x"); ax.set_ylabel("dx/dt")
ax.set_title(f"Van der Pol phase portrait (mu={mu})")
ax.legend(); ax.grid(True, alpha=0.3)
plt.savefig("phase_portrait.png", dpi=150, bbox_inches="tight")
```

Notes:
- `streamplot` auto-normalizes arrow spacing, so wildly varying field magnitude
  does not swamp the plot. If you use `quiver` instead, normalize the arrows
  (`U/np.hypot(U,W)`) or they will be unreadable.
- All orbits collapsing onto a single closed loop is the signature of a **limit
  cycle** (Van der Pol has exactly one, stable, for `mu > 0`).

### 3D systems

For a 3D flow (Lorenz, Rossler) integrate one long trajectory and plot it with
`ax = fig.add_subplot(projection="3d")`. A single well-resolved orbit reveals the
attractor's geometry; a grid of streamlines is impractical in 3D.

## Finding Fixed Points

Equilibria solve `f(y*) = 0`. `fsolve` returns the root nearest its initial
guess, so seed it from a grid and deduplicate to find them all.

```python
from scipy.optimize import fsolve

def rhs(y):                     # time-independent RHS: f(y)
    x, v = y
    return [v, mu * (1 - x**2) * v - x]

def find_all_equilibria(rhs, ndim, span=(-5, 5), n=7, tol=1e-6):
    guesses = np.array(np.meshgrid(*[np.linspace(*span, n)] * ndim)).reshape(ndim, -1).T
    found = []
    for g in guesses:
        root, info, ier, _ = fsolve(rhs, g, full_output=True)
        if ier == 1 and np.linalg.norm(info["fvec"]) < tol:     # converged AND residual small
            if not any(np.allclose(root, e, atol=1e-5) for e in found):
                found.append(root)
    return found

equilibria = find_all_equilibria(rhs, ndim=2)   # -> [array([0., 0.])]
```

Always check the residual (`info["fvec"]`): `ier == 1` alone can report a
non-root as "converged" on a flat region.

## The Jacobian

Stability comes from the eigenvalues of `J_ij = df_i/dy_j` at the equilibrium.
Prefer an **analytic** Jacobian when you can derive it; fall back to finite
differences otherwise.

```python
def jacobian_analytic(y):
    x, v = y
    return np.array([[0.0, 1.0],
                     [-2 * mu * x * v - 1.0, mu * (1 - x**2)]])

def jacobian_numeric(rhs, y, eps=1e-8):
    y = np.asarray(y, float)
    f0 = np.asarray(rhs(y), float)
    J = np.empty((len(y), len(y)))
    for j in range(len(y)):
        yp = y.copy(); yp[j] += eps
        J[:, j] = (np.asarray(rhs(yp), float) - f0) / eps      # forward difference
    return J
```

Forward differences with `eps≈1e-8` are usually fine; if the system is
ill-scaled, use central differences (`(f(y+eps)-f(y-eps))/(2*eps)`) or scale
`eps` per component.

## Classifying an Equilibrium (2D)

```python
def classify_fixed_point(eigenvalues, imag_tol=1e-10):
    re, im = eigenvalues.real, eigenvalues.imag
    if np.all(np.abs(im) < imag_tol):           # real spectrum
        if np.all(re < 0):  return "stable node"
        if np.all(re > 0):  return "unstable node"
        return "saddle point"
    if np.all(re < 0):      return "stable spiral"
    if np.all(re > 0):      return "unstable spiral"
    if np.all(np.abs(re) < imag_tol): return "center (linear)"
    return "saddle-focus / mixed"

J = jacobian_analytic(equilibria[0])
print(classify_fixed_point(np.linalg.eigvals(J)))   # -> unstable spiral (mu=1)
```

### 2D classification table

| Eigenvalues | Type | Behavior |
|---|---|---|
| `λ₁ < λ₂ < 0` (real) | Stable node | All nearby orbits approach the FP |
| `0 < λ₁ < λ₂` (real) | Unstable node | All nearby orbits leave the FP |
| `λ₁ < 0 < λ₂` (real) | Saddle | Attracted along one eigendirection, repelled along the other |
| `α ± iβ`, `α < 0` | Stable spiral | Spirals inward |
| `α ± iβ`, `α > 0` | Unstable spiral | Spirals outward |
| `±iβ` (pure imaginary) | Center | Closed orbits — **only guaranteed in conservative systems** |

For `n > 2` the same rule generalizes: the equilibrium is (locally) stable iff
**every** eigenvalue has negative real part; any eigenvalue with positive real
part makes it unstable; a zero real part is marginal and needs nonlinear
analysis (center-manifold reduction). A **saddle-focus** — one real and a complex
pair of opposite stability sign — is the organizing center of Shilnikov chaos.

## Caveats

- Linearization is silent when any `Re(λ) = 0` (non-hyperbolic FP). The "center"
  verdict is a *linear* statement; verify closed orbits with a conserved quantity
  (`conservation-law-discovery`) or by direct integration.
- A stable equilibrium is only **locally** stable. It says nothing about the
  basin of attraction or coexisting attractors — the phase portrait does.
