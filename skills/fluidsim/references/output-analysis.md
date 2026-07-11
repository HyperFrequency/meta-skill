# Output and Analysis

## What gets written

Each output type saves on its own period (`params.output.periods_save.*`) into
the run directory:

| Output | File(s) | Contents |
|---|---|---|
| Physical fields | `state_phys_t*.h5` | velocity, vorticity, buoyancy, ... at snapshot times |
| Spatial means | `spatial_means.txt` | volume-averaged time series (energy, enstrophy, ...) |
| Spectra | `spectra_*.h5` | energy/enstrophy vs wavenumber |
| Spectral energy budget | `spect_energy_budg_*.h5` | inter-scale energy transfer |

Typical directory layout:

```
sim_dir/
├── params_simul.xml        # parameters used
├── info_solver.xml         # solver metadata
├── stdout.txt              # run log
├── state_phys_t*.h5        # field snapshots
├── spatial_means.txt       # averaged time series
├── spectra_*.h5
└── spect_energy_budg_*.h5
```

## Loading a run

Fast, read-only (for plotting/analysis; does not rebuild full solver state):

```python
from fluidsim import load_sim_for_plot
sim = load_sim_for_plot("sim_dir")
```

Full state (for continuation):

```python
from fluidsim import load_state_phys_file
sim = load_state_phys_file("sim_dir/state_phys_t10.000.h5")
```

## Physical fields

```python
sim.output.phys_fields.plot()          # default field
sim.output.phys_fields.animate()       # animate a field over saved snapshots
sim.output.phys_fields.save()          # manual snapshot
```

Field keys are solver-specific. List them with `sim.state.keys_state_phys`
before passing a key string to `plot()`.

## Spatial means (time series)

```python
sim.output.spatial_means.plot()
data = sim.output.spatial_means.load()   # dict of numpy arrays keyed by quantity
# e.g. data["t"], data["E"] (kinetic energy) — inspect data.keys() for the set
```

Energy evolution:

```python
import matplotlib.pyplot as plt
data = sim.output.spatial_means.load()
plt.plot(data["t"], data["E"])
plt.xlabel("time"); plt.ylabel("energy"); plt.show()
```

## Spectra

```python
sim.output.spectra.plot1d(tmin=5.0, tmax=10.0)   # time-averaged 1D spectrum
sim.output.spectra.plot2d()
```

Fit a power law in the inertial range:

```python
import numpy as np
k, E_k = sim.output.spectra.load1d_mean(tmin=5.0, tmax=10.0)
mask = (k > k_lo) & (k < k_hi)
slope, intercept = np.polyfit(np.log(k[mask]), np.log(E_k[mask]), 1)
```

## Spectral energy budget

```python
sim.output.spect_energy_budg.plot()
```

## Parametric-study aggregation

Collect a scalar metric across many runs:

```python
import os, pandas as pd
from fluidsim import load_sim_for_plot

rows = []
for name in os.listdir("simulations"):
    path = f"simulations/{name}"
    if not os.path.isdir(path):
        continue
    try:
        sim = load_sim_for_plot(path)
        data = sim.output.spatial_means.load()
        rows.append({"nu": sim.params.nu_2,
                     "nx": sim.params.oper.nx,
                     "final_energy": data["E"][-1]})
    except Exception as err:
        print(f"skip {name}: {err}")

results = pd.DataFrame(rows)
```

## External visualization and export

HDF5 field files open directly in **ParaView** or **VisIt** for 3D rendering:

```bash
paraview sim_dir/state_phys_t*.h5
```

Read raw arrays with `h5py` and export to NumPy/CSV:

```python
import h5py, numpy as np
with h5py.File("sim_dir/state_phys_t10.000.h5", "r") as f:
    vx = f["state_phys"]["vx"][:]     # confirm dataset names for your solver
np.save("vx.npy", vx)
```

## Performance monitoring

```python
sim.output.print_stdout.plot_clock_times()   # wall-clock per step
```
