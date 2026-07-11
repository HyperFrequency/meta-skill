# Validation & Troubleshooting

Stability limits, correctness checks, expected physics, and a symptom → fix
catalogue for the solvers in `incompressible-solvers.md`. Run the four sanity
checks in the SKILL.md before reporting any result.

---

## Stability Limits (Explicit Schemes)

The explicit FTCS vorticity update in the cavity/channel solvers is
**conditionally stable**. Both conditions must hold at the *actual peak*
velocity, not the nominal boundary velocity.

| Condition | Limit | Meaning |
|---|---|---|
| Advective CFL | `|u|·dt/dx < 1` (target `< 0.5`) | information travels < 1 cell/step |
| Diffusion number | `ν·dt/dx² < 0.25` (2D), `< 0.5` (1D) | explicit diffusion stability |

With `ν = 1/Re` on a unit domain, the diffusion limit is `dt < 0.25·Re·dx²`. As
you refine the grid (`dx ↓`) this shrinks quadratically — the usual reason a
finer run suddenly blows up. Escape routes:

- **Smaller `dt`** — cheapest fix, but slows convergence to steady state.
- **Implicit diffusion** (Crank-Nicolson) — unconditionally stable for the
  diffusion term; solve a tridiagonal/banded system each step.
- **RK time integration** (RK2/RK4) for the advection term — larger stable CFL
  and higher temporal order.
- **Upwind advection** for high `Re` — FTCS advection is only marginally stable
  and adds dispersive wiggles; first-order upwind or a flux limiter is more robust.

---

## Correctness Checks

**Divergence-free field** — incompressibility means `∇·u = 0` everywhere; the
discrete divergence should stay at discretisation-noise level:

```python
import numpy as np
def max_divergence(u, v, dx):
    div = np.zeros_like(u)
    div[1:-1, 1:-1] = ((u[1:-1, 2:] - u[1:-1, :-2]) +
                       (v[2:, 1:-1] - v[:-2, 1:-1])) / (2*dx)
    return np.max(np.abs(div))
```

The vorticity-streamfunction formulation is divergence-free by construction, so a
growing `max|∇·u|` there points to a boundary-condition or indexing bug. In a
projection solver, it measures how well the pressure Poisson solve converged.

**Steady-state convergence** — track `max|ω|` (or the kinetic energy); a steady
run should plateau. If it keeps drifting, you have not run long enough or the
scheme is unstable.

**Grid convergence** — refine `N` until the reported quantity (cavity centerline,
`Cd`, shedding frequency) stops changing to your tolerance. A result that moves
with resolution is not converged.

**Benchmark comparison** — for the lid-driven cavity, compare the centerline
`u(0.5, y)` and `v(x, 0.5)` profiles against Ghia et al. (1982), Table I. Load
the tabulated values from the paper and interpolate your solution to their 17
non-uniform y-stations, then report the L2 error. Qualitative anchors at
`Re = 100`: a single primary vortex centred above and right of the geometric
centre, two weak secondary vortices in the bottom corners, and a centerline
`u` that dips to a negative minimum in the lower half of the cavity.

---

## Flow-Regime Map (Flow Past a Cylinder)

Use this to sanity-check that a wake simulation is producing the right physics
for its Reynolds number.

| Reynolds number | Regime | What you should see |
|---|---|---|
| `Re < 1` | Stokes (creeping) | Fore-aft symmetric, reversible, inertia-free |
| `1 < Re < ~40` | Steady laminar | Attached twin recirculation vortices |
| `~40 < Re < ~200` | Von Kármán shedding | Periodic vortex street, `St ≈ 0.2` |
| `~200 < Re < ~10⁵` | Turbulent wake | Broadband spectrum, 3D instabilities |
| `Re > ~10⁵` | Drag crisis | Boundary-layer transition, `Cd` drops sharply |

Boundaries are approximate and geometry-dependent. `St = f·D/U∞` is the Strouhal
number (shedding frequency `f`, diameter `D`).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Solution blows up / NaNs | CFL or diffusion number violated | Reduce `dt`; recheck limits at *peak* `|u|`, not boundary speed |
| Blows up only after refining grid | Diffusion limit `dt < 0.25·Re·dx²` shrank | Shrink `dt` quadratically with `dx`, or go implicit |
| Checkerboard pressure/velocity | Collocated-grid decoupling | Use a staggered (MAC) grid, or Rhie-Chow interpolation |
| Poisson solve dominates runtime | Jacobi/Gauss-Seidel too slow | SOR (`w ≈ 1.7–1.95`) or the DST direct solver (`incompressible-solvers.md`) |
| Dispersive wiggles near shear layers | Central advection at high `Re` | First-order upwind or a flux-limited scheme |
| `max|∇·u|` grows over time | BC/indexing bug or under-converged pressure Poisson | Recheck wall BCs; tighten Poisson tolerance |
| Wrong drag / `Cd` | Under-resolved boundary layer near the body | Refine near the surface; verify wake plane is in clean flow |
| Wrong shedding frequency | Domain too small / blockage | Enlarge domain; keep blockage ratio `D/H` small |
| Energy spectrum flattens at high `k` | Under-resolution or aliasing | Refine grid; dealias, or switch to `fluidsim` for periodic turbulence |
| Cavity vortex in wrong place | Not converged, or swapped `u`/`v` sign | Run longer; verify `u = ∂ψ/∂y`, `v = −∂ψ/∂x` |

---

## References

- Ghia, U., Ghia, K.N., Shin, C.T. (1982). "High-Re solutions for incompressible
  flow using the Navier-Stokes equations and a multigrid method." *J. Comput.
  Phys.* 48(3), 387–411. — canonical lid-driven cavity benchmark.
- Hunt, J.C.R., Wray, A.A., Moin, P. (1988). Eddies, streams, and convergence
  zones in turbulent flows. — origin of the Q-criterion.
