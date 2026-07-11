# Plotting Guide

Scanpy plots (`sc.pl.*`) mirror the tools (`sc.tl.*`) that produce their inputs.
Most accept `color` (a gene name or an `.obs` column), a `save` suffix, and
`show`. Gene-expression plots read `.raw` when `use_raw=True` (the default once
`adata.raw` is set) — pass `use_raw=False` to read the current `.X`.

## Quality control

```python
sc.pl.violin(adata, ["n_genes_by_counts", "total_counts", "pct_counts_mt"],
             jitter=0.4, multi_panel=True, save="_qc.pdf")
sc.pl.scatter(adata, x="total_counts", y="pct_counts_mt")
sc.pl.scatter(adata, x="total_counts", y="n_genes_by_counts")
sc.pl.highest_expr_genes(adata, n_top=20)
```

## Embeddings

```python
# PCA + elbow
sc.pl.pca(adata, color="leiden")
sc.pl.pca_variance_ratio(adata, n_pcs=50, log=True)
sc.pl.pca_loadings(adata, components=[1, 2, 3])

# UMAP: clusters, metadata, genes
sc.pl.umap(adata, color=["leiden", "cell_type", "batch"])
sc.pl.umap(adata, color=["CD3D", "CD14", "MS4A1"], use_raw=True)
sc.pl.umap(adata, color="leiden", legend_loc="on data",
           legend_fontsize=10, legend_fontoutline=2,
           add_outline=True, frameon=False, palette="Set2")

# t-SNE
sc.pl.tsne(adata, color="leiden", legend_loc="right margin")
```

## Cluster / gene-set summaries

Pick by shape of the story you are telling:

| Plot | Best for |
|------|----------|
| `sc.pl.dotplot` | mean expression + % expressing, compact marker panels |
| `sc.pl.matrixplot` | mean expression heat grid, genes × groups |
| `sc.pl.stacked_violin` | per-group distributions across many genes |
| `sc.pl.heatmap` | single-cell resolution, genes × cells within groups |
| `sc.pl.tracksplot` | expression trend bands across ordered groups |

```python
genes = ["CD3D", "CD14", "MS4A1", "NKG7", "FCGR3A"]
sc.pl.dotplot(adata, genes, groupby="leiden")
sc.pl.matrixplot(adata, genes, groupby="cell_type", standard_scale="var")
sc.pl.stacked_violin(adata, genes, groupby="leiden")
sc.pl.heatmap(adata, genes, groupby="cell_type", swap_axes=True,
              show_gene_labels=True)
```

## Marker-gene results

Run `sc.tl.rank_genes_groups` first; these read `adata.uns["rank_genes_groups"]`.

```python
sc.pl.rank_genes_groups(adata, n_genes=25, sharey=False)
sc.pl.rank_genes_groups_heatmap(adata, n_genes=10, groupby="leiden",
                                show_gene_labels=True)
sc.pl.rank_genes_groups_dotplot(adata, n_genes=5)
sc.pl.rank_genes_groups_stacked_violin(adata, n_genes=5)
sc.pl.rank_genes_groups_matrixplot(adata, n_genes=5)
```

## Trajectory

```python
sc.pl.paga(adata, color="leiden")
sc.pl.paga(adata, color=["leiden", "dpt_pseudotime"])
sc.pl.umap(adata, color="dpt_pseudotime")
sc.pl.dpt_timeseries(adata)
```

## Density

```python
sc.tl.embedding_density(adata, basis="umap", groupby="cell_type")
sc.pl.embedding_density(adata, basis="umap", key="umap_density_cell_type")
```

## Multi-panel figures

Pass explicit axes and `show=False`; scanpy draws into your grid.

```python
import matplotlib.pyplot as plt
fig, axes = plt.subplots(2, 2, figsize=(12, 12))
sc.pl.umap(adata, color="leiden", ax=axes[0, 0], show=False)
sc.pl.umap(adata, color="CD3D",   ax=axes[0, 1], show=False)
sc.pl.umap(adata, color="CD14",   ax=axes[1, 0], show=False)
sc.pl.umap(adata, color="MS4A1",  ax=axes[1, 1], show=False)
fig.tight_layout(); fig.savefig("figures/panel.pdf")
```

## Publication settings and export

```python
sc.settings.set_figure_params(dpi=300, frameon=False, figsize=(5, 5),
                              facecolor="white")
sc.settings.figdir = "./figures/"
sc.settings.file_format_figs = "pdf"               # vector; or "svg"

# save="..." writes figdir/<plotfunc><suffix>, e.g. figures/umap_final.pdf
sc.pl.umap(adata, color="cell_type", save="_final.pdf")

# Or capture the figure object for manual control
fig = sc.pl.umap(adata, color="leiden", show=False, return_fig=True)
fig.savefig("figures/umap.pdf", dpi=300, bbox_inches="tight")
```

Tips: prefer vector formats (PDF/SVG); reuse one categorical palette across every
figure; use colorblind-safe palettes (`Set2`, `colorblind`); set
`frameon=False` and `legend_loc="on data"` for compact panels. For layout beyond
what scanpy exposes, drop to `matplotlib` / `seaborn` on axes you pass in.
