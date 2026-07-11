---
name: cellxgene-census
version: 0.1.0
description: >-
  Query the CZ CELLxGENE Census — a versioned TileDB-SOMA collection of 60M+
  standardized single-cell RNA expression profiles spanning human and mouse
  tissues, diseases, and cell types. Use when you need population-scale
  expression or metadata from the largest curated single-cell atlas: filter
  cells by cell_type / tissue / disease, count or profile populations, build
  reference-atlas comparisons, stream out-of-core matrices too big for RAM, or
  feed a PyTorch training loop. Covers open_soma, get_anndata, get_obs/get_var,
  value-filter syntax, axis_query streaming, presence matrices, and scanpy
  handoff. Do NOT use to analyze your OWN single-cell data (use scanpy /
  scvi-tools directly), for non-transcriptomic assays, for bulk RNA-seq, or when
  you need a matrix the Census does not host — it serves raw counts curated from
  CELLxGENE Discover only.
metadata:
  skill-author: adapted from openscience (Synthetic Sciences, Apache-2.0)
  source-license: Apache-2.0
  source-library-license: MIT (cellxgene-census, Chan Zuckerberg Initiative)
---

# CZ CELLxGENE Census

## Overview

The CZ CELLxGENE Census is a programmatic, versioned view over the single-cell
RNA data curated in CELLxGENE Discover — tens of millions of cells (60M+ in
recent builds) from human and mouse, with harmonized metadata (cell type,
tissue, disease, assay, donor) and raw count matrices. It is stored as a
TileDB-SOMA object collection hosted in the cloud, so you query slices remotely
without downloading whole datasets.

This skill routes you through the `cellxgene-census` Python API: opening a
versioned Census, exploring metadata, pulling filtered slices into AnnData,
streaming matrices that exceed RAM, and handing off to `scanpy` / PyTorch.

Two rules govern almost every query:

- **Always filter `is_primary_data == True`** unless you are deliberately
  studying cross-dataset duplicates — cells recur across datasets and will be
  double-counted otherwise.
- **Pin `census_version`** for any analysis you need to reproduce; the default
  `"stable"` tag advances over time.

## When to Use This Skill

- Filtering single-cell expression by `cell_type`, `tissue`, `disease`, `assay`, or `donor_id`.
- Counting or profiling cell populations across the whole atlas.
- Building reference-atlas comparisons or cross-tissue / cross-disease contrasts.
- Streaming an expression matrix too large for memory (out-of-core statistics, embeddings).
- Feeding standardized single-cell data into a PyTorch training loop.
- Loading a Census slice as AnnData to continue in a `scanpy` workflow.

## When NOT to Use This Skill

- **Analyzing your own single-cell data** — the Census only serves data already
  curated in CELLxGENE Discover. Use `scanpy` or `scvi-tools` on your files directly.
- **Non-RNA or spatial-only assays**, bulk RNA-seq, ATAC, or proteomics — the
  Census carries raw scRNA counts (plus some spatial), not arbitrary modalities.
- **You need a specific gene the Census dropped during construction** — check the
  dataset presence matrix first (see references).
- **Downstream ML mechanics** once data is in memory — hand off to `pytorch-lightning`,
  `scikit-learn`, or `umap-learn`.

## Install

```bash
uv pip install cellxgene-census
# ML / dataloader extras (experimental, API shifts by version — see references):
uv pip install "cellxgene-census[experimental]"
```

## Core Workflow

Open the Census with a context manager so remote handles close cleanly. `open_soma`
returns a SOMA collection with two branches: `census_info` (summary + dataset
catalog) and `census_data` (per-organism experiments keyed `"homo_sapiens"` /
`"mus_musculus"`).

```python
import cellxgene_census

with cellxgene_census.open_soma(census_version="2023-12-15") as census:
    ...  # query inside the block; default is census_version="stable"
```

**Explore before you pull.** Query metadata to size a request and learn what
values exist, then pull expression. `get_obs` / `get_var` return pandas
DataFrames of cell / gene metadata:

