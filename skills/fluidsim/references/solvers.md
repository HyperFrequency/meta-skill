# Solvers

Every solver integrates its equations on a **periodic** domain with
pseudospectral methods (Fourier space + FFT). Pick the solver whose equations
match your physics; the rest of the workflow is identical.

Two import styles work everywhere:

```python
from fluidsim.solvers.ns2d.solver import Simul          # explicit
# or
import fluidsim
Simul = fluidsim.import_simul_class_from_key("ns2d")     # dynamic, by key
```

## Catalogue

### 2D incompressible Navier-Stokes — `ns2d`

- Module: `fluidsim.solvers.ns2d.solver`
- For: 2D turbulence, vortex dynamics, quick prototyping and validation.
- Physics: dual energy/enstrophy cascades, vorticity transport.

### 3D incompressible Navier-Stokes — `ns3d`

- Module: `fluidsim.solvers.ns3d.solver`
- For: 3D turbulence, realistic DNS, high-resolution parallel runs.
- Physics: forward energy cascade; the natural target for MPI.

### Stratified (Boussinesq) — `ns2d.strat`, `ns3d.strat`

- Modules: `fluidsim.solvers.ns2d.strat.solver`, `fluidsim.solvers.ns3d.strat.solver`
- For: oceanic/atmospheric internal-wave and buoyancy-driven flows.
- Physics: Boussinesq approximation, constant Brunt-Vaisala frequency.
- Key parameter: `params.N` (stratification / buoyancy frequency). Adds a
  buoyancy field to the state.

### One-layer shallow water — `sw1l`

- Module: `fluidsim.solvers.sw1l.solver`
- For: geophysical flows, rotating systems, geostrophic-balance studies.
- Key parameters: `params.f` (Coriolis parameter), `params.c2` (squared
  gravity-wave phase speed).

### Elastic plate (Foppl-von Karman) — `fvk`

- Module: `fluidsim.solvers.fvk.solver`
- For: elastic-plate wave turbulence and fluid-structure studies.

## Selection guide

1. 2D turbulence or fast iteration -> `ns2d`.
2. Realistic 3D flow / DNS -> `ns3d`.
3. Density stratification -> `ns2d.strat` or `ns3d.strat`.
4. Rotating geophysical / shallow water -> `sw1l`.
5. Elastic plate -> `fvk`.

## Modified variants

Several solvers ship variants that add physics such as extra forcing terms,
passive scalars, or alternate boundary treatments. Browse the `fluidsim.solvers`
package for the complete set, and confirm each variant's state variables with
`sim.state.keys_state_phys` after instantiation rather than assuming names.
