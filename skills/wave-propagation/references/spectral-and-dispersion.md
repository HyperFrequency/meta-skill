# Pseudospectral Solver & Numerical Dispersion

Two related topics: (1) an FFT-based spatial solver that is nearly exact in space
on periodic domains, and (2) how to *measure* the dispersion error of any scheme
and how to keep it small.

## Pseudospectral solver (periodic domains)

Replace the finite-difference Laplacian with a spectral one: in Fourier space
`∇² → -k²`, so a spatial derivative becomes exact to machine precision for a
band-limited periodic field. Only the time integration remains approximate.

For `∂²u/∂t² = c²∇²u`, transform each mode to the harmonic oscillator
`ü_hat = -(c k)² u_hat` and integrate with a symplectic (semi-implicit
Euler / leapfrog-type) step, which conserves a shadow energy and does not drift:

```python
import numpy as np

def wave_spectral(N=256, L=2*np.pi, T=10.0, c=1.0, dt=0.01):
    x = np.linspace(0, L, N, endpoint=False)      # periodic grid (no endpoint)
    k = 2*np.pi * np.fft.fftfreq(N, d=L/N)         # angular wavenumbers
    omega2 = (c * k)**2

    u = np.exp(-((x - L/2)**2) / 0.05)             # initial Gaussian pulse
    u_hat = np.fft.fft(u)
    v_hat = np.zeros(N, dtype=complex)             # du/dt = 0 initially

    # Stability of this symplectic step: dt < 2 / (c * k_max), k_max = pi*N/L
    assert dt < 2.0 / (c * np.abs(k).max()), "reduce dt (spectral CFL)"

    Nt = int(T / dt)
    snapshots = [(0.0, u.copy())]
    for n in range(Nt):
        v_hat -= dt * omega2 * u_hat               # update velocity...
        u_hat += dt * v_hat                         # ...then position (symplectic)
        if (n + 1) % (Nt // 8) == 0:
            snapshots.append(((n+1)*dt, np.real(np.fft.ifft(u_hat))))
    return x, snapshots
```

Notes:

- **Periodicity is mandatory.** The FFT assumes the field wraps; a non-periodic
  field aliases and rings (Gibbs). To fake an open domain, add a sponge/damping
  zone or window the field near the edges.
- **Spatial accuracy is spectral** (exponential in `N`) for smooth fields, so you
  need far fewer points per wavelength than FDTD — often 2–4 rather than 10–20.
  The error budget is then dominated by the time step.
- For higher-order time accuracy use velocity-Verlet or an RK4 on the
  `(u_hat, v_hat)` pair; the spectral CFL bound `dt < 2/(c·k_max)` still applies.
- For non-periodic bounded domains, the spectral analogue is a **Chebyshev**
  collocation solver (`numpy.polynomial.chebyshev` / a differentiation matrix),
  which admits real boundary conditions but has a much stricter `dt ~ O(1/N²)`.

## Measuring the numerical dispersion relation ω(k)

Every discrete scheme propagates different wavenumbers at slightly wrong speeds —
**numerical dispersion**. Measure it directly: record the field on a line over
time to build a `(Nt, Nx)` array `u(t, x)`, take a 2D FFT, and the energy in the
`(k, ω)` plane traces the scheme's actual dispersion curve. Compare it to the
exact `ω = c|k|`.

```python
import matplotlib.pyplot as plt

def measure_dispersion(field_tx, dx, dt):
    """field_tx: array shaped (Nt, Nx) of the field sampled along a line."""
    Nt, Nx = field_tx.shape
    power = np.abs(np.fft.fftshift(np.fft.fft2(field_tx)))**2
    k     = 2*np.pi * np.fft.fftshift(np.fft.fftfreq(Nx, d=dx))
    omega = 2*np.pi * np.fft.fftshift(np.fft.fftfreq(Nt, d=dt))

    plt.figure(figsize=(8, 6))
    plt.pcolormesh(k, omega, np.log10(power + 1e-20), cmap="hot", shading="auto")
    plt.plot(k, np.abs(k), "w--", lw=1, label="exact  ω = c|k|")   # c = 1 here
    plt.xlabel("wavenumber k [rad/m]"); plt.ylabel("frequency ω [rad/s]")
    plt.title("Numerical dispersion relation"); plt.legend()
    plt.colorbar(label="log10 |FFT|²")
    plt.savefig("dispersion.png", dpi=150, bbox_inches="tight")
```

The measured ridge sags below the exact line at high `k`: those short-wavelength
modes travel too slowly on the grid. That deviation *is* the dispersion error.

## Controlling dispersion: points per wavelength

For second-order FDTD the phase-velocity error scales with `(k·dx)²`. The
practical rule:

| Points per wavelength `λ/dx` | Phase-speed error (2nd-order FDTD) | Use for                     |
| ---------------------------- | ---------------------------------- | --------------------------- |
| ~5                           | several % — visibly wrong          | quick look only             |
| 10                           | ~1%                                | typical engineering runs    |
| 20                           | ~0.3%                              | long-distance propagation   |
| spectral                     | machine precision (space)          | when periodicity allows     |

Compute the requirement from the *shortest* wavelength present:
`λ_min = c_min / f_max`, then `dx ≤ λ_min / 10`. Long propagation distances
accumulate phase error, so bump toward 20 when the wave must travel many
wavelengths. Higher-order stencils (fourth-order in space) relax the requirement
at the cost of wider stencils and more careful boundaries.
