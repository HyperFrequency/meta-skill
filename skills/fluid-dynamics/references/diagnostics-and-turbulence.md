# Diagnostics & Turbulence Statistics

Post-processing for a resolved velocity field `(u, v)` on a uniform grid with
spacing `dx = dy`. All snippets assume the `[j, i]` (row = y, col = x) layout used
by the solvers in `incompressible-solvers.md`.

---

## Vorticity, Strain, and the Q-Criterion

```python
import numpy as np

def velocity_gradients(u, v, dx):
    dudy, dudx = np.gradient(u, dx, dx)     # np.gradient returns d/d(axis0=y), d/d(axis1=x)
    dvdy, dvdx = np.gradient(v, dx, dx)
    return dudx, dudy, dvdx, dvdy

def vorticity(u, v, dx):
    dudx, dudy, dvdx, dvdy = velocity_gradients(u, v, dx)
    return dvdx - dudy                      # ω_z = ∂v/∂x − ∂u/∂y

def q_criterion(u, v, dx):
    """Q = 0.5(||Ω||² − ||S||²); Q>0 marks vortex cores (Hunt et al. 1988)."""
    dudx, dudy, dvdx, dvdy = velocity_gradients(u, v, dx)
    S12 = 0.5 * (dudy + dvdx)               # symmetric (strain rate)
    W12 = 0.5 * (dudy - dvdx)               # antisymmetric (rotation)
    S_norm2 = dudx**2 + dvdy**2 + 2*S12**2
    W_norm2 = 2*W12**2
    return 0.5 * (W_norm2 - S_norm2)
```

Contour `vorticity` to visualise shear layers and shed vortices; threshold
`q_criterion > 0` to isolate coherent vortex cores independent of shear.

---

## Integral Loads: Drag and Lift

For a body in a uniform stream `U∞`, estimate loads without differentiating the
pressure field, using far-field balances. State the assumptions when you report a
number — these are approximations that require the control surfaces to sit in
clean flow.

**Drag by wake momentum deficit** (per unit span). On a plane downstream of the
body where pressure has recovered to freestream:

```python
def drag_wake(u_wake, U_inf, rho, dy):
    """u_wake: u-velocity profile on a downstream plane (1D array across the wake)."""
    return rho * np.sum(u_wake * (U_inf - u_wake)) * dy
```

The drag coefficient is `Cd = D / (0.5 ρ U∞² L)` with `L` the projected frontal
length (cylinder diameter). Resolve the near-wall region well — under-resolution
is the usual cause of a wrong `Cd`.

**Lift by circulation (Kutta-Joukowski)**: `L' = −ρ U∞ Γ`, with circulation
`Γ = ∮ u·dl = ∬ ω dA` over a contour enclosing the body:

```python
def circulation(omega, dx):
    return np.sum(omega) * dx**2            # ∬ ω dA over the integration region
```

---

## Turbulence Statistics

### Reynolds stresses and TKE

Decompose each velocity component into mean + fluctuation, `u = ⟨u⟩ + u'`, using
an ensemble or time series of snapshots. Stack snapshots along a leading axis.

```python
def reynolds_stresses(u_stack, v_stack):
    """u_stack, v_stack: shape (T, Ny, Nx) — T snapshots of the field."""
    up = u_stack - u_stack.mean(axis=0)
    vp = v_stack - v_stack.mean(axis=0)
    Ruu = (up * up).mean(axis=0)            # ⟨u'u'⟩
    Rvv = (vp * vp).mean(axis=0)            # ⟨v'v'⟩
    Ruv = (up * vp).mean(axis=0)            # ⟨u'v'⟩  (turbulent shear stress)
    tke = 0.5 * (Ruu + Rvv)                 # 2D turbulent kinetic energy
    return Ruu, Rvv, Ruv, tke
```

Averaging in time requires statistical stationarity; averaging in a homogeneous
spatial direction (e.g. streamwise in a channel) is often more robust for short
records.

### Kinetic-energy spectrum

For an approximately homogeneous, **periodic** field, shell-average the spectral
energy density. Do not apply this to a bounded cavity or a developing wake — the
FFT assumes periodicity, and a non-periodic field leaks energy across all
wavenumbers.

```python
def energy_spectrum(u, v):
    """Radially-averaged E(k) for a periodic 2D field on a square grid."""
    N = u.shape[0]
    uh = np.fft.fft2(u) / N**2
    vh = np.fft.fft2(v) / N**2
    e = 0.5 * (np.abs(uh)**2 + np.abs(vh)**2)     # energy per Fourier mode
    kx = np.fft.fftfreq(N, d=1.0/N)
    KX, KY = np.meshgrid(kx, kx)
    kmag = np.sqrt(KX**2 + KY**2).astype(int)
    kbins = np.arange(0, N // 2)
    Ek = np.array([e[(kmag == k)].sum() for k in kbins])
    return kbins, Ek
```

Check for the expected scaling on a log-log plot: `E(k) ∝ k^(−5/3)` in a 3D
inertial range (Kolmogorov), or `k^(−3)` in the 2D enstrophy-cascade range. A
spectrum that flattens or rises at high `k` signals under-resolution or aliasing
— refine the grid or dealias.

---

## Flow Visualisation

- **Streamlines** — `plt.streamplot(X, Y, u, v)` for instantaneous topology;
  contour the streamfunction `ψ` for a cleaner steady picture.
- **Vorticity field** — `plt.contourf(X, Y, vorticity(u, v, dx), cmap='RdBu_r')`
  with a symmetric colour range about zero.
- **Vector field** — `plt.quiver(...)`, subsampling the grid (`[::s, ::s]`) so
  arrows stay legible.

For publication-quality figures, hand the fields to the `matplotlib` skill.
