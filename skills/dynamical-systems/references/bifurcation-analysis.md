# Bifurcation Analysis

A **bifurcation** is a qualitative change in the phase portrait as a parameter
`p` crosses a critical value — an equilibrium appearing/vanishing, swapping
stability, or giving birth to a limit cycle. Two practical tools: brute-force
iteration for maps, and natural-parameter continuation for flows.

## Bifurcation Diagram of an Iterated Map

For a map `x_{n+1} = g(x_n; r)`, iterate at each `r`, discard the transient, and
plot the surviving attractor. The logistic map `x_{n+1} = r x_n (1 - x_n)` is the
canonical period-doubling-to-chaos example.

```python
import numpy as np
import matplotlib.pyplot as plt

def logistic_bifurcation(r_values, n_discard=500, n_plot=200, x0=0.5):
    R, X = [], []
    for r in r_values:
        x = x0
        for _ in range(n_discard):          # settle onto the attractor
            x = r * x * (1 - x)
        for _ in range(n_plot):             # record the attractor's points
            x = r * x * (1 - x)
            R.append(r); X.append(x)
    return np.array(R), np.array(X)

r_values = np.linspace(2.5, 4.0, 2000)
R, X = logistic_bifurcation(r_values)

fig, ax = plt.subplots(figsize=(12, 7))
ax.scatter(R, X, s=0.01, c="black", alpha=0.5)
ax.set_xlabel("r"); ax.set_ylabel("x*")
ax.set_title("Logistic map bifurcation diagram")
plt.savefig("bifurcation.png", dpi=200, bbox_inches="tight")
```

Reading it: a single curve = stable fixed point; a fork into 2, 4, 8 branches =
period-doubling cascade; the smear near `r ≈ 3.57+` = chaos, punctuated by
periodic windows (the wide period-3 window near `r ≈ 3.83` is Sarkovskii's
"period three implies chaos").

The successive doubling thresholds `r_n` converge geometrically at the
**Feigenbaum constant** `δ ≈ 4.669`, `(r_n - r_{n-1})/(r_{n+1} - r_n) → δ` — a
universal check that your cascade is resolved correctly.

## Continuation of Flow Equilibria

For a continuous system `dy/dt = f(y; p)`, track an equilibrium branch by solving
`f(y; p) = 0` at each `p`, reusing the previous solution as the next initial
guess (natural-parameter continuation). Record stability at each step.

```python
from scipy.optimize import fsolve

def continue_equilibria(rhs, param_values, y_init):
    """rhs(y, p) -> list. Returns (equilibria, is_stable) arrays aligned to param_values."""
    equilibria, is_stable = [], []
    guess = np.asarray(y_init, float)
    ndim = len(guess)
    for p in param_values:
        root, info, ier, _ = fsolve(lambda y: rhs(y, p), guess, full_output=True)
        if ier == 1 and np.linalg.norm(info["fvec"]) < 1e-8:
            guess = root                                   # warm-start next step
            J = np.empty((ndim, ndim))                     # finite-difference Jacobian
            f0, eps = np.asarray(rhs(root, p), float), 1e-8
            for j in range(ndim):
                yp = root.copy(); yp[j] += eps
                J[:, j] = (np.asarray(rhs(yp, p), float) - f0) / eps
            equilibria.append(root)
            is_stable.append(bool(np.all(np.linalg.eigvals(J).real < 0)))
        else:                                              # branch lost / turned around
            equilibria.append(np.full(ndim, np.nan))
            is_stable.append(False)
    return np.array(equilibria), np.array(is_stable)
```

Plot each branch, drawing stable segments solid and unstable segments dashed; the
`p` where `is_stable` flips is a bifurcation.

**Limitation.** Natural-parameter continuation cannot get past a fold (saddle-node)
where the branch turns back on itself, and it will not find disconnected
branches. When you hit that wall, switch to **pseudo-arclength continuation** —
parametrize the branch by arclength instead of `p` so folds are just smooth
points — or use a dedicated package: **PyDSTool**, **MatCont**, or **AUTO-07p**,
which also track fold/Hopf curves in two parameters.

## Identifying the Bifurcation Type

Watch how the Jacobian eigenvalues move as `p` crosses the critical value.

| Bifurcation | What happens | Eigenvalue signature |
|---|---|---|
| Saddle-node (fold) | Two equilibria collide and annihilate | One **real** eigenvalue crosses 0; branch folds |
| Transcritical | Two equilibria exchange stability, both persist | One real eigenvalue crosses 0; branches cross |
| Pitchfork | A symmetric equilibrium splits into two (needs symmetry) | One real eigenvalue crosses 0 |
| Hopf | Equilibrium spawns a limit cycle | A **complex** pair crosses the imaginary axis (`Re → 0⁺`) |
| Period-doubling (flip) | A limit cycle's period doubles | A **Floquet multiplier** of the cycle crosses `−1` |

Practical detection:
- **Zero-crossing bifurcations** (fold/transcritical/pitchfork): monitor
  `min |Re(λ)|` along the branch and flag where the sign of the smallest real
  eigenvalue changes.
- **Hopf**: track the complex pair with largest real part; a Hopf point is where
  its real part changes sign while its imaginary part is nonzero. The emergent
  cycle's amplitude grows like `sqrt(p - p_c)` (supercritical) near onset.
- **Period-doubling** requires **Floquet multipliers** of a periodic orbit, not
  equilibrium eigenvalues — integrate the monodromy (variational) matrix over one
  period `T` and take the eigenvalues of `Φ(T)`. This is a limit-cycle
  computation, not an equilibrium one; see the Lyapunov reference for the
  variational-equation machinery you reuse here.

Distinguishing pitchfork from transcritical requires knowing the system's
symmetry — pitchforks live in systems with a `y → −y` (or similar) invariance.
