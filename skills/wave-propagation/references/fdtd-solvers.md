# FDTD Solvers (1D / 2D / 3D)

Explicit second-order finite-difference time-domain solvers for the scalar wave
equation `∂²u/∂t² = c²∇²u + s`. All three share the same leapfrog time update;
they differ only in the Laplacian stencil and the CFL constant. Keep three time
levels (`u_prev`, `u_curr`, `u_next`) and roll them each step.

## 1D solver with a Ricker source and Mur absorbing boundary

```python
import numpy as np
import matplotlib.pyplot as plt

def ricker(t, f, t0=None):
    """Ricker (Mexican-hat) wavelet, peak frequency f, centered at t0."""
    t0 = 1.0 / f if t0 is None else t0
    a = (np.pi * f * (t - t0))**2
    return (1 - 2*a) * np.exp(-a)

def wave_1d(Nx=1000, Nt=2000, c=1.0, dx=0.01, CFL=0.9,
            source_pos=0.2, source_freq=5.0, bc="absorbing"):
    dt = CFL * dx / c                       # 1D CFL: c*dt/dx <= 1
    r2 = (c * dt / dx)**2
    x = np.arange(Nx) * dx
    src = int(source_pos / dx)
    print(f"Courant c*dt/dx = {c*dt/dx:.3f}  dt = {dt:.5g}")

    u_prev = np.zeros(Nx)
    u_curr = np.zeros(Nx)
    snapshots = []

    for n in range(Nt):
        t = n * dt
        u_next = np.empty_like(u_curr)
        u_next[1:-1] = (2*u_curr[1:-1] - u_prev[1:-1]
                        + r2 * (u_curr[2:] - 2*u_curr[1:-1] + u_curr[:-2]))

        # Source enters the discretized d^2u/dt^2, so scale by dt^2
        u_next[src] += dt**2 * ricker(t, source_freq)

        if bc == "absorbing":                      # first-order Mur
            m = (c*dt - dx) / (c*dt + dx)
            u_next[0]  = u_curr[1]  + m * (u_next[1]  - u_curr[0])
            u_next[-1] = u_curr[-2] + m * (u_next[-2] - u_curr[-1])
        elif bc == "fixed":                        # Dirichlet
            u_next[0] = u_next[-1] = 0.0
        elif bc == "free":                          # Neumann (zero gradient)
            u_next[0], u_next[-1] = u_next[1], u_next[-2]
        elif bc == "periodic":
            u_next[0], u_next[-1] = u_next[-2], u_next[1]

        u_prev, u_curr = u_curr, u_next             # roll (no copies needed)

        if n % (Nt // 10) == 0:
            snapshots.append((t, u_curr.copy()))
    return x, snapshots

x, snaps = wave_1d()
fig, ax = plt.subplots(figsize=(11, 6))
for t, u in snaps:
    ax.plot(x, u + t*0.3, lw=0.8, label=f"t={t:.3f}")   # waterfall offset
ax.set(xlabel="x", ylabel="u (offset by t)",
       title="1D wave, Ricker source, Mur ABC")
ax.legend(ncol=2, fontsize=8); ax.grid(alpha=0.3)
fig.savefig("wave_1d.png", dpi=150, bbox_inches="tight")
```

Note the rolling `u_prev, u_curr = u_curr, u_next` — no `.copy()` in the hot loop
because each array becomes owned by exactly one name. Copy only the snapshots you
retain.

## 2D solver (five-point Laplacian)

