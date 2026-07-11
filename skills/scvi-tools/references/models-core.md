# Core models: scRNA-seq and ATAC-seq

Per-model purpose, when-to-use, key API, and parameters for the scRNA-seq and
chromatin-accessibility models. All models follow the
`setup_anndata → build → train → extract` contract and require **raw counts**.

> Namespace note: core models import from `scvi.model`; several here
> (contrastiveVI, scBasset, VeloVI, Solo, CellAssign) live under `scvi.external`
> or a companion package, and the exact path and some accessor names vary by
> version — confirm against docs.scvi-tools.org.

## scVI — the default model

Unsupervised integration, batch correction, denoising, and DE for scRNA-seq. It
is the base other models extend (Solo, DestVI, scArches reference mapping).

**Use when** you are starting analysis, need batch-corrected embeddings, want
denoised/normalized expression, or want posterior DE.

```python
scvi.model.SCVI.setup_anndata(adata, layer="counts", batch_key="batch")
model = scvi.model.SCVI(adata, n_latent=30, gene_likelihood="nb")
model.train(max_epochs=400, early_stopping=True)

latent      = model.get_latent_representation()      # batch-corrected embedding
normalized  = model.get_normalized_expression()      # denoised expression
de          = model.differential_expression(groupby="cell_type",
                                            group1="A", group2="B")
```

**Key parameters**
- `n_latent` (default 10) — latent dimensionality; 10-30 typical, larger for
  heterogeneous data.
- `n_layers` (1) / `n_hidden` (128) — encoder/decoder depth and width.
- `dropout_rate` (0.1) — network dropout.
- `gene_likelihood` — `"zinb"` (zero-inflated NB, sparse 10x data), `"nb"`
  (many current workflows prefer this), or `"poisson"`.
- `dispersion` — `"gene"` or `"gene-batch"` (batch-specific dispersion).

**Common outputs**: `get_latent_representation()`, `get_normalized_expression()`,
`differential_expression()`, `get_feature_correlation_matrix()`.

## scANVI — semi-supervised annotation

Extends scVI with cell-type labels to jointly correct batch and predict labels
from a partially annotated dataset. The standard label-transfer model.

**Use when** you have some labeled cells and want to annotate the rest, or map a
query onto a labeled reference.

```python
# Warm-start from a trained scVI model (recommended)
scanvi = scvi.model.SCANVI.from_scvi_model(
    scvi_model, unlabeled_category="Unknown", labels_key="cell_type")
scanvi.train(max_epochs=20)

preds  = scanvi.predict()               # hard labels for every cell
probs  = scanvi.predict(soft=True)      # per-class probabilities
latent = scanvi.get_latent_representation()
```

**Key parameters**: `labels_key`, `unlabeled_category`, plus all scVI params.

## AUTOZI — zero-inflation detection

Learns which genes are zero-inflated (technical dropout vs biological zero),
returning gene-level zero-inflation parameters. Use to characterize dropout in
very sparse datasets.

```python
scvi.model.AUTOZI.setup_anndata(adata, layer="counts")
model = scvi.model.AUTOZI(adata); model.train()
alphas_betas = model.get_alphas_betas()   # per-gene ZI Beta parameters
```

## VeloVI — RNA velocity

Probabilistic RNA velocity from spliced/unspliced counts with uncertainty. Use
for differentiation dynamics. Requires spliced (`Ms`) and unspliced (`Mu`) moment
layers (compute with scVelo first). VeloVI ships as the companion `velovi`
package.

```python
VELOVI.setup_anndata(adata, spliced_layer="Ms", unspliced_layer="Mu")
model = VELOVI(adata); model.train()
latent_time = model.get_latent_time()
velocity    = model.get_velocity()
```

## contrastiveVI — perturbation isolation

Splits variation into a *shared* background latent and a *target* (perturbation-
specific) latent, so treatment effects are separated from baseline biology. Use
for drug/CRISPR screens and control-vs-treated contrasts. Requires a background
(control) subset and a target subset.

Extract with `get_latent_representation(representation="shared")` and
`representation="salient"/"target"` (name varies by version).

## CellAssign — marker-based annotation

