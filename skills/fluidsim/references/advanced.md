# Advanced Features

## Forcing

Forcing injects energy to sustain turbulence instead of letting it decay.

### Time-correlated random (`tcrandom`) — most common

```python
params.forcing.enable = True
params.forcing.type = "tcrandom"
params.forcing.nkmin_forcing = 2      # forced wavenumber band
params.forcing.nkmax_forcing = 5
params.forcing.forcing_rate = 1.0     # energy injection rate
params.forcing.tcrandom_time_correlation = 1.0   # correlation time
```

### Proportional

Maintains a target spectral shape:

```python
params.forcing.type = "proportional"
params.forcing.forcing_rate = 1.0
```

### In-script forcing

Override the forcing computation with your own function in Fourier space:

```python
params.forcing.enable = True
params.forcing.type = "in_script"
sim = Simul(params)

def compute_forcing_fft(sim):
    fx = sim.oper.create_arrayK(value=0.)
    fy = sim.oper.create_arrayK(value=0.)
    fx[10, 10] = 1.0 + 0.5j      # force specific modes
    return fx, fy

sim.forcing.forcing_maker.compute_forcing_fft = lambda: compute_forcing_fft(sim)
sim.time_stepping.start()
```

Exact hook names on `forcing_maker` can vary by version — confirm against the
installed source before relying on the override.

## In-script initial conditions

Write physical arrays, then sync the spectral state (see also
`references/parameters.md`). Field names are solver-specific — check
`sim.state.keys_state_phys`.

```python
from math import pi
import numpy as np

params.init_fields.type = "in_script"
sim = Simul(params)

X, Y = sim.oper.get_XY_loc()
vx = sim.state.state_phys.get_var("vx")
vy = sim.state.state_phys.get_var("vy")
vx[:] = np.sin(X) * np.cos(Y)         # Taylor-Green
vy[:] = -np.cos(X) * np.sin(Y)

sim.state.statespect_from_statephys()  # phys -> spect, required
sim.time_stepping.start()
```

Stratified example — a Gaussian buoyancy anomaly:

```python
from fluidsim.solvers.ns2d.strat.solver import Simul
params = Simul.create_default_params()
params.N = 1.0
params.init_fields.type = "in_script"
sim = Simul(params)

X, Y = sim.oper.get_XY_loc()
b = sim.state.state_phys.get_var("b")   # buoyancy
b[:] = np.exp(-((X - pi)**2 + (Y - pi)**2) / (2 * 0.5**2))

sim.state.statespect_from_statephys()
sim.time_stepping.start()
```

## MPI parallelization

Install with `[fft,mpi]`, then run the script under `mpirun`:

```bash
mpirun -np 8 python simulation_script.py
```

FluidSim detects MPI and decomposes the domain automatically — no code changes.
Output is written from rank 0, and analysis scripts read the results the same way
for serial and parallel runs. Reserve MPI for large 3D (`ns3d`) cases:

```python
params.oper.nx = params.oper.ny = params.oper.nz = 512
# mpirun -np 64 python script.py
```

## Parametric sweeps

```python
from fluidsim.solvers.ns2d.solver import Simul

for nu in [1e-3, 5e-4, 1e-4]:
    for nx in [128, 256, 512]:
        params = Simul.create_default_params()
        params.oper.nx = params.oper.ny = nx
        params.nu_2 = nu
        params.time_stepping.t_end = 10.0
        params.output.sub_directory = f"nu{nu}_nx{nx}"
        sim = Simul(params)
        sim.time_stepping.start()
```

For clusters, generate one script per point and submit each with a
`fluiddyn.clusters` helper (see `references/workflow.md`). Aggregate results with
the pattern in `references/output-analysis.md`.

## Custom solvers

Subclass an existing solver to add physics — new parameters and extra tendency
terms:

```python
from fluidsim.solvers.ns2d.solver import Simul as SimulNS2D

class SimulCustom(SimulNS2D):
    @staticmethod
    def _complete_params_with_default(params):
        SimulNS2D._complete_params_with_default(params)
        params._set_child("custom", {"param1": 0.0})

    def tendencies_nonlin(self, state_spect=None):
        tendencies = super().tendencies_nonlin(state_spect)
        # add custom terms to tendencies here
        return tendencies

params = SimulCustom.create_default_params()
sim = SimulCustom(params)
sim.time_stepping.start()
```

## Checkpoint and restart

Snapshots saved via `periods_save.phys_fields` double as checkpoints. Resume by
initializing from one:

```python
params = Simul.create_default_params()
params.init_fields.type = "from_file"
params.init_fields.from_file.path = "sim_dir/state_phys_t5.000.h5"
params.time_stepping.t_end = 20.0
sim = Simul(params)
sim.time_stepping.start()
```

## Performance tuning

- Disable unused outputs: set their `periods_save` to `0`.
- Save fields less often for long runs (`periods_save.phys_fields = 10.0`).
- Pin an FFT backend via `FLUIDSIM_TYPE_FFT2D` / `FLUIDSIM_TYPE_FFT3D`
  (e.g. `fft2d.with_fftw`).
- Use adaptive stepping (`USE_CFL = True`) with a `type_time_scheme` such as
  `"RK4"`.
