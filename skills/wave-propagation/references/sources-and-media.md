# Sources & Media

How to excite the field, and how to run it through non-uniform, layered, or
vector-valued media.

## Source wavelets

Inject a source as `u_next[src] += dt**2 * s(t)` (it enters the discretized
`∂²u/∂t²`). Keep the source **band-limited** so its spectrum stays within the
well-resolved wavenumber range — a raw impulse excites high-`k` modes the grid
propagates badly, producing ringing.

| Wavelet         | Formula (peak freq `f`, center `t0`)                 | Use for                          |
| --------------- | ---------------------------------------------------- | -------------------------------- |
| Ricker          | `(1 - 2a)·exp(-a)`, `a = (π f (t-t0))²`              | seismic, broadband pulse         |
| Gaussian pulse  | `exp(-(t-t0)²/(2σ²))`                                 | simple smooth test pulse         |
| Gaussian deriv. | `-(t-t0)/σ² · exp(-(t-t0)²/(2σ²))`                    | zero-DC broadband excitation     |
| Tone burst      | `sin(2π f t) · window(t)`                             | narrowband, near single-freq     |
| Plane wave      | set a whole line/plane of cells to `s(t)`            | incident field for scattering    |

- Set `t0 ≈ 1/f` (Ricker) or `t0 ≈ 3–4σ` (Gaussian) so the wavelet starts near
  zero — a nonzero value at `t=0` injects a step and rings.
- For a **tone burst**, use a Hann/Tukey window so onset and offset are smooth.
- A **hard source** (`u[src] = s(t)`, overwriting) acts as a rigid scatterer for
  later waves; a **soft/additive source** (`u[src] += …`) is transparent and is
  what you almost always want.

## Point, line, and plane sources

- **Point/monopole**: inject into one cell — radiates isotropically.
- **Directional / dipole**: inject `+s` and `-s` into adjacent cells.
- **Plane wave**: drive an entire row/column with the same `s(t)` (a
  total-field/scattered-field formulation cleanly separates incident from
  scattered field for cross-section measurement, but a driven line plus a PML is
  enough for a first look).

## Heterogeneous and layered media

Promote the constant `c` to a field `c[x]` (or `c[i,j]`). The stencil becomes

```python
r2 = (dt / dx)**2                       # pull c out of the constant
u_next[1:-1] = (2*u_curr[1:-1] - u_prev[1:-1]
                + r2 * c[1:-1]**2 * (u_curr[2:] - 2*u_curr[1:-1] + u_curr[:-2]))
```

- **CFL uses `c_max`**, resolution uses `c_min` (shortest wavelength). Both live
  in the same `c[x]` array.
- **Interfaces** (a jump in `c`) partially reflect and transmit — this is real
  physics, not an artifact. Amplitude reflection at normal incidence is
  `(Z2 - Z1)/(Z2 + Z1)` with impedance `Z = ρc`; if you model only `c` (constant
  density), use `(c2 - c1)/(c2 + c1)` as a check.
- **Smooth gradients** (e.g. a velocity that increases with depth) refract the
  wavefront — the basis of seismic ray bending. Keep the gradient resolved
  (several cells across any change in `c`) to avoid staircase scattering.
- A layered `c[i,j]` reproduces classic seismic layer models; snapshot the field
  to see direct, reflected, and head waves separate.

## Beyond the scalar equation

The scalar solver covers acoustic pressure, out-of-plane (SH) displacement, and a
single scalar EM component. Two important systems are *not* scalar and need
staggered grids — described here at the design level; use a dedicated package for
production work.

### Vector electromagnetics — the Yee grid

Maxwell's curl equations couple **E** and **H**. The classic **Yee (1966) FDTD**
scheme stores E and H components **interleaved in space and time** (a staggered
grid): each E component sits at a cell edge, each H component on a face, and the
two are advanced in a leapfrog half-step apart. This staggering makes the
discrete curl second-order accurate and automatically satisfies the divergence
constraints. Update, per step: advance **H** from the curl of **E**, then advance
**E** from the curl of **H** (plus source/current terms). The CFL bound is the
same `c·dt ≤ dx/√d` form. Material properties enter as per-cell `ε`, `μ`, and
conductivity `σ`. For anything beyond a teaching demo — dispersive materials,
PML for EM, periodic/Bloch boundaries — use `meep`, `gprMax`, or `fdtdz` rather
than hand-rolling the Yee update.

### Elastic waves — velocity-stress staggered grid

Elastic media carry coupled **P (compressional)** and **S (shear)** waves at
different speeds. The standard approach is the **velocity-stress FDTD** scheme:
store particle-velocity and stress-tensor components on a staggered grid and
leapfrog them, with the medium described by density `ρ` and Lamé parameters
`λ, μ`. The CFL must use the **fastest** wave speed `c_p = √((λ+2μ)/ρ)`, while
resolution must resolve the **slowest** (`c_s = √(μ/ρ)`) — S waves are shorter and
set `dx`. This is the workhorse of computational seismology; mature
implementations (SeisSol, SPECFEM, Devito-based solvers) handle the free-surface
condition and topography that a naive stencil gets wrong.
