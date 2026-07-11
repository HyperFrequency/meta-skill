---
name: zarr-python
version: 0.1.0
description: >-
  Store, chunk, and compress large N-dimensional arrays with zarr-python 3.x for
  parallel and cloud-native I/O. Use when arrays are too big for memory, when you
  need concurrent chunk-wise reads/writes, cloud object-store (S3/GCS) access, or a
  NumPy/Dask/Xarray-compatible on-disk array format — covers array/group creation,
  chunk and shard sizing, codec/compression choice, storage backends, consolidated
  metadata, concurrency, and diagnostics. Not for small in-memory arrays (use NumPy
  .npy/.npz), for heterogeneous tabular/columnar data (use `polars`, `vaex`, or
  Parquet), or for the parallel compute graph itself (use `dask`, which reads Zarr
  arrays natively). Targets the Zarr v3 API: synchronizers are gone and concurrency
  is chunk-partitioned.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: MIT
---

# Zarr Python

## Overview

Zarr stores a large N-dimensional array as a grid of independently compressed
**chunks** plus a small JSON metadata document. Any slice reads only the chunks it
touches, chunks compress and decompress in parallel, and the on-disk layout works
identically on a local filesystem or a cloud object store. This makes Zarr the
default format for out-of-core scientific arrays that NumPy alone cannot hold in
memory, and the storage layer beneath Xarray and Dask array pipelines.

This skill targets **zarr-python 3.x** (`import zarr`). The v3 API differs from v2 in
several load-bearing ways — `resize` takes a shape tuple, compression is set with
`compressors=`, codecs live under `zarr.codecs`, cloud stores use fsspec URLs, and
the v2 `synchronizer` mechanism is gone. Treat any v2 snippet you find elsewhere with
suspicion.

## When to Use This Skill

- The array is larger than RAM and you need to read/write **slices** without
  materializing the whole thing.
- You want **parallel or concurrent** chunk-wise I/O (many workers, many processes).
- You need **cloud-native** array access on S3/GCS/Azure with minimal round-trips.
- You want an on-disk array that `numpy`, `dask`, and `xarray` all read directly.
- You are appending along an axis over time (time-series, simulation output).
- You are converting HDF5/NetCDF/NumPy data into a chunked, cloud-friendly form.

## When NOT to Use This Skill

- **Small arrays that fit in memory** → use NumPy and `np.save`/`np.savez`; Zarr's
  metadata and chunk overhead is pure cost here.
- **Heterogeneous tabular/columnar data** (mixed per-column dtypes, string-heavy) →
  Zarr stores one homogeneous dtype per array; use `polars`, `vaex`, or Parquet.
- **The parallel compute graph itself** (lazy reductions, map-blocks, task
  scheduling) → that is `dask`; Zarr is only its storage layer.
- **Labeled dims/coords with pandas-style `.sel()`** → use Xarray (which uses Zarr as
  a backend). Reach for raw Zarr when you need direct chunk/codec/store control.
- **A single self-contained file for tiny archival data with no cloud story** → HDF5
  or NetCDF can be simpler; Zarr's advantage is chunk-parallel and object-store I/O.

## Create and Open Arrays

```python
import zarr
import numpy as np

# Create (Zarr v3): store may be a path string, a Store object, or a cloud URL.
z = zarr.create_array(
    store="data/example.zarr",
    shape=(10_000, 10_000),
    chunks=(1_000, 1_000),   # the unit of read + (de)compression
    dtype="float32",
)
z[:] = np.random.random((10_000, 10_000))   # write
subset = z[0:100, 0:100]                     # read -> returns a NumPy array

# Open existing
z = zarr.open_array("data/example.zarr", mode="r")    # read-only, must exist
z = zarr.open_array("data/example.zarr", mode="r+")   # read/write, must exist
obj = zarr.open("data/example.zarr")                  # auto-detect Array vs Group
```

Modes: `r` (read-only, must exist), `r+` (read/write, must exist), `a` (read/write,
create if missing — default), `w` (create, overwrite), `w-` (create, fail if exists).
Convenience constructors `zarr.zeros`, `zarr.ones`, `zarr.full`, `zarr.array(data)`,
and `zarr.zeros_like(z)` also exist. Full signatures, indexing modes (`vindex`,
`oindex`, `blocks`), array properties, dtype strings, and error handling are in
[references/api-reference.md](references/api-reference.md).

## Chunking — the Single Biggest Lever

