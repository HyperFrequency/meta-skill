# The AnnData Object Model

AnnData binds one 2-D matrix `X` to metadata that stays aligned under every
slice, concatenation, reorder, and transpose. Rows are **observations** (`obs`,
often cells); columns are **variables** (`var`, often genes).

## Core Components

### `X` — the data matrix
Shape `(n_obs, n_vars)`. Dense (`numpy.ndarray`) or sparse
(`scipy.sparse.csr_matrix`/`csc_matrix`). Prefer sparse for single-cell counts.

```python
import anndata as ad
import numpy as np
from scipy.sparse import csr_matrix

adata = ad.AnnData(X=np.random.rand(100, 2000).astype("float32"))
adata = ad.AnnData(X=csr_matrix(adata.X))   # sparse variant

row0   = adata.X[0, :]     # one observation
gene0  = adata.X[:, 0]     # one variable across all observations
```

### `obs` / `var` — aligned metadata DataFrames
`obs` has `n_obs` rows, `var` has `n_vars` rows. Their indices become
`obs_names` / `var_names`.

```python
import pandas as pd
obs = pd.DataFrame(
    {"cell_type": ["T", "B", "Mono"], "condition": ["ctrl", "treat", "ctrl"]},
    index=["cell_1", "cell_2", "cell_3"],
)
var = pd.DataFrame({"gene_name": ["ACTB", "GAPDH", "TP53"]},
                   index=["ENSG1", "ENSG2", "ENSG3"])
adata = ad.AnnData(X=np.random.rand(3, 3), obs=obs, var=var)

adata.obs["cell_type"]          # column as Series
adata.obs.loc["cell_1"]         # one observation's metadata row
```

### `layers` — same-shape alternative matrices
Dictionary of matrices all shaped `(n_obs, n_vars)`. Standard uses:
`counts` (raw), `normalized`, `scaled`, `imputed`.

```python
adata.layers["counts"]     = np.random.randint(0, 100, adata.shape)
adata.layers["log1p"]      = np.log1p(adata.X)
```

### `obsm` / `varm` — multidimensional annotations
`obsm[k]` is `(n_obs, d)` (embeddings); `varm[k]` is `(n_vars, d)` (loadings).
Scanpy conventions prefix embeddings with `X_`.

```python
adata.obsm["X_pca"]  = np.random.rand(adata.n_obs, 50)
adata.obsm["X_umap"] = np.random.rand(adata.n_obs, 2)
adata.varm["PCs"]    = np.random.rand(adata.n_vars, 50)
```

### `obsp` / `varp` — pairwise graphs
Square sparse matrices: `obsp[k]` is `(n_obs, n_obs)`, `varp[k]` is
`(n_vars, n_vars)`. Cell-cell neighbor graphs (`connectivities`, `distances`)
and gene-gene correlations live here.

```python
from scipy.sparse import csr_matrix
n = adata.n_obs
adata.obsp["connectivities"] = csr_matrix((n, n))
```

### `uns` — unstructured annotations
Free-form nested dict for parameters, plotting palettes, cluster info, and
processing history. Persisted with the object.

```python
adata.uns["pca"] = {"variance_ratio": [0.15, 0.10], "params": {"n_comps": 50}}
adata.uns["cell_type_colors"] = ["#e41a1c", "#377eb8", "#4daf4a"]
```

### `raw` — pre-filtering snapshot
Optional attribute preserving `X` and `var` before you subset genes, so
downstream tools can still reach dropped features.

```python
adata.raw = adata.copy()                       # snapshot BEFORE filtering
adata = adata[:, adata.var["highly_variable"]] # keep only HVGs in the main obj
original = adata.raw.X                          # full matrix still reachable
```

## Object Properties

```python
adata.n_obs, adata.n_vars, adata.shape   # dimensions
adata.obs_names, adata.var_names         # index labels
adata.is_view                            # True if a lightweight slice
adata.isbacked                           # True if X lives on disk (backed mode)
adata.filename                           # backing file path, if backed
```

## Creating AnnData Objects

```python
# Minimal
adata = ad.AnnData(np.random.rand(100, 2000))

# From a labelled DataFrame (rows = observations, columns = variables)
df = pd.DataFrame(np.random.rand(100, 50),
                  index=[f"cell_{i}" for i in range(100)],
                  columns=[f"gene_{i}" for i in range(50)])
adata = ad.AnnData(df)

# With every slot at once
adata = ad.AnnData(
    X=np.random.rand(100, 2000).astype("float32"),
    obs=obs, var=var,
    layers={"counts": np.random.randint(0, 100, (100, 2000))},
    obsm={"X_pca": np.random.rand(100, 50)},
    uns={"experiment": "demo"},
)
```

## Access Patterns

```python
# Vector extraction (searches obs columns AND var_names)
adata.obs_vector("cell_type")   # an obs column as an array
adata.obs_vector("ACTB")        # expression of one gene across observations
adata.var_vector("gene_name")   # a var column as an array

# Slicing (see references/manipulation.md for the full matrix of forms)
adata[0:10, 0:100]                        # by integer position
adata[["cell_1", "cell_2"], ["ACTB"]]     # by label
adata[adata.obs["cell_type"] == "T"]      # by metadata condition
```

## Convert to pandas

```python
df = adata.to_df()                 # X as a DataFrame (obs_names × var_names)
df = adata.to_df(layer="log1p")    # a specific layer instead of X
```

## Memory Levers (summary)

- Sparse `X` for count data (often 10-100x smaller).
- Categorical metadata for repeated strings: `adata.strings_to_categoricals()`.
- Backed / lazy mode for data larger than RAM — see `references/io.md`.
- Views avoid copying; call `.copy()` when you need an independent object.

Depth on each lever: `references/best-practices.md`.
