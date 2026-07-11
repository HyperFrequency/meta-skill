# Stability, Validation, and Troubleshooting

A PDE solution is worthless until you have shown it is *stable* (does not blow up), *accurate*
(converges under refinement), and *consistent* (satisfies the equation and its boundary
conditions). Do all three before trusting any number.

---

## Stability conditions

Explicit time-stepping is only conditionally stable — the time step is capped by the grid
spacing. Violating the limit makes the solution blow up (exponentially growing oscillations).

| Method | Stability condition | Notes |
|---|---|---|
| Explicit Euler (heat/parabolic) | `r = αΔt/Δx² ≤ 0.5` (1D); `≤ 0.25` in 2D | Simple, but Δt shrinks like Δx² |
| Implicit (backward) Euler (heat) | Unconditionally stable | Linear solve per step; 1st order in time |
| Crank–Nicolson (heat) | Unconditionally stable | 2nd order in time; can ring on sharp ICs |
| Explicit (wave/hyperbolic) | CFL: `cΔt/Δx ≤ 1` | Courant number ≤ 1 |
| Spectral + leapfrog | CFL on the *largest* wavenumber | Very restrictive as Δx shrinks |
| MOL + adaptive implicit (BDF/Radau) | Automatic | Integrator controls Δt; best general choice |
| PINN | N/A (optimization) | No stability limit; accuracy limited by training |

**The CFL number.** For advection/wave problems the Courant number `C = cΔt/Δx` measures how
many cells information crosses per step; explicit schemes require `C ≤ 1` (a signal must not
skip a cell). For diffusion the analogous number is `r = αΔt/Δx²`, and the `Δx²` scaling is
why explicit diffusion solvers become impractical on fine grids — prefer implicit or MOL.

If an explicit run blows up, the first suspect is always a violated stability condition:
reduce `Δt`, coarsen the grid, or switch to an implicit / adaptive method.

---

## Mesh convergence study

Halve `Δx` (and `Δt` to keep the scheme's ratio fixed) and confirm the solution stops
changing. The error should shrink at the scheme's formal order (2 for centered differences).

```python
import numpy as np

errors, hs = [], []
for Nx in [50, 100, 200, 400]:
    x, u = heat_1d_crank_nicolson(Nx=Nx, Nt=4 * Nx)   # keep Δt/Δx pattern consistent
    u_exact = np.sin(np.pi * x) * np.exp(-0.01 * np.pi**2 * 0.5)
    errors.append(np.max(np.abs(u - u_exact)))
    hs.append(1.0 / Nx)

rates = np.diff(np.log(errors)) / np.diff(np.log(hs))   # slope ≈ scheme order
print("errors:", errors, "\nobserved order:", rates)
```

A clean second-order slope (`≈ 2`) confirms the discretization is correct. A flat or noisy
slope signals a bug, a lower-order boundary treatment, or that you have hit round-off /
solver-tolerance floors.

---

## Method of Manufactured Solutions (MMS)

When no analytical solution exists, *manufacture* one: pick a smooth `u_exact(x, t)`,
substitute it into the PDE to get the source term `f` it implies, solve the PDE with that
`f` and matching BCs, and check the numerical result reproduces `u_exact` at the expected
order. Use `sympy` to derive `f` symbolically (see the `sympy` skill). MMS is the gold
standard for verifying a solver has no discretization bugs.

---

## Validation checklist

After solving any PDE, confirm:

- [ ] **Analytical check** — compare against a closed-form solution where one exists.
- [ ] **Mesh convergence** — halve `Δx`; the solution barely moves and error drops at the
      scheme's order.
- [ ] **Boundary conditions** — the numerical solution actually satisfies the imposed BCs at
      the edges (print/plot the boundary rows).
- [ ] **Conservation** — for conservative PDEs, the conserved quantity (mass, energy) is
      constant to solver tolerance over time.
- [ ] **CFL / stability** — for explicit schemes, the stability number is within its limit.
- [ ] **Residual** — substitute the solution back into the discrete PDE and confirm the
      residual is near zero (spikes localize the problem region).

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Solution blows up / NaNs | Explicit stability (CFL/`r`) violated | Reduce Δt, coarsen grid, or use implicit / MOL-BDF |
| Oscillations (Gibbs) near edges or shocks | Numerical dispersion; centered scheme on sharp features | Finer grid, higher-order/limited scheme, add slight diffusion |
| Crank–Nicolson rings on a discontinuous IC | Marginal stability of trapezoidal rule | Smooth the IC, or take a few backward-Euler steps first |
| Steady state is wrong | BCs not enforced correctly | Recheck boundary rows / source vector each step |
| Sparse direct solve is slow or OOM | System too large for LU | Switch to CG (SPD) / GMRES with an ILU preconditioner |
| MOL integrator crawls | Stiff system on an explicit method | Use `method="BDF"` or `"Radau"`; supply the Jacobian |
| Spectral solution has ringing | Aliasing from nonlinear products | Apply the 2/3 dealiasing rule; ensure periodicity/smoothness |
| PINN loss plateaus high | Bad architecture, LR, or loss balance | Deeper/wider net, lower LR, finish with L-BFGS, tune `loss_weights` |
| PINN fits PDE but not BCs | BC term underweighted | Raise BC `loss_weights`, or hard-constrain BCs via output transform |
| Pure-Neumann problem has no unique answer | Solution defined only up to a constant | Pin one node or add a mean/compatibility constraint |