Chunk shape, not chunk size alone, decides performance: a read must fetch and
decompress **every chunk it overlaps**. Align the chunk grid with your dominant access
pattern.

```python
# Rule of thumb: aim for ~1-10 MB per chunk (float32 1 MB ~ 512x512).
zarr.create_array(store=s, shape=(10_000, 10_000), chunks=(10, 10_000), dtype="f4")   # row-wise reads
zarr.create_array(store=s, shape=(10_000, 10_000), chunks=(10_000, 10), dtype="f4")   # column-wise reads
zarr.create_array(store=s, shape=(10_000, 10_000), chunks=(1_000, 1_000), dtype="f4") # mixed/random
```

For a `(200, 200, 200)` array, reading along the first axis is dramatically faster with
chunks `(200, 200, 1)` than `(1, 200, 200)` — order of tens of times. Chunk-size math,
access-pattern recipes, and how to fix a slow array are in
[references/performance.md](references/performance.md).

**Sharding** (v3): when a good chunk size yields millions of tiny objects, group many
chunks into one storage object with `shards=` so the filesystem/object store sees far
fewer files while reads stay chunk-granular.

```python
z = zarr.create_array(
    store="data/big.zarr", shape=(100_000, 100_000),
    chunks=(256, 256), shards=(4096, 4096), dtype="float32",
)
```

## Compression and Codecs

In Zarr v3, `compressors=` sets byte→byte codecs, `filters=` sets array→array codecs,
and `serializer=` sets the array→bytes step. Pass `compressors=None` to disable.

```python
z = zarr.create_array(
    store="data/c.zarr", shape=(1000, 1000), chunks=(100, 100), dtype="float32",
    compressors=zarr.codecs.BloscCodec(
        cname="zstd", clevel=5, shuffle=zarr.codecs.BloscShuffle.shuffle
    ),
)
```

Rough guide: `BloscCodec(cname="lz4", clevel=1)` for speed, `cname="zstd", clevel=5`
for a balance (the default family), `zarr.codecs.GzipCodec(level=9)` for maximum ratio.
The shuffle filter helps most numeric data. Codec catalog and tuning are in
[references/performance.md](references/performance.md).

## Storage Backends, Groups, and Cloud

Local paths create a `LocalStore` automatically. Other backends:

```python
zarr.storage.MemoryStore()                 # ephemeral, in-process
zarr.storage.ZipStore("data.zip", mode="w")  # single file — MUST .close() when done

# Cloud via fsspec: pass the URL and storage_options; needs s3fs / gcsfs installed.
z = zarr.create_array(
    store="s3://my-bucket/data.zarr", storage_options={"anon": False},
    shape=(10_000, 10_000), chunks=(1_000, 1_000), dtype="float32",
)
```

**Groups** organize many arrays into an HDF5-like tree, each array free to have its own
chunks/codecs. **Consolidated metadata** (`zarr.consolidate_metadata(store)` then
`zarr.open_consolidated(store)`) collapses per-array metadata reads into one request —
essential on high-latency cloud stores, but goes stale if you mutate the tree
afterward. Backend details, group/attribute APIs, consolidated-metadata caveats, and
NumPy/Dask/Xarray integration (including format conversion) are in
[references/storage-groups-integration.md](references/storage-groups-integration.md).

## Concurrency and Thread Safety (v3)

Zarr v3 removed v2's `ThreadSynchronizer`/`ProcessSynchronizer`; the `synchronizer`
argument is now a deprecated no-op. The model is chunk-partitioned:

- **Concurrent reads** are always safe.
- **Concurrent writes within one process** are safe.
- **Multi-process writes** are safe only when processes write **disjoint chunks** and
  the store supports atomic writes. Two processes writing the **same** chunk (including
  a write that straddles a chunk boundary) is a data race — partition the work by chunk
  so no two writers touch one chunk, or serialize externally.

## Diagnostics

```python
print(z.info)              # cheap summary: shape, chunks, shards, dtype, codecs
print(z.info_complete())   # actual stored (compressed) size — scans the store
print(z.chunks, z.shards, z.nchunks)
```

Use `z.info_complete()` to check the real compression ratio before committing to a
codec choice at scale.

## Related Skills

- `dask` — lazy, out-of-core parallel compute over Zarr chunks (`da.from_zarr`).
- `polars`, `vaex` — reach for these instead when the data is tabular, not N-D array.
