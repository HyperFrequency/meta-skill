---
name: fluidsim
version: 0.1.0
description: >-
  Run high-performance computational fluid dynamics on periodic domains with
  FluidSim, an object-oriented Python framework using pseudospectral (FFT-based)
  solvers. Use when simulating incompressible Navier-Stokes turbulence (2D/3D),
  stratified/Boussinesq flows, one-layer shallow-water/rotating geophysical
  flows, or elastic-plate (Foppl-von Karman) wave turbulence; studying
  energy/enstrophy cascades, vortex dynamics, spectra, or spectral energy
  budgets; running MPI-parallel DNS and parametric sweeps; or post-processing
  FluidSim HDF5 field/spectra output. NOT for wall-bounded, complex-geometry, or
  non-periodic domains (use a finite-volume/element or spectral-element code);
  NOT for compressible/high-Mach, shocks, multiphase, or free-surface flows; NOT
  for RANS/LES engineering, meshing, or CAD workflows; and NOT for plotting or
  post-processing data that did not come from FluidSim (use matplotlib or
  data-analysis).
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: CeCILL (fluidsim)
---

# FluidSim

## Overview

FluidSim is an object-oriented Python framework for high-performance computational fluid dynamics on **periodic domains**, using pseudospectral (FFT-based) methods. Hot loops are compiled with Pythran/Transonic and can be MPI-parallelized, so throughput approaches Fortran/C++ while the interface stays Python.

It ships several solvers (2D/3D Navier-Stokes, stratified Boussinesq, one-layer shallow water, elastic plate), a hierarchical **typo-safe** parameter system, and automatic HDF5/text output with built-in analysis: physical fields, spatial means, spectra, and spectral energy budgets. Use this skill to configure, run, restart, parallelize, and post-process spectral turbulence and geophysical-flow simulations.

## When to Use This Skill

- Simulating incompressible **Navier-Stokes** turbulence in a periodic box (2D `ns2d`, 3D `ns3d`), decaying or forced.
- **Stratified / Boussinesq** flows (`ns2d.strat`, `ns3d.strat`) for internal-wave and buoyancy dynamics (set `params.N`).
- **Shallow-water / rotating** geophysical flows (`sw1l`; set `params.f`, `params.c2`).
- **Elastic-plate** (Foppl-von Karman, `fvk`) wave turbulence.
- Studying energy/enstrophy cascades, vortex dynamics, **spectra**, and **spectral energy budgets**.
- Running **MPI-parallel** high-resolution DNS or parametric sweeps, then loading HDF5 output for analysis.

## When NOT to Use This Skill

- **Non-periodic / wall-bounded / complex geometry** (channels, airfoils, pipes) — Fourier periodicity does not apply; use a finite-volume/element or spectral-element code (OpenFOAM, Nek5000; Dedalus for non-Fourier bases).
- **Compressible / high-Mach, shocks, multiphase, or free-surface** flows.
- **Engineering RANS/LES with turbulence models, meshing, or CAD** workflows.
- Plotting or post-processing **data that did not come from FluidSim** — use `matplotlib` or `data-analysis` directly.

## Install

FFT support is mandatory for the spectral solvers:

```bash
uv pip install "fluidsim[fft]"        # pulls fluidfft + pyfftw
uv pip install "fluidsim[fft,mpi]"    # add MPI (compiles mpi4py locally)
```

Optional output/scratch locations (no API keys or accounts needed):

```bash
export FLUIDSIM_PATH=/path/to/outputs
export FLUIDDYN_PATH_SCRATCH=/path/to/scratch
```

FFT-backend selection and verification: see `references/installation.md`.

## Core workflow

Every run follows the same five steps — pick a solver class, build defaults, edit params, instantiate, start:

```python
from fluidsim.solvers.ns2d.solver import Simul
from math import pi

params = Simul.create_default_params()    # hierarchical, typo-safe
params.oper.nx = params.oper.ny = 256
params.oper.Lx = params.oper.Ly = 2 * pi
params.nu_2 = 1e-3                         # Laplacian viscosity
params.time_stepping.t_end = 10.0
params.time_stepping.USE_CFL = True        # adaptive dt
params.init_fields.type = "noise"
params.output.periods_save.phys_fields = 1.0

sim = Simul(params)
sim.time_stepping.start()

sim.output.phys_fields.plot()              # default field (vorticity for ns2d)
sim.output.spatial_means.plot()
sim.output.spectra.plot1d()
```

