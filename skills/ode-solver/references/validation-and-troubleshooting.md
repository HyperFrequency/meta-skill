# ODE Solver — Validation & Troubleshooting

## Validation checklist

Run these before trusting or reporting any integration:

- [ ] `sol.success is True` and `sol.message` is clean.
- [ ] **Convergence:** halve `max_step` (or tighten `rtol`/`atol` by ~2–3
      orders) and confirm the solution does not change meaningfully. If it
      moves, it was not converged.
- [ ] **Invariants:** for conservative systems, check that energy / momentum /
      any known conserved quantity holds to tolerance over the whole run. A
      slow monotone drift means you need a symplectic integrator, not a tighter
      tolerance.
- [ ] **Known limits:** compare against an analytic solution in a limit you can
      solve by hand (e.g. small-angle pendulum, undamped oscillator).
- [ ] **Stiffness:** if the run was slow, confirm you used `Radau`/`BDF`/`LSODA`
      rather than fighting an explicit solver.
- [ ] **Events:** verify each expected crossing appears in `sol.t_events` and
      that `max_step` was smaller than the event's timescale.
- [ ] **BVP:** check `sol.status == 0`; a nonzero status means the boundary
      conditions were not satisfied.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Integration is extremely slow | Stiff system on an explicit solver | Switch to `Radau` / `BDF` / `LSODA`; supply `jac` |
| `success=False`, message about step size | Solver cannot meet tolerance / stiffness | Try an implicit method, loosen `rtol`, or reduce `max_step` through a transient |
| Solution changes when tolerances tighten | Not converged | Keep tightening `rtol`/`atol` until it stabilizes |
| Energy drifts over long runs | Non-symplectic integrator | Use leapfrog / Störmer–Verlet for Hamiltonian systems |
| Trajectory oscillates or looks noisy | Under-resolved | Lower `rtol`/`atol`, cap `max_step` |
| Expected event never fires | rhs stepped over the crossing, or wrong `direction` | Reduce `max_step` below the event timescale; check `event.direction` sign |
| Event fires at the wrong time | Coarse root bracketing | Set `dense_output=True` and a smaller `max_step` |
| `solve_bvp` `status == 1` | Mesh exhausted | Improve `y_init`, raise `max_nodes`, or relax `tol` |
| `solve_bvp` `status == 2` | Singular Jacobian | Fix the initial guess; check the boundary conditions are independent and well-posed |
| NaNs in `sol.y` | rhs blew up (singularity, division by zero) | Guard the rhs; add `max_step`; rescale / nondimensionalize the system |
| Wildly different runtime for a tiny parameter change | Crossed a stiffness threshold | Use `LSODA` (auto-switching) or the implicit solvers |

## When results look wrong but nothing errors

- **Re-derive the first-order form.** A silent index/sign error in `fun` is the
  most common cause of a "converged" but physically wrong trajectory.
- **Nondimensionalize.** Extreme parameter magnitudes hurt conditioning; use
  `dimensional-analysis` to rescale time and state to O(1).
- **Check units** on constants (e.g. `g = 9.80665 m/s²`) and on `t_span`.
