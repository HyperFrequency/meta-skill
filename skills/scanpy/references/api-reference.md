# Scanpy API Reference

Functions by module. Import convention: `import scanpy as sc`. Signatures show
the commonly used keywords, not the full parameter list — consult
https://scanpy.readthedocs.io/ for exhaustive detail.

## Reading and writing

```python
sc.read_10x_mtx(path, var_names="gene_symbols")   # 10x Cell Ranger mtx directory
sc.read_10x_h5(filename)                           # 10x filtered/raw .h5
sc.read_h5ad(filename)                             # native AnnData
sc.read_csv(filename); sc.read_text(filename)
sc.read_loom(filename); sc.read_excel(filename, sheet)
sc.read_visium(path)                               # 10x Visium spatial

adata.write(filename)                              # -> .h5ad
adata.write_h5ad(filename, compression="gzip")
adata.write_loom(filename); adata.write_zarr(store)
```

Object construction and non-10x readers (`read_mtx`, backed/lazy modes) live in
the `anndata` skill.

## Preprocessing — `sc.pp.*`

```python
# QC
sc.pp.calculate_qc_metrics(adata, qc_vars=["mt"], inplace=True, log1p=False)
sc.pp.filter_cells(adata, min_genes=200)           # or min_counts / max_genes
sc.pp.filter_genes(adata, min_cells=3)             # or min_counts
sc.pp.scrublet(adata)                              # doublet scores (needs scrublet)

# Normalization / transform
sc.pp.normalize_total(adata, target_sum=1e4)       # None -> median depth
sc.pp.log1p(adata)

# Feature selection
sc.pp.highly_variable_genes(adata, n_top_genes=2000, flavor="seurat")
sc.pp.highly_variable_genes(adata, flavor="seurat_v3", layer="counts")  # raw counts
sc.pp.highly_variable_genes(adata, min_mean=0.0125, max_mean=3, min_disp=0.5)

# Scaling / regression (optional, lossy)
sc.pp.regress_out(adata, ["total_counts", "pct_counts_mt"])
sc.pp.scale(adata, max_value=10)

# Graph / reduction helpers
sc.pp.pca(adata, n_comps=50)                       # alias of sc.tl.pca
sc.pp.neighbors(adata, n_neighbors=15, n_pcs=40)

# Batch correction
sc.pp.combat(adata, key="batch")                   # in-place expression correction
```

## Tools — `sc.tl.*`

```python
# Reduction / embedding
sc.tl.pca(adata, n_comps=50, svd_solver="arpack")
sc.tl.umap(adata)
sc.tl.tsne(adata, n_pcs=40)
sc.tl.diffmap(adata)
sc.tl.draw_graph(adata, layout="fa")               # force-directed (ForceAtlas2)

# Clustering
sc.tl.leiden(adata, resolution=0.5, flavor="igraph", n_iterations=2)
sc.tl.louvain(adata, resolution=0.5)
sc.tl.dendrogram(adata, groupby="leiden")

# Markers / DE
sc.tl.rank_genes_groups(adata, "leiden", method="wilcoxon")   # or t-test, logreg
sc.get.rank_genes_groups_df(adata, group="0")                 # tidy result
sc.tl.filter_rank_genes_groups(adata, min_fold_change=1)

# Trajectory
sc.tl.paga(adata, groups="leiden")
sc.tl.dpt(adata)                                   # needs adata.uns["iroot"]

# Scoring
sc.tl.score_genes(adata, gene_list, score_name="score")
sc.tl.score_genes_cell_cycle(adata, s_genes=..., g2m_genes=...)

# Density / reference mapping
sc.tl.embedding_density(adata, basis="umap", groupby="leiden")
sc.tl.ingest(adata, adata_ref, obs="cell_type")    # label transfer onto adata
```

## Plotting — `sc.pl.*`

```python
# QC
sc.pl.violin(adata, ["n_genes_by_counts", "total_counts", "pct_counts_mt"],
             jitter=0.4, multi_panel=True)
sc.pl.scatter(adata, x="total_counts", y="pct_counts_mt")
sc.pl.highest_expr_genes(adata, n_top=20)

# Embeddings
sc.pl.pca(adata, color="leiden"); sc.pl.pca_variance_ratio(adata, log=True)
sc.pl.umap(adata, color=["leiden", "CD3D"])
sc.pl.tsne(adata, color="leiden"); sc.pl.diffmap(adata, color="leiden")

# Gene-set / cluster summaries
sc.pl.dotplot(adata, var_names, groupby="leiden")
sc.pl.matrixplot(adata, var_names, groupby="leiden")
sc.pl.stacked_violin(adata, var_names, groupby="leiden")
sc.pl.heatmap(adata, var_names, groupby="leiden")
sc.pl.tracksplot(adata, var_names, groupby="leiden")
sc.pl.dendrogram(adata, groupby="leiden")

# Marker results
sc.pl.rank_genes_groups(adata, n_genes=25, sharey=False)
sc.pl.rank_genes_groups_heatmap(adata, n_genes=10)
sc.pl.rank_genes_groups_dotplot(adata, n_genes=5)
sc.pl.rank_genes_groups_stacked_violin(adata, n_genes=5)
sc.pl.rank_genes_groups_matrixplot(adata, n_genes=5)

# Trajectory
sc.pl.paga(adata, color="leiden"); sc.pl.dpt_timeseries(adata)
```

## Result extraction — `sc.get.*`

```python
sc.get.rank_genes_groups_df(adata, group="0")      # names, scores, logFC, pvals
sc.get.obs_df(adata, keys=["CD3D", "leiden"])      # per-cell expression + metadata
sc.get.var_df(adata, keys=[...])
```

## Settings — `sc.settings`

```python
sc.settings.verbosity = 1                          # 0 error … 3 hint
sc.settings.set_figure_params(dpi=80, facecolor="white")
sc.settings.figdir = "./figures/"
sc.settings.n_jobs = 8                             # parallelism
sc.settings.autoshow = False; sc.settings.autosave = True
sc.logging.print_versions()                        # environment for reproducibility
```

## External wrappers — `sc.external.*`

```python
sc.external.pp.bbknn(adata, batch_key="batch")               # graph-level integration
sc.external.pp.harmony_integrate(adata, key="batch")         # PCA-level (needs harmonypy)
```

## Notes on accuracy

Some functions occasionally cited for scanpy do **not** exist in the public API
(e.g. there is no `sc.tl.kmeans` or `sc.pp.sqrt`). Use `scikit-learn`'s `KMeans`
on `adata.obsm["X_pca"]` for k-means; use `numpy` for a sqrt transform. When a
signature is uncertain, verify against the online reference before relying on it.
