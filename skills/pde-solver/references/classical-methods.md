# Classical Numerical Methods for PDEs

Deterministic discretizations: finite differences, Fourier/Chebyshev spectral methods,
and the Method of Lines. All examples use `numpy`, `scipy.sparse`, and `scipy.integrate`.

---

## 1. Finite Differences

Replace derivatives with difference stencils on a uniform grid. Second derivative:
`u''(x_i) ≈ (u_{i+1} − 2 u_i + u_{i−1}) / Δx²`.

### 1D heat equation — explicit (forward) Euler

`∂u/∂t = α ∂²u/∂x²`. Simplest scheme; stable only when `r = αΔt/Δx² ≤ 0.5`.

```python
import numpy as np

def heat_1d_explicit(L=1.0, T=0.5, alpha=0.01, Nx=100, Nt=5000,
                     u_left=0.0, u_right=0.0, u0=None):
    dx, dt = L / Nx, T / Nt
    r = alpha * dt / dx**2
    if r > 0.5:
        raise ValueError(f"CFL violated: r={r:.4f} > 0.5. Reduce dt or coarsen space.")
    x = np.linspace(0, L, Nx + 1)
    u = u0(x) if u0 else np.sin(np.pi * x / L)
    u[0], u[-1] = u_left, u_right
    for _ in range(Nt):
        u_new = u.copy()
        u_new[1:-1] = u[1:-1] + r * (u[2:] - 2 * u[1:-1] + u[:-2])
        u_new[0], u_new[-1] = u_left, u_right      # re-enforce Dirichlet BCs
        u = u_new
    return x, u
```

### 1D heat equation — Crank–Nicolson (implicit, unconditionally stable)

Average the explicit and implicit second-difference operators. Second-order accurate in
time, no CFL limit. Factor the left-hand matrix once with `splu` and reuse it every step.

```python
from scipy.sparse import diags, identity
from scipy.sparse.linalg import splu

def heat_1d_crank_nicolson(L=1.0, T=0.5, alpha=0.01, Nx=100, Nt=500):
    dx, dt = L / Nx, T / Nt
    r = alpha * dt / dx**2                          # any r is stable
    x = np.linspace(0, L, Nx + 1)
    u = np.sin(np.pi * x / L)
    A = diags([1, -2, 1], [-1, 0, 1], shape=(Nx - 1, Nx - 1))   # interior nodes
    I = identity(Nx - 1)
    left  = (I - 0.5 * r * A).tocsc()
    right = (I + 0.5 * r * A)
    solve = splu(left)                              # one LU factorization
    ui = u[1:-1].copy()                             # homogeneous Dirichlet ends (u=0)
    for _ in range(Nt):
        ui = solve.solve(right @ ui)
    u[1:-1] = ui
    return x, u
```

For **nonzero Dirichlet** BCs, add the boundary contribution vector `b` (the stencil
terms that reach a fixed boundary node) to the right-hand side each step. Pure **implicit
(backward) Euler** is the same pattern with `left = I - r*A`, `right = I` — first order in
time but rock-solid for stiff/diffusive problems.

### 2D Poisson — direct sparse solve via Kronecker products

`∇²u = f(x,y)` on a rectangle with Dirichlet BCs. Build the 2D Laplacian from 1D operators
with `kron`, then solve the sparse linear system once.

```python
import numpy as np
from scipy.sparse import diags, kron, eye
from scipy.sparse.linalg import spsolve

def poisson_2d(Nx=50, Ny=50, Lx=1.0, Ly=1.0, source=None):
    dx, dy = Lx / Nx, Ly / Ny
    nx, ny = Nx - 1, Ny - 1                          # interior counts
    Dxx = diags([1, -2, 1], [-1, 0, 1], shape=(nx, nx)) / dx**2
    Dyy = diags([1, -2, 1], [-1, 0, 1], shape=(ny, ny)) / dy**2
    L = kron(eye(ny), Dxx) + kron(Dyy, eye(nx))     # discrete Laplacian
    x, y = np.linspace(0, Lx, Nx + 1), np.linspace(0, Ly, Ny + 1)
    if source is None:
        source = lambda X, Y: -2 * np.pi**2 * np.sin(np.pi * X) * np.sin(np.pi * Y)
    Xi, Yi = np.meshgrid(x[1:-1], y[1:-1])
    f = source(Xi, Yi).ravel()
    u = np.zeros((Ny + 1, Nx + 1))                  # BCs already zero on the frame
    u[1:-1, 1:-1] = spsolve(L, f).reshape(ny, nx)
    X, Y = np.meshgrid(x, y)
    return X, Y, u
```

### Boundary condition handling

- **Dirichlet** (`u = g`): drop boundary nodes from the unknowns and move their fixed
  values into the right-hand side (as above).
- **Neumann** (`∂u/∂n = g`): introduce a *ghost node* one step outside the domain and
  eliminate it with the BC. For `∂u/∂x = g` at the left (`i=0`), the ghost relation
  `u_{-1} = u_1 − 2Δx·g` folds into the boundary-node equation, giving a modified stencil
  `2(u_1 − u_0)/Δx² − 2g/Δx`. A pure-Neumann problem is singular up to a constant — pin one
  node or add a compatibility constraint.
