# Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Phase-portrait arrows all tiny or huge | Field magnitude varies over orders of magnitude | Use `streamplot` (auto-scaled) or normalize `quiver` arrows by `np.hypot(U, W)` |
| `fsolve` "converges" to a non-root | `ier == 1` reported on a flat region | Check `info["fvec"]` residual `< 1e-8`; reject otherwise |
| Missing some equilibria | Single initial guess only finds the nearest root | Seed `fsolve` from a grid of guesses and deduplicate (multi-start) |
| Lyapunov exponent won't settle | Integration too short, or transient not discarded | Integrate 10–100 Lyapunov times; drop the transient before averaging; plot the running estimate |
| Lyapunov exponent noisy / wrong sign | Loose solver tolerance corrupts the tangent flow | Tighten to `rtol≈1e-10`, `atol≈1e-12` |
| Spectrum sum ≠ `⟨tr J⟩` | Renormalization/QR step wrong or `dt` too large | Verify `Σλ_k ≈ ⟨tr J⟩`; shrink `dt_renorm` |
| Poincaré section too sparse | Not enough crossings collected | Increase `t_total`, or use the `events` API to catch every crossing |
| Poincaré points look jittery | Linear-interpolation error between `t_eval` samples | Switch to `solve_ivp(events=...)` for root-accurate crossings |
| Bifurcation branch stops mid-sweep | Continuation hit a fold (saddle-node) or lost the branch | Use pseudo-arclength continuation, or PyDSTool/MatCont/AUTO-07p |
| Bifurcation diagram missing branches | Parameter step too large, or disconnected branch | Shrink the step; seed continuation from multiple starting solutions |
| Integration blows up / is glacially slow | Stiff system on an explicit solver | Switch `method="Radau"` or `"LSODA"`; supply an analytic `jac=` |
| `solve_ivp` returns few/uneven points | Adaptive stepper output only | Pass `t_eval=...` for a fixed grid, or `dense_output=True` and call `sol.sol(t)` |

## Stiffness

If the RHS mixes fast and slow timescales (large eigenvalue-magnitude spread in
`J`), an explicit method (`RK45`, `DOP853`) either crawls or diverges. Symptoms:
the solver takes thousands of tiny steps, or a physically bounded trajectory
overflows. Fix by using an implicit stiff solver and, ideally, providing the
Jacobian:

```python
sol = solve_ivp(rhs, (0, T), y0, method="Radau", jac=jacobian, rtol=1e-8, atol=1e-10)
```

`"LSODA"` auto-switches between stiff and non-stiff and is a good default when you
are unsure.

## Non-hyperbolic Fixed Points

When any eigenvalue has `Re(λ) = 0`, linear stability analysis is inconclusive
and the equilibrium's fate is decided by nonlinear terms:
- Do **not** report "center" from pure-imaginary eigenvalues unless the system is
  conservative — confirm closed orbits with a conserved quantity
  (`conservation-law-discovery`) or by direct integration over many periods.
- A zero real eigenvalue usually flags a bifurcation point; study the branch
  either side of it rather than at it.
- For a rigorous verdict, apply center-manifold reduction / normal-form theory to
  the reduced dynamics on the marginal eigenspace.

## Reproducibility

- Seed every RNG used for initial tangent vectors (`np.random.default_rng(seed)`)
  so Lyapunov runs repeat exactly.
- Record solver `method`, `rtol`, `atol`, `t_total`, and transient-discard length
  alongside any reported exponent — a Lyapunov value is meaningless without them.
