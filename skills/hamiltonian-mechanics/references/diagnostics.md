# Phase-Space Diagnostics

How to tell whether a long integration is trustworthy, and how to read the geometry of the
motion. Assumes `import numpy as np`.

## Energy drift — the first check on any run

For a symplectic integrator the measured energy oscillates in a bounded band; a *trend* is a
red flag.

```python
def energy_report(H_values, dt):
    H0 = H_values[0]
    rel = (H_values - H0) / abs(H0)
    print(f"max |ΔH/H₀|  = {np.max(np.abs(rel)):.2e}")     # bounded band width
    # crude secular-trend test: slope of a linear fit should be ~0 for symplectic runs
    t = np.arange(len(H_values)) * dt
    slope = np.polyfit(t, rel, 1)[0]
    print(f"drift slope   = {slope:.2e} per unit time  (≈0 ⇒ symplectic; ≠0 ⇒ drifting)")
    return rel
```

Interpretation:

- **Bounded oscillation, slope ≈ 0** → symplectic behaviour, run is sound.
- **Monotone growth/decay** → you are using a non-symplectic method, or feeding a
  non-separable `H` into an explicit scheme. Fix the method, not `dt`.
- Band width scales as `dt^order`; halving `dt` shrinks a leapfrog band ~4×.

## Poincaré surface of section

Sample the trajectory whenever a chosen coordinate `q[section_idx]` crosses `section_val`
in the positive direction, and record the *other* phase-space coordinates. Interpolate the
crossing — do not snap to the nearest stored sample, or the section blurs.

```python
def poincare_section(q, p, section_idx=0, section_val=0.0, direction=+1):
    """q, p: (T, n) trajectory arrays. Returns crossing points (q_cross, p_cross),
    each (n_crossings, n-1), with the section coordinate removed."""
    s = q[:, section_idx] - section_val
    other = [j for j in range(q.shape[1]) if j != section_idx]
    qc, pc = [], []
    for i in range(1, len(q)):
        crossed = (s[i - 1] < 0 <= s[i]) if direction > 0 else (s[i - 1] > 0 >= s[i])
        if crossed:
            frac = -s[i - 1] / (s[i] - s[i - 1])            # linear interpolation
            qi = q[i - 1] + frac * (q[i] - q[i - 1])
            pi = p[i - 1] + frac * (p[i] - p[i - 1])
            qc.append(qi[other]); pc.append(pi[other])
    return np.array(qc), np.array(pc)
```

Reading the section (energy fixed on the surface):

- **Closed curves / nested loops** → invariant KAM tori; the motion is regular
  (quasi-periodic) and confined to a torus.
- **Scattered cloud filling an area** → the chaotic sea; a positive Lyapunov exponent.
- **Chains of small islands** → resonances (rational frequency ratios) with their own tori.

Increasing the system's energy (or a perturbation parameter) shrinks the tori and grows the
chaotic sea — the KAM-to-chaos transition. See the Chirikov overlap criterion in
[theory.md](theory.md).

## Lyapunov exponent — quantify chaos

The largest Lyapunov exponent `λ` measures exponential divergence of nearby trajectories;
`λ > 0` is the sharp signature of chaos. Estimate it by integrating a reference trajectory
alongside a shadow started a tiny distance `d0` away, renormalizing the separation each
interval and averaging the log stretch:

```python
def lyapunov_estimate(step_fn, state0, d0=1e-8, n_renorm=2000, sub_steps=50):
    """step_fn(state, sub_steps) advances a (q, p) state and returns the new state.
    Benettin renormalization method. Returns the largest Lyapunov exponent (per unit
    of the total integrated time)."""
    ref = state0
    pert = state0 + d0 * unit_perturbation(state0)          # small offset in phase space
    log_sum, total_t = 0.0, 0.0
    for _ in range(n_renorm):
        ref, t  = step_fn(ref, sub_steps)
        pert, _ = step_fn(pert, sub_steps)
        sep = np.linalg.norm(pert - ref)
        log_sum += np.log(sep / d0)
        pert = ref + (d0 / sep) * (pert - ref)               # renormalize back to d0
        total_t += t
    return log_sum / total_t
```

`unit_perturbation` / `step_fn` are problem-specific glue: `step_fn` wraps your leapfrog to
advance `sub_steps` and report the elapsed time. A cleaner but heavier route is to integrate
the tangent (variational) equations directly. For a full Lyapunov *spectrum*, evolve an
orthonormal frame and QR-reorthonormalize (Benettin's algorithm).

## Action variables

For an integrable 1-DOF system the action is the phase-space area enclosed by an orbit,
`J = (1/2π) ∮ p dq`, and is an adiabatic invariant. Compute it numerically over one closed
period of the trajectory:

```python
def action_variable(q_period, p_period):
    """One full period of a single degree of freedom. Shoelace area / 2π."""
    q, p = np.asarray(q_period), np.asarray(p_period)
    area = 0.5 * np.abs(np.sum(q * np.roll(p, -1) - np.roll(q, -1) * p))   # shoelace
    return area / (2 * np.pi)
```

Isolate a single period first (e.g. between successive positive crossings of `q = q_center`).
Constancy of `J` under a slowly varied parameter is the adiabatic theorem; a sudden jump in
`J` flags a separatrix crossing. Definitions and the angle variable are in [theory.md](theory.md).
