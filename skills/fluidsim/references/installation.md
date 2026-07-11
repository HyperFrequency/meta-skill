# Installation and Environment

## Requirements

- Python >= 3.9, ideally in a fresh virtual environment.
- A C/C++ toolchain for the FFT and (optional) MPI extensions, since some
  dependencies compile locally.

## Install variants

FluidSim's solvers are pseudospectral, so the FFT extra is not optional for real
work — install it unless you only intend to inspect the API.

```bash
uv pip install fluidsim               # core only; no FFT solvers
uv pip install "fluidsim[fft]"        # fluidfft + pyfftw — needed for solvers
uv pip install "fluidsim[fft,mpi]"    # add mpi4py for parallel runs
```

The `[fft,mpi]` variant triggers a local build of `mpi4py`; make sure an MPI
implementation (OpenMPI or MPICH) and `mpicc` are on `PATH` first.

## Environment variables

All optional. Set them before launching a run.

| Variable | Purpose |
|---|---|
| `FLUIDSIM_PATH` | Root directory for simulation output folders. |
| `FLUIDDYN_PATH_SCRATCH` | Working/scratch directory for temporary data. |
| `FLUIDSIM_TYPE_FFT2D` | Force a 2D FFT backend, e.g. `fft2d.with_fftw`. |
| `FLUIDSIM_TYPE_FFT3D` | Force a 3D FFT backend, e.g. `fft3d.with_fftw`. |

If you do not set an FFT backend, fluidfft chooses one from what is installed.
Pin a backend when you want reproducible performance across machines.

## Verify the install

```bash
pytest --pyargs fluidsim
```

A quick smoke test in Python:

```python
from fluidsim.solvers.ns2d.solver import Simul
params = Simul.create_default_params()   # succeeds only if FFT deps import
```

If import fails with a missing `fluidfft`/`pyfftw`, you installed the bare
package — reinstall with the `[fft]` extra.

## No authentication

FluidSim needs no API keys, tokens, or accounts. It is fully local.
