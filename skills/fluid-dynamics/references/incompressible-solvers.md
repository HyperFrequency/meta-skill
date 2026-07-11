# Incompressible Solvers

Runnable NumPy/SciPy solvers for 2D incompressible flow. The workhorse is the
vorticity-streamfunction formulation; primitive-variable projection is included
for cases where you need pressure or open boundaries. Read the stability and
validation notes in `validation-and-troubleshooting.md` before trusting output.

Index convention throughout: arrays are `[j, i]` with `j` the y-index (row) and
`i` the x-index (column), grid spacing `dx = dy`.

---

## 1. Lid-Driven Cavity — Full Run with Plots

The core loop is in the SKILL.md quick start. Here it is wrapped with
post-processing. The domain is the unit square; the top wall (lid) moves at
`U_lid = 1`, all other walls are no-slip, and `ψ = 0` on every wall.

```python
import numpy as np
import matplotlib.pyplot as plt

def cavity(N=128, Re=100, dt=1e-3, n_steps=40000, poisson_iters=60):
    dx = 1.0 / (N - 1)
    U_lid = 1.0
    omega = np.zeros((N, N))
    psi = np.zeros((N, N))
    assert U_lid * dt / dx < 1.0 and dt / (Re * dx**2) < 0.25

    for step in range(n_steps):
        for _ in range(poisson_iters):                       # ∇²ψ = -ω
            psi[1:-1, 1:-1] = 0.25 * (
                psi[1:-1, 2:] + psi[1:-1, :-2] +
                psi[2:, 1:-1] + psi[:-2, 1:-1] +
                dx**2 * omega[1:-1, 1:-1])

        omega[0, :]  = -2 * psi[1, :]  / dx**2                # bottom wall
        omega[-1, :] = -2 * psi[-2, :] / dx**2 - 2*U_lid/dx   # moving lid
        omega[:, 0]  = -2 * psi[:, 1]  / dx**2                # left wall
        omega[:, -1] = -2 * psi[:, -2] / dx**2                # right wall

        u = np.zeros_like(psi); v = np.zeros_like(psi)
        u[1:-1, 1:-1] =  (psi[2:, 1:-1] - psi[:-2, 1:-1]) / (2*dx)
        v[1:-1, 1:-1] = -(psi[1:-1, 2:] - psi[1:-1, :-2]) / (2*dx)

        adv = (u[1:-1, 1:-1]*(omega[1:-1, 2:] - omega[1:-1, :-2])/(2*dx) +
               v[1:-1, 1:-1]*(omega[2:, 1:-1] - omega[:-2, 1:-1])/(2*dx))
        lap = (omega[1:-1, 2:] + omega[1:-1, :-2] +
               omega[2:, 1:-1] + omega[:-2, 1:-1] - 4*omega[1:-1, 1:-1]) / dx**2
        omega[1:-1, 1:-1] += dt * (-adv + lap / Re)

    return psi, omega, u, v

psi, omega, u, v = cavity()
N = psi.shape[0]
x = np.linspace(0, 1, N); X, Y = np.meshgrid(x, x)

fig, ax = plt.subplots(1, 3, figsize=(18, 5))
ax[0].contour(X, Y, psi, levels=30, cmap='RdBu_r');  ax[0].set_title(r'$\psi$')
ax[1].contourf(X, Y, omega, levels=30, cmap='RdBu_r'); ax[1].set_title(r'$\omega$')
s = 6
ax[2].quiver(X[::s, ::s], Y[::s, ::s], u[::s, ::s], v[::s, ::s])
ax[2].set_title('velocity')
for a in ax: a.set_aspect('equal')
plt.tight_layout(); plt.savefig('cavity.png', dpi=150)
```

### Ghia benchmark overlay

Compare the vertical-centerline `u(x=0.5, y)` against Ghia et al. (1982). Supply
the reference arrays from the paper (Table I) — the qualitative check is a single
primary vortex sitting above and right of centre with an S-shaped centerline
profile that reaches a negative minimum in the lower half.

```python
i_mid = N // 2
u_centerline = u[:, i_mid]          # u along the vertical centerline
plt.plot(u_centerline, x, label='computed')
# plt.plot(u_ghia, y_ghia, 'ko', label='Ghia et al. 1982')  # from the paper
plt.xlabel('u'); plt.ylabel('y'); plt.legend()
```

---

## 2. Poisson Accelerators

The Jacobi sweep above is simple but slow (hundreds of iterations to converge at
`N=128`). Swap in one of these for the `∇²ψ = -ω` solve.

### Successive over-relaxation (SOR), red-black vectorised