Probabilistic assignment of cells to types from a binary marker matrix
(genes × cell types). Use when you have curated markers but no annotated
reference. Lives in `scvi.external`.

```python
from scvi.external import CellAssign
CellAssign.setup_anndata(adata, size_factor_key="size_factor", layer="counts")
model = CellAssign(adata, marker_gene_mat)   # DataFrame: genes (rows) × types (cols), 0/1
model.train()
adata.obs["celltype"] = model.predict().idxmax(axis=1)
```

## Solo — doublet detection

Semi-supervised doublet detection built on a trained scVI model by simulating
artificial doublets. Run per-batch. Lives in `scvi.external`.

```python
from scvi.external import SOLO
solo = SOLO.from_scvi_model(scvi_model)
solo.train()
preds = solo.predict()                # DataFrame with doublet/singlet scores
adata.obs["doublet"] = preds["doublet"]
```

## AmortizedLDA — topic modeling

Latent Dirichlet Allocation over expression: each cell is a mixture of gene-
program "topics". Use for interpretable, program-level decomposition.

```python
scvi.model.AmortizedLDA.setup_anndata(adata, layer="counts")
model = scvi.model.AmortizedLDA(adata, n_topics=10); model.train()
cell_topics = model.get_latent_representation()   # per-cell topic proportions
```
The gene-by-topic loading accessor name varies by version — check the API docs.

---

## PeakVI — scATAC peak analysis

VAE for scATAC-seq peak-count matrices: batch-corrected accessibility embeddings
and differential accessibility. The default ATAC model.

**Use when** you have a called-peak count matrix (cells × peaks), the most common
scATAC format.

```python
scvi.model.PEAKVI.setup_anndata(adata, batch_key="batch")   # peaks in adata.X
model = scvi.model.PEAKVI(adata, n_latent=20)
model.train(max_epochs=400)

adata.obsm["X_PeakVI"] = model.get_latent_representation()
da = model.differential_accessibility(groupby="cell_type", group1="A", group2="B")
```

**Key parameters**: `n_latent` (10), `n_hidden` (128), `region_factors` (True —
learn peak-specific scaling, helps with technical variation),
`latent_distribution` (`"normal"` or `"ln"`).

## PoissonVI — quantitative ATAC fragments

Models fragment **counts** (not binary peak presence) with a Poisson likelihood,
capturing graded accessibility. Choose over PeakVI when you have high-coverage
fragment-count data and care about subtle quantitative differences.

```python
scvi.model.POISSONVI.setup_anndata(adata, batch_key="batch")
model = scvi.model.POISSONVI(adata); model.train()
latent = model.get_latent_representation()
```

## scBasset — sequence-based ATAC

CNN over peak DNA sequences: batch correction *plus* interpretability — TF-motif
enrichment, in-silico mutagenesis, and accessibility prediction for new
sequences. Choose when you want regulatory/sequence insight, not just an
embedding. Requires extracted peak sequences and a genome reference; more compute
than PeakVI. Lives in `scvi.external`.

---

## Model selection — scRNA-seq

| Goal | Model |
|------|-------|
| Unsupervised integration, batch correction, DE | **scVI** |
| Annotate from partial labels / reference | **scANVI** |
| Marker-based annotation (no reference) | **CellAssign** |
| Detect zero-inflated genes | **AUTOZI** |
| RNA velocity / dynamics | **VeloVI** |
| Perturbation-specific effects | **contrastiveVI** |
| Doublet QC | **Solo** |
| Interpretable gene programs | **AmortizedLDA** |

## Model selection — ATAC

| Situation | Model |
|-----------|-------|
| Standard called-peak matrix, fast | **PeakVI** |
| High-coverage fragment counts, quantitative | **PoissonVI** |
| Want TF motifs / sequence interpretation | **scBasset** |
| Paired RNA+ATAC (10x Multiome) | **MultiVI** (see `models-integration.md`) |

## ATAC best practices

- Filter peaks present in very few cells; QC cells on peak count and TSS
  enrichment.
- Always pass `batch_key` when integrating multiple samples.
- Store the latent in `adata.obsm["X_PeakVI"]` and hand off to `scanpy` for
  neighbors/UMAP/Leiden.
- ATAC matrices are large — use GPU and consider `region_factors=True`.