- **Periodic**: use `np.roll` for the stencil, or a circulant/`diags`-with-wraparound
  operator; spectral methods (below) are usually better for periodic domains.

### Large systems — iterative solvers

`spsolve` (direct LU) is fine up to ~10⁵–10⁶ unknowns. Beyond that, switch to Krylov
iterations with a preconditioner:

```python
from scipy.sparse.linalg import cg, gmres, spilu, LinearOperator
u, info = cg(L, f, rtol=1e-8)            # CG: symmetric positive-definite (Poisson)
# gmres(L, f) for nonsymmetric operators; build an ILU preconditioner via spilu for speed
```

Use **CG** for the symmetric Laplacian, **GMRES/BiCGSTAB** for nonsymmetric operators
(advection–diffusion). An incomplete-LU (`spilu`) preconditioner wrapped in a
`LinearOperator` typically cuts iteration counts by an order of magnitude.

---

## 2. Spectral Methods

Represent the solution in a global basis (Fourier for periodic domains, Chebyshev for
bounded non-periodic domains). Differentiation becomes multiplication in transform space;
accuracy is exponential ("spectral") for smooth solutions.

### 1D wave equation — Fourier pseudospectral

`u_tt = c² u_xx` on a periodic domain. In Fourier space `û_tt = −(ck)² û`. Integrate with a
symplectic (semi-implicit) leapfrog so energy stays bounded.

```python
import numpy as np

def wave_1d_spectral(Lx=2 * np.pi, T=10.0, N=128, c=1.0, dt=0.01):
    dx = Lx / N
    x = np.linspace(0, Lx, N, endpoint=False)       # periodic: drop the last point
    k = np.fft.fftfreq(N, d=dx) * 2 * np.pi          # wavenumbers
    u = np.exp(-((x - Lx / 2) ** 2) / 0.1)           # Gaussian pulse
    u_hat = np.fft.fft(u)
    v_hat = np.zeros_like(u_hat)                     # zero initial velocity
    omega2 = (c * k) ** 2
    for _ in range(int(T / dt)):                     # symplectic Euler / leapfrog
        v_hat -= dt * omega2 * u_hat
        u_hat += dt * v_hat
    return x, np.real(np.fft.ifft(u_hat))
```

Spatial derivatives generally: `u_x = ifft(1j * k * fft(u))`. The leapfrog CFL depends on
the *largest* resolved wavenumber, so halving `Δx` forces a much smaller `Δt`.

### Non-periodic domains — Chebyshev

For Dirichlet/Neumann BCs on `[−1, 1]`, use a Chebyshev collocation (differentiation)
matrix `D` on the Chebyshev–Gauss–Lobatto nodes `x_j = cos(jπ/N)`; the Laplacian is `D @ D`
with BC rows replaced. Chebyshev keeps spectral accuracy without requiring periodicity.

### Aliasing (nonlinear terms)

Products in physical space alias high modes back into the resolved band. For nonlinear PDEs
(Burgers, Navier–Stokes) apply the **2/3 dealiasing rule**: zero the top third of the
spectrum after each nonlinear product, or pad by 3/2 before transforming.

---

## 3. Method of Lines (MOL)

Discretize **space only** with finite differences, leaving a coupled system of ODEs
`du/dt = f(t, u)`, then hand it to an adaptive ODE integrator. This decouples spatial
accuracy from time-step stability — the integrator picks `Δt` for you.

```python
import numpy as np
from scipy.integrate import solve_ivp

def heat_1d_mol(L=1.0, alpha=0.01, Nx=100, T=0.5):
    dx = L / Nx
    x = np.linspace(0, L, Nx + 1)
    def rhs(t, ui):                                  # ui = interior nodes only
        u = np.zeros(Nx + 1)
        u[1:-1] = ui                                 # Dirichlet: u[0]=u[-1]=0
        return alpha * (u[2:] - 2 * u[1:-1] + u[:-2]) / dx**2
    u0 = np.sin(np.pi * x / L)
    sol = solve_ivp(rhs, (0, T), u0[1:-1], method="BDF",
                    rtol=1e-8, atol=1e-10, t_eval=np.linspace(0, T, 100))
    return x, sol
```

- Diffusion-discretized systems are **stiff**; use an implicit integrator — `method="BDF"`
  or `method="Radau"` — not `RK45`, or the explicit method will crawl at a CFL-limited
  step. Advection-dominated (hyperbolic) systems are non-stiff; `RK45` is fine.
- MOL is the best general-purpose approach for 1D/2D transient PDEs on simple grids: no
  hand-derived CFL condition, adaptive error control, and easy switching of the RHS.
- For 2D, ravel the grid into a vector and provide the 2D Laplacian action inside `rhs`
  (or pass a sparse `jac` / `LinearOperator` so the implicit solver factors it efficiently).

---

## Related capability boundaries

- Turbulent / high-Reynolds Navier–Stokes on periodic domains is a specialist regime — see
  the `fluid-dynamics` skill (pseudospectral DNS, `fluidsim`).
- Complex, unstructured, or curved geometries need finite elements (FEniCS/`dolfinx`),
  which these structured-grid methods do not cover.
- Symbolic/analytical solutions and manufactured-solution derivations belong in `sympy`.
