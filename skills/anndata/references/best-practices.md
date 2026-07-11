# Best Practices, Failure Modes, and Pitfalls

## Memory management

**Sparse `X` for count data.** Single-cell matrices are mostly zeros; CSR/CSC
storage is typically 10-100x smaller.

```python
import numpy as np
from scipy.sparse import csr_matrix, issparse

if not issparse(adata.X):
    density = np.count_nonzero(adata.X) / adata.X.size
    if density < 0.5:
        adata.X = csr_matrix(adata.X)
```

**Categorical metadata for repeated strings.**

```python
adata.strings_to_categoricals()   # 10-50x smaller for columns like cell_type
```

**Backed / lazy mode for data larger than RAM.**

```python
adata = ad.read_h5ad("big.h5ad", backed="r")
adata = adata[adata.obs["quality"] > 0.8].to_memory()   # load only what you keep
```

## Views vs copies — the rule

Slicing yields a view sharing memory with the parent. Copy whenever you will
**store**, **mutate**, or **outlive the parent**.

```python
# Read-only analysis on a view is fine and cheap
mean_expr = adata[adata.obs["cell_type"] == "T"].X.mean()

# Storing or mutating -> copy
subset = adata[keep, :].copy()
subset.obs["new"] = values          # safe; does not touch the parent
```

## Working with `raw`

Snapshot before you drop genes so downstream tools can still reach them.

```python
adata.raw = adata.copy()                          # BEFORE gene filtering
adata = adata[:, adata.var["highly_variable"]]    # main object shrinks
adata.raw[:, "GENE"].X                             # dropped gene still reachable
```

Use `raw` for differential expression and for plotting genes not in the filtered
set.

## Storage choices

| Format | Best for | Notes |
|--------|----------|-------|
| `.h5ad` | most workflows | fast random access, backed mode, good compression |
| `.zarr` | cloud / parallel | chunked, S3/GCS-friendly, tune chunk size |
| `.csv` | interop | human-readable, large and slow; small data only |

Optimize before writing: sparse-ify, `strings_to_categoricals()`, then
`compression="gzip"`. Expect 5-20x file-size reduction.

## Performance

- Boolean masks as **numpy arrays** are faster than passing a pandas `Series`
  directly: `mask = np.asarray(adata.obs["q"] > 0.5); adata[mask]`.
- Precompute integer indices for repeated selection:
  `idx = np.where(cond)[0]`.
- Group once instead of re-subsetting per category:
  `for name, idx in adata.obs.groupby("cell_type").groups.items(): ...`.
- Use `chunked_X` instead of materializing full `X` for streaming compute.

## Reproducibility

Record what produced the object inside `uns`.

```python
import sys, anndata
adata.uns["params"]   = {"pca": {"n_comps": 50, "random_state": 42}}
adata.uns["history"]  = ["loaded 10x", "filtered n_genes>200", "log1p"]
adata.uns["versions"] = {"anndata": anndata.__version__, "python": sys.version}
```

## Validation

```python
from scipy.sparse import issparse
assert adata.X.shape == (adata.n_obs, adata.n_vars)
assert adata.obs_names.is_unique, "duplicate observation names"
assert adata.var_names.is_unique, "duplicate variable names"

X = adata.X.data if issparse(adata.X) else adata.X
if np.isnan(X).any():   print("warning: NaNs in X")
if (X < 0).any():       print("warning: negative values in X")
```

## Common pitfalls

**1. Mutating a view.** Assigning into a slice can write through to the parent.
Copy first if the subset must be independent.

```python
sub = adata[:100, :].copy()   # not adata[:100, :]
sub.X = new_data
```

**2. Index misalignment.** Assigning a raw array/Series ignores labels and can
scramble rows.

```python
# Wrong — positional, may misalign
adata.obs["new"] = external["values"]
# Right — align on the index
adata.obs["new"] = external.set_index("cell_id").loc[adata.obs_names, "values"]
```

**3. Accidental densification.** Arithmetic on a sparse matrix with a scalar can
blow up memory.

```python
# Wrong — densifies the whole matrix
result = adata.X + 1
# Right — operate on stored values
result = adata.X.copy(); result.data += 1
```

**4. Dangling views.** Deleting the parent can invalidate a view.

```python
sub = adata[mask, :].copy()   # copy if it must outlive adata
del adata
```

**5. Loading a huge file into RAM.** Reach for backed mode.

```python
adata = ad.read_h5ad("100GB.h5ad", backed="r")
adata = adata[adata.obs["keep"]].to_memory()
```

## Reference workflow

```python
import anndata as ad
import numpy as np
from scipy.sparse import csr_matrix, issparse

adata = ad.read_h5ad("data.h5ad", backed="r")            # 1) lazy open
adata = adata[adata.obs["quality_score"] > 0.8].to_memory()  # 2) filter+load
adata.strings_to_categoricals()                          # 3) compact metadata
if not issparse(adata.X):                                #    sparse-ify
    if np.count_nonzero(adata.X) / adata.X.size < 0.5:
        adata.X = csr_matrix(adata.X)
adata.raw = adata.copy()                                 # 4) snapshot
adata = adata[:, adata.var["highly_variable"]].copy()    # 5) keep HVGs
adata.uns["processing"] = {"filter": "quality>0.8", "n_hvg": adata.n_vars}
adata.write_h5ad("processed.h5ad", compression="gzip")   # 6) save optimized
```
