# Standard scRNA-seq Workflow

The end-to-end scanpy pipeline with the reasoning and decision points at each
step. Every function mutates one `AnnData` in place unless noted. Prefer
explicit `.copy()` after any boolean-mask slice.

## 0. Setup and load

```python
import scanpy as sc
import numpy as np

sc.settings.verbosity = 1                       # 0 error, 1 warning, 2 info, 3 hint
sc.settings.set_figure_params(dpi=80, facecolor="white")
sc.settings.figdir = "./figures/"

adata = sc.read_10x_mtx("data/matrix_dir/", var_names="gene_symbols")
adata.var_names_make_unique()                   # gene symbols can collide
```

Readers: `sc.read_10x_mtx`, `sc.read_10x_h5`, `sc.read_h5ad`, `sc.read_csv`,
`sc.read_loom`, `sc.read_text`, `sc.read_visium`. Object *construction* and
non-10x I/O belong to the `anndata` skill.

## 1. Quality control

Flag gene families, compute per-cell metrics, then filter. `pct_counts_mt` is the
single most useful QC axis — dying cells leak cytoplasm and over-represent
mitochondrial transcripts.

```python
adata.var["mt"]   = adata.var_names.str.startswith("MT-")     # human; "mt-" for mouse
adata.var["ribo"] = adata.var_names.str.startswith(("RPS", "RPL"))
sc.pp.calculate_qc_metrics(adata, qc_vars=["mt", "ribo"], inplace=True, log1p=False)

sc.pp.filter_cells(adata, min_genes=200)        # drop near-empty droplets
sc.pp.filter_genes(adata, min_cells=3)          # drop genes seen in <3 cells
adata = adata[adata.obs.pct_counts_mt < 10].copy()
```

Metrics land in `.obs`: `n_genes_by_counts`, `total_counts`, `pct_counts_mt`.
**Always inspect distributions before choosing thresholds** — they are
dataset-specific. Typical starting points: `min_genes` 200–500, `min_cells`
3–10, `pct_counts_mt` 5–20. Consider an upper `n_genes_by_counts` bound to catch
doublets. See doublet detection in `advanced.md`.

## 2. Normalization

```python
sc.pp.normalize_total(adata, target_sum=1e4)    # counts-per-10k; None = median depth
sc.pp.log1p(adata)                              # log(x+1); sets adata.uns["log1p"]
adata.raw = adata                               # snapshot log-normalized values
```

Set `adata.raw` here so `sc.pl.*` gene plots and `rank_genes_groups` can recover
log-normalized expression even after you subset or scale `.X`.

## 3. Highly variable genes

```python
sc.pp.highly_variable_genes(adata, n_top_genes=2000, flavor="seurat")
```

Flavors: `seurat` and `cell_ranger` expect **log-normalized** input; `seurat_v3`
expects **raw counts** (run it before `log1p`, or pass a counts layer via
`layer=`). Typical `n_top_genes` 2000–3000. You need not physically subset —
`sc.tl.pca` honors the `highly_variable` mask automatically. Subset only to save
memory:

```python
# adata = adata[:, adata.var.highly_variable].copy()   # optional
```

## 4. Scaling and regression — OPTIONAL and lossy

Both steps destroy count structure and can remove biological signal. Modern
best-practice pipelines frequently **skip** them and run PCA directly on
log-normalized HVGs.

```python
sc.pp.regress_out(adata, ["total_counts", "pct_counts_mt"])   # slow; use sparingly
sc.pp.scale(adata, max_value=10)                              # z-score, clip at 10
```

If you scale `.X`, keep the earlier `adata.raw` snapshot so gene plots and marker
tests still show expression, not z-scores.

## 5. Dimensionality reduction

```python
sc.tl.pca(adata, n_comps=50, svd_solver="arpack")
sc.pl.pca_variance_ratio(adata, n_pcs=50, log=True)   # pick n_pcs at the elbow

sc.pp.neighbors(adata, n_neighbors=15, n_pcs=40)      # kNN graph in .obsp
sc.tl.umap(adata)                                     # writes .obsm["X_umap"]
# sc.tl.tsne(adata, n_pcs=40)                          # alternative embedding
```

Choose `n_pcs` from the variance-ratio elbow (commonly 20–50). `n_neighbors`
10–30 trades local detail for global smoothness. **Recompute `neighbors` if you
change the PCA or `n_pcs`** — UMAP and clustering read the stale graph otherwise.

## 6. Clustering

```python
sc.tl.leiden(adata, resolution=0.5, flavor="igraph", n_iterations=2)
```

Leiden is preferred over Louvain (better-connected communities, faster with the
`igraph` flavor). `resolution` controls granularity (0.4–1.2; higher = more
clusters). Sweep it and keep each result under its own key:

```python
for res in (0.3, 0.5, 0.8, 1.0):
    sc.tl.leiden(adata, resolution=res, key_added=f"leiden_{res}",
                 flavor="igraph", n_iterations=2)
```

Labels are **strings** (`"0"`, `"1"`, …) and not stable across runs — pin
`random_state` if you need reproducibility.

## 7. Marker genes

```python
sc.tl.rank_genes_groups(adata, "leiden", method="wilcoxon")   # per-cluster vs rest
sc.pl.rank_genes_groups(adata, n_genes=25, sharey=False)
markers = sc.get.rank_genes_groups_df(adata, group="0")       # tidy DataFrame
```

Methods: `wilcoxon` (recommended default), `t-test`, `t-test_overestim_var`,
`logreg`. This is a per-cell one-vs-rest test for *exploration* — it is not a
replacement for a bulk DE model (pydeseq2) when you have real replicates.

## 8. Cell-type annotation

```python
marker_genes = ["CD3D", "CD14", "MS4A1", "NKG7", "FCGR3A"]
sc.pl.dotplot(adata, marker_genes, groupby="leiden")          # inspect expression
sc.pl.umap(adata, color=marker_genes, use_raw=True)

cluster_to_celltype = {"0": "CD4 T", "1": "CD14+ Mono", "2": "B", "3": "CD8 T"}
adata.obs["cell_type"] = (
    adata.obs["leiden"].map(cluster_to_celltype).astype("category")
)
sc.pl.umap(adata, color="cell_type", legend_loc="on data")
```

Validate every label with **multiple** markers. For automated / model-based
annotation, use scvi-tools (scANVI) or a reference-mapping tool.

## 9. Save

```python
adata.write("results/processed.h5ad")           # full object, resumable
adata.obs.to_csv("results/cell_metadata.csv")   # labels + QC for external use
```

Write intermediate checkpoints — long pipelines can fail partway (e.g. an OOM in
`regress_out`), and recomputing PCA/UMAP is expensive.

## Parameter cheat-sheet

| Step | Parameter | Typical | Effect |
|------|-----------|---------|--------|
| filter_cells | `min_genes` | 200–500 | drop empty droplets |
| filter_genes | `min_cells` | 3–10 | drop rare genes |
| QC mask | `pct_counts_mt` | 5–20 | remove dying cells |
| normalize_total | `target_sum` | 1e4 / None | depth normalization |
| highly_variable_genes | `n_top_genes` | 2000–3000 | feature count |
| pca | `n_comps` | 50 | components computed |
| neighbors | `n_pcs` | 20–50 (elbow) | signal dimensions used |
| neighbors | `n_neighbors` | 10–30 | local vs global |
| leiden | `resolution` | 0.4–1.2 | cluster granularity |
