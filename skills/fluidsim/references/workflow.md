# Simulation Workflow

## The five steps

### 1. Import a solver

```python
from fluidsim.solvers.ns2d.solver import Simul
# or dynamically by key:
import fluidsim
Simul = fluidsim.import_simul_class_from_key("ns2d")
```

### 2. Build default parameters

```python
params = Simul.create_default_params()
```

Returns a hierarchical `Parameters` object with every setting the chosen solver
understands, pre-filled with defaults.

### 3. Configure

```python
from math import pi

# Domain and resolution
params.oper.nx = params.oper.ny = 256
params.oper.Lx = params.oper.Ly = 2 * pi

# Physics
params.nu_2 = 1e-3                      # Laplacian viscosity

# Time stepping
params.time_stepping.t_end = 10.0
params.time_stepping.USE_CFL = True     # adaptive dt (recommended)

# Initial condition
params.init_fields.type = "noise"       # dipole / vortex / from_file / in_script

# Output cadence
params.output.periods_save.phys_fields = 1.0
params.output.periods_save.spectra = 0.5
params.output.periods_save.spatial_means = 0.1
```

The `Parameters` object raises `AttributeError` on any unknown attribute, so a
misspelled key fails loudly instead of being silently ignored (the usual failure
mode of text-config CFD codes).

### 4. Instantiate

```python
sim = Simul(params)
```

Builds the FFT operators, state variables, output handlers, and time-stepping
scheme.

### 5. Run

```python
sim.time_stepping.start()   # integrates until t_end (or it_end)
```

### 6. Analyze (during or after)

```python
sim.output.phys_fields.plot()        # default field
sim.output.spatial_means.plot()
sim.output.spectra.plot1d()
sim.output.spectra.plot2d()
```

## Loading a saved simulation

Fast, read-only load for plotting/analysis (does not rebuild full state):

```python
from fluidsim import load_sim_for_plot
sim = load_sim_for_plot("path/to/sim_dir")
sim.output.phys_fields.plot()
```

Full-state load, e.g. to continue integrating:

```python
from fluidsim import load_state_phys_file
sim = load_state_phys_file("path/to/sim_dir/state_phys_t10.000.h5")
sim.time_stepping.start()
```

## Restart from a saved state

```python
params = Simul.create_default_params()
params.init_fields.type = "from_file"
params.init_fields.from_file.path = "path/to/sim_dir/state_phys_t5.000.h5"
params.time_stepping.t_end = 20.0        # extend the run

sim = Simul(params)
sim.time_stepping.start()
```

## Cluster submission

FluidDyn ships helpers for HPC schedulers. The exact class is site-specific;
below is the pattern (here a LEGI-lab cluster) — swap in the class for your site.

```python
from fluiddyn.clusters.legi import Calcul8 as Cluster

cluster = Cluster()
cluster.submit_script(
    "my_simulation.py",
    name_run="my_job",
    nb_nodes=4,
    nb_cores_per_node=24,
    walltime="24:00:00",
)
```

The submitted script contains the standard steps (import, configure, run).

## Complete example

```python
from fluidsim.solvers.ns2d.solver import Simul
from math import pi

params = Simul.create_default_params()
params.oper.nx = params.oper.ny = 256
params.oper.Lx = params.oper.Ly = 2 * pi
params.nu_2 = 1e-3
params.time_stepping.t_end = 10.0
params.init_fields.type = "dipole"
params.output.periods_save.phys_fields = 1.0

sim = Simul(params)
sim.time_stepping.start()

sim.output.phys_fields.plot()
sim.output.spatial_means.plot()
```
