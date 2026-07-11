# Chaos, Lyapunov Exponents & Poincaré Sections

Deterministic chaos = bounded, aperiodic motion with **exponential sensitivity to
initial conditions**. The quantitative fingerprint is a positive largest
Lyapunov exponent `λ_max`; the qualitative tool is the Poincaré section.
Running example: the Lorenz system.

```python
import numpy as np
from scipy.integrate import solve_ivp

def lorenz(t, y, sigma=10.0, rho=28.0, beta=8/3):
    x, y_, z = y
    return [sigma * (y_ - x), x * (rho - z) - y_, x * y_ - beta * z]
```

## Largest Lyapunov Exponent (Benettin variational method)

Evolve the state together with a tangent vector `δ` under the linearized flow
`dδ/dt = J(y) δ`. Periodically measure how much `δ` grew, accumulate the log, and
renormalize `δ` back to unit length so it never overflows. `λ_max` is the
long-time average growth rate. (Benettin et al. 1980; Wolf et al. 1985.)

```python
def largest_lyapunov(rhs, y0, t_total=200.0, dt_renorm=1.0, rtol=1e-10):
    y0 = np.asarray(y0, float)
    n = len(y0)

    def augmented(t, Y):                       # state + tangent vector
        y, delta = Y[:n], Y[n:]
        f0 = np.asarray(rhs(t, y), float)
        J = np.empty((n, n)); eps = 1e-8       # finite-difference Jacobian
        for j in range(n):
            yp = y.copy(); yp[j] += eps
            J[:, j] = (np.asarray(rhs(t, yp), float) - f0) / eps
        return np.concatenate([f0, J @ delta])

    rng = np.random.default_rng(0)
    delta = rng.standard_normal(n); delta /= np.linalg.norm(delta)
    Y = np.concatenate([y0, delta])

    n_steps = int(t_total / dt_renorm)
    lyap_sum, running = 0.0, []
    for i in range(n_steps):
        t0, t1 = i * dt_renorm, (i + 1) * dt_renorm
        sol = solve_ivp(augmented, (t0, t1), Y, method="RK45",
                        rtol=rtol, atol=rtol * 1e-2)
        Y = sol.y[:, -1]
        norm = np.linalg.norm(Y[n:])
        lyap_sum += np.log(norm)               # accumulate log-growth
        Y[n:] /= norm                          # renormalize the tangent vector
        running.append(lyap_sum / t1)          # convergence trace
    return lyap_sum / t_total, np.array(running)

lam, running = largest_lyapunov(lorenz, [1, 1, 1], t_total=200.0)
print(f"lambda_max = {lam:.4f}   (Lorenz reference ~ 0.906)")
```

- **Positive `λ_max`** (robust to `t_total`, initial condition, and tolerance) ⇒
  chaos. Near zero ⇒ quasi-periodic/periodic. Negative ⇒ a stable fixed point.
- Always plot `running`; trust the value only once it has flattened. If it is
  still drifting, `t_total` is too short — integrate for 10–100 **Lyapunov times**.
- **Discard the transient** before starting the average, or a slow approach to the
  attractor pollutes the estimate.

### Lyapunov time

`t_Lyap = 1 / λ_max` is the horizon over which nearby trajectories separate by a
factor of `e`. For Lorenz, `≈ 1.1` time units — prediction error grows ~10× every
`t_Lyap · ln 10 ≈ 2.5` units, which is why long-range forecasting of a chaotic
system is hopeless regardless of model accuracy.

## Full Lyapunov Spectrum (QR / Gram-Schmidt)

For the whole spectrum `λ_1 ≥ … ≥ λ_n`, evolve `n` orthonormal tangent vectors
(the columns of `Q`) and reorthonormalize with a QR decomposition at each step;
`λ_k` is the time-averaged `log` of the k-th diagonal of `R`.

