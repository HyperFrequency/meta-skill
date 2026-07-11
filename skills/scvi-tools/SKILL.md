---
name: scvi-tools
version: 0.1.0
description: >-
  scvi-tools is the scverse framework of deep generative (variational-inference /
  VAE) models for single-cell omics, built on PyTorch Lightning over AnnData:
  probabilistic batch correction and integration (scVI), semi-supervised
  annotation and reference label transfer (scANVI, scArches), CITE-seq RNA+protein
  (totalVI), paired/unpaired multi-omic RNA+ATAC (MultiVI, PeakVI, PoissonVI),
  spatial deconvolution and mapping (DestVI, Stereoscope, Tangram), and
  uncertainty-aware Bayesian differential expression. Use when you need
  model-based batch correction, transfer learning onto a reference atlas,
  multimodal integration, or DE with posterior uncertainty — always starting from
  RAW counts. Do NOT use for the standard exploratory pipeline (use `scanpy`), for
  the AnnData container / file I/O (use `anndata`), for bulk RNA-seq DE (use
  pydeseq2/DESeq2), or for generic non-count-aware VAEs, dimensionality reduction,
  or plotting (use `pytorch-lightning`, `umap-learn`, `matplotlib`).
metadata:
  skill-author: "adapted from openscience (Synthetic Sciences, Apache-2.0)"
  source-license: "Apache-2.0"
  source-library-license: "BSD-3-Clause (scvi-tools)"
---

# scvi-tools

## Overview

scvi-tools fits deep generative models to single-cell count data by variational
inference. An encoder network maps each cell's raw counts to a low-dimensional
latent variable `z`; a decoder reconstructs the counts from `z` conditioned on
registered technical covariates (batch, donor, etc.). Because covariates flow
through the decoder rather than `z`, the latent space is *batch-corrected* — it
captures biology while technical variation is explained away. The count
likelihood (negative binomial or zero-inflated NB) models overdispersion and
dropout natively, so you never log-normalize the input.

Every model follows the same four-step contract:

```
setup_anndata(adata, layer="counts", batch_key=...)  # register data + covariates
model = scvi.model.SCVI(adata)                        # build
model.train()                                          # fit the VAE
model.get_latent_representation() / .differential_expression()  # extract
```

This skill is a **router**. It gives the mental model, install path, a
quick-start, and a model map, then delegates the full model catalogue, the
Bayesian DE framework, production workflows, and the mathematics to
`references/`.

## When to Use This Skill

- You need **model-based batch correction / integration** across samples,
  donors, studies, or protocols (scVI, scANVI, SysVI).
- You want **semi-supervised annotation or reference mapping** — transfer labels
  from an annotated atlas to a query with uncertainty (scANVI, scArches).
- You have **multimodal data**: CITE-seq RNA+protein (totalVI), 10x Multiome or
  unpaired RNA+ATAC (MultiVI), ATAC alone (PeakVI, PoissonVI, scBasset).
- You have **spatial transcriptomics** and want cell-type deconvolution or
  single-cell-to-spot mapping (DestVI, Stereoscope, Tangram, gimVI).
- You need **differential expression / accessibility with posterior
  uncertainty**, batch correction folded in, and no arbitrary pseudocounts.
- You work with **specialized modalities**: methylation (MethylVI), flow/mass
  cytometry (CytoVI), doublet detection (Solo), RNA velocity (VeloVI),
  perturbation contrasts (contrastiveVI), or multi-sample decomposition (MrVI).

## When NOT to Use This Skill

- **Standard exploratory single-cell analysis** — QC, normalize, HVG, PCA,
  neighbors, UMAP, Leiden, marker ranking — is `scanpy`'s job. Reach for
  scvi-tools only when a probabilistic model earns its training cost.
- **Building / reading the AnnData object**, sparse/backed I/O, concatenation —
  that is the container layer, use `anndata`.
- **Bulk RNA-seq differential expression** with a negative-binomial GLM — use
  pydeseq2 (DESeq2). scvi-tools DE is a per-cell posterior contrast, not a bulk
  design-matrix model.
- **Log-normalized or scaled input** — these models require raw integer counts.
  Feeding normalized data silently degrades or NaNs training.
- **Generic (non-count) VAEs, embeddings, or plotting** — use
  `pytorch-lightning` / plain PyTorch, `umap-learn`, `matplotlib`.

## Installation

```bash
uv pip install scvi-tools            # CPU / auto
uv pip install "scvi-tools[cuda]"    # + CUDA (GPU strongly recommended >10k cells)
```

