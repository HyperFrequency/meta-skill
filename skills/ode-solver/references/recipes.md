# ODE Solver — Recipes

Runnable, copy-paste examples for each capability. All use
`scipy.integrate`, `numpy`, and (for plots) `matplotlib`.

```python
import numpy as np
from scipy.integrate import solve_ivp, solve_bvp
import matplotlib.pyplot as plt
```

---

## Recipe 1 — Basic IVP

Solve `dy/dt = f(t, y)`. The right-hand side returns the derivative of every
state component.

```python
def harmonic_oscillator(t, y, omega=2.0):
    """x'' + omega^2 x = 0, written as a first-order system."""
    x, v = y
    return [v, -omega**2 * x]

t_span = (0.0, 10.0)
y0 = [1.0, 0.0]                       # x(0)=1, v(0)=0
sol = solve_ivp(
    harmonic_oscillator, t_span, y0,
    method="RK45",
    t_eval=np.linspace(*t_span, 1000),  # output grid, not the internal steps
    rtol=1e-10, atol=1e-12,
)
assert sol.success, sol.message

plt.plot(sol.t, sol.y[0], label="x(t)")
plt.plot(sol.t, sol.y[1], label="v(t)")
plt.xlabel("Time [s]"); plt.ylabel("State"); plt.legend()
plt.grid(True, alpha=0.3)
plt.savefig("harmonic_oscillator.png", dpi=150, bbox_inches="tight")
```

Result fields: `sol.t` (times), `sol.y` shape `(n_states, n_times)`,
`sol.success`, `sol.message`, `sol.nfev` (rhs evaluations).

---

## Recipe 2 — Stiff system

The Van der Pol oscillator becomes stiff at large `mu`. An explicit solver
would take a huge number of steps; use an implicit one.

```python
def van_der_pol(t, y):
    mu = 1000.0                       # stiffness parameter
    x, v = y
    return [v, mu * (1 - x**2) * v - x]

sol = solve_ivp(
    van_der_pol, (0.0, 3000.0), [2.0, 0.0],
    method="Radau",                   # or "BDF"; "LSODA" to auto-detect
    rtol=1e-8, atol=1e-10,
    max_step=10.0,
)
assert sol.success, sol.message
```

Providing an analytic Jacobian accelerates `Radau`/`BDF`:

```python
def van_der_pol_jac(t, y):
    mu = 1000.0
    x, v = y
    return [[0.0, 1.0],
            [-2 * mu * x * v - 1.0, mu * (1 - x**2)]]

sol = solve_ivp(van_der_pol, (0, 3000), [2.0, 0.0],
                method="BDF", jac=van_der_pol_jac, rtol=1e-8, atol=1e-10)
```

---

## Recipe 3 — Event detection

Events are roots of a scalar function `g(t, y)`. The solver reports the exact
time and state at each sign change.

```python
def projectile(t, y):
    """2-D projectile with quadratic drag. State = [x, vx, z, vz]."""
    x, vx, z, vz = y
    g, drag = 9.80665, 0.01
    speed = np.hypot(vx, vz)
    return [vx, -drag * speed * vx,
            vz, -g - drag * speed * vz]

def hit_ground(t, y):
    return y[2]                        # z == 0
hit_ground.terminal = True            # stop integration at first hit
hit_ground.direction = -1             # only while z is decreasing

def apex(t, y):
    return y[3]                        # vz == 0
apex.direction = -1

sol = solve_ivp(
    projectile, (0.0, 100.0), [0.0, 50.0, 0.0, 50.0],
    events=[hit_ground, apex],
    max_step=0.1,                     # keep < event timescale
    dense_output=True,
)
print(f"Impact  at t = {sol.t_events[0][0]:.3f} s")
print(f"Apex    at t = {sol.t_events[1][0]:.3f} s")
```

`sol.t_events[i]` and `sol.y_events[i]` hold the crossings for event `i`.
With `dense_output=True`, call `sol.sol(t)` to interpolate at any time.

---

## Recipe 4 — Symplectic (leapfrog) integration