Setting an unknown parameter raises `AttributeError` immediately — typos never silently no-op. Restart, dynamic solver import (`fluidsim.import_simul_class_from_key`), and cluster submission: `references/workflow.md`.

## Choosing a solver

| Problem | Key | Import module |
|---|---|---|
| 2D turbulence, fast tests | `ns2d` | `fluidsim.solvers.ns2d.solver` |
| 3D turbulence / DNS | `ns3d` | `fluidsim.solvers.ns3d.solver` |
| Stratified (Boussinesq) | `ns2d.strat`, `ns3d.strat` | `...ns2d.strat.solver` |
| Shallow water, rotating | `sw1l` | `fluidsim.solvers.sw1l.solver` |
| Elastic plate (FvK) | `fvk` | `fluidsim.solvers.fvk.solver` |

Selection guidance and modified variants: `references/solvers.md`.

## Configuring parameters

Params are grouped by concern:

- `params.oper` — grid (`nx`/`ny`/`nz`), box (`Lx`/`Ly`/`Lz`), `coef_dealiasing` (default `2/3`).
- Viscosity — `nu_2` (Laplacian) plus optional hyperviscosity `nu_4`, `nu_8`.
- `params.time_stepping` — `t_end`, `USE_CFL`, `CFL`, `type_time_scheme` (e.g. `"RK4"`, `"RK2"`).
- `params.init_fields.type` — `"noise"`, `"dipole"`, `"from_file"`, `"in_script"`, ...
- `params.output.periods_save.*` — per-output save periods (set `0` to disable).
- `params.forcing` — sustained energy injection.

Use powers-of-two resolutions for FFT speed; the 2/3 dealiasing rule caps the largest resolved wavenumber. Full table: `references/parameters.md`.

## Outputs and analysis

FluidSim writes each output type on its own period: physical fields (`state_phys_t*.h5`), a `spatial_means.txt` time series, `spectra_*.h5`, and `spect_energy_budg_*.h5`. Reload without recomputing:

```python
from fluidsim import load_sim_for_plot

sim = load_sim_for_plot("path/to/sim_dir")
sim.output.spectra.plot1d(tmin=5.0, tmax=10.0)
data = sim.output.spatial_means.load()     # dict of time-series arrays
```

Use `load_state_phys_file(...)` when you need a full state to continue. HDF5 3D fields open directly in ParaView/VisIt. Analysis recipes, spectral fitting, parametric aggregation, and export: `references/output-analysis.md`.

## Advanced

Sustained turbulence via forcing (`params.forcing.type = "tcrandom"`), in-script initial and forcing fields, MPI runs (`mpirun -np N python run.py`), parametric sweeps, checkpoint/restart, custom solvers by subclassing, and performance tuning: `references/advanced.md`.

When you write fields yourself (`init_fields.type = "in_script"`), set the **physical** arrays and then synchronize the **spectral** state that the solver actually integrates — call `sim.state.statespect_from_statephys()` before `start()`. Introspect valid field names with `sim.state.keys_state_phys` / `sim.state.keys_state_spect` rather than guessing key strings.

## Common gotchas

- **Import fails / no FFT** — install the `[fft]` extra; bare `fluidsim` lacks fluidfft.
- **Blowup / NaNs** — `dt` too large or flow under-resolved; enable `USE_CFL`, lower `CFL`, add hyperviscosity `nu_4`, or raise resolution.
- **Odd/prime `nx`** — slow FFTs; prefer 128/256/512/1024.
- **In-script IC has no effect** — you set `state_phys` but never called `sim.state.statespect_from_statephys()`.
- **Wrong field key** — keys are solver/version specific; check `sim.state.keys_state_phys`.

## Reference files

- `references/installation.md` — install extras, FFT backends, env vars, verification.
- `references/solvers.md` — solver catalogue and selection guide.
- `references/workflow.md` — full workflow, restart, dynamic import, clusters.
- `references/parameters.md` — every parameter group with defaults and guidance.
- `references/output-analysis.md` — output types, loading, spectra fitting, export.
- `references/advanced.md` — forcing, in-script fields, MPI, sweeps, custom solvers, tuning.

## Related skills

- `matplotlib` — customize FluidSim's built-in plots and build publication figures.
- `dask` — parallelize post-processing across many output directories.
- Upstream docs: https://fluidsim.readthedocs.io/