```python
def poisson_sor(psi, omega, dx, w=1.8, iters=200):
    """Over-relaxation; optimal w ~ 2/(1+sin(pi/N)), typically 1.7-1.95."""
    for _ in range(iters):
        for color in (0, 1):                       # red-black to vectorise G-S
            m = np.zeros_like(psi, dtype=bool)
            m[1:-1, 1:-1] = ((np.add.outer(np.arange(psi.shape[0]),
                              np.arange(psi.shape[1])) % 2)[1:-1, 1:-1] == color)
            gs = 0.25 * (np.roll(psi, 1, 0) + np.roll(psi, -1, 0) +
                         np.roll(psi, 1, 1) + np.roll(psi, -1, 1) + dx**2 * omega)
            psi[m] = (1 - w) * psi[m] + w * gs[m]
        psi[0, :] = psi[-1, :] = psi[:, 0] = psi[:, -1] = 0.0
    return psi
```

### FFT / discrete-sine-transform (direct, fastest for Dirichlet squares)

For `ψ = 0` on all boundaries the Laplacian diagonalises under the type-I DST, so
one transform pair solves the Poisson equation exactly (no iteration).

```python
from scipy.fft import dstn, idstn

def poisson_dst(rhs_interior, dx):
    """Solve ∇²ψ = rhs on a square with ψ=0 Dirichlet BCs.
    rhs_interior has shape (m, m) = interior nodes; returns interior ψ."""
    m = rhs_interior.shape[0]
    rhs_hat = dstn(rhs_interior, type=1, norm='ortho')
    k = np.arange(1, m + 1)
    lam = (2 * np.cos(k * np.pi / (m + 1)) - 2) / dx**2   # 1D eigenvalues
    psi_hat = rhs_hat / (lam[:, None] + lam[None, :])
    return idstn(psi_hat, type=1, norm='ortho')

# usage inside the time loop:  psi[1:-1,1:-1] = poisson_dst(-omega[1:-1,1:-1], dx)
```

Use the DST solver whenever the streamfunction/pressure BC is homogeneous
Dirichlet on a rectangle — it turns an O(iters·N²) inner loop into a single
O(N² log N) transform and removes Poisson-convergence error entirely.

---

## 3. Plane Poiseuille / Channel Startup

Pressure-driven flow between two no-slip walls has the analytic steady profile
`u(y) = (G / 2ν)(h² − y²)` for half-height `h` and forcing `G = −(1/ρ)dp/dx`.
March the 1D unsteady momentum equation to that steady state — a clean unit test
for your diffusion operator and boundary handling.

```python
def channel_startup(Ny=101, nu=0.01, G=1.0, dt=1e-3, n_steps=20000):
    h = 0.5
    y = np.linspace(-h, h, Ny); dy = y[1] - y[0]
    assert nu * dt / dy**2 < 0.5, "diffusion number too large"
    u = np.zeros(Ny)                                   # no-slip walls: u[0]=u[-1]=0
    for _ in range(n_steps):
        u[1:-1] += dt * (nu * (u[2:] - 2*u[1:-1] + u[:-2]) / dy**2 + G)
    u_exact = (G / (2*nu)) * (h**2 - y**2)
    return y, u, u_exact                               # u should converge to u_exact
```

---

## 4. Flow Past a Bluff Body — Projection + Immersed Boundary

This is a **teaching-grade scaffold**, not a validated wake solver. It uses
Chorin projection on a collocated grid with a Brinkman penalty that drives the
velocity toward zero inside the body. Collocated grids admit pressure-velocity
decoupling (checkerboarding) — for quantitative wake, shedding-frequency, or drag
studies use a staggered grid, a lattice-Boltzmann code, or FEniCS/OpenFOAM.

Structure (each step):

1. **Predictor** — advance velocity with advection + diffusion, ignoring
   pressure: `u* = uⁿ + dt(−(u·∇)u + ν∇²u)`.
2. **Penalty** — add `−(χ/η) u*` where `χ` is the body mask and `η` a small
   permeability, forcing `u* → 0` inside the solid.
3. **Pressure Poisson** — solve `∇²p = (ρ/dt)∇·u*` (use the FFT/SOR solvers above
   with the appropriate BC).
4. **Correction** — project: `uⁿ⁺¹ = u* − (dt/ρ)∇p`, which is divergence-free.

Expected behaviour by Reynolds number (see the regime table in
`validation-and-troubleshooting.md`): attached twin vortices below `Re ≈ 40`,
periodic Von Kármán shedding from `Re ≈ 40–200` at Strouhal number `St ≈ 0.2`,
and a broadband turbulent wake above.

```python
# Body mask for a cylinder of radius R centred at (cx, cy) on an (Ny, Nx) grid:
Y, X = np.meshgrid(np.arange(Ny), np.arange(Nx), indexing='ij')
mask = ((X - cx)**2 + (Y - cy)**2) < R**2   # chi = 1 inside the cylinder
```

Keep the inflow uniform (`u = U∞`), use a convective/Neumann outflow, and free-slip
or far-field top/bottom boundaries far enough away that they do not squeeze the wake.

---

## When to Reach for Something Heavier

- **Periodic-box turbulence** → `fluidsim` (pseudospectral, dealiased, much faster).
- **Curved/complex geometry, boundary layers** → FEniCS (FEM) or OpenFOAM (FVM).
- **Moving/deforming bodies, free surfaces** → lattice Boltzmann or a level-set FVM code.
