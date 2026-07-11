# Input / Output

Namespaces to know (AnnData 0.10+):

- Native round-trip functions are top-level *and* under `anndata.io`:
  `ad.read_h5ad`, `ad.read_zarr` (aliases of `ad.io.read_h5ad`, `ad.io.read_zarr`).
- All other readers live under **`anndata.io`**: `read_csv`, `read_excel`,
  `read_hdf`, `read_mtx`, `read_text`, `read_umi_tools`, `read_loom`.
- Out-of-core / lazy / element helpers live under **`anndata.experimental`**:
  `read_lazy`, `read_elem_lazy`, `AnnCollection`, `AnnLoader`, `concat_on_disk`.

> AnnData ships **no 10x reader**. `read_10x_h5` / `read_10x_mtx` are `scanpy`
> functions (`sc.read_10x_h5`, `sc.read_10x_mtx`).

## Native format: `.h5ad` (HDF5)

Fastest for random access; supports backed mode.

```python
import anndata as ad

adata.write_h5ad("data.h5ad")
adata.write_h5ad("data.h5ad", compression="gzip", compression_opts=4)
adata.write_h5ad("dense.h5ad", as_dense=["X"])   # force-densify a slot on write

adata = ad.read_h5ad("data.h5ad")                # full into memory
adata = ad.read_h5ad("data.h5ad", backed="r")    # memory-map, read-only
adata = ad.read_h5ad("data.h5ad", backed="r+")   # memory-map, read-write
```

### Backed mode
Only accessed data is pulled into RAM — inspect metadata and filter without
loading `X`.

```python
adata = ad.read_h5ad("large.h5ad", backed="r")
print(adata.obs.head())                 # metadata is available immediately
subset = adata[:100, :500]              # a view; nothing loaded yet
in_mem = subset.to_memory()             # materialize just this slice
adata.file.close()                      # release the file handle when done
```

Modifying a backed object needs `backed="r+"` (metadata writes flush to disk) or
`to_memory()` first.

## Native format: `.zarr`

Chunked store, strong fit for cloud (S3/GCS) and parallel I/O.

```python
adata.write_zarr("data.zarr", chunks=(1000, 1000))
adata = ad.read_zarr("data.zarr")

# Remote store
import s3fs
store = s3fs.S3Map(root="s3://bucket/data.zarr", s3=s3fs.S3FileSystem())
adata = ad.read_zarr(store)
```

Tune chunks to the access pattern: larger for sequential scans, smaller for
random access.

## Alternative input formats (`anndata.io`)

```python
from anndata import io

adata = io.read_csv("data.csv")                       # rows = obs, cols = vars
adata = io.read_csv("data.tsv", delimiter="\t")
adata = io.read_text("data.txt", delimiter=",", first_column_names=True)
adata = io.read_excel("data.xlsx", sheet="Sheet1")
adata = io.read_hdf("data.h5", key="dataset")         # generic HDF5, not .h5ad
adata = io.read_umi_tools("counts.tsv")
adata = io.read_loom("data.loom", obs_names="CellID", var_names="Gene")

# Matrix Market: verify orientation. .mtx often stores genes as rows —
# transpose so observations end up on axis 0.
adata = io.read_mtx("matrix.mtx")
if adata.shape[0] < adata.shape[1]:   # heuristic: fewer rows than cols
    pass                               # inspect and .T if genes are on rows
adata = io.read_mtx("matrix.mtx").T    # explicit transpose when needed
```

For 10x CellRanger output, use scanpy:

```python
import scanpy as sc
adata = sc.read_10x_h5("filtered_feature_bc_matrix.h5")
adata = sc.read_10x_mtx("filtered_feature_bc_matrix/")   # a directory
```

## Alternative output formats

```python
adata.write_csvs("out_dir/")               # X.csv, obs.csv, var.csv, ...
adata.write_csvs("out_dir/", skip_data=True)   # omit the X matrix
adata.write_loom("out.loom")
```

## Element-level and lazy reads

Read or write one slot without touching the rest of the file. `io.read_elem`
takes an *open* h5py/zarr group or dataset (not a path); `io.write_elem` writes
into an open group.

```python
import h5py
from anndata import io

with h5py.File("data.h5ad", "r") as f:
    obs   = io.read_elem(f["obs"])           # just the obs frame
    layer = io.read_elem(f["layers/log1p"])  # just one layer

with h5py.File("data.h5ad", "a") as f:
    io.write_elem(f, "layers/new", adata.layers["log1p"])

# Lazy: Dask-backed X, xarray-backed frames; nothing computed until accessed
f = h5py.File("large.h5ad", "r")
adata = ad.experimental.read_lazy(f)          # user manages file lifetime
type(adata.X)                                 # dask.array.core.Array
adata.X[:100, :100].compute()
```

Exact element signatures shift between versions — confirm against the installed
API before relying on them.

## Format conversion

```python
ad.io.read_mtx("matrix.mtx").T.write_h5ad("data.h5ad")   # MTX  -> h5ad
ad.read_h5ad("data.h5ad").write_zarr("data.zarr")        # h5ad -> zarr
```

## Large-dataset I/O strategies

```python
# 1) Filter-then-load
adata = ad.read_h5ad("100GB.h5ad", backed="r")
keep  = adata[adata.obs["quality_score"] > 0.8].to_memory()

# 2) Chunked scan
adata = ad.read_h5ad("huge.h5ad", backed="r")
for i in range(0, adata.n_obs, 1000):
    process(adata[i:i+1000, :].to_memory())

# 3) Out-of-core concat (never fully loads inputs)
ad.experimental.concat_on_disk(
    {"p1": "part1.h5ad", "p2": "part2.h5ad"},
    out_file="combined.h5ad", join="inner", label="batch",
)
```

## Performance tips

- `backed="r"` for query-only access to big files; `backed="r+"` to edit metadata.
- Compress for storage: `gzip` (smaller) or `lzf` (faster). Compression can slow
  reads slightly.
- `strings_to_categoricals()` before writing shrinks files noticeably.
- Convert dense→sparse when density is low before writing.
- Zarr chunk size is the main knob for cloud/parallel throughput.
