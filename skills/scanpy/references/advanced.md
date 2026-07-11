# Advanced Analysis and Failure Modes

Extensions beyond the core pipeline, plus the mistakes that silently corrupt
results. Read `workflow.md` first for the base pipeline.

## Trajectory inference (PAGA + DPT)

PAGA abstracts the cluster graph into a coarse connectivity map; diffusion
pseudotime orders cells along it from a chosen root.

```python
sc.tl.paga(adata, groups="leiden")
sc.pl.paga(adata, color="leiden")                 # inspect connectivity first

# Optionally re-initialize UMAP from the PAGA layout for a cleaner tree
sc.tl.umap(adata, init_pos="paga")

# Diffusion pseudotime — requires a diffusion map and a root cell
sc.tl.diffmap(adata)
adata.uns["iroot"] = int(np.flatnonzero(adata.obs["leiden"] == "0")[0])
sc.tl.dpt(adata)
sc.pl.umap(adata, color="dpt_pseudotime")
```

Choose `iroot` from biology (e.g. the stem/progenitor cluster), not arbitrarily —
pseudotime direction depends entirely on it. For richer trajectories (fate
probabilities, RNA velocity kernels) use CellRank; for spliced/unspliced velocity
use scVelo. Those are separate scverse packages, not scanpy.

## Condition contrasts within a cell type

`rank_genes_groups` also compares experimental groups. Subset to one cell type so
composition differences do not confound the contrast.

```python
sub = adata[adata.obs["cell_type"] == "CD8 T"].copy()
sc.tl.rank_genes_groups(sub, groupby="condition",
                        groups=["treated"], reference="control", method="wilcoxon")
de = sc.get.rank_genes_groups_df(sub, group="treated")
```

**Boundary:** this is a per-cell nonparametric test that treats every cell as an
independent replicate (pseudoreplication) and inflates significance. For real
statistical DE with biological replicates, aggregate to pseudobulk per
sample×celltype and run pydeseq2 (DESeq2). Scanpy's test is for exploration.

## Gene-set and cell-cycle scoring

```python
sc.tl.score_genes(adata, ["CD3D", "CD3E", "CD3G"], score_name="T_cell_score")
sc.pl.umap(adata, color="T_cell_score")

sc.tl.score_genes_cell_cycle(adata, s_genes=s_list, g2m_genes=g2m_list)
# adds .obs["S_score"], .obs["G2M_score"], .obs["phase"]
```

Cell-cycle scores let you either interpret proliferation or regress it out
(`sc.pp.regress_out(adata, ["S_score", "G2M_score"])`) when it dominates the
embedding — do this deliberately, not by default.

## Batch integration

Choose by where the batch effect must be removed:

```python
# Graph level (fast, integration only for neighbors/UMAP/clustering)
sc.external.pp.bbknn(adata, batch_key="batch")          # replaces sc.pp.neighbors

# PCA level (corrected embedding in .obsm["X_pca_harmony"])
sc.external.pp.harmony_integrate(adata, key="batch")    # needs harmonypy
sc.pp.neighbors(adata, use_rep="X_pca_harmony")

# Expression level (mutates .X — ComBat)
sc.pp.combat(adata, key="batch")
```

**Boundary:** for model-based integration that also yields a denoised latent
space, imputation, and probabilistic label transfer, use scvi-tools (scVI /
scANVI). Scanpy's built-ins are linear/graph heuristics — good defaults, not deep
models. Never integrate away a batch that is confounded with your biological
condition; you will erase the signal you care about.

## Doublet detection

```python
sc.pp.scrublet(adata)                              # .obs["predicted_doublet"], "doublet_score"
adata = adata[~adata.obs["predicted_doublet"]].copy()
```

Run on raw counts before normalization, ideally per sample. Complements (does not
replace) an upper `n_genes_by_counts` QC bound.

## Subclustering

To resolve substructure inside one cluster, isolate it and recompute the graph on
that subset — the global PCA under-resolves within-cluster variation.

```python
tcells = adata[adata.obs["leiden"] == "3"].copy()
sc.pp.highly_variable_genes(tcells, n_top_genes=2000)
sc.tl.pca(tcells); sc.pp.neighbors(tcells); sc.tl.umap(tcells)
sc.tl.leiden(tcells, resolution=0.4, flavor="igraph", n_iterations=2)
```

## Label transfer (`ingest`)

Map labels from an annotated reference onto a query embedded in the same space.

```python
var_shared = adata_ref.var_names.intersection(adata_query.var_names)
sc.tl.ingest(adata_query[:, var_shared], adata_ref[:, var_shared], obs="cell_type")
```

For robust cross-dataset mapping under batch effects, prefer a trained scvi-tools
model or a dedicated reference-mapping tool over `ingest`.

## Failure modes and pitfalls

- **Scaled data into `rank_genes_groups`**: marker tests on z-scored `.X` are
  meaningless. Keep `adata.raw` log-normalized and let the test default to it.
- **`.raw` mismatch**: subsetting genes then plotting with `use_raw=True` reads a
  differently-shaped `.raw`; gene sets can silently mismatch. Confirm
  `adata.raw.var_names` covers the genes you plot.
- **Views mutated in place**: `adata[mask]` is a view; downstream in-place calls
  emit an `ImplicitModificationWarning` or error. Always `.copy()` after slicing.
- **Stale neighbor graph**: changing PCA or `n_pcs` without re-running
  `sc.pp.neighbors` leaves UMAP/Leiden on the old graph — results look fine but
  are wrong. Recompute `neighbors` after any reduction change.
- **`highly_variable_genes` flavor vs input scale**: `seurat_v3` wants raw
  counts; `seurat`/`cell_ranger` want log-normalized. Wrong pairing yields a
  degenerate HVG set.
- **Leiden reproducibility**: cluster count and labels shift across runs and
  package versions; pin `random_state`, `flavor`, and `n_iterations`, and record
  the scanpy/leidenalg versions (`sc.logging.print_versions()`).
- **Memory on `regress_out` / dense `scale`**: both densify and can OOM on large
  datasets. Checkpoint (`adata.write`) before them; consider skipping.
- **Ambient RNA / empty droplets**: scanpy does not remove ambient contamination.
  Use a dedicated tool (CellBender / SoupX) upstream if it matters.
- **Non-unique gene names**: 10x symbol duplicates break gene lookups — call
  `adata.var_names_make_unique()` right after loading.
