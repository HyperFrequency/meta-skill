---
name: scanpy
version: 0.1.0
description: >-
  Scanpy is the scverse Python toolkit for end-to-end single-cell (scRNA-seq and
  related) analysis over AnnData objects: quality control, normalization,
  highly-variable-gene selection, scaling, PCA, neighbor graphs, UMAP/t-SNE
  embeddings, Leiden/Louvain clustering, marker-gene ranking, cell-type
  annotation, trajectory and pseudotime (PAGA, DPT), gene-set scoring, batch
  integration, and publication figures. Use when you have a cell-by-gene count
  matrix (.h5ad, 10x mtx/h5, csv, loom) and need an established exploratory
  pipeline from raw counts to annotated clusters and plots. Do NOT use for
  building/holding the AnnData container or file I/O (use `anndata`); for deep
  probabilistic single-cell models such as scVI, totalVI, or scANVI (use
  scvi-tools); for bulk RNA-seq differential expression (use pydeseq2/DESeq2); or
  for generic plotting and ML that is not single-cell-aware (use `matplotlib`,
  `seaborn`, `scikit-learn`, `umap-learn`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (Scanpy)"
---

# Scanpy

## Overview

Scanpy is a scalable single-cell analysis toolkit built on the `anndata`
container. Every step mutates one `AnnData` object *in place*: preprocessing
functions (`sc.pp.*`) transform `.X` and write metrics into `.obs`/`.var`,
tools (`sc.tl.*`) write results into `.obsm`/`.obs`/`.uns`, and plotting
(`sc.pl.*`) reads them back. The canonical pipeline is:

```
QC → normalize → log1p → HVG → (scale) → PCA → neighbors → UMAP → Leiden → markers → annotate
```

This skill is a **router**. It gives you the mental model, an install path, a
quick-start pipeline, and a capability map, then delegates the full API surface,
plotting patterns, advanced analyses, and failure modes to `references/`.

## When to Use This Skill

- Analyzing a single-cell count matrix (10x mtx/h5, `.h5ad`, csv, loom).
- Running quality control and filtering low-quality cells/genes.
- Normalizing, selecting highly variable genes, and reducing dimensionality.
- Computing UMAP/t-SNE embeddings and Leiden/Louvain clusters.
- Ranking marker genes and annotating cell types from known markers.
- Trajectory / pseudotime inference (PAGA, diffusion pseudotime).
- Gene-set / cell-cycle scoring, condition contrasts, batch integration.
- Producing publication-quality single-cell figures.

## When NOT to Use This Skill

- **Constructing or reading the AnnData object itself**, sparse/backed/lazy I/O,
  concatenating batches — that is the container layer, use `anndata`.
- **Deep generative / probabilistic models** (scVI, totalVI, scANVI, MultiVI,
  label transfer via a trained model) — use scvi-tools.
- **Bulk RNA-seq differential expression** with a negative-binomial GLM — use
  pydeseq2 (DESeq2); scanpy's `rank_genes_groups` is a per-cell nonparametric
  test, not a bulk DE model.
- **Spatial-specific analysis** (neighborhood enrichment, ligand-receptor,
  image features) — use squidpy; scanpy handles the expression side only.
- **Generic dimensionality reduction / clustering / plotting** with no
  single-cell semantics — use `scikit-learn`, `umap-learn`, `matplotlib`,
  `seaborn`.

## Installation

```bash
uv pip install scanpy
uv pip install "scanpy[leiden]"     # + igraph + leidenalg for Leiden clustering
uv pip install harmonypy scrublet   # optional: batch integration, doublets
```

Leiden clustering needs `igraph`+`leidenalg`; Harmony integration needs
`harmonypy`; doublet detection needs `scrublet`. Import as `import scanpy as sc`.

## Quick Start

```python
import scanpy as sc

sc.settings.verbosity = 1
sc.settings.set_figure_params(dpi=80, facecolor="white")

adata = sc.read_10x_mtx("data/filtered_feature_bc_matrix/", var_names="gene_symbols")

# 1. QC — flag mito genes, compute metrics, filter
adata.var["mt"] = adata.var_names.str.startswith("MT-")
sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], inplace=True)
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)
adata = adata[adata.obs.pct_counts_mt < 10].copy()

# 2. Normalize + log, then snapshot for downstream gene lookups
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
adata.raw = adata                       # keep log-normalized values in .raw

# 3. Feature selection + reduction (subset is optional; PCA can use the mask)
sc.pp.highly_variable_genes(adata, n_top_genes=2000)
sc.tl.pca(adata, n_comps=50)
sc.pp.neighbors(adata, n_neighbors=15, n_pcs=40)
sc.tl.umap(adata)

# 4. Cluster + markers
sc.tl.leiden(adata, resolution=0.5, flavor="igraph", n_iterations=2)
sc.tl.rank_genes_groups(adata, "leiden", method="wilcoxon")

sc.pl.umap(adata, color="leiden", legend_loc="on data")
adata.write("results/processed.h5ad")
```

Read `references/workflow.md` for the fully explained pipeline with parameter
guidance and the decision points at each step.

## Capability Map

### End-to-end workflow — `references/workflow.md`
The complete pipeline with rationale for each step: QC metrics and thresholds,
normalization strategies (`normalize_total`, `log1p`), HVG flavors
(`seurat`, `cell_ranger`, `seurat_v3`), whether to `scale`/`regress_out`, PCA
component selection via the variance-ratio elbow, neighbor-graph tuning,
embeddings, multi-resolution clustering, marker ranking, and cell-type
annotation from a marker dictionary.

### API reference — `references/api-reference.md`
Function tables by module: readers/writers, `sc.pp.*` (preprocessing),
`sc.tl.*` (tools), `sc.pl.*` (plotting), `sc.get.*` (result extraction), and
`sc.settings`. Import conventions and common keyword arguments.

### Plotting — `references/plotting.md`
QC plots, embedding plots (PCA/UMAP/t-SNE colored by cluster or gene), marker
visualizations (`rank_genes_groups_*`, `dotplot`, `matrixplot`,
`stacked_violin`, `heatmap`, `tracksplot`), trajectory plots, multi-panel
figures via `ax=`, and publication-quality settings, palettes, and export.

### Advanced analysis & failure modes — `references/advanced.md`
Trajectory (PAGA + diffusion pseudotime), condition contrasts within a cell
type, gene-set and cell-cycle scoring, batch integration (BBKNN, Harmony,
ComBat) and its boundary vs scvi-tools, doublet detection (`scrublet`),
subclustering, label transfer (`ingest`), plus the pitfalls that silently
corrupt results.

## Common Pitfalls (full list in `references/advanced.md`)

- **`.raw` / `use_raw`**: set `adata.raw = adata` *after* `log1p`. Gene-expression
  plots and `rank_genes_groups` default to `.raw`; if you scaled `.X` without a
  `.raw` snapshot, plots show z-scores, not expression.
- **Views vs copies**: boolean-mask slicing returns a *view*. Append `.copy()`
  before mutating, or later in-place ops warn or fail.
- **Leiden defaults are changing**: pass `flavor="igraph", n_iterations=2`
  explicitly to get the modern, faster path and silence the deprecation warning.
- **`scale`/`regress_out` are optional and lossy**: both destroy count structure
  and can remove biological signal; many current workflows skip them and run PCA
  on log-normalized HVGs. Never feed scaled data to `rank_genes_groups`.
- **`neighbors` before `umap`/`leiden`**: UMAP and clustering read the neighbor
  graph in `.obsp`; recompute `neighbors` if you change `n_pcs` or the PCA.
- **Cluster labels are strings** (`"0"`, `"1"`, …) and unstable across runs; set
  a random seed and never assume numeric ordering.

## Related Skills

`anndata` (the container, I/O, concatenation — scanpy operates *on* it),
scvi-tools (deep probabilistic models and model-based label transfer), pydeseq2
(bulk DE), `flow-cytometry-analysis` and `bioimage-analysis` (sibling
single-cell/imaging modalities), `umap-learn` and `scikit-learn` (the general
algorithms scanpy wraps), `matplotlib` / `seaborn` (customizing extracted
plots), `polars` / `dask` (wrangling large `.obs` tables or out-of-core arrays).

## Reference Index

- `references/workflow.md` — explained end-to-end pipeline with parameters.
- `references/api-reference.md` — functions by module + common kwargs.
- `references/plotting.md` — visualization patterns and publication export.
- `references/advanced.md` — trajectory, contrasts, integration, failure modes.

## Resources

- Documentation: https://scanpy.readthedocs.io/
- Tutorials: https://scanpy.readthedocs.io/en/stable/tutorials/
- Single-cell best practices: https://www.sc-best-practices.org/
- Scverse ecosystem: https://scverse.org/ (anndata, muon, squidpy, scvi-tools)
