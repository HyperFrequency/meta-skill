# Symplectic Integrators — Full Reference

All code assumes `import numpy as np`. The integrators here are symplectic **only for a
separable Hamiltonian** `H(q, p) = T(p) + V(q)`. See the last section for the non-separable
case.

## General leapfrog (∂H/∂q, ∂H/∂p form)

When you prefer to pass the two partials of `H` directly rather than a force:

```python
def leapfrog_general(dH_dq, dH_dp, q0, p0, dt, n_steps):
    """Störmer–Verlet. dH_dq = ∂H/∂q (so ṗ = -dH_dq), dH_dp = ∂H/∂p (so q̇ = dH_dp).

    Exactly symplectic only when H is separable (dH_dq depends on q only,
    dH_dp on p only). For a p-dependent force this becomes implicit and the
    explicit update below is only approximate — use the non-separable methods.
    """
    q = np.empty((n_steps + 1,) + np.shape(q0))
    p = np.empty_like(q)
    q[0], p[0] = q0, p0
    for i in range(n_steps):
        p_half   = p[i] - 0.5 * dt * dH_dq(q[i], p[i])
        q[i + 1] = q[i] + dt * dH_dp(q[i], p_half)
        p[i + 1] = p_half - 0.5 * dt * dH_dq(q[i + 1], p_half)
    return q, p
```

## Worked example: Kepler orbit + energy check

`H = p²/2 − 1/|q|` with `GM = 1`. A sub-circular launch speed gives an ellipse.

```python
import matplotlib.pyplot as plt

def force(q):                       # -dV/dq for V = -1/|q|
    r = np.linalg.norm(q)
    return -q / r**3

q0, p0 = np.array([1.0, 0.0]), np.array([0.0, 0.8])
dt, n_steps = 0.01, 100_000         # 1000 time units

q, p = leapfrog(force, q0, p0, dt, n_steps)     # leapfrog() from SKILL.md

H  = 0.5 * np.sum(p**2, axis=1) - 1 / np.linalg.norm(q, axis=1)
print(f"max |ΔH/H₀| = {np.max(np.abs((H - H[0]) / H[0])):.2e}")   # bounded, ~1e-4

fig, ax = plt.subplots(1, 2, figsize=(13, 5))
ax[0].plot(q[:, 0], q[:, 1], lw=0.3); ax[0].plot(0, 0, 'yo')
ax[0].set_aspect('equal'); ax[0].set_title('Orbit (leapfrog)')
t = np.arange(n_steps + 1) * dt
ax[1].plot(t, (H - H[0]) / abs(H[0]), lw=0.3)
ax[1].set(xlabel='time', ylabel='ΔH/|H₀|', title='energy (bounded, no drift)')
plt.tight_layout()
```

A monotone trend in the right panel means the map is not actually symplectic (wrong method,
or non-separable `H`).

## Yoshida 4th order

Cancel leapfrog's leading error by composing three leapfrog sub-steps with Yoshida's (1990)
coefficients. Written as a drift–kick sequence `D(c₀) K(d₀) D(c₁) K(d₁) D(c₂) K(d₂) D(c₃)`:

```python
def yoshida4(force, q0, p0, dt, n_steps, mass=1.0):
    """4th-order symmetric composition (Yoshida 1990). ~3 force evals/step."""
    w1 = 1.0 / (2.0 - 2.0**(1/3))
    w0 = -2.0**(1/3) * w1
    c = np.array([w1/2, (w0 + w1)/2, (w0 + w1)/2, w1/2])   # drift (position) coeffs
    d = np.array([w1, w0, w1, 0.0])                        # kick (momentum) coeffs; d[3]=0

    q = np.empty((n_steps + 1,) + np.shape(q0)); p = np.empty_like(q)
    q[0], p[0] = q0, p0
    for i in range(n_steps):
        qi, pi = q[i].copy(), p[i].copy()
        for k in range(4):
            qi = qi + c[k] * dt * pi / mass
            if d[k] != 0.0:
                pi = pi + d[k] * dt * force(qi)
        q[i + 1], p[i + 1] = qi, pi
    return q, p
```