```python
    obs = cellxgene_census.get_obs(
        census, "homo_sapiens",
        value_filter="tissue_general == 'lung' and is_primary_data == True",
        column_names=["cell_type"],
    )
    print(obs["cell_type"].value_counts())   # what cell types exist, how many cells
```

**Pull a slice into AnnData** when the result fits in memory (rule of thumb:
< ~100k cells). `get_anndata` filters cells with `obs_value_filter`, genes with
`var_value_filter`, and trims returned columns with `obs_column_names`:

```python
    adata = cellxgene_census.get_anndata(
        census=census,
        organism="Homo sapiens",
        obs_value_filter="cell_type == 'B cell' and tissue_general == 'lung' and is_primary_data == True",
        var_value_filter="feature_name in ['CD19', 'MS4A1', 'CD79A']",
        obs_column_names=["assay", "disease", "sex", "donor_id"],
    )
```

Note the organism-name quirk: `get_anndata` takes `organism="Homo sapiens"`
(scientific name, with a space), while `get_obs` / `get_var` and the collection
key use the snake-case `"homo_sapiens"`. Both forms are accepted where documented.

**Stream out-of-core** when a query exceeds RAM. Open an `axis_query` on the
organism experiment and iterate the X matrix as Arrow tables (columns
`soma_data`, `soma_dim_0` = cell, `soma_dim_1` = gene) — compute running
statistics instead of materializing everything:

```python
import tiledbsoma as soma

    query = census["census_data"]["homo_sapiens"].axis_query(
        measurement_name="RNA",
        obs_query=soma.AxisQuery(value_filter="tissue_general == 'brain' and is_primary_data == True"),
        var_query=soma.AxisQuery(value_filter="feature_name in ['FOXP2', 'TBR1']"),
    )
    total = count = 0
    for batch in query.X("raw").tables():   # pyarrow.Table chunks
        vals = batch["soma_data"].to_numpy()
        total += vals.sum(); count += len(vals)
    mean_expression = total / count
```

## Value-Filter Syntax (essentials)

Filters are Python-like strings parsed by TileDB-SOMA:

- Comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`
- Membership: `in`, e.g. `tissue_general in ['lung', 'liver']`
- Boolean: `and` / `&`, `or` / `|`, grouped with parentheses
- Booleans compare against `True` / `False`: `is_primary_data == True`

Prefer ontology term IDs (`cell_type_ontology_term_id == 'CL:0000236'`) over free
text when you need cross-dataset consistency. Full operator table, the complete
metadata field list, and SOMA object types are in
[references/census-schema.md](references/census-schema.md).

## Deeper Material

- [references/census-schema.md](references/census-schema.md) — full `obs` / `var`
  field catalog, complete filter-syntax rules, SOMA object model (`census_info`
  vs `census_data`, Experiment / Measurement / DataFrame / SparseNDArray), data
  inclusion criteria, UMI-vs-read count caveats, presence matrix, versioning.
- [references/query-patterns.md](references/query-patterns.md) — copy-ready
  patterns for exploratory / AnnData / out-of-core / PyTorch / `scanpy` /
  multi-dataset queries, incremental (Welford) statistics, best practices,
  common pitfalls, and a troubleshooting guide (too many cells, memory errors,
  duplicates, gene-not-found, version drift).

## Downstream Handoff

Once a slice is in AnnData, continue in the standard single-cell toolchain:
`scanpy` for normalization / HVG / neighbors, `umap-learn` for embeddings,
`pytorch-lightning` or `scikit-learn` for modeling. The Census experimental ML
module (`cellxgene_census.experimental.ml`, and the newer standalone
`tiledbsoma_ml` package) exposes streaming PyTorch dataloaders so you can train
without materializing the matrix — but that API is experimental and its class /
function names have shifted between releases, so check your installed version.
Example dataloader code and the version caveat live in
[references/query-patterns.md](references/query-patterns.md).
