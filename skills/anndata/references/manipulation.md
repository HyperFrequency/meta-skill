# Data Manipulation

Subset, transform, and reorganize AnnData objects. Every slice keeps `obs`,
`var`, `layers`, `obsm`, `varm`, `obsp`, and `varp` aligned automatically.

## Subsetting

Indexing is 2-D: `adata[obs_selector, var_selector]`. A single argument selects
observations (`adata[obs_selector]`).

```python
import anndata as ad
import numpy as np

adata = ad.AnnData(np.random.rand(1000, 2000))

# By integer position
adata[0:100, 0:500]
adata[[0, 10, 20], :]

# By label
adata[["cell_0", "cell_1"], ["gene_0", "gene_10"]]

# By boolean mask (prefer numpy arrays — see best-practices for why)
adata[np.asarray(adata.obs["quality"] > 0.5), :]

# By metadata condition
adata[adata.obs["cell_type"] == "T"]
adata[(adata.obs["cell_type"].isin(["A", "B"])) &
      (adata.obs["quality"] > 0.7),
      adata.var["highly_variable"]]
```

## Views vs copies

Slicing returns a **view** — a lightweight reference sharing memory with the
parent. Materialize with `.copy()` when you will store or mutate the subset.

```python
view = adata[0:100, :]
view.is_view           # True
indep = view.copy()    # independent object
indep.is_view          # False
```

Mutating a view can write through to the parent, and deleting the parent can
invalidate a view — see `references/best-practices.md`.

## Transposition

```python
adata_T = adata.T      # swaps obs<->var (and obsm<->varm, obsp<->varp)
adata.shape            # (1000, 2000)
adata_T.shape          # (2000, 1000)
```

## Renaming

```python
adata.obs_names = [f"cell_{i}" for i in range(adata.n_obs)]
adata.var_names = [f"gene_{i}" for i in range(adata.n_vars)]

adata.obs_names_make_unique()   # de-duplicate by appending suffixes
adata.var_names_make_unique()

# Rename the levels of a categorical column
adata.rename_categories("cell_type", ["T_cell", "B_cell", "Monocyte"])
```

## Type conversions

```python
# Strings -> categoricals (memory + smaller files)
adata.strings_to_categoricals()

# Dense <-> sparse
from scipy.sparse import csr_matrix, issparse
if not issparse(adata.X):
    adata.X = csr_matrix(adata.X)
else:
    adata.X = adata.X.toarray()

adata.layers["normalized"] = csr_matrix(adata.layers["normalized"])
```

## Adding and removing components

```python
# Add metadata — ALWAYS align external data on the index
adata.obs["score"] = np.random.rand(adata.n_obs)
ext = pd.read_csv("meta.csv", index_col="cell_id")
adata.obs["group"] = ext.loc[adata.obs_names, "group"]   # aligned, order-safe

# Add / replace slots
adata.layers["log1p"] = np.log1p(adata.X)
adata.obsm["X_pca"]   = np.random.rand(adata.n_obs, 50)

# Remove
del adata.layers["log1p"]
del adata.obsm["X_pca"]
del adata.uns["stale_key"]
adata.obs.drop("unwanted", axis=1, inplace=True)

# Grow by concatenation (see references/concatenation.md)
adata = ad.concat([adata, more_cells], axis=0)
```

## Reordering

```python
adata = adata[adata.obs.sort_values("quality").index, :]      # by metadata
adata = adata[:, sorted(adata.var_names)]                     # by var name
adata = adata[desired_cell_order, :]                          # match a list
```

## Chunked iteration

```python
for chunk in adata.chunked_X(chunk_size=1000):
    compute(chunk)     # process X without materializing all of it
```

## Quality-control filtering

```python
adata.obs["n_genes"]      = np.asarray((adata.X > 0).sum(axis=1)).ravel()
adata.obs["total_counts"] = np.asarray(adata.X.sum(axis=1)).ravel()
adata.var["n_cells"]      = np.asarray((adata.X > 0).sum(axis=0)).ravel()

adata = adata[adata.obs["n_genes"] > 200, :]
adata = adata[adata.obs["total_counts"] < 50000, :]
adata = adata[:, adata.var["n_cells"] >= 3]
```

Scanpy provides the same as `sc.pp.filter_cells` / `sc.pp.filter_genes` plus
`sc.pp.calculate_qc_metrics` — prefer those in a scanpy pipeline.

## Highly variable genes (manual)

```python
adata.var["variance"] = np.asarray(np.var(adata.X.toarray()
                                          if issparse(adata.X) else adata.X,
                                          axis=0)).ravel()
thresh = np.percentile(adata.var["variance"], 90)
adata.var["highly_variable"] = adata.var["variance"] > thresh
adata_hvg = adata[:, adata.var["highly_variable"]].copy()
```

## Train / test splits

```python
from sklearn.model_selection import train_test_split
train_idx, test_idx = train_test_split(
    np.arange(adata.n_obs), test_size=0.2,
    stratify=adata.obs["cell_type"], random_state=42,
)
adata_train = adata[train_idx, :].copy()
adata_test  = adata[test_idx, :].copy()
```
