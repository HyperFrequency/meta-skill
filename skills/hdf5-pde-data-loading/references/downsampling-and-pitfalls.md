# Downsampling Guidance & Pitfalls

Downsampling (the `res_x` / `res_t` strides in `load_pde_hdf5`) is the main lever
for fitting PDE data in memory and controlling training cost. It is also where the
physics can be silently destroyed — a stride that is fine for a smooth field can
erase a shock. Choose the factor from the problem, not the memory budget alone.

## Spatial downsampling

| Original grid | Downsampled | Factor | Use when |
|---|---|---|---|
| 1024 | 256 | 4x | Smooth problems, standard benchmarks, fast iteration |
| 1024 | 512 | 2x | Moderate shocks, multi-variable systems |
| 1024 | 1024 | 1x | Sharp shocks (e.g. viscosity nu <= 0.001) — needs a large GPU |

## Temporal downsampling

| Original steps | Downsampled | Factor | Use when |
|---|---|---|---|
| 200 | 40 | 5x | Standard horizon (e.g. 10 input + 30 rollout) |
| 100 | 20 | 5x | Short series (e.g. 10 input + 10 rollout) |

Set `init_step` (input window) and rollout length against the **downsampled** T,
not the original — see `dataloader.md`.

## The shock-destruction warning

Downsampling a field with thin features can remove them entirely. A shock of width
~0.001 on a domain of length 1 spans a single cell at 1024 points; at 256 points
(4x) it falls **below one grid cell** and vanishes from the training signal — the
model then learns a smoothed problem that does not match the true dynamics. Before
downsampling a convective/compressible or low-viscosity case:

- Estimate the narrowest feature width and compare it to the downsampled grid
  spacing `L / X_ds`. If a feature spans < ~2 cells, do not downsample that axis.
- Prefer 2x or 1x spatial for shock-dominated regimes; reserve 4x for smooth
  diffusion-dominated problems.

## Failure modes

| Pitfall | Symptom | Fix |
|---|---|---|
| Wrong transpose / axis order | Model will not converge; loss plateaus at noise | Fix the permutation in one place: HDF5 `[N,T,X,C]` -> model convention (this skill uses `[N,X,T,C]`); assert `data.shape[1] == grid.shape[0]` |
| Reading the whole array at once | Host OOM during loading | Read Layout A in row-chunks (~500 trajectories) and downsample each block before it lands in `data` |
| HF repo/file missing or renamed | `RepositoryNotFoundError` / `EntryNotFoundError` | Fall back to DaRUS via the PDEBench URL CSV + `aria2c` (see `data-sources.md`) |
| Grid key absent | Wrong grid spacing; coordinates misaligned | Try `x-coordinate` -> `x` -> `X`; fall back to `np.linspace(0, 1, X)`, strided by `res_x` |
| Truncated / partial download | HDF5 read error, or `KeyError` on expected datasets | Verify file size and md5 against the PDEBench CSV; delete and re-download |
| float64 carried into training | High host/GPU memory, slow kernels | Cast to float32 explicitly at load (`.astype(np.float32)`) |
| Over-aggressive spatial downsample on a shock | Model "converges" but predictions are unphysically smooth | Reduce the spatial factor (2x or 1x); check feature width vs grid spacing first |
| Downsampling the grid but not the field (or vice versa) | Grid length != spatial axis; assertion fails | Apply the **same** `res_x` stride to both the field and the coordinate array |

## Quick sanity checklist after loading

```python
assert data.dtype == np.float32
assert data.ndim == 4                      # [N, X, T, C]
assert data.shape[1] == grid.shape[0]      # spatial axis matches grid
assert np.isfinite(data).all()             # no NaN/Inf from a bad read
print(data.shape, grid.shape, data.min(), data.max())
```
