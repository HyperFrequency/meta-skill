# Fundamental dimensions and dimensionless-number catalogue

## Fundamental dimensions (SI base)

| Dimension | Symbol | SI unit | pint dimensionality |
|---|---|---|---|
| Mass | M | kg | `[mass]` |
| Length | L | m | `[length]` |
| Time | T | s | `[time]` |
| Temperature | Θ | K | `[temperature]` |
| Electric current | I | A | `[current]` |
| Amount of substance | N | mol | `[substance]` |
| Luminous intensity | J | cd | `[luminosity]` |

Everything else is a product of powers of these. Examples: force `M L T⁻²` (N), energy
`M L² T⁻²` (J), pressure `M L⁻¹ T⁻²` (Pa), dynamic viscosity `M L⁻¹ T⁻¹` (Pa·s), kinematic
viscosity `ν = μ/ρ` is `L² T⁻¹`.

## Common dimensionless numbers

| Number | Symbol | Formula | Ratio it measures |
|---|---|---|---|
| Reynolds | Re | ρvL/μ = vL/ν | inertia / viscous force |
| Mach | Ma | v/c | flow speed / speed of sound |
| Prandtl | Pr | ν/α | momentum diffusivity / thermal diffusivity |
| Schmidt | Sc | ν/D | momentum diffusivity / mass diffusivity |
| Péclet (thermal) | Pe | vL/α | advection / thermal diffusion |
| Péclet (mass) | Pe | vL/D | advection / mass diffusion |
| Rayleigh | Ra | gβΔT L³/(να) | buoyancy / diffusive damping |
| Grashof | Gr | gβΔT L³/ν² | buoyancy / viscous force |
| Nusselt | Nu | hL/k | convective / conductive heat transfer |
| Sherwood | Sh | k_c L/D | convective / diffusive mass transfer |
| Froude | Fr | v/√(gL) | inertia / gravity |
| Weber | We | ρv²L/σ | inertia / surface tension |
| Capillary | Ca | μv/σ | viscous / surface tension |
| Knudsen | Kn | λ/L | mean free path / system size |
| Strouhal | St | fL/v | oscillation / mean flow |
| Euler | Eu | Δp/(ρv²) | pressure / inertia |
| Bond | Bo | ρgL²/σ | gravity / surface tension |
| Stokes | Stk | τ_p v/L | particle response time / flow time |

Symbols: `ρ` density, `v` velocity, `L` length scale, `μ` dynamic viscosity, `ν=μ/ρ`
kinematic viscosity, `α` thermal diffusivity, `D` mass diffusivity, `c` sound speed, `g`
gravity, `β` thermal expansion coefficient, `ΔT` temperature difference, `σ` surface tension,
`h`/`k_c` heat/mass transfer coefficients, `k` thermal conductivity, `λ` mean free path,
`f` frequency, `Δp` pressure difference, `τ_p` particle relaxation time.

## Compute helper

```python
def dimensionless_numbers(params):
    """Compute whichever standard numbers the supplied parameters allow.

    params keys (SI): density, velocity, length, viscosity (dynamic, Pa·s),
        thermal_diff (alpha, m^2/s), mass_diff (D, m^2/s), sound_speed (c, m/s),
        gravity (default 9.81), thermal_exp (beta, 1/K), delta_T (K), surf_tension (sigma).
    Returns {name: value} for every number that is fully determined.
    """
    p = params.get
    rho, v, L, mu = p('density'), p('velocity'), p('length'), p('viscosity')
    alpha, D, c = p('thermal_diff'), p('mass_diff'), p('sound_speed')
    g, beta, dT, sigma = p('gravity', 9.81), p('thermal_exp'), p('delta_T'), p('surf_tension')
    nu = mu / rho if (mu and rho) else None

    out = {}
    if rho and v and L and mu:            out['Re'] = rho * v * L / mu
    if v and c:                           out['Ma'] = v / c
    if nu and alpha:                      out['Pr'] = nu / alpha
    if nu and D:                          out['Sc'] = nu / D
    if v and L and alpha:                 out['Pe_thermal'] = v * L / alpha
    if v and L and D:                     out['Pe_mass'] = v * L / D
    if g and beta and dT and L and nu and alpha:
                                          out['Ra'] = g * beta * dT * L**3 / (nu * alpha)
    if g and beta and dT and L and nu:    out['Gr'] = g * beta * dT * L**3 / nu**2
    if v and g and L:                     out['Fr'] = v / (g * L) ** 0.5
    if rho and v and L and sigma:         out['We'] = rho * v**2 * L / sigma
    if mu and v and sigma:                out['Ca'] = mu * v / sigma
    return out
```

## Regime thresholds

Use the computed number to pick the physical regime and, often, the right model.

- **Reynolds (internal pipe flow):** `Re < 2300` laminar · `2300 ≤ Re < 4000` transitional ·
  `Re ≥ 4000` turbulent. (Flat-plate / external transition is nearer `Re ≈ 5×10⁵`; the
  threshold is geometry-dependent — quote the geometry.)
- **Mach:** `Ma < 0.3` effectively incompressible · `0.3–0.8` subsonic compressible ·
  `≈1` transonic · `>1` supersonic · `>5` hypersonic.
- **Péclet:** `Pe ≫ 1` advection-dominated (sharp fronts, upwind schemes, watch numerical
  diffusion) · `Pe ≪ 1` diffusion-dominated (smooth, diffusion sets the timestep).
- **Rayleigh (buoyant convection):** below `Ra_c ≈ 1708` (Rayleigh–Bénard) conduction only;
  above it convection cells appear; higher still → turbulent convection.
- **Knudsen:** `Kn < 0.01` continuum (Navier–Stokes valid) · `0.01–0.1` slip flow ·
  `0.1–10` transitional · `>10` free-molecular (kinetic/DSMC, not continuum).
- **Weber / Capillary:** `We ≪ 1` or `Ca ≪ 1` ⇒ surface tension holds drops/interfaces
  together; large values ⇒ inertia or viscous shear breaks them up (atomization).
- **Froude:** `Fr < 1` subcritical (gravity-controlled, waves travel upstream) · `Fr > 1`
  supercritical.

Because dimensional analysis fixes only the *form* `Π₁ = f(Π₂, …)`, these thresholds are
empirical constants for their problem class — cite the geometry and source when you rely on a
specific cutoff.