For Hamiltonian systems, `solve_ivp` drifts in energy over long runs. Leapfrog
(Störmer–Verlet) is 2nd-order and symplectic. This is plain NumPy, not a
SciPy call.

```python
def leapfrog(dH_dq, dH_dp, q0, p0, dt, n_steps):
    """
    dH_dq(q, p) -> -dp/dt (the "force")
    dH_dp(q, p) ->  dq/dt (the "velocity")
    Returns arrays q_hist, p_hist of shape (n_steps+1, dim).
    """
    q, p = np.array(q0, float), np.array(p0, float)
    q_hist, p_hist = [q.copy()], [p.copy()]
    for _ in range(n_steps):
        p = p - 0.5 * dt * dH_dq(q, p)   # half kick
        q = q + dt * dH_dp(q, p)          # full drift
        p = p - 0.5 * dt * dH_dq(q, p)   # half kick
        q_hist.append(q.copy()); p_hist.append(p.copy())
    return np.array(q_hist), np.array(p_hist)

# Kepler problem (GM = 1): elliptical orbit
def dH_dq(q, p):
    return q / np.linalg.norm(q)**3      # gravitational force
def dH_dp(q, p):
    return p                              # velocity (unit mass)

q_hist, p_hist = leapfrog(dH_dq, dH_dp,
                          q0=[1.0, 0.0], p0=[0.0, 0.8],
                          dt=0.01, n_steps=10_000)

# Energy should stay flat (up to bounded oscillation)
E = 0.5 * np.sum(p_hist**2, axis=1) - 1.0 / np.linalg.norm(q_hist, axis=1)
print(f"Energy drift: {E.max() - E.min():.2e}")
```

For separable, non-separable, or higher-order needs, use a 4th-order Yoshida
composition of leapfrog steps.

---

## Recipe 5 — Boundary value problem

Two-point BVP: `y'' + y = 0` with `y(0) = y(pi) = 0`.

```python
def rhs(x, y):
    return np.vstack([y[1], -y[0]])       # shape (n_states, mesh)

def bc(ya, yb):
    return np.array([ya[0], yb[0]])       # residuals: y(0)=0, y(pi)=0

x = np.linspace(0, np.pi, 100)
y_init = np.zeros((2, x.size))
y_init[0] = np.sin(x)                     # initial guess drives convergence

sol = solve_bvp(rhs, bc, x, y_init)
print("BVP solved:", sol.success, sol.status, sol.message)
xs = np.linspace(0, np.pi, 200)
ys = sol.sol(xs)[0]                       # continuous interpolant
```

`solve_bvp` is a collocation solver; a poor `y_init` is the usual cause of
non-convergence. `sol.status`: 0 = converged, 1 = max mesh nodes exceeded,
2 = singular Jacobian.

---

## Recipe 6 — Parameter sweep & phase portrait

```python
from functools import partial

def damped(t, y, gamma=0.1, omega=1.0):
    x, v = y
    return [v, -2 * gamma * v - omega**2 * x]

fig, (ax_t, ax_phase) = plt.subplots(1, 2, figsize=(12, 5))
for gamma in [0.05, 0.1, 0.5, 1.0, 2.0]:
    rhs = partial(damped, gamma=gamma)
    sol = solve_ivp(rhs, (0, 20), [1.0, 0.0],
                    t_eval=np.linspace(0, 20, 500), rtol=1e-10)
    regime = "under" if gamma < 1 else ("critical" if gamma == 1 else "over")
    ax_t.plot(sol.t, sol.y[0], label=f"γ={gamma} ({regime}damped)")
    ax_phase.plot(sol.y[0], sol.y[1])     # x vs v = phase portrait

ax_t.set_xlabel("t [s]"); ax_t.set_ylabel("x(t)"); ax_t.legend()
ax_phase.set_xlabel("x"); ax_phase.set_ylabel("v")
for ax in (ax_t, ax_phase): ax.grid(True, alpha=0.3)
plt.savefig("damped_sweep.png", dpi=150, bbox_inches="tight")
```
