---
name: anndata
version: 0.1.0
description: >-
  AnnData is the annotated data-matrix container and .h5ad/.zarr file format at
  the base of the scverse single-cell ecosystem: a 2-D measurement matrix X
  paired with row-aligned obs and column-aligned var metadata, alternative
  layers, multidimensional obsm/varm, pairwise obsp/varp graphs, unstructured
  uns, and an optional raw snapshot. Use when creating, reading, or writing
  AnnData objects; handling .h5ad, .zarr, loom, mtx, csv, or 10x inputs; managing
  sparse matrices, backed mode, or Dask-backed lazy reads for data larger than
  RAM; concatenating batches or modalities; or subsetting, filtering, and
  QC-annotating single-cell data. Do NOT use for the analysis algorithms
  themselves (normalization, PCA, neighbors, clustering, UMAP — those live in
  scanpy) or for model training loops (use `pytorch-lightning`; AnnData's
  AnnLoader only bridges to PyTorch). For generic tabular work prefer `polars`;
  for out-of-core array compute prefer `dask`.
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (AnnData)"
---

# AnnData

## Overview

AnnData stores one primary 2-D matrix `X` of shape `(n_obs, n_vars)` — think
cells × genes — alongside metadata that stays aligned to it under every slice,
concatenation, and reorder. Around `X` sit `obs` (per-row DataFrame), `var`
(per-column DataFrame), `layers` (same-shape alternative matrices), `obsm`/`varm`
(multidimensional embeddings/loadings), `obsp`/`varp` (pairwise graphs), `uns`
(free-form dict), and `raw` (a pre-filtering snapshot). It is the on-disk
`.h5ad`/`.zarr` interchange format for the scverse ecosystem.

This skill is a **router**. It gives you the object model, a quick-start path,
and a capability map, then delegates deep API surface and pattern libraries to
`references/`.

## When to Use This Skill

- Creating, reading, or writing AnnData objects (`.h5ad`, `.zarr`).
- Loading single-cell inputs: mtx, loom, csv/tsv, excel, or 10x matrices.
- Holding a matrix with row/column metadata that must survive slicing.
- Managing memory: sparse `X`, categorical metadata, backed mode, or lazy
  Dask/xarray reads for datasets larger than RAM.
- Concatenating experimental batches (obs axis) or modalities (var axis).
- Subsetting, filtering, transposing, and QC-annotating annotated matrices.
- Feeding data into the scverse tools (`scanpy`, muon) or a PyTorch loader.

## When NOT to Use This Skill

- **Analysis algorithms** (normalization, HVG selection, PCA, neighbors, Leiden,
  UMAP) — AnnData only *holds* results; the algorithms live in `scanpy`. This
  skill covers the container, not the pipeline.
- **Model training loops** — use `pytorch-lightning`; `AnnLoader` only adapts an
  AnnData/AnnCollection into a PyTorch `DataLoader`.
- **Generic tabular ETL** with no aligned matrix — reach for `polars` or pandas.
- **Out-of-core array math** on a bare matrix — reach for `dask`; AnnData wraps
  Dask arrays but is not itself a compute engine.
- **Dimensionality reduction as an end** — see `umap-learn` / `scikit-learn`.

## Installation

```bash
uv pip install anndata          # core
uv pip install "anndata[dev]"   # with test/doc extras
```

## The Object Model

| Attribute | Shape / type | Holds |
|-----------|--------------|-------|
| `X` | `(n_obs, n_vars)` dense or sparse | primary measurements |
| `obs` / `var` | DataFrame, `n_obs` / `n_vars` rows | row / column metadata |
| `layers[k]` | `(n_obs, n_vars)` | alternative matrices (raw, normalized, scaled) |
| `obsm[k]` / `varm[k]` | `(n_obs, d)` / `(n_vars, d)` | embeddings / loadings |
| `obsp[k]` / `varp[k]` | `(n_obs, n_obs)` / `(n_vars, n_vars)` sparse | pairwise graphs |
| `uns` | dict | unstructured params, colors, history |
| `raw` | AnnData-like | pre-filtering snapshot of `X` + `var` |

Full component semantics, creation recipes, and access patterns:
`references/data-structure.md`.

## Quick Start

