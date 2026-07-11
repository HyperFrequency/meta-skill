---
name: shock-capturing-neural-operators
version: 0.1.0
description: >-
  Design and diagnose neural operators (FNO variants) for PDE solutions that
  contain shocks, contact discontinuities, or steep gradients, where a plain
  Fourier Neural Operator produces Gibbs oscillations near the jump. Covers
  gated local-global spectral blocks (a local convolution branch beside the FFT
  path to capture sub-mode-scale features), reflection padding for
  non-periodic / outgoing / transmissive boundary conditions, resolution
  scaling against physical shock width (~ nu/U), per-band frequency-error
  diagnostics that localize where the operator fails, and architecture
  selection per viscosity regime. Use for low-viscosity Burgers, compressible
  Euler, Riemann / shock-tube problems, or any operator-learning task where a
  standard FNO oscillates at discontinuities. Do NOT use for smooth PDEs (a
  standard FNO or DeepONet via `neural-operator` suffices), as a PDE solver or
  training-data generator (use `pde-solver`), for long-horizon time-stepping
  (use `autoregressive-neural-pde-solver`), or non-PDE regression.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# Shock-Capturing Neural Operators

## Overview

A Fourier Neural Operator (FNO) mixes information globally by truncating a
Fourier transform: `FFT -> keep k modes -> iFFT`. That is efficient for smooth
solution fields, but it fails on discontinuities. The Fourier coefficients of a
jump decay only as O(1/k), so a truncated spectral representation always
oscillates near the discontinuity — the **Gibbs phenomenon**. This is a
mathematical property of the representation, not a training bug: no amount of
data or epochs removes it, and adding modes helps only marginally while
inflating cost. In practice, going from a smooth to a shock-dominated problem
degrades FNO relative error by roughly an order of magnitude (e.g. viscous
Burgers nRMSE ~3e-3 at nu=0.1 vs ~3e-2 at nu=0.001).

This skill is the shock-hardened companion to `neural-operator`. It keeps the
FNO backbone but adds three architectural interventions plus a spectral
diagnostic, so the operator resolves sharp fronts without ringing. It does not
introduce a new library — the techniques are small PyTorch modules layered onto
a standard FNO block.

## When to Use This Skill

- The target PDE has shocks, contact discontinuities, rarefaction edges, or
  steep gradients: low-viscosity Burgers, compressible Euler, Navier-Stokes at
  high Reynolds number, Riemann / shock-tube problems.
- A trained FNO shows oscillatory over/undershoot near jumps, or its error is
  concentrated in high wavenumbers.
- The domain is **non-periodic** — outgoing, transmissive, or Dirichlet
  boundaries — which violates the FFT's periodicity assumption and leaks energy
  from one boundary to the other.
- You need to know *where* an operator fails (which spatial scales) to justify
  an architecture change.

## When NOT to Use This Skill

- The solution is smooth (diffusion-dominated, subsonic, well-resolved). Use a
  standard FNO/TFNO/DeepONet via `neural-operator` — the extra branches only add
  parameters.
- You need to *solve* one PDE instance or *generate* ground-truth training
  data. Use `pde-solver` (or a shock-capturing classical scheme: Godunov, WENO,
  MUSCL) — a neural operator needs solved instances to learn from.
- You need long-horizon autoregressive roll-outs. Use
  `autoregressive-neural-pde-solver`; the modules here are drop-in for its FNO
  block but the roll-out stability concerns live there.
- The task is not an operator-learning problem over a function space (plain
  tabular/time-series regression).

## The three interventions

**1. Gated local-global block.** Run a local `Conv1d` branch in parallel with
the spectral branch and blend them with a learned scalar gate. The spectral path
captures large-scale global structure; the local convolution captures the shock
and its immediate neighborhood at sub-mode scale, without spectral ringing. The
core blend, given a global output `global_out` and a local output `local_out`:

```python
alpha = torch.sigmoid(self.gate)          # gate is an nn.Parameter, init ~0.3
return (1 - alpha) * global_out + alpha * local_out
```

Kernel width should span a few grid cells at the shock scale (e.g. 7). In
trained models the per-layer gate typically settles to alpha ~ 0.3-0.6, i.e.
both branches genuinely contribute. Full `FNOBlock` and `SpectralConv1d`
wiring, plus the multi-variable (Euler/NS) per-channel normalization variant,
are in [references/architectures.md](references/architectures.md).

**2. Reflection padding for non-periodic BCs.** The FFT treats the field as
periodic, so a wave leaving the right boundary re-enters at the left in Fourier
space. Pad the field with `mode='reflect'` before the spectral layers and crop
after. Reflection creates a smooth continuation (unlike zero-padding, which
injects its own jump) and cuts spectral leakage from the boundaries. Use a
*substantial* pad — order 10% of the grid (e.g. 32 points on a 256-grid), not
the token 2-point pad. Code and the Fourier-Continuation alternative are in
[references/architectures.md](references/architectures.md).

**3. Resolution scaling.** For shocks, grid resolution is the single largest
lever. The viscous shock width scales as ~ nu/U, so you must resolve that width
with enough cells: nu=0.1 needs ~256 points, nu=0.001 needs ~1024 (and an
A100-class GPU), and truly inviscid problems want as much resolution as you can
afford. The full viscosity-to-grid table and the memory/compute scaling are in
[references/diagnostics.md](references/diagnostics.md).

## Diagnosing where the operator fails

Do not read a single scalar error. Decompose the prediction error by wavenumber
band (low / mid / high) with an rFFT to localize the failure. The canonical
signature of a Gibbs-limited operator is: low band ~0.1% (large-scale structure
is captured), mid band ~5-10% (shock-scale features), high band ~30% (Gibbs
oscillations dominate). Rising high-band error is your signal to add resolution
or switch representation. The `frequency_band_errors` function, its
interpretation, and the shock-aware training losses (H1/Sobolev loss, a
frequency-domain loss term, and a boundary-consistency loss) are in
[references/diagnostics.md](references/diagnostics.md).

## Choosing an architecture

Match the intervention set to the regime — moderate viscosity, low viscosity,
multi-variable systems, and non-periodic / Riemann problems each want a
different combination. The selection table is in
[references/diagnostics.md](references/diagnostics.md).

## Beyond FNO

When the high-band error refuses to fall, the FNO representation itself may be
the ceiling. Wavelet neural operators, Fourier-Continuation operators,
Convolutional Neural Operators, entropy-satisfying (Godunov) losses, and
DCT/DST spectral bases all attack the discontinuity problem more fundamentally.
Annotated pointers with references are in
[references/literature.md](references/literature.md).

## Related skills

- `neural-operator` — the base FNO/TFNO/DeepONet training workflow this skill
  hardens; start there for smooth problems.
- `pde-solver` — classical solvers (including shock-capturing WENO/Godunov) to
  generate the ground-truth training data.
- `autoregressive-neural-pde-solver` — long-horizon time-stepping; use these
  blocks inside its roll-out.
- `hdf5-pde-data-loading` — stream large shock datasets at the high resolutions
  this skill demands.
- `conservation-law-discovery`, `fluid-dynamics` — the physics of the systems
  (Euler, Burgers, Navier-Stokes) whose shocks you are modeling.