On the Kepler test above, `yoshida4` typically gives `max|ΔH/H₀| ~ 1e-8` — four orders
better than leapfrog at the same `dt`, for ~3× the cost.

## Higher order

The same triple-jump construction recurses: a 6th-order method composes three 4th-order
steps, an 8th-order method three 6th-order steps (Yoshida gives explicit coefficient sets).
Cost grows as `3^(k)` sub-steps for order `2(k+1)`, so 6th (7 evals/step) and 8th (15
evals/step) pay off only for very smooth forces and very tight tolerances. Prefer the
Yoshida-optimized coefficient sets over naive recursion for better error constants.

## Operator-splitting view

Leapfrog is the symmetric Strang split of the flow: `e^{dt·L} ≈ e^{(dt/2)·L_V} e^{dt·L_T}
e^{(dt/2)·L_V}`, where `L_T` (drift) and `L_V` (kick) are each exactly integrable for a
separable `H`. Every method above is a different composition of these two exact sub-flows;
symplecticity is automatic because a composition of symplectic maps is symplectic. The order
conditions on the coefficients are what Yoshida solved.

## N-body

Vectorize the pairwise force, **soften** the singularity, and drive it with KDK leapfrog.

```python
def nbody_acceleration(q, masses, G=1.0, eps=1e-3):
    """q: (N, D). Softened gravity: 1/r → 1/(r²+eps²)^{3/2}. Returns (N, D) accel."""
    disp = q[None, :, :] - q[:, None, :]                 # (N, N, D): r_j - r_i
    r2   = np.sum(disp**2, axis=-1) + eps**2             # (N, N), softened
    inv  = r2**-1.5
    np.fill_diagonal(inv, 0.0)                           # no self-force
    return G * np.einsum('ij,ijd,j->id', inv, disp, masses)

def nbody_leapfrog(q0, v0, masses, dt, n_steps, G=1.0, eps=1e-3, stride=100):
    q, v = q0.copy(), v0.copy()
    a = nbody_acceleration(q, masses, G, eps)
    traj = [q.copy()]
    for step in range(n_steps):
        v += 0.5 * dt * a
        q += dt * v
        a  = nbody_acceleration(q, masses, G, eps)
        v += 0.5 * dt * a
        if step % stride == 0:
            traj.append(q.copy())
    return np.array(traj)
```

Figure-8 three-body test (Chenciner–Montgomery), a stringent long-run stability check:

```python
masses = np.array([1.0, 1.0, 1.0])
q0 = np.array([[-0.97000436, 0.24308753, 0.0],
               [ 0.97000436, -0.24308753, 0.0],
               [ 0.0,        0.0,        0.0]])
vb = np.array([0.4662036850, 0.4323657300, 0.0])
v0 = np.array([-vb/2, -vb/2, vb])                     # velocities (= momenta, unit mass)
traj = nbody_leapfrog(q0, v0, masses, dt=1e-3, n_steps=100_000, eps=0.0)
```

Naive `O(N²)` force scales badly; for large `N` use a Barnes–Hut tree or an FFT/PM Poisson
solver, still driven by the same KDK stepper.

## Non-separable H and adaptive stepping

- **Non-separable `H(q, p)`** (magnetic vector potential, relativistic kinetic term): the
  explicit leapfrog above is no longer symplectic. Options: (a) split into an explicitly
  integrable set of terms if one exists; (b) extended-phase-space methods (Tao 2016) that
  duplicate `(q, p)` into two copies with a binding term and use a symplectic map on the
  enlarged space; (c) an implicit symplectic method (implicit midpoint, Gauss–Legendre) —
  robust but requires a nonlinear solve per step.
- **Adaptive/regularized stepping**: a plain variable `dt` destroys symplecticity. Use a
  *time transformation* — introduce fictitious time `s` with `dt/ds = g(q)` and integrate the
  extended Hamiltonian symplectically (Mikkola–Aarseth time-transformed leapfrog). Standard
  for gravitational close encounters where a fixed `dt` cannot resolve the pericenter.