```python
import anndata as ad
import numpy as np
import pandas as pd

# Create: 100 cells x 2000 genes with metadata
X = np.random.rand(100, 2000).astype("float32")
obs = pd.DataFrame({"cell_type": ["T", "B"] * 50},
                   index=[f"cell_{i}" for i in range(100)])
var = pd.DataFrame(index=[f"ENSG{i:05d}" for i in range(2000)])
adata = ad.AnnData(X=X, obs=obs, var=var)

# Write / read (native format)
adata.write_h5ad("data.h5ad", compression="gzip")
adata = ad.read_h5ad("data.h5ad")

# Subset by metadata (returns a view — .copy() to detach)
t_cells = adata[adata.obs["cell_type"] == "T"].copy()

# Annotate
adata.obs["n_genes"] = (adata.X > 0).sum(axis=1)
print(adata.shape)  # (100, 2000)
```

## Capability Map

### Input / output — `references/io.md`
Native `.h5ad` and `.zarr`; alternative readers in the **`anndata.io`** namespace
(`read_csv`, `read_excel`, `read_hdf`, `read_mtx`, `read_text`, `read_umi_tools`,
`read_loom`); backed mode (`backed="r"`/`"r+"`) for query-without-load; lazy
Dask/xarray reads (`anndata.experimental.read_lazy`); element-level
`io.read_elem`/`io.write_elem`; compression and format conversion.

> **Boundary note:** AnnData ships **no 10x reader**. `read_10x_h5` and
> `read_10x_mtx` live in `scanpy` (`sc.read_10x_h5(...)`,
> `sc.read_10x_mtx(...)`). Plain `.mtx` goes through `ad.io.read_mtx`; verify
> orientation and `.T` if genes are stored as rows.

### Concatenation — `references/concatenation.md`
`ad.concat([...], axis=0)` stacks observations (batches); `axis=1` stacks
variables (modalities). `join="inner"|"outer"`, `merge`/`uns_merge` strategies,
`label`+`keys` for provenance, `index_unique` for collisions, `pairwise=True`
for graphs. Out-of-core: `experimental.concat_on_disk`; virtual:
`experimental.AnnCollection`.

### Manipulation — `references/manipulation.md`
Subsetting (indices, names, boolean masks, metadata conditions), views vs
copies, transposition, renaming and category renaming, sparse⇄dense and
string→categorical conversions, adding/removing components, reordering, QC
filtering, and train/test splits.

### Large-data strategies — `references/best-practices.md`
Sparse `X` and categorical metadata for memory; `backed="r"` + `to_memory()`
for filter-then-load; chunked iteration (`chunked_X`); `read_lazy`/AnnCollection
for out-of-core; `raw` before gene filtering; index-alignment and view-mutation
pitfalls; reproducibility metadata in `uns`.

## Scverse Ecosystem

AnnData is the shared substrate: `scanpy` runs the single-cell pipeline in place
on an AnnData; muon (`MuData`) wraps several AnnData objects for multimodal data;
`AnnLoader` (in `anndata.experimental`) exposes an AnnData or AnnCollection as a
PyTorch `DataLoader`. Keep raw counts in a `layer` or in `raw` so downstream
tools can recover pre-normalization values.

```python
import scanpy as sc                       # analysis lives here, not in anndata
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
sc.pp.highly_variable_genes(adata, n_top_genes=2000)
```

## Related Skills

`scikit-learn` and `umap-learn` (embeddings/clustering on `X` or `obsm`),
`pytorch-lightning` (training over `AnnLoader`), `dask` (out-of-core arrays
behind `read_lazy`), `polars` (tabular metadata wrangling), `matplotlib` /
`seaborn` (plotting extracted vectors).

## Reference Index

- `references/data-structure.md` — the object model, creation, access patterns.
- `references/io.md` — reading/writing every format, backed and lazy modes.
- `references/concatenation.md` — combining objects, joins, merge strategies.
- `references/manipulation.md` — subset, view/copy, convert, filter, reorder.
- `references/best-practices.md` — memory, performance, pitfalls, reproducibility.

## Resources

- Documentation: https://anndata.readthedocs.io/
- Source: https://github.com/scverse/anndata
- Scverse ecosystem: https://scverse.org/