```python
def wave_2d(Nx=200, Ny=200, Nt=500, c=1.0, dx=0.01, CFL=0.7,
            freq=10.0, t0=0.1):
    dt = CFL * dx / (c * np.sqrt(2))        # 2D CFL: c*dt/dx <= 1/sqrt(2)
    r2 = (c * dt / dx)**2
    si, sj = Nx // 4, Ny // 2
    u_prev = np.zeros((Nx, Ny))
    u_curr = np.zeros((Nx, Ny))
    snapshots = []

    for n in range(Nt):
        t = n * dt
        u_next = np.zeros_like(u_curr)
        u_next[1:-1, 1:-1] = (
            2*u_curr[1:-1, 1:-1] - u_prev[1:-1, 1:-1]
            + r2 * (u_curr[2:, 1:-1] + u_curr[:-2, 1:-1]
                    + u_curr[1:-1, 2:] + u_curr[1:-1, :-2]
                    - 4*u_curr[1:-1, 1:-1]))
        u_next[si, sj] += dt**2 * ricker(t, freq, t0)

        # Simple first-order absorbing edges (copy inward neighbor)
        u_next[0, :], u_next[-1, :] = u_next[1, :], u_next[-2, :]
        u_next[:, 0], u_next[:, -1] = u_next[:, 1], u_next[:, -2]

        u_prev, u_curr = u_curr, u_next
        if n % (Nt // 6) == 0:
            snapshots.append((t, u_curr.copy()))
    return snapshots

snaps = wave_2d()
fig, axes = plt.subplots(2, 3, figsize=(15, 9))
for ax, (t, u) in zip(axes.flat, snaps):
    ax.imshow(u.T, cmap="RdBu_r", vmin=-0.01, vmax=0.01,
              origin="lower", extent=[0, 2, 0, 2])
    ax.set_title(f"t = {t:.3f}")
fig.suptitle("2D wave propagation"); fig.tight_layout()
fig.savefig("wave_2d.png", dpi=150, bbox_inches="tight")
```

The `u_next[1,:]`-copy edges are a cheap absorber that works well only at
near-normal incidence. For clean open-domain 2D/3D runs, wrap the interior in a
PML (see `boundary-conditions.md`).

## 3D solver (seven-point Laplacian)

Same recipe; the CFL constant drops to `1/√3` and the Laplacian gains a third
axis. Memory is the constraint — three `float64` grids of `N³` cost `24·N³`
bytes (a 300³ run ≈ 0.65 GB per array).

```python
def wave_3d(N=120, Nt=200, c=1.0, dx=0.02, CFL=0.6, freq=8.0, t0=0.1):
    dt = CFL * dx / (c * np.sqrt(3))        # 3D CFL: c*dt/dx <= 1/sqrt(3)
    r2 = (c * dt / dx)**2
    s = (N // 2, N // 2, N // 2)
    u_prev = np.zeros((N, N, N))
    u_curr = np.zeros((N, N, N))
    for n in range(Nt):
        u_next = np.zeros_like(u_curr)
        lap = (u_curr[2:, 1:-1, 1:-1] + u_curr[:-2, 1:-1, 1:-1]
               + u_curr[1:-1, 2:, 1:-1] + u_curr[1:-1, :-2, 1:-1]
               + u_curr[1:-1, 1:-1, 2:] + u_curr[1:-1, 1:-1, :-2]
               - 6*u_curr[1:-1, 1:-1, 1:-1])
        u_next[1:-1, 1:-1, 1:-1] = (2*u_curr[1:-1, 1:-1, 1:-1]
                                    - u_prev[1:-1, 1:-1, 1:-1] + r2*lap)
        u_next[s] += dt**2 * ricker(n*dt, freq, t0)
        u_prev, u_curr = u_curr, u_next
    return u_curr
```

## Vectorization and performance

- The stencils above are already vectorized numpy slices — the loop is only over
  time. This is the right first implementation.
- For large 2D/3D grids, `scipy.ndimage.laplace(u)` computes the discrete
  Laplacian in one call (`u_next[...] += r2 * laplace(u_curr)`), often faster and
  clearer than manual slicing.
- If numpy is too slow, the same explicit stencil vectorizes cleanly onto
  `numba.@njit`, `cupy` (drop-in on GPU), or `jax` (with `jax.lax.scan` over
  time). The physics and CFL bound are unchanged.

## Energy check (your best sanity test)

Discrete energy `E = Σ[ (u_next-u_curr)²/(2dt²) + c²(∇u)²/2 ]·dx^d`. With
lossless reflecting or periodic boundaries `E` should be conserved to a few
percent over the run; with absorbing boundaries it should decay monotonically as
the wave exits. Growth in `E` means the CFL is violated.