Core models import from `scvi.model` (SCVI, SCANVI, TOTALVI, PEAKVI, POISSONVI,
MULTIVI, AUTOZI, AmortizedLDA, DestVI/CondSCVI). Community / specialized models
import from `scvi.external` (SOLO, GIMVI, CellAssign, Tangram, Stereoscope,
ContrastiveVI, SCBASSET, SysVI, MRVI, and others). **The namespace and some
accessor names vary by version — confirm imports against
[docs.scvi-tools.org](https://docs.scvi-tools.org/en/stable/api/index.html).**

## Quick Start

```python
import scvi
import scanpy as sc

adata = sc.read_h5ad("data.h5ad")

# scvi-tools needs RAW counts — snapshot them before any normalization
adata.layers["counts"] = adata.X.copy()
sc.pp.highly_variable_genes(adata, n_top_genes=2000, flavor="seurat_v3",
                            layer="counts", batch_key="batch", subset=True)

# 1. Register data + technical covariates
scvi.model.SCVI.setup_anndata(
    adata,
    layer="counts",
    batch_key="batch",
    continuous_covariate_keys=["pct_counts_mt"],
)

# 2. Build + train the VAE
model = scvi.model.SCVI(adata, n_latent=30, gene_likelihood="nb")
model.train(max_epochs=400, early_stopping=True)

# 3. Extract batch-corrected latent + denoised expression
adata.obsm["X_scVI"] = model.get_latent_representation()
adata.layers["scvi_normalized"] = model.get_normalized_expression(library_size=1e4)

# 4. Hand off to scanpy for clustering / visualization
sc.pp.neighbors(adata, use_rep="X_scVI")
sc.tl.umap(adata)
sc.tl.leiden(adata)

# 5. Posterior differential expression between clusters
de = model.differential_expression(groupby="leiden", group1="0", group2="1",
                                    mode="change", delta=0.25)
model.save("scvi_model", overwrite=True)
```

Read `references/workflows.md` for the fully explained pipeline, hyperparameters,
GPU tuning, reference mapping, and troubleshooting.

## Model Map

Pick a model by data modality and goal. Full per-model API, parameters, and
selection guidance live in the reference files below.

### Core: scRNA-seq + ATAC — `references/models-core.md`
- **scVI** — unsupervised integration, batch correction, denoising, DE. The
  default entry point and the base for Solo, DestVI, and scArches.
- **scANVI** — semi-supervised annotation; init `from_scvi_model`, `predict()`
  labels (with `soft=True` for probabilities).
- **AUTOZI** — gene-level zero-inflation detection. **VeloVI** — RNA velocity.
  **contrastiveVI** — isolate perturbation effects. **CellAssign** — marker-based
  annotation. **Solo** — doublet detection. **AmortizedLDA** — topic modeling.
- **PeakVI / PoissonVI** — scATAC peak vs fragment-count modeling, differential
  accessibility. **scBasset** — sequence-based ATAC with TF-motif interpretation.

### Integration: multimodal, spatial, specialized — `references/models-integration.md`
- **totalVI** (CITE-seq RNA+protein), **MultiVI** (paired/unpaired RNA+ATAC),
  **MrVI** (multi-sample variation decomposition).
- **DestVI / Stereoscope** (reference-based spatial deconvolution), **Tangram**
  (single-cell→spot mapping + gene imputation), **gimVI / scVIVA / ResolVI**.
- **MethylVI/MethylANVI** (methylation), **CytoVI** (flow/CyTOF), **SysVI**
  (large-scale integration), **Decipher** (trajectory), **scArches** (reference
  mapping via `load_query_data`).

### Bayesian differential expression — `references/differential-expression.md`
`model.differential_expression(...)` — `"vanilla"` vs `"change"` mode, `delta`
effect-size threshold, `bayes_factor` / `lfc_mean` / `is_de_fdr_*` outputs, FDR
control, multimodal DE (protein via totalVI, accessibility via PeakVI), and
comparison to Wilcoxon.

### Theory — `references/theory.md`
Variational inference and the ELBO, VAE architecture, NB/ZINB/Poisson count
likelihoods, the batch-correction formulation, Bayes factors and FDP, and how
scVI compares to PCA, Harmony, and Seurat integration.

## Common Pitfalls (full list in `references/workflows.md`)

- **Raw counts only.** Register the untouched count layer via `layer="counts"`;
  never log-normalize or scale first. This is the #1 cause of NaN loss and
  garbage latents.
- **Register every known covariate** in `setup_anndata` (`batch_key`,
  `categorical_covariate_keys`, `continuous_covariate_keys`) — the model can only
  correct variation you declare.
- **HVG selection uses `flavor="seurat_v3"`** on the counts layer; other flavors
  expect log-normalized data and will mis-rank on raw counts.
- **`setup_anndata` binds a specific AnnData.** Re-run it after subsetting or
  reloading; loading a saved model requires the same `adata` schema.
- **Early stopping + validation ELBO.** Watch `model.history["elbo_validation"]`;
  a still-decreasing curve means undertrained, divergence means lr too high.
- **DE needs enough cells per group** (~>50) and benefits from `mode="change"`
  with a `delta` so tiny, biologically trivial fold-changes aren't called.
- **Set seeds** with `scvi.settings.seed = 0` for reproducible latents and DE.

## Related Skills

`scanpy` (the exploratory pipeline scvi-tools plugs into — cluster/UMAP its
latent), `anndata` (the container and I/O layer these models read/write),
`pytorch-lightning` (the training backend; tune trainer/callbacks there),
`umap-learn` (embedding the `X_scVI` latent), `shap` (interpreting model
outputs), `flow-cytometry-analysis` and `bioimage-analysis` (sibling modality
skills — CytoVI feeds the former), `matplotlib` / `seaborn` (customizing spatial
and DE plots).

## Reference Index

- `references/models-core.md` — scRNA-seq + ATAC models: API, params, selection.
- `references/models-integration.md` — multimodal, spatial, specialized models.
- `references/differential-expression.md` — Bayesian DE/DA framework and outputs.
- `references/workflows.md` — end-to-end pipeline, tuning, GPU, mapping, troubleshooting.
- `references/theory.md` — variational inference, VAE, likelihoods, DE math.

## Resources

- Documentation: https://docs.scvi-tools.org/en/stable/
- Tutorials: https://docs.scvi-tools.org/en/stable/tutorials/index.html
- API reference: https://docs.scvi-tools.org/en/stable/api/index.html
- Scverse ecosystem: https://scverse.org/ (anndata, scanpy, muon, squidpy)
