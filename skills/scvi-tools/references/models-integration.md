# Integration models: multimodal, spatial, specialized

Models for joint multimodal analysis, spatial transcriptomics, and specialized
modalities. All require **raw counts**.

> Namespace note: totalVI, MultiVI, PeakVI and DestVI/CondSCVI are under
> `scvi.model`; many spatial and specialized models (Tangram, Stereoscope, gimVI,
> MrVI, SysVI, and others) live under `scvi.external`, and some accessor names
> vary by version — confirm against docs.scvi-tools.org.

## Multimodal

### totalVI — CITE-seq (RNA + protein)

Joint model of gene expression and surface-protein abundance from the same cells.
Learns a shared latent, denoises both modalities, imputes proteins for RNA-only
cells, and handles ambient-protein background. Use for CITE-seq / REAP-seq.

**Data**: RNA counts in a layer; protein counts in
`adata.obsm["protein_expression"]` (same cells).

```python
scvi.model.TOTALVI.setup_anndata(
    adata, layer="counts",
    protein_expression_obsm_key="protein_expression", batch_key="batch")
model = scvi.model.TOTALVI(adata, n_latent=20)
model.train(max_epochs=400)

adata.obsm["X_totalVI"] = model.get_latent_representation()
rna  = model.get_normalized_expression()
prot = model.get_normalized_expression(include_protein_background=True)  # protein side
```
Cluster on the joint latent (better than RNA alone). Use an empirical protein
background prior for ambient-protein datasets. DE works for both modalities
(`protein_expression=True`, see `differential-expression.md`).

### MultiVI — paired / unpaired RNA + ATAC

Integrates gene expression and chromatin accessibility across fully paired (10x
Multiome), partially paired, and completely unpaired cells, and imputes the
missing modality. Use to join separate RNA-seq and ATAC-seq experiments or to
predict one modality from the other.

```python
scvi.model.MULTIVI.setup_anndata(adata, batch_key="batch")
model = scvi.model.MULTIVI(adata, n_genes=n_genes, n_regions=n_regions)
model.train()
adata.obsm["X_MultiVI"] = model.get_latent_representation()
```
Features are concatenated in `adata.X` (genes then peaks); a modality column
marks which measurements each cell carries.

### MrVI — multi-sample decomposition

Decomposes variation into a shared latent and a sample-specific latent, enabling
sample-level comparisons (disease vs healthy, donor effects) at cell resolution.
Use for multi-donor / multi-condition studies where you want to separate
sample-driven from cell-type variation. Requires a `sample_key`. Provides
per-cell sample-specific representations and sample-sample distance matrices
(exact accessor names vary by version).

### Choosing among them

| Data | Model |
|------|-------|
| RNA + protein, same cells (CITE-seq) | **totalVI** |
| RNA + ATAC, paired or unpaired | **MultiVI** |
| Single-modality RNA, many samples | **MrVI** |

## Spatial transcriptomics

### DestVI — reference-based deconvolution

Multi-resolution deconvolution of spot-based spatial data (Visium) using a
single-cell reference: cell-type proportions per spot plus cell-type-specific
expression, with uncertainty. Two-stage — train a CondSCVI reference, then fit
DestVI on the spatial data.

```python
# Stage 1: single-cell reference
scvi.model.CondSCVI.setup_anndata(sc_adata, layer="counts", labels_key="cell_type")
sc_model = scvi.model.CondSCVI(sc_adata); sc_model.train()

# Stage 2: spatial
scvi.model.DestVI.setup_anndata(st_adata, layer="counts")
st_model = scvi.model.DestVI.from_rna_model(st_adata, sc_model)
st_model.train(max_epochs=2500)

proportions = st_model.get_proportions()             # cell-type props per spot
ct_expr     = st_model.get_scale_for_ct("T cells")   # per-CT expression at spots
```

### Stereoscope — simpler deconvolution

Reference-based proportion estimation, lighter than DestVI. Use for fast,
basic deconvolution. Split into `RNAStereoscope` (reference) and
`SpatialStereoscope` (spatial transfer) in `scvi.external`.

### Tangram — single-cell → spot mapping

Optimal-transport mapping of individual cells onto spatial coordinates; projects
cell annotations and imputes unmeasured genes at each location. Use for
single-cell-resolution spatial mapping and gene imputation. In `scvi.external`
(a companion `tangram` package also exists).

### gimVI / scVIVA / ResolVI

- **gimVI** — cross-modality imputation between spatial and single-cell data
  (impute genes not measured spatially).
- **scVIVA** — models cellular neighborhoods / microenvironments and
  environment-associated expression.
- **ResolVI** — resolution-aware denoising for noisy spatial data.

### Choosing among them

| Goal | Model |
|------|-------|
| Detailed reference deconvolution + uncertainty | **DestVI** |
| Fast/basic deconvolution | **Stereoscope** |
| Single-cell mapping + gene imputation | **Tangram** |
| Impute unmeasured spatial genes | **gimVI** |
| Microenvironment / niche analysis | **scVIVA** |
| Denoise noisy spatial data | **ResolVI** |

## Specialized modalities

| Model | Modality | Use |
|-------|----------|-----|
| **MethylVI** | scBS-seq methylation | unsupervised methylation embedding + denoising |
| **MethylANVI** | scBS-seq + labels | semi-supervised methylation annotation |
| **CytoVI** | flow / mass cytometry | batch correction of protein panels |
| **SysVI** | scRNA-seq | large-scale integration preserving biology |
| **Decipher** | scRNA-seq | trajectory / pseudotime |
| **peRegLM** | multiome | peak→gene regulatory links |
| **scArches** | any scvi model | reference mapping (see below) |

Methylation data register methylated/total counts; CytoVI reads protein
measurements from `obsm`. Analyze methylation and expression separately, then
integrate results downstream.

## Reference mapping (scArches)

Architectural-surgery transfer: freeze a reference model's core, add and fine-
tune query-specific nodes — no reference recomputation, no catastrophic
forgetting. Works with scVI and scANVI.

```python
ref_model = scvi.model.SCVI.load("reference_model", adata=ref_adata)
scvi.model.SCVI.prepare_query_anndata(query_adata, "reference_model")
q_model = scvi.model.SCVI.load_query_data(query_adata, "reference_model")
q_model.train(max_epochs=200, plan_kwargs={"weight_decay": 0.0})
query_latent = q_model.get_latent_representation()
```
Then transfer labels: with **scANVI** call `q_model.predict()`; with plain scVI,
fit a KNN on the reference latent and predict query labels. See
`workflows.md` for the full mapping recipe.

## Complete example: CITE-seq with totalVI

```python
import scvi, scanpy as sc

adata = sc.read_h5ad("cite_seq.h5ad")
adata.layers["counts"] = adata.X.copy()
sc.pp.highly_variable_genes(adata, n_top_genes=4000, flavor="seurat_v3",
                            layer="counts", batch_key="batch", subset=True)

scvi.model.TOTALVI.setup_anndata(
    adata, layer="counts",
    protein_expression_obsm_key="protein_expression", batch_key="batch")
model = scvi.model.TOTALVI(adata, n_latent=20)
model.train(max_epochs=400)

adata.obsm["X_totalVI"] = model.get_latent_representation()
sc.pp.neighbors(adata, use_rep="X_totalVI"); sc.tl.umap(adata); sc.tl.leiden(adata)

rna_de  = model.differential_expression(groupby="leiden", group1="0", group2="1")
prot_de = model.differential_expression(groupby="leiden", group1="0", group2="1",
                                        protein_expression=True)
model.save("totalvi_model", overwrite=True)
```
