# Layout Detection & Full Loader

## Inspect first, always

Never assume a layout. Print the keys and the shape of each dataset before
writing loading code:

```python
import h5py
with h5py.File(path, "r") as f:
    for k in f.keys():
        obj = f[k]
        kind = "dataset" if isinstance(obj, h5py.Dataset) else "group"
        shape = getattr(obj, "shape", None)
        print(f"{k:>16}  {kind:8}  {shape}")
```

- **Layout A** shows a single field-carrying dataset, usually `tensor`, shape
  `[N, T, X]` or `[N, T, X, C]`.
- **Layout B** shows one dataset per physical variable (`density`, `Vx`,
  `pressure`, `u`, ...), each `[N, T, X]`, plus small 1-D coordinate datasets
  (`x-coordinate`, `t-coordinate`).

Axis meaning throughout: **N** = number of trajectories/samples, **T** =
timesteps, **X** = spatial grid points, **C** = physical channels.

## The full, robust loader

Handles both layouts, downsamples spatial (`res_x`) and temporal (`res_t`) axes
by strided slicing, reads Layout A in row-chunks to avoid loading all N
trajectories at once, reorders to spatial-major `[N, X, T, C]`, recovers the
grid, and casts to float32.

```python
import h5py
import numpy as np


def load_pde_hdf5(path, res_x=1, res_t=1, chunk=500):
    """Load a PDE trajectory dataset from HDF5.

    Args:
        path:  path to the .hdf5/.h5 file
        res_x: spatial stride (4 keeps every 4th grid point)
        res_t: temporal stride (5 keeps every 5th timestep)
        chunk: trajectories read per iteration for Layout A (OOM guard)

    Returns:
        data: float32 array [N, X, T, C]  (spatial-major)
        grid: float32 array [X]
    """
    with h5py.File(path, "r") as f:
        if "tensor" in f:
            ds = f["tensor"]                       # [N, T, X] or [N, T, X, C]
            N = ds.shape[0]
            has_channel = ds.ndim == 4
            # Peek one downsampled row to learn the post-stride shape.
            probe = ds[0:1, ::res_t, ::res_x]
            if not has_channel:
                probe = probe[..., None]
            _, T_ds, X_ds, C = probe.shape
            data = np.empty((N, X_ds, T_ds, C), dtype=np.float32)
            for start in range(0, N, chunk):       # bounded memory
                stop = min(start + chunk, N)
                block = ds[start:stop, ::res_t, ::res_x]
                if not has_channel:
                    block = block[..., None]
                data[start:stop] = np.transpose(block, (0, 2, 1, 3))
        else:
            var_keys = [
                k for k in sorted(f.keys())
                if isinstance(f[k], h5py.Dataset) and f[k].ndim >= 3
            ]
            if not var_keys:
                raise ValueError(f"No field datasets (ndim>=3) found in {path}")
            arrays = [f[k][:, ::res_t, ::res_x] for k in var_keys]  # each [N,T,X]
            raw = np.stack(arrays, axis=-1)        # [N, T, X, C]
            data = np.transpose(raw, (0, 2, 1, 3)).astype(np.float32)

        grid = _load_grid(f, n_points=data.shape[1], res_x=res_x)

    return data, grid


def _load_grid(f, n_points, res_x):
    """Recover the spatial grid, falling back to a unit linspace."""
    for key in ("x-coordinate", "x", "X"):
        if key in f:
            return np.asarray(f[key], dtype=np.float32)[::res_x]
    return np.linspace(0.0, 1.0, n_points, dtype=np.float32)
```

## Why the `[N, T, X, C] -> [N, X, T, C]` transpose

HDF5 stores trajectories time-major (`[N, T, X, C]`) because the solver writes one
timestep at a time. Many neural-operator training setups want **spatial-major**
`[N, X, T, C]`: X is the "resolution" axis the operator is discretization-agnostic
over, and T becomes a per-point sequence you slice into an input window and a
rollout target. Getting this backwards silently trains the model on transposed
fields and it will not converge — pick one convention and assert the shape after
loading:

```python
assert data.shape[1] == grid.shape[0], "spatial axis must match grid length"
```

If your model expects time-major or channels-first (`[N, C, X, T]`), change the
`np.transpose` permutation in one place rather than reshaping downstream.

**1-D only, by default.** The loader above assumes one spatial axis. For a 2-D
field stored `[N, T, X, Y, C]` (or `[N, T, X, Y]` for a scalar), keep both spatial
axes: use the spatial-major permutation `(0, 2, 3, 1, 4)` -> `[N, X, Y, T, C]` and
recover an `x`- and `y`-coordinate grid. Do not rely on `ndim == 4` to detect a
channel axis in the 2-D case — an `[N, T, X, Y]` scalar field is `ndim == 4` yet has
no channel, so pass the spatial rank explicitly (e.g. a `spatial_ndim` argument)
instead of inferring `has_channel` from `ndim`.

## Chunked reads (OOM guard)

`ds[:]` materializes all N trajectories at once. For large N (or a 1024-point
grid at full temporal resolution), that can exhaust host RAM. Layout A reads in
row-blocks of `chunk` (default 500) and downsamples each block before it lands in
the pre-allocated `data` array. Tune `chunk` down on memory-constrained hosts.
Layout B stacks whole variables; if those are also large, apply the same
row-chunking per variable.

## Grid recovery and dtype

- **Grid key varies:** try `x-coordinate`, then `x`, then `X`; if none exist, fall
  back to `np.linspace(0, 1, X)`. Apply the same `res_x` stride to the grid so it
  stays aligned with the downsampled spatial axis.
- **Always cast to float32.** Simulation data is frequently stored float64;
  carrying that into training doubles memory and slows GPU kernels for no accuracy
  benefit at operator-training precision.