```python
def lyapunov_spectrum(rhs, y0, t_total=1000.0, dt=0.5, rtol=1e-9):
    y0 = np.asarray(y0, float); n = len(y0)

    def augmented(t, Y):                       # state + n tangent vectors (flattened)
        y = Y[:n]; Q = Y[n:].reshape(n, n)
        f0 = np.asarray(rhs(t, y), float)
        J = np.empty((n, n)); eps = 1e-8
        for j in range(n):
            yp = y.copy(); yp[j] += eps
            J[:, j] = (np.asarray(rhs(t, yp), float) - f0) / eps
        return np.concatenate([f0, (J @ Q).ravel()])

    Q = np.eye(n)
    Y = np.concatenate([y0, Q.ravel()])
    sums = np.zeros(n)
    n_steps = int(t_total / dt)
    for _ in range(n_steps):
        sol = solve_ivp(augmented, (0, dt), Y, method="RK45", rtol=rtol, atol=rtol * 1e-2)
        Y = sol.y[:, -1]
        Q, R = np.linalg.qr(Y[n:].reshape(n, n))
        Q *= np.sign(np.diag(R))               # keep R's diagonal positive
        sums += np.log(np.abs(np.diag(R)))     # accumulate per-direction growth
        Y[n:] = Q.ravel()
    return sums / t_total
```

Sanity checks on the spectrum:
- A **continuous-time flow with a bounded attractor** has one exponent exactly
  **zero** (the flow direction). Your numerical `λ` closest to zero should be
  small — a coarse gauge of accuracy.
- Their **sum equals the average divergence** `⟨tr J⟩`. For Lorenz that is the
  constant `−(σ + 1 + β) = −13.67`, so `Σλ_k ≈ −13.67` — a strong correctness
  test. Lorenz's spectrum is `≈ (0.906, 0, −14.57)`.
- The **Kaplan-Yorke dimension** interpolates where the cumulative sum of
  exponents hits zero, estimating the attractor's fractal dimension.

## Poincaré Sections

Reduce a flow to a map by recording where the trajectory pierces a hyperplane
(e.g. `z = z*`) in one direction. Periodic orbit → finite set of points;
quasi-periodic → closed curve; chaos → fractal point cloud.

### Manual crossing detection (linear interpolation)

```python
def poincare_section(rhs, y0, t_total, section_var=2, section_val=None,
                     direction="positive"):
    sol = solve_ivp(rhs, (0, t_total), y0,
                    t_eval=np.linspace(0, t_total, int(t_total * 1000)),
                    rtol=1e-10, atol=1e-12)
    s = sol.y[section_var] - (np.mean(sol.y[section_var]) if section_val is None else section_val)
    crossings = []
    for i in range(1, len(s)):
        rising  = s[i-1] < 0 <= s[i]
        falling = s[i-1] >= 0 > s[i]
        if (direction == "positive" and rising) or (direction == "negative" and falling):
            frac = -s[i-1] / (s[i] - s[i-1])                       # linear-interp the crossing
            crossings.append(sol.y[:, i-1] + frac * (sol.y[:, i] - sol.y[:, i-1]))
    return np.array(crossings)
```

Accuracy is limited by the `t_eval` spacing between the two bracketing samples.

### Precise crossings with `solve_ivp` events (preferred)

`solve_ivp` roots each event function to solver tolerance — no interpolation
error. Set `event.direction` for a one-sided section; leave `terminal=False` to
collect every crossing in `sol.y_events`.

```python
def z_section(t, y, z_star=27.0):
    return y[2] - z_star
z_section.direction = 1        # only upward crossings

sol = solve_ivp(lorenz, (0, 500), [1, 1, 1], rtol=1e-10, atol=1e-12,
                dense_output=True, events=z_section)
crossings = sol.y_events[0]    # shape (n_crossings, 3)
```

## What Counts as Chaos

Positive `λ_max` alone is not proof — also require: (1) the motion is **bounded**
(rules out simple divergence), (2) it is **aperiodic** (a Poincaré section that is
neither a finite set nor a smooth closed curve), and (3) `λ_max > 0` is **robust**
to `t_total`, tolerance, and initial condition. For noisy experimental time series
where no model is available, use the **0-1 test for chaos** or Rosenstein's
algorithm to estimate `λ_max` from a delay-embedded reconstruction rather than the
variational method above.
