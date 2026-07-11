# Storage Backends, Groups, Consolidated Metadata, and Integration

## Storage Backends

A plain path string creates a `LocalStore`. Use explicit store classes for other
targets. Import from `zarr.storage`.

### Local filesystem (default)

```python
z = zarr.create_array(store="data/my_array.zarr", shape=(1000, 1000),
                      chunks=(100, 100), dtype="f4")
# equivalent to:
store = zarr.storage.LocalStore("data/my_array.zarr")
z = zarr.create_array(store=store, shape=(1000, 1000), chunks=(100, 100), dtype="f4")
```

### In-memory (ephemeral)

```python
store = zarr.storage.MemoryStore()
z = zarr.create_array(store=store, shape=(1000, 1000), chunks=(100, 100), dtype="f4")
# Data lives only for the life of the process — good for tests and scratch work.
```

### ZIP archive (single file)

```python
store = zarr.storage.ZipStore("data.zip", mode="w")
z = zarr.create_array(store=store, shape=(1000, 1000), chunks=(100, 100), dtype="f4")
z[:] = np.random.random((1000, 1000))
store.close()   # REQUIRED — the central directory is written on close

store = zarr.storage.ZipStore("data.zip", mode="r")
z = zarr.open_array(store=store)
data = z[:]
store.close()
```

A ZipStore is append-only while open and must be closed to be readable. It is ideal for
shipping one Zarr hierarchy as a single portable file.

### Cloud object stores (S3 / GCS / Azure)

v3 routes cloud access through fsspec. The simplest form is to pass the URL directly and
hand credentials/options via `storage_options`:

```python
z = zarr.create_array(
    store="s3://my-bucket/path/data.zarr",
    storage_options={"anon": False},   # forwarded to s3fs
    shape=(10_000, 10_000), chunks=(1_000, 1_000), dtype="float32",
)
z[:] = data

# Google Cloud Storage
z = zarr.create_array(
    store="gs://my-bucket/path/data.zarr",
    storage_options={"project": "my-project"},
    shape=(10_000, 10_000), chunks=(1_000, 1_000), dtype="float32",
)
```

You can also build the store explicitly with `zarr.storage.FsspecStore.from_url(url,
storage_options=...)`. Requires `s3fs` / `gcsfs` / `adlfs` installed for the respective
scheme.

> v2 note: the old `s3fs.S3Map(...)` / `gcsfs.GCSMap(...)` mutable-mapping pattern is v2
> era. In v3 prefer the URL + `storage_options` form (or `FsspecStore`).

See `performance.md` for cloud chunk sizing and consolidated-metadata tuning.

## Groups and Hierarchies

Groups nest arrays into an HDF5-like tree. Each array keeps its own chunks, codecs, and
attributes.

```python
root = zarr.group(store="data/hierarchy.zarr")

temperature = root.create_group("temperature")
precipitation = root.create_group("precipitation")

t2m = temperature.create_array(
    name="t2m", shape=(365, 720, 1440), chunks=(1, 720, 1440), dtype="float32"
)

array = root["temperature/t2m"]   # path access
print(root.tree())                # visualize the hierarchy
print(list(root.keys()), list(root.groups()), list(root.arrays()))
```

### h5py-compatible surface

For users migrating from HDF5:

```python
root = zarr.group("data.zarr")
dset = root.create_dataset("my_data", shape=(1000, 1000), chunks=(100, 100), dtype="f4")
grp  = root.require_group("subgroup")                      # create if absent
arr  = grp.require_dataset("array", shape=(500, 500), chunks=(50, 50), dtype="i4")
```

`create_dataset` / `require_dataset` / `require_group` mirror h5py naming so existing
HDF5 code ports with minimal change.

## Consolidated Metadata

A hierarchy with many arrays otherwise costs one metadata read per node. Consolidation
writes a single combined metadata document so opening the tree is one request.

```python
root = zarr.group("data.zarr")
# ... create arrays / groups ...
zarr.consolidate_metadata("data.zarr")     # write the consolidated doc

root = zarr.open_consolidated("data.zarr")  # one metadata read for the whole tree
```

- **Big win on cloud stores** and for `tree()` / traversal over many nodes.
- **Goes stale**: if you add, remove, or reshape nodes afterward, re-run
  `consolidate_metadata`. Opening consolidated metadata will not reflect un-consolidated
  changes.
- **Avoid for frequently mutated trees** or multi-writer stores where readers could see
  an inconsistent snapshot. To bypass an existing consolidated doc, open with
  `use_consolidated=False`.

## Integration with NumPy, Dask, and Xarray

### NumPy

A Zarr array supports NumPy-style indexing and returns NumPy arrays on read. Reductions
like `np.sum(z, axis=0)` work but pull data into memory — prefer Dask for large arrays.

```python
result = np.sum(z[:100, :100], axis=0)   # bounded slice -> fine
arr = z[:]                               # loads the WHOLE array into RAM — beware
```

### Dask (out-of-core parallel compute)

```python
import dask.array as da

dz = da.from_zarr("data.zarr")           # lazy; no data read yet
mean = dz.mean(axis=0).compute()         # parallel, chunk-by-chunk, out-of-core

big = da.random.random((100_000, 100_000), chunks=(1_000, 1_000))
da.to_zarr(big, "output.zarr")           # write a Dask array straight to Zarr
```

Dask reuses Zarr's chunk grid as its task grid, so aligned chunks give clean parallelism.
This is the recommended path for anything larger than memory — see the `dask` skill.

### Xarray (labeled dims and coordinates)

```python
import xarray as xr

ds = xr.open_zarr("data.zarr")                       # lazy, Dask-backed Dataset
subset = ds.sel(time="2024-01", lat=slice(30, 60))   # label-based selection
ds.to_zarr("output.zarr")                            # write a Dataset to Zarr
```

Xarray adds named dimensions, coordinates, and `.sel()`/`.isel()` on top of Zarr storage
— the usual choice for climate/geospatial workflows. Reach for raw Zarr when you need
direct control over chunks, codecs, or the store.

## Format Conversion

```python
# HDF5 -> Zarr
import h5py
with h5py.File("data.h5", "r") as h5:
    z = zarr.array(h5["dataset_name"][:], chunks=(1000, 1000), store="data.zarr")

# NumPy -> Zarr
z = zarr.array(np.load("data.npy"), chunks="auto", store="data.zarr")

# Zarr -> NetCDF (via Xarray)
xr.open_zarr("data.zarr").to_netcdf("data.nc")

# Zarr -> NumPy file
np.save("data.npy", zarr.open("data.zarr", mode="r")[:])
```

## Concurrency (recap)

Zarr v3 has no synchronizer API (v2's `ThreadSynchronizer` / `ProcessSynchronizer` were
removed; the `synchronizer` argument is a deprecated no-op). Concurrent reads are always
safe; concurrent writes are safe as long as no two writers touch the same chunk. Design
multi-process writes so each worker owns a disjoint set of chunks; otherwise serialize
externally. Writes that straddle a chunk boundary count as touching every overlapped
chunk.
