# Boundary Conditions

The interior stencil is only half the solver — the boundary decides whether waves
reflect, pass through, or wrap. Pick the one that matches the physics, and know
how much spurious reflection each leaves behind.

## Reflecting and periodic conditions (exact, cheap)

| Condition        | Physics                          | Update at boundary `i=0`            |
| ---------------- | -------------------------------- | ----------------------------------- |
| Fixed (Dirichlet)| Clamped / rigid wall, `u=0`      | `u_next[0] = 0`                     |
| Free (Neumann)   | Open / stress-free, `∂u/∂n = 0`  | `u_next[0] = u_next[1]`             |
| Periodic         | Tiling / infinite periodic media | `u_next[0] = u_next[-2]` (wrap)     |

These are exact — no reflection artifact, because reflection *is* the intended
physics (a wall reflects; a periodic edge wraps). A closed domain built from
fixed/free walls conserves energy and is the setting for **cavity resonances and
standing waves**: excite, march, and read the resonant frequencies off the FFT of
a probe time series.

## Absorbing boundaries (open domains)

To model an *unbounded* medium on a finite grid you must absorb outgoing waves so
they do not reflect back and contaminate the interior.

### First-order Mur ABC

Discretize the one-way (Sommerfeld radiation) condition `∂u/∂t + c ∂u/∂n = 0`:

```python
m = (c*dt - dx) / (c*dt + dx)
u_next[0]  = u_curr[1]  + m * (u_next[1]  - u_curr[0])     # left edge
u_next[-1] = u_curr[-2] + m * (u_next[-2] - u_curr[-1])    # right edge
```

- **1D: nearly perfect** — a wave hitting the boundary head-on is almost fully
  absorbed.
- **2D/3D: only good near normal incidence.** A wave arriving obliquely reflects
  a fraction that grows with the angle; grazing waves reflect strongly.
- Second-order Mur adds tangential-derivative terms and cuts oblique reflection
  substantially, but is fiddly at corners.

### Perfectly Matched Layer (PML) — the robust choice

A PML surrounds the physical domain with a lossy layer whose impedance is matched
so that, in the continuous limit, waves enter it **without reflection at any angle
or frequency** and are then damped exponentially before they can return.

Mechanics (concept — full split-field/CPML equations belong in a dedicated
implementation):

- Add a **damping profile** `σ(x)` that is zero in the interior and ramps
  smoothly up through a layer ~8–20 cells thick at each edge. A polynomial ramp
  `σ(x) = σ_max·(d/D)^m` with `m ≈ 2–3` and `d` the depth into the layer is
  standard; an abrupt jump in `σ` itself causes reflection, so ramp gently.
- In the layer, march an **auxiliary/split field** with an added loss term so the
  outgoing wave decays. In split-field PML the field `u = u_x + u_y` is split per
  axis, each part damped only by that axis's `σ`.
- Tune `σ_max` for a target reflection (e.g. `R ≈ 1e-6`); too small under-absorbs,
  too large reflects off the interior/PML interface.

Use a PML whenever boundary reflection would corrupt the measurement — scattering
cross-sections, long records, or 2D/3D fields with oblique wavefronts. For quick
1D work, first-order Mur is usually enough.

## Reflection levels at a glance

| Method            | Normal incidence | Oblique / grazing | Cost         |
| ----------------- | ---------------- | ----------------- | ------------ |
| Copy-neighbor     | moderate         | poor              | trivial      |
| First-order Mur   | very low (1D)    | grows with angle  | trivial      |
| Second-order Mur  | very low         | low–moderate      | low          |
| PML               | very low         | very low          | moderate     |

## Practical notes

- **Corners** need care: apply the ABC/PML consistently on both edges meeting at a
  corner, or leave a small fixed cell — corners are the classic reflection leak.
- A **sponge layer** (multiply the field by a factor `<1` that ramps up near the
  edge) is a crude but reliable fallback when a PML is too much machinery; it is
  frequency-dependent and thicker than a PML for the same absorption.
- Always verify absorption with the **energy check**: with absorbing boundaries,
  total energy should decay to ~0 as the last wavefront exits. Residual
  oscillation left in the interior is reflected energy — thicken the layer or
  retune `σ_max`.
