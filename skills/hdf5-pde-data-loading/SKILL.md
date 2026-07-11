---
name: hdf5-pde-data-loading
version: 0.1.0
description: >-
  Patterns for loading PDE and simulation datasets stored in HDF5 (PDEBench,
  PhiFlow, JAX-CFD, or custom solver output) into NumPy arrays and PyTorch
  DataLoaders for neural-operator training. Covers HDF5 layout detection (a
  single stacked "tensor" dataset vs separate per-variable datasets), chunked
  reads to avoid OOM, spatial and temporal downsampling, multi-variable
  stacking, [N,T,X,C] -> [N,X,T,C] axis reordering, grid-coordinate recovery,
  autoregressive input/rollout windows, and fetching data from HuggingFace Hub
  or the DaRUS repository via aria2c. Use when preparing PDE/simulation HDF5 for
  FNO, DeepONet, or other neural operators. Do NOT use for generic HDF5 tabular
  I/O (use h5py/pandas directly), for AnnData .h5ad single-cell files (use
  `anndata`), for the model and training loop itself (use `pytorch-lightning`),
  or to run the PDE solver that produces the data (that is PhiFlow/JAX-CFD; this
  only ingests their output).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
---

# HDF5 PDE Data Loading

## Overview

PDE benchmark data (PDEBench, PhiFlow, JAX-CFD, and homegrown solver dumps) ships
as HDF5, but with no single convention: some files pack every trajectory into one
stacked dataset, others store each physical variable as its own dataset, and axis
order, grid coordinates, and dtype vary between them. This skill gives you a
robust ingest path — detect the layout, read in chunks, downsample spatially and
temporally, stack multi-variable systems, reorder axes to the convention your
model expects, recover the spatial grid, and wrap the result in a PyTorch
`DataLoader` for neural-operator training.

This is a **router**. The body gives you the decision points and a quick-start;
deep functions, source-specific download recipes, and troubleshooting tables live
in `references/`.

## When to Use This Skill

- Loading PDE/simulation trajectories from `.hdf5`/`.h5` for neural-operator
  training (FNO, DeepONet, U-Net operators) or autoregressive rollout.
- The file is a PDEBench, PhiFlow, or JAX-CFD export, or a custom solver dump.
- You must detect layout (single `tensor` dataset vs separate variables) before
  you can read it.
- Multi-variable systems (density, velocity, pressure) that must be stacked into
  a channel axis.
- The dataset is too large to load whole and needs chunked reads and/or spatial
  or temporal downsampling.
- You need to fetch the data first — from HuggingFace Hub or DaRUS.

## When NOT to Use This Skill

- **Generic HDF5 or tabular I/O** with no PDE/simulation structure — use `h5py`,
  `pandas`, or `polars` directly.
- **AnnData `.h5ad` single-cell files** — same container, different schema; use
  `anndata`.
- **The neural-operator model or training loop itself** — this skill stops at the
  `DataLoader`; build and train the model with `pytorch-lightning` (or raw
  PyTorch).
- **Running the PDE solver** to *generate* trajectories — that is PhiFlow /
  JAX-CFD / your own solver; this skill only ingests their output.
- **Out-of-core array math** across many files at once — reach for `dask`.

## The Two Layouts

Almost every PDE HDF5 file is one of two shapes. Detect by inspecting keys:

```python
import h5py
with h5py.File(path, "r") as f:
    print(list(f.keys()))
```

- **Layout A — single stacked dataset.** One key (commonly `"tensor"`) holds
  every trajectory: shape `[N, T, X]` (scalar field) or `[N, T, X, C]`
  (multi-channel). N = trajectories, T = timesteps, X = spatial points, C =
  channels.
- **Layout B — separate per-variable datasets.** One key per physical field
  (`"density"`, `"Vx"`, `"pressure"`, or `"u"`), each `[N, T, X]`. Stack them
  along a new trailing channel axis to form `[N, T, X, C]`.

A single `load_pde_hdf5(path, res_x, res_t)` should handle both, then reorder to
your model's convention (this skill uses spatial-major `[N, X, T, C]`, treating X
as the resolution axis and T as the sequence axis). Full implementation, chunking,
grid recovery, and dtype handling: `references/layout-and-loading.md`.

**Spatial dimensionality.** The loader and its `[N,T,X,C] -> [N,X,T,C]` transpose
assume a **single** spatial axis — 1-D PDEs (advection, Burgers, 1-D CFD). For 2-D
(`[N,T,X,Y,C]`) or 3-D fields (2-D/3-D PDEBench, most PhiFlow / JAX-CFD output),
keep every spatial axis and extend the permutation (2-D spatial-major:
`(0, 2, 3, 1, 4)` -> `[N,X,Y,T,C]`) and recover a per-axis grid. Watch the
2-D-scalar trap: an `[N,T,X,Y]` field is also `ndim==4`, so the 1-D loader mistakes
its trailing spatial axis for a channel — pass the field's spatial rank explicitly
rather than inferring it from `ndim`. See `references/layout-and-loading.md`.

## Quick Start

```python
import h5py, numpy as np
from torch.utils.data import Dataset, DataLoader

def load_pde_hdf5(path, res_x=1, res_t=1):
    """Return (data[N, X, T, C] float32, grid[X] float32). See references for the
    full chunked, layout-detecting version."""
    with h5py.File(path, "r") as f:
        if "tensor" in f:                      # Layout A
            raw = f["tensor"][:, ::res_t, ::res_x]      # [N, T, X(, C)]
            if raw.ndim == 3:
                raw = raw[..., None]
        else:                                  # Layout B: stack variables
            keys = [k for k in sorted(f.keys())
                    if isinstance(f[k], h5py.Dataset) and f[k].ndim >= 3]
            raw = np.stack([f[k][:, ::res_t, ::res_x] for k in keys], axis=-1)
        data = np.transpose(raw, (0, 2, 1, 3)).astype(np.float32)  # -> [N, X, T, C]
        grid = None
        for key in ("x-coordinate", "x", "X"):
            if key in f:
                grid = np.asarray(f[key], np.float32)[::res_x]
                break
        if grid is None:
            grid = np.linspace(0, 1, data.shape[1], dtype=np.float32)
    return data, grid

data, grid = load_pde_hdf5(path, res_x=4, res_t=5)   # 4x spatial, 5x temporal
```

For large files, read in row-chunks instead of `[:]` — see
`references/layout-and-loading.md`.

## Capability Map

### Layout detection & loading — `references/layout-and-loading.md`
The full `load_pde_hdf5`: both layouts, chunked reads (batches of ~500 to avoid
OOM), the `[N,T,X,C] -> [N,X,T,C]` transpose and why it matters, grid-coordinate
recovery with `linspace` fallback, and explicit float32 casting.

### Fetching the data — `references/data-sources.md`
HuggingFace Hub via `hf_hub_download` (fast CDN, when a mirror exists); DaRUS
(University of Stuttgart, the authoritative PDEBench host) via parallel `aria2c`;
resolving DaRUS file IDs from the PDEBench URL CSV; Modal/container install notes.

### PyTorch DataLoader — `references/dataloader.md`
A `Dataset` that yields autoregressive `(input_window, full_trajectory, grid)`
tuples, train/val splitting, and `DataLoader` config (`num_workers`,
`pin_memory`, `shuffle`).

### Downsampling & pitfalls — `references/downsampling-and-pitfalls.md`
Spatial/temporal downsampling-factor guidance, the shock-destruction warning
(downsampling can erase thin shocks entirely), and a symptom→fix table for the
common failure modes (wrong transpose, OOM, missing grid key, truncated
downloads, dtype bloat).

## Related Skills

`pytorch-lightning` (the model and training loop the `DataLoader` feeds),
`anndata` (the other big scientific HDF5 schema — `.h5ad`, not PDE), `dask`
(out-of-core arrays when a single file will not fit), `polars` (tabular metadata
alongside the arrays).

## Reference Index

- `references/layout-and-loading.md` — full loader, chunking, transpose, grid.
- `references/data-sources.md` — HuggingFace Hub and DaRUS download recipes.
- `references/dataloader.md` — PyTorch `Dataset`/`DataLoader` for rollout training.
- `references/downsampling-and-pitfalls.md` — downsampling tables and failure modes.

## Resources

- PDEBench: https://github.com/pdebench/PDEBench
- DaRUS (data repository): https://darus.uni-stuttgart.de/
- h5py: https://docs.h5py.org/
